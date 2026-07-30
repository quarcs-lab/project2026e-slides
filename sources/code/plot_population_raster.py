# ─── VENDORED SNAPSHOT — BEGIN (do not edit; do not remove these two markers) ───
# source repo : https://github.com/quarcs-lab/project2026e
# source path : code/plot_population_raster.py
# last commit : c2594c67cad1de438638bfb169f88489e8926e5a  (2026-07-12)
# snapshot    : 2026-07-30 @ 9856b81
# refresh     : uv run python scripts/_sync_check.py . --root /path/to/project2026e
# ─── VENDORED SNAPSHOT — END ───
#!/usr/bin/env python3
"""Plot the Bolivia population raster (GHS-POP, ~500 m) as a log-scaled map.

Reads the single-band population-count GeoTIFF exported by `code/plot-population-raster.ipynb`
(committed to `data/population/rasters/`), masks it to Bolivia, and renders a log-scaled heatmap.
Pixel values are residential **population count per ~500 m cell** (GHS-POP P2023A, 2017 interpolated
from the 2015 and 2020 epochs), so summing over Bolivia recovers the national total (~11.45 M).

Reusable from the command line or as a module: `notebooks/population-raster.qmd` imports
`plot_population` to produce the embedded figure.

Example
-------
    python code/plot_population_raster.py \
        --tif data/population/rasters/bolivia_ghspop_2017.tif
"""
from __future__ import annotations

import argparse
import math
import os

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.crs import CRS
from rasterio.features import geometry_mask
from rasterio.warp import Resampling, calculate_default_transform, reproject
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

BOLIVIA_LAT = -16.7  # undo the aspect distortion of an unprojected (degrees) map
DISPLAY_CRS = "EPSG:4326"  # warp for display so Bolivia renders upright (matches the other maps)

# Defaults assume the repository root is the working directory.
DEFAULT_TIF = "data/population/rasters/bolivia_ghspop_2017.tif"
DEFAULT_BOUNDARY = "data/maps/bolivia339geoqueryOpt.geojson"
DEFAULT_REGION_CSV = "data/regionNames/regionNames.csv"
DEFAULT_OUT = "images/fig-population-raster.png"


def _load_boundary(path, crs):
    gdf = gpd.read_file(path)
    if gdf.crs is not None and crs is not None and str(gdf.crs) != str(crs):
        gdf = gdf.to_crs(crs)
    return gdf


def _read_masked(tif, boundary):
    """Band 1 as a float64 masked array (masked outside Bolivia / at nodata) + extent, crs,
    gdf, and the native affine transform."""
    with rasterio.open(tif) as src:
        arr = src.read(1).astype("float64")
        crs, b, transform, nd = src.crs, src.bounds, src.transform, src.nodata
        gdf = _load_boundary(boundary, crs)
        country = gdf.union_all()
    bad = ~np.isfinite(arr)
    if nd is not None and np.isfinite(nd):
        bad |= (arr == nd)
    outside = geometry_mask([country], out_shape=arr.shape, transform=transform, invert=False)
    masked = np.ma.masked_array(arr, mask=outside | bad)
    extent = [b.left, b.right, b.bottom, b.top]
    return masked, extent, crs, gdf, transform


def _warp_for_display(disp, src_transform, src_crs, boundary, dst_crs=DISPLAY_CRS):
    """Warp a 2-D display array to ``dst_crs`` (default EPSG:4326) so the map renders upright.

    The source raster is in ESRI:54009 (World Mollweide), a global equal-area projection
    centered on longitude 0°; Bolivia sits ~63° west of that center, so its shape is sheared
    in the native grid. Warping to geographic lat/lon removes the shear and matches the
    embeddings and nighttime-lights maps. This is a *display-only* reprojection — the ~11.5 M
    population total is computed from the native array, never from this resampled one.

    Returns ``(masked_array, extent, gdf)`` in ``dst_crs``: the warped values (masked outside
    Bolivia / at nodata), the imshow extent in degrees, and the boundary reprojected to
    ``dst_crs`` so boundary overlays line up.
    """
    dst = CRS.from_string(dst_crs)
    h, w = disp.shape
    left, top = src_transform.c, src_transform.f
    right, bottom = left + w * src_transform.a, top + h * src_transform.e
    dst_transform, dst_w, dst_h = calculate_default_transform(
        src_crs, dst, w, h, left, bottom, right, top)

    # Warp the filled display array (empty cells already floored to 1); NaN marks "no source
    # pixel" so it can be re-masked. Nearest resampling avoids inventing intermediate values.
    src = disp.filled(np.nan).astype("float64")
    dest = np.full((dst_h, dst_w), np.nan, dtype="float64")
    reproject(
        source=src, destination=dest,
        src_transform=src_transform, src_crs=src_crs,
        dst_transform=dst_transform, dst_crs=dst,
        src_nodata=np.nan, dst_nodata=np.nan, resampling=Resampling.nearest,
    )

    gdf = _load_boundary(boundary, dst)
    outside = geometry_mask([gdf.union_all()], out_shape=(dst_h, dst_w),
                            transform=dst_transform, invert=False)
    masked = np.ma.masked_array(dest, mask=outside | ~np.isfinite(dest))
    d_left, d_top = dst_transform.c, dst_transform.f
    d_right, d_bottom = d_left + dst_w * dst_transform.a, d_top + dst_h * dst_transform.e
    extent = [d_left, d_right, d_bottom, d_top]
    return masked, extent, gdf


