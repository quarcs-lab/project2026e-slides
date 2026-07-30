# ─── VENDORED SNAPSHOT — BEGIN (do not edit; do not remove these two markers) ───
# source repo : https://github.com/quarcs-lab/project2026e
# source path : code/spatial_weights.py
# last commit : 314cb381afd5778720c16ee4a12d2aefe0b1b66c  (2026-07-20)
# snapshot    : 2026-07-30 @ 9856b81
# refresh     : uv run python scripts/_sync_check.py . --root /path/to/project2026e
# ─── VENDORED SNAPSHOT — END ───
#!/usr/bin/env python3
"""The project's ONE spatial-weights definition: queen contiguity, islands repaired.

Every global Moran's I and every LISA classification in the manuscript -- Table 1's
clustering column, Table 3's four-view comparison, the three body cluster maps, and
all of Appendices D and E -- must be built from the same matrix. This module is that
matrix, so a change to the neighbour definition happens in one place rather than in
the four call sites that used to carry their own copy.

Import pattern (matches ``code/labels.py``; flat import via ``sys.path``, never
``from code.spatial_weights import ...`` -- ``code`` shadows a standard-library
module name)::

    import os, sys
    sys.path.insert(0, os.path.abspath("../code"))   # from notebooks/
    from spatial_weights import queen_repaired

    W, meta = queen_repaired(gdf)                     # row-standardised, no islands

WHY QUEEN CONTIGUITY
--------------------
Two municipalities are neighbours if their boundaries touch at all, along an edge or
at a single point. That is the definition a reader can picture from a map, and it
respects the real geography: a large municipality with many small ones around it gets
many neighbours, an isolated one gets few. A k-nearest-neighbour rule instead forces
every unit to have exactly k neighbours regardless of whether they adjoin it, which
is arbitrary in a country whose municipal areas differ by orders of magnitude.

THE ISLAND, AND WHY IT MUST BE REPAIRED RATHER THAN DROPPED
-----------------------------------------------------------
Moran's I and LISA are undefined for a unit with an empty neighbour set -- its
spatial lag would divide by zero -- so an island cannot simply be left in. Bolivia
has exactly one: **Coipasa** (Oruro, ``asdf_id`` 311), alone on the Salar de Coipasa
salt flat. Dropping it would silently change the sample from 339 to 338 municipalities
and break the row alignment every cached prediction depends on.

Instead the island is joined to its ``k`` nearest municipalities by centroid distance,
where ``k`` defaults to the **rounded mean queen cardinality** over all rows (islands
counted as zero) -- i.e. the island is given the number of neighbours an average
municipality has, rather than an arbitrary one. For the 339 Bolivian municipalities
that mean is 5.516, so k = 6. The graft is **symmetrised**: each of those six also
gains the island, so the matrix stays symmetric, as queen contiguity itself is.

DO NOT use ``libpysal.weights.attach_islands`` for this. It attaches an island to its
single nearest neighbour, not to k of them.

ROW ORDER IS LOAD-BEARING
-------------------------
Weights are positional. Callers must pass a frame already sorted the way the cached
predictions were computed -- ``sort_values("asdf_id").reset_index(drop=True)`` -- or
the neighbour sets will be valid but different from the published ones.
"""

from __future__ import annotations

import numpy as np
from libpysal.weights import KNN, Queen, W

__all__ = ["queen_repaired", "ISLAND_K_BOLIVIA"]

#: k used to reconnect an island for the 339 Bolivian municipalities, i.e.
#: ``round(5.516)``. Passed explicitly only when a caller wants to pin it; the
#: default path recomputes it from the frame so the module stays general.
ISLAND_K_BOLIVIA = 6


def queen_repaired(gdf, k=None, transform="r"):
    """Row-standardised queen-contiguity weights with every island reconnected.

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        Polygons, already in the row order the analysis uses (see module docstring).
    k : int, optional
        Number of nearest neighbours to attach each island to. Defaults to the
        rounded mean queen cardinality over all rows, islands counted as zero.
    transform : str, default "r"
        Weights transform. "r" row-standardises, so each unit's weights sum to one
        and the spatial lag is a plain neighbourhood average.

    Returns
    -------
    (W, meta) : tuple
        ``W`` is the ``libpysal`` weights object. ``meta`` is a dict with
        ``islands`` (row positions repaired), ``k``, ``mean_card_queen`` (before the
        graft) and ``mean_card`` (after), so a notebook can print what it built.
    """
    # The island is expected and is repaired below, so libpysal's disconnected-components
    # warning is noise here. The `if w.islands` check after the rebuild is the real guard.
    queen = Queen.from_dataframe(gdf, use_index=False, silence_warnings=True)
    cards = np.array([queen.cardinalities[i] for i in range(len(gdf))], dtype=float)
    mean_card_queen = float(cards.mean())

    if k is None:
        k = int(round(mean_card_queen))
    if k < 1:
        raise ValueError(f"k must be at least 1, got {k}")

    neighbors = {i: list(v) for i, v in queen.neighbors.items()}
    islands = list(queen.islands)

    if islands:
        knn = KNN.from_dataframe(gdf, k=k)
        for isl in islands:
            attached = [int(j) for j in knn.neighbors[isl]]
            neighbors[isl] = attached
            for j in attached:                      # symmetrise the graft
                if isl not in neighbors[j]:
                    neighbors[j] = neighbors[j] + [isl]

    w = W(neighbors, silence_warnings=True)

    # A silent island would make every downstream statistic wrong, so fail loudly.
    if w.islands:
        raise RuntimeError(f"islands remain after repair: {w.islands}")
    if len(w.neighbors) != len(gdf):
        raise RuntimeError(f"weights cover {len(w.neighbors)} of {len(gdf)} rows")

    w.transform = transform
    meta = {
        "islands": islands,
        "k": k,
        "mean_card_queen": mean_card_queen,
        "mean_card": float(np.mean([len(v) for v in neighbors.values()])),
    }
    return w, meta


def describe(meta, n=None):
    """One-line summary of what :func:`queen_repaired` built, for notebook output."""
    head = f"Queen contiguity{f' over {n} units' if n else ''}"
    body = f"mean neighbours {meta['mean_card_queen']:.3f}"
    if meta["islands"]:
        body += (f" -> {meta['mean_card']:.3f} after reconnecting "
                 f"{len(meta['islands'])} island(s) to their {meta['k']} nearest")
    else:
        body += ", no islands"
    return f"{head}: {body}"


if __name__ == "__main__":  # pragma: no cover - manual check
    import geopandas as gpd

    g = (gpd.read_file("data/maps/bolivia339geoqueryOpt.geojson")
           .sort_values("asdf_id").reset_index(drop=True))
    w, m = queen_repaired(g)
    print(describe(m, len(g)))
    print("islands repaired:", m["islands"], "| k =", m["k"])
    for isl in m["islands"]:
        print(f"  row {isl} -> {w.neighbors[isl]}")
