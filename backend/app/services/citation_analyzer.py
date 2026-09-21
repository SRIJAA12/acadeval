"""
Module 6 — Citation & Reference Analysis Service
==================================================
Extracts, parses, cross-verifies, and scores bibliography references from
capstone project proposals.

Workflow:
  1. PDF Documents  → GROBID TEI XML parser (http://localhost:8070/api/processReferences)
  2. Plain text/DOC → Fallback Regex & AnyStyle-compatible heuristic parser
  3. Verification    → Cross-check with Semantic Scholar API (ss_client)
  4. Sub-scores      → reference_count, percent_verified, avg_reference_age, percent_recent
  5. Explainability  → Detailed per-reference verification trace & flags
"""

import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

import requests

from app.config import settings
from app.services.semantic_scholar import ss_client

log = logging.getLogger(__name__)

# TEI XML namespace for GROBID parser
TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}
CITATION_METHOD_VERSION = "citation-verification-v2.0"


class ReferenceParserService:
    """Handles GROBID TEI XML parsing and heuristic text extraction."""

    @staticmethod
    def parse_tei_xml(xml_content: str) -> List[Dict[str, Any]]:
        """Parses GROBID TEI XML output into structured reference dicts."""
        references = []
        try:
            root = ET.fromstring(xml_content)
            # Find all biblStruct elements
            for bibl in root.findall(".//tei:biblStruct", TEI_NS):
                title_elem = bibl.find(".//tei:analytic/tei:title", TEI_NS)
                if title_elem is None:
                    title_elem = bibl.find(".//tei:monogr/tei:title", TEI_NS)

                title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""

                # Extract authors
                authors = []
                for author_elem in bibl.findall(".//tei:author", TEI_NS):
                    pers_name = author_elem.find("tei:persName", TEI_NS)
                    if pers_name is not None:
                        forename = pers_name.findtext("tei:forename", "", TEI_NS)
                        surname = pers_name.findtext("tei:surname", "", TEI_NS)
                        full = f"{forename} {surname}".strip()
                        if full:
                            authors.append(full)

                # Extract year
                year = None
                date_elem = bibl.find(".//tei:date[@type='published']", TEI_NS)
                if date_elem is not None:
                    when = date_elem.attrib.get("when", "")
                    match = re.search(r"\b(19\d\d|20\d\d)\b", when or date_elem.text or "")
                    if match:
                        year = int(match.group(1))

                # Extract venue / journal / booktitle
                journal_elem = bibl.find(".//tei:monogr/tei:title", TEI_NS)
                venue = journal_elem.text.strip() if journal_elem is not None and journal_elem.text else ""

                if title or authors:
                    references.append({
                        "raw_title": title,
                        "authors": authors,
                        "year": year,
                        "venue": venue,
                        "source": "grobid"
                    })
        except Exception as exc:
            log.warning("GROBID TEI XML parsing error: %s", exc)

        return references

    @staticmethod
    def fallback_parse_text(text: str) -> List[Dict[str, Any]]:
        """
        Fallback parser for non-PDF files or unstructured text.
        Extracts reference lines using bibliography heuristics and regex matching.
        """
        references = []
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        # Locate References section
        ref_section_started = False
        ref_lines = []

        for line in lines:
            if not ref_section_started:
                if re.search(r"\b(references|bibliography|works cited)\b", line.lower()):
                    ref_section_started = True
                continue
            ref_lines.append(line)

        # If no explicit header found, look for numbered citations e.g., [1] Author, Title...
        target_lines = ref_lines if ref_lines else lines

        for line in target_lines:
            # Match patterns like: [1] J. Doe et al., "Paper Title", 2023.
            clean_line = re.sub(r"^\[\d+\]\s*", "", line)
            clean_line = re.sub(r"^\d+\.\s*", "", clean_line)

            year_match = re.search(r"\b(19\d\d|20\d\d)\b", clean_line)
            year = int(year_match.group(1)) if year_match else None

            # Simple heuristic split: Title inside quotes or long sentence
            title_match = re.search(r'["“](.*?)["”]', clean_line)
            title = title_match.group(1) if title_match else clean_line[:120]

            if len(clean_line) > 20 and (year or title_match):
                references.append({
                    "raw_title": title.strip(),
                    "authors": [],
                    "year": year,
                    "venue": "",
                    "source": "anystyle_fallback"
                })

        return references[:50]  # Cap at 50 references for evaluation safety


