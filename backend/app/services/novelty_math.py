"""Pure, deterministic helpers for graph novelty scoring.

Keeping the mathematics independent from Neo4j makes the scoring rules easy to
test and ensures the same inputs always produce the same result.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping


def clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def combine_signals(signals: Iterable[float]) -> float:
    """Return the unweighted v2 composite on a 0..100 scale."""
    values = [clamp(value) for value in signals]
    if not values:
        return 0.0
    return round(sum(values) / len(values) * 100.0, 1)


def jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def graph_distance(
    candidate_entities: set[str],
    historical_projects: Iterable[Mapping[str, object]],
    top_k: int = 5,
) -> tuple[float, list[dict]]:
    """Use nearest-neighbour Jaccard distance so near duplicates stay visible."""
    if not candidate_entities:
        return 0.5, []
    ranked: list[dict] = []
    for project in historical_projects:
        entity_names = {
            str(name).strip().casefold()
            for name in project.get("entity_names", [])
            if str(name).strip()
        }
        similarity = jaccard(candidate_entities, entity_names)
        ranked.append({
            "project_id": str(project.get("project_id", "")),
            "title": str(project.get("title") or project.get("project_id") or "Untitled project"),
            "similarity_score": round(similarity, 4),
        })

    ranked.sort(key=lambda item: item["similarity_score"], reverse=True)
    nearest_similarity = ranked[0]["similarity_score"] if ranked else 0.5
    return clamp(1.0 - nearest_similarity), ranked[:top_k]


def feature_rarity(feature_counts: Iterable[int], corpus_size: int) -> float:
    counts = [max(0, int(count)) for count in feature_counts]
    if corpus_size <= 0 or not counts:
        return 0.5
    return clamp(sum((corpus_size - min(count, corpus_size)) / corpus_size for count in counts) / len(counts))


def relationship_rarity(pair_counts: Iterable[int]) -> float:
    counts = [max(0, int(count)) for count in pair_counts]
    if not counts:
        return 0.5
    return clamp(sum(1.0 / (1.0 + count) for count in counts) / len(counts))


def neighborhood_sparsity(sibling_count: int, corpus_size: int) -> float:
    if corpus_size <= 0:
        return 0.5
    return clamp(1.0 - (max(0, sibling_count) / corpus_size))


def new_connection_score(
    pairs: Iterable[tuple[str, str]],
    pair_counts: Mapping[tuple[str, str], int],
    known_features: set[str],
) -> float:
    """Share of unseen pairings between features already known to the corpus."""
    eligible = []
    for left, right in pairs:
        if left in known_features and right in known_features:
            key = tuple(sorted((left, right)))
            eligible.append(max(0, int(pair_counts.get(key, 0))))
    if not eligible:
        return 0.5
    return clamp(sum(1 for count in eligible if count == 0) / len(eligible))
