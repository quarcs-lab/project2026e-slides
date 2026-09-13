# Outline — Predicting and monitoring local development from outer space

**Deck:** `slides/monitoring-local-development/`
**Format:** conference cut, **20 minutes**, **30 sections** — 22 on the linear path (18 content
+ 3 act dividers + title) and 8 in an appendix that sits after the Thank-you slide.
**Status:** re-cut for a 20-minute international conference 2026-09-12 — Tiers B, B′, S and the
snapshot check all pass; every slide measured in-browser at 720px, none overflows. Tier A/A′/C did
not run this round (`uv sync --extra qa` cannot build llvmlite under Python 3.14 on this machine);
the overflow sweep was done directly in Chrome instead. Earlier: rebuilt and audited 2026-07-28,
both `beautiful-deck full` Agent audits run (reports in `notes/monitoring-local-development/`).
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

International conference, **applied and development economists**. **Logos 55 · Ethos 30 ·
Pathos 15.** Assume the room knows cross-validation and reads a regression table, but knows
**nothing** about satellite embeddings, nothing about the Bolivian SDG atlas, and does not yet see
why aggregation choice matters. That assumption is what the four *How we measure it* slides exist
for — the 2026-07-28 cut assumed a geospatial room and asserted the data construction instead of
explaining it. No code on slides. One running example — **poverty (SDG 1)** — carried from
prediction through the range to the cluster map.

**Bullet rule, binding.** One sentence or one phrase per bullet. Never two sentences. A bullet that
needs a second sentence is either two bullets or a speaker note.

## Acronym policy

Spell out *Sustainable Development Goals* on first use; goal **names** in prose ("No Poverty",
"Clean Energy", "Climate Action"). `SDG 1`-style labels survive only inside figure axes, where the
goal number is the identifier. Never "NTL", "DTE", or "LODO" — use *nighttime lights*, *daytime
embeddings*, *department transfer* (`code/labels.py` treats the acronyms as retired).

---

## The arc

Two acts, mirroring the manuscript. The paper's abstract, introduction and conclusion all run
**predict → monitor**, and the deck runs the same way. What the 2026-09-12 cut adds in front of
them is a third block, *How we measure it*, because an economics room cannot judge the results
until it knows what the outcome variable is and what an embedding is.

Slide numbers are the ones reveal.js shows, counted over all 30 sections.

### Opening (1–3)

| # | Archetype | Assertion title | Carries |
|---|---|---|---|
| 1 | Title | *Predicting and monitoring local development from outer space* | Subtitle *Evidence from the Bolivian municipalities*, over the full-bleed orbital background. No date — the talk is reused across venues |
| 2 | Bullets + quote | **Where development data is scarcest, it is needed most** | The mayor with no current poverty number — the deck's one human image and its whole pathos budget. A census is a snapshot, not a series; 339 municipalities. Names no census year, see *Design decisions* |
| 3 | Incremental | **Two questions, and they are not the same question** | Read vs map, stated as the two things the two acts answer. Replaces the old two-column slide 4, whose left half is now slides 5–7 and whose right half is this |

### Block 0 — *How we measure it* (divider 4; content 5–9) — **new in the 2026-09-12 cut**

