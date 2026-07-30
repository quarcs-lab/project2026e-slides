# ─── VENDORED SNAPSHOT — BEGIN (do not edit; do not remove these two markers) ───
# source repo : https://github.com/quarcs-lab/project2026e
# source path : code/plot_embedding_raster.py
# last commit : 690441f729ffd8b3ff0052057fd59a7176da7066  (2026-07-18)
# snapshot    : 2026-07-30 @ 9856b81
# refresh     : uv run python scripts/_sync_check.py . --root /path/to/project2026e
# ─── VENDORED SNAPSHOT — END ───
#!/usr/bin/env python3
"""Plot the Bolivia satellite-embeddings raster as a PCA false-color composite.

Reads the 64-band AlphaEarth / Google Satellite Embedding GeoTIFF (`A00`..`A63`) exported by
`code/plot-embeddings-raster.ipynb`, reduces the 64 dimensions to their first 3 principal
components, and renders a false-color RGB map masked to Bolivia. The colours are **arbitrary** —
they encode similarity in embedding space (a PCA rotation), not physical reflectance.

The full 64-band raster is large (~1–1.5 GB at 500 m) and is **not** committed to git; keep it
locally (e.g. `data/satelliteEmbeddings/rasters/`, which is gitignored) and/or on Hugging Face.
Only the rendered PNG is committed to the repository.

Example
-------
    python code/plot_embedding_raster.py \
        --tif data/satelliteEmbeddings/rasters/bolivia_embeddings_2017.tif
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
from sklearn.decomposition import PCA

# Sibling module (flat import; see code/labels.py for why this is not a package import).
import labels as L

EMB_COLS = [f"A{i:02d}" for i in range(64)]   # A00..A63
BOLIVIA_LAT = -16.7                            # aspect correction for a degrees-based map

DEFAULT_TIF = "data/satelliteEmbeddings/rasters/bolivia_embeddings_2017.tif"
DEFAULT_BOUNDARY = "data/maps/bolivia339geoqueryOpt.geojson"
DEFAULT_REGION_CSV = "data/regionNames/regionNames.csv"
DEFAULT_OUT = "images/fig-embeddings-pca-rgb.png"


def _load_boundary(path, crs):
    gdf = gpd.read_file(path)
    if gdf.crs is not None and crs is not None and str(gdf.crs) != str(crs):
        gdf = gdf.to_crs(crs)
    return gdf


def _read_stack(tif, boundary):
    """Return (bands [B,H,W] float32, inside [H,W] bool, extent, crs, gdf).

    `inside` marks pixels within Bolivia that are finite in every band.
    """
    with rasterio.open(tif) as src:
        arr = src.read()
        if arr.dtype != np.float32:
            arr = arr.astype("float32")
        crs, b, transform, nd = src.crs, src.bounds, src.transform, src.nodata
        gdf = _load_boundary(boundary, crs)
        country = gdf.union_all()
    _, H, W = arr.shape
    outside = geometry_mask([country], out_shape=(H, W), transform=transform, invert=False)
    finite = np.isfinite(arr).all(axis=0)
    if nd is not None and np.isfinite(nd):
        finite &= ~(arr == nd).any(axis=0)
    inside = (~outside) & finite
    extent = [b.left, b.right, b.bottom, b.top]
    return arr, inside, extent, crs, gdf


def raster_has_data(tif, boundary=DEFAULT_BOUNDARY):
    """True if the raster has a usable number of finite pixels inside Bolivia."""
    try:
        _, inside, *_ = _read_stack(tif, boundary)
    except Exception:
        return False
    return int(inside.sum()) > 100


def _pca_rgb(arr, inside, seed=42, sample=200_000):
    """First 3 PCs of the 64-band stack as an (H, W, 3) array in [0, 1]; outside pixels = 0."""
    _, H, W = arr.shape
    X = arr[:, inside].T                                   # (n_valid, 64)
    rng = np.random.RandomState(seed)
    idx = rng.choice(X.shape[0], size=min(sample, X.shape[0]), replace=False)
    pca = PCA(n_components=3, random_state=seed).fit(X[idx])
    pcs = pca.transform(X)                                 # (n_valid, 3)

    flat = np.zeros((H * W, 3), dtype="float32")
    inside_flat = inside.ravel()
    for c in range(3):
        lo, hi = np.percentile(pcs[:, c], [2, 98])
        chan = np.clip((pcs[:, c] - lo) / (hi - lo + 1e-12), 0.0, 1.0)
        flat[inside_flat, c] = chan
    return flat.reshape(H, W, 3), pca.explained_variance_ratio_


def plot_pca_rgb(tif, *, boundary=DEFAULT_BOUNDARY, region_csv=None, out_png=None,
                 year=2017, title=None, facecolor="black", text_color="white"):
    """Render the embeddings PCA false-color map masked to Bolivia, in an "Earth at night"
    dark theme matching the nighttime-lights and population figures. Returns the figure.

    The false-colors encode similarity in embedding space (a PCA rotation), not physical
    reflectance. Pixels outside Bolivia are transparent (alpha 0), so they show the dark
    ``facecolor`` background; white department boundaries and faint municipal boundaries
    overlay the composite. There is no web basemap, so the figure renders offline.
    """
    arr, inside, extent, crs, gdf = _read_stack(tif, boundary)
    rgb, evr = _pca_rgb(arr, inside)
    rgba = np.dstack([rgb, inside.astype("float32")])      # alpha 0 outside Bolivia

    deps = None
    if region_csv:
        names = pd.read_csv(region_csv)[["asdf_id", "dep"]]
        deps = gdf.merge(names, on="asdf_id", how="left").dissolve(by="dep").reset_index()

    aspect = (1.0 / math.cos(math.radians(BOLIVIA_LAT))) if (crs and crs.is_geographic) else 1.0
    if title is None:
        title = f"{L.EMB}, {year} — PCA false-color (PC1–3 → RGB)"

    fig, ax = plt.subplots(figsize=(7.5, 7.5), facecolor=facecolor)
    ax.set_facecolor(facecolor)
    ax.imshow(rgba, extent=extent, origin="upper")
    if deps is not None:
        deps.boundary.plot(ax=ax, color="white", linewidth=0.6)
    gdf.boundary.plot(ax=ax, color="skyblue", linewidth=0.15, alpha=0.55)
    ax.set_aspect(aspect)
    ax.set_title(title, color=text_color)
    ax.set_axis_off()
    ax.text(0.01, 0.01, f"PC1–3 explain {100 * float(evr.sum()):.0f}% of embedding variance",
            transform=ax.transAxes, fontsize=7, color="0.8", va="bottom", ha="left")

    if out_png:
        os.makedirs(os.path.dirname(out_png) or ".", exist_ok=True)
        fig.savefig(out_png, dpi=300, bbox_inches="tight", facecolor=facecolor)
    return fig


def _main():
    p = argparse.ArgumentParser(description="PCA false-color map of the Bolivia embeddings raster.")
    p.add_argument("--tif", default=DEFAULT_TIF)
    p.add_argument("--boundary", default=DEFAULT_BOUNDARY)
    p.add_argument("--region-csv", default=DEFAULT_REGION_CSV,
                   help="region-name CSV for department boundaries (pass '' to skip)")
    p.add_argument("--out", default=DEFAULT_OUT)
    p.add_argument("--year", type=int, default=2017)
    a = p.parse_args()

    plt.switch_backend("Agg")
    if not os.path.exists(a.tif):
        raise SystemExit(f"tif not found: {a.tif} (run code/plot-embeddings-raster.ipynb in Colab)")
    if not raster_has_data(a.tif, a.boundary):
        raise SystemExit("raster has no finite data inside Bolivia — re-export the GeoTIFF.")
    plot_pca_rgb(a.tif, boundary=a.boundary, region_csv=(a.region_csv or None),
                 out_png=a.out, year=a.year)
    print("wrote", a.out)


if __name__ == "__main__":
    _main()
