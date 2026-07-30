# From pixels to municipalities: how two satellite rasters become one predictor table.
#
# A conference audience of development economists has not built a raster pipeline, and the talk
# claims numbers derived from one. This is the bridge, in four columns:
#
#   two sensors  ->  one aggregation  ->  a FORK (equal pixels vs weighted by people)  ->  the table
#
# The fork is the reason this slide exists. It is the choice slides 10-12 then show to be worth
# 0.29 -> 0.41 on the embeddings, so the room has to have seen it before the result lands.
#
# WHY NOT REUSE code/plot_workflow_diagrams.py. That module draws the manuscript's Figures 1 and 2
# and its palette is hard-coded LIGHT at module level (INK = "#1A1A1A", NEUTRAL_FILL = "#F2F2F2",
# white badge text). Parameterising it would edit a manuscript figure, which is out of scope, and
# copying it wholesale would put a twelve-step chart on a slide that needs a ten-second read. What
# IS carried over is its SHAPE GRAMMAR, so the deck and the paper read the same way:
#
#   rounded box  = an input data product
#   sharp box    = a processing step
#   dashed box   = the shared population surface
#   header-ruled box with an offset copy behind it = the output predictor table
#
# Roles are carried by shape, not by colour, so the figure survives greyscale and colour-blindness.
# Colour only says WHICH SENSOR: amber is nighttime lights, blue is daytime embeddings, everywhere
# in this deck.
#
# Reproduces figures/fig-pipeline.svg
import pathlib
import sys
import textwrap

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _paths                            # noqa: E402
_paths.bootstrap()                       # deck root + scripts/ + the vendored sources/code
DECKDIR = _paths.DECK
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

import labels as L
from _palette import DECK, EMB, NTL, apply_deck_style

apply_deck_style()

W, H = 13.5, 5.9                      # inches; the axes fill the figure, so 1 data unit = 1 inch
FS_TITLE, FS_SUB = 14.0, 11.5
PAD = 0.18                            # inner horizontal padding inside a box

fig = plt.figure(figsize=(W, H))
ax = fig.add_axes([0, 0, 1, 1])       # axes fill the canvas: data units are inches in BOTH axes
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.set_axis_off()

renderer = fig.canvas.get_renderer()


def _text_width(s: str, size: float) -> float:
    """Width of `s` in DATA units (= inches), measured with the real renderer."""
    t = ax.text(0, 0, s, fontsize=size)
    bb = t.get_window_extent(renderer=renderer)
    t.remove()
    return bb.width / fig.dpi


def _wrap(s: str, size: float, max_w: float) -> list[str]:
    """Greedy wrap to `max_w` inches, then verify. Raises rather than letting text overflow.

    A silent overflow is the failure mode this guards: an edited label that runs past its box
    still renders, still passes every static check, and is only visible to whoever is in the room.
    """
    if _text_width(s, size) <= max_w:
        return [s]
    for width in range(len(s), 4, -1):
        lines = textwrap.wrap(s, width=width)
        if lines and all(_text_width(ln, size) <= max_w for ln in lines):
            return lines
    raise ValueError(f"cannot fit {s!r} at {size}pt into {max_w:.2f}in — shorten it or widen the box")


HEADER_H = 0.58        # height of the output table's header band


def box(x, yc, w, h, title, sub=None, *, kind="step", color=None):
    """Draw one node. `kind` selects the shape grammar; see the module docstring."""
    # `hairline` scores 2.11:1 on the canvas, which is right for a 1px table rule and wrong for a
    # box whose SHAPE is the encoding: the `.source` line teaches rounded-vs-sharp-vs-dashed, and
    # at that contrast four of the seven nodes read as floating text with no shape at all — the
    # fork included. `accent_dim` is 5.0:1 and already in the palette.
    edge = color or DECK["accent_dim"]
    y0 = yc - h / 2
    if kind == "out":
        # Offset copy behind it — the paper's idiom for "a table, one row per unit".
        ax.add_patch(Rectangle((x + 0.10, y0 - 0.10), w, h, facecolor=DECK["bg_deep"],
                               edgecolor=DECK["hairline"], lw=1.0, zorder=2))
        ax.add_patch(Rectangle((x, y0), w, h, facecolor=DECK["bg_alt"],
                               edgecolor=edge, lw=1.4, zorder=3))
        ax.plot([x, x + w], [y0 + h - HEADER_H] * 2, color=edge, lw=1.1, zorder=4)
        # Title lives INSIDE the header band and the subtitle below the rule. Centring the whole
        # text block on the box, as every other kind does, drove the title straight through the
        # rule and over the first subtitle line.
        inner = w - 2 * PAD
        tlines = _wrap(title, FS_TITLE, inner)
        slines = _wrap(sub, FS_SUB, inner) if sub else []
        lh_t, lh_s = FS_TITLE * 1.24 / 72.0, FS_SUB * 1.30 / 72.0
        y = y0 + h - HEADER_H / 2 + (len(tlines) - 1) * lh_t / 2
        for ln in tlines:
            ax.text(x + w / 2, y, ln, ha="center", va="center", fontsize=FS_TITLE,
                    color=DECK["ink"], zorder=5)
            y -= lh_t
        body_mid = y0 + (h - HEADER_H) / 2
        y = body_mid + (len(slines) - 1) * lh_s / 2
        for ln in slines:
            ax.text(x + w / 2, y, ln, ha="center", va="center", fontsize=FS_SUB,
                    color=DECK["faint"], zorder=5)
            y -= lh_s
        return {"x0": x, "x1": x + w, "yc": yc, "y0": y0, "y1": y0 + h}
    elif kind == "data":
        ax.add_patch(FancyBboxPatch((x, y0), w, h, boxstyle="round,pad=0,rounding_size=0.20",
                                    facecolor=DECK["bg_alt"], edgecolor=edge, lw=1.6, zorder=3))
    elif kind == "weights":
        # Rounded AND dashed: rounded because it is an input data product like the two sensors,
        # dashed because it enters as weights rather than as a predictor.
        ax.add_patch(FancyBboxPatch((x, y0), w, h, boxstyle="round,pad=0,rounding_size=0.20",
                                    facecolor="none", edgecolor=edge, lw=1.4,
                                    ls=(0, (4, 3)), zorder=3))
    else:                                                     # "step"
        ax.add_patch(Rectangle((x, y0), w, h, facecolor=DECK["bg_alt"], edgecolor=edge,
                               lw=1.4, zorder=3))

    inner = w - 2 * PAD
    tlines = _wrap(title, FS_TITLE, inner)
    slines = _wrap(sub, FS_SUB, inner) if sub else []
    lh_t, lh_s = FS_TITLE * 1.30 / 72.0, FS_SUB * 1.28 / 72.0
    block = len(tlines) * lh_t + (0.10 + len(slines) * lh_s if slines else 0)
    y = yc + block / 2 - lh_t * 0.72
    for ln in tlines:
        ax.text(x + w / 2, y, ln, ha="center", va="center", fontsize=FS_TITLE,
                color=DECK["ink"], zorder=5)
        y -= lh_t
    if slines:
        y -= 0.10
        for ln in slines:
            ax.text(x + w / 2, y, ln, ha="center", va="center", fontsize=FS_SUB,
                    color=DECK["faint"], zorder=5)
            y -= lh_s
    return {"x0": x, "x1": x + w, "yc": yc, "y0": y0, "y1": y0 + h}


