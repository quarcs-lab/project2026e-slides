"""Every path this deck touches, resolved relative to the DECK FOLDER.

The deck folder is the portable root. It works in place at ``slides/<deck>/`` inside the
manuscript repository, and it works when its contents *are* a repository root of their own.
Nothing in this module counts directory levels upward, which is the whole point: the scripts
used to open with ``ROOT = Path(__file__).resolve().parents[3]``, an assumption that broke
silently the moment the folder moved, in eleven files at once.

Three places an input can come from, always tried in this order:

1. **A live checkout** of the manuscript repository, named by ``$DECK_SOURCE_ROOT`` (or by
   ``--root`` on the verification scripts). Use this when you want the deck to track the paper.
2. **The vendored snapshot** in ``sources/``. This is the normal path, and the only one that
   exists in a fresh clone of the portable deck.
3. **Hugging Face**, for the one input too large to vendor. Data files only.

Everything raises :class:`Unavailable` rather than returning a path that does not exist, so a
missing input fails at the point of resolution with a message naming the file, rather than
thirty lines later inside pandas.

Usage, in every figure script::

    import pathlib, sys
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import _paths                       # noqa: E402
    _paths.bootstrap()
    DECKDIR = _paths.DECK

    df = pd.read_csv(_paths.table("tbl-popweighting-master.csv"))
    gdf = gpd.read_file(_paths.data("maps/bolivia339geoqueryOpt.geojson"))
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import sys

# ---- anchors. All downward from the deck folder; none look above it. --------------------
DECK = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = DECK / "scripts"
SOURCES = DECK / "sources"
FIGURES = DECK / "figures"
DERIVED = DECK / "derived"

#: A checkout of the manuscript repository, if you want the deck to read the live paper.
ENV_ROOT = "DECK_SOURCE_ROOT"
#: Set to any non-empty value to refuse the Hugging Face fallback and fail immediately.
#: Used by the test suite to prove that no figure except the nighttime-lights ones needs
#: the network, and useful on a plane.
ENV_OFFLINE = "DECK_NO_NETWORK"

#: Mirrors ``sources/code/hf_data.py``. Named here only so error messages can quote it.
HF_REPO = "cmg777/project2026e"

#: The one input too large to vendor: 118 MB, over GitHub's 100 MB per-file limit.
BIG_RASTER = "nighttimeLights/rasters/bolivia_ntl_viirs_2017.tif"

#: Upstream keeps the pickled fits in a dot-directory; the snapshot drops the dot, because
#: the manuscript repository's root .gitignore has the bare pattern ``.notebook-cache/``,
#: which git matches at any depth — a vendored ``sources/.notebook-cache/`` was silently
#: un-addable. See sources/README.md.
CACHE_UPSTREAM = ".notebook-cache"
CACHE_SNAPSHOT = "notebook-cache"

# Set by set_source_root(); overrides the environment variable when not None.
_root_override: pathlib.Path | None = None
_bootstrapped = False


class Unavailable(RuntimeError):
    """A required input is not in the snapshot, not in ``--root``, and not fetchable."""


# ---- sys.path -----------------------------------------------------------------------------
def bootstrap() -> None:
    """Put the deck, its ``scripts/`` and the vendored ``sources/code`` on ``sys.path``.

    Idempotent, and safe to call from any script at any time. Replaces the ad-hoc
    ``sys.path.insert`` calls that used to open each figure script.

    Three entries, in this precedence order:

    ``DECK``
        for ``_palette``, which lives at the deck root rather than in ``scripts/``.
        Previously the three raster figure scripts found it only by luck: they insert
        ``scripts/`` themselves, and ``_palette`` resolved because ``import _rasters``
        happened to run first and insert the deck root as a side effect.
    ``SCRIPTS``
        for ``_rasters``, ``_fourview``, ``_goals``, ``_paths``.
    ``SOURCES/"code"``
        for the vendored ``labels``, ``spatial_weights`` and ``plot_*`` modules. These must
        be imported **flat**, never as a ``code.labels`` package: a directory named ``code``
        on the path would shadow Python's own ``code`` module, and ``plot_data_overview``
        imports its siblings flat for the same reason. Hence no ``__init__.py`` under
        ``sources/``.
    """
    global _bootstrapped
    if _bootstrapped:
        return
    for entry in (SOURCES / "code", SCRIPTS, DECK):
        s = str(entry)
        if s in sys.path:
            sys.path.remove(s)
        sys.path.insert(0, s)
    _bootstrapped = True


# ---- the optional live checkout -----------------------------------------------------------
def set_source_root(p: str | os.PathLike | None) -> None:
    """Point resolution at a manuscript checkout, or clear it with ``None``.

    This is how ``--root`` is plumbed through from ``_sync_check.py`` and
    ``_source_checks.py``. It takes precedence over ``$DECK_SOURCE_ROOT``.
    """
    global _root_override
    _root_override = pathlib.Path(p).expanduser().resolve() if p is not None else None


def source_root() -> pathlib.Path | None:
    """The manuscript checkout to prefer, or ``None`` if none was named.

    Validated, because a typo must not silently degrade to the snapshot and leave you
    believing you verified against the live paper. A path that is named but is not a
    manuscript checkout raises rather than being ignored.
    """
    raw = _root_override or os.environ.get(ENV_ROOT) or None
    if raw is None:
        return None
    root = pathlib.Path(raw).expanduser().resolve()
    if not root.is_dir():
        raise Unavailable(f"{ENV_ROOT} points at {root}, which is not a directory.")
    if not (root / "tables").is_dir() or not (root / "code" / "labels.py").is_file():
        raise Unavailable(
            f"{root} does not look like a project2026e checkout "
            "(expected both tables/ and code/labels.py).\n"
            f"  Unset {ENV_ROOT} to use the vendored snapshot in sources/ instead."
        )
    return root


# ---- resolvers ----------------------------------------------------------------------------
def table(name: str) -> pathlib.Path:
    """A result table, by file name. ``tables/`` prefix optional.

    Order: live checkout, then the snapshot. **Never** Hugging Face — a table is small
    enough to vendor, so its absence is a packaging bug, not a network problem.
    """
    rel = name[len("tables/"):] if name.startswith("tables/") else name
    looked = []
    root = source_root()
    if root is not None:
        cand = root / "tables" / rel
        looked.append(cand)
        if cand.is_file():
            return cand
    cand = SOURCES / "tables" / rel
    looked.append(cand)
    if cand.is_file():
        return cand
    raise Unavailable(_not_found(f"tables/{rel}", looked))


def data(rel: str) -> pathlib.Path:
    """A data file, by path relative to ``data/``.

    Order: live checkout, snapshot, Hugging Face. The snapshot check duplicates what
    ``hf_data.data_path`` would do anyway, and that is deliberate: it means the common case
    never imports ``huggingface_hub``, and it means ``HF_DATA_FORCE_REMOTE`` — a debugging
    switch inside ``hf_data`` — cannot accidentally send a collaborator to the network for a
    900 KB GeoJSON.
    """
    rel = rel.lstrip("/")
    looked = []
    root = source_root()
    if root is not None:
        cand = root / "data" / rel
        looked.append(cand)
        if cand.is_file():
            return cand
    cand = SOURCES / "data" / rel
    looked.append(cand)
    if cand.is_file():
        return cand

    if os.environ.get(ENV_OFFLINE):
        raise Unavailable(_not_found(rel, looked, hf="refused: $" + ENV_OFFLINE + " is set"))
    try:
        bootstrap()
        from hf_data import data_path  # noqa: PLC0415  (vendored; only needed on this path)
        return pathlib.Path(data_path(rel))
    except Unavailable:
        raise
    except Exception as exc:  # network down, dataset moved, huggingface_hub missing
        raise Unavailable(_not_found(rel, looked, hf=f"fetch failed: {exc}")) from exc


def cache(name: str) -> pathlib.Path:
    """A pickled model fit, by file name (e.g. ``sdg1_combow.pkl``).

    Note the directory name flips between the two locations: upstream it is dotted,
    the snapshot's is not. See :data:`CACHE_SNAPSHOT`.
    """
    rel = pathlib.PurePath(name).name
    looked = []
    root = source_root()
    if root is not None:
        cand = root / CACHE_UPSTREAM / rel
        looked.append(cand)
        if cand.is_file():
            return cand
    cand = SOURCES / CACHE_SNAPSHOT / rel
    looked.append(cand)
    if cand.is_file():
        return cand
    raise Unavailable(_not_found(f"{CACHE_SNAPSHOT}/{rel}", looked))


def derived(rel: str) -> pathlib.Path:
    """A path under ``derived/``, with parents created. The only writable location
    outside ``figures/``.

    Anything the deck *computes* goes here, never into ``sources/``: the snapshot is what
    ``_sync_check.py`` hashes, so a regenerated file landing there would read as divergence
    from the manuscript, which is exactly backwards — and the natural fix, re-freezing,
    would quietly bless a deck-computed value as if it had come from the paper.
    """
    out = DERIVED / rel.lstrip("/")
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


def figure(name: str) -> pathlib.Path:
    """A path under ``figures/``, with parents created."""
    out = FIGURES / pathlib.PurePath(name).name
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


# ---- hashing, shared with _sync_check.py --------------------------------------------------
BANNER_BEGIN = "VENDORED SNAPSHOT — BEGIN"
BANNER_END = "VENDORED SNAPSHOT — END"


def sha256(path: str | os.PathLike, *, strip_banner: bool = False) -> str:
    """sha256 of a file, optionally ignoring a vendored-snapshot banner.

    ``strip_banner`` drops everything from the BEGIN marker line through the END marker line
    inclusive before hashing, which is what makes a banner-carrying vendored file still
    comparable to its upstream original. Without it every banner-carrying file would report
    as diverged from the day it was frozen, and a check that always fails is a check that
    gets ignored.
    """
    raw = pathlib.Path(path).read_bytes()
    if strip_banner:
        raw = strip_banner_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def strip_banner_bytes(raw: bytes) -> bytes:
    """Remove a delimited vendored-snapshot banner from file content. Idempotent."""
    text = raw.decode("utf-8", errors="surrogateescape")
    if BANNER_BEGIN not in text or BANNER_END not in text:
        return raw
    lines = text.splitlines(keepends=True)
    start = next((i for i, ln in enumerate(lines) if BANNER_BEGIN in ln), None)
    end = next((i for i, ln in enumerate(lines) if BANNER_END in ln), None)
    if start is None or end is None or end < start:
        return raw
    del lines[start:end + 1]
    return "".join(lines).encode("utf-8", errors="surrogateescape")


def has_banner(path: str | os.PathLike) -> bool:
    """True if the file carries both banner markers."""
    text = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
    return BANNER_BEGIN in text and BANNER_END in text


# ---- reporting ----------------------------------------------------------------------------
def describe() -> str:
    """One line for a script's log, so a surprising figure can be traced to its inputs."""
    try:
        root = source_root()
    except Unavailable as exc:
        return f"paths: INVALID root — {exc}"
    snap = "sources/" if (SOURCES / "tables").is_dir() else "MISSING"
    hf = "refused" if os.environ.get(ENV_OFFLINE) else "enabled"
    return f"paths: snapshot={snap}  root={root or '-'}  hf={hf}"


