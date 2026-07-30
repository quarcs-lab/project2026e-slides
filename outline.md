# Outline — Predicting and monitoring local development from outer space

**Deck:** `slides/monitoring-local-development/`
**Format:** conference cut, ~15–20 minutes, **24 slides** (21 content + 2 act dividers + title)
**Status:** rebuilt, rendered and verified 2026-07-28 — Tiers B, B′, S and A/A′/C all pass; both
`beautiful-deck full` Agent audits run (reports in `notes/monitoring-local-development/`).
**Built with:** `/project:beautiful-deck full` · `nightlight` preset, **inverted to dark**
**Supersedes:** `legacy/visible-from-space-conference-20260719/`

This file is kept in sync with the deck. If it disagrees with the `.qmd`, the `.qmd` is right and
this file is a bug.

---

## Q6 — the one sentence the audience leaves with

> What a development goal is *made of* decides whether satellites can see it, and weighting by
> where people live decides how well. Combined, the two views read municipal poverty at
> **0.54 to 0.72** out of sample and find its clusters and traps well enough to target scarce
> effort — but health, gender and justice stay invisible.

## Audience triage

Conference (applied economics / development / geospatial). **Logos 55 · Ethos 30 · Pathos 15.**
Assume the room knows cross-validation and Moran's I but not AlphaEarth, not the Bolivian SDG
atlas, and not why aggregation choice matters. No code on slides. One running example —
**poverty (SDG 1)** — carried from prediction through the range to the cluster map.

## Acronym policy

Spell out *Sustainable Development Goals* on first use; goal **names** in prose ("No Poverty",
"Clean Energy", "Climate Action"). `SDG 1`-style labels survive only inside figure axes, where the
goal number is the identifier. Never "NTL", "DTE", or "LODO" — use *nighttime lights*, *daytime
embeddings*, *department transfer* (`code/labels.py` treats the acronyms as retired).

---

## The arc

Two acts, mirroring the manuscript. The paper's abstract, introduction and conclusion all run
**predict → monitor**, with two findings in each half, and the deck now runs the same way. Slide
numbers are the ones reveal.js shows.

### Opening (1–4)

| # | Archetype | Assertion title | Carries |
|---|---|---|---|
| 1 | Title | *Predicting and monitoring local development from outer space* | Subtitle *Evidence from the Bolivian municipalities*, over the full-bleed orbital background. No date — the talk is reused across venues |
| 2 | Bullets + quote | **Where development data is scarcest, it is needed most** | A census is a snapshot, not a series; 339 municipalities. Names no census year — see *Design decisions* below |
| 3 | Figure `fig-data-layers.png` | **Lights, landscape, and people: three ways to see Bolivia** | All three data layers on one frame. The lights being dark exactly where the embeddings are richest is visible at a glance; the population panel plants the weighting turn |
| 2 | | | *(continued)* The mayor with no current poverty number opens the slide, not the note — it is the deck's one human image and its whole pathos budget |
| 4 | Two-column | **Development is visible from space — but which dimensions?** | Left: 64 numbers per patch, learned with *no* socioeconomic labels; the lights add eight bands. Right: 15 indices from 62 indicators, the two questions the two acts answer, the learner, and the honesty rule — which carries the slide's bold, not the optimizer |

### Act I — *Can satellites read development?* (divider 5; content 6–14)

