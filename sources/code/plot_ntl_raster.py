# ─── VENDORED SNAPSHOT — BEGIN (do not edit; do not remove these two markers) ───
# source repo : https://github.com/quarcs-lab/project2026e
# source path : code/plot_ntl_raster.py
# last commit : 690441f729ffd8b3ff0052057fd59a7176da7066  (2026-07-18)
# snapshot    : 2026-07-30 @ 9856b81
# refresh     : uv run python scripts/_sync_check.py . --root /path/to/project2026e
# ─── VENDORED SNAPSHOT — END ───
#!/usr/bin/env python3
"""Plot VIIRS nighttime-lights raster bands over Bolivia.

Reads a multi-band GeoTIFF of the VIIRS DNB Annual V2.1 statistics — exported by
``code/plot-ntl-viirs-rasters.ipynb`` and committed to
``data/nighttimeLights/rasters/`` — and renders a two-panel map of any two bands,
masked to the Bolivian national outline. Reusable from the command line or as a
module: the manuscript notebook ``notebooks/ntl-viirs-rasters.qmd`` imports
``plot_bands`` to produce the embedded figure.

Band names, in export order (see ``code/aggregate-ntl-viirs-to-adm.js``)::

    average, average_masked, median, median_masked, minimum, maximum, cf_cvg, cvg

The six radiance bands are in nanoWatts/sr/cm²; ``cf_cvg``/``cvg`` are observation
counts. Bands are selected by name via the GeoTIFF band descriptions, falling back
to the canonical order above if descriptions are absent.

Examples
--------
    python code/plot_ntl_raster.py --bands average maximum
    python code/plot_ntl_raster.py --bands median cf_cvg --out images/ntl_median_cvg.png
"""
from __future__ import annotations

import argparse
import math
import os

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import geometry_mask
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.colors import PowerNorm
import contextily as cx

# Sibling module (flat import; see code/labels.py for why this is not a package import).
import labels as L

# Canonical VIIRS DNB Annual V2.1 band order.
NTL_COLS = ["average", "average_masked", "median", "median_masked",
            "minimum", "maximum", "cf_cvg", "cvg"]

# The six radiance statistics (excludes the two coverage/observation-count bands
# ``cf_cvg`` and ``cvg``), used for the six-panel manuscript figure.
RADIANCE_BANDS = ["average", "average_masked", "median", "median_masked",
                  "minimum", "maximum"]

# Human-readable panel labels for the radiance bands.
BAND_LABELS = {
    "average": "Mean", "average_masked": "Mean, masked",
    "median": "Median", "median_masked": "Median, masked",
    "minimum": "Minimum", "maximum": "Maximum",
}

BOLIVIA_LAT = -16.7  # undo the aspect distortion of an unprojected (degrees) map

# Defaults assume the repository root is the working directory.
DEFAULT_TIF = "data/nighttimeLights/rasters/bolivia_ntl_viirs_2017.tif"
DEFAULT_BOUNDARY = "data/maps/bolivia339geoqueryOpt.geojson"
DEFAULT_REGION_CSV = "data/regionNames/regionNames.csv"
DEFAULT_OUT = "images/fig-ntl-viirs-rasters.png"


def _band_index(src, name):
    """1-based band index for ``name`` via GeoTIFF descriptions, else ``NTL_COLS`` order."""
    descs = list(src.descriptions or [])
    if name in descs:
        return descs.index(name) + 1
    if name in NTL_COLS:
        return NTL_COLS.index(name) + 1
    raise KeyError(f"band {name!r} not found; tif descriptions={descs}, known={NTL_COLS}")


def _read_masked(src, name, country):
    """Read one band as a float64 masked array: masked outside Bolivia and at nodata."""
    arr = src.read(_band_index(src, name)).astype("float64")
    bad = ~np.isfinite(arr)                      # -inf / +inf / nan fills
    nd = src.nodata
    if nd is not None and np.isfinite(nd):
        bad |= (arr == nd)
    outside = geometry_mask([country], out_shape=arr.shape,
                            transform=src.transform, invert=False)  # True == outside country
    return np.ma.masked_array(arr, mask=outside | bad)


def _load_boundary(boundary_path, crs):
    gdf = gpd.read_file(boundary_path)
    if gdf.crs is not None and crs is not None and str(gdf.crs) != str(crs):
        gdf = gdf.to_crs(crs)
    return gdf


def raster_has_data(tif, name="average", boundary=DEFAULT_BOUNDARY):
    """True if ``name`` has finite, non-constant pixels inside Bolivia (i.e. is plottable)."""
    try:
        with rasterio.open(tif) as src:
            country = _load_boundary(boundary, src.crs).union_all()
            m = _read_masked(src, name, country)
    except Exception:
        return False
    if m.count() == 0:
        return False
    return float(np.ma.max(m)) > float(np.ma.min(m))


