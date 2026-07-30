# Daytime embeddings alone, full-bleed: AlphaEarth PC1-3 as false colour over Bolivia, 2017.
#
# NOT CURRENTLY ON A SLIDE — see the header of fig-ntl-raster.py. Kept as the single-layer escape
# hatch, drawing from the same `_rasters.draw_emb` as the three-panel figure.
#
# Reproduces figures/fig-emb-raster.png
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _paths                            # noqa: E402
_paths.bootstrap()                       # _palette lives at the DECK root, not in scripts/

import matplotlib.pyplot as plt

import _rasters as R
from _palette import apply_deck_style

apply_deck_style()

gdf, bb = R.muni_and_bbox()
fig, ax = plt.subplots(figsize=R.FIGSIZE)
evr = R.draw_emb(ax, gdf, bb)

out = R.DECKDIR / "figures/fig-emb-raster.png"
fig.savefig(out, dpi=R.DPI, bbox_inches="tight")
print(f"wrote {out.name}  (PC1-3 explained variance: {evr})")
