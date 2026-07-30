# ─── VENDORED SNAPSHOT — BEGIN (do not edit; do not remove these two markers) ───
# source repo : https://github.com/quarcs-lab/project2026e
# source path : code/hf_data.py
# last commit : ba2ac79b754879849fa03e050a8a8f3ef1a56e5d  (2026-07-12)
# snapshot    : 2026-07-30 @ 9856b81
# refresh     : uv run python scripts/_sync_check.py . --root /path/to/project2026e
# ─── VENDORED SNAPSHOT — END ───
"""Local-first, Hugging-Face-fallback loader for the project's data files.

The ``data/`` folder is mirrored to the public HF dataset
``cmg777/project2026e`` (see ``scripts/upload_data_hf.py``). This helper lets
notebooks and scripts resolve a data file by its path *relative to* ``data/``:
if the file exists locally it is used as-is; otherwise it is downloaded from the
HF dataset repo and cached (in the standard HF cache) for reuse.

This keeps today's local + git workflow working unchanged (local files always
win) while letting large future datasets stream directly from the Hub instead of
being committed to git.

Usage
-----
>>> import pandas as pd
>>> from hf_data import data_path            # or: from code.hf_data import data_path
>>> df = pd.read_csv(data_path("satelliteEmbeddings/bolivia_pop_weighted_2017.csv"))

>>> import geopandas as gpd
>>> gdf = gpd.read_file(data_path("maps/bolivia339geoqueryOpt.geojson"))

Set the environment variable ``HF_DATA_FORCE_REMOTE=1`` to always fetch from the
Hub (ignoring any local copy) — handy for testing the streaming path.
"""

from __future__ import annotations

import os
from pathlib import Path

from huggingface_hub import hf_hub_download

REPO_ID = "cmg777/project2026e"
REPO_TYPE = "dataset"

# ``code/hf_data.py`` -> repo root -> data/
_LOCAL_ROOT = Path(__file__).resolve().parent.parent / "data"


def data_path(rel: str) -> str:
    """Return a filesystem path for a data file given its path relative to ``data/``.

    Prefers the local copy under ``data/``; if it is absent (or
    ``HF_DATA_FORCE_REMOTE`` is set), downloads and caches the file from the
    ``cmg777/project2026e`` HF dataset repo.

    Parameters
    ----------
    rel:
        Path relative to the ``data/`` folder, e.g.
        ``"satelliteEmbeddings/bolivia_pop_weighted_2017.csv"``.

    Returns
    -------
    str
        Absolute path to a readable local file.
    """
    rel = rel.lstrip("/")
    local = _LOCAL_ROOT / rel
    if local.exists() and not os.environ.get("HF_DATA_FORCE_REMOTE"):
        return str(local)
    return hf_hub_download(repo_id=REPO_ID, repo_type=REPO_TYPE, filename=rel)
