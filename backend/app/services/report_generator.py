"""
Module 6 — Explainable Novelty Report Generator
=================================================
Combines Module 1-5 outputs into the structured JSON Explainable Novelty Report
schema defined in Section 7.6 of the AcadEval+ specification.
"""

import logging

from app.services.classifier import classifier_service
from app.services.explainability import explainability_service
from app.services.extractor import extractor_service
from app.services.graph_db import graph_service
from app.services.novelty_engine import novelty_engine_service
from app.services.trend_scorer import trend_scorer_service

log = logging.getLogger(__name__)


class NoveltyReportGeneratorService:
    def generate_full_report(self, project_id: str, title: str, abstract: str) -> dict:
        """
        Generates the complete Explainable Novelty Report JSON for a project proposal.
        """
        # Step 1: Module 1 — Domain Classification
        classification = classifier_service.classify_project(title, abstract)
        domain = classification["domain"]
        sub_domain = classification["sub_domain"]

        # Step 2: Module 2 — Entity Extraction (use DB persisted entities if available)
        entities = {}
        try:
            from app.database import SessionLocal
            from app.models.project import Project
            db = SessionLocal()
            proj = db.query(Project).filter(Project.id == project_id).first()
            if proj and proj.extracted_entities and any(proj.extracted_entities.values()):
                entities = proj.extracted_entities
            db.close()
        except Exception:
            pass

        if not entities or not any(entities.values()):
            full_text = f"{title}\n{abstract}"
            entities = extractor_service.extract_entities(full_text)

        # Step 3: Module 3 — Graph Ingestion
        graph_stats = graph_service.build_project_graph(
            project_id=project_id,
            title=title,
            domain=domain,
            sub_domain=sub_domain,
            extracted_entities=entities
        )

        # Step 4: Module 4 — Novelty Engine
        novelty_data = novelty_engine_service.compute_novelty_signals(
            project_id=project_id,
            extracted_entities=entities,
            domain=domain,
            sub_domain=sub_domain
        )

        # Step 4b: Module 9 — Explainability Layer
        explainability = explainability_service.generate_explanations(novelty_data)

        # Step 5: Module 5 — Trend Scoring
        topic = classification.get("topic", domain)
        trend_data = trend_scorer_service.get_topic_trend(topic)

        # Step 6: Assemble Module 6 Report Schema
        report_json = {
            "project_id": project_id,
            "title": title,
            "domain": domain,
            "sub_domain": sub_domain,
            "overall_novelty_band": novelty_data["novelty_band"],
            "overall_novelty_score": novelty_data["composite_novelty_score"],
            "signals_breakdown": {
                "graph_distance": novelty_data["signal_1_graph_distance"],
                "feature_rarity": novelty_data["signal_2_feature_rarity"],
                "relationship_rarity": novelty_data["signal_3_relationship_rarity"],
                "graph_density": novelty_data["signal_4_graph_density"],
                "new_connection_discovery": novelty_data["signal_5_new_connection_discovery"]
            },
            "extracted_entities": entities,
            "trend_context": trend_data,
            "most_similar_projects": novelty_data["similar_projects"],
            "explanation_lines": novelty_data["explanation_bullets"],
            "graph_stats": graph_stats,
            "explainability": explainability,
        }

        log.info("Generated Explainable Novelty Report for Project %s (Score: %.1f)",
                 project_id, novelty_data["composite_novelty_score"])
        return report_json


# Singleton instance
report_generator_service = NoveltyReportGeneratorService()
