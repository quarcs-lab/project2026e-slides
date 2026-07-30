# ─── VENDORED SNAPSHOT — BEGIN (do not edit; do not remove these two markers) ───
# source repo : https://github.com/quarcs-lab/project2026e
# source path : code/plot_data_overview.py
# last commit : 690441f729ffd8b3ff0052057fd59a7176da7066  (2026-07-18)
# snapshot    : 2026-07-30 @ 9856b81
# refresh     : uv run python scripts/_sync_check.py . --root /path/to/project2026e
# ─── VENDORED SNAPSHOT — END ───
#!/usr/bin/env python3
"""Build the manuscript's four-panel data-introduction figure over Bolivia.

Consolidates the study's four data layers into a single 2x2 figure, styled to match
the manuscript's SDG choropleth (``notebooks/monitoring-views-comparison.qmd``):
a **light** theme on a CartoDB Positron basemap, serif type, black department
boundaries with labels, a north arrow, and a 200 km scale bar on every panel.

    (a) SDG outcomes    — the No Poverty (SDG 1) index, a polygon choropleth
    (b) Nighttime lights — the VIIRS mean (``average`` band) raster
    (c) Daytime embeddings — the 64-band embedding reduced to a PCA false-color RGB raster
    (d) Population        — the GHS-POP residential-population raster

All four panels are drawn in EPSG:3857 (Web Mercator) so panel (a) is identical to
the manuscript's Figure 7 panel (a) and every panel shares one coordinate system and
one framing. The three raster panels are masked to Bolivia and drawn semi-transparent
over the same basemap, so the surrounding-country context is identical across panels.

Because the embeddings GeoTIFF is ~3 GB, its PCA false-color composite is **precomputed
once** into a small, committed RGBA GeoTIFF (already warped to EPSG:3857); the figure
build reads that small raster instead of the 3 GB source.

Reusable from the command line or as a module (``notebooks/data-overview-panels.qmd``
imports :func:`plot_overview`). It reuses the per-layer read/mask/PCA helpers from the
sibling ``plot_ntl_raster``/``plot_embedding_raster``/``plot_population_raster`` modules.

Examples
--------
    # one-time: write the small PCA-RGB raster from the 3 GB embeddings GeoTIFF
    python code/plot_data_overview.py --precompute-embeddings

    # build the figure (reads the committed small RGB raster, the NTL and population rasters)
    python code/plot_data_overview.py
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
from rasterio.warp import Resampling, calculate_default_transform, reproject
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.colors import BoundaryNorm, ListedColormap, PowerNorm
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from matplotlib.offsetbox import AnchoredText
from mpl_toolkits.axes_grid1.anchored_artists import AnchoredSizeBar
import mapclassify as mc
import contextily as cx

# Sibling plotting modules (flat imports; code/ is on sys.path when run as a script or
# after the notebook's ``sys.path.insert(0, "../code")``).
import plot_ntl_raster as pnr
import plot_embedding_raster as peb
import plot_population_raster as ppr
import labels as L

WEB_MERCATOR = 3857
BOLIVIA_LAT = -17.0  # central latitude, to undo Web-Mercator scale distortion in the scale bar

# Defaults assume the repository root is the working directory.
DEFAULT_SDG_CSV = "data/sdg/sdg.csv"
DEFAULT_GEOJSON = "data/maps/bolivia339geoqueryOpt.geojson"
DEFAULT_REGION_CSV = "data/regionNames/regionNames.csv"
DEFAULT_NTL_TIF = "data/nighttimeLights/rasters/bolivia_ntl_viirs_2017.tif"
DEFAULT_EMB_TIF = "data/satelliteEmbeddings/rasters/bolivia_embeddings_2017.tif"
DEFAULT_EMB_RGB_TIF = "data/satelliteEmbeddings/rasters/bolivia_embeddings_pca_rgb_2017.tif"
DEFAULT_POP_TIF = "data/population/rasters/bolivia_ghspop_2017.tif"
DEFAULT_OUT = "images/fig-data-overview.png"

# Development-bracket palette = the five LISA colours ordered low -> high index (blue -> red),
# copied verbatim from monitoring-views-comparison.qmd so panel (a) matches Figure 7 exactly.
CLUSTER_COLORS = {
    "High-high": "#c23429", "Low-high": "#b5d8e7", "Low-low": "#4679b1",
    "High-low": "#efb16e", "Not significant": "#d3d3d3",
}
BRACKET_COLORS = [CLUSTER_COLORS[k] for k in
                  ["Low-low", "Low-high", "Not significant", "High-low", "High-high"]]
BRACKET_CMAP = ListedColormap(BRACKET_COLORS)


# --- Map furniture — copied from monitoring-views-comparison.qmd -------------------------
def add_basemap(ax, zorder=0):
    """CartoDB Positron basemap; a transient tile-server failure degrades to a plain
    background instead of breaking the render. ``zorder=0`` keeps the tiles *below* the
    raster ``imshow`` panels (which contextily's own ``imshow`` would otherwise cover)."""
    try:
        cx.add_basemap(ax, crs=f"EPSG:{WEB_MERCATOR}",
                       source=cx.providers.CartoDB.Positron, attribution=False, zorder=zorder)
    except Exception as exc:
        print(f"(basemap skipped: {type(exc).__name__})")


def add_north_arrow(ax, x=0.94, y=0.97):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.10), xycoords="axes fraction",
                ha="center", va="center", fontsize=10, fontweight="bold",
                arrowprops=dict(facecolor="black", edgecolor="black", width=3.0,
                                headwidth=8, headlength=7))