| # | Archetype | Assertion title | Carries |
|---|---|---|---|
| 4 | Divider (full-bleed) | *How we measure it* | Kicker: **The data and the method, in four slides** |
| 5 | `.chain` + `.goal-grid` | **The prediction targets: 15 development goals** | **New.** The outcome variable, said out loud: 62 indicators from official statistics → 15 goal indices, each 0–100 with higher better → one value per municipality, 2017. The right column names all fifteen goals as tiles, in SDG order and ungrouped (the manuscript dropped its taxonomy), using `_goals.SHORT` so they match the R² tick labels. The source line cites the Municipal Atlas (Andersen et al., 2020) and plants the bound on circularity (two of 62 come from space) |
| 6 | Figure `fig-nasa-viirs.jpg` | **Nighttime lights: the proxy economists already know** | NASA Black Marble global context. Retitled to name the audience's existing knowledge rather than announce an opportunity |
| 6b | Figure `fig-ntl-sdg1-scatter.svg` | **Example: Nighttime lights and SDG 1 (no poverty)** | **New, inserted after the 2026-09-12 cut — it shifts every slide number from here on by one, and the numbers in this file and in `numbers.toml` have not been renumbered.** The baseline made concrete: a plain scatter of the 339 municipalities, log population-weighted radiance against the poverty index, with the OLS slope and an in-sample R² of 0.54 printed on it. Motivational only; the wide scatter among the dim municipalities is the opening the embeddings walk through |
| 7 | Bullets + figure `fig-dte-alphaearth.png` (`.figure-with-quote`) | **A satellite embedding: one year of images, summarised** | **Rewritten.** Absorbs the old slide 7. The three bullets are the explainer; the middle one — *think of it as a fixed-effect vector for a place* — is the analogy that lands for this room |
| 8 | Quote + figure `fig-pipeline.svg` (`.figure-lede`) | **From pixels to municipalities** | The pixel-to-municipality bridge and the aggregation fork that slides 11–13 cash in. Kicker dropped and the quote cut to one line so the chart clears 430px and its internal labels are readable from the back |
| 9 | `.cards` + bullets | **How we test: out of sample, two ways** | **New.** Random folds vs department transfer, side by side, so the reader already knows what two bounds mean before slide 18 shows them. Ends on *no place ever helps predict itself* |

### Act I — *Can satellites read development?* (divider 10; content 11–15)

| # | Archetype | Assertion title | Carries |
|---|---|---|---|
| 10 | Divider (full-bleed) | *Can satellites read development?* | Kicker: **Part one · Prediction** |
| 11 | Figure `fig-r2-master-simple.svg` | **On the raw average, the lights win the headline goals** | Fifteen goals, **simple municipal mean**. The lights lead on poverty (0.52 vs 0.38) and energy (0.51 vs 0.32); the embeddings lead 8 of 15. Title shortened to one line — at 62 characters it wrapped and pushed the source caption onto the footer |
| 12 | Quote + figure `fig-data-layers.png` (`.figure-with-quote`) | **Most land is empty — weight where people live** | The methodological turn. Weighting lifts the embeddings 0.29 → 0.41; the lights slip 0.25 → 0.22. **Quote above the figure**, so the claim can never be pushed off the bottom by the image |
| 13 | Figure `fig-r2-master.svg` | **Weight where people live — the embeddings pull ahead** | Same fifteen goals, same axis as slide 11, now **population-weighted**. 8 → 14, with the source line conceding the lead clears fold noise on only 5 of the 15 |
| 14 | Incremental (`.vcenter`) | **What a goal is made of decides whether satellites see it** | **Merged** from the old slides 9 and 13: the claim and its evidence in one beat. Carries two numbers only — poverty 0.69 and institutions −0.05. The other seven values moved to appendix slide 26 |
| 15 | Figure `fig-legibility-clustering.svg` | **Legibility has a spatial signature** | The hinge into Act II: the goals that cluster most are the goals the imagery reads, ρ = 0.67. Carries the paper's own hedge — an observation, not a result |

### Act II — *Which goals can we map — and how well?* (divider 16; content 17–20)

| # | Archetype | Assertion title | Carries |
|---|---|---|---|
| 16 | Divider (full-bleed) | *Which goals can we map — and how well?* | Kicker: **Part two · Monitoring** |
| 17 | Stat card + bullets | **Together, the two views read poverty best of all** | `0.72` in a stat card labelled *the upper bound of a 0.54–0.72 range*, so the headline number carries its scope limit in the same breath. 64 + 8 features, one consistent weighting. Three goals pass 0.60; Zero Hunger is the 0.59 near miss, in the notes |
| 18 | Figure `fig-combined-range.svg` | **How you test decides what you get: 0.54 to 0.72** | The estimation range for all fifteen goals. The gap is the reach of spatial autocorrelation, and it cuts both ways. Slide 9 has already taught the two protocols, so this slide no longer has to |
| 19 | Figure `fig-transfer-floor.svg` | **Under the hard test, only the fusion never collapses** | The deck's only evidence that combining beats *both* singles — and at the lower bound. On climate action the fusion is a hair behind the embeddings alone, while the lights collapse to −0.28 |
| 20 | Figure `fig-views-lisa-sdg1.png` | **The combined view recovers the geography of poverty** | Agreement 77 / 78 / 80; hot-coldspots 53 / 80 / 75 of 104; Moran's *I* actual 0.50, lights 0.33, embeddings 0.60, combined 0.50. Every panel header prints all three — see *Audit fixes* |

