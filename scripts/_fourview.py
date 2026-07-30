"""Shared loader for the four-view maps (actual / lights / embeddings / combined), per goal.

Both `fig-views-choropleth.py` and `fig-views-lisa.py` need the same four aligned series, and
getting that alignment wrong produces a map that looks plausible and is wrong. The loading and the
guard therefore live here once.

Covers the three goals that clear the deck's 0.60 bar — see `GOALS`. Everything except the target
column, the cache slug and the cluster wording is goal-independent, so the spatial spec and the
palettes are shared verbatim across all three maps.

Provenance. The predictions are the random 5-fold out-of-fold series the manuscript's four-panel
figures plot — `oof_pred` from the notebook cache. NO MODEL IS RE-FIT; these are frozen outputs.

On unpickling: `.notebook-cache/*.pkl` is written by this repository's own notebooks, is gitignored,
and never leaves the machine that produced it — it is a local build artifact, not third-party data,
so `pickle.loads` here carries no untrusted-input risk. The exported CSV exists partly so that the
committed, shareable path into this data needs no unpickling at all.

Do NOT recompute R² from these series for a slide. The manuscript's R² is the per-fold average
(`r2_mean` in the cache); a pooled R² over the concatenated out-of-fold vector is a different and
consistently higher estimator — SDG 7 lights is 0.532 pooled against 0.500 published. Both are
defensible, but only one is in the paper. Quote the table. Pearson r, by contrast, is identical
either way, which is what makes it a useful cross-check that these series are aligned at all: all
nine match the published tables to three decimals.

Two traps this module exists to avoid:

1. The pickles carry no `asdf_id`. Alignment to geography is POSITIONAL, against `data/sdg/sdg.csv`
   row order after dropping missing targets. `_from_cache` asserts each pickle's stored `y_true`
   matches the actual series element-wise; that assertion is the only thing standing between a
   correct map and a silently scrambled one.

2. `data/predictions/sdg1_oos_2017.csv` is NOT a source for the combined panel. Its `sdg1_oof`
   column is the department-transfer series, not the random-fold one — different map, different
   Moran's I, different clusters.

The cache is gitignored, so the first successful run exports a tracked CSV that later runs (and a
fresh clone) read instead. If neither the CSV nor the cache is present the loader raises rather
than falling back to anything that would re-fit.
"""
from __future__ import annotations

import pathlib
import pickle
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _paths                                       # noqa: E402
# Must run before the `from _palette import MAP` below (_palette lives at the deck root, not
# in scripts/) and before the lazy `from spatial_weights import queen_repaired` further down.
_paths.bootstrap()

import numpy as np                                  # noqa: E402
import pandas as pd                                 # noqa: E402

# The three goals whose combined upper-bound out-of-sample R² clears 0.60 — the deck's bar for
# drawing a map. Mirrors SDG_INFO in notebooks/monitoring-views-comparison.qmd:115; keep the two in
# step, because the manuscript's figures and these are meant to be the same maps.
#
# All three are ACHIEVEMENT indices (higher = better), which is what makes the cluster semantics
# uniform: a high-high cluster is a cluster of high achievement, a low-low cluster a trap of low
# achievement. `hi_label`/`lo_label` are the plain-language versions for a talk — "Poverty trap"
# means something to an audience in a way "Low-low" does not, and the wording has to change per
# goal or it is simply wrong (a "poverty trap" on the energy map is nonsense).
GOALS = {
    "sdg1": {
        "target": "index_sdg1", "label": "SDG 1", "theme": "No Poverty",
        "hi_label": "Low-poverty cluster", "lo_label": "Poverty trap",
    },
    "sdg7": {
        "target": "index_sdg7", "label": "SDG 7", "theme": "Affordable and Clean Energy",
        "hi_label": "Cluster of good access", "lo_label": "Trap of poor access",
    },
    "sdg13": {
        "target": "index_sdg13", "label": "SDG 13", "theme": "Climate Action",
        "hi_label": "Cluster of strong action", "lo_label": "Trap of weak action",
    },
}
DEFAULT_SLUG = "sdg1"


