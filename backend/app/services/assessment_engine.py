"""Versioned, deterministic scoring for the non-novelty report dimensions.

The engine deliberately scores only evidence found in the submitted text and
the structured entities extracted from it.  It does not infer team size,
budget, available hardware, or completed experiments when they are absent.
This keeps the prototype explainable and gives the journal evaluation a stable
method that can be reproduced without an external LLM.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from typing import Any


ASSESSMENT_METHOD_VERSION = "evidence-assessment-v1.0"


SECTION_RULES: dict[str, tuple[str, ...]] = {
    "Abstract": ("abstract", "executive summary"),
    "Problem statement / objectives": (
        "problem statement", "research question", "objectives", "aims",
    ),
    "Literature review": ("literature review", "related work", "background"),
    "Methodology": ("methodology", "proposed method", "approach"),
    "System design / architecture": (
        "system design", "system architecture", "architecture", "proposed system", "design overview",
    ),
    "Data / requirements": (
        "dataset", "data collection", "requirements", "hardware requirements",
        "software requirements",
    ),
    "Implementation": ("implementation", "development", "modules"),
    "Evaluation / results": (
        "evaluation", "experiments", "results", "performance analysis", "testing",
    ),
    "Conclusion / future work": ("conclusion", "future work", "limitations"),
    "References": ("references", "bibliography", "works cited"),
}

METRIC_TERMS = (
    "accuracy", "precision", "recall", "f1", "auc", "rmse", "mae", "latency",
    "throughput", "benchmark", "baseline", "validation", "user study",
)
RESOURCE_INTENSIVE_TERMS = (
    "large language model", "llm", "transformer", "3d", "real-time video",
    "gpu", "cuda", "edge device", "iot", "virtual reality", "blockchain",
)
RISK_TERMS = (
    "external api", "third-party", "real-time", "clinical", "medical", "patient",
    "financial", "biometric", "personal data", "sensor", "hardware", "internet",
)
MITIGATION_TERMS = (
    "fallback", "privacy", "consent", "anonym", "encrypt", "offline", "cache",
    "backup", "risk mitigation", "ethics", "approval", "rate limit",
)


def _clamp(value: float) -> float:
    return round(max(0.0, min(100.0, float(value))), 1)


def _normalise_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").casefold()).strip()


def _contains_any(text: str, terms: Iterable[str]) -> list[str]:
    return [term for term in terms if re.search(rf"\b{re.escape(term)}\b", text)]


def _entity_values(entities: Mapping[str, Any], key: str) -> list[str]:
    values = entities.get(key, [])
    if not isinstance(values, list):
        return []
    return sorted({str(value).strip() for value in values if str(value).strip()})


def weighted_mean(parts: Iterable[tuple[float | None, float]]) -> float | None:
    available = [(float(score), float(weight)) for score, weight in parts if score is not None]
    total_weight = sum(weight for _score, weight in available)
    if not available or total_weight <= 0:
        return None
    return _clamp(sum(score * weight for score, weight in available) / total_weight)


def grade_for(score: float | None) -> str:
    if score is None:
        return "N/A"
    if score >= 90:
        return "A+"
    if score >= 80:
        return "A"
    if score >= 70:
        return "B"
    if score >= 60:
        return "C"
    if score >= 50:
        return "D"
    return "Needs Work"


def overall_score(scores: Mapping[str, float | None]) -> float | None:
    """Apply the documented rubric, treating similarity as a risk/penalty."""
    risk = scores.get("similarity_risk")
    originality = None if risk is None else 100.0 - float(risk)
    return weighted_mean((
        (scores.get("novelty"), 0.20),
        (scores.get("feasibility"), 0.20),
        (scores.get("completeness"), 0.15),
        (scores.get("technical_depth"), 0.20),
        (scores.get("clarity"), 0.10),
        (originality, 0.10),
        (scores.get("publication_potential"), 0.05),
    ))


def section_presence(text: str) -> dict[str, bool]:
    """Detect section headings while avoiding arbitrary body-word matches."""
    lines = [re.sub(r"^[\s#*\d.()_-]+", "", line).strip().casefold()
             for line in (text or "").splitlines()]
    heading_lines = [line for line in lines if 1 <= len(line.split()) <= 8]
    result: dict[str, bool] = {}
    for label, aliases in SECTION_RULES.items():
        result[label] = any(
            any(re.match(rf"^{re.escape(alias)}(?:\s|:|-|$)", line) for alias in aliases)
            for line in heading_lines
        )
    return result


def _criterion(score: float, evidence: list[str], gaps: list[str]) -> dict[str, Any]:
    return {"score": _clamp(score), "evidence": evidence, "gaps": gaps}


def _feasibility(text: str, entities: Mapping[str, Any], github_url: str | None) -> dict[str, Any]:
    datasets = _entity_values(entities, "datasets")
    technologies = _entity_values(entities, "technologies")
    frameworks = _entity_values(entities, "frameworks")
    libraries = _entity_values(entities, "libraries")
    hardware = _entity_values(entities, "hardware")
    metrics = _entity_values(entities, "metrics")

    data_terms = _contains_any(text, ("dataset", "data collection", "public data", "survey", "sensor data", "database"))
    data_score = 100 if datasets else 70 if data_terms else 20
    data_evidence = ([f"Named datasets: {', '.join(datasets[:4])}"] if datasets else
                     [f"Data plan terms: {', '.join(data_terms[:4])}"] if data_terms else [])
    data_gaps = [] if data_score >= 70 else ["Name the data source and explain access, size, and licensing."]

    stack = technologies + frameworks + libraries
    architecture_terms = _contains_any(text, ("architecture", "pipeline", "api", "frontend", "backend", "database", "module"))
    implementation_score = min(100, 30 + len(stack[:4]) * 12 + len(architecture_terms[:3]) * 8 + (10 if github_url else 0))
    implementation_evidence = []
    if stack:
        implementation_evidence.append(f"Implementation stack: {', '.join(stack[:6])}")
    if architecture_terms:
        implementation_evidence.append(f"System detail terms: {', '.join(architecture_terms[:4])}")
    if github_url:
        implementation_evidence.append("A source repository URL was supplied.")
    implementation_gaps = [] if implementation_score >= 65 else ["Specify the architecture, components, and implementation stack."]

    metric_terms = sorted(set(metrics + _contains_any(text, METRIC_TERMS)))
    experiment_terms = _contains_any(text, ("experiment", "test set", "cross-validation", "ablation", "comparison", "user study"))
    evaluation_score = min(100, 20 + len(metric_terms[:4]) * 15 + len(experiment_terms[:2]) * 10)
    evaluation_evidence = [f"Evaluation evidence: {', '.join((metric_terms + experiment_terms)[:6])}"] if metric_terms or experiment_terms else []
    evaluation_gaps = [] if evaluation_score >= 65 else ["Define measurable metrics, baselines, and a validation protocol."]

    intensive = _contains_any(text, RESOURCE_INTENSIVE_TERMS)
    resource_mentions = hardware + _contains_any(text, ("workstation", "cloud", "server", "memory", "cpu", "gpu", "device"))
    if intensive and not resource_mentions:
        resource_score = 30
    elif intensive:
        resource_score = 75
    else:
        resource_score = 80 if stack else 50
    resource_evidence = [f"Resource evidence: {', '.join(resource_mentions[:5])}"] if resource_mentions else []
    resource_gaps = (["State the compute/hardware capacity required by the proposed workload."]
                     if intensive and not resource_mentions else [])

    planning_terms = _contains_any(text, ("timeline", "milestone", "phase", "week", "schedule", "deliverable", "module"))
    objective_terms = _contains_any(text, ("objective", "aim", "scope", "deliverable"))
    planning_score = 85 if len(planning_terms) >= 2 else 60 if planning_terms or objective_terms else 25
    planning_evidence = [f"Planning evidence: {', '.join((planning_terms + objective_terms)[:5])}"] if planning_terms or objective_terms else []
    planning_gaps = [] if planning_score >= 60 else ["Add milestones, deliverables, and an achievable project schedule."]

    risks = _contains_any(text, RISK_TERMS)
    mitigations = _contains_any(text, MITIGATION_TERMS)
    risk_score = 80 if risks and mitigations else 40 if risks else 70
    risk_evidence = []
    if risks:
        risk_evidence.append(f"Dependencies/risks mentioned: {', '.join(risks[:5])}")
    if mitigations:
        risk_evidence.append(f"Mitigations mentioned: {', '.join(mitigations[:5])}")
    risk_gaps = (["Document mitigations for external, ethical, privacy, or hardware dependencies."]
                 if risks and not mitigations else [])

    criteria = {
        "data_availability": _criterion(data_score, data_evidence, data_gaps),
        "implementation_plan": _criterion(implementation_score, implementation_evidence, implementation_gaps),
        "evaluation_plan": _criterion(evaluation_score, evaluation_evidence, evaluation_gaps),
        "resource_fit": _criterion(resource_score, resource_evidence, resource_gaps),
        "scope_and_schedule": _criterion(planning_score, planning_evidence, planning_gaps),
        "dependency_risk": _criterion(risk_score, risk_evidence, risk_gaps),
    }
    score = weighted_mean((item["score"], 1.0) for item in criteria.values()) or 0.0
    return {"score": score, "criteria": criteria}


def _completeness(text: str, submission_type: str) -> dict[str, Any]:
    if submission_type == "abstract":
        return {
            "score": None,
            "present_sections": [],
            "missing_sections": [],
            "reason": "Completeness requires a full document or presentation.",
        }
    presence = section_presence(text)
    present = [name for name, found in presence.items() if found]
    missing = [name for name, found in presence.items() if not found]
    score = _clamp(len(present) / len(presence) * 100.0)
    return {"score": score, "present_sections": present, "missing_sections": missing}


def _technical_depth(text: str, entities: Mapping[str, Any]) -> dict[str, Any]:
    entity_groups = {
        name: _entity_values(entities, name)
        for name in ("algorithms", "technologies", "frameworks", "libraries", "datasets", "hardware", "metrics")
    }
    named_entities = sorted({value for values in entity_groups.values() for value in values})
    represented_categories = sum(bool(values) for values in entity_groups.values())
    specificity_score = min(100, len(named_entities[:8]) * 8 + represented_categories * 8)

    method_terms = _contains_any(text, (
        "algorithm", "model", "method", "training", "preprocessing", "optimization",
        "feature extraction", "inference", "protocol", "query", "schema",
    ))
    method_score = min(100, 20 + len(method_terms) * 10 + min(len(_entity_values(entities, "algorithms")), 3) * 15)

    architecture_terms = _contains_any(text, (
        "architecture", "pipeline", "component", "module", "api", "database",
        "frontend", "backend", "deployment", "workflow",
    ))
    architecture_score = min(100, 15 + len(architecture_terms) * 10)

    evaluation_terms = sorted(set(_entity_values(entities, "metrics") + _contains_any(text, METRIC_TERMS)))
    evaluation_score = min(100, 15 + len(evaluation_terms) * 12)

    reproducibility_terms = _contains_any(text, (
        "github", "repository", "docker", "requirements", "configuration", "seed",
        "test", "open source", "license", "version",
    ))
    reproducibility_score = min(100, 20 + len(reproducibility_terms) * 13)

    criteria = {
        "technical_specificity": _criterion(
            specificity_score,
            [f"Named technical entities: {', '.join(named_entities[:8])}"] if named_entities else [],
            [] if specificity_score >= 60 else ["Name the concrete algorithms, data, frameworks, and metrics."],
        ),
        "method_detail": _criterion(
            method_score,
            [f"Method terms: {', '.join(method_terms[:6])}"] if method_terms else [],
            [] if method_score >= 60 else ["Explain processing steps and algorithm/model choices."],
        ),
        "architecture_detail": _criterion(
            architecture_score,
            [f"Architecture terms: {', '.join(architecture_terms[:6])}"] if architecture_terms else [],
            [] if architecture_score >= 60 else ["Add a component-level architecture and data flow."],
        ),
        "evaluation_rigor": _criterion(
            evaluation_score,
            [f"Metrics/baselines: {', '.join(evaluation_terms[:6])}"] if evaluation_terms else [],
            [] if evaluation_score >= 60 else ["Define quantitative metrics, baselines, and experiments."],
        ),
        "reproducibility": _criterion(
            reproducibility_score,
            [f"Reproducibility terms: {', '.join(reproducibility_terms[:6])}"] if reproducibility_terms else [],
            [] if reproducibility_score >= 60 else ["Document setup, versions, tests, and reproducibility steps."],
        ),
    }
    score = weighted_mean((item["score"], 1.0) for item in criteria.values()) or 0.0
    return {"score": score, "criteria": criteria}


def _citation_quality(citations: Mapping[str, Any]) -> float | None:
    if not citations or citations.get("status") == "not_applicable":
        return None
    summary = citations.get("summary", {}) if isinstance(citations.get("summary"), dict) else {}
    count = int(summary.get("reference_count", 0) or 0)
    if count == 0:
        return 0.0
    volume = min(100.0, count / 10.0 * 100.0)
    verified = float(summary.get("percent_verified", 0.0) or 0.0)
    recent = float(summary.get("percent_recent", 0.0) or 0.0)
    return weighted_mean(((volume, 0.25), (verified, 0.45), (recent, 0.30)))


class AssessmentEngine:
    @staticmethod
    def input_hash(
        title: str,
        submission_type: str,
        abstract: str,
        full_text: str,
        entities: Mapping[str, Any],
        novelty_score: float | None,
    ) -> str:
        payload = {
            "title": title,
            "submission_type": submission_type,
            "abstract": abstract,
            "full_text": full_text,
            "entities": entities,
            "novelty_score": novelty_score,
            "method": ASSESSMENT_METHOD_VERSION,
        }
        canonical = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def evaluate(
        self,
        *,
        title: str,
        submission_type: str,
        abstract: str,
        full_text: str,
        entities: Mapping[str, Any],
        novelty_score: float | None,
        similar_projects: list[Mapping[str, Any]],
        writing_analysis: Mapping[str, Any],
        citation_analysis: Mapping[str, Any],
        github_url: str | None = None,
    ) -> dict[str, Any]:
        combined_text = "\n".join(value for value in (title, abstract, full_text) if value).strip()
        normalised = _normalise_text(combined_text)
        feasibility = _feasibility(normalised, entities, github_url)
        completeness = _completeness(combined_text, submission_type)
        technical = _technical_depth(normalised, entities)

        writing_metrics = writing_analysis.get("metrics", {}) if isinstance(writing_analysis, Mapping) else {}
        clarity = writing_analysis.get("quality_score") if isinstance(writing_analysis, Mapping) else None
        clarity = float(clarity) if clarity is not None else None

        nearest_similarity = 0.0
        if similar_projects:
            nearest_similarity = max(float(item.get("similarity_score", 0.0) or 0.0) for item in similar_projects)
        similarity_risk = _clamp(nearest_similarity * 100.0)
        originality = 100.0 - similarity_risk

        citation_quality = _citation_quality(citation_analysis)
        publication_potential = weighted_mean((
            (novelty_score, 0.30),
            (technical["score"], 0.25),
            (completeness["score"], 0.20),
            (clarity, 0.10),
            (citation_quality, 0.15),
        ))

        overall = overall_score({
            "novelty": novelty_score,
            "feasibility": feasibility["score"],
            "completeness": completeness["score"],
            "technical_depth": technical["score"],
            "clarity": clarity,
            "similarity_risk": similarity_risk,
            "publication_potential": publication_potential,
        })

        evidence_quality = "full_document" if submission_type != "abstract" and len(combined_text.split()) >= 500 else "limited"
        if submission_type == "abstract":
            evidence_quality = "abstract_only"

        strengths: list[str] = []
        weaknesses: list[str] = []
        dimension_pairs = (
            ("Feasibility", feasibility["score"]),
            ("Completeness", completeness["score"]),
            ("Technical depth", technical["score"]),
            ("Clarity", clarity),
            ("Originality", originality),
            ("Publication readiness", publication_potential),
        )
        for label, value in dimension_pairs:
            if value is not None and value >= 75:
                strengths.append(f"{label} is supported by the submitted evidence ({value:.1f}/100).")
            elif value is not None and value < 50:
                weaknesses.append(f"{label} has limited supporting evidence ({value:.1f}/100).")

        gaps: list[str] = []
        for block in (feasibility, technical):
            for criterion in block["criteria"].values():
                gaps.extend(criterion["gaps"])
        gaps.extend(f"Add a clearly labelled {name} section." for name in completeness["missing_sections"][:4])

        roadmap = [
            {
                "week": 1,
                "focus": "Evidence and feasibility",
                "actions": gaps[:2] or ["Verify data access, resource needs, and evaluation constraints."],
            },
            {
                "week": 2,
                "focus": "Technical validation",
                "actions": gaps[2:4] or ["Run baseline comparisons and report quantitative metrics."],
            },
            {
                "week": 3,
                "focus": "Reproducibility and publication",
                "actions": gaps[4:6] or ["Document setup, limitations, citations, and reproducibility steps."],
            },
        ]

        return {
            "method_version": ASSESSMENT_METHOD_VERSION,
            "evidence_quality": evidence_quality,
            "scores": {
                "feasibility": feasibility["score"],
                "completeness": completeness["score"],
                "technical_depth": technical["score"],
                "clarity": _clamp(clarity) if clarity is not None else None,
                "similarity_risk": similarity_risk,
                "publication_potential": publication_potential,
                "overall": overall,
            },
            "feasibility": feasibility,
            "completeness": completeness,
            "technical_depth": technical,
            "writing": {
                "quality_score": clarity,
                "word_count": writing_metrics.get("word_count", 0),
                "method_version": writing_analysis.get("method_version"),
            },
            "citations": {
                "quality_score": citation_quality,
                "status": citation_analysis.get("status", "no_data"),
            },
            "similarity": {
                "nearest_similarity_percent": similarity_risk,
                "nearest_projects": similar_projects[:5],
            },
            "strengths": strengths,
            "weaknesses": weaknesses,
            "gaps": list(dict.fromkeys(gaps)),
            "improvement_roadmap": roadmap,
            "grade": grade_for(overall),
        }


assessment_engine = AssessmentEngine()