### Close (21–22)

| # | Archetype | Assertion title | Carries |
|---|---|---|---|
| 21 | Closing (full-bleed) | **Satellites see the material geography of development** | The decision first — let imagery carry the legible goals between survey rounds, spend survey money on the rest — then the limit. Three one-sentence paragraphs instead of the old two long ones. A source line marks the forward step as a **projection, not a measurement** |
| 22 | Sign-off (full-bleed, centred) | **Thank you** | `carlos-mendez.org` |

### Appendix (divider 23; content 24–30) — **new in the 2026-09-12 cut**

Not part of the twenty minutes. Reached with the right arrow from *Thank you*, or by pressing `M`
and jumping straight to the slide a questioner is asking about.

| # | Archetype | Assertion title | Carries |
|---|---|---|---|
| 23 | Divider (full-bleed) | *Appendix* | Kicker: **Backup slides · not part of the twenty minutes** |
| 24 | Incremental | **Objections, answered — one of two** | The first three of the old slide 22's five objections. Split across two slides so each bullet is an objection plus a single-clause answer rather than two sentences |
| 25 | Incremental | **Objections, answered — two of two** | Circularity and "combining always wins?", plus the bounded-circularity count. Carries the long note the old slide 22 carried |
| 26 | Bullets (`.vcenter`) | **The full legibility ladder** | The seven R² values cut from slide 14: 0.63 / 0.63 / 0.58 read well, 0.27 / 0.28 barely, Reduced Inequalities 0.57 the best-read social goal, Life on Land 0.10 the goal weighting **costs** us |
| 27 | Figure `fig-views-lisa-sdg7.png` | **Clean energy: the lights read the level, not the pattern** | Was slide 20. Lights reach *r* = 0.73 on the level but place only 49% of the 91 hot/coldspots. Embeddings lift to 83% / 75%, combined 82% / 70% |
| 28 | Figure `fig-views-lisa-sdg13.png` | **Climate action: it finds the clusters — and overstates them** | Was slide 21. Best recovery of the three (combined 92%, embeddings 91% of 124) — but Moran's *I* 0.84 and 0.81 against an actual 0.65, and neither embedding view recovers any of the six spatial outliers |
| 29 | Figure `fig-data-layers.png` | **Lights, landscape, and people: three ways to see Bolivia** | Was slide 3. The three-layer frame, kept for the "what does an embedding map look like?" question. The figure is still inlined twice (here and on slide 12) — that duplication is ~3.6 MB of the 21 MB artifact and is deliberate |
| 30 | Bullets (`.vcenter`) | **How the estimate is produced** | **New.** Random forest, Optuna TPE, nested CV, and the mean-of-per-fold-R² convention — the methods detail slide 9 deliberately does not carry |

**If it runs long,** slide 6 (the NASA lights context) is the first cut: it is the one slide whose
content this audience already knows, and it carries no result. Slide 8 (the pipeline) is second.
**Never cut 15 or 19** — they are the two beats that make the fusion argument. **Never cut 5, 7 or
9** — they are why this cut exists.

---

## What changed on 2026-09-12, and why

The 2026-07-28 deck was written for a room that already knew what a satellite raster was. This cut
is for applied economists in a hard 20-minute slot, and three things had to change.

**1. The data and the method got their own block (slides 4–9).** Three explanations the old deck
either skipped or compressed into a bridge:

- *What we predict is not satellite data* (5) — the outcome variable is an official index built
  from 62 census and administrative indicators. The old deck said this in half a bullet inside a
  two-column slide. For this audience it is the first thing that has to be true.
- *A satellite embedding: one year of images, summarised* (7) — the old slide 7 showed the
  AlphaEarth workflow figure and left the viewer to infer what an embedding is. It now says it, and
  offers the fixed-effect analogy.
- *How we test: out of sample, two ways* (9) — the two bounds used to be explained for the first
  time in slide 17's speaker notes, three slides after the deck started quoting both of them.

