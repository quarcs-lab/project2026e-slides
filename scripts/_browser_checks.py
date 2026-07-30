#!/usr/bin/env python3
"""Browser-driven checks for a beautiful-deck reveal.js deck (Tiers A / A' / C of visual-qa.md).

The `beautiful-deck` skill copies this file into each deck as
`slides/<deck>/scripts/_browser_checks.py`.

This is the only layer that sees what the AUDIENCE sees. Its siblings stop short:
  `_qa_checks.py`   (Tier B)  reads the source -- theme.scss, the .qmd, the figure files.
  `_html_checks.py` (Tier B') reads the rendered HTML as text.
Neither can tell you whether the page, once JavaScript has run, actually displays correctly.
The canonical example is math: a deck with `html-math-method: katex` emits perfectly well-formed
HTML and ships equations frozen as raw `\\hat\\alpha`.

Subcommands
  math    Confirm every equation typeset. Exit 1 if any did not.
  shots   Per-slide PNGs at 1280x720 (@2x) into `_qa/` -- the record the graphics audit looks at.
  pdf     Slide-accurate PDF via reveal.js `?print-pdf`, WITH backgrounds.
  all     shots + pdf + math.

Usage (no project dependency -- `--with` builds a throwaway overlay env, lockfile untouched):
    uv run --with playwright python slides/<deck>/scripts/_browser_checks.py slides/<deck> math

Browser: launches the SYSTEM Google Chrome via `channel="chrome"`, so no `playwright install`
browser download is needed. Falls back to Playwright's bundled Chromium if that is unavailable.

Exit codes: 0 = passed or not applicable, 1 = a check FAILED, 2 = usage error,
            3 = no browser available (caller should report `[~]`, not `[✗]`).
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

CANVAS_W, CANVAS_H = 1280, 720
DEVICE_SCALE = 2
MATHJAX_TIMEOUT_MS = 25_000
SETTLE_MS = 1_500
DUMP_DOM_BUDGET_MS = 8_000   # async CDN fetch + typeset must finish before Chrome snapshots the DOM

CHROME_PATHS = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
)

EXIT_OK, EXIT_FAIL, EXIT_USAGE, EXIT_NO_BROWSER = 0, 1, 2, 3


# ---- deck resolution ---------------------------------------------------------
def resolve_deck(deck_dir: Path) -> tuple[Path, Path]:
    """(qmd, html). Identical to _html_checks.resolve_deck; keep the two in step.

    The artifact is identified by CONTENT, not by name: `deck_dir.name` means nothing once a
    deck's contents are a repository root, and a deck with `output-file: index.html` has no
    `<deck>.html`, in which case a name-based glob picked up `fonts.html` — a `<style>`
    fragment — and captured screenshots of it.
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


def deck_has_math(qmd: Path) -> bool:
    if not qmd.exists():
        return False
    text = qmd.read_text(encoding="utf-8", errors="ignore")
    return bool(re.search(r"\$\$.+?\$\$", text, re.DOTALL) or re.search(r"(?<!\$)\$[^$\n]+\$", text))


