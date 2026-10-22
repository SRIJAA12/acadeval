"""
Backfills the reference corpus into Neo4j so the novelty engine has a real
historical baseline.

Corpus file: CORPUS_CSV_PATH, or by default
datasets/new_dataset/new_AcadEval_Corpus.csv.xls (a CSV despite the extension,
~31k rows). Template/filler rows (Publication_Type "Conceptual academic
project") are skipped and any projects from an older corpus that are no longer
in the kept set are pruned from Neo4j.

Entities come from the CSV's structured columns (Algorithms, Technologies,
Frameworks, Tools, Hardware, Dataset_Used, Keywords). Without --structured-only
the title+abstract text is also run through the entity extractor, which is much
slower (about 100 rows per 6-40 s) and is only worth it for small corpora.

Run after `docker compose up -d neo4j`:

    python scripts/backfill_corpus_graph.py --structured-only --no-co-occurs [--limit N]
"""
import argparse
import csv
import hashlib
import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.corpus_matcher import _resolve_corpus_paths
from app.services.corpus_quality import boilerplate_cells, is_template_row
from app.services.extractor import extractor_service
from app.services.graph_db import graph_service, GraphUnavailableError

# Structured corpus columns -> graph entity categories. Cell texts that repeat
# across many unrelated domains are template filler and are skipped (see
# corpus_quality.boilerplate_cells); template rows are skipped entirely.
STRUCTURED_COLUMNS = {
    "Algorithms": ("algorithms", ","),
    "Technologies": ("technologies", ","),
    "Programming_Languages": ("technologies", ","),
    "Frameworks": ("frameworks", ","),
    "Tools": ("libraries", ","),
    "Dataset_Used": ("datasets", None),
    "Hardware": ("hardware", ";"),
    "Keywords": ("applications", ","),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Only ingest the first N kept rows (smoke test; skips pruning)")
    parser.add_argument(
        "--structured-only", action="store_true",
        help="Build entities from the CSV columns only; skip the slow per-row text extraction.",
    )
    parser.add_argument(
        "--no-co-occurs", action="store_true",
        help="Skip the analytics-only CO_OCCURS edges (not used by scoring or the graph view); much faster for large corpora.",
    )
    args = parser.parse_args()

    paths = _resolve_corpus_paths()
    if not paths:
        sys.exit("No corpus CSV found. Set CORPUS_CSV_PATH or place the file under datasets/.")
    corpus_csv = paths[0]
    print(f"Corpus file: {corpus_csv}")

    graph_service.ensure_constraints()

    with open(corpus_csv, "rb") as corpus_file:
        corpus_version = hashlib.sha256(corpus_file.read()).hexdigest()

    with open(corpus_csv, encoding="utf-8-sig", newline="") as f:
        all_rows = list(csv.DictReader(f))

    boiler = boilerplate_cells(all_rows)
    rows = [r for r in all_rows if not is_template_row(r)]
    print(f"{len(all_rows)} rows read, {len(all_rows) - len(rows)} template rows skipped, {len(rows)} kept")

    if args.limit:
        rows = rows[: args.limit]

    total = len(rows)
    active_project_ids = [f"CORPUS-{row['Project_ID'].strip()}" for row in rows]
    ok, failed = 0, 0
    start = time.time()

    def structured_entities(row: dict) -> dict:
        found: dict[str, list[str]] = {}
        for col, (category, sep) in STRUCTURED_COLUMNS.items():
            cell = (row.get(col) or "").strip()
            if not cell or cell in boiler.get(col, ()):
                continue
            parts = [cell] if sep is None else [p.strip() for p in cell.split(sep)]
            found.setdefault(category, []).extend(p for p in parts if p)
        return found

    for i, row in enumerate(rows, start=1):
        project_id = f"CORPUS-{row['Project_ID'].strip()}"
        title = row["Title"].strip()
        abstract = (row.get("Abstract") or "").strip()
        domain = (row.get("Domain") or "").strip() or "Uncategorized"
        sub_domain = (row.get("Sub_Domain") or "").strip() or "General"

        try:
            if args.structured_only:
                entities = {}
            else:
                entities = extractor_service.extract_entities(f"{title}\n{abstract}")
            for category, names in structured_entities(row).items():
                merged = list(entities.get(category, []))
                seen = {n.casefold() for n in merged}
                merged.extend(n for n in names if n.casefold() not in seen)
                entities[category] = merged
            graph_service.build_project_graph(
                project_id=project_id,
                title=title,
                domain=domain,
                sub_domain=sub_domain,
                extracted_entities=entities,
                source_type="corpus",
                source_version=corpus_version,
                co_occurrence=not args.no_co_occurs,
            )
            ok += 1
        except GraphUnavailableError as e:
            print(f"\nNeo4j unavailable — aborting at row {i}/{total}: {e}", flush=True)
            sys.exit(1)
        except Exception as e:
            failed += 1
            print(f"  [{i}/{total}] FAILED {project_id} ({title[:40]!r}): {e}", flush=True)
            continue

        if i % 500 == 0 or i == total:
            elapsed = time.time() - start
            print(f"  [{i}/{total}] ingested (ok={ok}, failed={failed}, {elapsed:.1f}s elapsed)", flush=True)

    pruned = graph_service.prune_corpus_projects(active_project_ids) if args.limit is None else 0

    print(
        f"\nDone: {ok} ingested, {failed} failed, out of {total} kept corpus rows. "
        f"Pruned: {pruned}. Corpus version: {corpus_version}",
        flush=True,
    )


if __name__ == "__main__":
    main()
