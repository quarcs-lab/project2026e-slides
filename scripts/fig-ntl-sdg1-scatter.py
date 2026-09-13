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

# The fit statistic, upper left, where the point cloud is thinnest. INK, not amber: amber is the
# sensor's colour in this deck, and a statistic drawn in it reads as a property of the sensor
# rather than of the fit. The slope used to sit above it and was removed at the author's request
# (2026-09-13); it is still computed, drawn as the line, and printed below.
ax.text(0.025, 0.965,
        f"{L.R2} = {r2:.2f}   (OLS, in-sample, n = {len(df)})",
        transform=ax.transAxes, ha="left", va="top",
        fontsize=15, linespacing=1.5, color=DECK["ink"])

out = DECKDIR / "figures/fig-ntl-sdg1-scatter.svg"
fig.savefig(out)
print(f"wrote {out.name}  (slope = {slope:.4f}, intercept = {intercept:.4f}, "
      f"r = {r:.4f}, R2 = {r2:.4f}, n = {len(df)}; x = log {BAND} {L.POPW})")

# ---- interactive twin: figures/fig-ntl-sdg1-scatter.html (what the slide shows) -------------------
# Same points, same fit, same statistic. What interactivity adds is the one thing the static
# figure deliberately withholds: WHICH municipality a point is. It is shown on hover only, so the
# slide itself still names no outlier (see the header). Drag zooms, double-click resets.
import plotly.graph_objects as go        # noqa: E402

import _interactive as I                 # noqa: E402

names = pd.read_csv(_paths.data("regionNames/regionNames.csv"))[["asdf_id", "mun", "dep"]]
hov = df.merge(names, on="asdf_id", how="left", validate="one_to_one")
assert len(hov) == N_MUNI and hov["mun"].notna().all(), "a municipality has no name"

TICKS = [0.1, 0.3, 1, 3, 10, 30, 90]
ifig = go.Figure()
ifig.add_trace(go.Scatter(
    x=hov[BAND], y=hov[GOAL], mode="markers", name="Municipality", showlegend=False,
    marker=dict(size=10, color=NTL, opacity=0.75, line=dict(color=DECK["bg_deep"], width=0.8)),
    customdata=hov[["mun", "dep"]].to_numpy(),
    hovertemplate=("<b>%{customdata[0]}</b> · %{customdata[1]}<br>"
                   "Radiance: %{x:.2f} nW/sr/cm²<br>"
                   f"{L.GOAL_LABEL[GOAL]} index: %{{y:.1f}}<extra></extra>"),
))
ifig.add_trace(go.Scatter(
    x=np.exp(grid), y=intercept + slope * grid, mode="lines", showlegend=False,
    line=dict(color=DECK["ink"], width=3), hoverinfo="skip",
))
ifig.add_annotation(
    x=0.01, y=0.99, xref="paper", yref="paper", xanchor="left", yanchor="top", showarrow=False,
    align="left", font=dict(size=17, color=DECK["ink"]),
    text=f"{L.R2} = {r2:.2f}   (OLS, in-sample, n = {len(df)})",
)
ifig.update_layout(I.layout(
    width=980, margin=dict(l=90, r=20, t=10, b=75), hovermode="closest", dragmode="zoom",
    xaxis=I.axis(type="log", tickvals=TICKS, ticktext=[f"{t:g}" for t in TICKS], fixedrange=False,
                 title=dict(text=f"{L.NTL}, {L.POPW_PROSE} mean radiance  (nW/sr/cm², log scale)",
                            font=dict(size=I.TITLE))),
    yaxis=I.axis(range=[0, 100], fixedrange=False, showgrid=True,
                 gridcolor="rgba(42,81,131,0.5)",   # DECK["hairline"] at the SVG's grid alpha
                 title=dict(text=f"{L.GOAL_LABEL[GOAL]} index, 2017", font=dict(size=I.TITLE))),
))
I.write(ifig, "fig-ntl-sdg1-scatter", script="fig-ntl-sdg1-scatter.py",
        alt=(f"Interactive scatter of {N_MUNI} Bolivian municipalities: {L.GOAL_LABEL[GOAL]} index "
             f"against log {L.POPW_PROSE} nighttime-light radiance, with a rising OLS fit line. "
             "Hover a point for its municipality and department."))
print("wrote fig-ntl-sdg1-scatter.html  (interactive)")
