#!/usr/bin/env python3
"""Snapshot-integrity checks for a portable deck (the companion to Tier S).

WHAT THIS IS FOR
This deck ships a frozen copy of every input it needs in ``sources/`` — result tables, model
fits, geometry, rasters, and seven Python modules — so that it renders, regenerates and verifies
itself with no reference to the manuscript repository it was built from. That snapshot buys
portability and immediately creates two new ways to be wrong:

  1. **The snapshot rots.** The paper is revised, a table is regenerated, and the deck keeps
     drawing last month's figure from a copy nobody remembered was a copy.
  2. **The snapshot is edited.** Someone "fixes" a number in ``sources/tables/`` instead of
     fixing it upstream, and the deck now disagrees with the published paper while every other
     check passes, because every other check reads the same edited file.

``_source_checks.py`` (Tier S) verifies that the *slides* match the *tables*. This script
verifies that the *tables* still match the *paper*. Neither subsumes the other, and the two
failures call for opposite responses — see FAILURE MEANS DIFFERENT THINGS below.

WHY sha256 AND NOT THE GIT SHA
The provenance record stores both, but only the content hash is ever compared. A commit SHA
answers "which revision did this come from", which is a question about narrative; it does not
answer "is this byte-identical to upstream today", which is the question that matters. Concretely
it fails in both directions:

    a rebase / filter-repo / rename   ->  SHA changes, content identical   ->  false alarm
    an uncommitted edit under --root  ->  SHA identical, content changed   ->  MISSED DIVERGENCE

The second is precisely the failure this script exists to catch, so the git SHA is recorded for
traceability and `git log` archaeology, and never branched on.

THE BANNER PROBLEM
A provenance header makes a vendored file no longer byte-identical to its source, which is the
very property that made diffing cheap. Two consequences, both forced rather than chosen:

  * **Only the seven ``.py`` files carry a banner.** A comment line at the top of a CSV breaks
    ``csv.DictReader`` and ``pandas.read_csv``; ``.geojson``, ``.tif`` and ``.pkl`` obviously
    cannot carry one. So every non-Python file in the snapshot is byte-identical to its original
    and ``PROVENANCE.toml`` is its only record.
  * **Banners are delimited and stripped before hashing.** ``PROVENANCE.toml`` stores ``sha256``
    (as vendored) and ``sha256_body`` (banner removed), and only the latter is compared upstream.
    Hash the raw bytes instead and all seven modules report as diverged from the day they were
    frozen — and a check that always fails is worse than no check, because it gets ignored.

FAILURE MEANS DIFFERENT THINGS
    Tier S fails                 -> the DECK is wrong. Fix the slide or the manifest.
    this script says UPSTREAM ADVANCED  -> the PAPER moved. Decide whether to take the change,
                                           copy it in, re-freeze, and rebuild the figures.
    this script says SNAPSHOT EDITED    -> someone edited the frozen copy. Revert it, and make
                                           the change upstream instead.

USAGE
    uv run python scripts/_sync_check.py <deck-dir>
    uv run python scripts/_sync_check.py <deck-dir> --root /path/to/project2026e
    uv run python scripts/_sync_check.py <deck-dir> --root /path/to/project2026e --freeze
    uv run python scripts/_sync_check.py <deck-dir> --root /path/to/project2026e --freeze-claims

Without ``--root`` this is a **self-audit**, not a no-op: every hash is recomputed against the
local snapshot and any unlisted or missing file fails. That catches an accidental edit even with
no manuscript checkout in sight. The upstream comparison is simply reported as skipped.

``--freeze`` rewrites ``PROVENANCE.toml`` from the current local content plus git metadata read
from ``--root``. It deliberately **does not copy files**: copying stays an explicit human step, so
freezing can never quietly overwrite a copy that was pinned on purpose.

Exit codes: 0 = in sync / snapshot intact, 1 = divergence, corruption, or file-set mismatch,
2 = usage error, 3 = --root is not a manuscript checkout.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys
import tomllib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _paths  # noqa: E402

OK, WARN, FAIL, SKIP = "ok", "warn", "fail", "skip"
GLYPH = {OK: "[✓]", WARN: "[~]", FAIL: "[✗]", SKIP: "[·]"}

#: Files inside sources/ that are documentation or provenance, not vendored content.
EXEMPT = {"README.md", "PROVENANCE.toml", "claims.toml"}

#: The seven modules that may carry a provenance banner (see THE BANNER PROBLEM).
BANNERED_SUFFIX = ".py"

MANIFEST = "PROVENANCE.toml"
CLAIMS = "claims.toml"

SOURCE_REPO = "https://github.com/quarcs-lab/project2026e"


class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []

    def add(self, state: str, name: str, detail: str = "") -> None:
        self.rows.append((state, name, detail))

    def count(self, *states: str) -> int:
        return sum(1 for s, _, _ in self.rows if s in states)

    def render(self) -> None:
        for state, name, detail in self.rows:
            print(f"{GLYPH[state]} {name}{('  — ' + detail) if detail else ''}")


# ---- git metadata -------------------------------------------------------------------------
def git_info(root: pathlib.Path, rel: str) -> tuple[str, str]:
    """(last commit touching `rel`, its date). ('untracked', mtime) when git knows nothing.

    The nine pickled fits are gitignored upstream, so they genuinely have no git object. That
    is a fact to record, not an error to raise.
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "log", "-1", "--format=%H %cs", "--", rel],
            capture_output=True, text=True, timeout=30,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        out = ""
    if out:
        sha, _, date = out.partition(" ")
        return sha, date
    src = root / rel
    if src.exists():
        import datetime
        d = datetime.date.fromtimestamp(src.stat().st_mtime).isoformat()
        return "untracked", d
    return "untracked", "unknown"


