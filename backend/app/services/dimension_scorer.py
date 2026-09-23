"""
Module: AcadEval+ Dimension Scorer Service
==========================================
Computes deterministic, data-grounded evaluation scores (0-100) for:
  - Technical Depth (T)
  - Feasibility (F)
  - Completeness (C)
  - Clarity & IEEE Compliance (L)
  - Publication Potential (P)
  - Similarity Risk (S)
  - Overall Score (O)

Formula:
  Overall = 0.20*N + 0.20*T + 0.15*F + 0.15*C + 0.10*L + 0.10*P + 0.10*(100 - S)
"""

import os
import re
import math
import logging
from typing import Dict, List, Any, Optional
import pandas as pd

log = logging.getLogger(__name__)

# Master Corpus path
CORPUS_CSV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "datasets",
    "AcadEval_Corpus_MASTER.csv"
)

# Feature Knowledge Base path
FEATURE_KB_CSV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "datasets",
    "AcadEval_FeatureKnowledgeBase.csv"
)

# Trend Base path
TREND_BASE_CSV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "datasets",
    "AcadEval_TrendBase.csv"
)

# Algorithmic Complexity Tiers for Technical Depth
ALGO_COMPLEXITY_TIERS = {
    # Advanced / State-of-the-Art (Weight: 92 - 100)
    "transformer": 96, "bert": 94, "gpt": 95, "diffusion": 97, "gan": 93,
    "graph neural network": 95, "gnn": 95, "reinforcement learning": 94, "ppo": 95,
    "dqn": 93, "yolo": 90, "resnet": 88, "lstm": 86, "attention mechanism": 92,
    "contrastive learning": 94, "federated learning": 95, "zero-shot": 93, "few-shot": 92,
    "variational autoencoder": 92, "vae": 92, "vision transformer": 97, "vit": 97,
    "capsule network": 91, "spatial-temporal": 94, "bi-lstm": 89, "xgboost": 84, "lightgbm": 84,
    # Intermediate (Weight: 75 - 85)
    "random forest": 80, "support vector machine": 78, "svm": 78, "cnn": 82,
    "convolutional neural network": 82, "recurrent neural network": 82, "rnn": 82,
    "k-means": 72, "decision tree": 74, "naive bayes": 70, "logistic regression": 68,
    "linear regression": 65, "knn": 70, "k-nearest neighbors": 70, "gradient boosting": 82,
    "apriori": 70, "pca": 75, "principal component analysis": 75, "t-sne": 78,
}


def calculate_technical_depth(extracted_entities: Dict[str, Any], text: str = "") -> float:
    """
    Computes Technical Depth (0-100) based on:
    1. Algorithm complexity tier & diversity (40%)
    2. Technology stack breadth & depth (frameworks, libraries, hardware) (30%)
    3. Mathematical/algorithmic formulation in text (30%)
    """
    algorithms = [str(a).lower().strip() for a in extracted_entities.get("algorithms", [])]
    frameworks = extracted_entities.get("frameworks", []) + extracted_entities.get("libraries", [])
    hardware = extracted_entities.get("hardware", [])
    technologies = extracted_entities.get("technologies", [])

    # 1. Algorithm complexity score
    if algorithms:
        algo_scores = []
        for algo in algorithms:
            matched = False
            for key, score in ALGO_COMPLEXITY_TIERS.items():
                if key in algo or algo in key:
                    algo_scores.append(score)
                    matched = True
                    break
            if not matched:
                # Default for recognized specialized domain algorithms
                algo_scores.append(78.0)
        
        avg_algo_score = sum(algo_scores) / len(algo_scores)
        # Bonus for combining multiple distinct algorithms (hybrid architectures)
        diversity_bonus = min(10.0, (len(set(algorithms)) - 1) * 3.0)
        algo_component = min(100.0, avg_algo_score + diversity_bonus)
    else:
        algo_component = 60.0

    # 2. Tech stack breadth
    tech_count = len(technologies) + len(frameworks) + len(hardware)
    tech_component = min(100.0, 65.0 + (tech_count * 5.0))

    # 3. Methodological depth in text (equations, loss functions, metrics)
    text_lower = text.lower() if text else ""
    method_indicators = ["loss function", "optimization", "convergence", "backpropagation", "hyperparameter",
                         "gradient", "objective function", "complexity", "o(n", "o(log", "parameter", "latent space",
                         "architecture", "layer", "epoch", "batch size", "learning rate"]
    matched_indicators = sum(1 for ind in method_indicators if ind in text_lower)
    math_component = min(100.0, 60.0 + (matched_indicators * 4.0))

    depth_score = (0.40 * algo_component) + (0.30 * tech_component) + (0.30 * math_component)
    return round(max(0.0, min(100.0, depth_score)), 1)


