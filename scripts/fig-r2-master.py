# The legibility gradient: nighttime lights vs daytime embeddings across all fifteen goals.
# Draws ONE aggregation scheme per call so the deck can show a before/after pair:
#   fig-r2-master.py simple     -> figures/fig-r2-master-simple.svg  (raw municipal mean)
#   fig-r2-master.py weighted   -> figures/fig-r2-master.svg         (population-weighted; default)
# The two figures deliberately share one goal ordering and one x-axis (see below) so the audience
# reads them as the same fifteen goals moving from behind to ahead once the data is population-weighted.
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _paths                            # noqa: E402
_paths.bootstrap()                       # deck root + scripts/ + the vendored sources/code
DECKDIR = _paths.DECK
import pandas as pd
import matplotlib.pyplot as plt
import labels as L                       # L.NTL/L.EMB are STRINGS; _palette's NTL/EMB are COLOURS
import _goals as G
from _palette import DECK, NTL, EMB, apply_deck_style

# Which aggregation scheme this figure shows. Default is "weighted", so calling the script with no
# argument reproduces the original figures/fig-r2-master.svg unchanged (bar the shared x-axis below).
scheme = sys.argv[1] if len(sys.argv) > 1 else "weighted"
if scheme not in ("simple", "weighted"):
    raise SystemExit(f"usage: fig-r2-master.py [simple|weighted]  (got {scheme!r})")
weighting = {"simple": L.SIMPLE, "weighted": L.POPW}[scheme]
out_name = "fig-r2-master.svg" if scheme == "weighted" else "fig-r2-master-simple.svg"

apply_deck_style()
raw = pd.read_csv(_paths.table("tbl-popweighting-master.csv"))

# Keep the fifteen goals; drop the trailing aggregate row ("All 15 ... (mean)").
# Match on the "(mean)" suffix rather than the row's noun — the noun has been renamed once already.
df = raw[~raw[L.GOAL_INDEX].str.strip().str.lower().str.endswith("(mean)")].copy()
assert len(df) == 15, f"expected 15 goals, got {len(df)}"

# Header for each (view, scheme) pair — matches tbl-popweighting-master.csv verbatim (built by L.r2).
COL = {
    ("ntl", "simple"): L.r2(L.NTL, L.SIMPLE),
    ("ntl", "weighted"): L.r2(L.NTL, L.POPW),
    ("emb", "simple"): L.r2(L.EMB, L.SIMPLE),
    ("emb", "weighted"): L.r2(L.EMB, L.POPW),
}

# Both dumbbells are read as a before/after pair, so BOTH share one goal ordering and one x-axis:
#   * order is fixed by the WEIGHTED embeddings column (best-read goal on top), whichever scheme we draw;
#   * x-limits span every R² in the table (both schemes, both views).
df = df.sort_values(COL[("emb", "weighted")]).reset_index(drop=True)
ntl = df[COL[("ntl", scheme)]]
emb = df[COL[("emb", scheme)]]
all_vals = df[[COL[k] for k in COL]].to_numpy()

n_lead = int((emb.to_numpy() > ntl.to_numpy()).sum())
y = list(range(len(df)))

# Wide aspect: the theme caps images at 66vh, so a tall figure is height-bound and leaves ~40%
# of the slide width empty while shrinking the type below projection legibility.
fig, ax = plt.subplots(figsize=(13.5, 6.0))
for i in range(len(df)):
    ax.plot([ntl.iloc[i], emb.iloc[i]], [i, i], color=DECK["muted"], lw=1.6, zorder=1)