# ---- the math oracle ---------------------------------------------------------
# Run inside the page. Returns every `.math` element that MathJax did NOT typeset.
#
# This is deliberately DOM-based rather than a Reveal.next() walk reading visible text, which is
# how the upstream reference does it. Two reasons the walk is unsound:
#   1. Reveal.next() steps through FRAGMENTS before advancing slides, so a loop bounded by
#      getTotalSlides() silently stops short on any fragment-heavy deck -- the last slides are
#      never inspected.
#   2. Reveal hides pending fragments with `visibility: hidden`, which innerText omits. Math
#      inside a fragment is therefore invisible to a text scan even on slides it does reach.
# Querying the DOM covers every slide and every fragment at once, with no navigation at all.
#
# Selector precision matters here. Match ONLY Pandoc's own `class="math inline|display"` spans.
# A bare `.math` selector also picks up MathJax 2's *output* markup -- it wraps rendered glyphs in
# `<nobr><span class="math">` -- so every successfully typeset equation would be counted a second
# time as an un-rendered one, and a perfectly good deck would fail.
#
# Quarto revealjs ships MathJax **2**, which signals success with `<span class="MathJax">`.
# MathJax 3 uses `<mjx-container>`; KaTeX uses `.katex`. Accept any of the three so the probe
# survives a Quarto upgrade.
MATH_PROBE_JS = """
() => {
  const nodes = Array.from(
    document.querySelectorAll('.reveal .math.inline, .reveal .math.display')
  );
  const isTypeset = n => !!n.querySelector('.MathJax, mjx-container, .katex');
  const untypeset = nodes.filter(n => !isTypeset(n));
  return {
    total: nodes.length,
    engineLoaded: !!window.MathJax
      || !!document.querySelector('.MathJax, mjx-container, .katex'),
    untypeset: untypeset.slice(0, 8).map(n => (n.textContent || '').trim().slice(0, 70)),
    untypesetCount: untypeset.length,
  };
}
"""


def report_math(probe: dict, source: str) -> int:
    if probe["total"] == 0:
        print(f"[~] math render ({source}): deck contains no math -- nothing to verify")
        return EXIT_OK
    if not probe["engineLoaded"]:
        print(f"[✗] math render ({source}): no math engine ran -- {probe['total']} equation(s) "
              "will display as raw LaTeX")
        print("    check: the reveal math plugin loaded (revealjs/plugin/math/math.js), and the "
              "machine had network access -- MathJax is fetched from a CDN at runtime")
        return EXIT_FAIL
    if probe["untypesetCount"]:
        print(f"[✗] math render ({source}): {probe['untypesetCount']} of {probe['total']} "
              "equation(s) did NOT typeset")
        for sample in probe["untypeset"]:
            print(f"      raw: {sample}")
        return EXIT_FAIL
    print(f"[✓] math render ({source}): all {probe['total']} equation(s) typeset")
    return EXIT_OK


# ---- Playwright plumbing -----------------------------------------------------
def launch(pw):
    """System Chrome first (no browser download); bundled Chromium as fallback."""
    try:
        return pw.chromium.launch(channel="chrome")
    except Exception:
        try:
            return pw.chromium.launch()
        except Exception as exc:
            print(f"[~] no browser available: {str(exc).splitlines()[0]}")
            return None


def slide_grid(page) -> list[tuple[int, int]]:
    """Enumerate every (horizontal, vertical) slide index from the DOM.

    Preferred over stepping with Reveal.next(), which advances fragment-by-fragment and so does
    not correspond one-to-one with slides.
    """
    return [
        tuple(pair)
        for pair in page.evaluate(
            """
            () => {
              const stacks = Array.from(document.querySelectorAll('.reveal .slides > section'));
              const out = [];
              stacks.forEach((s, h) => {
                const subs = s.querySelectorAll(':scope > section').length;
                if (subs) { for (let v = 0; v < subs; v++) out.push([h, v]); }
                else out.push([h, 0]);
              });
              return out;
            }
            """
        )
    ]


def open_deck(page, html: str, query: str = "") -> None:
    page.goto(f"file://{html}{query}", wait_until="load", timeout=60_000)
    try:
        page.wait_for_selector("mjx-container, .reveal .slides section", timeout=MATHJAX_TIMEOUT_MS)
    except Exception:
        pass
    page.wait_for_timeout(SETTLE_MS)


# ---- Tier-2 fallback: Chrome CLI --dump-dom ----------------------------------
def chrome_binary() -> str | None:
    for path in CHROME_PATHS:
        if Path(path).exists():
            return path
    return shutil.which("google-chrome") or shutil.which("chromium")