def arrow(a, b, *, dashed=False, color=None, dy=0.0):
    """Right edge of `a` to left edge of `b`. Straight when level, a soft elbow when not.

    Straight, so the arrowhead points along the flow. An earlier version used
    `angle3,angleA=0,angleB=90`, which in a left-to-right chart made every fork arrow enter the
    UNDERSIDE of its target pointing straight up, and stacked the fork arrow's head on the dashed
    population arrow's at the same corner of the figure's key node. (`angleB=0` is not the fix:
    `angle3` builds its curve from two rays, and two rays at the same angle never intersect —
    matplotlib raises.) `dy` nudges one arrival point so two arrows into the same box do not land
    on top of each other.
    """
    p0, p1 = (a["x1"], a["yc"]), (b["x0"], b["yc"] + dy)
    ax.add_patch(FancyArrowPatch(
        p0, p1, arrowstyle="-|>", mutation_scale=15, lw=1.3,
        color=color or DECK["muted"], zorder=6, shrinkA=6, shrinkB=6,
        linestyle=(0, (4, 3)) if dashed else "solid",
        connectionstyle="arc3,rad=0.0",
    ))


# ------------------------------------------------------------------ column 1: the three inputs
# The population surface sits here, with the two sensors, because that is what it is: a third
# input data product. It kept the shape grammar's DASHED outline to mark it as the weights rather
# than a predictor, and putting it in this column both fills the panel and makes the dashed route
# to the weighted branch long enough to follow.
C1_X, C1_W = 0.15, 3.10
ntl = box(C1_X, 4.90, C1_W, 1.25, L.NTL,
          "VIIRS 2017 annual composite\n8 brightness bands", kind="data", color=NTL)
emb = box(C1_X, 3.10, C1_W, 1.25, L.EMB,
          "AlphaEarth 2017 mosaic\n64 numbers per 10 m pixel", kind="data", color=EMB)
pop = box(C1_X, 1.25, C1_W, 1.05, "GHS-POP population",
          "who lives on each pixel", kind="weights", color=DECK["accent_dim"])

# ------------------------------------------------- column 2: one aggregation, both sensors alike
C2_X, C2_W = 4.15, 2.75
agg = box(C2_X, 4.00, C2_W, 1.50, "Average the pixels",
          "inside each of the 339\nmunicipal boundaries", kind="step")

# ---------------------------------------------------------------- column 3: the fork that matters
C3_X, C3_W = 7.70, 2.75
simple = box(C3_X, 4.95, C3_W, 1.10, "Every pixel equally", "the simple mean", kind="step")
weighted = box(C3_X, 2.85, C3_W, 1.25, "Weighted by the people on it",
               "population-weighted", kind="step")

# ----------------------------------------------------------------------- column 4: the output
C4_X, C4_W = 11.15, 2.25
out = box(C4_X, 3.95, C4_W, 2.05, "One row per municipality",
          "339 rows\n8 + 64 predictors\nbuilt once under\neach scheme", kind="out",
          color=DECK["muted"])

for src in (ntl, emb):
    arrow(src, agg)
for dst in (simple, weighted):
    arrow(agg, dst)
for src in (simple, weighted):
    arrow(src, out)
# Offset downward so this arrowhead does not land on the fork arrow's, which arrives at the same
# left edge of the same box.
arrow(pop, weighted, dashed=True, color=DECK["accent_dim"], dy=-0.30)

fig.savefig(DECKDIR / "figures/fig-pipeline.svg")
print("wrote fig-pipeline.svg")