Slides 5 and 9 are **HTML/CSS in the `.qmd`**, using the new `.chain` and `.cards` primitives in
`theme.scss`. No new figure script, and no new number: every value on them was already declared.

**2. Eight slides left the linear path, none was deleted.** The devil's advocate slide, the clean
energy and climate action cluster maps, and the three-layer opener all moved to the appendix, where
`M` reaches them in one keystroke during questions. Old slides 9 and 13 merged into slide 14.

**3. Every bullet is now one sentence or one phrase.** The old slides 2, 4 and 22 each carried
bullets of two full sentences. Slide 22 was also the deck's only Tier B overflow flag (541 body
chars against a 480 heuristic); split across appendix slides 24 and 25, that flag is gone and
`_qa_checks.py` now reports **0 overflow-risk slides**.

Consequential smaller fixes, each measured rather than guessed:

- **Three titles shortened.** *On the raw average…*, *Most of a municipality is empty…* and *Weight
  where people live, and…* each wrapped to two lines at 34px, which pushed their `.source` caption
  onto the footer band — 738px measured against a 720px slide. Shortened, all three fit.
- **`.figure-lede` added to `theme.scss`.** The pipeline chart was capped at 340px by
  `.figure-with-quote` and its internal labels were unreadable at distance; removing the cap pushed
  its lowest box under the footer. 430px is the measured fit for title + one-line quote + footer.
- **Speaker notes rewritten**, 2,586 → **1,696 words** on the linear path, about 12 minutes of pure
  speech, leaving roughly 8 for pauses, figure walks and the walk-on. This was the one open action
  item the 2026-07-28 outline flagged and did not close. The appendix carries a further 787 words
  that are Q&A material, not spoken.
- **`numbers.toml` `claim` labels renumbered** to the 30-section deck. They are documentation only —
  Tier S matches on the bare token, deck-wide — but they are the map a reviewer uses.

### Not done, deliberately

- **No figure was regenerated.** `fig-pipeline.svg` is the one figure that is genuinely too dense
  for this audience and it was the plan's candidate for simplification, but `uv sync` cannot build
  `llvmlite` under Python 3.14 on this machine, so matplotlib is unavailable and rule 1 forbids
  `pip install`. The slide was fixed by layout instead. `fig-r2-master*.svg` and
  `fig-legibility-clustering.svg` also carry fifteen labelled goals each and are dense — but both
  *are* the result, and thinning them risks the claim. Flagged, not changed.
- **`.vcenter` was left inert.** Reveal's own `section { display: block }` outranks the theme's
  `.reveal .slide.vcenter { display: flex }`, so slides carrying that class are top-aligned like
  every other slide. Making it work would restyle slides the author has already approved, and the
  deck's void is closed by the footer band and the surfaces, not by re-centring — see
  `theme.scss` lines 74–78.

---

## What changed on 2026-07-28, and why

> **Slide numbers below, and in every section after this one, are the 2026-07-28 deck's 24-slide
> numbering.** They are left as they were written rather than renumbered, because the reasoning is
> about what was decided at the time. The *arc* table above is the current map.

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

Twelve figures on slides, from ten scripts. **No figure changed in the 2026-09-12 cut** — only
which slide each one sits on. See *Not done, deliberately* above for why `fig-pipeline.svg` was not
simplified even though it is the one that most needed it.

```bash
uv run python scripts/fig-r2-master.py  simple    # -> figures/fig-r2-master-simple.svg (raw)
uv run python scripts/fig-views-lisa.py sdg13     # -> figures/fig-views-lisa-sdg13.png
```