def export_path(slug: str) -> pathlib.Path:
    """Where the four-view series lives: the snapshot if it is there, else ``derived/``.

    Read and write are deliberately different places. ``sources/`` is the immutable snapshot
    that ``_sync_check.py`` hashes, so a regenerated CSV landing there would read as
    divergence from the manuscript — exactly backwards — and re-freezing to "fix" it would
    quietly bless a deck-computed value as if it had come from the paper.

    All three CSVs ship in the snapshot, so the normal path reads and never writes. ``derived/``
    fills only when someone removes a snapshot copy to prove the pickle-to-CSV chain still
    works, which is a test worth being able to run.
    """
    rel = f"data/predictions/{slug}_fourview_2017.csv"
    snap = _paths.SOURCES / rel
    return snap if snap.exists() else _paths.derived(rel)


def target_of(slug: str) -> str:
    if slug not in GOALS:
        raise KeyError(f"unknown goal {slug!r}; expected one of {sorted(GOALS)}")
    return GOALS[slug]["target"]
# view column -> cache tag. Tags are filesystem identifiers, not display labels.
VIEW_TAGS = {"pred_ntl": "ntlw8", "pred_emb": "weighted", "pred_combo": "combow"}
VIEW_COLS = ["actual", *VIEW_TAGS]

# Spatial spec, identical to notebooks/monitoring-views-comparison.qmd:105-106.
#
# The NEIGHBOUR DEFINITION is not here. It lives in `code/spatial_weights.queen_repaired`, the
# project's single weights authority, and `queen_weights()` below calls it. This module used to
# carry its own `KNN(k=6)`, which silently disagreed with the paper for eight days after the
# manuscript switched to queen contiguity on 2026-07-20. The k=6 was a misreading: six is the
# rounded MEAN queen cardinality, used only to reconnect the one island (Coipasa), never as a
# global rule. `verify_against_paper()` is what stops that class of drift recurring.
LISA_SEED = 12345
N_PERMUTATIONS = 999
SIG = 0.05

# Map palettes for the DARK canvas. Two of the light-preset colours invert badly:
#
#   "Not significant" must RECEDE. On white it was #d3d3d3; on #0B1F3A that scores 11:1 and would
#   make the non-significant municipalities the brightest thing on the map — the opposite of what
#   the class means. It becomes a dark slate that sits just above the canvas (1.6:1). Low contrast
#   is the goal here; `outline()` supplies the country's shape instead.
#
#   The cluster fills are lightened so they clear the dark canvas: the old red scored 3.0:1 and the
#   old blue 3.6:1.
# Single-sourced from _palette.MAP, which mirrors theme.scss. Hardcoding them here once meant the
# palette-drift check flagged the cluster red as off-palette — correctly, since nothing declared it.
from _palette import MAP as _MAP

CLUSTER_COLORS = {
    "High-high": _MAP["high_high"],        # low-poverty cluster, 4.7:1
    "Low-low": _MAP["low_low"],            # poverty trap,        6.7:1
    "High-low": _MAP["high_low"],          # outlier,             9.1:1
    "Low-high": _MAP["low_high"],          # outlier,             9.0:1
    "Not significant": _MAP["null_fill"],  # recessive by design, 1.7:1
}
# The choropleth's middle class is a real data class, not an absence of signal, so it stays LIGHT
# while the LISA "not significant" goes dark. That keeps the two neutrals unmistakable on adjacent
# slides — the distinction is now semantic, not just hue.
BRACKET_MID = _MAP["bracket_mid"]
BRACKET_COLORS = [CLUSTER_COLORS["Low-low"], CLUSTER_COLORS["Low-high"], BRACKET_MID,
                  CLUSTER_COLORS["High-low"], CLUSTER_COLORS["High-high"]]
OUTLINE = _MAP["outline"]          # national boundary — legible on dark, quiet against the data
PLOT_ORDER = ["Not significant", "Low-low", "High-low", "Low-high", "High-high"]
LEGEND_ORDER = ["High-high", "Low-low", "High-low", "Low-high", "Not significant"]
QUAD = {0: "Not significant", 1: "High-high", 2: "Low-high", 3: "Low-low", 4: "High-low"}

PANEL_TITLES = {
    "actual": "(a) Actual",
    "pred_ntl": "(b) Nighttime lights",
    "pred_emb": "(c) Daytime embeddings",
    "pred_combo": "(d) Combined",
}


