"""Quality filters for the reference corpus used by novelty matching.

The corpus CSVs mix topic-specific projects with template filler. Filler rows
share identical Algorithms / Technologies / Frameworks cells, so letting them
into the comparison makes unrelated projects look alike ("83% match" on React
+ Random Forest). Two cheap, explainable filters are used:

* is_template_row: drops rows explicitly flagged as conceptual placeholders.
* boilerplate_cells: finds cell texts that repeat AND span many unrelated
  domains. Repetition alone is not enough: a legitimate topic cluster such as
  "Fast-SLAM, A* Search, Extended Kalman Filter" repeats hundreds of times but
  only inside robotics. Filler repeats across the whole domain list. Such
  cells are stripped from a row's entity list (the row itself is kept).
"""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Mapping

TEMPLATE_PUBLICATION_TYPES = {"conceptual academic project"}
TEMPLATE_NOTE_MARKERS = ("intentionally blank",)

ENTITY_COLUMNS = (
    "Algorithms",
    "Technologies",
    "Frameworks",
    "Tools",
    "Hardware",
    "Dataset_Used",
    "Programming_Languages",
    "Keywords",
)


def is_template_row(row: Mapping[str, object]) -> bool:
    publication_type = str(row.get("Publication_Type") or "").strip().lower()
    if publication_type in TEMPLATE_PUBLICATION_TYPES:
        return True
    notes = str(row.get("Notes") or "").lower()
    return any(marker in notes for marker in TEMPLATE_NOTE_MARKERS)


def boilerplate_cells(
    rows: Iterable[Mapping[str, object]],
    columns: Iterable[str] = ENTITY_COLUMNS,
    min_repeats: int = 20,
    min_domains: int = 8,
    domain_column: str = "Domain",
) -> dict[str, set[str]]:
    """Per column, cell texts seen in >= min_repeats rows across >= min_domains domains."""
    columns = tuple(columns)
    counts: dict[str, dict[str, int]] = {col: defaultdict(int) for col in columns}
    domains: dict[str, dict[str, set[str]]] = {col: defaultdict(set) for col in columns}
    for row in rows:
        domain = str(row.get(domain_column) or "").strip().lower()
        for col in columns:
            cell = str(row.get(col) or "").strip()
            if cell:
                counts[col][cell] += 1
                domains[col][cell].add(domain)
    return {
        col: {
            cell
            for cell, count in counts[col].items()
            if count >= min_repeats and len(domains[col][cell]) >= min_domains
        }
        for col in columns
    }