def git_head(root: pathlib.Path) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=30,
        ).stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


# ---- the snapshot on disk -----------------------------------------------------------------
def upstream_of(rel: str) -> str:
    """The path this snapshot entry came from in the manuscript repository.

    One rename to undo: the pickled fits live in a dot-directory upstream, and the snapshot
    drops the dot because the repository's root .gitignore pattern ``.notebook-cache/`` matches
    at any depth and silently refused to track them. See sources/README.md.
    """
    if rel.startswith(_paths.CACHE_SNAPSHOT + "/"):
        return _paths.CACHE_UPSTREAM + rel[len(_paths.CACHE_SNAPSHOT):]
    return rel


def walk_snapshot(sources: pathlib.Path) -> list[str]:
    """Every vendored file, as a POSIX path relative to sources/, sorted. Exemptions dropped."""
    out = []
    for p in sorted(sources.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(sources).as_posix()
        if rel in EXEMPT or p.name == ".DS_Store" or "__pycache__" in rel:
            continue
        out.append(rel)
    return out


def hashes(path: pathlib.Path) -> tuple[str, str, bool]:
    """(sha256 as-is, sha256 with any banner stripped, carries a banner)."""
    bannered = path.suffix == BANNERED_SUFFIX and _paths.has_banner(path)
    raw = _paths.sha256(path)
    body = _paths.sha256(path, strip_banner=True) if bannered else raw
    return raw, body, bannered


# ---- freeze -------------------------------------------------------------------------------
def freeze(deck: pathlib.Path, root: pathlib.Path) -> int:
    sources = deck / "sources"
    files = walk_snapshot(sources)
    head = git_head(root)
    import datetime
    today = datetime.date.today().isoformat()

    lines = [
        "# Provenance for the vendored snapshot in this directory.",
        "#",
        "# Written by `scripts/_sync_check.py --root <checkout> --freeze`. Do not hand-edit: the",
        "# hashes are what makes divergence detectable, and a hand-corrected hash is a lie that",
        "# silences the only check that would have caught the problem.",
        "#",
        "# `sha256` is the file as vendored; `sha256_body` is the same file with any vendored-snapshot",
        "# banner stripped, and it is `sha256_body` that gets compared upstream. Only .py files carry",
        "# a banner — a comment line would break every CSV reader, and binaries cannot carry one at all.",
        "#",
        "# `last_commit = \"untracked\"` is normal, not an error: the pickled fits are gitignored",
        "# upstream, so git has no object for them and the date is the file's mtime.",
        "",
        "[meta]",
        f'source_repo     = "{SOURCE_REPO}"',
        f'snapshot_commit = "{head}"',
        f'snapshot_date   = "{today}"',
        'frozen_by       = "scripts/_sync_check.py --root <checkout> --freeze"',
        'hash            = "sha256"',
        'note = """',
        "Read-only snapshot. Paths below are relative to BOTH sources/ and the manuscript repository",
        "root, with one deliberate exception: upstream `.notebook-cache/` is vendored as",
        "`notebook-cache/` (no dot), because the repository's root .gitignore pattern",
        "`.notebook-cache/` matches at any depth and would have silently refused to track these",
        "files. `_sync_check.py` maps the name back when comparing.",
        '"""',
        "",
    ]

    missing = []
    for rel in files:
        p = sources / rel
        raw, body, bannered = hashes(p)
        up = upstream_of(rel)
        sha, date = git_info(root, up)
        if not (root / up).exists():
            missing.append(rel)
        lines += [
            "[[file]]",
            f'path        = "{rel}"',
            f'upstream    = "{up}"',
            f'sha256      = "{raw}"',
        ]
        if bannered:
            lines.append(f'sha256_body = "{body}"')
        lines += [
            f"bytes       = {p.stat().st_size}",
            f"banner      = {'true' if bannered else 'false'}",
            f'last_commit = "{sha}"',
            f'last_date   = "{date}"',
            "",
        ]

    (sources / MANIFEST).write_text("\n".join(lines), encoding="utf-8")
    print(f"[✓] wrote sources/{MANIFEST}: {len(files)} file(s), snapshot commit {head[:7]}")
    if missing:
        print(f"[~] {len(missing)} file(s) have no upstream counterpart under {root}:")
        for rel in missing:
            print(f"      {rel}")
        print("    Recorded anyway. Check whether they were renamed or moved to legacy/.")
    return 0


# ---- freeze the manuscript claims ---------------------------------------------------------
def freeze_claims(deck: pathlib.Path, root: pathlib.Path) -> int:
    """Snapshot the numbers the deck takes from the manuscript's PROSE.

    Fifteen values on the slides are stated in the paper's text and appear in no table cell.
    Upstream those were verified by regex against ``index.qmd``. The manuscript text does not
    ship with this deck, so instead we record each matched value, the line it was found on, and
    the sha256 of that line. Hashing the line rather than storing it is what keeps the paper out
    of a repository that may be handed to collaborators, while still letting a ``--root`` run
    distinguish *the number changed* from *the prose moved*.

    Refuses if any pattern fails to match: freezing a broken regex would bake in a check that
    can never fire again, which is how eight of the twelve original regexes rotted unnoticed.
    """
    import hashlib

    manifest = deck / "numbers.toml"
    if not manifest.exists():
        print(f"[✗] {manifest} not found — nothing to freeze.")
        return 1
    doc = tomllib.loads(manifest.read_text(encoding="utf-8"))
    entries = [e for e in doc.get("number", [])
               if e.get("source") in ("index.qmd", CLAIMS) and e.get("pattern")]
    if not entries:
        print("[✗] no manuscript-sourced entries found in numbers.toml "
              f'(expected source = "index.qmd" or "{CLAIMS}" with a pattern).')
        return 1

    src = root / "index.qmd"
    if not src.exists():
        print(f"[✗] {src} not found — cannot freeze claims without the manuscript.")
        return 1
    text = src.read_text(encoding="utf-8")
    lines = text.splitlines()

    out, bad = [], []
    for e in entries:
        pat = e["pattern"]
        m = re.search(pat, text)
        if not m:
            bad.append((e.get("value"), pat))
            continue
        ln = text[:m.start()].count("\n") + 1
        line_sha = hashlib.sha256(lines[ln - 1].strip().encode("utf-8")).hexdigest()
        key = e.get("frozen") or slugify(e.get("claim", str(e.get("value"))))
        out.append({
            "key": key, "value": e["value"], "pattern": pat,
            "line": ln, "line_sha256": line_sha, "claim": e.get("claim", ""),
        })

    if bad:
        print(f"[✗] {len(bad)} pattern(s) no longer match {src} — refusing to freeze:")
        for val, pat in bad:
            print(f"      {val}: {pat}")
        print("    Fix the pattern in numbers.toml first. Freezing a dead regex bakes in a")
        print("    check that can never fire again.")
        return 1

    keys = [c["key"] for c in out]
    dupes = {k for k in keys if keys.count(k) > 1}
    if dupes:
        print(f"[✗] duplicate claim key(s): {sorted(dupes)}. Set an explicit `frozen = \"...\"`.")
        return 1

    import datetime
    body = [
        "# Frozen manuscript claims — the numbers this deck takes from the paper's PROSE.",
        "#",
        "# Written by `scripts/_sync_check.py --root <checkout> --freeze-claims`.",
        "#",
        "# These are the values for which no `tables/*.csv` cell exists. numbers.toml's own header",
        "# explains the preference: a cell survives a prose edit, a regex does not — and eight of",
        "# twelve regexes in an earlier manifest had already gone stale by the time anyone checked.",
        "#",
        "# THE MANUSCRIPT TEXT IS NOT SHIPPED. Each entry records the matched VALUE, the LINE it was",
        "# found on, and the sha256 of that line. Storing the hash rather than the sentence is what",
        "# keeps the paper out of this repository while still failing loudly if the number changes.",
        "#",
        "# Standalone, `_source_checks.py` verifies the slides against these frozen values, and is",
        "# fail-closed: a missing key is a failure, exactly like a missing manifest. Given",
        "# `--root <checkout>` it re-runs each pattern against the live manuscript and separates",
        "#   the number changed        -> FAIL",
        "#   the value holds, prose moved -> WARN (re-freeze)",
        "",
        "[meta]",
        f'source        = "index.qmd"',
        f'source_sha256 = "{_paths.sha256(src)}"',
        f'source_commit = "{git_head(root)}"',
        f"source_lines  = {len(lines)}",
        f'frozen        = "{datetime.date.today().isoformat()}"',
        "",
    ]
    for c in sorted(out, key=lambda c: c["line"]):
        body += ["[[claim]]", f'key         = "{c["key"]}"']
        body.append(f'value       = {c["value"]}')
        body.append(f"pattern     = '{c['pattern']}'")
        body += [
            f"line        = {c['line']}",
            f'line_sha256 = "{c["line_sha256"]}"',
        ]
        if c["claim"]:
            body.append(f'claim       = "{c["claim"]}"')
        body.append("")

    (deck / "sources" / CLAIMS).write_text("\n".join(body), encoding="utf-8")
    print(f"[✓] wrote sources/{CLAIMS}: {len(out)} claim(s) frozen from index.qmd "
          f"@{git_head(root)[:7]}")
    print("    Now set `source = \"claims.toml\"` + `frozen = \"<key>\"` on those numbers.toml")
    print("    entries (keep `pattern` — it is what --root re-verification uses).")
    return 0


def slugify(s: str) -> str:
    s = re.sub(r"\(.*?\)", "", s).strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:48] or "claim"