def plot_bands(tif, band_a="average", band_b="maximum", *, boundary=DEFAULT_BOUNDARY,
               region_csv=None, out_png=None, cmap="magma", caps=(None, None),
               year=2017, titles=None):
    """Two-panel map of ``band_a`` | ``band_b``, masked to Bolivia. Returns the figure.

    ``caps`` sets a per-panel colour ceiling (nanoWatts/sr/cm²); ``None`` auto-scales to
    the band's 98th percentile. Pass ``region_csv`` to overlay department boundaries.
    """
    with rasterio.open(tif) as src:
        crs = src.crs
        b = src.bounds
        gdf = _load_boundary(boundary, crs)
        country = gdf.union_all()
        ma = _read_masked(src, band_a, country)
        mb = _read_masked(src, band_b, country)
    extent = [b.left, b.right, b.bottom, b.top]

    deps = None
    if region_csv:
        names = pd.read_csv(region_csv)[["asdf_id", "dep"]]
        deps = gdf.merge(names, on="asdf_id", how="left").dissolve(by="dep").reset_index()

    if titles is None:
        titles = (f"(a) {L.NTL} {band_a}, {year}",
                  f"(b) {L.NTL} {band_b}, {year}")

    def cap(arr, c):
        if c:
            return float(c)
        vals = arr.compressed()
        return float(np.percentile(vals, 98)) if vals.size else 1.0

    panels = [(ma, cap(ma, caps[0]), titles[0]), (mb, cap(mb, caps[1]), titles[1])]

    aspect = (1.0 / math.cos(math.radians(BOLIVIA_LAT))) if (crs and crs.is_geographic) else 1.0
    crs_str = crs.to_string() if crs else "EPSG:4326"

    fig = plt.figure(figsize=(13, 6.5))
    gs = GridSpec(1, 2, wspace=0.05)
    for i, (band, vmax, title) in enumerate(panels):
        ax = fig.add_subplot(gs[i])
        im = ax.imshow(band, extent=extent, origin="upper", vmin=0, vmax=vmax, cmap=cmap)
        if deps is not None:
            deps.boundary.plot(ax=ax, color="white", linewidth=0.6)
        gdf.boundary.plot(ax=ax, color="skyblue", linewidth=0.15, alpha=0.5)
        try:
            cx.add_basemap(ax, crs=crs_str, source=cx.providers.CartoDB.DarkMatterOnlyLabels,
                           attribution=False)
        except Exception as exc:
            print(f"(basemap skipped: {type(exc).__name__})")
        ax.set_aspect(aspect)
        ax.set_title(title)
        ax.set_axis_off()
        cbar = fig.colorbar(im, ax=ax, shrink=0.6, pad=0.02)
        cbar.set_label("Luminosity (nanoWatts/sr/cm$^2$)")
        ticks = [t for t in cbar.get_ticks() if 0 <= t <= vmax]
        if len(ticks) > 1:
            cbar.set_ticks(ticks)
            cbar.set_ticklabels([f"{t:g}" for t in ticks[:-1]] + [f"{ticks[-1]:g}+"])

    if out_png:
        os.makedirs(os.path.dirname(out_png) or ".", exist_ok=True)
        fig.savefig(out_png, dpi=300, bbox_inches="tight")
    return fig


def _robust_cap(arr, pct=99.0):
    """Positive upper colour cap for one band: the ``pct`` percentile of its lit
    (strictly positive) pixels, falling back to all pixels then to the band maximum.

    This keeps a meaningful ceiling even for the masked bands, whose pixels are zero
    almost everywhere, and it ignores the extreme single-pixel outliers (e.g. the
    ~45,000 nW value in the maximum band) that would otherwise flatten the display.
    """
    vals = arr.compressed()
    if vals.size == 0:
        return 1.0
    pos = vals[vals > 0]
    base = pos if pos.size >= 50 else vals
    c = float(np.percentile(base, pct))
    if not np.isfinite(c) or c <= 0:
        mx = float(np.max(vals))
        c = mx if mx > 0 else 1.0
    return c


