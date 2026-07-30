#!/usr/bin/env python3
"""Source-fidelity checks for a beautiful-deck talk (Tier S of references/visual-qa.md).

The `beautiful-deck` skill copies this file into each deck as `slides/<deck>/scripts/_source_checks.py`.

WHAT THIS IS FOR
A deck goes stale silently. The manuscript is revised, a table is regenerated, and the slides keep
asserting last month's number — which still looks perfectly plausible, renders cleanly, and passes
every other tier. The other checkers verify the deck against *itself*; this one verifies it against
the **source of truth**.

WHY IT WORKS THE WAY IT DOES (this design was forced by evidence, not chosen for elegance)
The obvious approach — "does this number appear anywhere in tables/ or index.qmd?" — was measured
against a deck that had genuinely gone stale, and it would have caught NONE of its wrong numbers:

    0.75 appeared in 6 tables and twice in index.qmd
    0.88 appeared in 3 tables
    52%  appeared in 27 tables
    0.58 appeared in 14 tables

With dozens of tables of three-decimal values, almost any two-decimal number matches something by
chance. Existence search is far too permissive to detect drift.

So this checker verifies **declared provenance** instead. Each number the deck asserts is declared
in `numbers.toml` against the exact cell it came from, and the check re-reads that cell. When a
table is regenerated, a rounding-compatible change still passes; a real change fails loudly with
both numbers.

WHAT IT DOES NOT PROVE — read this before trusting a green run
Pass 1 proves a declared number matches its declared source. It cannot prove the *right* source was
declared: point an entry at the wrong cell and it will happily verify the wrong number. It is a net,
not a proof. Pass 2 (undeclared numbers) is a review prompt, not a verdict — it will list legitimate
numbers, and that is the intended cost of catching the manifest falling behind the deck.

It also cannot see DOUBLE ROUNDING, and here it does worse than fail — it certifies the wrong
number. `matches()` re-rounds the source CELL, so when the cell is itself already rounded, the
result can differ from rounding the full-precision value once:

    published table stores 0.795   →  round(0.795, 2)  →  0.80   ← what this check will certify
    the figure computes  0.79479   →  formats to 2 dp  →  0.79   ← what the audience sees

So a caption can pass Tier S and still contradict the figure printed directly above it. When a
source table carries fewer decimals than the figure computes from, either quote the number at the
table's own precision or do not quote it at all. See render-and-fix.md § 19.

USAGE
    uv run python slides/<deck>/scripts/_source_checks.py slides/<deck> [--root REPO_ROOT]
    uv run python slides/<deck>/scripts/_source_checks.py slides/<deck> --init   # scaffold a manifest

`--root` overrides where relative `source` paths resolve from; by default the first ancestor
directory containing `tables/` is used.

EVERY NUMBER MUST BE ACCOUNTED FOR
The check is only worth running if it cannot be half-adopted. A manifest with one entry and thirty
undeclared numbers would otherwise pass exactly as cleanly as a complete one — the same hole, one
level up. So:

  * a missing manifest FAILS (run `--init` to generate one in a second);
  * an entry whose `source` is still "TODO" FAILS;
  * a number on a slide that no entry accounts for FAILS.

The escape hatch is explicit, not silent. Numbers that assert nothing about results go in
`[meta] ignore = [...]`, where a reader can see what was excluded and disagree.

Exit code: 0 = everything accounted for, 1 = drift / unaccounted numbers / malformed manifest,
2 = usage error.
"""
from __future__ import annotations

import csv
import hashlib
import re
import sys
import tomllib
from pathlib import Path

OK, WARN, FAIL = "ok", "warn", "fail"
GLYPH = {OK: "[✓]", WARN: "[~]", FAIL: "[✗]"}

MANIFEST_NAME = "numbers.toml"

# Numeric tokens that are never claims about results, so pass 2 does not ask about them.
IGNORE_PATTERNS = (
    r"^(19|20)\d{2}$",        # years
    r"^[0-9]$",               # bare single digits: list markers, "one of two", counts in prose
    r"^100$",                 # percentages of a whole, "100 m"
)


class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []

    def add(self, state: str, name: str, detail: str = "") -> None:
        self.rows.append((state, name, detail))

    def count(self, state: str) -> int:
        return sum(1 for s, _, _ in self.rows if s == state)

    def render(self) -> None:
        for state, name, detail in self.rows:
            print(f"{GLYPH[state]} {name}{('  (' + detail + ')') if detail else ''}")


