# ─── VENDORED SNAPSHOT — BEGIN (do not edit; do not remove these two markers) ───
# source repo : https://github.com/quarcs-lab/project2026e
# source path : code/labels.py
# last commit : 75e469ef2304e01565037304d8a1265c062c3ee2  (2026-07-20)
# snapshot    : 2026-07-30 @ 9856b81
# refresh     : uv run python scripts/_sync_check.py . --root /path/to/project2026e
# ─── VENDORED SNAPSHOT — END ───
#!/usr/bin/env python3
"""Canonical display labels for the manuscript's predictor views.

ONE concept -> ONE display string. Every figure legend, panel title, axis label,
and exported table column header must take its human-readable text from here, so
that a rename happens in one place instead of the ~12 notebooks that used to
carry their own copies.

Import pattern (matches ``notebooks/data-overview-panels.qmd`` and the flat
sibling imports in ``code/plot_data_overview.py``)::

    import os, sys
    sys.path.insert(0, os.path.abspath("../code"))   # from notebooks/
    import labels as L

    ax.scatter(..., label=L.NTL)                     # "Nighttime lights"
    tbl.columns = [L.GOAL_INDEX, L.r2(L.EMB), L.dr2_diff(L.EMB, L.NTL)]

NOTE: ``from code.labels import ...`` must NOT be used. ``code`` is a Python
standard-library module name (the interactive-interpreter helper), so a package
import would shadow it. That is why this repo uses ``sys.path`` + flat imports.

THE TWO-LEVEL VOCABULARY
------------------------
The manuscript aggregates 62 **component indicators** into 15 **goal indices**,
and those into 1 **composite index**. Do NOT write "SDG goal indices" — that
expands to "Sustainable Development Goal goal indices". "Indicator" means the 62
and only the 62. A table whose rows are the fifteen goal indices must head its
first column ``GOAL_INDEX``, never "Indicator" — otherwise the caption in
``index.qmd`` ("Out-of-sample R² by goal index ...") contradicts the table
printed beneath it. Write sites (notebooks) and read sites (the
``slides/*/scripts/fig-*.py`` figure scripts) both take the header from this
constant so the two cannot drift apart again.

CACHE AND FILE TAGS ARE NOT LABELS
----------------------------------
The tags ``simple``, ``weighted``, ``ntl8``, ``ntlw8``, ``combo``, ``combow``,
``combow_simplentl`` and the ``_rand`` / ``_lodo`` suffixes are **filesystem
identifiers** for ``.notebook-cache/<slug>_<tag>.pkl``. The canonical list lives
in ``scripts/generate_lodo_caches.py`` (the ``SETS`` dict). They MUST NOT be
renamed: doing so orphans every cached result and forces a full refit. This
module maps tag -> label in one direction only; never invert ``TAG_LABEL`` to
derive a filename.

RENAMING A LABEL LATER
----------------------
Quarto's ``freeze: auto`` hashes the ``.qmd`` source, NOT the modules it
imports. Editing this file alone will not re-execute any notebook. After a
change here, run ``rm -rf _freeze/notebooks/<slug>`` for each consumer and
re-render with the two-pass ``scripts/render.sh``.
"""

from __future__ import annotations

# --- The four concepts. These four strings are the whole point of this module. -----
ACTUAL = "Actual"
NTL = "Nighttime lights"
EMB = "Daytime embeddings"
COMBINED = "Combined"

#: Figure-panel order for the four-view comparison figures.
VIEWS = (ACTUAL, NTL, EMB, COMBINED)

# --- Row-key column headers. See "THE TWO-LEVEL VOCABULARY" above. -----------------
#: First-column header for a table whose rows are the 15 goal indices.
GOAL_INDEX = "Goal index"
#: First-column header for a table whose rows are the 62 component indicators.
INDICATOR = "Indicator"
#: Row label for the composite in a table whose other rows are goal indices.
#: The acronym "IMDS" is expanded exactly once, in index.qmd where the outcomes
#: are introduced; every other site — prose, row label, caption — uses this.
COMPOSITE = "Composite index"

