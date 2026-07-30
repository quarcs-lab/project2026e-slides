# Legibility has a spatial signature: the goals that cluster most in space are the goals the
# daytime embeddings read best. Fifteen goals, ranked twice.
#
#   left  = rank by global Moran's I of the ACTUAL index    tables/tbl-outcomes-descriptives.csv
#   right = rank by out-of-sample R², population-weighted   tables/tbl-popweighting-master.csv
#           daytime embeddings, spatial-interpolation
#           upper bound
#
# WHY A SLOPEGRAPH AND NOT A SCATTER. The paper's claim is explicitly about ORDER — "ranking the
# fifteen goals by spatial dependence and by predictive accuracy yields broadly the same order
# (Spearman rho = 0.67)" (index.qmd:386). A slopegraph draws exactly that: a flat line is a goal
# whose two ranks agree, a crossing is a goal where they do not. A scatter was built first and
# rejected — fifteen floating labels collided, and leader lines pointing across the panel made it
# ambiguous which point each name belonged to. It also invited a fitted line, which would assert a
# linear relationship Spearman does not test.
#
# The paper's own hedge belongs on the slide, not here: with fifteen goals this is an observation,
# not a result, and clustering and legibility are plausibly two consequences of how an index is
# built rather than one causing the other (index.qmd:388).
#
# Reproduces figures/fig-legibility-clustering.svg
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _paths                            # noqa: E402
_paths.bootstrap()                       # deck root + scripts/ + the vendored sources/code
DECKDIR = _paths.DECK
import matplotlib.pyplot as plt
import pandas as pd
from scipy.stats import spearmanr

import _goals as G
import labels as L
from _palette import DECK, EMB, apply_deck_style

apply_deck_style()

MORAN = "Moran's I"
PUBLISHED_RHO = 0.67          # index.qmd:386
# The three goals Act II goes on to map. Drawn in the accent so this slide visibly hands over to
# the monitoring section: these are the lines the audience should still be able to find.
MAPPED = {1, 7, 13}

desc = pd.read_csv(_paths.table("tbl-outcomes-descriptives.csv"))
pw = pd.read_csv(_paths.table("tbl-popweighting-master.csv"))

# Drop the trailing all-goals row. Match on the "(mean)" suffix, not the row's noun — the noun has
# been renamed once already (see fig-r2-master.py).
pw = pw[~pw[L.GOAL_INDEX].str.strip().str.lower().str.endswith("(mean)")]

df = desc.merge(pw, on=L.GOAL_INDEX, validate="one_to_one")
assert len(df) == 15, f"expected 15 goals after the join, got {len(df)}"

R2_COL = L.r2(L.EMB, L.POPW)
df["moran"] = df[MORAN].astype(float)
df["r2"] = df[R2_COL].astype(float)

rho, pval = spearmanr(df["moran"], df["r2"])
assert round(float(rho), 2) == PUBLISHED_RHO, (
    f"Spearman rho is {rho:.4f}, which does not round to the published {PUBLISHED_RHO}. "
    "Either a source table moved or this figure is reading the wrong R² column. "
    "index.qmd:386 is the reference; do not adjust the constant to match the code."
)

n = len(df)
# Most clustered / best read at the TOP, matching fig-r2-master.svg and fig-combined-range.svg —
# the audience meets the same fifteen goals in the same orientation three slides running. Plot y
# increases upward, so the rank in ascending order IS the y position.
df["y_left"] = df["moran"].rank(ascending=True, method="first")
df["y_right"] = df["r2"].rank(ascending=True, method="first")
df["num"] = [G.number(v) for v in df[L.GOAL_INDEX]]
df["name"] = [G.tick(v) for v in df[L.GOAL_INDEX]]

X0, X1 = 0.0, 1.0
fig, ax = plt.subplots(figsize=(12.6, 5.9))

for _, r in df.iterrows():
    mapped = r["num"] in MAPPED
    # The twelve unhighlighted slopes ARE the rho = 0.67 argument, so they cannot be a haze. At
    # alpha 0.55 and lw 1.2 they blended to about 2.5:1 while their own end markers were drawn at
    # full opacity — the dots were more visible than the lines connecting them.
    alpha = 1.0 if mapped else 0.8
    ax.plot([X0, X1], [r["y_left"], r["y_right"]],
            color=EMB if mapped else DECK["accent_dim"],
            lw=2.4 if mapped else 1.6, alpha=alpha,
            zorder=3 if mapped else 2, solid_capstyle="round")
    for xx, yy in ((X0, r["y_left"]), (X1, r["y_right"])):
        ax.plot([xx], [yy], marker="o", ms=8 if mapped else 6, alpha=alpha,
                color=EMB if mapped else DECK["accent_dim"],
                zorder=4 if mapped else 2)

    ink = DECK["ink"] if mapped else DECK["muted"]
    size = 13.5 if mapped else 12.5
    ax.text(X0 - 0.035, r["y_left"], f"{r['name']}   {r['moran']:.2f}",
            ha="right", va="center", color=ink, fontsize=size, zorder=5)
    ax.text(X1 + 0.035, r["y_right"], f"{r['r2']:.2f}   {r['name']}",
            ha="left", va="center", color=ink, fontsize=size, zorder=5)

# Column headers, in DATA coordinates. Do not reach for `ax.get_xaxis_transform()` here: it is
# (x data, y axes-fraction), so a y of n + 0.75 lands fifteen axes-heights above the plot, and with
# `savefig.bbox = "tight"` the saved canvas grows to contain it — the first version of this figure
# came out 1500 x 12476 px for exactly that reason.
head = dict(va="bottom", fontsize=15, color=DECK["ink"])
ax.text(X0 - 0.035, n + 1.20, "Spatial clustering", ha="right", **head)
ax.text(X1 + 0.035, n + 1.20, "Legibility", ha="left", **head)
sub = dict(va="bottom", fontsize=12.5, color=DECK["faint"])
ax.text(X0 - 0.035, n + 0.62, f"global {MORAN}", ha="right", **sub)
# Name the VIEW. Two slides later the same three goals reappear at 0.72/0.64/0.64 from the combined
# predictor; without this the room has no way to know these are the embeddings alone.
ax.text(X1 + 0.035, n + 0.62, f"out-of-sample {L.R2} · {L.lc(L.EMB)}", ha="left", **sub)

# INK, not the amber accent: amber means nighttime lights throughout this deck, and this chart's
# right-hand column is the daytime embeddings. A statistic annotated in a sensor's colour reads as
# belonging to that sensor.
ax.text(0.5, n + 1.20, f"Spearman $\\rho$ = {rho:.2f}",
        ha="center", va="bottom", fontsize=16, color=DECK["ink"])

# Room for the label columns, which are wider than the plotting area itself.
ax.set_xlim(X0 - 0.92, X1 + 0.92)
ax.set_ylim(0.3, n + 1.9)
ax.set_axis_off()

out = DECKDIR / "figures/fig-legibility-clustering.svg"
fig.savefig(out)
shift = (df["y_left"] - df["y_right"]).abs()
worst = df.loc[shift.idxmax()]
print(f"wrote {out.name}  (rho = {rho:.4f}, p = {pval:.4f}; mean rank shift {shift.mean():.1f}, "
      f"largest {int(shift.max())} at {worst['name']}; y = {R2_COL})")
