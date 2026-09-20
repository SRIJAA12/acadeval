"""
AcadEval Domain Taxonomy Search & Classification Engine
========================================================
Keyword, phrase-matching, and BM25 search over the taxonomy for domain classification.
Used by Module 4 (Domain Classification) and Module 5 (Similarity Detection).
"""

import re
from pathlib import Path

import pandas as pd

from taxonomy_loader import load_dataframe, get_all_keywords

# Optional: rank_bm25 for BM25 ranking (pip install rank_bm25)
try:
    # pyrefly: ignore [missing-import]
    from rank_bm25 import BM25Okapi
    _BM25_AVAILABLE = True
except ImportError:
    _BM25_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# KEYWORD & PHRASE SEARCH
# ─────────────────────────────────────────────────────────────────────────────

def search_by_keyword(query: str, top_k: int = 10) -> pd.DataFrame:
    """
    Keyword and phrase search across Common_Keywords, Related_Keywords,
    Technologies, Algorithms, and Description columns.
    Returns up to top_k matching rows sorted by match relevance score.
    """
    df = load_dataframe().copy()
    query_lower = query.lower().strip()
    query_tokens = {t for t in re.split(r"[\s,.\-/()\n]+", query_lower) if len(t) > 1}

    search_cols = [
        "Domain", "Sub_Domain", "Topic", "Description",
        "Common_Keywords", "Related_Keywords", "Technologies",
        "Algorithms", "Application_Areas",
    ]

    def score_row(row: pd.Series) -> int:
        text = " ".join(str(row.get(c, "")) for c in search_cols).lower()
        score = 0
        # Word overlap
        for token in query_tokens:
            if token in text:
                score += 1
        # Exact phrase match bonus
        if query_lower in text:
            score += 5
        return score

    df["_score"] = df.apply(score_row, axis=1)
    result = df[df["_score"] > 0].copy()
    if result.empty:
        return pd.DataFrame(columns=df.columns[:-1])
    return result.sort_values("_score", ascending=False).drop(columns="_score").head(top_k)


def classify_domain(text: str) -> dict:
    """
    Given a project title or abstract, return the most likely domain,
    sub-domain, confidence score, and top matching topics using phrase-aware indexing.

    Returns:
        {
            "domain": str,
            "sub_domain": str,
            "score": int,
            "top_topics": list[str],
            "all_domain_scores": dict[str, int]
        }
    """
    text_lower = text.lower()
    tokens = {t for t in re.split(r"[\s,.\-/()\n]+", text_lower) if len(t) > 2}
    domain_keywords = get_all_keywords()

    domain_scores: dict[str, int] = {}
    for domain, kws in domain_keywords.items():
        score = 0
        for kw in kws:
            kw_clean = kw.strip().lower()
            if not kw_clean:
                continue
            if " " in kw_clean:
                if kw_clean in text_lower:
                    score += 3  # Higher weight for multi-word phrase matches
            else:
                if kw_clean in tokens:
                    score += 1
        domain_scores[domain] = score

    best_domain = max(domain_scores, key=domain_scores.get) if domain_scores and max(domain_scores.values()) > 0 else "Unknown"
    best_score  = domain_scores.get(best_domain, 0)

    df = load_dataframe()
    domain_df = df[df["Domain"] == best_domain] if best_domain != "Unknown" else df

    # Top sub-domain & topics within domain
    sub_scores: dict[str, int] = {}
    topic_scores: dict[str, int] = {}

    for _, row in domain_df.iterrows():
        sub = row["Sub_Domain"]
        topic = row["Topic"]
        cell_text = (
            f"{row.get('Topic', '')} {row.get('Common_Keywords', '')} "
            f"{row.get('Related_Keywords', '')} {row.get('Technologies', '')} "
            f"{row.get('Algorithms', '')}"
        ).lower()

        cell_tokens = {t for t in re.split(r"[\s,.\-/()\n]+", cell_text) if len(t) > 2}
        row_score = len(tokens & cell_tokens)

        # Bonus for phrase matches in row
        for phrase in cell_text.split(","):
            phrase_clean = phrase.strip()
            if phrase_clean and " " in phrase_clean and phrase_clean in text_lower:
                row_score += 3

        sub_scores[sub] = sub_scores.get(sub, 0) + row_score
        topic_scores[topic] = topic_scores.get(topic, 0) + row_score

    best_sub = max(sub_scores, key=sub_scores.get) if sub_scores else ""
    top_topics = sorted(topic_scores, key=topic_scores.get, reverse=True)[:3]

    return {
        "domain": best_domain,
        "sub_domain": best_sub,
        "score": best_score,
        "top_topics": top_topics,
        "all_domain_scores": dict(sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)[:5]),
    }


# ─────────────────────────────────────────────────────────────────────────────
# BM25 SEARCH
# ─────────────────────────────────────────────────────────────────────────────

def build_bm25_corpus(df: pd.DataFrame) -> tuple:
    """Build a BM25 corpus from taxonomy rows."""
    if not _BM25_AVAILABLE:
        raise ImportError("Install rank_bm25: pip install rank-bm25")
    corpus_texts = []
    for _, row in df.iterrows():
        text = " ".join([
            str(row.get("Topic", "")),
            str(row.get("Description", "")),
            str(row.get("Common_Keywords", "")),
            str(row.get("Related_Keywords", "")),
            str(row.get("Technologies", "")),
        ])
        corpus_texts.append([t for t in re.split(r"\W+", text.lower()) if t])
    bm25 = BM25Okapi(corpus_texts)
    return bm25, corpus_texts


def bm25_search(query: str, top_k: int = 10) -> pd.DataFrame:
    """BM25-based search over taxonomy (requires rank_bm25)."""
    df = load_dataframe().copy()
    bm25, _ = build_bm25_corpus(df)
    tokens = [t for t in re.split(r"\W+", query.lower()) if t]
    scores = bm25.get_scores(tokens)
    top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    result = df.iloc[top_idx].copy()
    result["_bm25_score"] = [scores[i] for i in top_idx]
    return result.sort_values("_bm25_score", ascending=False)


# ─────────────────────────────────────────────────────────────────────────────
# CLI TEST
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "deep learning segmentation for brain MRI scans"
    print(f"\n=== Keyword Search: '{query}' ===")
    results = search_by_keyword(query, top_k=5)
    if results.empty:
        print("No results found.")
    else:
        print(results[["Taxonomy_ID", "Domain", "Sub_Domain", "Topic"]].to_string(index=False))

    print(f"\n=== Domain Classification: '{query}' ===")
    classification = classify_domain(query)
    print(f"  Domain     : {classification['domain']}")
    print(f"  Sub-domain : {classification['sub_domain']}")
    print(f"  Score      : {classification['score']}")
    print(f"  Top Topics : {classification['top_topics']}")
    print(f"  Top scores : {classification['all_domain_scores']}")