| Slide | File | Source |
|---|---|---|
| 1 | `fig-title-orbital-monitoring.png` | Generated cover art, set as the background in `title-slide.html`; provenance in `figures/README.md` |
| 12, 29 | `fig-data-layers.png` | All three rasters on one shared bbox via `scripts/_rasters.py`: VIIRS band `average` (gitignored ~118 MB, HF-mirrored), the **committed 11 MB** embeddings PCA composite, and the committed GHS-POP grid |
| 6 | `fig-nasa-viirs.jpg` | NASA Earth at Night / Black Marble; broad visual context, not the study raster |
| 6b | `fig-ntl-sdg1-scatter.svg` | `scripts/fig-ntl-sdg1-scatter.py` — `data/sdg/sdg.csv` ⋈ `data/nighttimeLights/bolivia_ntl_pop_weighted_2017.csv` on `asdf_id`. The lights table is **not vendored** in `sources/`, so this is the second figure (with `fig-ntl-raster.py`) that needs network access or `DECK_SOURCE_ROOT` |
| 7 | `fig-dte-alphaearth.png` | Built-in image-generation workflow graphic; prompt, scientific-status disclosure and alt text in `figures/README.md` |
| 8 | `fig-pipeline.svg` | `scripts/fig-pipeline.py` — no data reads; a hand-laid flow chart. Shown under `.figure-lede` (430px), not `.figure-with-quote` (340px), so its internal labels survive projection |
| 11 | `fig-r2-master-simple.svg` | `tables/tbl-popweighting-master.csv`, the **simple-mean** columns |
| 13 | `fig-r2-master.svg` | Same table, the **pop-weighted** columns. Shares slide 11's goal order and x-axis so the two read as a before/after pair |
| 15 | `fig-legibility-clustering.svg` | `tables/tbl-outcomes-descriptives.csv` (`Moran's I`) ⋈ `tables/tbl-popweighting-master.csv` (`R² daytime embeddings (pop-weighted)`) on `Goal index` |
| 18 | `fig-combined-range.svg` | `tbl-mon-comprehensive.csv` (lower) ⋈ `tbl-mon-featureset-comparison.csv` `Combined (pop-weighted)` (upper) |
| 19 | `fig-transfer-floor.svg` | `tables/tbl-views-lodo.csv` (lights, embeddings) + `tables/tbl-mon-comprehensive.csv` (combined) |
| 20, 27, 28 | `fig-views-lisa-sdg{1,7,13}.png` | `data/predictions/sdg{1,7,13}_fourview_2017.csv`, exported by `scripts/_fourview.py` from `.notebook-cache/sdg*_{ntlw8,weighted,combow}.pkl` key `oof_pred`. **Queen contiguity** via `code/spatial_weights.queen_repaired`, `Moran_Local(permutations=999, seed=12345)`, p < 0.05 |

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
quarto render monitoring-local-development.qmd
uv run python scripts/_source_checks.py .                  # Tier S  — gates
uv run python scripts/_html_checks.py .                    # Tier B′ — gates
uv run python scripts/_qa_checks.py .                      # Tier B  — diagnostic
uv run python scripts/_sync_check.py .                     # snapshot intact
uv run --extra qa python scripts/_browser_checks.py . all  # Tiers A/A′/C — run LAST
```

Result on 2026-09-12, after the conference re-cut:

| Tier | Surface | Result |
|---|---|---|
| B | source: contrast, figure fit, overflow, palette drift | 0 contrast failures, 0 palette drift, **0 overflow-risk slides** (was 1) |
| B′ | rendered HTML | **PASS**, 0 failures — 34 `<section>` tags from 29 headings, 25 note blocks, 7 dividers, 14 of 14 figures inlined |
| S | every number against its declared source | **PASS**, 0 unresolved, 0 noted — all 61 entries traced, and every number on a slide and in a speaker note accounted for |
| Sync | frozen snapshot | **PASS** — 33 files unchanged, 15 claims frozen |
| A′ / A / C | live page | **not run this round.** `uv sync --extra qa` cannot build `llvmlite` under Python 3.14 here, so playwright is unavailable and rule 1 forbids `pip install` |
| In-browser sweep | every section measured at 720px with all fragments revealed | **0 slides overflow** — this stood in for Tier C |

**How the sweep was done,** since it is the substitute for the screenshots and worth repeating:
serve the rendered `index.html` over `python3 -m http.server`, then walk `Reveal.slide(h, v)` across
every section, force `.fragment` elements visible, and compare `scrollHeight` against 720. Three
slides failed it at 738px on the first pass — all three because a long title wrapped to two lines
and pushed the `.source` caption onto the footer band. That is a defect the static heuristic in
`_qa_checks.py` cannot see, and it is the same class of defect the 2026-07-28 round needed
screenshots to find.

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