def _not_found(rel: str, looked: list[pathlib.Path], hf: str | None = None) -> str:
    """The message a missing input produces. The single place the offline story is told."""
    lines = [f"{rel} is not available.", "  looked in:"]
    for p in looked:
        lines.append(f"    {p}")
    if hf is not None:
        lines.append(f"    Hugging Face {HF_REPO}  ({hf})")
    if rel.endswith(BIG_RASTER) or BIG_RASTER in rel:
        lines += [
            "",
            "  This file is NOT vendored on purpose: it is 118 MB, over GitHub's 100 MB",
            "  per-file limit, so it is streamed from Hugging Face and cached under",
            "  ~/.cache/huggingface on first use.",
            "",
            "  It affects ONLY the nighttime-lights layer — scripts/fig-ntl-raster.py and",
            "  one panel of scripts/fig-data-layers.py. Every other figure in this deck",
            "  builds offline from sources/.",
        ]
    lines += [
        "",
        "  Fixes:",
        "    * connect to the network and re-run (the download is cached, once); or",
        f"    * point at a full manuscript checkout: {ENV_ROOT}=/path/to/project2026e uv run ...",
    ]
    return "\n".join(lines)


if __name__ == "__main__":  # pragma: no cover - manual check
    bootstrap()
    print(describe())
    print(f"DECK    {DECK}")
    print(f"SOURCES {SOURCES}")
    for probe in ("tbl-popweighting-master.csv",):
        print(f"table   {probe} -> {table(probe)}")
    for probe in ("maps/bolivia339geoqueryOpt.geojson", "sdg/sdg.csv"):
        print(f"data    {probe} -> {data(probe)}")
    print(f"cache   sdg1_combow.pkl -> {cache('sdg1_combow.pkl')}")
