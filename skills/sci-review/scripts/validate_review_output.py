#!/usr/bin/env python3
"""Validate sci-review outputs against structural and tone rules."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


CASE_RULES = {
    "literature-review": {
        "required": ["Introduction", "Methodology", "Challenges", "Conclusion"],
        "banned": [
            "it is worth noting",
            "as we all know",
            "significantly better",
        ],
    },
    "rebuttal": {
        "required": [
            "Reviewer concern",
            "Response",
            "Revision plan",
        ],
        "banned": [
            "reviewer misunderstood",
            "the reviewer is wrong",
            "obviously",
        ],
    },
}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def validate_text(text: str, case: str) -> dict:
    if case not in CASE_RULES:
        raise ValueError(f"Unknown case: {case}")

    normalized = normalize(text)
    rules = CASE_RULES[case]
    missing = [item for item in rules["required"] if item.lower() not in normalized]
    banned = [item for item in rules["banned"] if item.lower() in normalized]

    return {
        "case": case,
        "passed": not missing and not banned,
        "missing_required": missing,
        "banned_phrases": banned,
    }


def load_golden_cases(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate sci-review output structure and tone.")
    parser.add_argument("--case", choices=sorted(CASE_RULES), help="Validation case to apply.")
    parser.add_argument("--output", help="Path to a generated markdown/text output.")
    parser.add_argument("--golden", help="Path to golden_cases.json to list available cases.")
    parser.add_argument("--list-golden", action="store_true", help="List golden case prompts and expectations.")
    args = parser.parse_args(argv)

    if args.list_golden:
        golden_path = Path(args.golden or Path(__file__).resolve().parents[1] / "tests" / "golden_cases.json")
        print(json.dumps(load_golden_cases(golden_path), ensure_ascii=False, indent=2))
        return 0

    if not args.case or not args.output:
        parser.error("--case and --output are required unless --list-golden is used")

    text = Path(args.output).read_text(encoding="utf-8")
    result = validate_text(text, args.case)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