# ---- check --------------------------------------------------------------------------------
def check(deck: pathlib.Path, root: pathlib.Path | None) -> int:
    sources = deck / "sources"
    rep = Report()

    print(f"== portable-deck snapshot check: {deck} ==")
    if not sources.is_dir():
        print(f"\n[✗] no sources/ directory. This deck is not self-contained.")
        print("SYNC SUMMARY: no snapshot.  RESULT: FAIL")
        return 1

    man_path = sources / MANIFEST
    if not man_path.exists():
        print(f"\n[✗] sources/{MANIFEST} is missing.")
        print(f"    Create it:  _sync_check.py {deck} --root /path/to/project2026e --freeze")
        print("SYNC SUMMARY: manifest missing.  RESULT: FAIL")
        return 1
    try:
        man = tomllib.loads(man_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        print(f"\n[✗] sources/{MANIFEST} does not parse: {exc}")
        print("SYNC SUMMARY: manifest malformed.  RESULT: FAIL")
        return 1

    meta = man.get("meta", {})
    listed = {e["path"]: e for e in man.get("file", [])}
    on_disk = set(walk_snapshot(sources))
    print(f"   snapshot: {len(on_disk)} file(s)   frozen: {meta.get('snapshot_date', '?')} "
          f"@{str(meta.get('snapshot_commit', '?'))[:7]}")
    print(f"   upstream: {root if root else '(not given — comparison skipped)'}\n")

    # --- 1. the file set matches the manifest, both ways -----------------------------------
    unlisted = sorted(on_disk - set(listed))
    absent = sorted(set(listed) - on_disk)
    for rel in unlisted:
        rep.add(FAIL, f"{rel}", "present in sources/ but not in the manifest — re-freeze")
    for rel in absent:
        rep.add(FAIL, f"{rel}", "in the manifest but missing from sources/")
    if not unlisted and not absent:
        rep.add(OK, f"file set matches the manifest", f"{len(on_disk)} file(s)")

    # --- 2. every hash still matches, and every declared banner is still there -------------
    edited = []
    for rel in sorted(on_disk & set(listed)):
        e, p = listed[rel], sources / rel
        raw, body, bannered = hashes(p)
        if e.get("banner") and not bannered:
            rep.add(FAIL, rel, "declared banner is gone — the snapshot was hand-edited")
            edited.append(rel)
            continue
        if not e.get("banner") and bannered:
            rep.add(FAIL, rel, "carries a banner the manifest does not declare — re-freeze")
            edited.append(rel)
            continue
        if raw != e.get("sha256"):
            rep.add(FAIL, rel, f"content changed since freezing "
                               f"({e.get('sha256', '')[:12]} → {raw[:12]})")
            edited.append(rel)
        # else: intact; reported in aggregate below to keep the output readable.
    intact = len(on_disk & set(listed)) - len(edited)
    if intact:
        rep.add(OK, "vendored content unchanged since freezing", f"{intact} file(s)")

    # --- 3. upstream comparison ------------------------------------------------------------
    if root is None:
        rep.add(SKIP, "upstream comparison", "no --root given")
    else:
        verdicts = {"sync": 0}
        for rel in sorted(on_disk & set(listed)):
            e = listed[rel]
            up = root / e.get("upstream", upstream_of(rel))
            if not up.exists():
                rep.add(FAIL, rel, f"MISSING UPSTREAM at {up} — renamed, or moved to legacy/?")
                continue
            local_body = hashes(sources / rel)[1]
            up_body = _paths.sha256(up, strip_banner=True)
            recorded = e.get("sha256_body") or e.get("sha256")
            local_moved = local_body != recorded
            up_moved = up_body != recorded
            if not local_moved and not up_moved:
                verdicts["sync"] += 1
            elif not local_moved and up_moved:
                rep.add(FAIL, rel, "UPSTREAM ADVANCED — copy it in, re-freeze, rebuild figures")
            elif local_moved and not up_moved:
                rep.add(FAIL, rel, "SNAPSHOT EDITED LOCALLY — revert it; change upstream instead")
            elif local_body == up_body:
                rep.add(WARN, rel, "both moved, still identical — re-freeze to record it")
            else:
                rep.add(FAIL, rel, "FORKED — the snapshot and upstream disagree")
        if verdicts["sync"]:
            rep.add(OK, "in sync with upstream", f"{verdicts['sync']} file(s)")

    # --- 4. the claims snapshot ------------------------------------------------------------
    claims = sources / CLAIMS
    if claims.exists():
        try:
            doc = tomllib.loads(claims.read_text(encoding="utf-8"))
            n = len(doc.get("claim", []))
            cmeta = doc.get("meta", {})
            detail = f"{n} claim(s) frozen from {cmeta.get('source', '?')}"
            if root is not None:
                live = root / cmeta.get("source", "index.qmd")
                if live.exists():
                    same = _paths.sha256(live) == cmeta.get("source_sha256")
                    detail += "; live manuscript unchanged" if same else \
                              "; LIVE MANUSCRIPT HAS CHANGED — run _source_checks.py --root"
            rep.add(OK, f"sources/{CLAIMS}", detail)
        except tomllib.TOMLDecodeError as exc:
            rep.add(FAIL, f"sources/{CLAIMS}", f"does not parse: {exc}")
    else:
        rep.add(SKIP, f"sources/{CLAIMS}", "absent; Tier S will fail if any entry is `frozen`")

    rep.render()
    n_fail, n_warn = rep.count(FAIL), rep.count(WARN)
    verdict = "FAIL" if n_fail else "PASS"
    tail = "" if root else "  (no --root given — upstream comparison skipped)"
    print(f"\nSYNC SUMMARY: {n_fail} problem(s), {n_warn} note(s).  RESULT: {verdict}{tail}")
    if n_fail:
        print("   UPSTREAM ADVANCED  -> the paper moved. Take the change deliberately:")
        print("                         copy, --freeze, then rebuild every figure.")
        print("   SNAPSHOT EDITED    -> revert it. sources/ is read-only; fix upstream.")
    return 1 if n_fail else 0


# ---- main ---------------------------------------------------------------------------------
def main() -> int:
    args = sys.argv[1:]
    root_arg = None
    if "--root" in args:
        i = args.index("--root")
        try:
            root_arg = args[i + 1]
        except IndexError:
            print("--root needs a path")
            return 2
        del args[i:i + 2]
    do_freeze = "--freeze" in args
    do_claims = "--freeze-claims" in args
    args = [a for a in args if a not in ("--freeze", "--freeze-claims", "--verbose")]

    if len(args) != 1:
        print(__doc__.split("USAGE")[1].strip().splitlines()[0])
        print("usage: _sync_check.py <deck-dir> [--root REPO_ROOT] [--freeze] [--freeze-claims]")
        return 2
    deck = pathlib.Path(args[0]).expanduser().resolve()
    if not deck.is_dir():
        print(f"[✗] {deck} is not a directory")
        return 2

    root = None
    if root_arg is not None:
        _paths.set_source_root(root_arg)
        try:
            root = _paths.source_root()
        except _paths.Unavailable as exc:
            print(f"[✗] {exc}")
            return 3

    if (do_freeze or do_claims) and root is None:
        print("[✗] --freeze and --freeze-claims both require --root: the provenance record is")
        print("    built FROM the manuscript checkout.")
        return 2

    if do_claims:
        rc = freeze_claims(deck, root)
        if rc or not do_freeze:
            return rc
    if do_freeze:
        return freeze(deck, root)
    return check(deck, root)


if __name__ == "__main__":
    raise SystemExit(main())