def calculate_feasibility(extracted_entities: Dict[str, Any], text: str = "") -> float:
    """
    Computes Feasibility (0-100) based on:
    1. Dataset accessibility & presence (40%)
    2. Framework/Library maturity (30%)
    3. Hardware requirements feasibility (30%)
    """
    datasets = extracted_entities.get("datasets", [])
    frameworks = extracted_entities.get("frameworks", []) + extracted_entities.get("libraries", [])
    hardware = extracted_entities.get("hardware", [])
    text_lower = text.lower() if text else ""

    # 1. Dataset availability
    if datasets and len(datasets) > 0:
        dataset_score = 90.0 if len(datasets) >= 2 else 82.0
    elif any(term in text_lower for term in ["dataset", "kaggle", "uci", "benchmark", "corpus", "github", "collected"]):
        dataset_score = 75.0
    else:
        dataset_score = 60.0

    # 2. Standard open-source tooling
    mature_tools = ["pytorch", "tensorflow", "keras", "scikit-learn", "opencv", "numpy", "pandas",
                    "huggingface", "fastapi", "react", "node", "flask", "django", "spacy", "nltk"]
    tool_matches = sum(1 for tool in mature_tools if any(tool in str(f).lower() for f in frameworks) or tool in text_lower)
    tool_score = min(100.0, 70.0 + (tool_matches * 5.0))

    # 3. Hardware realism (GPU/TPU/Cloud specified vs unrealistic setup)
    if hardware or any(h in text_lower for h in ["gpu", "cuda", "rtx", "colab", "aws", "v100", "a100", "cpu", "tpu"]):
        hw_score = 88.0
    else:
        hw_score = 75.0

    feasibility = (0.40 * dataset_score) + (0.30 * tool_score) + (0.30 * hw_score)
    return round(max(0.0, min(100.0, feasibility)), 1)


def calculate_completeness(parsed_sections: Dict[str, Any], text: str = "", github_url: Optional[str] = None) -> float:
    """
    Computes Completeness (0-100) based on:
    1. Structural presence of 7 standard IEEE sections (60%)
    2. Length & detail depth (25%)
    3. Code / Artifact link availability (15%)
    """
    required_sections = [
        ("abstract", ["abstract", "summary", "overview"]),
        ("introduction", ["introduction", "background", "motivation"]),
        ("problem_statement", ["problem statement", "problem definition", "objective", "scope"]),
        ("methodology", ["methodology", "proposed methodology", "proposed system", "method", "approach"]),
        ("architecture", ["architecture", "system design", "workflow", "model architecture", "block diagram"]),
        ("results", ["result", "experimental result", "evaluation", "performance", "discussion"]),
        ("conclusion", ["conclusion", "future work", "summary"]),
        ("references", ["references", "bibliography", "citations"]),
    ]

    text_lower = text.lower() if text else ""
    sections_found = 0
    for key, aliases in required_sections:
        if parsed_sections and key in parsed_sections and len(str(parsed_sections[key])) > 30:
            sections_found += 1
        elif any(alias in text_lower for alias in aliases):
            sections_found += 1

    section_score = (sections_found / len(required_sections)) * 100.0

    # Length / depth check
    word_count = len(text.split()) if text else 0
    if word_count > 1500:
        length_score = 95.0
    elif word_count > 800:
        length_score = 85.0
    elif word_count > 300:
        length_score = 75.0
    else:
        length_score = 60.0

    # Artifact / GitHub link check
    code_score = 95.0 if (github_url or "github.com" in text_lower or "gitlab.com" in text_lower) else 70.0

    completeness = (0.60 * section_score) + (0.25 * length_score) + (0.15 * code_score)
    return round(max(0.0, min(100.0, completeness)), 1)


def calculate_clarity(writing_quality: Optional[Dict[str, Any]], citation_info: Optional[Dict[str, Any]]) -> float:
    """
    Computes Clarity & IEEE Compliance (0-100):
      Clarity = 0.50 * Readability_Score + 0.50 * IEEE_Compliance_Score
    """
    # 1. Readability (Flesch Reading Ease normalized to 0-100 scale, ideal academic 40-70 -> 80-100)
    readability_raw = 75.0
    if writing_quality and isinstance(writing_quality, dict):
        readability_raw = float(
            writing_quality.get("readability") or
            writing_quality.get("metrics", {}).get("readability") or
            75.0
        )
    
    # Scale Flesch score so academic range 40-70 gives 85-98
    if readability_raw >= 30:
        readability_norm = min(100.0, 70.0 + (readability_raw * 0.35))
    else:
        readability_norm = max(40.0, readability_raw * 2.0)

    # 2. IEEE Compliance
    ieee_compliance = 85.0
    if citation_info and isinstance(citation_info, dict):
        ieee_compliance = float(
            citation_info.get("ieeeCompliancePercent") or
            citation_info.get("summary", {}).get("ieee_compliance_percent") or
            citation_info.get("ieee_compliance_pct") or
            85.0
        )

    clarity = (0.50 * readability_norm) + (0.50 * ieee_compliance)
    return round(max(0.0, min(100.0, clarity)), 1)


