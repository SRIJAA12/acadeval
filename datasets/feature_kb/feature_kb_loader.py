"""
AcadEval Feature Knowledge Base Loader
========================================
Provides cached access to AcadEval_FeatureKnowledgeBase and generates
spaCy EntityRuler pattern dicts for Module 2 (Entity Extraction).
"""

import json
import logging
from functools import lru_cache
from pathlib import Path

# pandas is imported lazily inside load_feature_dataframe if needed
log = logging.getLogger(__name__)

KB_DIR = Path(__file__).parent
CSV_PATH = KB_DIR / "AcadEval_FeatureKnowledgeBase.csv"
JSON_PATH = KB_DIR / "AcadEval_FeatureKnowledgeBase.json"


@lru_cache(maxsize=1)
def load_feature_list() -> list[dict]:
    """Load Feature KB as a list of dicts."""
    if not JSON_PATH.exists():
        from feature_kb_generator import generate
        generate(KB_DIR)
    return json.loads(JSON_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_feature_dataframe():
    """Load Feature KB as a pandas DataFrame."""
    import pandas as pd
    return pd.DataFrame(load_feature_list())


def get_spacy_entity_ruler_patterns() -> list[dict]:
    """
    Generate spaCy EntityRuler pattern dictionaries.
    Example:
      {"label": "ALGORITHM", "pattern": "ResNet-50", "id": "FEAT-0001"}
    """
    features = load_feature_list()
    patterns = []
    for feat in features:
        label = feat["category"].upper()
        fid = feat.get("feature_id", feat["name"])
        
        # Primary name
        patterns.append({"label": label, "pattern": feat["name"], "id": fid})
        
        # Aliases
        for alias in feat.get("aliases", []):
            if alias and alias != feat["name"]:
                patterns.append({"label": label, "pattern": alias, "id": fid})
                
    log.info("Generated %d EntityRuler patterns from %d features", len(patterns), len(features))
    return patterns


def lookup_feature_by_name(name: str) -> dict | None:
    """Find a feature by name or alias (case-insensitive)."""
    name_clean = name.strip().lower()
    for feat in load_feature_list():
        if feat["name"].lower() == name_clean:
            return feat
        for alias in feat.get("aliases", []):
            if alias.lower() == name_clean:
                return feat
    return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    feats = load_feature_list()
    print(f"Loaded {len(feats)} features.")
    patterns = get_spacy_entity_ruler_patterns()
    print(f"Sample pattern: {patterns[0]}")