class CitationAnalysisService:
    """Main Citation & Reference Analysis Engine (Module 6)."""

    def process_pdf_grobid(self, pdf_path: str | Path) -> List[Dict[str, Any]]:
        """Posts PDF file to GROBID service to extract TEI XML references."""
        p = Path(pdf_path)
        if not p.exists():
            return []

        grobid_url = f"{settings.GROBID_URL.rstrip('/')}/api/processReferences"
        try:
            with open(p, "rb") as f:
                resp = requests.post(grobid_url, files={"input": f}, timeout=12.0)
            if resp.status_code == 200:
                return ReferenceParserService.parse_tei_xml(resp.text)
            log.warning("GROBID returned status HTTP %d", resp.status_code)
        except Exception as exc:
            log.warning("GROBID connection failed (%s) — using fallback parser", exc)

        return []

    def analyze_references(
        self,
        file_path: Optional[str | Path] = None,
        raw_text: str = ""
    ) -> Dict[str, Any]:
        """
        Main entry point for Module 6.
        Parses references, cross-checks against Semantic Scholar, and computes sub-scores.
        """
        raw_refs: List[Dict[str, Any]] = []

        # Step 1: Try GROBID if PDF provided
        if file_path and str(file_path).lower().endswith(".pdf"):
            raw_refs = self.process_pdf_grobid(file_path)

        # Step 2: Fallback to text parsing if GROBID returns nothing or non-PDF
        if not raw_refs and raw_text:
            raw_refs = ReferenceParserService.fallback_parse_text(raw_text)

        if not raw_refs:
            return self._empty_response("No structured references detected in proposal.")

        # Step 3: Cross-check against Semantic Scholar API
        verified_count = 0
        years: List[int] = []
        verified_details: List[Dict[str, Any]] = []

        current_year = datetime.now(timezone.utc).year
        recent_count = 0

        for ref in raw_refs:
            query = ref.get("raw_title", "")
            if not query or len(query) < 8:
                continue

            ss_match = None
            try:
                papers = ss_client.search_papers(query, limit=1)
                if papers:
                    ss_match = papers[0]
            except Exception as exc:
                log.warning("SS paper lookup failed for %r: %s", query[:30], exc)

            is_verified = bool(ss_match)
            pub_year = ss_match.get("year") if ss_match else ref.get("year")
            cit_count = ss_match.get("citationCount", 0) if ss_match else 0

            if is_verified:
                verified_count += 1

            if pub_year:
                years.append(pub_year)
                if current_year - pub_year <= 5:
                    recent_count += 1

            verified_details.append({
                "title": ss_match.get("title") if ss_match else ref.get("raw_title"),
                "authors": ref.get("authors", []),
                "year": pub_year,
                "venue": ref.get("venue"),
                "is_verified": is_verified,
                "citation_count": cit_count,
                "semantic_scholar_url": ss_match.get("url") if ss_match else None,
                "source": ref.get("source"),
            })

        # Step 4: Compute sub-scores
        total_refs = len(verified_details)
        if total_refs == 0:
            return self._empty_response("No valid citations could be parsed.")

        percent_verified = round((verified_count / total_refs) * 100.0, 1)
        avg_age = round(sum(current_year - y for y in years) / len(years), 1) if years else 0.0
        percent_recent = round((recent_count / len(years)) * 100.0, 1) if years else 0.0

        # Sub-score summary object for Module 9 / EvaluationReport
        summary_scores = {
            "reference_count": total_refs,
            "percent_verified": percent_verified,
            "average_reference_age": avg_age,
            "percent_recent": percent_recent,
            "verified_count": verified_count,
            "recent_count": recent_count,
        }

        # Quality flag heuristics
        flags = []
        if total_refs < 5:
            flags.append("Low Citation Volume: Fewer than 5 references cited.")
        if percent_verified < 40.0:
            flags.append("Low Verifiability: Less than 40% of references found on Semantic Scholar.")
        if percent_recent < 30.0:
            flags.append("Outdated Bibliography: Less than 30% of references are from the last 5 years.")

        return {
            "method_version": CITATION_METHOD_VERSION,
            "summary": summary_scores,
            "flags": flags,
            "references": verified_details,
            "status": "success",
            "scope_note": "Verifiability and recency are measured; citation style compliance is not inferred.",
        }

    @staticmethod
    def _empty_response(reason: str) -> Dict[str, Any]:
        return {
            "method_version": CITATION_METHOD_VERSION,
            "summary": {
                "reference_count": 0,
                "percent_verified": 0.0,
                "average_reference_age": 0.0,
                "percent_recent": 0.0,
                "verified_count": 0,
                "recent_count": 0,
            },
            "flags": [reason],
            "references": [],
            "status": "no_data",
            "scope_note": "No citation-style score is produced without structured references.",
        }


# Singleton instance
citation_analysis_service = CitationAnalysisService()