def calculate_publication_potential(
    novelty_score: float,
    domain: str = "",
    citation_count: int = 10,
    text: str = ""
) -> float:
    """
    Computes Publication Potential (0-100):
      Publication = 0.40 * Novelty + 0.40 * Trend_Velocity + 0.20 * Citation_Rigor
    """
    # 1. Novelty component
    nov_comp = max(0.0, min(100.0, float(novelty_score)))

    # 2. Trend Velocity from TrendBase
    trend_velocity = 80.0
    if os.path.exists(TREND_BASE_CSV_PATH):
        try:
            df_trend = pd.read_csv(TREND_BASE_CSV_PATH)
            domain_clean = str(domain).lower().strip()
            matched_row = None
            for _, row in df_trend.iterrows():
                topic_str = str(row.get("Topic", "")).lower()
                if domain_clean and (domain_clean in topic_str or topic_str in domain_clean):
                    matched_row = row
                    break
            if matched_row is not None:
                growth = float(matched_row.get("Growth_Rate_Pct", 15.0))
                # Map growth rate (e.g. 10% to 40%) to score 75-98
                trend_velocity = min(100.0, 70.0 + (growth * 0.8))
        except Exception as e:
            log.warning("Could not read TrendBase for publication potential: %s", e)

    # 3. Citation & empirical rigor
    citation_rigor = min(100.0, 70.0 + (min(citation_count, 20) * 1.5))

    publication_score = (0.40 * nov_comp) + (0.40 * trend_velocity) + (0.20 * citation_rigor)
    return round(max(0.0, min(100.0, publication_score)), 1)


def calculate_similarity_risk(title: str, abstract: str = "", domain: str = "") -> float:
    """
    Computes Similarity Risk (0-100) against AcadEval_Corpus_MASTER.csv.
    Higher score = higher plagiarism/similarity risk.
    """
    if not os.path.exists(CORPUS_CSV_PATH) or not title:
        return 12.0

    try:
        df = pd.read_csv(CORPUS_CSV_PATH)
        titles = df["Title"].dropna().astype(str).tolist()
        
        # Tokenize query title
        title_tokens = set(re.findall(r"\w+", title.lower()))
        if not title_tokens:
            return 10.0

        max_sim = 0.0
        for other_title in titles:
            other_tokens = set(re.findall(r"\w+", other_title.lower()))
            if not other_tokens:
                continue
            # Jaccard word overlap
            intersect = len(title_tokens & other_tokens)
            union = len(title_tokens | other_tokens)
            if union > 0:
                sim = intersect / float(union)
                if sim > max_sim:
                    max_sim = sim

        # Map overlap (0.0 - 1.0) to risk percentage (5.0% - 95.0%)
        # A normal innovative project will have 0.1 - 0.2 word overlap with related titles (8% - 18% risk)
        # An exact copy will have > 0.8 overlap (> 80% risk)
        risk_score = round(max_sim * 100.0, 1)
        return max(5.0, min(95.0, risk_score))
    except Exception as e:
        log.warning("Failed calculating similarity risk against corpus: %s", e)
        return 12.0


def calculate_overall_score(
    novelty: float,
    technical_depth: float,
    feasibility: float,
    completeness: float,
    clarity: float,
    publication_potential: float,
    similarity_risk: float
) -> tuple[float, str]:
    """
    Computes weighted Overall Score (0-100) and letter Grade:
      Overall = 0.20*N + 0.20*T + 0.15*F + 0.15*C + 0.10*L + 0.10*P + 0.10*(100 - S)
    """
    n = max(0.0, min(100.0, float(novelty)))
    t = max(0.0, min(100.0, float(technical_depth)))
    f = max(0.0, min(100.0, float(feasibility)))
    c = max(0.0, min(100.0, float(completeness)))
    l = max(0.0, min(100.0, float(clarity)))
    p = max(0.0, min(100.0, float(publication_potential)))
    s = max(0.0, min(100.0, float(similarity_risk)))

    weighted = (
        (0.20 * n) +
        (0.20 * t) +
        (0.15 * f) +
        (0.15 * c) +
        (0.10 * l) +
        (0.10 * p) +
        (0.10 * (100.0 - s))
    )
    final_score = round(weighted, 1)
    grade = (
        "A+" if final_score >= 90.0 else
        "A"  if final_score >= 80.0 else
        "B"  if final_score >= 70.0 else
        "C"  if final_score >= 50.0 else
        "D"
    )
    return final_score, grade