def math_via_dump_dom(html: Path) -> int:
    """Runtime math check without Playwright, using Chrome's post-JavaScript DOM dump.

    Coarser than the Playwright probe -- it can only compare counts, not pinpoint which equation
    failed -- but it still catches the case that matters: no engine ran.

    `--virtual-time-budget` is REQUIRED here. MathJax is fetched from a CDN and typesets
    asynchronously; a bare --dump-dom snapshots the DOM at the load event, before any equation has
    been processed, and reports a perfectly good deck as broken. Note this is the opposite of the
    rule for screenshots and print-to-pdf, where the same flag breaks hash navigation and yields a
    blank page -- it helps only --dump-dom.
    """
    chrome = chrome_binary()
    if not chrome:
        print("[~] math render: neither Playwright nor Chrome available -- static checks only")
        return EXIT_NO_BROWSER
    try:
        dom = subprocess.run(
            [chrome, "--headless=new", "--disable-gpu",
             f"--virtual-time-budget={DUMP_DOM_BUDGET_MS}", "--dump-dom", f"file://{html}"],
            capture_output=True, text=True, timeout=120,
        ).stdout
    except Exception as exc:
        print(f"[~] math render: Chrome --dump-dom failed ({exc}) -- static checks only")
        return EXIT_NO_BROWSER

    # Pandoc's source spans, then the renderer's output markers (MathJax 2 / MathJax 3 / KaTeX).
    spans = len(re.findall(r'class="math (?:inline|display)"', dom))
    typeset = len(re.findall(r'<mjx-container|class="MathJax[ "]|class="katex', dom))
    if spans == 0:
        print("[~] math render (chrome --dump-dom): deck contains no math -- nothing to verify")
        return EXIT_OK
    if typeset == 0:
        print(f"[✗] math render (chrome --dump-dom): {spans} equation(s) present but MathJax "
              "produced no output -- the deck will display raw LaTeX")
        return EXIT_FAIL
    print(f"[✓] math render (chrome --dump-dom): MathJax typeset {typeset} container(s) "
          f"for {spans} math element(s)")
    print("     note: count-level check only -- rerun with Playwright to pinpoint a single failure")
    return EXIT_OK


FONT_PROBE_JS = """
async () => {
  // Force the faces to load before reading their status. A @font-face the page has not yet had
  // cause to render stays `unloaded` indefinitely, so `Array.from(document.fonts)` filtered to
  // `:loaded` is a race, not a test — it reported different answers for the same file depending
  // on what the browser had got round to. document.fonts.load() resolves either way, so a face
  // that is still not `loaded` afterwards genuinely cannot be loaded.
  for (const fam of ['Inter', '"Source Serif 4"']) {
    try { await document.fonts.load(`400 40px ${fam}`); } catch (e) { /* report via status */ }
  }
  await document.fonts.ready;
  // Measure a family against monospace. If the family is missing the browser falls back to the
  // same monospace, the widths coincide, and the delta is exactly 0. That is the whole test:
  // a bundled webfont that failed to load does not error, it silently substitutes.
  const delta = (fam) => {
    const c = document.createElement('canvas').getContext('2d');
    c.font = `40px ${fam}, monospace`;
    const a = c.measureText('Hamburgefonstiv').width;
    c.font = '40px monospace';
    return +(a - c.measureText('Hamburgefonstiv').width).toFixed(2);
  };
  const h2 = document.querySelector('.reveal h2') || document.querySelector('.reveal h1');
  const title = document.querySelector('#title-slide h1.title')
             || document.querySelector('#title-slide .title');
  return {
    faces: Array.from(document.fonts).map(f => `${f.family}:${f.status}`),
    titleFamily: title ? getComputedStyle(title).fontFamily : null,
    headingFamily: h2 ? getComputedStyle(h2).fontFamily : null,
    interDelta: delta('Inter'),
    serifDelta: delta('"Source Serif 4"'),
    bogusDelta: delta('"NoSuchFace12345"'),
  };
}
"""


