# Nighttime lights alone, full-bleed: VIIRS annual mean radiance over Bolivia, 2017.
#
# NOT CURRENTLY ON A SLIDE. The deck introduces all three data layers on one three-panel slide
# (scripts/fig-data-layers.py). This script is kept as the escape hatch for a venue that wants a
# single layer to fill the frame — it draws from the same `_rasters.draw_ntl`, so it cannot drift
# from the panel version. Pair it with `{.portrait-figure}` on the slide; see theme.scss.
#
# Reproduces figures/fig-ntl-raster.png
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
vmax = R.draw_ntl(ax, fig, gdf, bb)

out = R.DECKDIR / "figures/fig-ntl-raster.png"
fig.savefig(out, dpi=R.DPI, bbox_inches="tight")
print(f"wrote {out.name}  (floor {R.NTL_FLOOR}, cap {vmax:.1f} nW/sr/cm2, gamma 0.45)")
