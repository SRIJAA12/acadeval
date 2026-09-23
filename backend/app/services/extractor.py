"""
Module 3 — Entity / Feature Extraction Service
================================================
Extracts structured entities (algorithms, technologies, frameworks, datasets,
hardware, applications, metrics) from free-text project proposals using
spaCy EntityRuler patterns seeded directly from AcadEval_FeatureKnowledgeBase.

Pipeline (per Section 7, Step 1-7):
  1. spaCy EntityRuler  — exact/alias match from FeatureKnowledgeBase (fast, free)
  2. Regex fallback     — case-insensitive scan of the same KB (catches casing variants)
  3. BERT similarity    — sentence-transformers embed & cosine compare for near-misses
                          (cheap first pass before LLM; skips LLM if similarity >= 0.75)
  4. Gemini LLM verify  — maps remaining unknowns to existing entries OR flags as new
  5. pending_review.json — queues genuinely new terms for faculty approval
"""

import json
import logging
import re
import sys
from pathlib import Path

from app.services.llm_client import call_gemini_json
from app.services.entity_normalizer import canonicalize_extracted_entities

# Robustly find feature_kb directory in Docker (/datasets/feature_kb) or local host
_possible_kb_dirs = [
    Path("/datasets/feature_kb"),
    Path(__file__).resolve().parents[3] / "datasets" / "feature_kb",
    Path(__file__).resolve().parents[2] / "datasets" / "feature_kb",
]
FEATURE_KB_DIR = next((p for p in _possible_kb_dirs if p.exists()), _possible_kb_dirs[0])
if str(FEATURE_KB_DIR) not in sys.path:
    sys.path.insert(0, str(FEATURE_KB_DIR))

try:
    from feature_kb_loader import load_feature_list, get_spacy_entity_ruler_patterns
except ImportError:
    load_feature_list = None
    get_spacy_entity_ruler_patterns = None

PENDING_REVIEW_PATH = FEATURE_KB_DIR / "pending_review.json"
KNOWN_CATEGORY_LABELS = {"algorithm", "technology", "framework", "library", "dataset", "application", "hardware", "metric"}
MAX_LLM_VERIFICATIONS_PER_CALL = 5
BERT_SIMILARITY_THRESHOLD = 0.75  # cosine score above which we trust BERT match and skip LLM

# Optional BERT / sentence-transformers for the similarity pass (Step 4)
try:
    from sentence_transformers import SentenceTransformer, util as st_util
    _SBERT_AVAILABLE = True
except ImportError:
    _SBERT_AVAILABLE = False

log = logging.getLogger(__name__)

# spaCy integration
try:
    import spacy
    from spacy.pipeline import EntityRuler
    _SPACY_AVAILABLE = True
except ImportError:
    _SPACY_AVAILABLE = False


