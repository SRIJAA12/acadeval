"""
Module 9 — Explainable AI Layer (Service)
=========================================
Provides feature attribution and human-readable explanations for novelty scores.

Version 1 implementation:
- Linear Additive Feature Attribution based on the weighted sum model:
  Signals & Weights:
  1. Graph Distance          (Weight: 0.25)
  2. Feature Rarity          (Weight: 0.20)
  3. Relationship Rarity     (Weight: 0.20)
  4. Graph Density           (Weight: 0.15)
  5. New-Connection Discovery (Weight: 0.20)

Design:
- Extensible architecture with pluggable explainer backends.
- Abstract/Base interface `BaseNoveltyExplainer` to allow seamless integration
  of SHAP (e.g. `KernelExplainer`, `TreeExplainer`) when a trained
  regression/scoring ML model is introduced in future iterations.
"""

import logging
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

# Default weights as defined in Section 7.4 of the spec & NoveltyEngineService
DEFAULT_SIGNAL_WEIGHTS = {
    "signal_1_graph_distance": {
        "name": "Graph Distance",
        "weight": 0.25,
        "description": "Measures structural separation from historical project proposals in the knowledge graph.",
    },
    "signal_2_feature_rarity": {
        "name": "Feature Rarity",
        "weight": 0.20,
        "description": "Assesses uniqueness of extracted algorithms, technologies, and methods across the corpus.",
    },
    "signal_3_relationship_rarity": {
        "name": "Relationship Rarity",
        "weight": 0.20,
        "description": "Evaluates how rarely specific pairs of entities co-occur across historical projects.",
    },
    "signal_4_graph_density": {
        "name": "Graph Density",
        "weight": 0.15,
        "description": "Evaluates domain neighborhood sparsity (higher sparsity indicates unexplored areas).",
    },
    "signal_5_new_connection_discovery": {
        "name": "New-Connection Discovery",
        "weight": 0.20,
        "description": "Adamic-Adar metric indicating novel cross-domain feature synthesis and linkages.",
    },
}


class BaseNoveltyExplainer:
    """Base interface for novelty explainability backends."""

    def explain(self, novelty_data: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement explain()")


class LinearWeightedExplainer(BaseNoveltyExplainer):
    """
    Version 1 Explainer for linear weighted composite score models.
    Calculates exact weighted contributions and generates human-readable explanations.
    """

    def __init__(self, signal_config: Optional[Dict[str, Dict[str, Any]]] = None):
        self.config = signal_config or DEFAULT_SIGNAL_WEIGHTS

    def explain(self, novelty_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes novelty signals dictionary and returns detailed feature attributions.

        Args:
            novelty_data: Dict containing novelty engine output signals and scores.

        Returns:
            Dict containing per-signal weighted contributions, explanations, and metadata.
        """
        signal_explanations: List[Dict[str, Any]] = []
        total_weighted_contrib = 0.0

        for key, meta in self.config.items():
            raw_val = float(novelty_data.get(key, 0.0))
            # Clamp novelty signal value to [0.0, 1.0] range
            clamped_val = max(0.0, min(1.0, raw_val))
            weight = float(meta["weight"])

            # Weighted contribution out of 100 points
            weighted_contrib = round(clamped_val * weight * 100.0, 2)
            max_possible_contrib = round(weight * 100.0, 2)
            total_weighted_contrib += weighted_contrib

            # Human-readable factual explanation generation
            explanation_text = self._generate_signal_explanation(
                name=meta["name"],
                raw_val=clamped_val,
                weight=weight,
                weighted_contrib=weighted_contrib,
                max_possible=max_possible_contrib,
                base_desc=meta["description"],
            )

            signal_explanations.append({
                "signal_key": key,
                "signal_name": meta["name"],
                "raw_value": round(clamped_val, 4),
                "weight": weight,
                "weighted_contribution": weighted_contrib,
                "max_possible_contribution": max_possible_contrib,
                "percentage_of_max": round((clamped_val * 100.0), 1),
                "explanation": explanation_text,
            })

        composite_score = novelty_data.get(
            "composite_novelty_score", round(total_weighted_contrib, 1)
        )
        novelty_band = novelty_data.get("novelty_band", self._score_to_band(composite_score))

        top_signal_name = (
            max(signal_explanations, key=lambda x: x["weighted_contribution"])["signal_name"]
            if signal_explanations
            else "N/A"
        )

        overall_summary = (
            f"Project received an overall score of {composite_score}/100 ({novelty_band}). "
            f"Top contributing signal was '{top_signal_name}'."
        )

        return {
            "explainer_mode": "linear_weighted_v1",
            "composite_novelty_score": composite_score,
            "novelty_band": novelty_band,
            "overall_summary": overall_summary,
            "signals": signal_explanations,
        }

    def _generate_signal_explanation(
        self,
        name: str,
        raw_val: float,
        weight: float,
        weighted_contrib: float,
        max_possible: float,
        base_desc: str,
    ) -> str:
        return (
            f"{name} (raw value: {raw_val:.4f}, weight: {weight}): {base_desc} "
            f"Contributes {weighted_contrib:.2f} points (out of max {max_possible:.2f} points) "
            f"towards the overall composite novelty score."
        )

    @staticmethod
    def _score_to_band(score: float) -> str:
        if score >= 75.0:
            return "Highly Novel"
        elif score >= 50.0:
            return "Moderately Novel"
        return "Low Novelty / Incremental"


class SHAPExplainerStub(BaseNoveltyExplainer):
    """
    Placeholder/Plug-in interface for SHAP (SHapley Additive exPlanations).
    Will be activated when a trained ML regression model replaces or complements
    the linear weighted formula.
    """

    def __init__(self, model: Any = None, background_data: Any = None):
        self.model = model
        self.background_data = background_data

    def explain(self, novelty_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Computes SHAP values for trained models.
        Falls back to LinearWeightedExplainer when no model is available,
        or raises NotImplementedError if a model is supplied but SHAP calculation is not implemented.
        """
        if self.model is None:
            log.info("No trained ML model supplied to SHAPExplainerStub; falling back to LinearWeightedExplainer.")
            return LinearWeightedExplainer().explain(novelty_data)

        raise NotImplementedError("SHAP value calculation for trained ML models is not yet implemented.")


class ExplainabilityService:
    """
    Main Explainability Service managing explainer selection and narrative generation.
    """

    def __init__(self):
        self._linear_explainer = LinearWeightedExplainer()
        self._shap_explainer = SHAPExplainerStub()

    def generate_explanations(
        self, novelty_data: Dict[str, Any], use_ml_explainer: bool = False
    ) -> Dict[str, Any]:
        """
        Generates explainability metrics for novelty signals.

        Args:
            novelty_data: Output dict from NoveltyEngineService.compute_novelty_signals()
            use_ml_explainer: Flag to route through SHAP explainer when ML model is active.

        Returns:
            Dict containing formatted feature attribution, contributions, and explanations.
        """
        if use_ml_explainer:
            return self._shap_explainer.explain(novelty_data)
        return self._linear_explainer.explain(novelty_data)


# Singleton instance
explainability_service = ExplainabilityService()
