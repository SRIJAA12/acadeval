"""
Entity Normalizer & Canonicalization Service
============================================
Cleans, normalizes, and canonicalizes extracted entities:
1. Strips synthetic expansion suffixes (e.g. 'Toolkit-1734', 'Mod-104', 'Feature Component-1140')
2. Maps well-known acronyms and phrase variants to a single canonical name
   (e.g. 'RAG' + 'Retrieval-Augmented Generation' -> 'Retrieval-Augmented Generation (RAG)')
3. Case-insensitive and alias-level deduplication across categories
"""

import re
from typing import Dict, List, Set

# Known acronyms and synonyms to canonical representation
SYNONYM_MAP: Dict[str, str] = {
    # RAG / Search
    "rag": "Retrieval-Augmented Generation (RAG)",
    "retrieval-augmented generation": "Retrieval-Augmented Generation (RAG)",
    "retrieval augmented generation": "Retrieval-Augmented Generation (RAG)",
    "vector search rag": "Retrieval-Augmented Generation (RAG)",
    "dense retrieval rag": "Retrieval-Augmented Generation (RAG)",
    "dense retrieval": "Retrieval-Augmented Generation (RAG)",

    # NLP / NLTK
    "nlp": "Natural Language Processing (NLP)",
    "natural language processing": "Natural Language Processing (NLP)",
    "natural language processing toolkit": "NLTK",
    "nltk": "NLTK",
    "sbert": "Sentence-BERT (SBERT)",
    "sentence-bert": "Sentence-BERT (SBERT)",
    "sentence transformers": "Sentence-BERT (SBERT)",
    "roberta": "RoBERTa",
    "vit": "Vision Transformer (ViT)",
    "vision transformer": "Vision Transformer (ViT)",

    # Web & Frameworks
    "react": "React",
    "react.js": "React",
    "reactjs": "React",

    # Computer Vision / Deep Learning Architectures
    "cnn": "Convolutional Neural Network (CNN)",
    "convolutional neural network": "Convolutional Neural Network (CNN)",
    "convolutional neural networks": "Convolutional Neural Network (CNN)",
    "rnn": "Recurrent Neural Network (RNN)",
    "recurrent neural network": "Recurrent Neural Network (RNN)",
    "recurrent neural networks": "Recurrent Neural Network (RNN)",
    "lstm": "Long Short-Term Memory (LSTM)",
    "long short-term memory": "Long Short-Term Memory (LSTM)",
    "gru": "Gated Recurrent Unit (GRU)",
    "gated recurrent unit": "Gated Recurrent Unit (GRU)",
    "gan": "Generative Adversarial Network (GAN)",
    "generative adversarial network": "Generative Adversarial Network (GAN)",
    "generative adversarial networks": "Generative Adversarial Network (GAN)",
    "transformer": "Transformer Architecture",
    "transformers": "Transformer Architecture",

    # NLP Models
    "bert": "BERT",
    "bidirectional encoder representations from transformers": "BERT",
    "gpt": "Generative Pre-trained Transformer (GPT)",
    "generative pre-trained transformer": "Generative Pre-trained Transformer (GPT)",
    "llm": "Large Language Model (LLM)",
    "llms": "Large Language Model (LLM)",
    "large language model": "Large Language Model (LLM)",
    "large language models": "Large Language Model (LLM)",
    "ner": "Named Entity Recognition (NER)",
    "named entity recognition": "Named Entity Recognition (NER)",

    # Classical ML & Stats
    "svm": "Support Vector Machine (SVM)",
    "support vector machine": "Support Vector Machine (SVM)",
    "support vector machines": "Support Vector Machine (SVM)",
    "knn": "K-Nearest Neighbors (KNN)",
    "k-nearest neighbors": "K-Nearest Neighbors (KNN)",
    "k nearest neighbors": "K-Nearest Neighbors (KNN)",
    "random forest": "Random Forest",
    "random forests": "Random Forest",
    "gradient boosting": "Gradient Boosting",
    "xgboost": "XGBoost",
    "lightgbm": "LightGBM",
    "tf-idf": "TF-IDF",
    "tfidf": "TF-IDF",
    "term frequency-inverse document frequency": "TF-IDF",
    "rl": "Reinforcement Learning (RL)",
    "reinforcement learning": "Reinforcement Learning (RL)",

    # Graph Databases & Tech
    "neo4j": "Neo4j",
    "neo4j graph data science": "Neo4j Graph Data Science (GDS)",
    "gds": "Neo4j Graph Data Science (GDS)",
    "graph data science": "Neo4j Graph Data Science (GDS)",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "redis": "Redis",
    "celery": "Celery",
    "docker": "Docker",
    "kubernetes": "Kubernetes",

    # Libraries
    "spacy": "spaCy",
    "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "keras": "Keras",
    "hugging face": "Hugging Face Transformers",
    "huggingface": "Hugging Face Transformers",
    "hugging face transformers": "Hugging Face Transformers",
    "lime": "LIME",
    "shap": "SHAP",

    # Datasets & Benchmarks
    "historical corpus": "AcadEval Historical Corpus",
    "acadeval historical corpus": "AcadEval Historical Corpus",
    "acadeval corpus": "AcadEval Historical Corpus",
    "acadeval_corpus_master": "AcadEval Historical Corpus",
    "master corpus": "AcadEval Historical Corpus",
    "acadeval domain taxonomy": "AcadEval Domain Taxonomy",
    "domain taxonomy": "AcadEval Domain Taxonomy",
    "acadeval_domaintaxonomy": "AcadEval Domain Taxonomy",
    "acadeval feature knowledge base": "AcadEval Feature Knowledge Base",
    "feature knowledge base": "AcadEval Feature Knowledge Base",
    "acadeval_featureknowledgebase": "AcadEval Feature Knowledge Base",
    "simbench": "AcadEval SimBench Benchmark",
    "acadeval simbench": "AcadEval SimBench Benchmark",
    "simbench benchmark": "AcadEval SimBench Benchmark",
    "acadeval_simbench": "AcadEval SimBench Benchmark",
    "trendbase": "AcadEval TrendBase",
    "acadeval trendbase": "AcadEval TrendBase",
    "acadeval_trendbase": "AcadEval TrendBase",
    "imagenet": "ImageNet",
    "coco": "COCO Dataset",
    "mnist": "MNIST",
    "squad": "SQuAD",
    "glue": "GLUE Benchmark",
    "mimic-iii": "MIMIC-III",
    "mimic iii": "MIMIC-III",

    # Metrics
    "f1": "F1-Score",
    "f1-score": "F1-Score",
    "f1 score": "F1-Score",
    "f-measure": "F1-Score",
    "accuracy": "Accuracy",
    "precision": "Precision",
    "recall": "Recall",
    "roc-auc": "ROC-AUC",
    "roc auc": "ROC-AUC",
    "pr-auc": "PR-AUC",
    "pr auc": "PR-AUC",
    "bleu": "BLEU Score",
    "rouge": "ROUGE Score",
    "perplexity": "Perplexity",
    "mse": "Mean Squared Error (MSE)",
    "rmse": "Root Mean Squared Error (RMSE)",
    "mae": "Mean Absolute Error (MAE)",
}