def add_scalebar(ax, length_km=200):
    bar_m = length_km * 1000.0 / math.cos(math.radians(BOLIVIA_LAT))
    sb = AnchoredSizeBar(ax.transData, bar_m, f"{length_km} km", loc="lower left",
                         pad=0.4, borderpad=0.6, sep=4, frameon=False, size_vertical=bar_m * 0.012,
                         color="#222222", fontproperties=fm.FontProperties(size=7))
    ax.add_artist(sb)


# --- Shared geometry helpers -------------------------------------------------------------
def _load_muni(geojson, region_csv):
    """Municipal geometry (as read) merged with department names, sorted by ``asdf_id``."""
    names = pd.read_csv(region_csv)[["asdf_id", "dep"]]
    gdf = (gpd.read_file(geojson).sort_values("asdf_id").reset_index(drop=True)
           .merge(names, on="asdf_id", how="left"))
    return gdf


def _bolivia_bbox_3857(gdf, margin=0.03):
    """Shared axis limits: the municipal total bounds in EPSG:3857 with a small margin,
    so all four panels frame the country identically."""
    minx, miny, maxx, maxy = gdf.to_crs(WEB_MERCATOR).total_bounds
    mx, my = (maxx - minx) * margin, (maxy - miny) * margin
    return (minx - mx, maxx + mx, miny - my, maxy + my)


def _dept_overlay(ax, gdf):
    """Black department boundaries + labels in EPSG:3857 (Figure-7 furniture)."""
    deps = gdf.dissolve(by="dep").reset_index().to_crs(WEB_MERCATOR)
    deps["pt"] = deps.geometry.representative_point()
    deps.boundary.plot(ax=ax, color="black", linewidth=0.5, zorder=6)
    for _, r in deps.iterrows():
        ax.text(r["pt"].x, r["pt"].y, r["dep"], ha="center", fontsize=5, zorder=7,
                bbox=dict(facecolor="white", alpha=0.8, pad=1, edgecolor="none"))


def _finish(ax, bb, title):
    """Shared per-panel finish: fixed frame, basemap, north arrow, scale bar, title."""
    ax.set_xlim(bb[0], bb[1])
    ax.set_ylim(bb[2], bb[3])
    ax.set_aspect("equal")
    add_basemap(ax)
    add_north_arrow(ax)
    add_scalebar(ax)
    ax.set_title(title, fontsize=10, loc="left")
    ax.set_axis_off()