| # | Archetype | Assertion title | Carries |
|---|---|---|---|
| 5 | Divider (full-bleed) | *Can satellites read development?* | Kicker: **Part one · Prediction** |
| 6 | Figure `fig-nasa-viirs.jpg` | **Nighttime lights offer an opportunity to measure local development** | NASA Black Marble global context. Luminosity is an established proxy, but darkness is ambiguous |
| 7 | Figure `fig-dte-alphaearth.png` | **Daytime embeddings: a new way to measure local development** | Conceptual six-tile workflow. Explicitly illustrative, not a map or a development score. The title says *daytime embeddings*, not "satellite embeddings" — the retired name had survived here alone |
| 8 | Figure `fig-pipeline.svg` | **A satellite sees pixels; an index describes a municipality** | **New.** The pixel-to-municipality bridge, and the aggregation fork that slides 10–12 then cash in |
| 9 | Incremental (`.vcenter`) | **What a goal is made of decides if satellites see it** | Things you can see vs things you cannot. Stated *before* the evidence, as a claim to be tested |
| 10 | Figure `fig-r2-master-simple.svg` | **On the raw average, the lights win the goals we care about most** | Fifteen goals, **simple municipal mean**. The lights lead on poverty (0.52 vs 0.38) and energy (0.51 vs 0.32); the embeddings lead 8 of 15 overall, which is why the title claims the two goals rather than the scoreboard |
| 11 | Quote + figure `fig-data-layers.png` (`.figure-with-quote`) | **Most of a municipality is empty — weight where people live** | The methodological turn. Weighting lifts the embeddings 0.29 → 0.41; the lights slip 0.25 → 0.22. **Quote above the figure**, so the claim can never be pushed off the bottom by the image |
| 12 | Figure `fig-r2-master.svg` | **Weight where people live, and the embeddings pull ahead** | Same fifteen goals, same axis as slide 10, now **population-weighted**. 8 → 14, with the source line conceding that the lead clears fold noise on only 5 of the 15 |
| 13 | Incremental (`.vcenter`) | **The contribution is not one number — it is a map of legibility** | The verdict on slide 9's claim: physical goals 0.69/0.63/0.63/0.58; social goals −0.05/0.27/0.28; Reduced Inequalities the best-read *of* the social goals at 0.57; and Life on Land at 0.10 as the goal weighting **costs** us |
| 14 | Figure `fig-legibility-clustering.svg` | **Legibility has a spatial signature** | **New.** The hinge into Act II: the goals that cluster most are the goals the imagery reads, ρ = 0.67. Carries the paper's own hedge — an observation, not a result |

### Act II — *Which goals can we map — and how well?* (divider 15; content 16–22)

| # | Archetype | Assertion title | Carries |
|---|---|---|---|
| 15 | Divider (full-bleed) | *Which goals can we map — and how well?* | Kicker: **Part two · Monitoring**. The divider used to ask *"Can we draw the map?"* and was then followed by three R² charts before the first map arrived — a promise the act broke for three minutes. It now asks the question slides 16–18 actually answer |
| 16 | Stat card + list | **Together, the two views read poverty best of all** | `0.72` in a stat card labelled *the upper bound of a 0.54–0.72 range*, so the headline number carries its scope limit in the same breath. 64 + 8 features, one consistent weighting. Three goals pass 0.60; Zero Hunger is the 0.59 near miss |
| 17 | Figure `fig-combined-range.svg` | **How you test decides what you get: 0.54 to 0.72** | The estimation range for all fifteen goals. The gap is the reach of spatial autocorrelation, and it cuts both ways |
| 18 | Figure `fig-transfer-floor.svg` | **Under the hard test, only the fusion never collapses** | **New.** The deck's only evidence that combining beats *both* singles — and at the lower bound, the regime not flattered by leakage. The title claims what the figure shows: on climate action the fusion is a hair behind the embeddings alone, while the lights collapse to −0.28 |
| 19 | Figure `fig-views-lisa-sdg1.png` | **The combined view recovers the geography of poverty** | Agreement 77 / 78 / 80; hot-coldspots 53 / 80 / 75 of 104; Moran's *I* actual 0.50, lights 0.33, embeddings 0.60, combined 0.50. Every panel header now prints all three, because when it printed only the hot/coldspot share the figure appeared to **refute its own title** — see *Audit fixes* below |
| 20 | Figure `fig-views-lisa-sdg7.png` | **Clean energy: the lights read the level, not the pattern** | The sharpest illustration that prediction ≠ monitoring: lights reach *r* = 0.73 on the level but place only 49% of the 91 hot/coldspots. Embeddings lift to 83% / 75%, combined 82% / 70% |
| 21 | Figure `fig-views-lisa-sdg13.png` | **Climate action: it finds the clusters — and overstates them** | Best recovery of the three (combined 92%, embeddings 91% of 124) — but Moran's *I* 0.84 and 0.81 against an actual 0.65, and neither embedding view recovers any of the six spatial outliers |
| 22 | Devil's advocate (`.incremental`) | **The lead is real, but smaller than it looks** | Five objections, revealed one at a time. See *Reversals* below — this slide's fifth bullet was factually wrong before this round |

### Close (23–24)

