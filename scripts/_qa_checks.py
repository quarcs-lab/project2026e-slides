#!/usr/bin/env python3
"""Static visual-QA checks for a beautiful-deck reveal.js deck (Tier B of references/visual-qa.md).

The `beautiful-deck` skill copies this file into each deck as `slides/<deck>/scripts/_qa_checks.py`.
It needs no browser. It performs four deterministic checks against the deck's single source of
colour truth (`theme.scss`) and its rendered assets:

  1. WCAG-AA contrast of every palette colour against the slide background (flag < 4.5:1).
  2. Figure-vs-slide pixel fit (flag figures too small for projection or wider than the canvas).
  3. Per-slide content-length overflow heuristic (the static stand-in for "content fits").
  4. Figure palette-drift (flag salient figure colours that are not in theme.scss).

Usage:
    uv run python slides/<deck>/scripts/_qa_checks.py slides/<deck>

Exit code is always 0 (diagnostic); failures are printed and summarised on the final line so the
calling agent can parse them.
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

# ---- tunables ----------------------------------------------------------------
CANVAS_W, CANVAS_H = 1280, 720          # logical reveal.js canvas (theme-design.md)
MIN_FIG_PX = 600                         # a projection figure under this min-dim reads soft
CONTRAST_NORMAL = 4.5                    # WCAG-AA normal text
CONTRAST_LARGE = 3.0                     # WCAG-AA large/bold text
MAX_BULLETS = 7
MAX_BODY_CHARS = 480
MAX_CODE_LINES = 18
DRIFT_RGB_TOL = 60.0                     # Euclidean RGB distance counted as "same colour"
NEUTRAL_CHROMA = 22                      # max-min channel below this == grey (gridline/text) → ignore


# ---- colour helpers ----------------------------------------------------------
def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _lin(c: float) -> float:
    c /= 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = (_lin(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> float:
    l1, l2 = luminance(fg), luminance(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def rgb_dist(a, b) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def is_neutral(rgb) -> bool:
    return (max(rgb) - min(rgb)) < NEUTRAL_CHROMA


# ---- theme.scss palette ------------------------------------------------------
def parse_palette(theme_scss: Path) -> dict[str, str]:
    """Return {sass_var_name: '#rrggbb'} for every `$name: #hex;` in theme.scss."""
    if not theme_scss.exists():
        return {}
    text = theme_scss.read_text(encoding="utf-8")
    pal: dict[str, str] = {}
    for name, hx in re.findall(r"\$([\w-]+)\s*:\s*(#[0-9A-Fa-f]{3,6})\s*;", text):
        pal[name] = hx.lower()
    return pal


def pick_background(pal: dict[str, str]) -> str:
    for key in ("body-bg", "bg"):
        if key in pal:
            return pal[key]
    return "#ffffff"


# ---- checks ------------------------------------------------------------------
# Sass vars that name a *background/surface* (not foreground text) → skip the vs-bg contrast check.
#
# This was once an exact-match set — {"body-bg", "bg", "bg-alt", ...} — which is the wrong shape for
# the job and has now failed twice for the same reason: it enumerates the backgrounds that happened
# to exist when it was written, so any preset introducing a new one gets it silently graded as
# foreground text against the canvas. The divider bug (see `divider_colors` below) was the first
# instance. The second: a dark preset with a depth ramp declares `$bg-deep`, `$bg-lift` and
# `$surface`, none of which are in the set, and all three "fail" at 1.2-1.6:1 — precisely because
# they are doing their job, since a surface is *supposed* to sit close to the canvas.
#
# So match on the NAME instead of on a list. The convention this enforces is worth having: give a
# background variable a background word in its name. A foreground colour that opts into one of these
# words (`$fill-text`) escapes the check, which is the accepted cost of not maintaining a list.
BG_NAME_PARTS = ("bg", "surface", "divider", "hairline", "fill", "canvas", "shade")
# Names that are backgrounds/borders but carry none of the words above.
BG_VARS_EXTRA = {"code-block-border-color", "selection-bg"}


def is_background_var(name: str) -> bool:
    """True if this Sass var names a background/surface rather than foreground text.

    `dark-bg-*` is the deliberate exception: those contain "bg" but are the TEXT colours used on a
    dark slide, and they are graded separately against every declared divider fill.
    """
    if name.startswith("dark-bg-"):
        return False
    return name in BG_VARS_EXTRA or any(part in name for part in BG_NAME_PARTS)


def divider_colors(theme_scss: Path, qmd: Path, pal: dict[str, str] | None = None) -> dict[str, str]:
    """Colours actually used as full-bleed slide backgrounds.

    Read from three places a deck can set one:
      * a Sass variable whose name contains "divider" (`$divider-dark: #05101F;`)
      * a `--divider` custom property, whether a literal hex OR a Sass interpolation
        (`--divider: #{$divider-dark};`) — the presets use the interpolated form
      * any `background-color="#hex"` attribute on a slide in the .qmd

    This replaces an earlier heuristic that assumed `$accent`/`$accent-2`/`$ink` might be divider
    fills. That held for a light deck, where the accent is dark enough to be a plausible background,
    but on a dark deck those are light foreground colours that are never used as backgrounds — so
    the heuristic reported unreadable dividers that do not exist, while never checking the colour
    the deck actually uses.

    Resolving the interpolated form matters and is not hypothetical: the shipped presets write
    `--divider: #{$divider-dark}`, so a literal-hex-only regex finds nothing and silently checks no
    divider at all. The regression suite pins this.
    """
    pal = pal or {}
    found: dict[str, str] = {}

    # 1. Sass variables named like a divider.
    for name, hx in pal.items():
        if "divider" in name:
            found[f"${name}"] = hx.lower()

    if theme_scss.exists():
        text = theme_scss.read_text(encoding="utf-8")
        # 2a. custom property holding a literal hex
        for m in re.finditer(r"--([\w-]*divider[\w-]*)\s*:\s*(#[0-9A-Fa-f]{3,8})", text):
            found[f"--{m.group(1)}"] = m.group(2).lower()
        # 2b. custom property interpolating a Sass variable
        for m in re.finditer(r"--([\w-]*divider[\w-]*)\s*:\s*#\{\s*\$([\w-]+)\s*\}", text):
            hx = pal.get(m.group(2))
            if hx:
                found[f"--{m.group(1)}"] = hx.lower()

    # 3. per-slide backgrounds declared in the deck itself
    if qmd.exists():
        for hx in re.findall(r'background-color="(#[0-9A-Fa-f]{3,8})"', qmd.read_text(encoding="utf-8")):
            found.setdefault(f"slide bg {hx.lower()}", hx.lower())
    return found


def check_contrast(pal: dict[str, str], theme_scss: Path | None = None,
                   qmd: Path | None = None) -> list[str]:
    out: list[str] = []
    bg_hex = pick_background(pal)
    bg = hex_to_rgb(bg_hex)
    dark_text = hex_to_rgb(pal.get("dark-bg-text-color", "#ffffff"))
    for name, hx in pal.items():
        # Skip backgrounds/surfaces and the dark-slide colours (those are checked below, vs darks).
        # `*divider*` and `*surface*` vars are slide BACKGROUNDS. Grading them as foreground text
        # here is meaningless and, on a dark deck, actively wrong: a surface is deliberately close to
        # the canvas, so it "fails" a test it was never subject to. (Light presets hid this — a dark
        # surface on a white canvas passes by luck.) See `is_background_var` for why this is a name
        # rule and not a list.
        if is_background_var(name) or name.startswith("dark-bg-"):
            continue
        ratio = contrast(hex_to_rgb(hx), bg)
        verdict = "ok" if ratio >= CONTRAST_NORMAL else (
            "large-only" if ratio >= CONTRAST_LARGE else "FAIL"
        )
        flag = "" if verdict == "ok" else f"  <-- {verdict}"
        out.append(f"  ${name:<24} {hx} on {bg_hex}: {ratio:4.1f}:1  ({verdict}){flag}")
    # Section dividers: the dark-slide text colour must read on every colour the deck actually uses
    # as a full-bleed background.
    dividers = divider_colors(theme_scss, qmd, pal) if theme_scss and qmd else {}
    for name, hx in dividers.items():
        r = contrast(dark_text, hex_to_rgb(hx))
        verdict = "ok" if r >= CONTRAST_NORMAL else ("large-only" if r >= CONTRAST_LARGE else "FAIL")
        flag = "" if verdict == "ok" else f"  <-- {verdict} (divider unreadable)"
        out.append(f"  divider text on {name:<18} {hx}: {r:4.1f}:1  ({verdict}){flag}")
    if not dividers:
        out.append("  (no divider background declared — skipped the divider legibility check)")
    return out


def figure_report(fig_dir: Path, pal: dict[str, str]) -> tuple[list[str], list[str]]:
    fit: list[str] = []
    drift: list[str] = []
    pal_rgb = [hex_to_rgb(h) for n, h in pal.items() if n not in ("body-bg", "bg")]
    bg = hex_to_rgb(pick_background(pal))
    if not fig_dir.exists():
        return ["  (no figures/ folder yet)"], []
    figs = sorted([*fig_dir.glob("*.png"), *fig_dir.glob("*.svg")])
    if not figs:
        return ["  (no figures generated yet)"], []
    try:
        from PIL import Image  # noqa: PLC0415
    except Exception:
        Image = None  # type: ignore[assignment]

    for f in figs:
        salient: list[tuple[int, int, int]] = []
        if f.suffix == ".png" and Image is not None:
            img = Image.open(f).convert("RGB")
            w, h = img.size
            if min(w, h) < MIN_FIG_PX:
                fit.append(f"  {f.name}: {w}x{h}px  <-- low-res for projection (min < {MIN_FIG_PX})")
            elif w > CANVAS_W * 2:
                fit.append(f"  {f.name}: {w}x{h}px  (ok; will be scaled to fit)")
            else:
                fit.append(f"  {f.name}: {w}x{h}px  (ok)")
            small = img.resize((80, 80))
            for cnt, rgb in sorted(small.getcolors(8000) or [], reverse=True)[:12]:
                if not is_neutral(rgb) and rgb_dist(rgb, bg) > 40:
                    salient.append(rgb)
        elif f.suffix == ".svg":
            text = f.read_text(encoding="utf-8", errors="ignore")
            fit.append(f"  {f.name}: vector SVG (scales cleanly)")
            for hx in re.findall(r"#[0-9A-Fa-f]{6}", text):
                rgb = hex_to_rgb(hx)
                if not is_neutral(rgb) and rgb_dist(rgb, bg) > 40:
                    salient.append(rgb)
        else:
            fit.append(f"  {f.name}: (PNG but Pillow unavailable — skipped pixel check)")
            continue
        # palette-drift: every salient colour should be near a palette hex
        for rgb in {tuple(s) for s in salient}:
            nearest = min(rgb_dist(rgb, p) for p in pal_rgb) if pal_rgb else 999
            if nearest > DRIFT_RGB_TOL:
                drift.append(f"  {f.name}: rgb{rgb} not in palette (nearest {nearest:.0f} > {DRIFT_RGB_TOL})")
    return fit, drift


# `fig-alt` is read by screen readers and never projected, so counting it toward a slide's on-slide
# character budget is the same false positive this function already avoids for speaker notes and
# HTML comments — and it penalises a well-described figure hardest, which is exactly backwards. A
# three-panel map needs a long alt text; that alt text alone can exceed MAX_BODY_CHARS and flag a
# slide carrying one image and one caption line. `fig-align` goes too: also not text on the slide.
_ATTR_NOT_PROJECTED = re.compile(r'\bfig-(?:alt|align)\s*=\s*"[^"]*"')


def _projected(ln: str) -> str:
    """The part of a source line that actually reaches the screen."""
    return _ATTR_NOT_PROJECTED.sub("", ln)


def check_overflow(qmd: Path) -> list[str]:
    out: list[str] = []
    if not qmd.exists():
        return []
    lines = qmd.read_text(encoding="utf-8").splitlines()
    title, body, bullets, code_lines, in_code = None, 0, 0, 0, False
    in_yaml = False
    in_notes = False      # speaker notes are NOT projected — see the note below
    in_comment = False
    has_columns = False   # a `.columns` slide splits content across two columns → looser char budget

    def flush():
        if title is None:
            return
        problems = []
        if bullets > MAX_BULLETS:
            problems.append(f"{bullets} bullets > {MAX_BULLETS}")
        body_limit = MAX_BODY_CHARS * 2 if has_columns else MAX_BODY_CHARS
        if body > body_limit:
            problems.append(f"{body} body chars > {body_limit}")
        if code_lines > MAX_CODE_LINES:
            problems.append(f"{code_lines}-line code block > {MAX_CODE_LINES}")
        if problems:
            out.append(f"  slide '{title[:50]}': overflow-risk ({'; '.join(problems)})")

    for ln in lines:
        if ln.strip() == "---":
            in_yaml = not in_yaml
            continue
        if in_yaml:
            continue
        # Speaker notes and HTML comments never reach the screen, so counting them toward a
        # slide's on-slide budget produces false "overflow-risk" flags on slides that fit
        # comfortably — and a well-annotated deck is penalised hardest. Skip both.
        stripped = ln.strip()
        if in_notes:
            if stripped == ":::":
                in_notes = False
            continue
        if stripped.startswith("::: {.notes}") or stripped.startswith(":::{.notes}"):
            in_notes = True
            continue
        if in_comment:
            if "-->" in ln:
                in_comment = False
            continue
        if stripped.startswith("<!--"):
            if "-->" not in ln:
                in_comment = True
            continue
        if ln.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            code_lines += 1
            continue
        if ln.startswith("## "):
            flush()
            title, body, bullets, code_lines = ln[3:].strip(), 0, 0, 0
            has_columns = False
        elif ln.startswith("# "):
            flush()
            title = None  # section divider — exempt
        elif title is not None:
            body += len(_projected(ln))
            if ".columns" in ln:
                has_columns = True
            if re.match(r"\s*[-*] ", ln):
                bullets += 1
    flush()
    return out


# ---- main --------------------------------------------------------------------
def main() -> int:
    # A USAGE error exits 2, not 0. This tier is deliberately diagnostic — it reports findings
    # and exits 0 even when it finds them — but that made a mistyped path indistinguishable from
    # a clean run, so a broken invocation inside a CI loop read as a pass. The findings stay
    # advisory; being unable to look at the deck at all does not.
    if len(sys.argv) < 2:
        print("usage: _qa_checks.py slides/<deck>")
        return 2
    deck_dir = Path(sys.argv[1])
    if not deck_dir.is_dir():
        print(f"[✗] not a directory: {deck_dir}")
        return 2
    theme = deck_dir / "theme.scss"
    pal = parse_palette(theme)
    qmd = deck_dir / f"{deck_dir.name}.qmd"
    if not qmd.exists():
        qmds = sorted(deck_dir.glob("*.qmd"))
        qmd = qmds[0] if qmds else qmd

    print(f"== beautiful-deck static QA: {deck_dir} ==\n")
    print("[1] WCAG contrast (palette vs slide background)")
    contrast_lines = check_contrast(pal, theme, qmd) if pal else ["  (no theme.scss palette parsed)"]
    print("\n".join(contrast_lines))

    print("\n[2/4] Figures — pixel fit and palette drift")
    fit_lines, drift_lines = figure_report(deck_dir / "figures", pal)
    print("\n".join(fit_lines))
    print("  -- palette drift --")
    print("\n".join(drift_lines) if drift_lines else "  (no drift detected)")

    print("\n[3] Per-slide content overflow heuristic")
    overflow_problems = check_overflow(qmd)
    print("\n".join(overflow_problems) if overflow_problems else "  (no overflow-risk slides)")

    n_contrast = sum("FAIL" in ln for ln in contrast_lines)
    n_drift = len(drift_lines)
    n_overflow = len(overflow_problems)
    print(
        f"\nQA SUMMARY: {n_contrast} contrast failure(s), {n_drift} palette-drift, "
        f"{n_overflow} overflow-risk slide(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
