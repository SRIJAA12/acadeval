"""Deterministic writing-quality analysis with inspectable measurements."""

from __future__ import annotations

import re
from typing import Any


WRITING_METHOD_VERSION = "writing-rules-v2.0"
WORD_RE = re.compile(r"\b[A-Za-z][A-Za-z'-]*\b")
PASSIVE_RE = re.compile(
    r"\b(?:am|is|are|was|were|be|been|being)\s+(?:\w+ly\s+)?\w+(?:ed|en)\b",
    re.IGNORECASE,
)


def _syllables(word: str) -> int:
    value = re.sub(r"[^a-z]", "", word.casefold())
    if not value:
        return 0
    groups = re.findall(r"[aeiouy]+", value)
    count = len(groups)
    if value.endswith("e") and not value.endswith(("le", "ye")) and count > 1:
        count -= 1
    return max(1, count)


def _clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 1)


class WritingQualityService:
    def analyze_text(self, text: str) -> dict[str, Any]:
        clean_text = (text or "").strip()
        words = WORD_RE.findall(clean_text)
        if len(words) < 30:
            return self._empty_response("Text sample is too short for a reliable writing analysis.")

        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", clean_text) if part.strip()]
        sentence_count = max(1, len(sentences))
        syllable_count = sum(_syllables(word) for word in words)
        complex_words = sum(_syllables(word) >= 3 for word in words)
        passive_count = len(PASSIVE_RE.findall(clean_text))
        long_sentences = sum(len(WORD_RE.findall(sentence)) > 30 for sentence in sentences)

        words_per_sentence = len(words) / sentence_count
        syllables_per_word = syllable_count / len(words)
        flesch = 206.835 - 1.015 * words_per_sentence - 84.6 * syllables_per_word
        fog = 0.4 * (words_per_sentence + 100.0 * complex_words / len(words))
        passive_percent = passive_count / sentence_count * 100.0
        long_sentence_percent = long_sentences / sentence_count * 100.0

        readability_component = _clamp(100.0 - abs(55.0 - flesch) * 1.25)
        sentence_component = _clamp(100.0 - max(0.0, words_per_sentence - 22.0) * 4.0)
        active_voice_component = _clamp(100.0 - passive_percent * 2.5)
        structure_component = _clamp(100.0 - long_sentence_percent * 1.5)
        quality_score = _clamp(
            readability_component * 0.35
            + sentence_component * 0.25
            + active_voice_component * 0.20
            + structure_component * 0.20
        )

        flags: list[str] = []
        if flesch < 30:
            flags.append("Very dense prose: simplify long sentences and define technical terms.")
        elif flesch > 80:
            flags.append("Very simple prose: add precise technical explanation where needed.")
        if passive_percent > 25:
            flags.append("Frequent passive voice may hide who performs each action.")
        if long_sentence_percent > 30:
            flags.append("Many sentences exceed 30 words and should be split.")

        if quality_score >= 75:
            rating = "Clear"
        elif quality_score >= 55:
            rating = "Adequate"
        else:
            rating = "Needs editing"

        return {
            "method_version": WRITING_METHOD_VERSION,
            "quality_score": quality_score,
            "overall_rating": rating,
            "metrics": {
                "word_count": len(words),
                "sentence_count": sentence_count,
                "words_per_sentence": round(words_per_sentence, 1),
                "flesch_reading_ease": round(flesch, 1),
                "gunning_fog": round(fog, 1),
                "passive_voice_count": passive_count,
                "passive_sentence_percent": round(passive_percent, 1),
                "long_sentence_percent": round(long_sentence_percent, 1),
            },
            "flags": flags,
            "status": "success",
        }

    @staticmethod
    def _empty_response(reason: str) -> dict[str, Any]:
        return {
            "method_version": WRITING_METHOD_VERSION,
            "quality_score": None,
            "overall_rating": "N/A",
            "metrics": {
                "word_count": 0,
                "sentence_count": 0,
                "words_per_sentence": 0.0,
                "flesch_reading_ease": None,
                "gunning_fog": None,
                "passive_voice_count": 0,
                "passive_sentence_percent": 0.0,
                "long_sentence_percent": 0.0,
            },
            "flags": [reason],
            "status": "no_data",
        }


writing_quality_service = WritingQualityService()
