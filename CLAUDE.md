# CLAUDE.md — AI assistant instructions

**What this repository is:** a self-contained Quarto reveal.js conference talk (24 slides, ~15–20
min) on predicting and monitoring Bolivian municipal development from satellite imagery. It
renders, regenerates every figure, and verifies every number it asserts with no reference to any
other repository.

**Read [`README.md`](README.md) first** — it is the reasoning behind every rule below. This file
is the short imperative form.

**First actions in a session:** read this file, then `README.md`, then `outline.md` for the
narrative arc. Run `uv run python scripts/_sync_check.py .` to confirm the snapshot is intact
before changing anything.

---

## Hard rules

1. **Never `pip install`.** `uv add` / `uv run` / `uv sync` only — `pip` bypasses `uv.lock`.
2. **Never delete anything** under `sources/`, `figures/`, `fonts/` or `scripts/`. Move a
   superseded file to `legacy/` instead.
3. **`sources/` is a read-only snapshot.** To change an input, change it upstream in
   `project2026e` and re-freeze (`scripts/_sync_check.py . --root <checkout> --freeze`). Never
   hand-edit a file in there, and never hand-edit a hash in `PROVENANCE.toml`. The vendored CSV,
   GeoJSON, TIF and PKL files are byte-identical to their originals and must stay so.
4. **Never compute a path with `parents[N]` above the deck folder.** Use `scripts/_paths.py`:
   `table()`, `data()`, `cache()`, `figure()`, `derived()`. This is the single defect the whole
   portability effort existed to remove, and it was present in eleven files.
5. **Never hand-edit a number inside a figure.** Regenerate it: `uv run python scripts/fig-*.py`.
6. **Every number on a slide needs a `numbers.toml` entry** (or an explicit `[meta] ignore`).
   Tier S is fail-closed by design — a new number with no entry is a build failure, not a warning.
7. **`theme.scss` and `_palette.py` are one palette in two files.** Change both, then re-run
   Tier B, or the figures drift from the slides.
8. **Never read `data/satelliteEmbeddings/rasters/bolivia_embeddings_2017.tif`** (~3 GB, and not
   in the snapshot). The deck uses the 11 MB PCA composite. Never call
   `plot_data_overview.plot_overview()` or `write_embeddings_rgb_3857()` from here.
9. **`chalkboard:` and `embed-resources: true` are mutually exclusive.** The chalkboard is
   absent on purpose. Do not "fix" it; if a venue needs it, make the two-line trade documented in
   `README.md` § Delivery and accept folder delivery.
10. **Never commit** `index.html`, `index_files/`, `_qa/`, `.quarto/`, `derived/`, or a copy of
    the 118 MB VIIRS raster. `.gitignore` covers all of them and explains each.
11. **Do not add `__init__.py` under `sources/`.** The vendored modules are imported flat on
    purpose; a package named `code` would shadow Python's own `code` module.
12. **`quarto render` BY FILE**, never `quarto render .` — the latter also builds `outline.md`
    into a page that would then be published.

## Commands

```bash
# render (Quarto only; the deck has no executable cells)
quarto render monitoring-local-development.qmd            # -> index.html, ~21 MB, self-contained

# environment
uv sync                                                   # figures + checks
uv sync --extra qa                                        # adds playwright for the browser tiers

# figures
uv run python scripts/fig-r2-master.py                    # one
uv run python scripts/fig-r2-master.py simple             # a variant argument
uv run python scripts/fig-views-lisa.py sdg7              # a goal slug: sdg1 | sdg7 | sdg13
for f in scripts/fig-*.py; do uv run python "$f"; done     # all

# verification — a change is done only when all of these pass
uv run python scripts/_source_checks.py .                 # Tier S   exits 1 on drift
uv run python scripts/_qa_checks.py .                     # Tier B   diagnostic; read QA SUMMARY
uv run python scripts/_html_checks.py .                   # Tier B'  exits 1 on failure
uv run python scripts/_sync_check.py .                    # snapshot intact
uv run --extra qa python scripts/_browser_checks.py . all  # Tiers A/A'/C  (fonts|shots|pdf|all)

# against the live manuscript, when a project2026e checkout is available
uv run python scripts/_sync_check.py .   --root /path/to/project2026e
uv run python scripts/_source_checks.py . --root /path/to/project2026e

# offline / source-tracking switches
DECK_NO_NETWORK=1     uv run python scripts/fig-pop-raster.py   # refuse the HF fallback
DECK_SOURCE_ROOT=/path/to/project2026e uv run python scripts/fig-r2-master.py
```

