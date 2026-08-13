"""
ai_score_estimator.py — Local heuristic estimator for AI detection likelihood.

Produces a 0-100 score (lower = more human-like) based on proxy signals:
1. Tier 1/2 word frequency
2. Burstiness (sentence length SD)
3. Transition word density
4. Punctuation fingerprint (em-dash, semicolon frequency)
5. Template phrase count

This is NOT a replacement for actual AI detectors. It provides a rough
pre-submission sanity check.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from tier1_words import TIER1_WORDS

TIER2_WORDS = {
    "significant": 5, "novel": 4, "effective": 5, "furthermore": 3,
    "moreover": 3, "notably": 3, "remarkable": 3, "remarkably": 3,
    "various": 5, "several": 5, "numerous": 3, "important": 5,
    "clearly": 4, "obviously": 1,
}

AI_TRANSITIONS = [
    "furthermore", "moreover", "additionally", "in addition",
    "in conclusion", "to summarize", "in summary",
    "as previously mentioned", "it is clear that",
    "this highlights the importance",
]

TEMPLATE_PHRASES = [
    r"it is worth noting that",
    r"it should be mentioned that",
    r"it is important to note that",
    r"in order to\b",
    r"due to the fact that",
    r"in light of the fact that",
    r"for the purpose of",
    r"with regard to",
    r"a large number of",
    r"in the majority of cases",
    r"it has been shown that",
    r"in recent years",
    r"with the rapid development of",
]


@dataclass
class ScoreBreakdown:
    total: int
    tier1_score: int
    tier2_score: int
    burstiness_score: int
    transition_score: int
    punctuation_score: int
    template_score: int
    details: dict


def count_words(text: str) -> int:
    return len(text.split())


def extract_sentences(text: str) -> list[str]:
    text = re.sub(r"\$[^$]+\$", "MATH", text)
    text = re.sub(r"\\cite\{[^}]*\}", "CITE", text)
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
    return [s.strip() for s in sentences if len(s.strip()) > 0]


def score_tier1(text: str) -> tuple[int, list[str]]:
    text_lower = text.lower()
    total_words = count_words(text)
    found = []
    count = 0
    for word in TIER1_WORDS:
        matches = re.findall(rf"\b{re.escape(word)}\b", text_lower)
        if matches:
            found.append(f"{word}({len(matches)})")
            count += len(matches)
    density = count / max(total_words, 1) * 1000
    score = min(int(density * 5), 25)
    return score, found


def score_tier2(text: str) -> tuple[int, list[str]]:
    text_lower = text.lower()
    violations = []
    violation_count = 0
    for word, threshold in TIER2_WORDS.items():
        matches = re.findall(rf"\b{re.escape(word)}\b", text_lower)
        if len(matches) > threshold:
            excess = len(matches) - threshold
            violations.append(f"{word}({len(matches)}/{threshold})")
            violation_count += excess
    score = min(violation_count * 3, 15)
    return score, violations


def score_burstiness(text: str) -> tuple[int, dict]:
    sentences = extract_sentences(text)
    if len(sentences) < 5:
        return 0, {"sd": 0, "note": "too few sentences (burstiness not evaluated)"}

    lengths = [len(s.split()) for s in sentences]
    mean = sum(lengths) / len(lengths)
    variance = sum((length - mean) ** 2 for length in lengths) / len(lengths)
    sd = variance ** 0.5
    length_range = max(lengths) - min(lengths)

    if sd >= 10:
        score = 0
    elif sd >= 8:
        score = 5
    elif sd >= 6:
        score = 12
    elif sd >= 4:
        score = 18
    else:
        score = 25

    return score, {"sd": round(sd, 2), "range": length_range}


def score_transitions(text: str) -> tuple[int, int]:
    text_lower = text.lower()
    total_words = count_words(text)
    count = 0
    for phrase in AI_TRANSITIONS:
        count += len(re.findall(rf"\b{re.escape(phrase)}\b", text_lower))
    density = count / max(total_words, 1) * 1000
    score = min(int(density * 4), 15)
    return score, count


def score_punctuation(text: str) -> tuple[int, dict]:
    total_words = count_words(text)
    em_dashes = text.count("—") + text.count("---")
    semicolons = text.count(";")

    em_per_300 = em_dashes / max(total_words, 1) * 300
    semi_per_300 = semicolons / max(total_words, 1) * 300

    score = 0
    if em_per_300 > 1:
        score += min(int((em_per_300 - 1) * 5), 10)
    if semi_per_300 > 0.5:
        score += min(int(semi_per_300 * 4), 5)

    return min(score, 10), {"em_dashes": em_dashes, "semicolons": semicolons}


def score_templates(text: str) -> tuple[int, int]:
    text_lower = text.lower()
    count = 0
    for pattern in TEMPLATE_PHRASES:
        count += len(re.findall(pattern, text_lower))
    score = min(count * 3, 10)
    return score, count


def estimate(text: str) -> ScoreBreakdown:
    t1_score, t1_found = score_tier1(text)
    t2_score, t2_violations = score_tier2(text)
    burst_score, burst_info = score_burstiness(text)
    trans_score, trans_count = score_transitions(text)
    punct_score, punct_info = score_punctuation(text)
    templ_score, templ_count = score_templates(text)

    total = t1_score + t2_score + burst_score + trans_score + punct_score + templ_score
    total = min(total, 100)

    return ScoreBreakdown(
        total=total,
        tier1_score=t1_score,
        tier2_score=t2_score,
        burstiness_score=burst_score,
        transition_score=trans_score,
        punctuation_score=punct_score,
        template_score=templ_score,
        details={
            "tier1_found": t1_found,
            "tier2_violations": t2_violations,
            "burstiness": burst_info,
            "transition_count": trans_count,
            "punctuation": punct_info,
            "template_count": templ_count,
        },
    )


def interpret_score(score: int) -> str:
    if score <= 15:
        return "LOW risk — text appears human-written"
    elif score <= 35:
        return "MODERATE risk — some AI patterns detected"
    elif score <= 60:
        return "HIGH risk — significant AI patterns present"
    else:
        return "VERY HIGH risk — strongly AI-like text"


def main():
    if len(sys.argv) < 2:
        print("Usage: python ai_score_estimator.py <text_file>")
        sys.exit(1)

    text_path = Path(sys.argv[1])
    text = text_path.read_text(encoding="utf-8")

    result = estimate(text)

    output = {
        "score": result.total,
        "interpretation": interpret_score(result.total),
        "breakdown": {
            "tier1_vocabulary": f"{result.tier1_score}/25",
            "tier2_frequency": f"{result.tier2_score}/15",
            "burstiness_deficit": f"{result.burstiness_score}/25",
            "ai_transitions": f"{result.transition_score}/15",
            "punctuation_fingerprint": f"{result.punctuation_score}/10",
            "template_phrases": f"{result.template_score}/10",
        },
        "details": result.details,
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
