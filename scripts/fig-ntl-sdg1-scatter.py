# The motivating scatter: one satellite variable, one goal index, one line through 339 points.
#
#   y = index_sdg1                     data/sdg/sdg.csv
#   x = log(average radiance)          data/nighttimeLights/bolivia_ntl_pop_weighted_2017.csv
#
# WHY THIS IS DELIBERATELY PLAIN. This slide sits immediately after the Black Marble image and
# before the embeddings are introduced; its only job is to show the room the proxy they already
# know, in the form they already read — a scatter, a fitted line, a slope and an R². Nothing is
# annotated, no municipality is named, no cluster is circled: an annotated version was built first
# and it invited questions about the labelled outliers two slides before the deck can answer them.
#
# WHY POPULATION-WEIGHTED, AND WHY LOGS. Both choices are the deck's headline scheme, not a fit to
# taste. Population weighting is what tables/tbl-popweighting-master.csv reports as the nighttime-
# lights baseline for SDG 1 (R² 0.553); the equal-pixel mean of the same band gives a much weaker
# bivariate fit (R² 0.37 in logs), because a municipality's unlit hinterland dominates its mean.
# Logs are the standard form for radiance in economics and the reason is visible in the axis: the
# variable spans 0.12 to 91 nW, three orders of magnitude, and in levels the fit is driven by a
# handful of cities (R² 0.33 vs 0.54).
#
# WHAT THIS NUMBER IS AND IS NOT. The R² printed here is an IN-SAMPLE ordinary-least-squares fit on
# one predictor, and it is labelled as such on the figure. It is NOT the 0.553 in the master table,
# which is an out-of-sample cross-validated R² from the full eight-band nighttime-lights block, and
# the two must never be quoted as the same quantity — they are close by coincidence of this goal.
# Both numbers are declared separately in numbers.toml for that reason.
#
# NOT IN THE SNAPSHOT. The municipal nighttime-lights CSV is fetched through _paths.data(), which
# falls back to Hugging Face; sources/ vendors the rasters' PCA composite and the SDG table but not
# the aggregated lights tables. So this is the second figure in the deck (after fig-ntl-raster.py)
# that needs either network access or DECK_SOURCE_ROOT. With DECK_NO_NETWORK=1 it fails loudly at
# path resolution rather than half-drawing.
#
# Reproduces figures/fig-ntl-sdg1-scatter.svg
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _paths                            # noqa: E402
_paths.bootstrap()                       # deck root + scripts/ + the vendored sources/code
DECKDIR = _paths.DECK
import matplotlib.pyplot as plt          # noqa: E402
import numpy as np                       # noqa: E402
import pandas as pd                      # noqa: E402
from matplotlib.ticker import FixedLocator, NullLocator  # noqa: E402

import labels as L                       # noqa: E402
from _palette import DECK, NTL, apply_deck_style  # noqa: E402

apply_deck_style()

GOAL = "index_sdg1"
BAND = "average"                 # VIIRS DNB Annual V2.1 mean radiance, nW/sr/cm²
N_MUNI = 339

sdg = pd.read_csv(_paths.data("sdg/sdg.csv"))[["asdf_id", GOAL]]
ntl = pd.read_csv(_paths.data("nighttimeLights/bolivia_ntl_pop_weighted_2017.csv"))
df = sdg.merge(ntl[["asdf_id", "year", BAND]], on="asdf_id", validate="one_to_one")
assert (df["year"] == 2017).all(), "the lights table carries a year other than 2017"
df = df.dropna(subset=[GOAL, BAND])
assert len(df) == N_MUNI, f"expected {N_MUNI} municipalities, got {len(df)}"
assert (df[BAND] > 0).all(), "a non-positive radiance would make the log undefined"

x = np.log(df[BAND].to_numpy())
y = df[GOAL].to_numpy()
slope, intercept = np.polyfit(x, y, 1)
r = float(np.corrcoef(x, y)[0, 1])
r2 = r ** 2

fig, ax = plt.subplots(figsize=(11.0, 5.6))

# One colour, one shape, no size encoding: the only claim is the slope. Alpha 0.7 with a thin
# darker edge keeps the dense low-radiance end readable without turning it into a solid band.
ax.scatter(df[BAND], y, s=46, color=NTL, alpha=0.7,
           edgecolor=DECK["bg_deep"], linewidth=0.6, zorder=3)

grid = np.linspace(x.min(), x.max(), 200)
ax.plot(np.exp(grid), intercept + slope * grid,
        color=DECK["ink"], lw=2.4, zorder=4, solid_capstyle="round")

ax.set_xscale("log")
# Fixed decade ticks with plain labels: matplotlib's default log formatter prints 10^0 / 10^1,
# which reads as an exponent the audience has to convert back into nanowatts mid-sentence.
ax.xaxis.set_major_locator(FixedLocator([0.1, 0.3, 1, 3, 10, 30, 90]))
ax.xaxis.set_minor_locator(NullLocator())
ax.set_xticklabels(["0.1", "0.3", "1", "3", "10", "30", "90"])
ax.set_xlabel(f"{L.NTL}, {L.POPW_PROSE} mean radiance  (nW/sr/cm², log scale)")
ax.set_ylabel(f"{L.GOAL_LABEL[GOAL]} index, 2017")
ax.set_ylim(0, 100)
ax.grid(axis="y", lw=0.8, alpha=0.5)
ax.set_axisbelow(True)

# The two statistics, upper left, where the point cloud is thinnest. INK, not amber: amber is the
# sensor's colour in this deck, and a statistic drawn in it reads as a property of the sensor
# rather than of the fit.
ax.text(0.025, 0.965,
        f"slope = {slope:.1f} index points per log nW\n"
        f"{L.R2} = {r2:.2f}   (OLS, in-sample, n = {len(df)})",
        transform=ax.transAxes, ha="left", va="top",
        fontsize=15, linespacing=1.5, color=DECK["ink"])

out = DECKDIR / "figures/fig-ntl-sdg1-scatter.svg"
fig.savefig(out)
print(f"wrote {out.name}  (slope = {slope:.4f}, intercept = {intercept:.4f}, "
      f"r = {r:.4f}, R2 = {r2:.4f}, n = {len(df)}; x = log {BAND} {L.POPW})")
