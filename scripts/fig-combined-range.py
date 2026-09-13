# The estimation range for the combined predictor, all fifteen goals.
# Hollow marker  = department-transfer LOWER bound (no training municipality shares a department
#                  with the test set, so the spatial-autocorrelation signal ATTENUATES — it is not
#                  severed. The queen-contiguity neighbour structure is built once over all 339
#                  municipalities, so a municipality on a departmental border still has training
#                  neighbours. index.qmd was corrected on exactly this point on 2026-07-27.)
# Filled marker  = random 5-fold spatial-interpolation UPPER bound.
# The gap between them is the reach of spatial autocorrelation, not error.
#
# Ordered by the upper bound, so this figure doubles as the ranking of goals by legibility.
# Reproduces figures/fig-combined-range.svg
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _paths                            # noqa: E402
_paths.bootstrap()                       # deck root + scripts/ + the vendored sources/code
DECKDIR = _paths.DECK
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import labels as L
import _goals as G
from _palette import DECK, EMB, apply_deck_style

apply_deck_style()

THRESHOLD = 0.60          # the paper's own gate for drawing a spatial map of a goal


def drop_aggregate(df):
    """Remove the trailing all-goals row. The two tables word it differently
    ('All 15 goals (mean)' vs 'Overall (mean of 15)'), so match on 'mean'."""
    return df[~df[L.GOAL_INDEX].str.contains("mean", case=False, na=False)].copy()


# LOWER bound — department transfer. NOTE: the 'Department range' column in this file is the
# per-department min/max WITHIN the transfer run; it is not the bounds pair and is not plotted.
lower = drop_aggregate(pd.read_csv(_paths.table("tbl-mon-comprehensive.csv")))
lower = lower.rename(columns={f"Out-of-sample {L.R2}": "lo"})[[L.GOAL_INDEX, "Goal", "lo"]]

# UPPER bound — random 5-fold, combined predictor, both views population-weighted.
upper = drop_aggregate(pd.read_csv(_paths.table("tbl-mon-featureset-comparison.csv")))
upper = upper.rename(columns={L.popw(L.COMBINED): "up"})[[L.GOAL_INDEX, "up"]]

df = lower.merge(upper, on=L.GOAL_INDEX, validate="one_to_one")
assert len(df) == 15, f"expected 15 goals after the join, got {len(df)}"
assert (df["up"] >= df["lo"] - 1e-9).all(), "an upper bound fell below its lower bound"

df = df.sort_values("up").reset_index(drop=True)           # best-read goal at the top
df["label"] = [G.tick(v) for v in df[L.GOAL_INDEX]]
y = list(range(len(df)))

fig, ax = plt.subplots(figsize=(13.5, 6.0))
for i, r in df.iterrows():
    ax.plot([r["lo"], r["up"]], [i, i], color=DECK["muted"], lw=2.0, zorder=1)
# facecolors="none": the slide's source line calls these hollow, and on a dark canvas a white fill
# would read as solid — brighter than the filled markers it is meant to contrast with.
ax.scatter(df["lo"], y, facecolors="none", edgecolors=EMB, s=105, lw=1.9, zorder=3)
ax.scatter(df["up"], y, color=EMB, s=105, zorder=3)
# The 0.60 rule is drawn in MUTED, not in the amber accent. Amber means nighttime lights everywhere
# else in this deck, and drawing a threshold in the lights colour on a chart that has no lights
# series on it makes the rule look like a series. (Same reasoning retires amber from the Spearman
# annotation in fig-legibility-clustering.py.)
ax.axvline(THRESHOLD, color=DECK["muted"], lw=1.4, ls="--", zorder=2)
ax.text(THRESHOLD + 0.012, len(df) - 0.4, f"{THRESHOLD:.2f} — mapped in space",
        color=DECK["muted"], fontsize=13, va="center")
ax.set_yticks(y)
ax.set_yticklabels(df["label"], fontsize=14)
ax.tick_params(axis="x", labelsize=14)
ax.set_xlabel(f"Out-of-sample {L.R2}  ({L.lc(L.COMBINED)} predictor)", fontsize=17)
ax.set_xlim(float(df["lo"].min()) - 0.06, max(float(df["up"].max()), THRESHOLD) + 0.14)
# Legend, UPPER LEFT. Two earlier placements failed and are worth recording, because the third is
# only obviously right once you know why:
#   lower-right  — crosses the 0.60 reference line, which spans the full height;
#   lower-left   — covers the Land and Institutions rows, whose ranges sit exactly there, and
#                  hiding data is worse than crossing a guide line;
#   no legend    — what shipped next, and it was the worst of the three. Hollow-vs-filled was left
#                  to a 0.46em caption nobody reads, so the figure's whole encoding was unexplained.
# Upper LEFT is empty by construction: goals are sorted by upper bound, so the top rows are the
# best-read goals and their markers all sit far to the right. No overlap, so no background box is
# needed. Re-check this if the sort order or the x-limits ever change.
handles = [
    Line2D([], [], marker="o", ls="", markerfacecolor="none", markeredgecolor=EMB,
           markeredgewidth=1.9, markersize=11, label="Lower bound — tested in a new region"),
    Line2D([], [], marker="o", ls="", color=EMB, markersize=10,
           label="Upper bound — tested within a region it knows"),
]
leg = ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=2,
                frameon=False, fontsize=13.5, labelcolor=DECK["ink"], handletextpad=0.8,
                columnspacing=3.0, borderaxespad=0.0)
