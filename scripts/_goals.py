"""One naming and grouping convention for the fifteen goals, shared by every deck figure.

Why this exists. The source tables carry two different label systems — `tbl-popweighting-master`
uses short names with an unspaced tag (`"Poverty (SDG1)"`) while `tbl-mon-comprehensive` uses a
`Goal index` / `Goal` pair with full official names (`"SDG 1"` + `"No Poverty"`). Figures built
straight from each table therefore disagreed about what the same goal is called, five slides apart.

Two rules, applied here once:

1. **Short names.** Full official titles ("Industry, Innovation and Infrastructure") are unreadable
   as tick labels at projection size and eat the plotting area.
2. **`SDG 1`, never `SDG1`.** `code/labels.py:179` is explicit: *"'SDG 1'..'SDG 17' are proper
   labels, not acronyms, and must keep the space: never 'SDG1'."* The source tables violate this in
   their own row keys, so the deck normalises rather than inheriting it.

Group membership matches the manuscript's three-way taxonomy, read off `tables/tbl-g{1,2,3}-*.csv`.
Colouring by group is what lets the master figure pay off the taxonomy claim made a slide earlier.
"""
from __future__ import annotations

import re

#: SDG number -> short display name.
SHORT = {
    1: "Poverty", 2: "Hunger", 3: "Health", 4: "Education", 5: "Gender",
    6: "Water", 7: "Energy", 8: "Jobs", 9: "Infrastructure", 10: "Inequality",
    11: "Cities", 13: "Climate", 15: "Land", 16: "Institutions", 17: "Partnerships",
}

#: SDG number -> taxonomy group (keys match `_palette.GROUP_COLORS`).
GROUP = {
    **{n: "Material & Built" for n in (1, 6, 7, 9, 11)},
    **{n: "Land & Environmental" for n in (2, 13, 15)},
    **{n: "Social & Institutional" for n in (3, 4, 5, 8, 10, 16, 17)},
}


def number(label: str) -> int:
    """Pull the SDG number out of any of the label forms the tables use."""
    m = re.search(r"SDG\s*(\d+)", str(label))
    if not m:
        raise ValueError(f"no SDG number in {label!r}")
    return int(m.group(1))


def tick(label: str) -> str:
    """Canonical tick label: `Poverty (SDG 1)` — short name, spaced tag."""
    n = number(label)
    return f"{SHORT[n]} (SDG {n})"


def group(label: str) -> str:
    return GROUP[number(label)]