def report_fonts(probe: dict) -> int:
    """Tier A' — the bundled webfonts actually loaded and are actually being used.

    This exists because the failure mode is SILENT. `fonts.html` carries the postmortem: an
    `@font-face` whose `url()` sits inside `theme.scss` resolves against the compiled stylesheet
    under `<deck>_files/libs/revealjs/dist/theme/`, finds reveal's own `fonts/` directory, and
    404s — while the deck renders perfectly in a fallback system serif. No error, no warning,
    and nothing a grep or a screenshot reliably catches. `embed-resources: true` changes the
    URL-resolution path again, so this is live risk, not history.

    `bogusDelta` is the control. A nonexistent family MUST measure 0 against monospace; if it
    does not, the measurement is meaningless and a green run here would prove nothing.
    """
    faces = probe.get("faces") or []
    loaded = {f.split(":")[0] for f in faces if f.endswith(":loaded")}
    fails = []

    if probe.get("bogusDelta") != 0:
        print(f"[✗] fonts: the probe itself is broken — a nonexistent family measured "
              f"{probe['bogusDelta']} against monospace instead of 0. Ignore the results below.")
        return EXIT_FAIL

    for want, delta_key in (("Inter", "interDelta"), ("Source Serif 4", "serifDelta")):
        d = probe.get(delta_key)
        if want not in loaded:
            fails.append(f"{want!r} is not in document.fonts as loaded (saw: {sorted(loaded)})")
        elif d == 0:
            fails.append(f"{want!r} reports loaded but measures identically to monospace "
                         "— it is not actually rendering")

    if fails:
        print("[✗] fonts: bundled webfonts did not take effect")
        for f in fails:
            print(f"    {f}")
        print("    check: @font-face lives in the head file loaded via `include-in-header`, NOT")
        print("           in theme.scss — see the postmortem at the top of fonts.html.")
        return EXIT_FAIL

    print(f"[✓] fonts: bundled webfonts loaded and rendering  "
          f"(Inter Δ{probe['interDelta']}, Source Serif 4 Δ{probe['serifDelta']}, control 0)")
    for label, key in (("title", "titleFamily"), ("headings", "headingFamily")):
        if probe.get(key):
            print(f"    {label}: {probe[key]}")
    return EXIT_OK


# ---- subcommands -------------------------------------------------------------
def run_math(page, html: Path) -> int:
    open_deck(page, str(html))
    return report_math(page.evaluate(MATH_PROBE_JS), "playwright")


def run_fonts(page, html: Path) -> int:
    open_deck(page, str(html))
    return report_fonts(page.evaluate(FONT_PROBE_JS))


def run_shots(page, html: Path, qa_dir: Path) -> int:
    open_deck(page, str(html))
    grid = slide_grid(page)
    if not grid:
        print("[✗] screenshots: no slides found in the rendered deck")
        return EXIT_FAIL
    qa_dir.mkdir(parents=True, exist_ok=True)
    # Clear previous captures first. A shorter deck would otherwise leave higher-numbered
    # screenshots from an earlier run behind, and the graphics audit would review slides that
    # no longer exist.
    for old in qa_dir.glob("slide-*.png"):
        old.unlink()
    for n, (h, v) in enumerate(grid):
        # Reveal ALL fragments before capturing. `Reveal.slide(h, v)` lands on fragment 0, so an
        # `.incremental` list or a `. . .` pause photographs as an empty slide — which reads as a
        # rendering defect to anyone (or any audit agent) reviewing the captures. The useful
        # record is the slide's final state, with everything on screen.
        page.evaluate(
            """([h, v]) => {
                if (!window.Reveal) return;
                Reveal.slide(h, v);
                for (let i = 0; i < 40 && Reveal.nextFragment(); i++) { /* reveal all */ }
            }""",
            [h, v],
        )
        page.wait_for_timeout(320)
        page.screenshot(path=str(qa_dir / f"slide-{n:02d}.png"))
    print(f"[✓] screenshots: {len(grid)} slide(s) -> {qa_dir}/slide-NN.png")
    return EXIT_OK