def _from_cache(slug: str) -> pd.DataFrame:
    target, export = target_of(slug), export_path(slug)
    sdg = pd.read_csv(_paths.data("sdg/sdg.csv"))
    sub = sdg.dropna(subset=[target]).reset_index(drop=True)
    actual = sub[target].to_numpy()

    out = {"asdf_id": sub["asdf_id"].to_numpy(), "actual": actual}
    for col, tag in VIEW_TAGS.items():
        try:
            path = _paths.cache(f"{slug}_{tag}.pkl")
        except _paths.Unavailable as exc:
            raise FileNotFoundError(
                f"{slug}_{tag}.pkl not found and {export} does not exist either.\n"
                "Run notebooks/monitoring-views-comparison.qmd (or the prediction notebooks) to "
                "rebuild the cache. This script will not fit a model.\n"
                f"{exc}"
            ) from exc
        res = pickle.loads(path.read_bytes())
        # The guard. Positional alignment is only valid if the stored truth matches ours.
        if not np.allclose(res["y_true"], actual):
            raise AssertionError(
                f"{path.name}: stored y_true does not match {target} from sdg/sdg.csv. "
                "Row alignment is positional, so the map would be scrambled. Refusing to plot."
            )
        out[col] = np.asarray(res["oof_pred"])

    df = pd.DataFrame(out)
    names = pd.read_csv(_paths.data("regionNames/regionNames.csv"))[["asdf_id", "mun", "dep"]]
    df = df.merge(names, on="asdf_id", how="left", validate="one_to_one")
    return df[["asdf_id", "mun", "dep", *VIEW_COLS]]


def load(slug: str = DEFAULT_SLUG, export: bool = True) -> pd.DataFrame:
    """Return the four aligned series for `slug`, preferring the tracked CSV over the cache."""
    path = export_path(slug)
    if path.exists():
        df = pd.read_csv(path)
        missing = [c for c in VIEW_COLS if c not in df.columns]
        if missing:
            raise ValueError(f"{path} is missing column(s): {missing}")
        return df

    df = _from_cache(slug)
    if export:
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)
        print(f"exported {path.relative_to(_paths.DECK)}  ({len(df)} rows)")
    return df


def geo(df: pd.DataFrame):
    """Join the series onto municipal geometry, in the file's NATIVE CRS (EPSG:4326).

    Deliberately not reprojected, and the reason is narrower than it used to be. Queen contiguity
    is topological — two polygons either touch or they do not — so the CRS cannot change it. But
    `queen_repaired` reconnects the one island (Coipasa) to its k nearest neighbours by CENTROID
    DISTANCE, and that step is metric: computed on Mercator metres it could pick a different set
    than on degrees. `monitoring-views-comparison.qmd:229` reads the same geojson with no `to_crs`
    and builds its weights on that frame, so this one must too. Callers reproject for display via
    `web_mercator()`.
    """
    import geopandas as gpd

    g = gpd.read_file(_paths.data("maps/bolivia339geoqueryOpt.geojson"))[["asdf_id", "geometry"]]
    g = g.merge(df, on="asdf_id", how="inner", validate="one_to_one")
    assert len(g) == len(df), f"geometry join lost rows: {len(g)} of {len(df)}"
    # Row order fixes the weights' index, so pin it the way the notebook does.
    return g.sort_values("asdf_id").reset_index(drop=True)


def web_mercator(g):
    """Reproject for display only — never for weights construction."""
    return g.to_crs(3857)


def outline(g, ax):
    """Draw the national boundary.

    On the dark canvas the "not significant" fill is deliberately close to the background, so
    without this the country's silhouette would dissolve and the map would lose its shape. A thin
    light outline carries the geography while staying quiet against the data.
    """
    g.dissolve().boundary.plot(ax=ax, color=OUTLINE, linewidth=0.7, zorder=5)


def queen_weights(g):
    """Row-standardised queen contiguity, island repaired — the project's ONE weights definition.

    Delegates to `code/spatial_weights.queen_repaired`, which every other consumer also calls
    (`scripts/build_outcome_descriptives.py`, `notebooks/monitoring-views-comparison.qmd`,
    `notebooks/monitoring-sdg1-spacetime.qmd`, `notebooks/esda-imds.qmd`). Never build a weights
    matrix here: Table 1, Table 3, the manuscript's cluster maps and these slides must all come
    from the same neighbour sets, and `verify_against_paper()` asserts that they do.

    `g` must already be `sort_values("asdf_id").reset_index(drop=True)` — weights are positional.
    `geo()` guarantees that.
    """
    # sources/code is on sys.path via _paths.bootstrap() at import time — guaranteed, where it
    # used to be incidental on whichever caller happened to insert the path first.
    from spatial_weights import queen_repaired

    w, _meta = queen_repaired(g)
    return w