def _warp_masked_to(masked, src_transform, src_crs, dst_crs=f"EPSG:{WEB_MERCATOR}"):
    """Warp a 2-D masked array to ``dst_crs`` for display; returns ``(masked_array, extent)``.

    Masked cells are carried through as NaN and re-masked after reprojection, so the
    Bolivia mask survives the warp. Nearest resampling avoids inventing values. This is a
    display-only reprojection — analysis values are never taken from the resampled copy.
    """
    dst = CRS.from_string(dst_crs)
    h, w = masked.shape
    left, top = src_transform.c, src_transform.f
    right, bottom = left + w * src_transform.a, top + h * src_transform.e
    dst_transform, dw, dh = calculate_default_transform(src_crs, dst, w, h, left, bottom, right, top)
    src = masked.filled(np.nan).astype("float64")
    dest = np.full((dh, dw), np.nan, dtype="float64")
    reproject(source=src, destination=dest, src_transform=src_transform, src_crs=src_crs,
              dst_transform=dst_transform, dst_crs=dst,
              src_nodata=np.nan, dst_nodata=np.nan, resampling=Resampling.nearest)
    d_left, d_top = dst_transform.c, dst_transform.f
    d_right, d_bottom = d_left + dw * dst_transform.a, d_top + dh * dst_transform.e
    extent = [d_left, d_right, d_bottom, d_top]
    return np.ma.masked_invalid(dest), extent


# --- Precompute: embeddings PCA false-color -> small committed RGBA raster (3857) --------
def write_embeddings_rgb_3857(emb_tif=DEFAULT_EMB_TIF, out_tif=DEFAULT_EMB_RGB_TIF,
                              boundary=DEFAULT_GEOJSON, seed=42):
    """Reduce the 64-band embeddings raster to a PCA false-color RGBA composite, warp it to
    EPSG:3857, and write a small 4-band uint8 GeoTIFF (R, G, B, alpha) with the PC1-3
    explained-variance stored as a tag. Run once; the figure build reads this small raster
    instead of the ~3 GB source. Returns the PC1-3 explained-variance fraction.
    """
    arr, inside, _extent, crs, _gdf = peb._read_stack(emb_tif, boundary)
    rgb, evr = peb._pca_rgb(arr, inside, seed=seed)          # (H, W, 3) in [0, 1]; outside = 0
    with rasterio.open(emb_tif) as src:
        transform = src.transform
    H, W = inside.shape

    # Stack R, G, B, and an alpha channel (1 inside Bolivia, 0 outside), then warp to 3857.
    src4 = np.stack([rgb[..., 0], rgb[..., 1], rgb[..., 2], inside.astype("float32")])  # (4, H, W)
    dst = CRS.from_epsg(WEB_MERCATOR)
    left, top = transform.c, transform.f
    right, bottom = left + W * transform.a, top + H * transform.e
    dst_transform, dw, dh = calculate_default_transform(crs, dst, W, H, left, bottom, right, top)
    dest = np.zeros((4, dh, dw), dtype="float32")            # uncovered pixels -> alpha 0
    reproject(source=src4, destination=dest, src_transform=transform, src_crs=crs,
              dst_transform=dst_transform, dst_crs=dst, resampling=Resampling.nearest)
    out = np.clip(dest * 255.0, 0, 255).astype("uint8")

    os.makedirs(os.path.dirname(out_tif) or ".", exist_ok=True)
    with rasterio.open(out_tif, "w", driver="GTiff", height=dh, width=dw, count=4,
                       dtype="uint8", crs=dst, transform=dst_transform,
                       compress="deflate", predictor=2) as ds:
        ds.write(out)
        ds.descriptions = ("R", "G", "B", "alpha")
        ds.update_tags(pc1_3_evr=f"{float(evr.sum()):.4f}")
    print(f"wrote {out_tif}  ({dw}x{dh}, 4-band uint8; PC1-3 EVR={float(evr.sum()):.3f})")
    return float(evr.sum())


