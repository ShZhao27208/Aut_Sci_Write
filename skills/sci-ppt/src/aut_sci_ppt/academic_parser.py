"""Lightweight academic content parser used by EnhancedPPTAgent."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List


class ContentType(Enum):
    THEOREM = "theorem"
    DEFINITION = "definition"
    FORMULA = "formula"
    EXPERIMENT = "experiment"
    INNOVATION = "innovation"
    BACKGROUND = "background"
    CONCLUSION = "conclusion"
    OTHER = "other"


@dataclass
class ContentBlock:
    type: ContentType
    title: str
    content: str
    importance: float
    formulas: List[str] = field(default_factory=list)


class AcademicParser:
    def __init__(self):
        self.content_blocks: List[ContentBlock] = []

    def parse_text(self, text: str) -> List[ContentBlock]:
        self.content_blocks = []
        for paragraph in re.split(r"\n\s*\n", text):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            content_type = self._identify_type(paragraph)
            self.content_blocks.append(
                ContentBlock(
                    type=content_type,
                    title=self._extract_title(paragraph),
                    content=paragraph,
                    importance=self._importance(paragraph, content_type),
                    formulas=self._extract_formulas(paragraph),
                )
            )
        return self.content_blocks

    def get_blocks_by_type(self, content_type: ContentType) -> List[ContentBlock]:
        return [block for block in self.content_blocks if block.type == content_type]

    def get_top_blocks(self, limit: int = 12) -> List[ContentBlock]:
        return sorted(self.content_blocks, key=lambda block: block.importance, reverse=True)[:limit]

    def generate_ppt_outline(self, limit: int = 12) -> str:
        lines = []
        for index, block in enumerate(self.get_top_blocks(limit), 1):
            title = block.title or f"Section {index}"
            lines.append(f"{index}. {title}")
            for sentence in self._sentences(block.content)[:3]:
                lines.append(f"- {sentence[:160]}")
        return "\n".join(lines)

    @staticmethod
    def _identify_type(text: str) -> ContentType:
        lower = text.lower()
        if re.search(r"\$[^$]+\$|\\begin\{equation\}|equation|formula", lower):
            return ContentType.FORMULA
        if re.search(r"\b(theorem|lemma|proposition|corollary)\b", lower):
            return ContentType.THEOREM
        if re.search(r"\b(definition|define|denote)\b", lower):
            return ContentType.DEFINITION
        if re.search(r"\b(experiment|result|evaluation|benchmark|dataset)\b", lower):
            return ContentType.EXPERIMENT
        if re.search(r"\b(novel|propose|contribution|innovation|introduce)\b", lower):
            return ContentType.INNOVATION
        if re.search(r"\b(background|introduction|related work)\b", lower):
            return ContentType.BACKGROUND
        if re.search(r"\b(conclusion|summary|future work)\b", lower):
            return ContentType.CONCLUSION
        return ContentType.OTHER

    @staticmethod
    def _extract_title(text: str) -> str:
        first_line = text.splitlines()[0].strip()
        first_line = re.sub(r"^\d+(\.\d+)*\s*", "", first_line)
        return first_line[:100]

    @staticmethod
    def _extract_formulas(text: str) -> List[str]:
        return [match.strip("$") for match in re.findall(r"\$[^$]+\$", text)]

    @staticmethod
    def _importance(text: str, content_type: ContentType) -> float:
        base = {
            ContentType.THEOREM: 0.9,
            ContentType.INNOVATION: 0.9,
            ContentType.EXPERIMENT: 0.8,
            ContentType.FORMULA: 0.75,
            ContentType.DEFINITION: 0.7,
            ContentType.CONCLUSION: 0.65,
            ContentType.BACKGROUND: 0.55,
            ContentType.OTHER: 0.45,
        }[content_type]
        return min(1.0, base + (0.1 if len(text) > 600 else 0.0))

    @staticmethod
    def _sentences(text: str) -> List[str]:
        return [item.strip() for item in re.split(r"(?<=[.!?])\s+", text) if len(item.strip()) > 20]
