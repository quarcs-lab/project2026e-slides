# The study's three data layers over one Bolivia, side by side.  [slide 3]
#
# All three panels share ONE bounding box (`_rasters.muni_and_bbox`), which is the entire point:
# the comparison only means something if the frames are identical. Sequential full-bleed slides
# made the room hold each map in memory to compare it with the next; here the lights being dark
# exactly where the embeddings are richest is visible in a single glance.
#
# Municipality boundaries (the 339 units of analysis) are drawn on every panel; no region names —
# 339 labels would bury the raster, and the mesh of analysis units is the point. See
# _rasters.muni_overlay.
#
# Each panel keeps its own key. That was an explicit request, and it is the layout risk here: the
# six-class population legend and the four-line embeddings note have to stay readable at a third of
# the slide width. KEY_SCALE is the knob — verify against a rendered slide screenshot, never by
# looking at the PNG on its own, since the deck scales it to fit.
#
# Reproduces figures/fig-data-layers.png
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _paths                            # noqa: E402
_paths.bootstrap()                       # deck root + scripts/ + the vendored sources/code
DECKDIR = _paths.DECK

import matplotlib.pyplot as plt

import labels as L
import _rasters as R
from _palette import DECK, apply_deck_style

apply_deck_style()

# Three portrait maps (~0.88 w:h each) side by side give a combined aspect near 2.6:1 — the same
# shape as the deck's existing four-panel choropleth strips, so it fills the slide width instead of
# being height-capped the way a single portrait map is. The extra height over 15/2.64 = 5.7 is room
# for the panel titles.
FIGSIZE = (15.0, 6.4)
KEY_SCALE = 1.25          # keys are ~25% larger than in the standalone figures; see the note above

gdf, bb = R.muni_and_bbox()
fig, axes = plt.subplots(1, 3, figsize=FIGSIZE)

# Panel titles come from code/labels.py, not string literals — one concept, one name, repo-wide.
vmax = R.draw_ntl(axes[0], fig, gdf, bb, scale=KEY_SCALE)
evr = R.draw_emb(axes[1], gdf, bb, scale=KEY_SCALE)
inhabited = R.draw_pop(axes[2], gdf, bb, scale=KEY_SCALE)

for ax, title in zip(axes, (L.NTL, L.EMB, "Population")):
    ax.set_title(title, fontsize=17, color=DECK["ink"], pad=10)

# Tight wspace: the panels are the comparison, so gutters between them are wasted slide width.
fig.subplots_adjust(wspace=0.02, left=0.01, right=0.99, top=0.92, bottom=0.02)

out = DECKDIR / "figures/fig-data-layers.png"
fig.savefig(out, dpi=192, bbox_inches="tight")
print(f"wrote {out.name}  (lights cap {vmax:.1f} nW/sr/cm2 · PC1-3 evr {evr} · "
      f"{inhabited:.1f}% of cells inhabited)")
