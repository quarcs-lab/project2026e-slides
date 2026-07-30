"""Nightlight palette, DARK — single source of truth for figure colour.

Mirrors `theme.scss` exactly. If you change one, change the other, then re-run
`scripts/_qa_checks.py`, which parses `theme.scss` and will fail if a foreground colour stops
clearing 4.5:1 against the canvas or a figure ships a colour that is not in the palette.

Every ratio below is measured against `DECK["bg"]` (#0A1C36).
"""
from pathlib import Path

DECK = {
    "accent": "#8FC0EC",     # sky blue,  8.9:1 — daytime embeddings
    "accent2": "#F5B455",    # amber,     9.4:1 — nighttime lights
    "accent_dim": "#5A8FC4", # ornament,  5.0:1 — rules, inactive markers
    "ink": "#EEF3F9",        # body text, 15.3:1
    "muted": "#A9BDD4",      # secondary, 8.9:1
    "faint": "#8199B4",      # captions,  5.8:1
    "bg": "#0A1C36",         # night-sky canvas
    "bg_deep": "#06101F",    # divider / vignette floor
    "bg_alt": "#13304F",     # panel surface
    "hairline": "#2A5183",   # 1px borders, grid lines
    "alert": "#F58A73", "success": "#6FD69B",
    "tertiary1": "#63D2E0", "tertiary2": "#DCC77A",
}

# Map ramp for the LISA cluster maps and the choropleth brackets. Mirrors the `$cluster-*` /
# `$bracket-mid` / `$map-outline` block in theme.scss — declared in BOTH so the palette-drift check
# has something to compare the rendered figures against. `_fourview.py` reads these; do not
# hardcode a map colour there.
MAP = {
    "high_high": "#E05A4E",   # low-poverty cluster ... 4.7:1
    "low_low": "#6FA8DC",     # poverty trap .......... 6.7:1
    "high_low": "#EFB16E",    # outlier ............... 9.1:1
    "low_high": "#8FC4DC",    # outlier ............... 9.0:1
    "bracket_mid": "#9AA6B5", # middle choropleth class 6.9:1
    "outline": "#8899AD",     # national boundary ..... 5.9:1
    # Recessive BY DESIGN — low contrast is the goal, so it is exempt from the text gate by name.
    "null_fill": "#33415A",   # not significant ....... 1.7:1
}
# Intuitive figure convention, unchanged: lights = amber, embeddings = blue.
NTL = DECK["accent2"]
EMB = DECK["accent"]
PALETTE = [DECK["accent"], DECK["accent2"], DECK["success"], DECK["tertiary1"],
           DECK["tertiary2"], DECK["alert"]]

import os

import matplotlib as mpl
import seaborn as sns
from matplotlib import font_manager as fm

_FONT_DIR = Path(__file__).resolve().parent / "fonts"


def _register_fonts() -> str:
    """Register the deck's bundled webfonts with matplotlib so figures match the slides.

    Returns the family to use, falling back to matplotlib's default if the files are missing —
    a figure in the wrong font is a blemish, a crashed build is a blocker.

    KNOWN LIMIT: matplotlib renders only a variable font's DEFAULT INSTANCE, so every weight
    resolves to Regular. Figure hierarchy therefore has to come from SIZE, not weight; asking for
    bold here silently returns the same glyphs. (Static Inter instances are available from the
    rsms/inter v4.1 release if that ever stops being good enough.)
    """
    ok = False
    for f in ("Inter-Variable.ttf", "SourceSerif4-Variable.ttf"):
        p = _FONT_DIR / f
        if p.exists():
            fm.fontManager.addfont(str(p))
            ok = ok or f.startswith("Inter")
    return "Inter" if ok else "sans-serif"


def apply_deck_style():
    family = _register_fonts()
    # REPRODUCIBLE SVG. Two things in matplotlib's SVG writer are nondeterministic by default,
    # and both are pure noise in a git diff: an embedded <dc:date>, and the random salt behind
    # every clip-path / marker / hatch id. Regenerating an unchanged figure therefore produced a
    # ~54-line diff with no real change in it — which is exactly how a real change gets missed.
    # A fixed hashsalt and a fixed SOURCE_DATE_EPOCH make regeneration byte-for-byte, so
    # `git status` after rebuilding a figure is either empty or meaningful.
    #
    # SOURCE_DATE_EPOCH is the reproducible-builds convention matplotlib already honours; the
    # value is arbitrary and fixed (2017-01-01, the deck's data year). Only set if the caller
    # has not chosen one.
    os.environ.setdefault("SOURCE_DATE_EPOCH", "1483228800")
    sns.set_theme(style="white", context="talk")          # 'talk' = larger fonts for projection
    mpl.rcParams.update({
        "svg.hashsalt": "monitoring-local-development",
        # TRANSPARENT, not the canvas colour. The slide background is a gradient; an opaque
        # facecolor matching $bg would ship as a visible flat rectangle sitting on top of it.
        # Transparent also means the figure stays correct if the canvas is ever retuned.
        "figure.facecolor": "none", "axes.facecolor": "none",
        "savefig.facecolor": "none", "savefig.edgecolor": "none",
        "savefig.transparent": True,
        "font.family": family,
        "axes.edgecolor": DECK["hairline"], "axes.labelcolor": DECK["ink"],
        "text.color": DECK["ink"], "xtick.color": DECK["ink"], "ytick.color": DECK["ink"],
        "grid.color": DECK["hairline"],
        "axes.prop_cycle": mpl.cycler(color=PALETTE),
        "axes.spines.top": False, "axes.spines.right": False,
        "font.size": 16, "axes.titlesize": 19, "axes.labelsize": 16,
        "xtick.labelsize": 13, "ytick.labelsize": 13, "legend.fontsize": 13,
        "figure.dpi": 100, "savefig.dpi": 192, "savefig.bbox": "tight",
    })