def plot_grid(tif, bands=None, *, boundary=DEFAULT_BOUNDARY, region_csv=None,
              out_png=None, cmap="magma", gamma=0.45, cap_pct=99.0,
              nrows=3, ncols=2, year=2017, titles=None,
              dep_color="white", muni_color="skyblue",
              facecolor="black", text_color="white"):
    """Grid of VIIRS radiance bands, each log/gamma-stretched and masked to Bolivia.

    Renders ``bands`` (default the six :data:`RADIANCE_BANDS`) as an ``nrows`` x ``ncols``
    grid of ``imshow`` panels in an "Earth at night" dark theme. Each panel is scaled
    independently with a ``PowerNorm(gamma)`` stretch from 0 to a per-band robust cap (see
    :func:`_robust_cap`), so the dim rural majority stays legible while urban cores glow — a
    display choice, not an analysis choice. Masked pixels (outside Bolivia and water bodies)
    render in ``facecolor`` via the colormap's "bad" colour, so they merge into the dark
    background instead of showing white. White department boundaries and faint municipal
    boundaries overlay the raster; there is no web basemap, so the figure renders offline.
    Returns the figure.
    """
    bands = list(bands) if bands is not None else list(RADIANCE_BANDS)

    with rasterio.open(tif) as src:
        crs = src.crs
        b = src.bounds
        gdf = _load_boundary(boundary, crs)
        country = gdf.union_all()
        arrays = [_read_masked(src, name, country) for name in bands]
    extent = [b.left, b.right, b.bottom, b.top]

    deps = None
    if region_csv:
        names = pd.read_csv(region_csv)[["asdf_id", "dep"]]
        deps = gdf.merge(names, on="asdf_id", how="left").dissolve(by="dep").reset_index()

    if titles is None:
        letters = "abcdefghijklmnop"
        titles = [f"({letters[i]}) {BAND_LABELS.get(name, name)}, {year}"
                  for i, name in enumerate(bands)]

    # Masked pixels (outside the country, lakes/salt flats) take the dark background colour
    # rather than the default transparent, which would otherwise show the page through.
    cmap_obj = plt.get_cmap(cmap).copy()
    cmap_obj.set_bad(facecolor)

    aspect = (1.0 / math.cos(math.radians(BOLIVIA_LAT))) if (crs and crs.is_geographic) else 1.0

    fig = plt.figure(figsize=(9.5, 12), facecolor=facecolor)
    gs = GridSpec(nrows, ncols, wspace=0.10, hspace=0.14)
    for i, (arr, title) in enumerate(zip(arrays, titles)):
        ax = fig.add_subplot(gs[i])
        ax.set_facecolor(facecolor)
        vmax = _robust_cap(arr, cap_pct)
        norm = PowerNorm(gamma=gamma, vmin=0.0, vmax=vmax, clip=True)
        im = ax.imshow(arr, extent=extent, origin="upper", norm=norm, cmap=cmap_obj)
        if deps is not None:
            deps.boundary.plot(ax=ax, color=dep_color, linewidth=0.5)
        gdf.boundary.plot(ax=ax, color=muni_color, linewidth=0.15, alpha=0.55)
        ax.set_aspect(aspect)
        ax.set_title(title, fontsize=11, color=text_color)
        ax.set_axis_off()
        cbar = fig.colorbar(im, ax=ax, shrink=0.72, pad=0.02)
        cbar.set_label("Luminosity (nanoWatts/sr/cm$^2$)", fontsize=8, color=text_color)
        cbar.ax.tick_params(labelsize=7, colors=text_color)
        cbar.outline.set_edgecolor(text_color)
        ticks = [t for t in cbar.get_ticks() if 0 <= t <= vmax]
        if len(ticks) > 1:
            cbar.set_ticks(ticks)
            cbar.set_ticklabels([f"{t:g}" for t in ticks[:-1]] + [f"{ticks[-1]:g}+"])

    if out_png:
        os.makedirs(os.path.dirname(out_png) or ".", exist_ok=True)
        fig.savefig(out_png, dpi=300, bbox_inches="tight", facecolor=facecolor)
    return fig


def _main():
    p = argparse.ArgumentParser(description="Plot VIIRS NTL raster bands over Bolivia.")
    p.add_argument("--tif", default=DEFAULT_TIF)
    p.add_argument("--bands", nargs=2, default=["average", "maximum"], metavar=("A", "B"),
                   help=f"two band names from: {', '.join(NTL_COLS)}")
    p.add_argument("--boundary", default=DEFAULT_BOUNDARY)
    p.add_argument("--region-csv", default=DEFAULT_REGION_CSV,
                   help="region-name CSV for department boundaries (pass '' to skip)")
    p.add_argument("--out", default=DEFAULT_OUT)
    p.add_argument("--year", type=int, default=2017)
    a = p.parse_args()

    plt.switch_backend("Agg")
    if not os.path.exists(a.tif):
        raise SystemExit(f"tif not found: {a.tif}")
    if not raster_has_data(a.tif, a.bands[0], a.boundary):
        raise SystemExit(
            f"band {a.bands[0]!r} has no finite data inside Bolivia — re-export the GeoTIFF "
            "(run code/plot-ntl-viirs-rasters.ipynb in Colab)."
        )
    plot_bands(a.tif, a.bands[0], a.bands[1], boundary=a.boundary,
               region_csv=(a.region_csv or None), out_png=a.out, year=a.year)
    print("wrote", a.out)


if __name__ == "__main__":
    _main()
