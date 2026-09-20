"""
Module 1 — Domain & Sub-domain Classification Service
======================================================
Assigns incoming project proposal text (title + abstract) to a domain
and sub-domain using AcadEval_DomainTaxonomy embeddings and LLM tie-breaker.
"""

import logging
import re
import sys
from pathlib import Path

# Add datasets taxonomy directory to path for taxonomy_loader / taxonomy_search imports
TAXONOMY_DIR = Path(__file__).resolve().parents[3] / "datasets" / "taxonomy"
if str(TAXONOMY_DIR) not in sys.path:
    sys.path.insert(0, str(TAXONOMY_DIR))

try:
    from taxonomy_loader import load_dataframe
    from taxonomy_search import classify_domain as phrase_classify_domain
except ImportError:
    # Fallback if path resolution differs
    load_dataframe = None
    phrase_classify_domain = None

from app.services.llm_client import call_gemini_json

log = logging.getLogger(__name__)

# Optional Sentence-Transformers integration
try:
    from sentence_transformers import SentenceTransformer, util
    _ST_AVAILABLE = True
except ImportError:
    _ST_AVAILABLE = False


class DomainClassifierService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self.taxonomy_df = None
        self.node_embeddings = None
        self.node_labels = []
        self._initialized = False

    def _lazy_init(self):
        if self._initialized:
            return
        
        if load_dataframe:
            self.taxonomy_df = load_dataframe()

        if _ST_AVAILABLE:
            try:
                log.info("Loading SentenceTransformer model '%s' for Module 1...", self.model_name)
                self.model = SentenceTransformer(self.model_name)
                if self.taxonomy_df is not None:
                    # Pre-compute embeddings for all taxonomy topics
                    texts = [
                        f"{row['Domain']} {row['Sub_Domain']} {row['Topic']}: {row['Description']} {row['Common_Keywords']}"
                        for _, row in self.taxonomy_df.iterrows()
                    ]
                    self.node_labels = [
                        (row["Domain"], row["Sub_Domain"], row["Topic"])
                        for _, row in self.taxonomy_df.iterrows()
                    ]
                    self.node_embeddings = self.model.encode(texts, convert_to_tensor=True)
                    log.info("Embedded %d taxonomy nodes for Module 1.", len(texts))
            except Exception as e:
                log.warning("Failed to initialize SentenceTransformer (%s). Falling back to phrase classifier.", e)
                self.model = None

        self._initialized = True

    def classify_project(self, title: str, abstract: str) -> dict:
        """
        Classifies a project title + abstract into a domain and sub-domain.
        Returns:
          {
            "domain": str,
            "sub_domain": str,
            "topic": str,
            "confidence_score": float,
            "is_ambiguous": bool,
            "top_candidates": list[dict]
          }
        """
        self._lazy_init()
        full_text = f"{title}\n{abstract}".strip()

        if self.model is not None and self.node_embeddings is not None:
            # Embedding nearest-neighbor lookup
            project_emb = self.model.encode(full_text, convert_to_tensor=True)
            cosine_scores = util.cos_sim(project_emb, self.node_embeddings)[0]
            
            top_results = cosine_scores.topk(k=min(5, len(self.node_labels)))
            candidates = []
            for score, idx in zip(top_results.values, top_results.indices):
                score_val = float(score)
                domain, sub_domain, topic = self.node_labels[int(idx)]
                candidates.append({
                    "domain": domain,
                    "sub_domain": sub_domain,
                    "topic": topic,
                    "score": round(score_val, 4)
                })

            top1 = candidates[0]
            top2 = candidates[1] if len(candidates) > 1 else None
            
            is_ambiguous = False
            if top2 and (top1["score"] - top2["score"]) < 0.05:
                is_ambiguous = True
                # Run LLM tie-breaker if ambiguous
                tie_break = self._llm_tie_breaker(full_text, top1, top2)
                if tie_break:
                    top1["domain"] = tie_break.get("domain", top1["domain"])
                    top1["sub_domain"] = tie_break.get("sub_domain", top1["sub_domain"])

            matched_keywords = self._extract_matched_keywords(
                full_text, top1["domain"], top1["sub_domain"], top1["topic"]
            )

            return {
                "domain": top1["domain"],
                "sub_domain": top1["sub_domain"],
                "topic": top1["topic"],
                "confidence_score": top1["score"],
                "is_ambiguous": is_ambiguous,
                "matched_keywords": matched_keywords,
                "top_candidates": candidates
            }

        # Fallback to phrase & keyword match if SentenceTransformer is not loaded
        if phrase_classify_domain:
            res = phrase_classify_domain(full_text)
            matched_keywords = self._extract_matched_keywords(
                full_text, res["domain"], res["sub_domain"], res["top_topics"][0] if res.get("top_topics") else ""
            )
            return {
                "domain": res["domain"],
                "sub_domain": res["sub_domain"],
                "topic": res["top_topics"][0] if res["top_topics"] else "",
                "confidence_score": round(min(1.0, float(res["score"]) / 10.0), 2),
                "is_ambiguous": False,
                "matched_keywords": matched_keywords,
                "top_candidates": []
            }

        matched_keywords = self._extract_matched_keywords(full_text, "Artificial Intelligence", "Machine Learning", "General Machine Learning")
        return {
            "domain": "Artificial Intelligence",
            "sub_domain": "Machine Learning",
            "topic": "General Machine Learning",
            "confidence_score": 0.5,
            "is_ambiguous": False,
            "matched_keywords": matched_keywords,
            "top_candidates": []
        }

    def _extract_matched_keywords(self, full_text: str, domain: str, sub_domain: str, topic: str) -> list[str]:
        """Extracts keyword evidence present in both proposal text and the taxonomy."""
        text_lower = full_text.lower()
        matched: list[str] = []
        if self.taxonomy_df is not None and not self.taxonomy_df.empty:
            matches = self.taxonomy_df[
                (self.taxonomy_df["Domain"] == domain) &
                (self.taxonomy_df["Sub_Domain"] == sub_domain)
            ]
            if not matches.empty:
                row = matches.iloc[0]
                kw_str = f"{row.get('Common_Keywords', '')} {row.get('Technologies', '')} {row.get('Algorithms', '')}"
                candidate_kws = [k.strip() for k in re.split(r"[,;|\n]+", kw_str) if len(k.strip()) > 2]
                for kw in candidate_kws:
                    if kw.lower() in text_lower and kw not in matched:
                        matched.append(kw)

        if not matched:
            for word in f"{domain} {sub_domain} {topic}".split():
                clean_w = re.sub(r"[^\w]", "", word)
                if len(clean_w) > 3 and clean_w.lower() in text_lower and clean_w not in matched:
                    matched.append(clean_w)
        return matched[:10]

    def _llm_tie_breaker(self, project_text: str, candidate_a: dict, candidate_b: dict) -> dict | None:
        """
        LLM tie-breaker prompt for ambiguous classifications (|score_a - score_b| < 0.05).
        Falls back to Candidate A (the higher-cosine-score match) if Gemini is
        unavailable or fails to return a usable answer.
        """
        log.info("Module 1 LLM Tie-Breaker triggered between Candidate A (%s) and Candidate B (%s)",
                 candidate_a["domain"], candidate_b["domain"])

        prompt = f"""You are classifying an academic capstone project proposal into a domain taxonomy.

Project title + abstract:
\"\"\"{project_text}\"\"\"

Two taxonomy entries are nearly tied as the best match:
Candidate A: domain="{candidate_a['domain']}", sub_domain="{candidate_a['sub_domain']}", topic="{candidate_a['topic']}"
Candidate B: domain="{candidate_b['domain']}", sub_domain="{candidate_b['sub_domain']}", topic="{candidate_b['topic']}"

Which candidate better matches the project? Respond with a single JSON object only:
{{"choice": "A" or "B", "domain": "<chosen domain>", "sub_domain": "<chosen sub_domain>"}}
"""
        result = call_gemini_json(prompt)
        if result and result.get("choice") in ("A", "B"):
            chosen = candidate_a if result["choice"] == "A" else candidate_b
            return {
                "domain": result.get("domain") or chosen["domain"],
                "sub_domain": result.get("sub_domain") or chosen["sub_domain"],
            }
        return candidate_a


# Singleton instance
classifier_service = DomainClassifierService()
