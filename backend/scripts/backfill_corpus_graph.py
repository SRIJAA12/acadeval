"""
Backfills AcadEval_Corpus_MASTER.csv (datasets/AcadEval_Corpus_MASTER.csv,
~3,150 rows) through the same Module 2 (extraction) + Module 4 (graph
ingestion) path used for live submissions, so both the in-memory corpus
index (Module: novelty-engine-fix, corpus_index.py -- the DEFAULT scoring
engine) and the Neo4j visualization graph have a real historical baseline.

Modes:
  (default)     backfills BOTH Postgres graph_nodes/graph_edges AND Neo4j.
  --local-only  backfills ONLY Postgres graph_nodes/graph_edges, skips Neo4j
                entirely (no connection attempted), and warms the in-memory
                corpus index singleton at the end -- for instant local
                testing without waiting on Neo4j/Docker.

Note: corpus_index.py reads datasets/AcadEval_Corpus_MASTER.csv directly and
builds its own in-memory index independent of this script (see
app/services/corpus_index.py) -- this script's corpus_index step just
confirms that index loads and reports its row count; it does not need to be
run before the API can score against the corpus engine.

Run after `docker compose up -d neo4j` for the default mode, or standalone
for --local-only:

    python scripts/backfill_corpus_graph.py [--limit N] [--local-only]
"""
import argparse
import hashlib
import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.services.extractor import extractor_service
from app.services.graph_builder import ingest_project_to_relational_graph
from app.services.graph_db import graph_service, GraphUnavailableError

CORPUS_CSV = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "datasets", "AcadEval_Corpus_MASTER.csv")
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Only ingest the first N rows (for a quick smoke test)")
    parser.add_argument(
        "--local-only", action="store_true",
        help="Backfill Postgres graph_nodes/graph_edges only; skip Neo4j entirely "
             "and warm the in-memory corpus index singleton at the end.",
    )
    args = parser.parse_args()

    if not args.local_only:
        graph_service.ensure_constraints()

    import pandas as pd
    df = pd.read_csv(CORPUS_CSV)
    if args.limit:
        df = df.head(args.limit)
    rows = df.to_dict("records")

    with open(CORPUS_CSV, "rb") as corpus_file:
        corpus_version = hashlib.sha256(corpus_file.read()).hexdigest()

    total = len(rows)
    db = SessionLocal()
    postgres_ok, neo4j_synced, neo4j_pending, failed = 0, 0, 0, 0
    start = time.time()

    try:
        for i, row in enumerate(rows, start=1):
            project_id = f"CORPUS-{str(row['Project_ID']).strip()}"
            title = str(row.get("Title", "") or "").strip()
            abstract = str(row.get("Abstract", "") or "").strip()
            domain = str(row.get("Domain", "") or "").strip() or "Uncategorized"
            sub_domain = str(row.get("Sub_Domain", "") or "").strip() or "General"

            full_text = f"{title}\n{abstract}"
            try:
                entities = extractor_service.extract_entities(full_text)
                result = ingest_project_to_relational_graph(
                    db=db,
                    project_id=project_id,
                    title=title,
                    domain=domain,
                    sub_domain=sub_domain,
                    extracted_entities=entities,
                    skip_neo4j=args.local_only,
                )
                postgres_ok += 1
                if result["neo4j_sync"] == "synced":
                    neo4j_synced += 1
                elif result["neo4j_sync"] == "pending":
                    neo4j_pending += 1
            except GraphUnavailableError as e:
                # Only reachable when --local-only is NOT set and Neo4j drops
                # mid-run in a way graph_builder didn't already convert into
                # a "pending" row (e.g. ensure_constraints failing later).
                print(f"\nNeo4j unavailable — aborting at row {i}/{total}: {e}")
                sys.exit(1)
            except Exception as e:
                failed += 1
                print(f"  [{i}/{total}] FAILED {project_id} ({title[:40]!r}): {e}")
                continue

            if i % 100 == 0 or i == total:
                elapsed = time.time() - start
                print(
                    f"  [{i}/{total}] postgres_ok={postgres_ok} neo4j_synced={neo4j_synced} "
                    f"neo4j_pending={neo4j_pending} failed={failed} ({elapsed:.1f}s elapsed)"
                )
    finally:
        db.close()

    print(
        f"\nDone: {postgres_ok}/{total} written to Postgres graph_nodes/graph_edges. "
        + (
            "Neo4j skipped (--local-only)."
            if args.local_only
            else f"{neo4j_synced} synced to Neo4j, {neo4j_pending} pending (will retry via the "
                 f"scheduled.retry_pending_neo4j_sync beat task)."
        )
        + f" {failed} failed. Corpus version: {corpus_version}"
    )

    # Warm (and report on) the in-memory corpus index singleton -- this is
    # the DEFAULT scoring engine and reads the CSV independently of
    # everything above, so this is a confirmation step, not a dependency.
    from app.services.corpus_index import get_corpus_index
    index = get_corpus_index()
    print(f"In-memory corpus index: {index.n_projects} projects loaded from {index.csv_path}")


if __name__ == "__main__":
    main()