def clusters(values, w):
    """LISA classes at p < 0.05, non-significant otherwise. Returns (labels, Moran's I)."""
    from esda.moran import Moran, Moran_Local

    lisa = Moran_Local(values, w, permutations=N_PERMUTATIONS, seed=LISA_SEED)
    labels = pd.Series(np.where(lisa.p_sim < SIG, lisa.q, 0)).map(QUAD).to_numpy()
    return labels, float(Moran(values, w).I)


def hotcold_agreement(labels: dict, view: str, reference: str = "actual") -> float:
    """Share of the reference's hotspots and coldspots that `view` classifies the same way.

    "Hotspots and coldspots" are the high-high and low-low classes — the clusters a monitor exists
    to find. Restricting to them is the honest denominator: including the non-significant majority
    would inflate every view's score, because most municipalities are non-significant in both maps.
    """
    ref = pd.Series(labels[reference])
    sel = ref.isin(["High-high", "Low-low"])
    return float((pd.Series(labels[view])[sel] == ref[sel]).mean())


# --------------------------------------------------------------------------- paper agreement
# Column name in tables/tbl-views-comparison-<slug>.csv for each of our view columns.
PAPER_COLS = {
    "actual": "Actual (reference)",
    "pred_ntl": "Nighttime lights",
    "pred_emb": "Daytime embeddings",
    "pred_combo": "Combined",
}


def _rounds_to(ours: float, stored: str) -> bool:
    """True if `ours` rounds to the value the table stores, at the table's own precision.

    The shipped CSVs are already rounded, and to a varying number of places (0.33 next to 0.596),
    so a fixed tolerance is either too loose or too tight. Deriving it from the stored string is
    exact: a genuine drift here moves values by whole percentage points, not by an ulp.
    """
    d = len(stored.split(".")[1]) if "." in stored else 0
    return abs(ours - float(stored)) <= 0.5 * 10 ** (-d) + 1e-9


def verify_against_paper(slug: str, morans: dict, labels: dict) -> None:
    """Assert the deck reproduces the manuscript's spatial statistics exactly.

    The deck and the paper must draw the SAME maps. They compute them independently — the paper in
    `notebooks/monitoring-views-comparison.qmd`, the deck here — from the same frozen out-of-fold
    predictions, the same geometry, the same seed, and (since this module stopped rolling its own
    KNN) the same weights. So every statistic must agree, and this raises if one does not.

    It is deliberately not optional and not tolerance-tuned. From 2026-07-20 to 2026-07-28 the deck
    shipped Moran's I and hot/coldspot shares off by up to seven points because nothing compared
    them to anything. Silence was the bug.
    """
    name = f"tbl-views-comparison-{slug}.csv"
    try:
        path = _paths.table(name)
    except _paths.Unavailable:                  # a goal the manuscript does not tabulate
        print(f"  (no published table at {name}; verification skipped)")
        return

    tbl = pd.read_csv(path, dtype=str).set_index("Statistic")
    actual = pd.Series(labels["actual"])
    hotcold = actual.isin(["High-high", "Low-low"])
    bad = []

    for col, paper_col in PAPER_COLS.items():
        checks = [("Moran's I", morans[col])]
        if col != "actual":
            pred = pd.Series(labels[col])
            checks += [
                ("LISA agreement %", float((pred == actual).mean()) * 100.0),
                ("LISA hot/cold %", float((pred[hotcold] == actual[hotcold]).mean()) * 100.0),
            ]
        for stat, ours in checks:
            stored = tbl.at[stat, paper_col]
            if pd.isna(stored) or str(stored).strip() in {"", "–", "-"}:
                continue
            if not _rounds_to(ours, str(stored).strip()):
                bad.append(f"    {stat:<18} {paper_col:<20} deck {ours:>9.3f}  paper {stored:>8}")

    if bad:
        raise AssertionError(
            f"{slug}: the deck's spatial statistics disagree with {path.name}.\n"
            + "\n".join(bad)
            + "\n  The deck and the manuscript must draw the same maps. Check the weights "
              "definition, the row order, and the LISA seed before regenerating this figure."
        )
    print(f"  verified against tables/{path.name}: all statistics match the manuscript")
