"""Shared dark-canvas raster furniture for the three data-layer slides (3, 4, 5).

The layer *maths* is reused verbatim from the manuscript's own plotters — the read, the
mask, the stretch and the warp must not fork, or the slides would show a different
Bolivia from the paper. What is NOT reused is the panel *drawing*.

WHY THE PANEL DRAWERS ARE NOT REUSED
``code/plot_data_overview.py`` builds a light 2x2 manuscript figure, and five things in it
are wrong on a #0A1C36 slide:

  * ``_finish()`` fetches a light CartoDB Positron basemap, which on the night canvas is a
    white rectangle — and ``_palette.apply_deck_style()`` sets ``savefig.transparent=True``
    precisely so deck figures do *not* ship an opaque panel. It is also a network fetch that
    degrades silently, so the figure would render differently offline.
  * ``_finish()`` hardcodes the grid letter its caller passes ("(b) ...", "(c) ...") and
    ``fontsize=10``. Meaningless on a one-panel slide, and unreadable at projection scale.
  * ``add_north_arrow`` is ``facecolor="black"`` and ``add_scalebar`` is ``color="#222222"``.
  * ``_dept_overlay`` draws black boundaries with white label boxes at ``fontsize=5``.

Deleting those artists after the fact is worse than not drawing them: the basemap is an
``imshow`` at ``zorder=0`` and the scale bar an ``AnchoredSizeBar`` identifiable only by
type. So the drawing is deck-local and the maths is imported.

The helpers here are named WITHOUT a leading underscore (``finish``, not ``_finish``) so a
reader can see at a glance that they are the deck's, not ``PDO``'s.

DISPLAY ONLY: ``PDO._warp_masked_to`` resamples nearest-neighbour for display. Never derive
a statistic from its output — quote the tables instead.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _paths                                       # noqa: E402
# Puts sources/code on the path BEFORE plot_data_overview loads: that module does flat sibling
# imports (`import plot_ntl_raster as pnr`), so it cannot be imported as a package.
_paths.bootstrap()
DECKDIR = _paths.DECK

import matplotlib.pyplot as plt                     # noqa: E402
import numpy as np                                  # noqa: E402
import rasterio                                     # noqa: E402
from matplotlib.colors import BoundaryNorm, ListedColormap, PowerNorm   # noqa: E402
from matplotlib.offsetbox import AnchoredText       # noqa: E402
from matplotlib.patches import Patch                # noqa: E402

from _palette import DECK, MAP                      # noqa: E402

import plot_data_overview as PDO                    # noqa: E402  _warp_masked_to, _load_muni,
                                                    #   _bolivia_bbox_3857, POP_BOUNDS, POP_LABELS
import plot_ntl_raster as pnr                       # noqa: E402  _read_masked, _robust_cap
import plot_population_raster as ppr                # noqa: E402  _read_masked

# Resolved through _paths, which prefers a live manuscript checkout, then the vendored
# sources/ snapshot, then Hugging Face. PDO's own DEFAULT_* paths are relative and assume the
# repo root is the working directory, which is never true from the deck folder, so every path
# this module hands to PDO is passed explicitly.
#
# These three are vendored, so resolving them eagerly costs a stat() and nothing else.
GEOJSON = _paths.data("maps/bolivia339geoqueryOpt.geojson")
REGION_CSV = _paths.data("regionNames/regionNames.csv")
# The 11 MB PCA composite, already in EPSG:3857. Never the 3 GB 64-band source: that raster is
# gitignored and exists only for `plot_data_overview --precompute-embeddings`.
EMB_RGB = _paths.data("satelliteEmbeddings/rasters/bolivia_embeddings_pca_rgb_2017.tif")
POP_TIF = _paths.data("population/rasters/bolivia_ghspop_2017.tif")


def ntl_tif():
    """The VIIRS nighttime-lights raster — resolved LAZILY, on first use.

    This one is 118 MB, over GitHub's 100 MB per-file limit, so it is not vendored and
    ``_paths.data`` streams it from Hugging Face. As a module-level constant it was a trap:
    ``fig-pop-raster.py`` and ``fig-emb-raster.py`` import this module and never touch
    nighttime lights, yet merely importing it would have pulled 118 MB over the network to
    draw a population map. It would have *worked*, just slowly, so nobody would have noticed
    — and it would have failed offline for no reason at all.

    Called only from ``draw_ntl``. Keep it that way.
    """
    return _paths.data(_paths.BIG_RASTER)

YEAR = 2017
# Sized to the SHIPPED aspect, not a nominal canvas. `set_aspect("equal")` on the Bolivia bbox
# makes the axes portrait (~0.89 w:h) and `bbox_inches="tight"` crops the empty bands either side,
# so figsize*dpi does not predict the output. A wide 11x6 canvas was tried first: it cropped to
# 821x925 and, because point sizes are absolute while the canvas shrank to ~4.3in, every label
# rendered proportionally huge and the colorbar caption ran off the edge. Matching figsize to the
# real aspect keeps font sizes meaning what they say.
FIGSIZE = (7.0, 7.9)
DPI = 280                  # -> ~1250x1400 after crop, comparable to the 2860x1081 choropleths

# --- nighttime-lights stretch. All three constants are tuned together; see draw_ntl. ---
NTL_FLOOR = 0.17           # just OVER the in-country median of 0.166 nW — see draw_ntl
NTL_CAP = 1.5              # nW ceiling. A FIXED value, not a percentile — see draw_ntl for why
NTL_ALPHA_RAMP = 0.08      # fraction of the ramp over which alpha climbs 0 -> 1


def muni_and_bbox():
    """Municipal geometry + the shared EPSG:3857 frame, so all three slides frame Bolivia
    identically — the whole point of showing them one after another."""
    gdf = PDO._load_muni(GEOJSON, REGION_CSV)
    return gdf, PDO._bolivia_bbox_3857(gdf)


def muni_overlay(ax, gdf):
    """The 339 municipality boundaries — the unit of analysis — under a crisp national border.

    Municipalities are what the study measures, so they are what the map should show. The earlier
    version dissolved these up to nine departments and labelled the departments by name; both are
    gone. No region names are drawn: the point of the overlay is the mesh of analysis units, and 339
    names would bury the raster.

    Two lines, deliberately unequal:

      * Interior mesh — the 339 municipalities, thin and translucent in the map-outline colour. At the
        department scale a 0.6 pt line at 0.75 alpha was a frame; for 339 polygons the same weight is a
        cage that hides the raster the panel exists to show, so it drops to a hairline reference grid.
      * National border — the union of all municipalities, in the hairline colour (~2:1 on the canvas)
        and a little wider ON TOP. Near-white was too heavy; this reads as a defined edge without
        shouting, and stays the dominant line only because it is continuous and wider than the 0.2 pt
        interior mesh, not because of colour contrast.

    Tune against a render, not by arithmetic: the combined panel is ~5in wide displayed ~330px, so a
    hairline here is what a reader actually sees.
    """
    munis = gdf.to_crs(PDO.WEB_MERCATOR)
    munis.boundary.plot(ax=ax, color=MAP["outline"], linewidth=0.2, alpha=0.5, zorder=6)
    munis.dissolve().boundary.plot(ax=ax, color=DECK["hairline"], linewidth=1.0, alpha=1.0, zorder=7)


def finish(ax, bb):
    """Fixed shared frame, equal aspect, no axes — and deliberately no title and no basemap.

    The slide's own H2 is the title; a second one inside the figure would be a duplicate.
    """
    ax.set_xlim(bb[0], bb[1])
    ax.set_ylim(bb[2], bb[3])
    ax.set_aspect("equal")
    ax.set_axis_off()


def inset_colorbar(ax, fig, im, label, ticks=None, ticklabels=None, scale=1.0):
    """A horizontal colorbar inside the axes, lower right.

    ``set_aspect("equal")`` on the Bolivia bbox leaves the map height-bound on a 16:9 figure,
    so there are empty bands either side. Putting the bar there costs no map area — the same
    trick as ``PDO._inset_colorbar``, recoloured for the dark canvas.
    """
    cax = ax.inset_axes([0.62, 0.11, 0.34, 0.024])
    cbar = fig.colorbar(im, cax=cax, orientation="horizontal")
    # Label ABOVE the bar. Below it, a caption wider than the 0.34 axes overflows the figure edge
    # and `bbox_inches="tight"` does not rescue it, because the inset is clipped to the parent axes.
    cbar.ax.set_title(label, fontsize=10.5 * scale, color=DECK["ink"], pad=5)
    cbar.ax.tick_params(labelsize=9.5 * scale, length=2, pad=2, colors=DECK["ink"])
    cbar.outline.set_edgecolor(DECK["hairline"])
    cbar.outline.set_linewidth(0.6)
    if ticks is not None:
        cbar.set_ticks(ticks)
        if ticklabels is not None:
            cbar.set_ticklabels(ticklabels)
    return cbar


def dark_box(artist):
    """Restyle an AnchoredText / legend frame for the night canvas.

    The manuscript's notes and legends are white boxes at ``alpha=0.9``; on #0A1C36 that is a
    glare patch. A panel-surface fill with a hairline edge keeps them readable without
    competing with the raster.
    """
    patch = getattr(artist, "patch", None) or artist.get_frame()
    patch.set(facecolor=DECK["bg_alt"], alpha=0.92, edgecolor=DECK["hairline"], linewidth=0.6)
    return artist


# --- the three data layers ---------------------------------------------------------------
# Each draws ONE layer into a caller-supplied axes, so the standalone slide figures and the
# three-panel comparison figure share a single implementation. Before this, the drawing lived in
# the three fig-*.py scripts and a fourth copy would have been needed for the combined figure —
# which is exactly how a slide and its archive drift apart.
#
# `scale` multiplies every key font size. It exists because point sizes do NOT carry between
# the two figures: a standalone panel is 7in wide and displayed ~430px tall, while a combined panel
# is ~5in wide and displayed ~330px tall, so the same 10pt caption reads differently in each. Tune
# it against a render, not by arithmetic.

def draw_ntl(ax, fig, gdf, bb, *, keys=True, scale=1.0):
    """Nighttime lights: VIIRS annual mean radiance, magma on an alpha ramp.

    STRETCH — two decisions here, and they pull in opposite directions.

    FLOOR: departs from the manuscript's panel (b), which anchors vmin=0. The VIIRS annual mean
    carries a detection floor around 0.15-0.20 nW — the in-country median is 0.166 and 87% of pixels
    sit at or below 0.2. That is airglow and sensor background, not settlement, and the repo's own
    docs agree: `average_masked`, which the aggregation script calls the "preferred development
    proxy" because VNL background-zeroing isolates persistent anthropogenic lighting, reads 0.000 at
    the 95th percentile inside Bolivia. VIIRS itself reports no light across most of the country.
    Anchoring at 0 contradicts that and renders the whole map as a flat pink blanket.

    CAP: a FIXED 1.5 nW, not a percentile. Bolivia's settlement signal lives in roughly 0.2-2 nW, so
    floor and cap together decide how much of the country reads as lit. Measured over all 5.2M
    in-country pixels:

        floor  cap      opaque   visible   saturated
        0.20  18.87       4.3%     0.8%      0.10%   <- p99.9; the first cut, far too sparse
        0.15   1.50      66.3%     9.1%      0.56%   <- most coverage, but a purple haze countrywide
        0.17   1.50      36.2%     6.3%      0.56%   <- HERE
        0.19   1.50      15.6%     5.0%      0.56%
        0.17   2.50      31.2%     4.0%      0.39%
        0.10   0.78         --    91.3%      1.00%
        0.00   0.78         --   100.0%      1.00%   <- the manuscript's setting: a uniform wash

    The FLOOR is the decisive lever, not the cap. It sits just ABOVE the 0.166 median so background
    clips to transparent: at 0.15 two thirds of the country renders fully opaque and the Chaco and
    altiplano read as a flat purple field, which is sensor background drawn as light. At 0.17 the
    empty land goes dark again while the road network, Beni's river towns and the highland
    settlement pattern all stay visible. This was chosen by looking at a floor sweep, not computed.

    A percentile cap is the wrong instrument at this end of the distribution — p99 = 0.775 and
    p99.9 = 18.87, a 24x jump across 0.9% of pixels, so the render would lurch on any change to the
    mask. A named nW ceiling is stable and can be reasoned about.
    """
    with rasterio.open(ntl_tif()) as src:
        crs, transform = src.crs, src.transform
        m = pnr._read_masked(src, "average", gdf.to_crs(crs).union_all())

    warped, extent = PDO._warp_masked_to(m, transform, crs)

    # Alpha ramps in over the bottom of the range so the floor fades out instead of ending on a hard
    # edge that would trace a false coastline around every town.
    cols = plt.get_cmap("magma")(np.linspace(0.0, 1.0, 256))
    cols[:, 3] = np.clip(np.linspace(0.0, 1.0, 256) / NTL_ALPHA_RAMP, 0.0, 1.0)
    cmap = ListedColormap(cols)
    cmap.set_bad(alpha=0.0)                             # outside Bolivia -> the slide gradient
    vmax = NTL_CAP
    norm = PowerNorm(gamma=0.45, vmin=NTL_FLOOR, vmax=vmax, clip=True)

    im = ax.imshow(warped, extent=extent, origin="upper", norm=norm, cmap=cmap,
                   interpolation="nearest", zorder=5)
    muni_overlay(ax, gdf)
    finish(ax, bb)
    if keys:
        # Three ticks. The middle is the value landing at the colour midpoint under the gamma
        # stretch, so the bar reads honestly rather than implying a linear ramp.
        mid = NTL_FLOOR + (vmax - NTL_FLOOR) * 0.5 ** (1 / 0.45)
        # Precision follows the cap. These were hardcoded to "%.0f" back when the cap was ~19 nW;
        # at a 1.5 nW ceiling that printed the 0.44 midpoint as "0" and the ceiling as "2+", i.e.
        # two wrong numbers on a bar whose whole job is to be read.
        fmt = "{:.0f}" if vmax >= 10 else "{:.1f}"
        inset_colorbar(ax, fig, im, "Luminosity (nW/sr/cm$^2$)",
                       ticks=[NTL_FLOOR, mid, vmax],
                       ticklabels=["dark", fmt.format(mid), fmt.format(vmax) + "+"], scale=scale)
    return vmax


def draw_emb(ax, gdf, bb, *, keys=True, scale=1.0):
    """Daytime embeddings: AlphaEarth PC1-3 as false colour.

    Reads the COMMITTED 11 MB PCA composite, already in EPSG:3857 — never the gitignored 3 GB
    64-band source. (That is why code/plot_embedding_raster.plot_pca_rgb, otherwise the dark-theme
    plotter, is unusable here: it needs all 64 bands.)
    """
    with rasterio.open(EMB_RGB) as src:
        rgba = src.read()                               # (4, H, W) uint8, already EPSG:3857
        b = src.bounds
        evr = src.tags().get("pc1_3_evr")

    img = np.transpose(rgba, (1, 2, 0)).astype("float32") / 255.0
    # Full opacity inside Bolivia; outside, alpha is already 0. The manuscript multiplies alpha by
    # 0.85 so its light basemap reads through — there is no basemap here, so dimming would only wash
    # the false colours toward the canvas and cost the separation the panel exists to show.
    ax.imshow(img, extent=[b.left, b.right, b.bottom, b.top], origin="upper",
              interpolation="nearest", zorder=5)
    muni_overlay(ax, gdf)
    finish(ax, bb)
    if keys:
        # The variance share lives HERE, inside the figure, not in the slide's .source line: a number
        # in a caption is a Tier S claim needing a numbers.toml entry, and this one is a property of
        # the composite rather than a result.
        note = ("Similar colours = similar places\n(land cover, built-up, terrain).\n"
                "Colours are arbitrary.")
        if evr is not None:
            note += f"\nPC1-3 explain {100 * float(evr):.0f}% of variance."
        at = AnchoredText(note, loc="lower right", frameon=True, pad=0.4, borderpad=0.6,
                          prop=dict(size=8.5 * scale, color=DECK["ink"], linespacing=1.3))
        at.set_zorder(8)
        dark_box(at)
        ax.add_artist(at)
    return evr


def draw_pop(ax, gdf, bb, *, keys=True, scale=1.0):
    """Population: GHS-POP counts in six classes.

    Six classes, not a continuous ramp. The distribution is extreme — most cells are empty and the
    inhabited ones run from 1 to ~1500 people — so a linear viridis would show a handful of cities
    on an otherwise uniform field. The class edges in PDO.POP_BOUNDS track the distribution of
    INHABITED cells (median ~5, p75 ~15, p90 ~51, p99 ~1500).

    Empty cells are masked rather than binned, so the transparent background IS the finding: the
    territory people actually occupy is a thin scatter.
    """
    # Native GHS-POP is ESRI:54009 (World Mollweide); _warp_masked_to takes it to 3857 for display.
    m, _extent_native, crs, _gdf_r, transform = ppr._read_masked(str(POP_TIF), str(GEOJSON))
    filled = m.filled(0.0)
    disp = np.ma.masked_array(filled, mask=np.ma.getmaskarray(m) | (filled <= 0.0))
    warped, extent = PDO._warp_masked_to(disp, transform, crs)

    pop_labels = PDO.POP_LABELS
    # Start at 0.25, not 0.0. Viridis's bottom is near-black, which on the night canvas makes the two
    # sparsest classes — the ones covering most inhabited territory — effectively invisible, so the
    # map would show only cities and lose the scatter that is the whole point.
    colors = plt.cm.viridis(np.linspace(0.25, 1.0, len(pop_labels)))
    cmap = ListedColormap(colors)
    cmap.set_bad(alpha=0.0)                             # empty / outside -> the slide gradient
    norm = BoundaryNorm(PDO.POP_BOUNDS, ncolors=len(pop_labels))

    ax.imshow(warped, extent=extent, origin="upper", norm=norm, cmap=cmap,
              interpolation="nearest", zorder=5)
    muni_overlay(ax, gdf)
    finish(ax, bb)
    if keys:
        # The cell resolution stays in this legend title and out of the slide's .source line: "500"
        # is not in _source_checks.IGNORE_PATTERNS, so in a caption it is a hard Tier S failure.
        handles = [Patch(facecolor=colors[i], edgecolor="none", label=pop_labels[i])
                   for i in range(len(pop_labels))]
        leg = ax.legend(handles=handles, loc="lower right", fontsize=8 * scale, frameon=True,
                        labelcolor=DECK["ink"], title="People per ~500 m cell",
                        title_fontsize=8.5 * scale, handlelength=1.5, handleheight=0.9,
                        labelspacing=0.35, borderpad=0.6)
        leg.get_title().set_color(DECK["ink"])
        dark_box(leg)
    return float((disp.count() / disp.size) * 100)