| # | Archetype | Assertion title | Carries |
|---|---|---|---|
| 23 | Closing (full-bleed) | **Satellites see the material geography of development** | The decision first — let imagery carry the legible goals between survey rounds, spend survey money on the rest — then the limit. Says *justice stays invisible, health and gender barely register*, because at 0.27 and 0.28 those two are weakly read, not invisible. A source line marks the forward step as a **projection, not a measurement** |
| 24 | Sign-off (full-bleed, centred) | **Thank you** | `carlos-mendez.org` |

**If it runs long,** slide 20 (clean energy) is the first cut: it is the goal where nighttime lights
alone nearly suffice, so it carries the least new information, and cutting it keeps the poverty
worked example and the climate contrast that makes the argument. Slide 8 (the pipeline) is second.
**Never cut 14 or 18** — they are the two beats that make the fusion argument.

---

## What changed on 2026-07-28, and why

The deck was last touched 2026-07-20; `index.qmd` was last edited 2026-07-28. The manuscript moved
underneath it in four ways.

### 1. The paper was retitled, and the spine was rebuilt to match

It is now *Predicting and monitoring local development from outer space*. The deck's cover, footer
and whole structure said *Monitoring…*, which under-sold half the talk. Act I is now explicitly
prediction and Act II explicitly monitoring, and each act delivers the two findings the paper's own
introduction assigns to that half.

### 2. Every spatial statistic was stale — and this was the blocking defect

On 2026-07-20 the project switched its spatial weights from `KNN(k=6)` to queen contiguity
(`code/spatial_weights.queen_repaired`). `scripts/_fourview.py` kept building its own
`KNN.from_dataframe(g, k=6)`, and its comment claiming to mirror
`notebooks/monitoring-views-comparison.qmd` had become false. So the three LISA maps and every
Moran's *I* and hot/coldspot share on the map slides were computed on a different neighbour matrix
than the paper's. This is the open item that had been carried in five consecutive handoffs.

The `k = 6` was a **misreading**: six is the rounded *mean queen cardinality*, used only to
reconnect the one island (Coipasa, Oruro), never as a global rule.

`_fourview.py` now calls `queen_repaired`, and `verify_against_paper()` asserts every recomputed
statistic against `tables/tbl-views-comparison-<slug>.csv` **before the figure is written**. All
nine per-goal checks pass. The deck can no longer drift from the paper in silence.

### 3. One narrative claim reversed

The steel-man slide asserted *"embeddings edge combined on all three goals"*. Under queen
contiguity that is false. The combined predictor now leads on the **full LISA classification** for
SDG 1 (79.6 vs 77.6) and SDG 13 (80.5 vs 79.1), and on hot/coldspot recovery for SDG 13 (91.9 vs
91.1). The embeddings keep a hot/coldspot edge on SDG 1 (79.8 vs 75.0) and SDG 7 (74.7 vs 70.3)
only. The bullet now says exactly that, and slide 19 volunteers the concession rather than waiting
for the objection.

### 4. Three new beats the manuscript had gained

- **Slide 8, the pipeline.** *World Development*'s readers are development economists, not
  remote-sensing specialists, and the talk claimed numbers from a raster pipeline it never showed.
- **Slide 14, clustering vs legibility.** New in the paper (§4, Spearman ρ = 0.67) and the natural
  bridge into monitoring: it explains *why* the map works.
- **Slide 18, the transfer floors.** §5.1 gained per-view lower bounds. This is the deck's only
  evidence that the fusion beats *both* singles rather than splitting the difference.

### Two defects cleared on the way

`outline.md` and `numbers.toml` both carried **committed** `<<<<<<< Updated upstream` merge-conflict
markers, from commit `36b45a1`. The manifest was therefore unparseable, so Tier S had not been able
to run at all. And 8 of its 12 `index.qmd` regexes no longer matched: the prose they keyed on had
been rewritten. Both files were rebuilt rather than patched.

---

## Audit fixes (2026-07-28, after the two `full`-mode audits)

Both audits ran against the rendered screenshots and both independently found the same blocker,
which is the strongest signal in either report.

**The two blockers.**

1. **Slide 11 overflowed.** At the theme's default `64vh` image cap, the title + kicker + figure +
   two-line pull-quote did not fit: the second of the deck's two contrasting numbers — *the lights
   slip from 0.25 to 0.22* — was sliced by the bottom frame edge and printed through the footer
   band. `theme.scss`'s cap was sized for slides that "carry no bullets and a single-line source";
   kicker *and* quote was never budgeted. **No static checker can see this** — every element fits
   on its own, and only the composition fails. Fixed with a new `.figure-with-quote` class
   (340px, in pixels not vh, for the reasons `.portrait-figure` records) **and** by putting the
   quote *above* the figure, so the claim cannot be pushed off the slide by the image.