# --- Panel drawers -----------------------------------------------------------------------
def _class_legend_labels(values, bins, interval):
    cls = mc.UserDefined(values, bins=bins).yb
    return [f"{interval[i]}  ({int((cls == i).sum())})" for i in range(len(interval))]


def _panel_sdg(ax, gdf, sdg_csv, bb):
    """(a) SDG 1 (No Poverty) polygon choropleth — the Figure-7 panel (a) recipe."""
    df = pd.read_csv(sdg_csv)[["asdf_id", "index_sdg1"]]
    g = gdf.merge(df, on="asdf_id", how="inner").to_crs(WEB_MERCATOR)
    vals = g["index_sdg1"].values
    bins = list(mc.FisherJenks(vals, k=5).bins)
    edges = [float(vals.min())] + bins
    interval = [f"{edges[i]:.1f}–{edges[i + 1]:.1f}" for i in range(5)]
    g.plot(column="index_sdg1", cmap=BRACKET_CMAP, alpha=0.85, scheme="UserDefined",
           classification_kwds={"bins": bins}, linewidth=0.1, edgecolor="white", legend=True,
           legend_kwds={"labels": _class_legend_labels(vals, bins, interval),
                        "loc": "lower right", "fontsize": 6, "title": "SDG 1 class (n)",
                        "frameon": True, "framealpha": 0.9}, ax=ax)
    _dept_overlay(ax, gdf)
    # Border key in the UPPER-RIGHT, just below the north arrow — that corner is off-country
    # (basemap), so it does not overlap the mapped territory. The municipal border is white on the
    # map (invisible on a white legend box), so the legend uses a light-grey proxy line; the map is
    # unchanged. Preserve the class legend (add_artist) before adding this second legend.
    class_leg = ax.get_legend()
    ax.add_artist(class_leg)
    border_handles = [Line2D([0], [0], color="black", lw=1.2, label="Department border (admin 1)"),
                      Line2D([0], [0], color="white", lw=1.2, label="Municipal border (admin 3)")]
    # Grey box so the white municipal line (matching the map exactly) is visible; the department
    # line is black and label text stays black — both readable on medium grey.
    ax.legend(handles=border_handles, loc="upper right", bbox_to_anchor=(0.99, 0.83),
              fontsize=5.5, frameon=True, facecolor="0.72", framealpha=0.95, edgecolor="0.45",
              borderpad=0.4, labelspacing=0.3, handlelength=1.6, handletextpad=0.5)
    _finish(ax, bb, "(a) SDG outcomes — No Poverty (SDG 1)")


def _panel_ntl(ax, fig, ntl_tif, gdf, bb):
    """(b) VIIRS mean radiance raster, magma / gamma stretch, masked to Bolivia."""
    with rasterio.open(ntl_tif) as src:
        crs, transform = src.crs, src.transform
        country = gdf.to_crs(crs).union_all()
        m = pnr._read_masked(src, "average", country)
    vmax = pnr._robust_cap(m, 99.0)
    warped, extent = _warp_masked_to(m, transform, crs)
    cmap = plt.get_cmap("magma").copy()
    cmap.set_bad(alpha=0.0)                                   # masked -> transparent (basemap shows)
    norm = PowerNorm(gamma=0.45, vmin=0.0, vmax=vmax, clip=True)
    im = ax.imshow(warped, extent=extent, origin="upper", norm=norm, cmap=cmap, alpha=0.85,
                   interpolation="nearest", zorder=5)
    _dept_overlay(ax, gdf)
    _finish(ax, bb, f"(b) {L.NTL} — VIIRS mean")
    _inset_colorbar(ax, fig, im, "Luminosity (nW/sr/cm$^2$)", top_plus=True)


