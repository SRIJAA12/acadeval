"""
Module 6 — Explainable Novelty Report Generator
=================================================
Combines Module 1-5 outputs into the structured JSON Explainable Novelty Report
schema defined in Section 7.6 of the AcadEval+ specification.
"""

import logging

from app.services.classifier import classifier_service
from app.services.extractor import extractor_service
from app.services.novelty_engine import novelty_engine_service
from app.services.trend_scorer import trend_scorer_service

log = logging.getLogger(__name__)


class NoveltyReportGeneratorService:
    def generate_full_report(self, project_id: str, title: str, abstract: str, github_url: str = None) -> dict:
        """
        Generates the complete Explainable Novelty Report JSON for a project proposal.
        """
        # Step 0: GitHub Repository Data Fetching (if URL provided)
        github_data = None
        if github_url:
            from app.services.github_fetcher import github_fetcher_service
            github_data = github_fetcher_service.fetch_repository_data(github_url)

        # Combine text for classification & extraction
        full_text = f"{title}\n{abstract}"
        if github_data and github_data.get("formatted_text"):
            full_text += f"\n\n{github_data['formatted_text']}"

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
            entities = extractor_service.extract_entities(full_text)

        # If GitHub tech stack was detected, merge into technologies/frameworks
        if github_data and github_data.get("detected_stack"):
            existing_techs = set(entities.get("technologies", []))
            for item in github_data["detected_stack"]:
                if item and item not in existing_techs:
                    entities.setdefault("technologies", []).append(item)
            entities["technologies"] = sorted(list(set(entities.get("technologies", []))))

        # Step 3: Module 4 — score the temporary candidate against the frozen
        # historical graph before it is eligible to join that graph.
        novelty_data = novelty_engine_service.compute_novelty_signals(
            project_id=project_id,
            extracted_entities=entities,
            domain=domain,
            sub_domain=sub_domain
        )

        # Graph ingestion is intentionally not performed by a report generator.
        # The pipeline persists the versioned score first and owns the later,
        # idempotent graph-ingestion step.

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
            "scoring_metadata": novelty_data.get("scoring_metadata"),
            "github_analysis": {
                "url": github_url,
                "valid": github_data.get("valid", False) if github_data else False,
                "owner": github_data.get("owner", "") if github_data else "",
                "repo": github_data.get("repo", "") if github_data else "",
                "description": github_data.get("description", "") if github_data else "",
                "primary_language": github_data.get("primary_language", "") if github_data else "",
                "topics": github_data.get("topics", []) if github_data else [],
                "detected_stack": github_data.get("detected_stack", []) if github_data else [],
                "file_structure": github_data.get("file_structure", []) if github_data else [],
                "readme_snippet": (github_data.get("readme_text", "")[:500] + "...") if github_data and github_data.get("readme_text") else "",
                "license": github_data.get("license", "") if github_data else "",
                "languages": github_data.get("languages", []) if github_data else [],
                "has_tests": github_data.get("has_tests", False) if github_data else False,
                "recent_commits": github_data.get("recent_commits", 0) if github_data else 0,
            } if github_url else None
        }

        log.info("Generated Explainable Novelty Report for Project %s (Score: %.1f)",
                 project_id, novelty_data["composite_novelty_score"])
        return report_json


# Singleton instance
report_generator_service = NoveltyReportGeneratorService()

