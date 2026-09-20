"""
Backfills AcadEval_Corpus (datasets/corpus/new_AcadEval_Corpus.csv, ~2,611 rows)
into Neo4j through the same Module 2 (extraction) + Module 3 (graph ingestion)
path used for live submissions, so the Graph-Based Novelty Engine (Module 4)
has a real historical baseline instead of only whatever's been submitted
in-process since the last restart.

The corpus already carries a curated Domain/Sub_Domain per row, so this script
skips Module 1 (classification) and uses those columns directly — re-running
the embedding classifier over 2,611 rows would be slow and would only
re-derive what the corpus already states.

Run after `docker compose up -d neo4j` and after `ensure_constraints()` has
run at least once (i.e. after the API has started once):

    python scripts/backfill_corpus_graph.py [--limit N]
"""
import argparse
import csv
import hashlib
import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.extractor import extractor_service
from app.services.graph_db import graph_service, GraphUnavailableError

CORPUS_CSV = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "datasets", "AcadEval_Corpus_MASTER.csv")
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Only ingest the first N rows (for a quick smoke test)")
    args = parser.parse_args()

    graph_service.ensure_constraints()

    with open(CORPUS_CSV, "rb") as corpus_file:
        corpus_version = hashlib.sha256(corpus_file.read()).hexdigest()

    with open(CORPUS_CSV, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if args.limit:
        rows = rows[: args.limit]

    total = len(rows)
    active_project_ids = [f"CORPUS-{row['Project_ID'].strip()}" for row in rows]
    ok, failed = 0, 0
    start = time.time()

    for i, row in enumerate(rows, start=1):
        project_id = f"CORPUS-{row['Project_ID'].strip()}"
        title = row["Title"].strip()
        abstract = row.get("Abstract", "").strip()
        domain = row.get("Domain", "").strip() or "Uncategorized"
        sub_domain = row.get("Sub_Domain", "").strip() or "General"

        full_text = f"{title}\n{abstract}"
        try:
            entities = extractor_service.extract_entities(full_text)
            graph_service.build_project_graph(
                project_id=project_id,
                title=title,
                domain=domain,
                sub_domain=sub_domain,
                extracted_entities=entities,
                source_type="corpus",
                source_version=corpus_version,
            )
            ok += 1
        except GraphUnavailableError as e:
            print(f"\nNeo4j unavailable — aborting at row {i}/{total}: {e}")
            sys.exit(1)
        except Exception as e:
            failed += 1
            print(f"  [{i}/{total}] FAILED {project_id} ({title[:40]!r}): {e}")
            continue

        if i % 100 == 0 or i == total:
            elapsed = time.time() - start
            print(f"  [{i}/{total}] ingested (ok={ok}, failed={failed}, {elapsed:.1f}s elapsed)")

    pruned = graph_service.prune_corpus_projects(active_project_ids) if args.limit is None else 0

    print(
        f"\nDone: {ok} ingested, {failed} failed, out of {total} corpus rows. "
        f"Pruned: {pruned}. Corpus version: {corpus_version}"
    )


if __name__ == "__main__":
    main()