def _panel_emb(ax, emb_rgb_tif, gdf, bb):
    """(c) Embeddings PCA false-color RGBA raster (precomputed, already in 3857)."""
    with rasterio.open(emb_rgb_tif) as src:
        rgba = src.read()                                    # (4, H, W) uint8
        b = src.bounds
        evr = src.tags().get("pc1_3_evr")
    extent = [b.left, b.right, b.bottom, b.top]
    img = np.transpose(rgba, (1, 2, 0)).astype("float32") / 255.0   # (H, W, 4)
    img[..., 3] *= 0.85                                      # inside ~0.85, outside stays 0
    ax.imshow(img, extent=extent, origin="upper", interpolation="nearest", zorder=5)
    _dept_overlay(ax, gdf)
    _finish(ax, bb, f"(c) {L.EMB} — PCA false-color")
    # A plain reading note in the lower-right box (matching panels (a)/(d)'s legend corner) rather
    # than a PC->colour key: the composite colours are blends and the PCs are abstract, so a channel
    # key does not help a reader. The rule for reading the map — similar colour = similar place — is
    # what a reviewer needs. Consistent with the paper's stance that the dimensions are not
    # individually interpretable, so no meaning is assigned to any colour.
    note = ("Similar colors = similar places\n"
            "(land cover, built-up, terrain);\n"
            "colors are arbitrary.")
    if evr is not None:
        note += f"\nPC1–3 explain {100 * float(evr):.0f}% of variance."
    at = AnchoredText(note, loc="lower right", frameon=True, pad=0.3, borderpad=0.5,
                      prop=dict(size=6))
    at.patch.set(facecolor="white", alpha=0.9, edgecolor="0.7", linewidth=0.5)
    at.set_zorder(8)
    ax.add_artist(at)


# Six quantile-informed "nice" population classes (people per ~500 m cell). The edges track the
# distribution of inhabited cells (median ~5, p75 ~15, p90 ~51, p99 ~1500), so populated places are
# separable at many levels. Empty cells (94.9% of the territory) are masked, not binned.
POP_BOUNDS = [0, 1, 5, 15, 50, 500, 1e9]
POP_LABELS = ["< 1", "1–5", "5–15", "15–50", "50–500", "500+"]


def _panel_pop(ax, fig, pop_tif, gdf, geojson, bb):
    """(d) GHS-POP population raster in six classes, inhabited cells only (empty cells reveal the
    basemap), warped from Mollweide to 3857."""
    m, _extent_native, crs, _gdf_r, transform = ppr._read_masked(pop_tif, geojson)
    # Keep only inhabited (>0) cells; empty and outside-Bolivia cells are masked -> transparent, so
    # the light basemap shows through and the scattered settlements stand out across the country.
    filled = m.filled(0.0)
    disp = np.ma.masked_array(filled, mask=np.ma.getmaskarray(m) | (filled <= 0.0))
    warped, extent = _warp_masked_to(disp, transform, crs)
    colors = plt.cm.viridis(np.linspace(0.0, 1.0, len(POP_LABELS)))
    cmap = ListedColormap(colors)
    cmap.set_bad(alpha=0.0)
    norm = BoundaryNorm(POP_BOUNDS, ncolors=len(POP_LABELS))
    ax.imshow(warped, extent=extent, origin="upper", norm=norm, cmap=cmap, alpha=0.85,
              interpolation="nearest", zorder=5)
    _dept_overlay(ax, gdf)
    _finish(ax, bb, "(d) Human settlement — Population count")
    handles = [Patch(facecolor=colors[i], edgecolor="none", label=POP_LABELS[i])
               for i in range(len(POP_LABELS))]
    ax.legend(handles=handles, loc="lower right", fontsize=6, frameon=True, framealpha=0.9,
              title="People per ~500 m cell", title_fontsize=6)


