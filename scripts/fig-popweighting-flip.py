# The population-weighting flip: the embeddings' lead over nighttime lights, before and after
# weighting each pixel by resident population. Goals above zero are goals the embeddings win.
# The count above zero moves 8 of 15 -> 14 of 15, which is the slide's headline.
#
# Plotting the GAP (embeddings - lights) rather than two separate scoreboards is what makes the
# flip legible: the zero line is the scoreboard, and the arrow shows each goal crossing it.
#
# Reproduces figures/fig-popweighting-flip.svg
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
from _palette import DECK, NTL, EMB, apply_deck_style

apply_deck_style()
raw = pd.read_csv(_paths.table("tbl-popweighting-master.csv"))
df = raw[~raw[L.GOAL_INDEX].str.strip().str.lower().str.endswith("(mean)")].copy()
assert len(df) == 15, f"expected 15 goals, got {len(df)}"

# The embeddings' margin over the lights, under each aggregation.
df["gap_simple"] = df[L.r2(L.EMB, L.SIMPLE)] - df[L.r2(L.NTL, L.SIMPLE)]
df["gap_popw"] = df[L.r2(L.EMB, L.POPW)] - df[L.r2(L.NTL, L.POPW)]
n_simple = int((df["gap_simple"] > 0).sum())
n_popw = int((df["gap_popw"] > 0).sum())

df = df.sort_values("gap_popw").reset_index(drop=True)
y = list(range(len(df)))

fig, ax = plt.subplots(figsize=(13.5, 6.0))
ax.axvspan(0, 1.0, color=DECK["bg_alt"], zorder=0)          # the half where embeddings lead
for i, r in df.iterrows():
    # The movement is the finding, so the arrows dominate: amber, heavy, large heads, drawn
    # above the shading and the markers rather than as a faint connector between them.
    ax.annotate("", xy=(r["gap_popw"], i), xytext=(r["gap_simple"], i),
                arrowprops=dict(arrowstyle="-|>,head_width=0.42,head_length=0.85",
                                color=NTL, lw=3.4, shrinkA=0, shrinkB=0),
                zorder=4)
# facecolors="none", not "white": the caption calls these markers hollow, and a white disc on a
# dark canvas reads as the most solid thing in the figure — the opposite of the intended encoding.
# Unfilled also lets the slide's background gradient show through.
ax.scatter(df["gap_simple"], y, facecolors="none", edgecolors=EMB, s=95, lw=1.8,
           zorder=5, label=f"{L.SIMPLE.capitalize()} average")
ax.scatter(df["gap_popw"], y, color=EMB, s=95, zorder=5,
           label=L.POPW_PROSE.capitalize())
ax.axvline(0, color=DECK["ink"], lw=1.2)
ax.set_yticks(y)
ax.set_yticklabels([G.tick(v) for v in df[L.GOAL_INDEX]], fontsize=14)
ax.set_xlabel(f"{L.EMB} margin over {L.lc(L.NTL)}   ({L.DR2}, out of sample)", fontsize=17)
lo = float(df[["gap_simple", "gap_popw"]].to_numpy().min()) - 0.05
hi = float(df[["gap_simple", "gap_popw"]].to_numpy().max()) + 0.05
ax.set_xlim(lo, hi)
handles = [
    Line2D([], [], marker="o", ls="", markerfacecolor="none", markeredgecolor=EMB,
           markeredgewidth=1.8, markersize=11, label=f"Simple average — leads on {n_simple} of 15"),
    Line2D([], [], marker="o", ls="", color=EMB, markersize=10,
           label=f"{L.POPW_PROSE.capitalize()} — leads on {n_popw} of 15"),
]
ax.legend(handles=handles, loc="lower right", frameon=False, fontsize=13.5)
ax.tick_params(axis="x", labelsize=14)
out = DECKDIR / "figures/fig-popweighting-flip.svg"
fig.savefig(out)
print(f"wrote {out.name}  (lead {n_simple} of 15 -> {n_popw} of 15)")