class FeatureExtractorService:
    def __init__(self):
        self.nlp = None
        self._sbert_model = None          # loaded lazily for BERT similarity pass
        self._kb_embeddings = None        # cached FeatureKB embeddings (numpy array)
        self._kb_names: list[str] = []    # parallel list of KB names for lookup
        self._initialized = False

    def _lazy_init(self):
        if self._initialized:
            return

        if _SPACY_AVAILABLE:
            try:
                # Load blank or small English spacy model
                try:
                    self.nlp = spacy.load("en_core_web_sm")
                except Exception:
                    self.nlp = spacy.blank("en")

                if get_spacy_entity_ruler_patterns:
                    patterns = get_spacy_entity_ruler_patterns()
                    ruler = self.nlp.add_pipe("entity_ruler", before="ner" if "ner" in self.nlp.pipe_names else None)
                    ruler.add_patterns(patterns)
                    log.info("Initialized spaCy EntityRuler with %d patterns for Module 3.", len(patterns))
            except Exception as e:
                log.warning("Failed to initialize spaCy EntityRuler (%s). Using regex extractor fallback.", e)
                self.nlp = None

        # SBERT is loaded lazily on demand for unmatched spans (avoids blocking startup)
        self._initialized = True

    def extract_from_full_proposal(self, title: str, abstract: str, body: str = "") -> dict:
        """
        Convenience wrapper for full-proposal extraction (Module 1 output).
        Concatenates title + abstract + optional body text and runs extract_entities.
        This is the method called by the /submit pipeline.
        """
        full_text = "\n".join(filter(None, [title, abstract, body])).strip()
        return self.extract_entities(full_text)

    def extract_entities(self, text: str) -> dict:
        """
        Full Module 3 extraction pipeline (Steps 1-5 from the spec).
        Returns:
          {
            "algorithms": list[str],
            "technologies": list[str],
            "frameworks": list[str],
            "libraries": list[str],
            "datasets": list[str],
            "applications": list[str],
            "hardware": list[str],
            "metrics": list[str],
            "unmatched_spans": list[str],
            "all_extracted": list[dict]
          }
        """
        self._lazy_init()
        extracted_by_cat = {
            "algorithms": set(),
            "technologies": set(),
            "frameworks": set(),
            "libraries": set(),
            "datasets": set(),
            "applications": set(),
            "hardware": set(),
            "metrics": set(),        # Step 7 — metrics[] field for Module 4
        }
        all_extracted = []
        unmatched_candidates = []

        if self.nlp is not None:
            doc = self.nlp(text)
            for ent in doc.ents:
                label_lower = ent.label_.lower()
                cat_key = f"{label_lower}s" if not label_lower.endswith("s") else label_lower
                if label_lower == "algorithm":
                    extracted_by_cat["algorithms"].add(ent.text)
                elif label_lower == "technology":
                    extracted_by_cat["technologies"].add(ent.text)
                elif label_lower == "framework":
                    extracted_by_cat["frameworks"].add(ent.text)
                elif label_lower == "library":
                    extracted_by_cat["libraries"].add(ent.text)
                elif label_lower == "dataset":
                    extracted_by_cat["datasets"].add(ent.text)
                elif label_lower == "application":
                    extracted_by_cat["applications"].add(ent.text)
                elif label_lower == "hardware":
                    extracted_by_cat["hardware"].add(ent.text)
                elif label_lower == "metric":
                    extracted_by_cat["metrics"].add(ent.text)
                elif label_lower not in KNOWN_CATEGORY_LABELS:
                    # Generic NER label (ORG, PRODUCT, GPE, ...) the EntityRuler
                    # didn't claim — candidate for BERT then LLM verification.
                    unmatched_candidates.append(ent.text)

                all_extracted.append({
                    "text": ent.text,
                    "category": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char
                })

        # ── Step 2: Regex fallback / augmentation against FeatureKB list ──────────
        if load_feature_list:
            feats = load_feature_list()
            text_lower = text.lower()
            for feat in feats:
                name = feat["name"]
                name_l = name.lower()
                cat = feat["category"].lower()
                cat_key = f"{cat}s" if not cat.endswith("s") else cat

                # Fast substring pre-check before regex boundary search
                matched = False
                if name_l in text_lower and re.search(r'\b' + re.escape(name_l) + r'\b', text_lower):
                    matched = True
                else:
                    for alias in feat.get("aliases", []):
                        if alias:
                            alias_l = alias.lower()
                            if alias_l in text_lower and re.search(r'\b' + re.escape(alias_l) + r'\b', text_lower):
                                matched = True
                                break

                if matched and cat_key in extracted_by_cat:
                    extracted_by_cat[cat_key].add(name)

        # ── Step 2b: Dedicated Dataset & Benchmark Discovery ─────────────────────
        dataset_patterns = [
            r"\b(AcadEval[_\s]*(?:Corpus(?:_MASTER)?|Historical[_\s]*Corpus|Master[_\s]*Corpus|Domain[_\s]*Taxonomy|Feature[_\s]*Knowledge[_\s]*Base|SimBench|Trend[_\s]*Base))\b",
            r"\b(Historical[_\s]+Corpus)\b",
            r"\b(Domain[_\s]+Taxonomy)\b",
            r"\b(Feature[_\s]+Knowledge[_\s]*Base)\b",
            r"\b(SimBench(?:[_\s]+Benchmark)?)\b",
            r"\b(Trend[_\s]*Base)\b",
            r"\b([A-Z][a-zA-Z0-9_\-]+(?:\s+[A-Z][a-zA-Z0-9_\-]+)*\s+(?:Dataset|Corpus|Benchmark|Knowledge[_\s]+Base|Data[_\s]+Bank))\b",
        ]
        for pat in dataset_patterns:
            for match in re.finditer(pat, text, flags=re.IGNORECASE):
                cand = re.sub(r"\s+", " ", match.group(1)).strip()
                if len(cand) >= 4 and not re.search(r"\b(Project|Section|Module|System|Architecture|Evaluation)\b", cand, re.I):
                    extracted_by_cat["datasets"].add(cand)

        # De-dup unmatched candidates and drop any that a known feature already covers
        known_names_lower = {n.lower() for cat in extracted_by_cat.values() for n in cat}
        seen = set()
        deduped_unmatched = []
        for span in unmatched_candidates:
            key = span.lower().strip()
            if key and key not in seen and key not in known_names_lower:
                seen.add(key)
                deduped_unmatched.append(span)

        # ── Step 3: BERT similarity pass (cheap, no API cost) ────────────────────
        after_bert, bert_rescued = self._bert_similarity_pass(deduped_unmatched, extracted_by_cat)
        if bert_rescued:
            log.info("BERT similarity pass resolved %d span(s); %d remain for LLM.", bert_rescued, len(after_bert))

        # ── Step 4: LLM verification for spans still unresolved after BERT ───────
        still_unmatched = self._verify_unmatched_spans(after_bert, extracted_by_cat)

        raw_result = {
            "algorithms": sorted(list(extracted_by_cat["algorithms"])),
            "technologies": sorted(list(extracted_by_cat["technologies"])),
            "frameworks": sorted(list(extracted_by_cat["frameworks"])),
            "libraries": sorted(list(extracted_by_cat["libraries"])),
            "datasets": sorted(list(extracted_by_cat["datasets"])),
            "applications": sorted(list(extracted_by_cat["applications"])),
            "hardware": sorted(list(extracted_by_cat["hardware"])),
            "metrics": sorted(list(extracted_by_cat["metrics"])),  # Step 7 output
            "unmatched_spans": still_unmatched,
            "all_extracted": all_extracted
        }
        cleaned_result = canonicalize_extracted_entities(raw_result)
        cleaned_result["all_extracted"] = all_extracted
        return cleaned_result

    def _bert_similarity_pass(self, spans: list[str], extracted_by_cat: dict) -> tuple[list[str], int]:
        """
        Step 3 (BERT similarity check): embeds each unmatched span and compares
        to the pre-computed FeatureKnowledgeBase embeddings. Spans with a best
        cosine similarity >= BERT_SIMILARITY_THRESHOLD are mapped to the closest
        KB entry without making an LLM call. Returns (still_unmatched, resolved_count).
        """
        if not spans or self._sbert_model is None or self._kb_embeddings is None:
            return spans, 0

        try:
            span_embeddings = self._sbert_model.encode(spans, convert_to_tensor=True)
            scores = st_util.cos_sim(span_embeddings, self._kb_embeddings)  # shape: [n_spans, n_kb]
        except Exception as e:
            log.warning("BERT similarity pass failed (%s); skipping to LLM.", e)
            return spans, 0

        still_unmatched = []
        resolved = 0
        if load_feature_list:
            feats = load_feature_list()
        else:
            return spans, 0

        for i, span in enumerate(spans):
            best_idx = int(scores[i].argmax())
            best_score = float(scores[i][best_idx])
            if best_score >= BERT_SIMILARITY_THRESHOLD:
                feat = feats[best_idx]
                cat = feat["category"].lower()
                cat_key = f"{cat}s" if not cat.endswith("s") else cat
                if cat_key in extracted_by_cat:
                    extracted_by_cat[cat_key].add(feat["name"])
                    resolved += 1
                    log.debug("BERT mapped %r → %r (%.3f similarity)", span, feat["name"], best_score)
                else:
                    still_unmatched.append(span)
            else:
                still_unmatched.append(span)

        return still_unmatched, resolved

    def _verify_unmatched_spans(self, spans: list[str], extracted_by_cat: dict) -> list[str]:
        """
        Module 3's "send to LLM, map-or-confirm-new" pass (Section 7, step 5).
        Spans Gemini maps to an existing FeatureKnowledgeBase entry get folded
        into `extracted_by_cat`; spans confirmed as genuinely new are appended
        to `pending_review.json` for manual curation and returned as still-unmatched.
        """
        if not spans or not load_feature_list:
            return spans

        known_names = [f["name"] for f in load_feature_list()]
        still_unmatched = []

        for span in spans[:MAX_LLM_VERIFICATIONS_PER_CALL]:
            prompt = f"""A project-proposal parser found the phrase "{span}" but it isn't in our known
feature vocabulary. Known feature names include: {", ".join(known_names[:150])}

Does "{span}" refer to one of these existing features (a spelling/naming variant), or is it a
genuinely new algorithm/technology/framework/library/dataset/application/hardware term?
Respond with a single JSON object only:
{{"is_new": true or false, "category": "Algorithm|Technology|Framework|Library|Dataset|Application|Hardware", "matched_name": "<existing name if not new, else null>"}}
"""
            result = call_gemini_json(prompt)
            if not result:
                still_unmatched.append(span)
                continue

            category = str(result.get("category", "")).strip().lower()
            cat_key = f"{category}s" if not category.endswith("s") else category

            if not result.get("is_new") and result.get("matched_name") and cat_key in extracted_by_cat:
                extracted_by_cat[cat_key].add(result["matched_name"])
            elif result.get("is_new"):
                self._queue_pending_review(span, category or "unknown")
                still_unmatched.append(span)
            else:
                still_unmatched.append(span)

        # Anything beyond the per-call cap is left unverified rather than dropped silently
        still_unmatched.extend(spans[MAX_LLM_VERIFICATIONS_PER_CALL:])
        return still_unmatched

    @staticmethod
    def _queue_pending_review(span: str, category: str):
        try:
            queue = []
            if PENDING_REVIEW_PATH.exists():
                queue = json.loads(PENDING_REVIEW_PATH.read_text(encoding="utf-8"))
            if not any(item["name"].lower() == span.lower() for item in queue):
                queue.append({"name": span, "category": category})
                PENDING_REVIEW_PATH.write_text(json.dumps(queue, indent=2), encoding="utf-8")
        except Exception as e:
            log.warning("Failed to queue pending-review candidate %r (%s)", span, e)


# Singleton instance
extractor_service = FeatureExtractorService()