2. **Slide 19's figure appeared to refute its title.** The panel headers printed one statistic —
   the hot/coldspot share — and it read *(c) embeddings 80%* against *(d) combined 75%*, under a
   title asserting the combined view recovers the geography best. The evidence that supports the
   title (80% agreement over the *full* classification, and Moran's *I* 0.50 against an actual
   0.50) was only in the speaker notes. Every panel now prints all three, on all three map slides.

**Framing corrections.** Two claims on slide 13 were wrong and the deck refuted them itself: Life
on Land was filed under "assembled from social and administrative records" when the paper is
explicit that its weakness comes from population weighting discarding unsettled forest; and
Reduced Inequalities was called *the one* socially defined goal the imagery reads, forty seconds
before slide 14 puts Quality Education at 0.43 on screen. Slide 10's title claimed the lights
"win" when the scoreboard is 8–7 to the embeddings. Slide 16's speaker note claimed the 0.60 gate
was "stated in advance rather than chosen after seeing the maps" — which nothing in the repo
establishes, and which is the selected-maximum anti-pattern; it now says what the paper says, that
the threshold is a methodological choice. Slide 18's title was a comparative across regimes when
only one regime is shown, and visibly false on one of the three goals.

**Encoding.** Amber was doing four jobs; it is now reserved for the nighttime lights, so the 0.60
rule and the Spearman annotation moved to neutral ink. The `.bignum` was set in the *embeddings*
blue while stating a *combined-predictor* number, and is now ink. The two dumbbells gained
square-vs-circle markers — the deck's three series sit 13/255 apart in greyscale, so hue was the
only channel — and the combined bars on slide 18 gained a hatch, because under deuteranopia the
green and the embeddings blue both resolve to light purples. `fig-pipeline`'s step boxes were
drawn at 1.27:1 fill and 2.11:1 edge, so the shape grammar its caption teaches was invisible; its
arrows also arrived vertically in a left-to-right chart and stacked two arrowheads on one corner.

**Not taken, deliberately.** Cutting slide 6, merging the clean-energy and climate map slides,
adding a cross-validation protocol slide, replacing slide 13 with an annotated dumbbell, and
deleting the *Thank you* slide were all proposed. Each changes the 24-slide structure the author
approved, so they are recorded here rather than applied. **One is worth acting on before the
talk:** the rhetoric audit measured the speaker notes at ~2,600 words, which is about 18.6 minutes
of pure speech at 140 wpm with no pauses and no figure walks. The notes were trimmed this round
but not by enough to guarantee a 20-minute delivery. The cut ladder above is the lever.

Full reports: `notes/monitoring-local-development/monitoring-local-development_{rhetoric,graphics}-audit_20260728.md`.

---

## Figures

Twelve figures on slides, from ten scripts. Three are new this round.

```bash
uv run python scripts/fig-r2-master.py  simple    # -> figures/fig-r2-master-simple.svg (raw)
uv run python scripts/fig-views-lisa.py sdg13     # -> figures/fig-views-lisa-sdg13.png
```

| Slide | File | Source |
|---|---|---|
| 1 | `fig-title-orbital-monitoring.png` | Generated cover art, set as the background in `title-slide.html`; provenance in `figures/README.md` |
| 3, 11 | `fig-data-layers.png` | All three rasters on one shared bbox via `scripts/_rasters.py`: VIIRS band `average` (gitignored ~118 MB, HF-mirrored), the **committed 11 MB** embeddings PCA composite, and the committed GHS-POP grid |
| 6 | `fig-nasa-viirs.jpg` | NASA Earth at Night / Black Marble; broad visual context, not the study raster |
| 7 | `fig-dte-alphaearth.png` | Built-in image-generation workflow graphic; prompt, scientific-status disclosure and alt text in `figures/README.md` |
| **8** | **`fig-pipeline.svg`** | **New.** `scripts/fig-pipeline.py` — no data reads; a hand-laid flow chart |
| 10 | `fig-r2-master-simple.svg` | `tables/tbl-popweighting-master.csv`, the **simple-mean** columns |
| 12 | `fig-r2-master.svg` | Same table, the **pop-weighted** columns. Shares slide 10's goal order and x-axis so the two read as a before/after pair |
| **14** | **`fig-legibility-clustering.svg`** | **New.** `tables/tbl-outcomes-descriptives.csv` (`Moran's I`) ⋈ `tables/tbl-popweighting-master.csv` (`R² daytime embeddings (pop-weighted)`) on `Goal index` |
| 17 | `fig-combined-range.svg` | `tbl-mon-comprehensive.csv` (lower) ⋈ `tbl-mon-featureset-comparison.csv` `Combined (pop-weighted)` (upper) |
| **18** | **`fig-transfer-floor.svg`** | **New.** `tables/tbl-views-lodo.csv` (lights, embeddings) + `tables/tbl-mon-comprehensive.csv` (combined) |
| 19, 20, 21 | `fig-views-lisa-sdg{1,7,13}.png` | `data/predictions/sdg{1,7,13}_fourview_2017.csv`, exported by `scripts/_fourview.py` from `.notebook-cache/sdg*_{ntlw8,weighted,combow}.pkl` key `oof_pred`. **Queen contiguity** via `code/spatial_weights.queen_repaired`, `Moran_Local(permutations=999, seed=12345)`, p < 0.05 |