# Regex pattern to match synthetic repetitive suffixes like:
# ' Mod-104', '-1734', ' Feature Component-1140', ' Feature Module', ' Component-22'
SYNTHETIC_SUFFIX_REGEX = re.compile(
    r"""(?ix)
    \s*(?:
        (?:Mod|Component|Feature\s*(?:Component|Module|ScaleUnit|Unit|Pattern|Variation|Config|Cluster|Type|Instance|Sample))
        (?:[\s\-_]*\d+)?
        |
        [\-_]\d{2,}
    )\s*$
    """
)


def normalize_entity_name(name: str) -> str:
    """
    Cleans a single entity name:
    1. Trims whitespace and surrounding quotes
    2. Strips synthetic variation suffixes (e.g. '-1734', 'Mod-8', 'Feature Component-1140')
    3. Resolves well-known acronyms and synonyms to a canonical title
    """
    if not name or not isinstance(name, str):
        return ""

    raw = name.strip().strip("'\"`")
    if not raw:
        return ""

    # Strip synthetic number/modifier suffixes
    cleaned = SYNTHETIC_SUFFIX_REGEX.sub("", raw).strip()
    cleaned = re.sub(r"(?i)\s+Feature$", "", cleaned).strip()
    if not cleaned:
        cleaned = raw

    # Check synonym dictionary (case-insensitive)
    lower = cleaned.lower()
    if lower in SYNONYM_MAP:
        return SYNONYM_MAP[lower]

    # Also check without hyphens/spaces
    compact = re.sub(r"[\s\-_]+", " ", lower).strip()
    if compact in SYNONYM_MAP:
        return SYNONYM_MAP[compact]

    return cleaned


def canonicalize_extracted_entities(extracted_entities: dict) -> dict:
    """
    Takes an extracted_entities dictionary (with categories: algorithms, technologies,
    frameworks, libraries, datasets, applications, hardware, metrics) and:
    - Normalizes each entity name
    - Deduplicates case-insensitively within and across categories
    - Removes empty or trivial noise
    - Returns a clean dictionary with sorted lists
    """
    if not isinstance(extracted_entities, dict):
        return {}

    categories = [
        "algorithms", "technologies", "frameworks", "libraries",
        "datasets", "applications", "hardware", "metrics"
    ]

    result: Dict[str, List[str]] = {}
    globally_seen_keys: Set[str] = set()

    # Pre-populate non-category metadata (e.g., domain, sub_domain)
    for k, v in extracted_entities.items():
        if k not in categories and k != "all_extracted" and k != "unmatched_spans":
            result[k] = v

    for cat in categories:
        raw_list = extracted_entities.get(cat, [])
        if not isinstance(raw_list, list):
            continue

        cat_cleaned: List[str] = []
        cat_seen_keys: Set[str] = set()

        for item in raw_list:
            norm = normalize_entity_name(str(item))
            if not norm or len(norm) < 2:
                continue

            key = norm.casefold()
            # If already seen in this category, skip
            if key in cat_seen_keys:
                continue

            # If globally seen (e.g. RAG in both technologies and frameworks), skip duplicate
            if key in globally_seen_keys:
                continue

            cat_seen_keys.add(key)
            globally_seen_keys.add(key)
            cat_cleaned.append(norm)

        result[cat] = sorted(cat_cleaned)

    # Preserve unmatched_spans if present, but also filter out any that became recognized
    unmatched = extracted_entities.get("unmatched_spans", [])
    if isinstance(unmatched, list):
        clean_unmatched = []
        for span in unmatched:
            if not isinstance(span, str):
                continue
            norm = normalize_entity_name(span)
            if norm and norm.casefold() not in globally_seen_keys:
                clean_unmatched.append(span)
        result["unmatched_spans"] = clean_unmatched

    return result
