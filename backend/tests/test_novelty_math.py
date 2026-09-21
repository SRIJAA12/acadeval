import unittest

from app.services.novelty_math import (
    combine_signals,
    feature_rarity,
    graph_distance,
    new_connection_score,
    relationship_rarity,
)


class NoveltyMathTests(unittest.TestCase):
    def test_near_duplicate_is_not_hidden_by_distant_projects(self):
        candidate = {"bert", "pytorch", "imdb"}
        signal, matches = graph_distance(candidate, [
            {"project_id": "duplicate", "title": "Duplicate", "entity_names": ["BERT", "PyTorch", "IMDb"]},
            {"project_id": "distant", "title": "Distant", "entity_names": ["Arduino", "LoRa"]},
        ])
        self.assertEqual(signal, 0.0)
        self.assertEqual(matches[0]["project_id"], "duplicate")

    def test_empty_candidate_does_not_look_novel(self):
        signal, _matches = graph_distance(
            set(),
            [{"project_id": "history", "title": "History", "entity_names": ["algorithm:bert"]}],
        )
        self.assertEqual(signal, 0.5)

    def test_feature_rarity_uses_only_historical_counts(self):
        self.assertAlmostEqual(feature_rarity([0, 2], corpus_size=4), 0.75)

    def test_relationship_rarity_declines_with_repeated_pair(self):
        self.assertGreater(relationship_rarity([0]), relationship_rarity([5]))

    def test_new_connection_requires_individually_known_features(self):
        pairs = [("algorithm:bert", "dataset:new"), ("algorithm:bert", "framework:pytorch")]
        score = new_connection_score(
            pairs,
            {("algorithm:bert", "framework:pytorch"): 0},
            {"algorithm:bert", "framework:pytorch"},
        )
        self.assertEqual(score, 1.0)

    def test_combiner_is_unweighted_and_bounded(self):
        self.assertEqual(combine_signals([0.0, 0.5, 1.0, 2.0, -1.0]), 50.0)


if __name__ == "__main__":
    unittest.main()