# SQUARE for the lights, CIRCLE for the embeddings — the manuscript's own marker convention, and
# the only redundant channel these two series have. In greyscale the deck's amber and blue sit 7
# points apart out of 255 (Rec.601 luminance 189 vs 182), so on a washed-out projector or in an
# audience photograph hue alone does not separate them. Both series used to be circles.
ax.scatter(ntl, y, color=NTL, s=115, marker="s", zorder=3, label=L.NTL)
ax.scatter(emb, y, color=EMB, s=110, marker="o", zorder=3, label=L.EMB)
ax.axvline(0, color=DECK["ink"], lw=0.8)
# No left spine: it draws a rule between each goal's label and its own dumbbell.
ax.spines["left"].set_visible(False)
ax.tick_params(axis="y", length=0)
ax.set_yticks(y)
ax.set_yticklabels([G.tick(v) for v in df[L.GOAL_INDEX]], fontsize=14)
# No taxonomy colour-coding: the manuscript no longer names three goal groups, so encoding them
# here would assert a structure the paper has dropped. The ordering carries the gradient on its own.
ax.set_xlabel(f"Out-of-sample {L.R2}", fontsize=17)   # the aggregation is stated in the slide's source line
ax.set_xlim(min(0.0, float(all_vals.min()) - 0.04),
            float(all_vals.max()) + 0.06)
ax.legend(loc="lower right", frameon=False, fontsize=13.5)
ax.tick_params(axis="x", labelsize=14)
out = DECKDIR / "figures" / out_name
fig.savefig(out)
print(f"wrote {out.name}  ({L.lc(L.EMB)} lead on {n_lead} of {len(df)} goals, {weighting})")

# ---- interactive twin: figures/<same stem>.html (what the slide shows) ----------------------------
# Same ordering, same shared x-axis, same square/circle convention. Hovering a row shows both R²
# and the embeddings' lead for that goal; clicking a legend entry hides that series.
import plotly.graph_objects as go        # noqa: E402

import _interactive as I                 # noqa: E402

ticks = [G.tick(v) for v in df[L.GOAL_INDEX]]
gap = (emb - ntl).to_numpy()
seg_x, seg_y = [], []
for i, t in enumerate(ticks):
    seg_x += [ntl.iloc[i], emb.iloc[i], None]
    seg_y += [t, t, None]

S = I.fit(I.WIDTH, I.HEIGHT, I.BOX_ONE_LINE)   # designed at 1120 x 460, enlarged uniformly
ifig = go.Figure()
ifig.add_trace(go.Scatter(x=seg_x, y=seg_y, mode="lines", showlegend=False, hoverinfo="skip",
                          line=dict(color=DECK["muted"], width=2 * S)))
ifig.add_trace(go.Scatter(
    x=ntl, y=ticks, mode="markers", name=L.NTL,
    marker=dict(symbol="square", size=13 * S, color=NTL),
    hovertemplate=f"{L.NTL}: %{{x:.3f}}<extra></extra>",
))
ifig.add_trace(go.Scatter(
    x=emb, y=ticks, mode="markers", name=L.EMB, customdata=gap,
    marker=dict(symbol="circle", size=14 * S, color=EMB),
    hovertemplate=(f"{L.EMB}: %{{x:.3f}}<br>"
                   "Embeddings' lead: %{customdata:+.3f}<extra></extra>"),
))
ifig.add_shape(type="line", x0=0, x1=0, y0=0, y1=1, yref="paper",
               line=dict(color=DECK["ink"], width=S))
ifig.update_layout(I.layout(
    S, margin=dict(l=210 * S, r=20 * S, t=10 * S, b=62 * S), hovermode="y unified",
    legend=dict(x=1, y=0, xanchor="right", yanchor="bottom", font=dict(size=16 * S)),
    xaxis=I.axis(S, range=[min(0.0, float(all_vals.min()) - 0.04), float(all_vals.max()) + 0.06],
                 title=dict(text=f"Out-of-sample {L.R2}"), showspikes=False),
    # tickvals pinned: left to itself plotly may thin fifteen category labels to every other one.
    yaxis=I.axis(S, type="category", categoryorder="array", categoryarray=ticks, tickvals=ticks,
                 showline=False, ticks="", ticksuffix="  "),
))
I.write(ifig, out.stem, script="fig-r2-master.py",
        alt=(f"Interactive dumbbell chart of out-of-sample {L.R2} for 15 goals, {weighting} "
             f"aggregation: {L.lc(L.NTL)} (squares) against {L.lc(L.EMB)} (circles). "
             f"{L.EMB} lead on {n_lead} of 15. Hover a row for both values."))
print(f"wrote {out.stem}.html  (interactive)")