#: Row label for each goal index, keyed by its column name in ``data/sdg/sdg.csv``.
#: The form is "<keyword> (SDG n)" — the same strings the eleven
#: ``notebooks/predict-development-*.qmd`` build locally from a ``KEYWORD`` dict.
#: Two label forms are in circulation and this is only one of them: the keyword form
#: here is what ``tables/tbl-popweighting-master.md`` (body Table 2) and the
#: ``tbl-g{1,2,3}-*`` group tables print, while ``tbl-views-lodo.md``,
#: ``tbl-mon-comprehensive.md`` and ``tbl-dev-master.md`` print the bare "SDG n" form.
#: Do NOT assume a rename here reaches every shipped table. New table builders under
#: ``scripts/`` import this instead of copying the dict a twelfth time.
#: Insertion order is SDG order; a table that wants the manuscript's legibility
#: ordering sorts its own rows. SDG 12 and SDG 14 have no municipal data and so have
#: no key here (see index.qmd, "Outcome variables").
GOAL_LABEL = {
    "index_sdg1": "Poverty (SDG 1)",
    "index_sdg2": "Hunger (SDG 2)",
    "index_sdg3": "Health (SDG 3)",
    "index_sdg4": "Education (SDG 4)",
    "index_sdg5": "Gender (SDG 5)",
    "index_sdg6": "Water (SDG 6)",
    "index_sdg7": "Energy (SDG 7)",
    "index_sdg8": "Jobs (SDG 8)",
    "index_sdg9": "Infrastructure (SDG 9)",
    "index_sdg10": "Inequality (SDG 10)",
    "index_sdg11": "Cities (SDG 11)",
    "index_sdg13": "Climate (SDG 13)",
    "index_sdg15": "Land (SDG 15)",
    "index_sdg16": "Institutions (SDG 16)",
    "index_sdg17": "Partnerships (SDG 17)",
}

#: The composite's column name in ``data/sdg/sdg.csv``. Its row label is COMPOSITE,
#: never the raw column name and never the expanded acronym.
COMPOSITE_COL = "imds"

# --- Prose forms. For captions and running text, never for headers or legends. -----
COMBINED_PROSE = "the combined predictor"
NTL_ATTR = "nighttime-lights"    # attributive: "the nighttime-lights baseline"
EMB_ATTR = "daytime-embeddings"  # attributive: "the daytime-embeddings block"

# --- Weighting qualifiers. Exactly two forms exist. --------------------------------
SIMPLE = "simple"          # equal-pixel (unweighted) spatial mean
POPW = "pop-weighted"      # figures and table headers
POPW_PROSE = "population-weighted"  # prose and fig-cap text ONLY


def qual(base: str, weighting: str) -> str:
    """``qual(NTL, SIMPLE)`` -> ``'Nighttime lights (simple)'``."""
    return f"{base} ({weighting})"


def simple(base: str) -> str:
    """``simple(EMB)`` -> ``'Daytime embeddings (simple)'``."""
    return qual(base, SIMPLE)


def popw(base: str) -> str:
    """``popw(NTL)`` -> ``'Nighttime lights (pop-weighted)'``."""
    return qual(base, POPW)


# --- Metric glyphs. Unicode throughout; never "R2" or "Delta R2". ------------------
R2 = "R²"       # U+00B2 SUPERSCRIPT TWO
DR2 = "ΔR²"  # U+0394 GREEK CAPITAL DELTA
MINUS = "−"     # U+2212 MINUS SIGN, for "ΔR² (A − B)" headers


def lc(base: str) -> str:
    """Lower the leading capital so a label reads as a common noun mid-sentence.

    ``lc(EMB)`` -> ``'daytime embeddings'``. Public: figure axis labels and prose
    f-strings outside this module need it.
    """
    return base[:1].lower() + base[1:]


#: Back-compat alias. ``lc`` is the public name; ``_lc`` predates it.
_lc = lc


