import unittest

from app.services.assessment_engine import (
    AssessmentEngine,
    grade_for,
    overall_score,
    section_presence,
    weighted_mean,
)
from app.services.writing_analyzer import writing_quality_service


FULL_PROPOSAL = """
Abstract
This project implements a reproducible image classification pipeline.

Problem Statement and Objectives
The objective is to detect crop disease from field images.

Related Work
Prior convolutional models provide the baseline.

Methodology
The method uses transfer learning, preprocessing, training and inference.

System Architecture
The architecture contains a frontend, API, database and model pipeline.

Dataset and Requirements
The PlantVillage dataset is public. A GPU workstation is available.

Implementation
Python, PyTorch and FastAPI are used in three implementation modules.

Evaluation and Results
Experiments compare accuracy, precision, recall and F1 against a baseline.

Conclusion and Future Work
The conclusion reports limitations and future work.

References
[1] A. Author, "Crop disease classification", 2023.
"""


class AssessmentMathTests(unittest.TestCase):
    def test_weighted_mean_ignores_unavailable_dimensions(self):
        self.assertEqual(weighted_mean(((80, 1), (None, 4), (60, 1))), 70.0)

    def test_similarity_is_a_penalty_in_overall_score(self):
        base = {
            "novelty": 70,
            "feasibility": 70,
            "completeness": 70,
            "technical_depth": 70,
            "clarity": 70,
            "publication_potential": 70,
        }
        low_risk = overall_score({**base, "similarity_risk": 10})
        high_risk = overall_score({**base, "similarity_risk": 90})
        self.assertGreater(low_risk, high_risk)

    def test_grade_scale_has_failing_band(self):
        self.assertEqual(grade_for(45), "C / Requires Improvement")
        self.assertEqual(grade_for(None), "N/A")

    def test_section_detection_requires_heading_like_lines(self):
        detected = section_presence(FULL_PROPOSAL)
        self.assertTrue(all(detected.values()))
        body_only = section_presence("We evaluated the implementation and reached a conclusion in this sentence.")
        self.assertFalse(body_only["Evaluation / results"])


class AssessmentEngineTests(unittest.TestCase):
    def setUp(self):
        self.entities = {
            "algorithms": ["Transfer Learning"],
            "technologies": ["Python"],
            "frameworks": ["PyTorch", "FastAPI"],
            "libraries": [],
            "datasets": ["PlantVillage"],
            "hardware": ["GPU"],
            "metrics": ["Accuracy", "F1"],
        }
        self.writing = writing_quality_service.analyze_text(FULL_PROPOSAL)

    def test_full_document_produces_all_assessment_dimensions(self):
        report = AssessmentEngine().evaluate(
            title="Crop disease detection",
            submission_type="document",
            abstract="A crop disease detector using transfer learning.",
            full_text=FULL_PROPOSAL,
            entities=self.entities,
            novelty_score=76.0,
            similar_projects=[{"similarity_score": 0.2, "title": "Prior work"}],
            writing_analysis=self.writing,
            citation_analysis={
                "status": "success",
                "summary": {"reference_count": 8, "percent_verified": 75, "percent_recent": 60},
            },
            github_url="https://github.com/example/project",
        )
        self.assertEqual(report["completeness"]["score"], 100.0)
        self.assertEqual(report["scores"]["similarity_risk"], 14.0)
        self.assertEqual(report["scores"]["similarity_internal"], 20.0)
        self.assertEqual(report["scores"]["similarity_external"], 0.0)
        self.assertIsNotNone(report["scores"]["overall"])
        self.assertGreater(report["scores"]["feasibility"], 60)

    def test_abstract_does_not_fabricate_completeness(self):
        report = AssessmentEngine().evaluate(
            title="Short proposal",
            submission_type="abstract",
            abstract="A short proposed prototype with a Python API and accuracy evaluation.",
            full_text="",
            entities={"technologies": ["Python"], "metrics": ["Accuracy"]},
            novelty_score=60.0,
            similar_projects=[],
            writing_analysis={"quality_score": None, "metrics": {}, "status": "no_data"},
            citation_analysis={"status": "not_applicable", "summary": {}},
        )
        self.assertIsNone(report["scores"]["completeness"])
        self.assertEqual(report["evidence_quality"], "abstract_only")

    def test_input_hash_changes_with_submission_text(self):
        engine = AssessmentEngine()
        one = engine.input_hash("T", "abstract", "one", "", {}, 50)
        two = engine.input_hash("T", "abstract", "two", "", {}, 50)
        self.assertNotEqual(one, two)


class WritingAnalyzerTests(unittest.TestCase):
    def test_writing_metrics_are_measured_not_defaults(self):
        result = writing_quality_service.analyze_text(FULL_PROPOSAL)
        self.assertEqual(result["status"], "success")
        self.assertGreater(result["metrics"]["word_count"], 30)
        self.assertIsNotNone(result["quality_score"])

    def test_short_text_returns_no_score(self):
        result = writing_quality_service.analyze_text("Too short.")
        self.assertEqual(result["status"], "no_data")
        self.assertIsNone(result["quality_score"])


if __name__ == "__main__":
    unittest.main()
