"""One-off Phase-0 verification script (not part of the app): checks that
LegacySnapshot reproduces NoveltyEngineService.compute_novelty_signals exactly
on a sample of real corpus projects already in Neo4j. Run inside the api
container: `python scripts/legacy_parity_check.py [N]`.
"""
import sys

sys.path.insert(0, "/app")

from app.services.graph_db import graph_service, ENTITY_LABELS  # noqa: E402
from app.services.novelty_engine import NoveltyEngineService, CATEGORY_EDGE_MAP, ENTITY_RELATIONSHIPS  # noqa: E402
from app.eval.legacy_scorer import LegacySnapshot  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 20

label_to_category = {label: cat for cat, (label, _rel) in CATEGORY_EDGE_MAP.items()}

print("Exporting LegacySnapshot (one-time, shared across all samples)...")
snapshot = LegacySnapshot.export()
print(f"Snapshot ready: {snapshot.corpus_size} projects")

with graph_service.session() as session:
    sample = session.run(
        """
        MATCH (p:Project)
        WHERE EXISTS { MATCH (p)-[r]->() WHERE type(r) IN $rels }
        RETURN p.id AS project_id, coalesce(p.domain,'') AS domain, coalesce(p.sub_domain,'') AS sub_domain
        ORDER BY rand() LIMIT $n
        """,
        rels=ENTITY_RELATIONSHIPS, n=N,
    ).data()

engine = NoveltyEngineService()
max_delta = 0.0
mismatches = []

for row in sample:
    pid, domain, sub_domain = row["project_id"], row["domain"], row["sub_domain"]
    with graph_service.session() as session:
        ent_rows = session.run(
            """
            MATCH (p:Project {id: $pid})-[r]->(e)
            WHERE type(r) IN $rels
            RETURN DISTINCT labels(e) AS labels, e.name AS name
            """,
            pid=pid, rels=ENTITY_RELATIONSHIPS,
        ).data()

    raw_entities: dict[str, list[str]] = {cat: [] for cat in CATEGORY_EDGE_MAP}
    for er in ent_rows:
        label = next((l for l in er["labels"] if l in ENTITY_LABELS), None)
        cat = label_to_category.get(label)
        if cat and er["name"]:
            raw_entities[cat].append(er["name"])

    live = engine.compute_novelty_signals(pid, raw_entities, domain, sub_domain)
    legacy = snapshot.score(raw_entities, domain, sub_domain, exclude_project_id=pid)

    deltas = {
        "composite": abs(live["composite_novelty_score"] - legacy["composite_novelty_score"]),
        "s1": abs(live["signal_1_graph_distance"] - legacy["signal_1_graph_distance"]),
        "s2": abs(live["signal_2_feature_rarity"] - legacy["signal_2_feature_rarity"]),
        "s3": abs(live["signal_3_relationship_rarity"] - legacy["signal_3_relationship_rarity"]),
        "s4": abs(live["signal_4_graph_density"] - legacy["signal_4_graph_density"]),
        "s5": abs(live["signal_5_new_connection_discovery"] - legacy["signal_5_new_connection_discovery"]),
    }
    worst = max(deltas.values())
    max_delta = max(max_delta, worst)
    status = "OK" if worst < 1e-6 else "MISMATCH"
    if worst >= 1e-6:
        mismatches.append((pid, deltas, live, legacy))
    print(f"{pid}: {status} worst_delta={worst:.8f} live_composite={live['composite_novelty_score']:.4f} legacy_composite={legacy['composite_novelty_score']:.4f}")

print()
print(f"Checked {len(sample)} projects. Max delta observed: {max_delta:.8f}")
if mismatches:
    print(f"{len(mismatches)} MISMATCHES:")
    for pid, deltas, live, legacy in mismatches:
        print(f"  {pid}: {deltas}")
        print(f"    live similar_projects[0]: {live['similar_projects'][0] if live['similar_projects'] else None}")
        print(f"    legacy similar_projects[0]: {legacy['similar_projects'][0] if legacy['similar_projects'] else None}")
else:
    print("All within 1e-6 tolerance.")