**Retired but kept on disk:** `fig-popweighting-flip.svg`, the three `fig-views-choropleth-sdg*.png`
levels maps, and the three single-layer rasters (`fig-{ntl,emb,pop}-raster.png`) with their thin
wrapper scripts around `_rasters.py`.

No model is re-fitted — the four-view panels read frozen out-of-fold predictions, and
`_fourview._from_cache()` asserts each cached `y_true` matches the actual series element-wise before
it will plot anything. Row alignment is positional; that assertion is the only thing between a
correct map and a silently scrambled one.

`scripts/_goals.py` is the single naming authority (`Poverty (SDG 1)`, never `SDG1`).
`_fourview.GOALS` carries the per-goal cluster wording — "Poverty trap" is meaningful on the poverty
map and nonsense on the energy one.

### Three assertions that stop the figures going stale

Each new script fails rather than shipping a wrong figure:

- `fig-views-lisa.py` → `_fourview.verify_against_paper()`: every Moran's *I*, LISA agreement and
  hot/coldspot share must reproduce `tables/tbl-views-comparison-<slug>.csv` at that table's own
  precision.
- `fig-legibility-clustering.py`: recomputes Spearman ρ and asserts it rounds to the published 0.67.
- `fig-transfer-floor.py`: asserts all nine cells against the three-decimal values the tables store.

---

## Design decisions worth keeping

Carried forward from earlier rounds; each was arrived at the hard way.

- **The census motivation names no year.** An earlier version asserted "Bolivia's last census was
  in 2012"; Bolivia has since run one, so the sentence was false as spoken. The argument never
  depended on any particular census being old — it depends on censuses being infrequent, which
  stays true after every new one.
- **The nighttime-lights stretch departs from the manuscript's, deliberately.** The VIIRS annual
  mean carries a noise floor near 0.15–0.20 nW (median 0.166), so the manuscript's `vmin=0` recipe
  renders the whole country as a flat wash on a dark full-bleed slide. `_rasters.py` starts the ramp
  at **0.17** — just above the in-country median, so background clips to transparent — with a
  **named constant cap of 1.5 nW**, not a percentile (p99 = 0.775 against p99.9 = 18.87, a 24× jump
  across 0.9% of pixels, so a percentile would lurch on any mask change). Same data, same band;
  display only.
- **The range figure's legend sits upper LEFT.** Lower-right crosses the 0.60 reference line;
  lower-left covers the Land and Institutions rows, and hiding data is worse than crossing a guide
  line; and no legend at all — which shipped once — left hollow-vs-filled explained only in a 0.46em
  caption. Upper left is empty by construction, because goals are sorted by upper bound.
- **The raster panels draw the 339 municipality boundaries, not the nine departments**, as a thin
  translucent mesh under a subtle national border, with no region names. Municipalities are the unit
  of analysis. The manuscript's own `code/plot_data_overview.py` still shows departments and was
  deliberately left alone.
- **Figures save transparent, not canvas-coloured.** The slide background is a gradient; an opaque
  facecolor matching `$bg` ships as a visible flat rectangle sitting on top of it.