# ---- reading the source -------------------------------------------------------
def read_cell(path: Path, row_key: str, col: str) -> str | None:
    """Value at (first column == row_key, header == col). None if not found."""
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or col not in reader.fieldnames:
            return None
        key_field = reader.fieldnames[0]
        for rec in reader:
            if (rec.get(key_field) or "").strip() == row_key:
                return (rec.get(col) or "").strip()
    return None


def matches(source_value: str, declared: float, places: int | None) -> tuple[bool, str]:
    """Does the source cell agree with the declared number, at the declared rounding?"""
    try:
        actual = float(str(source_value).replace("−", "-").replace("%", "").strip())
    except (TypeError, ValueError):
        return False, f"source cell is not numeric: {source_value!r}"
    if places is None:
        return abs(actual - declared) < 1e-9, f"source {actual}"
    shown = round(actual, places)
    return abs(shown - declared) < 10 ** (-places - 4), f"source {actual} → {shown:.{places}f}"


# ---- the frozen manuscript claims --------------------------------------------
CLAIMS_NAME = "claims.toml"


def load_claims(deck_dir: Path) -> tuple[dict, dict]:
    """(meta, {key: claim}) from the deck's frozen snapshot; ({}, {}) if there is none.

    Read from the DECK, never from `root`. That distinction is the whole point: a claim is
    *deck* data, not *source* data, so with `--root <a manuscript checkout>` the file still
    has to be found here. Resolving it against root would make all fifteen entries fail the
    moment you passed the flag that was supposed to verify them harder.
    """
    p = deck_dir / "sources" / CLAIMS_NAME
    if not p.exists():
        return {}, {}
    doc = tomllib.loads(p.read_text(encoding="utf-8"))
    return doc.get("meta", {}), {c["key"]: c for c in doc.get("claim", [])}


def check_frozen(rep: Report, e: dict, claim: str, declared: float,
                 claims: dict, claims_meta: dict, root_override: Path | None) -> None:
    """Verify one number against the frozen manuscript snapshot.

    Standalone this compares the slide against the frozen record, which is all a portable
    copy of the deck can do — and it is fail-closed, exactly like a missing manifest.

    Given `--root`, it additionally re-runs the original regex against the live manuscript and
    separates two outcomes that look identical in a diff but mean opposite things:

        the number changed          -> FAIL. The deck is stale.
        the value holds, prose moved -> WARN. Re-freeze; nothing is wrong with the deck.
    """
    key = e["frozen"]
    if not claims:
        rep.add(FAIL, claim, f"entry is `frozen` but sources/{CLAIMS_NAME} is missing")
        return
    c = claims.get(key)
    if c is None:
        rep.add(FAIL, claim, f"no [[claim]] with key = {key!r} in sources/{CLAIMS_NAME}")
        return
    if abs(float(c["value"]) - declared) > 1e-9:
        rep.add(FAIL, f"{claim}: deck says {e['value']}",
                f"frozen record says {c['value']} — DRIFT inside the deck")
        return

    source_name = claims_meta.get("source", "index.qmd")
    live = (root_override / source_name) if root_override else None
    if live is None or not live.exists():
        rep.add(OK, f"{claim} = {e['value']}",
                f"frozen from {source_name}@{str(claims_meta.get('source_commit', '?'))[:7]}"
                f" line {c.get('line')}; pass --root to re-verify against the live manuscript")
        return

    text = live.read_text(encoding="utf-8")
    pattern = e.get("pattern") or c.get("pattern")
    if not pattern:
        rep.add(WARN, f"{claim} = {e['value']}",
                "no pattern recorded, so --root cannot re-verify this one")
        return
    m = re.search(pattern, text)
    if not m:
        rep.add(FAIL, claim, f"pattern no longer matches {source_name}: {pattern} "
                             f"— the prose moved; re-freeze sources/{CLAIMS_NAME}")
        return
    found = m.group(1) if m.groups() else m.group(0)
    good, detail = matches(found, declared, e.get("round"))
    ln = text[:m.start()].count("\n") + 1
    line_sha = hashlib.sha256(text.splitlines()[ln - 1].strip().encode("utf-8")).hexdigest()
    if not good:
        rep.add(FAIL, f"{claim}: deck says {e['value']}", f"{detail} — DRIFT vs live manuscript")
    elif line_sha != c.get("line_sha256") or ln != c.get("line"):
        rep.add(WARN, f"{claim} = {e['value']}",
                f"{detail}; value holds but the sentence moved "
                f"(line {c.get('line')} → {ln}) — re-freeze sources/{CLAIMS_NAME}")
    else:
        rep.add(OK, f"{claim} = {e['value']}", f"{detail}; live manuscript unchanged")