def r2(base: str, weighting: str | None = None) -> str:
    """``r2(EMB)`` -> ``'R² daytime embeddings'``;
    ``r2(NTL, POPW)`` -> ``'R² nighttime lights (pop-weighted)'``."""
    s = f"{R2} {_lc(base)}"
    return s if weighting is None else qual(s, weighting)


def dr2(base: str, weighting: str | None = None) -> str:
    """``dr2(NTL)`` -> ``'ΔR² nighttime lights'``."""
    s = f"{DR2} {_lc(base)}"
    return s if weighting is None else qual(s, weighting)


def dr2_diff(a: str, b: str) -> str:
    """``dr2_diff(EMB, NTL)`` -> ``'ΔR² (daytime embeddings − nighttime lights)'``."""
    return f"{DR2} ({_lc(a)} {MINUS} {_lc(b)})"


# --- Feature counts. Stated only where block size is the subject of the figure. ----
N_EMB, N_NTL, N_COMBINED = 64, 8, 72


def with_count(base: str, n: int) -> str:
    """``with_count(EMB, N_EMB)`` -> ``'Daytime embeddings (64 features)'``."""
    return f"{base} ({n} features)"


# --- Panel lettering for the four-view figures ------------------------------------
def lettered(bases=VIEWS) -> list[str]:
    """``lettered()`` -> ``['(a) Actual', '(b) Nighttime lights', ...]``."""
    return [f"({chr(97 + i)}) {b}" for i, b in enumerate(bases)]


# --- tag -> label. One direction only; see the module docstring. -------------------
TAG_LABEL = {
    "simple": qual(EMB, SIMPLE),
    "weighted": qual(EMB, POPW),
    "ntl8": qual(NTL, SIMPLE),
    "ntlw8": qual(NTL, POPW),
    "combo": qual(COMBINED, SIMPLE),
    "combow": qual(COMBINED, POPW),
    "combow_simplentl": f"{COMBINED} (mixed weighting)",
}

#: Strings retired by the 2026-07 terminology pass. Grepped for in verification;
#: none of these may reappear in a notebook, a plotting module, or a shipped table.
RETIRED = (
    "Satellite embeddings", "Satellite embeddings (64-dim)", "Embeddings (64)",
    "Embeddings block (64)", "Embeddings (pop-wt)", "Emb. (simple)", "Emb. (pop-w)",
    "R² emb", "R² embeddings", "R² (emb)",
    "Nighttime lights (8)", "Nighttime lights (8-band)", "Nighttime-lights block (8)",
    "Nighttime lights (pop-wt)", "Lights (simple)", "Lights (pop-w)",
    "R² NTL", "ΔR² NTL", "R² (NTL)",
    "(pop-w)", "(pop-wt)", "NTL", "DTE", "R2 ", "Delta R2",
)

#: Acronyms retired from figure captions and table CONTENT by the 2026-07 pass.
#: KEPT — do not add: VIIRS, AlphaEarth, LISA, CartoDB, GHS-POP, HIV, AIDS, BMI,
#: CO2, and the Bolivian source institutions (INE, UDAPE, AGETIC, ASFI, OBSCD,
#: SEIE, AAPS, RUAT), which are glossed in the Table B2 note. "SDG 1".."SDG 17"
#: are proper labels, not acronyms, and must keep the space: never "SDG1".
#: "IMDS" is sanctioned at exactly one site, its definition in index.qmd.
#:
#: GREP HAZARD when verifying: do NOT add "CV" (it is a substring of the live
#: identifiers cv_cached / run_random_cv / run_spatial_cv) and note that "KNN"
#: matches real code (from libpysal.weights import KNN, KNN_K). Scope any check
#: to caption and label lines, not a bare recursive grep.
RETIRED_ACRONYMS = (
    "IMDS", "IMDS (composite)", "SDG1", "KNN", "OLS", "STI", "LPG", "ICT",
    "PC1", "PC2", "PC3", "SDG goal indices",
)