def raster_has_data(tif, boundary=DEFAULT_BOUNDARY):
    """True if the raster has positive population inside Bolivia (i.e. is plottable)."""
    try:
        m, *_ = _read_masked(tif, boundary)
    except Exception:
        return False
    return m.count() > 0 and float(np.ma.max(m)) > 0


def plot_population(tif, *, boundary=DEFAULT_BOUNDARY, region_csv=None, out_png=None,
                    year=2017, cmap="viridis", title=None,
                    facecolor="black", text_color="white"):
    """Render the log-scaled population map masked to Bolivia, in an "Earth at night" dark
    theme matching the nighttime-lights figure. Returns the figure.

    Population per cell spans orders of magnitude, so the colour scale is logarithmic
    (empty cells floored to 1, the darkest colour). Masked pixels (outside Bolivia / nodata)
    take ``facecolor`` via the colormap's "bad" colour, so they merge into the dark
    background instead of showing white. ``viridis`` is used by default to keep the
    population surface visually distinct from the magma nighttime-lights maps. There is no
    web basemap, so the figure renders offline.
    """
    pop, _extent_native, crs, gdf, transform = _read_masked(tif, boundary)

    vals = pop.compressed()
    positive = vals[vals > 0]
    vmax = max(float(np.percentile(positive, 99.5)) if positive.size else 2.0, 2.0)
    # LogNorm needs positive values: floor empty (0) cells to 1 (shown as the darkest colour),
    # keep the Bolivia mask so outside stays masked (drawn in the dark background colour).
    disp_native = np.ma.masked_array(np.clip(pop.filled(0.0), 1.0, None), mask=np.ma.getmaskarray(pop))
    norm = LogNorm(vmin=1.0, vmax=vmax)

    # Warp the display array to EPSG:4326 so Bolivia renders upright (the native raster is in
    # Mollweide, which shears the country). The ~11.5 M total above is from the native array;
    # this resampled copy is display-only. After warping, `crs`/`gdf`/`extent` are all in 4326.
    disp, extent, gdf = _warp_for_display(disp_native, transform, crs, boundary)
    crs = CRS.from_string(DISPLAY_CRS)

    deps = None
    if region_csv:
        names = pd.read_csv(region_csv)[["asdf_id", "dep"]]
        deps = gdf.merge(names, on="asdf_id", how="left").dissolve(by="dep").reset_index()

    # Masked pixels (outside the country, nodata) take the dark background colour rather than
    # the default transparent, which would otherwise show the page through.
    cmap_obj = plt.get_cmap(cmap).copy()
    cmap_obj.set_bad(facecolor)

    aspect = (1.0 / math.cos(math.radians(BOLIVIA_LAT))) if (crs and crs.is_geographic) else 1.0
    if title is None:
        title = f"Population, {year} (GHS-POP, ~500 m) — total ≈ {vals.sum() / 1e6:.1f} M"

    fig, ax = plt.subplots(figsize=(7.5, 7.5), facecolor=facecolor)
    ax.set_facecolor(facecolor)
    im = ax.imshow(disp, extent=extent, origin="upper", norm=norm, cmap=cmap_obj)
    if deps is not None:
        deps.boundary.plot(ax=ax, color="white", linewidth=0.6)
    gdf.boundary.plot(ax=ax, color="skyblue", linewidth=0.15, alpha=0.55)
    ax.set_aspect(aspect)
    ax.set_title(title, color=text_color)
    ax.set_axis_off()
    cbar = fig.colorbar(im, ax=ax, shrink=0.65, pad=0.02)
    cbar.set_label("Population per ~500 m cell (log scale)", color=text_color)
    cbar.ax.tick_params(colors=text_color)
    cbar.outline.set_edgecolor(text_color)

    if out_png:
        os.makedirs(os.path.dirname(out_png) or ".", exist_ok=True)
        fig.savefig(out_png, dpi=300, bbox_inches="tight", facecolor=facecolor)
    return fig


def _main():
    p = argparse.ArgumentParser(description="Log-scaled population map of Bolivia (GHS-POP ~500 m).")
    p.add_argument("--tif", default=DEFAULT_TIF)
    p.add_argument("--boundary", default=DEFAULT_BOUNDARY)
    p.add_argument("--region-csv", default=DEFAULT_REGION_CSV,
                   help="region-name CSV for department boundaries (pass '' to skip)")
    p.add_argument("--out", default=DEFAULT_OUT)
    p.add_argument("--year", type=int, default=2017)
    a = p.parse_args()

    plt.switch_backend("Agg")
    if not os.path.exists(a.tif):
        raise SystemExit(f"tif not found: {a.tif} (run code/plot-population-raster.ipynb in Colab)")
    if not raster_has_data(a.tif, a.boundary):
        raise SystemExit("raster has no positive population inside Bolivia — re-export the GeoTIFF.")
    plot_population(a.tif, boundary=a.boundary, region_csv=(a.region_csv or None),
                    out_png=a.out, year=a.year)
    print("wrote", a.out)


if __name__ == "__main__":
    _main()