# ---- pass 1: declared numbers must match their declared cell ------------------
def check_declared(rep: Report, entries: list[dict], root: Path,
                   claims: dict | None = None, claims_meta: dict | None = None,
                   root_override: Path | None = None) -> None:
    if not entries:
        rep.add(WARN, "no numbers declared", f"add entries to {MANIFEST_NAME}")
        return
    claims = claims or {}
    claims_meta = claims_meta or {}
    for i, e in enumerate(entries, 1):
        claim = e.get("claim") or f"entry {i}"

        # A frozen entry's `source` is NOT resolved against root, so this branch has to come
        # before the `src = root / e["source"]` line below.
        if "frozen" in e:
            try:
                declared = float(e["value"])
            except (KeyError, TypeError, ValueError):
                rep.add(FAIL, claim, "frozen entry needs a numeric `value`")
                continue
            check_frozen(rep, e, claim, declared, claims, claims_meta, root_override)
            continue

        try:
            declared = float(e["value"])
            src = root / e["source"]
        except (KeyError, TypeError, ValueError):
            rep.add(FAIL, f"{claim}", "manifest entry needs at least `value` and `source`")
            continue
        if str(e.get("source", "")).strip().upper() == "TODO":
            rep.add(FAIL, f"value {e['value']}", "source still TODO — scaffolded but not sourced")
            continue
        # The file must exist for EVERY entry, derived or not. This once read
        # `if not e.get("derived") and not src.exists()`, which skipped the check entirely for
        # derived entries — and that is backwards. A derived entry has no cell to verify, so the
        # generating script's path is the ONLY thing it asserts and a reader's only route to
        # re-deriving the number. Renaming that script left a manifest pointing at nothing while
        # the check reported success, which is precisely the silent staleness this tier exists to
        # prevent. Pinned by test_derived_source_must_exist.
        if not src.exists():
            rep.add(FAIL, f"{claim}", f"source not found: {e['source']}")
            continue
        places = e.get("round")

        if e.get("derived"):
            # Computed by a deck figure script from the source data, and NOT quoted in the
            # manuscript. Recording it here keeps the manifest complete and keeps the author
            # honest about which slide numbers the paper does not itself state. The generating
            # script is named so a reader can re-derive it — which only works if it resolves,
            # hence the existence check above.
            rep.add(WARN, f"{claim} = {e['value']}",
                    f"derived by {e['source']} — not quoted in the manuscript")
            continue

        if "pattern" in e:
            # Free-text source (e.g. index.qmd): a regex whose first group is the number.
            m = re.search(e["pattern"], src.read_text(encoding="utf-8"))
            if not m:
                rep.add(FAIL, f"{claim}", f"pattern not found in {e['source']}: {e['pattern']}")
                continue
            found = m.group(1) if m.groups() else m.group(0)
            good, detail = matches(found, declared, places)
        elif "row" in e and "col" in e:
            cell = read_cell(src, str(e["row"]), str(e["col"]))
            if cell is None:
                rep.add(FAIL, f"{claim}", f"no cell [{e['row']} × {e['col']}] in {e['source']}")
                continue
            good, detail = matches(cell, declared, places)
        else:
            rep.add(FAIL, f"{claim}", "entry needs either `row`+`col` or `pattern`")
            continue

        if good:
            rep.add(OK, f"{claim} = {e['value']}", detail)
        else:
            rep.add(FAIL, f"{claim}: deck says {e['value']}", f"{detail} — DRIFT")


# ---- pass 2: numbers the manifest does not account for ------------------------
ATTR_BLOCK = re.compile(r"\{[^{}]*\}")          # {background-color="#05101F" .center}, {width="38%"}
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
NOTES = re.compile(r"::: *\{\.notes\}.*?\n:::", re.DOTALL)
NUMBER = re.compile(r"(?<![\w.#-])(\d+(?:\.\d+)?)\s*%?")


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:]
    return text


def numbers_in(text: str) -> list[str]:
    text = ATTR_BLOCK.sub(" ", HTML_COMMENT.sub(" ", IMAGE.sub(" ", text)))
    out = []
    for m in NUMBER.finditer(text):
        tok = m.group(1)
        if any(re.match(p, tok) for p in IGNORE_PATTERNS):
            continue
        out.append(tok)
    return out