def run_pdf(page, html: Path, qa_dir: Path, name: str) -> int:
    """Slide-accurate PDF from reveal.js's ?print-pdf layout.

    `print_background=True` is the reason to do this here rather than with Chrome's CLI
    --print-to-pdf, which drops `data-background-color` and prints dark section dividers white.
    """
    qa_dir.mkdir(parents=True, exist_ok=True)
    out = qa_dir / f"{name}.pdf"
    open_deck(page, str(html), "?print-pdf")
    page.pdf(
        path=str(out),
        print_background=True,
        prefer_css_page_size=True,
        width=f"{CANVAS_W}px",
        height=f"{CANVAS_H}px",
        margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
    )
    size = out.stat().st_size
    if size < 50_000:
        print(f"[✗] pdf: {out} is only {size:,} bytes -- the print raced a partial render")
        return EXIT_FAIL
    print(f"[✓] pdf: {out} ({size:,} bytes, backgrounds included)")
    return EXIT_OK


# ---- main --------------------------------------------------------------------
def main() -> int:
    if len(sys.argv) < 2:
        print("usage: _browser_checks.py slides/<deck> [math|fonts|shots|pdf|all]")
        return EXIT_USAGE
    deck_dir = Path(sys.argv[1])
    mode = (sys.argv[2] if len(sys.argv) > 2 else "all").lower()
    if mode not in ("math", "fonts", "shots", "pdf", "all"):
        print(f"unknown subcommand: {mode}")
        return EXIT_USAGE
    if not deck_dir.is_dir():
        print(f"[✗] not a directory: {deck_dir}")
        return EXIT_USAGE

    qmd, html = resolve_deck(deck_dir)
    if not html.exists():
        print(f"[✗] {html} not found -- run `quarto render` first")
        return EXIT_FAIL
    html = html.resolve()

    print(f"== beautiful-deck browser checks ({mode}): {deck_dir} ==\n")

    # Skip the browser entirely when there is nothing for it to see.
    if mode == "math" and not deck_has_math(qmd):
        print("[~] math render: deck contains no math -- nothing to verify")
        return EXIT_OK

    try:
        from playwright.sync_api import sync_playwright  # noqa: PLC0415
    except ImportError:
        print("[~] Playwright unavailable in this interpreter.")
        print("    retry with:  uv run --with playwright python "
              f"{deck_dir}/scripts/_browser_checks.py {deck_dir} {mode}")
        if mode in ("math", "all"):
            return math_via_dump_dom(html)
        print("[~] fonts, screenshots and pdf need Playwright -- skipped")
        return EXIT_NO_BROWSER

    qa_dir = deck_dir / "_qa"
    with sync_playwright() as pw:
        browser = launch(pw)
        if browser is None:
            return math_via_dump_dom(html) if mode in ("math", "all") else EXIT_NO_BROWSER
        page = browser.new_page(
            viewport={"width": CANVAS_W, "height": CANVAS_H},
            device_scale_factor=DEVICE_SCALE,
        )
        try:
            codes = []
            if mode in ("fonts", "all"):
                codes.append(run_fonts(page, html))
            if mode in ("shots", "all"):
                codes.append(run_shots(page, html, qa_dir))
            if mode in ("pdf", "all"):
                # NOT deck_dir.name: it is "" for `.` and for a deck whose contents are a
                # repository root, which produced a file literally called `_qa/.pdf`. The .qmd
                # stem is the deck's real name in every layout.
                codes.append(run_pdf(page, html, qa_dir, qmd.stem or deck_dir.resolve().name))
            if mode in ("math", "all"):
                codes.append(run_math(page, html))
        finally:
            browser.close()

    return EXIT_FAIL if EXIT_FAIL in codes else EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