# NO path-effect stroke on these labels, and it should stay that way. There used to be one, because
# a second reference line at x=0 ran straight through this text and a filled legend box was the
# wrong fix (the figure saves transparent onto a slide gradient that is at its LIGHTEST in this
# corner, so a canvas-coloured box reads as a dark patch). That zero line has been removed — it
# marked nothing the reader needed, since no goal's range is anywhere near it.
#
# The 0.60 line is now the only rule on the chart, and it cannot reach this legend: with
# xlim = [lo.min() - 0.06, ...] = [-0.247, 0.861], x = 0.60 sits at axes fraction 0.71 while these
# labels end near 0.30. Nothing to mask. Re-check if the x-limits change.
out = DECKDIR / "figures/fig-combined-range.svg"
fig.savefig(out)

top = df.iloc[-1]
n_over = int((df["up"] >= THRESHOLD).sum())

# ---- interactive twin: figures/fig-combined-range.html (what the slide shows) ---------------------
# Same encoding and ordering; hovering a row shows both bounds, the gap between them (the reach of
# spatial autocorrelation) and the goal's full official name. The legend sits above the plot, as in
# the SVG — and clicking an entry hides that bound.
import plotly.graph_objects as go        # noqa: E402

import _interactive as I                 # noqa: E402

seg_x, seg_y = [], []
for _, r in df.iterrows():
    seg_x += [r["lo"], r["up"], None]
    seg_y += [r["label"], r["label"], None]

S = I.fit(I.WIDTH, I.HEIGHT, I.BOX_TWO_LINE)   # designed at 1120 x 460, enlarged uniformly
ifig = go.Figure()
ifig.add_trace(go.Scatter(x=seg_x, y=seg_y, mode="lines", showlegend=False, hoverinfo="skip",
                          line=dict(color=DECK["muted"], width=2.4 * S)))
ifig.add_trace(go.Scatter(
    x=df["lo"], y=df["label"], mode="markers", name="Lower bound — tested in a new region",
    marker=dict(symbol="circle-open", size=14 * S, color=EMB, line=dict(width=2.4 * S)),
    customdata=df["Goal"],
    hovertemplate="%{customdata}<br>Lower bound: %{x:.3f}<extra></extra>",
))
ifig.add_trace(go.Scatter(
    x=df["up"], y=df["label"], mode="markers", name="Upper bound — tested within a region it knows",
    marker=dict(symbol="circle", size=14 * S, color=EMB),
    customdata=(df["up"] - df["lo"]).to_numpy(),
    hovertemplate="Upper bound: %{x:.3f}<br>Gap: %{customdata:.3f}<extra></extra>",
))
ifig.add_shape(type="line", x0=THRESHOLD, x1=THRESHOLD, y0=0, y1=1, yref="paper",
               line=dict(color=DECK["muted"], width=1.6 * S, dash="dash"))
ifig.add_annotation(x=THRESHOLD, y=1, xref="x", yref="paper", xanchor="left", yanchor="bottom",
                    xshift=6 * S, showarrow=False, text=f"{THRESHOLD:.2f} — mapped in space",
                    font=dict(size=14 * S, color=DECK["muted"]))
ifig.update_layout(I.layout(
    S, margin=dict(l=220 * S, r=20 * S, t=52 * S, b=62 * S), hovermode="y unified",
    legend=dict(orientation="h", x=0.5, y=1.06, xanchor="center", yanchor="bottom",
                font=dict(size=16 * S), itemwidth=30 * S, tracegroupgap=0),
    xaxis=I.axis(S, range=[float(df["lo"].min()) - 0.06, max(float(df["up"].max()), THRESHOLD) + 0.14],
                 title=dict(text=f"Out-of-sample {L.R2}  ({L.lc(L.COMBINED)} predictor)")),
    # tickvals pinned: left to itself plotly thins fifteen category labels to every other one.
    yaxis=I.axis(S, type="category", categoryorder="array", categoryarray=list(df["label"]),
                 tickvals=list(df["label"]), ticksuffix="  "),
))
I.write(ifig, "fig-combined-range", script="fig-combined-range.py",
        alt=(f"Interactive range chart of out-of-sample {L.R2} for 15 goals with the "
             f"{L.lc(L.COMBINED)} predictor: a hollow lower bound (tested in a new region) and a "
             f"filled upper bound (tested within a known region), with a dashed line at "
             f"{THRESHOLD:.2f}. Hover a row for both bounds."))
print("wrote fig-combined-range.html  (interactive)")
print(f"wrote {out.name}  (best: {top['Goal']} {top['lo']:.3f}–{top['up']:.3f}; "
      f"{n_over} goal(s) clear {THRESHOLD:.2f} at the upper bound)")