def check_undeclared(rep: Report, qmd: Path, declared: set[str], ignored: set[str]) -> None:
    """Fail on any number the deck states that nothing accounts for.

    This is what makes the tier fail-closed. Verifying a handful of declared numbers while thirty
    others go unexamined would reproduce, one level up, exactly the silent-staleness problem the
    tier exists to prevent.

    Slide surface and speaker notes are reported separately — both fail, because a wrong number in
    the notes gets *spoken*, but they are triaged differently.

    The escape hatch is `[meta] ignore = [...]`: explicit, visible, and arguable. A number that
    asserts nothing about results (a count of slides, a round figure in an aside) belongs there
    rather than in a fabricated provenance entry.
    """
    raw = strip_frontmatter(qmd.read_text(encoding="utf-8"))
    notes_text = "\n".join(m.group(0) for m in NOTES.finditer(raw))
    surface = NOTES.sub(" ", raw)
    # `SDG 1`..`SDG 17` are goal labels, not results.
    surface = re.sub(r"SDG\s*\d+", " ", surface)
    notes_text = re.sub(r"SDG\s*\d+", " ", notes_text)

    accounted = declared | ignored
    for label, text in (("on slides", surface), ("in speaker notes", notes_text)):
        found = sorted({n for n in numbers_in(text)} - accounted, key=lambda s: (len(s), s))
        if found:
            rep.add(FAIL, f"unaccounted numbers {label}",
                    f"{len(found)}: {', '.join(found)} — declare each, or add to [meta] ignore")
        else:
            rep.add(OK, f"every number {label} is accounted for")


# ---- --init: scaffold a manifest from the deck's own numbers -----------------
def write_scaffold(manifest: Path, qmd: Path) -> None:
    """Generate a manifest listing every number the deck states, with sources left as TODO.

    Adoption has to be cheap or it will not happen, and a check nobody adopts protects nothing.
    This does the transcription; the author supplies the provenance. TODO entries fail, so a
    half-filled scaffold cannot pass.
    """
    raw = strip_frontmatter(qmd.read_text(encoding="utf-8"))
    notes_text = "\n".join(m.group(0) for m in NOTES.finditer(raw))
    surface = re.sub(r"SDG\s*\d+", " ", NOTES.sub(" ", raw))
    notes_text = re.sub(r"SDG\s*\d+", " ", notes_text)

    seen: list[tuple[str, str]] = []
    for where, text in (("slide", surface), ("notes", notes_text)):
        for n in dict.fromkeys(numbers_in(text)):
            if n not in {v for v, _ in seen}:
                seen.append((n, where))

    lines = [
        "# Provenance manifest — every number this deck asserts, and where it came from.",
        "#",
        "# Generated by `_source_checks.py --init`. Each entry below states a number the deck",
        "# shows; you supply the source. Replace every TODO with either:",
        "#",
        "#   source = \"tables/<file>.csv\"   + row = \"...\"  col = \"...\"   (a cell)",
        "#   source = \"index.qmd\"           + pattern = '...'              (a regex, group 1)",
        "#   source = \"scripts/fig-x.py\"    + derived = true               (computed by the deck)",
        "#",
        "# A number that asserts nothing about results belongs in `ignore` below, not in an entry —",
        "# an explicit exclusion a reader can see and disagree with.",
        "",
        "[meta]",
        "ignore = []",
        "",
    ]
    for value, where in seen:
        lines += [
            "[[number]]",
            f"value  = {value}",
            f'claim  = "TODO — what this number says, and where it appears ({where})"',
            'source = "TODO"',
            f"round  = {len(value.split('.')[1]) if '.' in value else 0}",
            "",
        ]
    manifest.write_text("\n".join(lines), encoding="utf-8")
    print(f"[✓] wrote {manifest} with {len(seen)} number(s) to source.")
    print("    Replace every TODO, then re-run without --init. TODO entries fail by design.")


# ---- main --------------------------------------------------------------------
def find_root(deck_dir: Path) -> Path:
    """The tree that relative `source` paths resolve against.

    Prefer the deck's OWN vendored snapshot. A portable deck ships `sources/{tables,data,code}`
    precisely so this tier passes with no reference to the manuscript repository; the walk-up
    survives for a deck that sits inside a full checkout and vendors nothing.

    The old `deck_dir.resolve().parents[1]` fallback is deliberately gone. Once a deck's contents
    ARE a repository root there is no `./tables` to find, so the walk continued past the
    repository and the fallback landed on its grandparent — and if that unrelated directory
    happened to contain a `tables/`, this tier would have verified the slides against a
    stranger's CSVs and printed a green PASS. Failing outright is strictly better.
    """
    snap = deck_dir / "sources"
    if (snap / "tables").is_dir():
        return snap
    for p in [deck_dir, *deck_dir.resolve().parents]:
        if (p / "tables").is_dir():
            return p
    raise SystemExit(
        f"[✗] no tables/ directory found from {deck_dir} upward, and no sources/ snapshot.\n"
        "    This deck's numbers cannot be verified against anything. Either vendor a snapshot\n"
        "    (see sources/README.md) or pass --root /path/to/the/source/repo."
    )


