# The fusion pays most where the test is hardest: department-transfer (LOWER-bound) out-of-sample
# R² for the three mapped goals, under each of the three feature sets.
#
#   nighttime lights, daytime embeddings   tables/tbl-views-lodo.csv     (both population-weighted)
#   the combined predictor                 tables/tbl-mon-comprehensive.csv
#
# This is the deck's only evidence that combining beats BOTH singles rather than splitting the
# difference — and it is deliberately shown at the lower bound, the regime that is not flattered by
# spatial leakage. index.qmd:464-467 is the prose version.
#
# Drawn honestly. For climate action the fusion lands a hair BELOW the embeddings alone
# (0.435 against 0.458), and that bar is not hidden or reordered away. The claim the slide makes is
# that the combined predictor wins on two of the three and never collapses the way the lights do on
# the one goal that emits no light.
#
# Reproduces figures/fig-transfer-floor.svg
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _paths                            # noqa: E402
_paths.bootstrap()                       # deck root + scripts/ + the vendored sources/code
DECKDIR = _paths.DECK
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import _goals as G
import labels as L
from _palette import DECK, EMB, NTL, apply_deck_style

apply_deck_style()

# Reading order matches the three map slides that follow (poverty, then energy, then climate), so
# the room meets the goals in the same sequence twice. Barh draws bottom-up, hence the reversal.
GOALS = ["SDG 1", "SDG 7", "SDG 13"]

# The combined predictor has no colour anywhere else in the deck — fig-combined-range.svg is
# entirely combined, so it uses the plain accent. Here all three feature sets are on one axis and
# it needs its own. Green is in theme.scss ($success), clears 9.6:1 on the canvas, and is not
# already spoken for: amber means nighttime lights and blue means daytime embeddings throughout.
COMBINED_COLOR = DECK["success"]

lodo = pd.read_csv(_paths.table("tbl-views-lodo.csv")).set_index(L.GOAL_INDEX)
comp = pd.read_csv(_paths.table("tbl-mon-comprehensive.csv")).set_index(L.GOAL_INDEX)

# The combined series also carries a HATCH, not just a hue. Under deuteranopia the green and the
# embeddings blue both resolve to light purples separated mainly by lightness — and those are
# precisely the two bars a viewer must separate to read "the fusion clears the embeddings". The
# hatch is the redundant channel; amber stays distinct without one.
SERIES = [
    (L.NTL, NTL, None, [float(lodo.at[g, L.r2(L.NTL)]) for g in GOALS]),
    (L.EMB, EMB, None, [float(lodo.at[g, L.r2(L.EMB)]) for g in GOALS]),
    (f"{L.COMBINED} (both)", COMBINED_COLOR, "///",
     [float(comp.at[g, f"Out-of-sample {L.R2}"]) for g in GOALS]),
]

# Sanity check, at the SOURCE tables' own precision. If a table moves, fail here rather than
# shipping a slide whose figure and whose speaker notes disagree.
EXPECTED = {                      # (lights, embeddings, combined), three decimals as stored
    "SDG 1": (0.451, 0.442, 0.537),
    "SDG 7": (0.459, 0.412, 0.484),
    "SDG 13": (-0.282, 0.458, 0.435),
}
for j, g in enumerate(GOALS):
    got = tuple(round(s[-1][j], 3) for s in SERIES)
    assert got == EXPECTED[g], f"{g}: read {got}, but the tables store {EXPECTED[g]}"

# DO NOT re-round the stored cells to two decimals. These CSVs are already rounded to three, and
# rounding twice is not rounding once: climate action's combined bound is stored as 0.435, whose
# float repr is fractionally BELOW the tie, so `round(0.435, 2)` returns 0.43 — while the true
# value in `.notebook-cache/sdg13_combow_lodo.pkl` is 0.435304 and the manuscript correctly prints
# 0.44. A figure captioned 0.43 beside speaker notes saying 0.44 is exactly the failure the deck's
# Tier S check cannot see, because it re-rounds the cell too. Labels therefore come from the
# paper's own rendering, and only the one boundary case needs naming.
PAPER_2DP = {("SDG 13", 2): "0.44"}          # (goal, SERIES index) -> the manuscript's rendering


def value_label(goal: str, k: int, v: float) -> str:
    return PAPER_2DP.get((goal, k), f"{v:.2f}")

n = len(SERIES)
H = 0.24                                       # bar height
base = np.arange(len(GOALS))[::-1]             # poverty on top

fig, ax = plt.subplots(figsize=(12.6, 5.6))
for k, (label, color, hatch, vals) in enumerate(SERIES):
    offs = base + (n - 1) / 2 * H - k * H
    # edgecolor: seaborn's white style forces a patch edge, which on a dark canvas outlines every
    # bar (and every legend swatch) in white and reads as a second encoding. The hatched series
    # needs an edge colour anyway — matplotlib draws hatching in the EDGE colour — so it takes the
    # canvas, which makes the hatch read as slots cut out of the bar rather than as added lines.
    ax.barh(offs, vals, height=H * 0.88, color=color, label=label, zorder=3,
            hatch=hatch, edgecolor=DECK["bg"] if hatch else "none",
            linewidth=0.0)
    for yy, v, goal in zip(offs, vals, GOALS):
        # Value labels sit outside the bar on the side the bar grows toward, so a negative bar
        # labels to its left. Without this the -0.28 label would be drawn on top of its own bar.
        ha, dx = ("left", 0.012) if v >= 0 else ("right", -0.012)
        ax.text(v + dx, yy, value_label(goal, k, v), va="center", ha=ha,
                color=DECK["ink"], fontsize=13, zorder=4)

ax.axvline(0, color=DECK["ink"], lw=1.1, zorder=2)
ax.set_yticks(base)
ax.set_yticklabels([G.tick(g) for g in GOALS], fontsize=15)
# Just the quantity. The evaluation regime is the slide's `.source` line, and having both say
# "tested in a department the model never saw" put the same sentence on screen twice.
ax.set_xlabel(f"Out-of-sample {L.R2}", fontsize=16)
ax.tick_params(axis="x", labelsize=13)
ax.set_xlim(min(-0.36, min(min(s[-1]) for s in SERIES) - 0.08),
            max(max(s[-1]) for s in SERIES) + 0.10)
ax.spines["left"].set_visible(False)
ax.tick_params(axis="y", length=0)
# Legend ABOVE the axes, not inside it. Every in-axes corner is occupied: the bars fill the right
# half at all three goals, the left half is claimed by the one negative bar, and the value labels
# sit just beyond every bar end. A first attempt at lower-right buried climate action's 0.46 and
# 0.44 labels under the legend text.
ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=3, frameon=False,
          fontsize=14, labelcolor=DECK["ink"], handlelength=1.4, handleheight=1.1,
          columnspacing=2.2, borderaxespad=0.0)

out = DECKDIR / "figures/fig-transfer-floor.svg"
fig.savefig(out)
wins = sum(1 for j in range(len(GOALS)) if SERIES[2][-1][j] >= max(SERIES[0][-1][j], SERIES[1][-1][j]))
print(f"wrote {out.name}  ({L.lc(L.COMBINED)} is highest on {wins} of {len(GOALS)} goals)")