def _inset_colorbar(ax, fig, im, label, top_plus=False):
    """Slim horizontal colorbar hugging the off-country bottom-right corner, so it does not
    overlap the mapped territory (mirrors panel (c)'s note placement). Few ticks to stay legible
    on a narrow bar."""
    cax = ax.inset_axes([0.63, 0.11, 0.31, 0.025])
    cbar = fig.colorbar(im, cax=cax, orientation="horizontal")
    cbar.set_label(label, fontsize=6, labelpad=1)
    cbar.ax.tick_params(labelsize=6, length=2, pad=1)
    cbar.outline.set_linewidth(0.4)
    # Explicit, uncrowded ticks: 0, a nice value near the bar's midpoint (accounting for the
    # gamma stretch), and the true maximum at the right end (marked "+" so it reads as a ceiling).
    vmax = im.norm.vmax
    gamma = getattr(im.norm, "gamma", 1.0)
    mid = round(vmax * 0.5 ** (1.0 / gamma), 1)
    ticks = [0.0] + ([mid] if 0.0 < mid < vmax else []) + [vmax]
    cbar.set_ticks(ticks)
    labels = [f"{t:g}" for t in ticks]
    labels[-1] = f"{vmax:.1f}+" if top_plus else f"{vmax:g}"
    cbar.set_ticklabels(labels)


# --- Figure ------------------------------------------------------------------------------
def plot_overview(sdg_csv=DEFAULT_SDG_CSV, geojson=DEFAULT_GEOJSON, region_csv=DEFAULT_REGION_CSV,
                  ntl_tif=DEFAULT_NTL_TIF, emb_rgb_tif=DEFAULT_EMB_RGB_TIF,
                  pop_tif=DEFAULT_POP_TIF, out_png=DEFAULT_OUT, year=2017):
    """Build and save the four-panel data-introduction figure. Returns the figure."""
    gdf = _load_muni(geojson, region_csv)
    bb = _bolivia_bbox_3857(gdf)

    fig, axes = plt.subplots(2, 2, figsize=(13, 12),
                             gridspec_kw={"wspace": 0.04, "hspace": 0.14})
    axes = axes.ravel()
    _panel_sdg(axes[0], gdf, sdg_csv, bb)
    _panel_ntl(axes[1], fig, ntl_tif, gdf, bb)
    _panel_emb(axes[2], emb_rgb_tif, gdf, bb)
    _panel_pop(axes[3], fig, pop_tif, gdf, geojson, bb)

    if out_png:
        os.makedirs(os.path.dirname(out_png) or ".", exist_ok=True)
        fig.savefig(out_png, dpi=300, bbox_inches="tight")
    return fig


def _main():
    p = argparse.ArgumentParser(description="Four-panel data-introduction figure over Bolivia.")
    p.add_argument("--precompute-embeddings", action="store_true",
                   help="write the small PCA-RGB raster from the ~3 GB embeddings GeoTIFF, then exit")
    p.add_argument("--emb-tif", default=DEFAULT_EMB_TIF)
    p.add_argument("--emb-rgb-tif", default=DEFAULT_EMB_RGB_TIF)
    p.add_argument("--ntl-tif", default=DEFAULT_NTL_TIF)
    p.add_argument("--pop-tif", default=DEFAULT_POP_TIF)
    p.add_argument("--boundary", default=DEFAULT_GEOJSON)
    p.add_argument("--sdg-csv", default=DEFAULT_SDG_CSV)
    p.add_argument("--region-csv", default=DEFAULT_REGION_CSV)
    p.add_argument("--out", default=DEFAULT_OUT)
    a = p.parse_args()

    plt.switch_backend("Agg")
    if a.precompute_embeddings:
        if not os.path.exists(a.emb_tif):
            raise SystemExit(f"embeddings tif not found: {a.emb_tif}")
        write_embeddings_rgb_3857(a.emb_tif, a.emb_rgb_tif, a.boundary)
        return

    for f in (a.sdg_csv, a.boundary, a.region_csv, a.ntl_tif, a.emb_rgb_tif, a.pop_tif):
        if not os.path.exists(f):
            raise SystemExit(f"required input not found: {f}")
    plot_overview(a.sdg_csv, a.boundary, a.region_csv, a.ntl_tif, a.emb_rgb_tif,
                  a.pop_tif, a.out)
    print("wrote", a.out)


if __name__ == "__main__":
    _main()