def main() -> int:
    args = sys.argv[1:]
    root_override = None
    if "--root" in args:
        i = args.index("--root")
        try:
            root_override = Path(args[i + 1])
        except IndexError:
            print("--root needs a path")
            return 2
        del args[i:i + 2]
    do_init = "--init" in args
    if do_init:
        args.remove("--init")
    if not args:
        print("usage: _source_checks.py slides/<deck> [--root REPO_ROOT] [--init]")
        return 2
    deck_dir = Path(args[0])
    if not deck_dir.is_dir():
        print(f"[✗] not a directory: {deck_dir}")
        return 2

    qmds = sorted(deck_dir.glob("*.qmd"))
    qmd = deck_dir / f"{deck_dir.name}.qmd"
    if not qmd.exists():
        qmd = qmds[0] if qmds else qmd
    manifest = deck_dir / MANIFEST_NAME
    root = root_override or find_root(deck_dir)

    print(f"== beautiful-deck source-fidelity checks: {deck_dir} ==")
    print(f"   manifest: {MANIFEST_NAME}    source root: {root}\n")

    if do_init:
        if not qmd.exists():
            print(f"[✗] no .qmd found in {deck_dir} — nothing to scaffold from.")
            return 2
        if manifest.exists():
            print(f"[✗] {manifest} already exists — refusing to overwrite it.")
            return 2
        write_scaffold(manifest, qmd)
        return 0

    if not manifest.exists():
        # A missing manifest is a FAILURE, not a shrug. An unverified deck and a verified one must
        # not look alike at the end of a run — that is what made this check opt-in, and opt-in
        # checks protect nothing.
        print(f"[✗] {MANIFEST_NAME} not found — this deck's numbers are unverified.")
        print(f"    Generate one from the deck's own numbers, then fill in the sources:\n")
        print(f"    uv run python {Path(sys.argv[0]).as_posix()} {deck_dir} --init\n")
        print("SOURCE SUMMARY: manifest missing.  RESULT: FAIL")
        return 1

    try:
        doc = tomllib.loads(manifest.read_text(encoding="utf-8"))
        entries = doc.get("number", [])
        ignored = {str(v) for v in doc.get("meta", {}).get("ignore", [])}
    except tomllib.TOMLDecodeError as exc:
        print(f"[✗] {MANIFEST_NAME} is malformed: {exc}")
        return 1

    claims_meta, claims = load_claims(deck_dir)
    if any("frozen" in e for e in entries) and not claims:
        # Fail-closed, mirroring the missing-manifest logic above: an entry that declares a
        # frozen source with no snapshot to check it against is unverified, and unverified must
        # not look like verified at the end of a run.
        n = sum(1 for e in entries if "frozen" in e)
        print(f"[✗] {n} entr{'y' if n == 1 else 'ies'} declare `frozen`, but "
              f"sources/{CLAIMS_NAME} is missing — those numbers are unverified.")
        print("    Re-create it from a manuscript checkout:\n")
        print(f"    uv run python scripts/_sync_check.py {deck_dir} "
              "--root /path/to/project2026e --freeze-claims\n")
        print("SOURCE SUMMARY: frozen claims missing.  RESULT: FAIL")
        return 1

    rep = Report()
    check_declared(rep, entries, root, claims, claims_meta, root_override)
    declared = {str(e["value"]) for e in entries if "value" in e}
    # A declared 0.5 also accounts for a slide writing it as 0.50, and 50 for "50%".
    declared |= {f"{float(v):.2f}" for v in declared if _isnum(v)}
    declared |= {str(int(float(v) * 100)) for v in list(declared) if _isnum(v) and float(v) < 1}
    if qmd.exists():
        check_undeclared(rep, qmd, declared, ignored)

    rep.render()
    n_fail, n_warn = rep.count(FAIL), rep.count(WARN)
    verdict = "FAIL" if n_fail else "PASS"
    print(f"\nSOURCE SUMMARY: {n_fail} unresolved, {n_warn} noted.  RESULT: {verdict}")
    print("   note: a green run proves each declared number matches the cell it declares —")
    print("         not that the right cell was declared. Spot-check the manifest itself.")
    return 1 if n_fail else 0


def _isnum(v: str) -> bool:
    try:
        float(v)
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    raise SystemExit(main())
