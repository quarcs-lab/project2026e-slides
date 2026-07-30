# Four views of the SPATIAL STRUCTURE of one goal: local indicators of spatial association,
# row-standardised QUEEN CONTIGUITY (code/spatial_weights.queen_repaired), p < 0.05, one panel
# per view. Every statistic printed below is asserted against the manuscript's own
# tables/tbl-views-comparison-<slug>.csv before the figure is written.
#
#   usage: fig-views-lisa.py [sdg1|sdg7|sdg13]      (default sdg1)
#
# All three indices score ACHIEVEMENT (higher = better), so the geometry of the legend is uniform:
#   high-high (red)  = a cluster of HIGH achievement
#   low-low  (blue)  = a cluster of LOW achievement — the trap
#   orange / light blue = spatial outliers (a place unlike its neighbours)
# The WORDING is not uniform and comes from FV.GOALS[slug]: "poverty trap" is meaningful to an
# audience and meaningless on the energy map.
#
# Prints each panel's global Moran's I and its agreement with the actual cluster map, which is
# what the slide's numbers are traced to.
#
# Reproduces figures/fig-views-lisa-<slug>.png
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _paths                            # noqa: E402
_paths.bootstrap()                       # deck root + scripts/ + the vendored sources/code
DECKDIR = _paths.DECK
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

import _fourview as FV
from _palette import DECK, apply_deck_style

apply_deck_style()

SLUG = sys.argv[1] if len(sys.argv) > 1 else FV.DEFAULT_SLUG
GOAL = FV.GOALS[SLUG]
df = FV.load(SLUG)
g = FV.geo(df)                             # NATIVE CRS — the weights must match the manuscript's
w = FV.queen_weights(g)

labels, morans = {}, {}
for col in FV.VIEW_COLS:
    labels[col], morans[col] = FV.clusters(g[col].to_numpy(), w)

# Gate BEFORE plotting: a figure that disagrees with the paper should never reach the deck.
FV.verify_against_paper(SLUG, morans, labels)

gm = FV.web_mercator(g)                    # reproject only for display

# One row of four — see the layout note in fig-views-choropleth.py.
fig, axes = plt.subplots(1, 4, figsize=(15.0, 6.0))
for ax, col in zip(axes.ravel(), FV.VIEW_COLS):
    cl = pd.Series(labels[col])
    for cat in FV.PLOT_ORDER:                       # grey first, clusters on top
        sel = gm[(cl == cat).to_numpy()]
        if len(sel):
            sel.plot(ax=ax, color=FV.CLUSTER_COLORS[cat], edgecolor="white", linewidth=0.15)
    # THREE statistics per panel, not one. This used to print only the hot/coldspot share, and on
    # the poverty slide that single number read (c) embeddings 80% against (d) combined 75% — under
    # a title asserting the combined view recovers the geography best. The figure appeared to refute
    # its own slide, because the evidence that supports the title (agreement over the FULL
    # classification, and clustering strength) was only in the speaker notes. A geospatial audience
    # reads the panel headers. Caught by the 2026-07-28 rhetoric audit.
    if col == "actual":
        sub = f"reference · I = {morans[col]:.2f}"
    else:
        agree = float((pd.Series(labels[col]) == pd.Series(labels["actual"])).mean())
        sub = (f"{agree:.0%} of all clusters · {FV.hotcold_agreement(labels, col):.0%} of hot/cold"
               f"\nMoran's I {morans[col]:.2f}  (actual {morans['actual']:.2f})")
    ax.set_title(f"{FV.PANEL_TITLES[col]}\n{sub}",
                 fontsize=12.5, color=DECK["ink"], pad=8, linespacing=1.5)
    FV.outline(gm, ax)
    ax.set_axis_off()

handles = [Patch(facecolor=FV.CLUSTER_COLORS[c], edgecolor="white", label=lab) for c, lab in [
    ("High-high", GOAL["hi_label"]),
    ("Low-low", GOAL["lo_label"]),
    ("High-low", "Outlier: high among low"),
    ("Low-high", "Outlier: low among high"),
    ("Not significant", "Not significant"),
]]
fig.legend(handles=handles, loc="lower center", ncol=5, frameon=False, fontsize=14,
           bbox_to_anchor=(0.5, -0.02))
fig.subplots_adjust(wspace=0.01, left=0.01, right=0.99, top=0.88, bottom=0.06)
out = DECKDIR / f"figures/fig-views-lisa-{SLUG}.png"
fig.savefig(out, dpi=192, bbox_inches="tight")

# Agreement with the actual cluster map: over all classes, and over hotspots/coldspots only.
actual = pd.Series(labels["actual"])
hotcold = actual.isin(["High-high", "Low-low"])
print("wrote", out.name)
print(f"  {'view':<28} {'Moran I':>8} {'all classes':>12} {'hot/coldspots':>14}")
print(f"  {'(a) Actual':<28} {morans['actual']:>8.2f} {'—':>12} {'—':>14}")
for col in FV.VIEW_TAGS:
    pred = pd.Series(labels[col])
    agree_all = float((pred == actual).mean())
    agree_hc = float((pred[hotcold] == actual[hotcold]).mean())
    print(f"  {FV.PANEL_TITLES[col]:<28} {morans[col]:>8.2f} "
          f"{agree_all:>11.0%} {agree_hc:>13.0%}")