- **`@font-face` lives in `fonts.html`, never in `theme.scss`.** Quarto compiles the theme into
  `_files/libs/revealjs/dist/theme/`, where a relative `url()` resolves against *reveal's* own
  `theme/fonts/` directory — so the deck silently falls back to a system font while the path looks
  fine. The deck did exactly that for a while.
- **`.portrait-figure` is currently unreferenced** but kept, because the three single-layer raster
  scripts are kept. Its cap is in **pixels, not vh**: reveal scales a fixed 1280×720 canvas by CSS
  transform, and `vh` resolves against the real viewport *before* that transform.
- **Tier B palette drift of 0 is luck, not compliance.** Magma, viridis and a PCA false-colour
  composite are perceptual data ramps, not brand colours, and none is in `theme.scss`. The check
  survives them only because it samples the twelve most common colours of an 80×80 downsample and
  skips anything neutral or near the canvas. If a future raster fills more of its frame, expect
  drift lines and read them as *expected* for the ramp. What must stay on-palette is everything
  *around* the raster.

### Two rounding traps this deck has already fallen into

- **Climate action's department-transfer bound.** `tables/tbl-mon-comprehensive.csv` stores
  **0.435**, whose float representation is fractionally below the tie, so `round(0.435, 2)` returns
  **0.43**. The true value in `.notebook-cache/sdg13_combow_lodo.pkl` is 0.435304 and the manuscript
  correctly prints **0.44**. `fig-transfer-floor.py` therefore labels that one bar from the paper's
  rendering, and `numbers.toml` sources it from `index.qmd`, not from the cell — because Tier S
  re-rounds the cell and would happily certify a caption contradicting the figure above it.
- **The lights' simple mean.** The table stores exactly 0.255 and `round(0.255, 2)` returns 0.26,
  while the manuscript prints 0.25. Also pinned to the paper's prose.

---

## Verification

```bash
uv run python slides/monitoring-local-development/scripts/_qa_checks.py     slides/monitoring-local-development
uv run python slides/monitoring-local-development/scripts/_html_checks.py   slides/monitoring-local-development
uv run python slides/monitoring-local-development/scripts/_source_checks.py slides/monitoring-local-development
uv run --with playwright python slides/monitoring-local-development/scripts/_browser_checks.py \
    slides/monitoring-local-development all
```

Result on 2026-07-28, after the audit fixes:

| Tier | Surface | Result |
|---|---|---|
| B | source: contrast, figure fit, overflow, palette drift | 0 contrast failures, 0 palette drift, **1 overflow-risk slide** (22, the devil's advocate, 541 chars against a 480 heuristic — accepted, see below) |
| B′ | rendered HTML | **PASS**, 0 failures |
| S | every number against its declared source | **PASS**, 0 unresolved, 0 noted — all 53 numbers traced |
| A′ / A / C | live page | 24 screenshots, an 11.1 MB PDF with backgrounds, no math to verify |
| Rhetoric audit | arc, titles, honesty rules, claim–evidence match | PASS-WITH-FIXES → **fixes applied** |
| Graphics audit | legibility, colour discipline, encoding honesty | PASS-WITH-FIXES → **fixes applied** |

**The one accepted flag.** Slide 22 is the steel-man, and it is bullet-heavy by design: five
objections revealed one at a time by `.incremental`, so the room never sees 541 characters at once.
It was trimmed from 737 this round. The same slide carried this flag in the previous deck.

⚠ **Run the screenshots LAST.** The graphics audit caught the `_qa/` PNGs having been written four
minutes before two of the three new figures were last regenerated, so it was reviewing a build that
no longer existed — it happened to show a defect already repaired, and could as easily have hidden
a new one. Regenerate figures → render → screenshot → run the checkers, in that order, every time.

---

## History

Earlier rounds are recorded in `handoffs/`, not here — this file used to accrete a dated revision
log per round and had grown to 35 KB with unresolved merge-conflict markers inside it. The durable
knowledge from those rounds is in *Design decisions worth keeping* above.

| Round | Handoff |
|---|---|
| Rebuilt to the predict → monitor arc; queen-contiguity fix | `handoffs/20260728_*.md` (this round) |
| Storyline sharpened; monitoring section trimmed to LISA-only | `handoffs/20260719_2125.md` |
| Data-layer slides consolidated to one three-panel slide | `handoffs/20260719_1746.md` |
| Dark-theme visual redesign; bundled fonts | `handoffs/20260719_1620.md` |
| First build of this deck | `handoffs/20260719_0930.md` |
