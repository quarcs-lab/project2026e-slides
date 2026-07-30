# `sources/` — the vendored snapshot

**This directory is read-only by convention. Do not edit anything in it.**

This deck is designed to be lifted out of the research repository it was built in and dropped
into a repository of its own.
Everything under `sources/` is a frozen copy of an input the deck needs in order to regenerate
its figures and verify its numbers, taken from the manuscript repository
[`project2026e`](https://github.com/quarcs-lab/project2026e).
Without it the deck would still *render* — the slides reference only `figures/` and `fonts/` — but
no figure could be rebuilt and no number could be checked.

`scripts/_paths.py` is the only thing that resolves paths in here.
Never open a file under `sources/` by a hand-written relative path.

## Why the layout mirrors the source repository

The tree below deliberately reproduces `project2026e`'s own layout (`code/`, `tables/`, `data/…`)
rather than flattening it.
Two things depend on that:

- `code/hf_data.py` computes its local data root as `Path(__file__).parent.parent / "data"`, which
  lands on `sources/data` with **no edit to the file**. That is what lets the vendored copy stay
  byte-identical to upstream.
- `scripts/_source_checks.py` resolves each `numbers.toml` entry as `<root>/<source>`, so pointing
  its root at `sources/` makes every `source = "tables/…"` entry work unchanged.

```
sources/
├── README.md            this file
├── PROVENANCE.toml      sha256 + git provenance for every file below
├── claims.toml          the 15 numbers the deck takes from the manuscript's prose
├── code/                7 Python modules, imported flat (never as a package)
├── tables/              9 result tables the figure scripts read
├── notebook-cache/      9 pickled out-of-fold predictions
└── data/
    ├── maps/            municipal boundaries (GeoJSON)
    ├── regionNames/     municipality and department names
    ├── sdg/             the goal indices
    ├── predictions/     the three four-view prediction series
    ├── population/rasters/            GHS-POP 2017
    └── satelliteEmbeddings/rasters/   the PCA false-colour composite
```

## Three things about this tree that will surprise you

**1. `notebook-cache/`, not `.notebook-cache/`.**
Upstream the pickles live in a dot-directory. Here the dot is dropped, because the source
repository's root `.gitignore` contains the bare pattern `.notebook-cache/`, which git matches at
*any* depth. A vendored `sources/.notebook-cache/` was therefore silently un-addable: `git add`
would exit 0 having added nothing, and the failure would only surface weeks later, in someone
else's fresh clone, as a `FileNotFoundError`. `_paths.cache()` maps the name back when it looks in
a full checkout, and `_sync_check.py` records the upstream path so the two can still be diffed.

**2. Only the seven `.py` files carry a provenance banner.**
This is forced, not a preference. A comment line at the top of a CSV breaks both `csv.DictReader`
and `pandas.read_csv`, and `.geojson`, `.tif` and `.pkl` obviously cannot carry one either. So
every non-Python file here is **byte-identical** to its upstream original and `PROVENANCE.toml` is
its only record. The Python banners are delimited by `BEGIN`/`END` marker lines so
`_sync_check.py` can strip them and still compare content; it stores both hashes for that reason.

**3. The nighttime-lights raster is deliberately missing.**
`data/nighttimeLights/rasters/bolivia_ntl_viirs_2017.tif` is 118 MB, over GitHub's 100 MB per-file
limit, so it is not vendored. `_paths.data()` falls back to streaming it from the Hugging Face
dataset [`cmg777/project2026e`](https://huggingface.co/datasets/cmg777/project2026e) through
`code/hf_data.py`, which caches it under `~/.cache/huggingface` on first use. This affects exactly
two figures — `scripts/fig-ntl-raster.py` and the nighttime-lights panel of
`scripts/fig-data-layers.py`. Every other figure in the deck builds offline from this snapshot.

## These files are for importing, not for running

The four `plot_*.py` modules define default input paths relative to the *current working
directory* (`"data/maps/…"`), because upstream they are run from the repository root. The deck
never uses those defaults — `scripts/_rasters.py` passes every path explicitly — but it does mean
that running one of them directly from here (`python sources/code/plot_ntl_raster.py`) will look
for a `data/` directory next to wherever you happen to be standing and fail. Run them from a full
`project2026e` checkout instead.

They also cannot be imported as a package: `plot_data_overview.py` imports its siblings flat
(`import plot_ntl_raster as pnr`), and a directory named `code` on the import path would shadow
Python's own `code` module. That is why there is no `__init__.py` here and why
`_paths.bootstrap()` puts `sources/code` on `sys.path` instead.

## Checking the snapshot

```bash
# Is the snapshot internally intact — every file present, every hash matching?
uv run python scripts/_sync_check.py .

# Has upstream moved on? (needs a project2026e checkout)
uv run python scripts/_sync_check.py . --root /path/to/project2026e
```

The first form needs nothing but this folder and exits 0 when the snapshot is undamaged.
The second compares each file against its original and says **which side moved** — whether
upstream advanced, or whether someone edited the snapshot here.

## Refreshing it

Refreshing is deliberately a two-step manual operation. `--freeze` rewrites the provenance record
but never copies files, so it cannot quietly overwrite a copy that was pinned on purpose.

```bash
R=/path/to/project2026e

# 1. See what actually moved, and decide whether you want it.
uv run python scripts/_sync_check.py . --root $R

# 2. Copy the files you decided to take. For example:
cp $R/tables/tbl-popweighting-master.csv sources/tables/
cp $R/code/labels.py sources/code/          # then restore its banner

# 3. Re-record the provenance, and re-freeze the manuscript claims.
uv run python scripts/_sync_check.py . --root $R --freeze
uv run python scripts/_sync_check.py . --root $R --freeze-claims

# 4. Rebuild every figure and re-verify every number.
for f in scripts/fig-*.py; do uv run python "$f"; done
uv run python scripts/_source_checks.py .
```

Step 4 is not optional. Changing an input under `sources/` changes figures, and a stale figure
next to a fresh number is exactly the failure the verification tiers exist to catch. In particular,
the spatial weights are one definition shared by the whole project (`code/spatial_weights.py`):
changing them moves every Moran's *I*, every LISA class, and can reverse a comparative claim.

## `claims.toml` — and why the paper is not in here

Fifteen numbers on the slides come from the manuscript's *prose*, not from any table cell.
Upstream those were verified with regular expressions against `index.qmd`. The manuscript text is
not shipped with this deck, so instead `claims.toml` records, for each of those numbers, the value,
the line number it was found on, and the **sha256 of that line**. Storing the hash rather than the
sentence is what keeps the paper out of this repository while still making the check fail loudly if
the number ever changes.

Standalone, `_source_checks.py` verifies the slides against those frozen values. Given
`--root <a project2026e checkout>` it additionally re-runs the original regexes against the live
manuscript, and distinguishes *the number changed* (a failure) from *the number is the same but the
prose moved* (a warning: re-freeze).
