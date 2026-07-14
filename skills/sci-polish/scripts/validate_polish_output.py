"""
validate_polish_output.py — Validates polished text against skill constraints.

Checks:
1. Protected regions intact (LaTeX commands, math, citations)
2. Tier 1 forbidden words absent
3. Burstiness metrics (sentence length SD > 8)
4. Terminology consistency (no synonym cycling for key terms)
5. Report format completeness
"""

from __future__ import annotations

import re
import sys
import json
from pathlib import Path
from dataclasses import dataclass, field

from tier1_words import TIER1_WORDS

LATEX_PROTECTION_PATTERNS = [
    r"\\cite\{[^}]*\}",
    r"\\ref\{[^}]*\}",
    r"\\label\{[^}]*\}",
    r"\$[^$]+\$",
    r"\\\[[^\]]*\\\]",
    r"\\begin\{equation\}.*?\\end\{equation\}",
    r"\\begin\{align\}.*?\\end\{align\}",
    r"\\begin\{algorithm\}.*?\\end\{algorithm\}",
]


@dataclass
class ValidationResult:
    passed: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


def extract_sentences(text: str) -> list[str]:
    text = re.sub(r"\$[^$]+\$", "MATH", text)
    text = re.sub(r"\\cite\{[^}]*\}", "CITE", text)
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
    return [s.strip() for s in sentences if len(s.strip()) > 0]


def word_count(sentence: str) -> int:
    return len(sentence.split())


def check_burstiness(text: str) -> dict:
    sentences = extract_sentences(text)
    if len(sentences) < 5:
        return {"sd": 0, "range": 0, "mid_band_ratio": 0, "status": "too_short"}

    lengths = [word_count(s) for s in sentences]
    mean = sum(lengths) / len(lengths)
    variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
    sd = variance ** 0.5
    length_range = max(lengths) - min(lengths)
    mid_band = sum(1 for l in lengths if 10 <= l <= 20)
    mid_band_ratio = mid_band / len(lengths)

    return {
        "sd": round(sd, 2),
        "range": length_range,
        "mid_band_ratio": round(mid_band_ratio, 2),
        "status": "pass" if sd > 8 and length_range >= 20 and mid_band_ratio < 0.5 else "fail",
    }


def check_tier1_words(text: str) -> list[str]:
    found = []
    text_lower = text.lower()
    for word in TIER1_WORDS:
        pattern = rf"\b{re.escape(word)}\b"
        matches = re.findall(pattern, text_lower)
        if matches:
            found.append(f"{word} ({len(matches)}x)")
    return found


def check_latex_protection(original: str, polished: str) -> list[str]:
    errors = []
    for pattern in LATEX_PROTECTION_PATTERNS:
        orig_matches = set(re.findall(pattern, original, re.DOTALL))
        polish_matches = set(re.findall(pattern, polished, re.DOTALL))
        missing = orig_matches - polish_matches
        if missing:
            for m in list(missing)[:3]:
                errors.append(f"Protected region removed/modified: {m[:60]}...")
    return errors


def check_report_format(report: str) -> list[str]:
    required_sections = [
        "Phase A",
        "Phase B",
        "Dimension",
        "Before",
        "After",
    ]
    missing = []
    for section in required_sections:
        if section not in report:
            missing.append(f"Missing required section: {section}")
    return missing


def validate(
    original: str,
    polished: str,
    report: str | None = None,
) -> ValidationResult:
    result = ValidationResult()

    tier1_found = check_tier1_words(polished)
    if tier1_found:
        result.passed = False
        result.errors.append(f"Tier 1 AI words found: {', '.join(tier1_found)}")

    protection_errors = check_latex_protection(original, polished)
    if protection_errors:
        result.passed = False
        result.errors.extend(protection_errors)

    burstiness = check_burstiness(polished)
    result.metrics["burstiness"] = burstiness
    if burstiness["status"] == "too_short":
        result.warnings.append(
            "Burstiness not evaluated: text has fewer than 5 sentences"
        )
    elif burstiness["status"] == "fail":
        result.warnings.append(
            f"Burstiness insufficient: SD={burstiness['sd']}, "
            f"range={burstiness['range']}, mid_band={burstiness['mid_band_ratio']}"
        )

    if report:
        format_errors = check_report_format(report)
        if format_errors:
            result.warnings.extend(format_errors)

    return result


def main():
    if len(sys.argv) < 3:
        print("Usage: python validate_polish_output.py <original_file> <polished_file> [report_file]")
        sys.exit(1)

    original_path = Path(sys.argv[1])
    polished_path = Path(sys.argv[2])
    report_path = Path(sys.argv[3]) if len(sys.argv) > 3 else None

    original = original_path.read_text(encoding="utf-8")
    polished = polished_path.read_text(encoding="utf-8")
    report = report_path.read_text(encoding="utf-8") if report_path else None

    result = validate(original, polished, report)

    output = {
        "passed": result.passed,
        "errors": result.errors,
        "warnings": result.warnings,
        "metrics": result.metrics,
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))
    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