## Layout

| Path | Role |
| --- | --- |
| `monitoring-local-development.qmd` | the deck; its front matter fixes the packaging |
| `theme.scss` · `_palette.py` | one palette, two files — always change together |
| `title-slide.html` · `fonts.html` | head/template partials; `fonts.html` carries a postmortem, read it |
| `figures/` · `fonts/` | committed assets; figures are generated, never hand-edited |
| `scripts/` | `_paths` (all path resolution) · `_rasters` `_fourview` `_goals` (shared) · `fig-*` · five checkers |
| `sources/` | frozen snapshot: `code/` `tables/` `notebook-cache/` `data/` + `PROVENANCE.toml` `claims.toml` |
| `numbers.toml` | every asserted number and its source |
| `derived/` | deck-computed output; gitignored, and deliberately not inside `sources/` |

## Definition of done

A change is complete when all of these hold:

- `quarto render monitoring-local-development.qmd` exits 0 with no warnings
- `_source_checks.py .` exits 0
- `_html_checks.py .` exits 0, and reports `artifact: index.html`
- `_qa_checks.py .` reports 0 contrast failures and 0 palette drift
- `_sync_check.py .` exits 0
- if a figure changed: it was regenerated by its script, not edited
- if a number changed: `numbers.toml` was updated in the same change

## Anti-patterns, with the evidence

Each of these has already happened in this project.

- **Declaring `@font-face` in `theme.scss`.** The relative `url()` resolves against the compiled
  stylesheet, finds reveal's own `fonts/` directory, and 404s — so the deck falls back to a system
  font with no error. See the comment at the top of `fonts.html`.
- **Building a private spatial-weights matrix.** `scripts/_fourview.py` once rolled its own
  `KNN(k=6)` and disagreed with the paper for eight days, shipping cluster maps that were wrong by
  up to seven points. Use `spatial_weights.queen_repaired`, and never bypass
  `verify_against_paper()`.
- **Recomputing R² from the out-of-fold series.** The published R² is the mean of per-fold R²,
  not a pooled R² over the concatenated vector; pooled runs consistently higher. Quote the table.
  Pearson *r* is identical under both, which makes it the right alignment cross-check.
- **Deriving a statistic from a warped raster.** `PDO._warp_masked_to` resamples
  nearest-neighbour for display only. Quote the tables.
- **Double rounding.** Re-rounding an already-rounded cell can disagree with rounding the
  full-precision value once, and Tier S will certify the version that contradicts its own figure.
- **Reading a figure count or a figure number from an older document.** Quote labels
  (`fig-views-lisa-sdg1`), never numbers.
- **Treating a large figure diff as a real change.** matplotlib output is not byte-stable across
  versions, including patch versions and including SVG — a bump moves every path coordinate in a
  visually identical chart. `uv.lock` pins the version so `uv sync` rebuilds reproduce the
  committed bytes. Judge figures by `verify_against_paper()` and Tier S, never by the diff size.
- **Applying the parent project's 6×4in/300dpi figure convention.** This deck's conventions are
  its own; see `README.md` § Figures.

## When something fails

- **Tier S fails** → the *deck* is wrong. Fix the slide, or fix the manifest entry.
- **`_sync_check` says UPSTREAM ADVANCED** → the *paper* moved. Decide whether to take the
  change; copy it in, `--freeze`, then rebuild every figure and re-run Tier S.
- **`_sync_check` says SNAPSHOT EDITED LOCALLY** → someone edited the frozen copy. Revert it and
  make the change upstream instead.
- **A figure script raises `_paths.Unavailable`** → read the message; it names the file and every
  location it looked. For the VIIRS raster the remedy is network access or `DECK_SOURCE_ROOT`.
- **The font probe fails** → check `fonts.html` is still loaded via `include-in-header` and that
  each `@font-face` names its file exactly once.
