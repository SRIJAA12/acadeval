import unittest

from app.services.novelty_math import (
    combine_signals,
    feature_rarity,
    graph_distance,
    neighborhood_sparsity,
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

    def test_feature_rarity_saturates_on_own_count_not_corpus_size(self):
        # 1/(1+0)=1.0, 1/(1+2)=1/3 -> mean 2/3. Must NOT scale with corpus_size
        # (a feature seen in 2 of 4 projects is exactly as rare as 2 of 40,000).
        self.assertAlmostEqual(feature_rarity([0, 2], corpus_size=4), 2 / 3)
        self.assertAlmostEqual(feature_rarity([0, 2], corpus_size=40000), 2 / 3)

    def test_feature_rarity_discriminates_common_from_unique(self):
        self.assertGreater(feature_rarity([0], corpus_size=1000), feature_rarity([900], corpus_size=1000))

    def test_neighborhood_sparsity_saturates_on_sibling_count_not_corpus_size(self):
        # An oversubscribed niche (142 siblings) must read as near-saturated
        # regardless of how large the overall multi-domain corpus is.
        self.assertAlmostEqual(neighborhood_sparsity(142, corpus_size=4000), 1 / 143)
        self.assertAlmostEqual(neighborhood_sparsity(142, corpus_size=36000), 1 / 143)

    def test_neighborhood_sparsity_rewards_a_genuinely_empty_niche(self):
        self.assertGreater(neighborhood_sparsity(0, corpus_size=10000), neighborhood_sparsity(500, corpus_size=10000))

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
