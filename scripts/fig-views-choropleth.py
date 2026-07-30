# Four views of one goal's LEVELS, 2017: actual beside three out-of-sample predictions.
#
#   usage: fig-views-choropleth.py [sdg1|sdg7|sdg13]      (default sdg1)
#
# All four panels share the five Fisher-Jenks brackets computed on the ACTUAL index, so the panels
# are directly comparable — a per-panel classification would flatter every prediction.
# All three indices score ACHIEVEMENT (higher = better), so red is always the good end.
#
# Reproduces figures/fig-views-choropleth-<slug>.png
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _paths                            # noqa: E402
_paths.bootstrap()                       # deck root + scripts/ + the vendored sources/code
DECKDIR = _paths.DECK
import matplotlib.pyplot as plt
import mapclassify as mc
import numpy as np
from matplotlib.patches import Patch

import _fourview as FV
from _palette import DECK, apply_deck_style

apply_deck_style()

SLUG = sys.argv[1] if len(sys.argv) > 1 else FV.DEFAULT_SLUG
df = FV.load(SLUG)
g = FV.web_mercator(FV.geo(df))            # display projection; no weights are built here

# One classification, computed on the actual index, applied to every panel.
K = 5
scheme = mc.FisherJenks(g["actual"].to_numpy(), k=K)
bins = list(scheme.bins)


def bracket(values):
    return mc.UserDefined(np.asarray(values), bins=bins).yb


# ONE ROW of four, not a 2x2. Bolivia is close to square, so a 2x2 grid produces a near-square
# figure; on a 16:9 slide that is height-limited and leaves the maps small with wide white
# margins. A 1x4 strip matches the slide's aspect, so the maps render about half again as large.
fig, axes = plt.subplots(1, 4, figsize=(15.0, 6.0))
for ax, col in zip(axes.ravel(), FV.VIEW_COLS):
    classes = bracket(g[col].to_numpy())
    for k in range(K):
        sel = g[classes == k]
        if len(sel):
            sel.plot(ax=ax, color=FV.BRACKET_COLORS[k], edgecolor="white", linewidth=0.15)
    # The correlation belongs in the title, not floating inside the axes: the map does not fill
    # its axes, so an anchored annotation drifts into the neighbouring panel.
    title = FV.PANEL_TITLES[col]
    if col != "actual":
        r = float(np.corrcoef(g["actual"], g[col])[0, 1])
        title += f"\nr = {r:.2f}"
    else:
        title += "\n "                       # keep every title the same height
    ax.set_title(title, fontsize=14, color=DECK["ink"], pad=8, linespacing=1.4)
    FV.outline(g, ax)
    ax.set_axis_off()

edges = [f"{b:.0f}" for b in bins]
labels = ([f"lowest – {edges[0]}"]
          + [f"{edges[i - 1]} – {edges[i]}" for i in range(1, K - 1)]
          + [f"{edges[K - 2]} – highest"])
handles = [Patch(facecolor=FV.BRACKET_COLORS[k], edgecolor="white", label=labels[k])
           for k in range(K)]
# No legend title — it adds a second row that crowds the southern tip of the maps. What the
# index means is carried by the slide's source line instead.
fig.legend(handles=handles, loc="lower center", ncol=K, frameon=False, fontsize=12.5,
           bbox_to_anchor=(0.5, -0.015))
fig.subplots_adjust(wspace=0.01, left=0.01, right=0.99, top=0.90, bottom=0.05)
out = DECKDIR / f"figures/fig-views-choropleth-{SLUG}.png"
fig.savefig(out, dpi=192, bbox_inches="tight")

rs = {c: float(np.corrcoef(g["actual"], g[c])[0, 1]) for c in FV.VIEW_TAGS}
exact = {c: float((bracket(g[c]) == bracket(g["actual"])).mean()) for c in FV.VIEW_TAGS}
within1 = {c: float((np.abs(bracket(g[c]) - bracket(g["actual"])) <= 1).mean())
           for c in FV.VIEW_TAGS}
print("wrote", out.name)
for c in FV.VIEW_TAGS:
    print(f"  {FV.PANEL_TITLES[c]:<28} r = {rs[c]:.2f}   "
          f"exact tier {exact[c]:.0%}   within one {within1[c]:.0%}")
