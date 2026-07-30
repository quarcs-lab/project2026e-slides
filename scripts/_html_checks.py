#!/usr/bin/env python3
"""Rendered-HTML smoke test for a beautiful-deck reveal.js deck (Tier B' of references/visual-qa.md).

The `beautiful-deck` skill copies this file into each deck as `slides/<deck>/scripts/_html_checks.py`.

Its sibling `_qa_checks.py` (Tier B) inspects the *source* — theme.scss, the .qmd, the figure
files. This one inspects the **deliverable**: the HTML that `quarto render` actually produced.
Those are different failure surfaces. A deck can pass every Tier-B check and still ship a broken
<img>, a chalkboard that never wired in, a leaked <FILL: ...> placeholder, or equations frozen as
raw LaTeX -- none of which the source can reveal.

Needs no browser and no third-party package: pure stdlib, runs in milliseconds, so it is cheap
enough for fast mode.

Checks
  1. Artifact       -- the .html exists, is non-trivially sized, and is NEWER than the .qmd.
  2. Structure      -- reveal.js scaffolding (.reveal + .slides) is present.
  3. Features       -- every feature the .qmd turns on left a footprint in the HTML.
  4. Dividers       -- at least one full-bleed data-background-color section.
  5. Slide count    -- <section> count is sane and consistent with the .qmd's headings.
  6. Figures        -- every <img> resolves (on disk when linked, non-empty when inlined).
  7. Placeholders   -- no leaked <FILL:>, {{MARKER}}, ?@ or unresolved cross-reference.
  8. Math           -- MathJax is wired and the emitted spans use \\(...\\) delimiters.

Usage:
    uv run python slides/<deck>/scripts/_html_checks.py slides/<deck>

Exit code: 0 = no failures (warnings allowed), 1 = at least one failure, 2 = usage error.
UNLIKE `_qa_checks.py`, which is diagnostic-only and always exits 0, this script GATES delivery.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# ---- tunables ----------------------------------------------------------------
MIN_HTML_BYTES = 20_000       # a real Quarto revealjs deck is well over this even non-embedded
MIN_SECTIONS = 3              # title + at least a couple of slides
MAX_SECTIONS = 200            # a deck this long is a defect in itself
MIN_DATA_URI_PAYLOAD = 100    # a data: URI shorter than this carries no real image
STALE_GRACE_SECONDS = 2.0     # git checkouts / editor saves jitter mtimes by fractions of a second

OK, WARN, FAIL = "ok", "warn", "fail"
GLYPH = {OK: "[✓]", WARN: "[~]", FAIL: "[✗]"}

_SCRIPT_OR_STYLE = re.compile(r"<(script|style)\b.*?</\1>", re.IGNORECASE | re.DOTALL)


def strip_code(html: str) -> str:
    """Drop <script>/<style> blocks so content checks only see slide content.

    Quarto inlines the whole reveal.js bundle, whose minified source contains JS template
    literals like `<img src="${t}">` and regex fragments that would otherwise register as
    broken figures or leaked placeholders. Feature detection still runs against the full
    HTML, because that is exactly where the plugin scripts live.
    """
    return _SCRIPT_OR_STYLE.sub("", html)


class Report:
    """Accumulates [✓]/[~]/[✗] assertions and renders them in source order."""

    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []

    def add(self, state: str, name: str, detail: str = "") -> None:
        self.rows.append((state, name, detail))

    def ok(self, name: str, detail: str = "") -> None:
        self.add(OK, name, detail)

    def warn(self, name: str, detail: str = "") -> None:
        self.add(WARN, name, detail)

    def fail(self, name: str, detail: str = "") -> None:
        self.add(FAIL, name, detail)

    def check(self, cond: bool, name: str, detail: str = "") -> bool:
        self.add(OK if cond else FAIL, name, detail)
        return cond

    def count(self, state: str) -> int:
        return sum(1 for s, _, _ in self.rows if s == state)

    def render(self) -> None:
        for state, name, detail in self.rows:
            suffix = f"  ({detail})" if detail else ""
            print(f"{GLYPH[state]} {name}{suffix}")


# ---- .qmd front-matter parsing (just enough; no YAML dependency) --------------
def strip_yaml_comments(line: str) -> str:
    """Drop a trailing ` # comment` so `chalkboard: true  # note` still parses, and a fully
    commented-out `# chalkboard: true` reads as absent."""
    out, in_str, quote = [], False, ""
    for ch in line:
        if in_str:
            out.append(ch)
            if ch == quote:
                in_str = False
        elif ch in "\"'":
            in_str = True
            quote = ch
            out.append(ch)
        elif ch == "#":
            break
        else:
            out.append(ch)
    return "".join(out)


def front_matter(qmd_text: str) -> str:
    """Return the leading `---`-delimited YAML block, comments stripped."""
    lines = qmd_text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    body: list[str] = []
    for ln in lines[1:]:
        if ln.strip() == "---":
            break
        body.append(strip_yaml_comments(ln))
    return "\n".join(body)


def yaml_flag(fm: str, key: str) -> bool | None:
    """True/False if `key: true|false` appears in the front matter, else None (unset)."""
    m = re.search(rf"^\s*{re.escape(key)}\s*:\s*(\S+)", fm, re.MULTILINE)
    if not m:
        return None
    val = m.group(1).strip().strip("\"'").lower()
    if val in ("true", "yes"):
        return True
    if val in ("false", "no"):
        return False
    return None


def yaml_value(fm: str, key: str) -> str | None:
    m = re.search(rf"^\s*{re.escape(key)}\s*:\s*(.+)$", fm, re.MULTILINE)
    return m.group(1).strip().strip("\"'") if m else None


# ---- checks ------------------------------------------------------------------
def check_artifact(rep: Report, html_path: Path, qmd_path: Path) -> str | None:
    """Confirm we are about to verify a fresh artifact. Returns the HTML text, or None."""
    if not html_path.exists():
        rep.fail("rendered HTML exists", f"{html_path} not found -- run `quarto render` first")
        return None
    size = html_path.stat().st_size
    rep.check(
        size >= MIN_HTML_BYTES,
        "rendered HTML is non-trivially sized",
        f"{size:,} bytes",
    )
    if qmd_path.exists():
        # Verifying a stale artifact is worse than not verifying: it reports on a deck that no
        # longer matches its source. Hard fail, not a warning -- but allow a couple of seconds
        # of slack, because a git checkout writes both files at effectively the same instant and
        # sub-second ordering between them is arbitrary.
        lag = qmd_path.stat().st_mtime - html_path.stat().st_mtime
        rep.check(
            lag <= STALE_GRACE_SECONDS,
            "rendered HTML is newer than the .qmd",
            f"stale by {lag:.0f}s -- re-render before trusting this report"
            if lag > STALE_GRACE_SECONDS else "fresh",
        )
    return html_path.read_text(encoding="utf-8", errors="ignore")


def check_structure(rep: Report, html: str) -> None:
    rep.check(
        'class="reveal"' in html and 'class="slides"' in html,
        "reveal.js structure present (.reveal + .slides)",
    )


# Each feature: the .qmd key that requests it -> (label, regexes any of which prove it shipped).
FEATURE_FOOTPRINTS: dict[str, tuple[str, tuple[str, ...]]] = {
    "chalkboard": ("chalkboard plugin", (r"RevealChalkboard", r"chalkboard[/\\]plugin", r"chalkboard")),
    "menu": ("menu plugin", (r"RevealMenu", r"menu[/\\]menu\.js", r"quarto-menu")),
    "progress": ("progress bar", (r"'?\"?progress'?\"?\s*:\s*true", r"class=\"progress\"")),
    "overview": ("overview mode", (r"'?\"?overview'?\"?\s*:\s*true",)),
}


def check_features(rep: Report, html: str, fm: str, qmd_body: str) -> None:
    """Assert that every feature the deck ASKS for actually shipped.

    Driven by the .qmd rather than hard-coded, so a deck that legitimately omits the chalkboard
    (e.g. an `embed-resources: true` single-file export, where it is incompatible) is not
    false-failed for it.
    """
    any_declared = False
    for key, (label, patterns) in FEATURE_FOOTPRINTS.items():
        if yaml_flag(fm, key) is not True:
            continue
        any_declared = True
        rep.check(
            any(re.search(p, html, re.IGNORECASE) for p in patterns),
            f"{label} requested and wired into the HTML",
        )

    # slide-number takes a format string (`c/t`), not a boolean.
    if yaml_value(fm, "slide-number"):
        rep.check(
            re.search(r"slideNumber", html) is not None,
            "slide numbers requested and wired into the HTML",
        )
        any_declared = True

    # Speaker notes are authored in the body, not the front matter.
    if "::: {.notes}" in qmd_body or ":::{.notes}" in qmd_body:
        n = len(re.findall(r'class="notes"', html))
        rep.check(n > 0, "speaker notes rendered", f"{n} note block(s)")
        any_declared = True

    if not any_declared:
        rep.warn("reveal.js features", "none declared in the .qmd -- nothing to verify")


def check_dividers(rep: Report, html: str) -> None:
    n = len(re.findall(r"data-background-color=", html))
    rep.check(n >= 1, "at least one full-bleed section divider", f"{n} found")


def check_slide_count(rep: Report, html: str, qmd_body: str) -> int:
    sections = len(re.findall(r"<section", html))
    headings = len(re.findall(r"^#{1,2} ", qmd_body, re.MULTILINE))
    rep.check(
        MIN_SECTIONS <= sections <= MAX_SECTIONS,
        "slide count is sane",
        f"{sections} <section> tags from {headings} heading(s)",
    )
    # Quarto nests `##` slides inside a wrapper <section> per `#` divider, so the rendered count
    # should never fall BELOW the heading count. If it does, slides were silently dropped.
    if headings and sections < headings:
        rep.fail(
            "every .qmd heading produced a slide",
            f"{sections} sections < {headings} headings -- slides were dropped",
        )
    return sections


def check_figures(rep: Report, html: str, html_path: Path, fm: str) -> None:
    """Verify every image reference, in whichever packaging mode the deck uses.

    embed-resources: false -> figures are linked; the path must exist on disk.
    embed-resources: true  -> figures are inlined as data: URIs; the payload must be non-empty.
    A deck can legitimately mix both, so classify per-image rather than per-deck.
    """
    srcs = re.findall(r'<img[^>]+src="([^"]+)"', html)
    srcs += re.findall(r'data-background-image="([^"]+)"', html)
    if not srcs:
        rep.warn("figure references", "no images referenced in this deck")
        return

    base = html_path.parent
    linked_ok, inline_ok, missing, empty, external = 0, 0, [], [], []
    for src in srcs:
        if src.startswith("data:"):
            payload = src.split(",", 1)[1] if "," in src else ""
            if len(payload) < MIN_DATA_URI_PAYLOAD:
                empty.append(src[:40] + "...")
            else:
                inline_ok += 1
        elif src.startswith(("http://", "https://", "//")):
            external.append(src)
        else:
            target = (base / src.split("?")[0].split("#")[0]).resolve()
            if target.exists():
                linked_ok += 1
            else:
                missing.append(src)

    mode = yaml_flag(fm, "embed-resources")
    detail = f"{linked_ok} linked + {inline_ok} inlined of {len(srcs)}"
    if mode is True and linked_ok and not missing:
        detail += " (embed-resources: true, but some stayed linked)"
    rep.check(not missing and not empty, "every figure reference resolves", detail)
    for m in missing:
        rep.fail("  missing figure on disk", m)
    for e in empty:
        rep.fail("  inlined figure has an empty payload", e)
    if external:
        # Not a failure -- but a deck presented offline (the usual case) will show a hole.
        rep.warn(
            "figures loaded from the network",
            f"{len(external)} external -- will break offline: {external[0]}",
        )


# Scaffold markers that must never survive into a delivered deck.
PLACEHOLDER_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"&lt;FILL:|<FILL:", "<FILL: ...> scaffold placeholder"),
    (r"\[FILL:", "[FILL: ...] scaffold placeholder"),
    (r"\{\{[A-Z_]{2,}\}\}", "{{MARKER}} substitution placeholder"),
    (r"\?@[\w-]+", "unresolved cross-reference (?@)"),
    (r"quarto-unresolved-ref", "unresolved cross-reference (Quarto)"),
)


def check_placeholders(rep: Report, html: str) -> None:
    leaks: list[str] = []
    for pattern, label in PLACEHOLDER_PATTERNS:
        hits = re.findall(pattern, html)
        if hits:
            sample = ", ".join(sorted({h if isinstance(h, str) else h[0] for h in hits})[:3])
            leaks.append(f"{label} x{len(hits)} ({sample})")
    rep.check(not leaks, "no leaked scaffold placeholders")
    for leak in leaks:
        rep.fail("  leaked placeholder", leak)


def check_math(rep: Report, html: str, fm: str) -> None:
    """Confirm a math engine is wired in, as far as static text can tell.

    How far that is depends on the engine, so this branches:

    MathJax (Quarto's default) typesets `\\(...\\)` delimiters that Pandoc has already written
    into the HTML. Raw `\\command` sitting inside a math span therefore means the delimiters came
    out wrong and nothing will render -- statically detectable.

    KaTeX renders entirely client-side from the LaTeX source, so raw `\\command` in the HTML is
    NORMAL and proves nothing either way. Judging a KaTeX deck by its source would report a
    failure on a deck that renders perfectly.

    Either way the authority on whether math *renders* is Tier C (`_browser_checks.py math`).
    """
    method = (yaml_value(fm, "html-math-method") or "").lower()
    spans = len(re.findall(r'class="math (?:inline|display)"', html))
    if spans == 0:
        rep.warn("math rendering", "deck contains no math -- nothing to verify")
        return

    if method == "katex":
        # Historically this option was broken in Quarto revealjs (it loaded KaTeX but never called
        # auto-render, shipping raw LaTeX). Verified working on Quarto 1.8.27 -- so this is a note,
        # not a failure. Tier C decides.
        rep.warn(
            "math engine is KaTeX, not the Quarto default",
            f"{spans} span(s); renders client-side so it cannot be judged statically "
            "-- Tier C required",
        )
        rep.check(
            re.search(r"katex", html, re.IGNORECASE) is not None,
            "KaTeX assets referenced",
        )
    else:
        rep.check(
            re.search(r"mathjax|tex-chtml|MathJax", html, re.IGNORECASE) is not None,
            "MathJax engine referenced",
            f"{spans} math span(s)",
        )
        rep.check(
            re.search(r'class="math (?:inline|display)">\\[a-zA-Z]', html) is None,
            r"math spans carry MathJax \(...\) delimiters, not raw \command",
        )
    print("     note: static only -- run `_browser_checks.py math` to confirm it renders")


# ---- main --------------------------------------------------------------------
def resolve_deck(deck_dir: Path) -> tuple[Path, Path]:
    """Return (qmd, html) for the deck, preferring <deck>/<deck>.{qmd,html}.

    `deck_dir.name` carries no useful information once a deck's contents ARE a repository root,
    so the glob fallbacks do real work here — and they have to identify the artifact by CONTENT.
    Excluding partials by name was not enough: a deck that sets `output-file: index.html` has no
    `<deck>.html`, and the old `sorted(glob("*.html"))` then picked `fonts.html` (a 1.7 KB
    `<style>` fragment) and every downstream check reported on that instead. It failed loudly
    only because it was under MIN_HTML_BYTES; a partial any larger would have failed silently.
    """
    qmd = deck_dir / f"{deck_dir.name}.qmd"
    if not qmd.exists():
        candidates = sorted(deck_dir.glob("*.qmd"))
        if candidates:
            qmd = candidates[0]
    html = qmd.with_suffix(".html")
    if not html.exists():
        html = deck_dir / "index.html"          # the `output-file: index.html` convention
    if not html.exists():
        reveal = [h for h in sorted(deck_dir.glob("*.html")) if _is_reveal_deck(h)]
        if reveal:
            html = max(reveal, key=lambda h: h.stat().st_size)
    return qmd, html


def _is_reveal_deck(path: Path) -> bool:
    """Does this HTML file look like a rendered reveal.js deck rather than a partial?"""
    try:
        head = path.read_text(encoding="utf-8", errors="ignore")[:200_000]
    except OSError:
        return False
    return 'class="reveal"' in head or "class='reveal'" in head


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: _html_checks.py slides/<deck>")
        return 2
    deck_dir = Path(sys.argv[1])
    if not deck_dir.is_dir():
        print(f"[✗] not a directory: {deck_dir}")
        return 2

    qmd, html_path = resolve_deck(deck_dir)
    qmd_text = qmd.read_text(encoding="utf-8", errors="ignore") if qmd.exists() else ""
    fm = front_matter(qmd_text)
    qmd_body = qmd_text[len(fm):] if fm else qmd_text

    print(f"== beautiful-deck rendered-HTML checks: {deck_dir} ==")
    print(f"   source: {qmd.name}    artifact: {html_path.name}\n")

    rep = Report()
    html = check_artifact(rep, html_path, qmd)
    if html is None:
        rep.render()
        print("\nHTML SUMMARY: 1 failure(s), 0 warning(s).  RESULT: FAIL")
        return 1

    content = strip_code(html)          # slide content only -- no bundled reveal.js source

    check_structure(rep, html)
    check_features(rep, html, fm, qmd_body)     # plugins live in <script> -- needs the full HTML
    check_dividers(rep, content)
    check_slide_count(rep, content, qmd_body)
    check_figures(rep, content, html_path, fm)
    check_placeholders(rep, content)
    check_math(rep, html, fm)                   # engine reference is a <script> src

    rep.render()
    n_fail, n_warn = rep.count(FAIL), rep.count(WARN)
    verdict = "FAIL" if n_fail else "PASS"
    print(f"\nHTML SUMMARY: {n_fail} failure(s), {n_warn} warning(s).  RESULT: {verdict}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
