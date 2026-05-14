"""Rule-based text parser for aut_sci_ppt.

The parser owns section-page creation. The paginator should only split or
decorate pages that already exist in ParsedData.
"""

from __future__ import annotations

import json
import re
from typing import Dict, List

from ..models import (
    ContentDetailData,
    ContentListData,
    CoverData,
    FigurePlaceholder,
    ListItem,
    Page,
    ParsedData,
    SectionData,
    TimelineData,
    TimelineEvent,
    PAGE_TYPE_CONTENT_DETAIL,
    PAGE_TYPE_CONTENT_LIST,
    PAGE_TYPE_SECTION,
    PAGE_TYPE_TIMELINE,
)

FIG_RE = re.compile(
    r"<!--\s*(?:fig|figure|\u56fe)\s*:?\s*([^|]+)\|\s*path=([^|]*)\|\s*position=(\w+)\s*-->",
    re.IGNORECASE,
)

TITLE_KEYS = {"title", "topic", "subject", "\u4e3b\u9898", "\u6807\u9898"}
AUTHOR_KEYS = {"author", "presenter", "speaker", "\u4f5c\u8005", "\u7533\u8bf7\u4eba", "\u6c47\u62a5\u4eba", "\u59d3\u540d"}
ADVISOR_KEYS = {"advisor", "supervisor", "\u5bfc\u5e08", "\u6307\u5bfc"}
DATE_KEYS = {"date", "time", "\u65e5\u671f", "\u65f6\u95f4"}
DIRECTION_KEYS = {"direction", "field", "\u65b9\u5411"}

DETAIL_KEYWORDS = {
    "research",
    "method",
    "result",
    "discussion",
    "analysis",
    "experiment",
    "background",
    "\u7814\u7a76",
    "\u65b9\u6cd5",
    "\u7ed3\u679c",
    "\u8ba8\u8bba",
    "\u5206\u6790",
    "\u5b9e\u9a8c",
}
TIMELINE_KEYWORDS = {"timeline", "plan", "schedule", "future", "\u8ba1\u5212", "\u672a\u6765", "\u89c4\u5212"}


class TextParser:
    SUPPORTED_CONTENT_TYPES = {
        "list": PAGE_TYPE_CONTENT_LIST,
        "detail": PAGE_TYPE_CONTENT_DETAIL,
        "timeline": PAGE_TYPE_TIMELINE,
    }

    def __init__(self, config=None, scene: str = "default"):
        self.config = config
        self.scene = scene
        self.parsed_data = ParsedData()
        self.warnings: List[str] = []

    def parse(self, text: str) -> ParsedData:
        self.parsed_data = ParsedData()
        text = self._preprocess(text)
        lines = text.strip().splitlines()
        self._parse_meta(lines)
        self._parse_sections(lines)
        return self.parsed_data

    def validate(self, data: ParsedData) -> List[str]:
        warnings = []
        if not data.meta.title:
            warnings.append("Missing title")
        if not data.meta.author:
            warnings.append("Missing author")
        if not data.sections:
            warnings.append("No sections detected")
        self.warnings = warnings
        return warnings

    def _preprocess(self, text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("{"):
            try:
                return self._convert_mapping_to_text(json.loads(stripped))
            except Exception:
                return text
        if stripped.startswith("---"):
            try:
                import yaml

                data = yaml.safe_load(stripped)
                if isinstance(data, dict):
                    return self._convert_mapping_to_text(data)
            except Exception:
                return text
        return text

    def _convert_mapping_to_text(self, data: Dict) -> str:
        lines = []
        for key, value in (data.get("meta") or {}).items():
            if value:
                lines.append(f"{key}: {value}")
        for index, section in enumerate(data.get("sections") or [], 1):
            title = section.get("title") or f"Section {index}"
            lines.append(f"{index}. {title}")
            for item in section.get("items") or section.get("points") or []:
                lines.append(f"- {item}")
            for event in section.get("events") or []:
                lines.append(
                    f"- {event.get('date', '')} {event.get('title', '')}: {event.get('description', '')}"
                )
        return "\n".join(lines)

    def _parse_meta(self, lines: List[str]) -> None:
        meta = CoverData()
        for raw in lines:
            parsed = self._split_key_value(raw)
            if not parsed:
                continue
            key, value = parsed
            key_lower = key.lower()
            if self._contains_any(key_lower, TITLE_KEYS):
                meta.title = value
            elif self._contains_any(key_lower, AUTHOR_KEYS):
                meta.author = value
            elif self._contains_any(key_lower, ADVISOR_KEYS):
                meta.advisor = value
            elif self._contains_any(key_lower, DATE_KEYS):
                meta.date = value
            elif self._contains_any(key_lower, DIRECTION_KEYS):
                meta.direction = value
        self.parsed_data.meta = meta

    def _parse_sections(self, lines: List[str]) -> None:
        current_title = None
        current_content: List[str] = []
        section_index = 0

        for raw in lines:
            line = raw.strip()
            if not line or self._split_key_value(line):
                continue
            if self._is_section_header(line):
                if current_title is not None:
                    section_index += 1
                    self._add_section(section_index, current_title, current_content)
                current_title = self._section_title(line)
                current_content = []
                continue
            if current_title is not None:
                current_content.append(line)

        if current_title is not None:
            section_index += 1
            self._add_section(section_index, current_title, current_content)

    def _add_section(self, index: int, title: str, content: List[str]) -> None:
        text_lines = []
        figures = []
        for line in content:
            match = FIG_RE.match(line)
            if match:
                figures.append(
                    FigurePlaceholder(
                        label=match.group(1).strip(),
                        path=match.group(2).strip(),
                        position=match.group(3).strip(),
                        caption=match.group(1).strip(),
                    )
                )
            else:
                text_lines.append(self._strip_bullet(line))

        page_type = self._classify_page(title, text_lines)
        if page_type == PAGE_TYPE_TIMELINE:
            data = self._timeline_data(title, index, text_lines)
        elif page_type == PAGE_TYPE_CONTENT_DETAIL:
            data = self._detail_data(title, index, text_lines)
        else:
            data = self._list_data(title, index, text_lines)
        data.figures = figures

        self.parsed_data.sections.append(
            Page(
                page_type=PAGE_TYPE_SECTION,
                data=SectionData(part_num=str(index), part_title=title),
            )
        )
        self.parsed_data.sections.append(Page(page_type=page_type, data=data))

    def _classify_page(self, title: str, lines: List[str]) -> str:
        joined = f"{title} {' '.join(lines)}".lower()
        if self._contains_any(joined, TIMELINE_KEYWORDS) or any(re.search(r"\b20\d{2}\b", line) for line in lines):
            return PAGE_TYPE_TIMELINE
        if self._contains_any(joined, DETAIL_KEYWORDS):
            return PAGE_TYPE_CONTENT_DETAIL
        return PAGE_TYPE_CONTENT_LIST

    @staticmethod
    def _list_data(title: str, index: int, lines: List[str]) -> ContentListData:
        return ContentListData(
            title=title,
            part_num=str(index),
            items=[ListItem(text=line) for line in lines if line],
        )

    @staticmethod
    def _detail_data(title: str, index: int, lines: List[str]) -> ContentDetailData:
        return ContentDetailData(title=title, part_num=str(index), points=[line for line in lines if line])

    @staticmethod
    def _timeline_data(title: str, index: int, lines: List[str]) -> TimelineData:
        events = []
        for line in lines:
            if not line:
                continue
            match = re.match(r"(\S+)\s*[:\-]\s*(.+)", line)
            if match:
                events.append(
                    TimelineEvent(
                        date=match.group(1),
                        title=match.group(2)[:20],
                        description=match.group(2),
                    )
                )
            else:
                events.append(TimelineEvent(date="", title=line[:20], description=line))
        return TimelineData(title=title, part_num=str(index), events=events)

    @staticmethod
    def _split_key_value(line: str):
        stripped = line.strip()
        if ":" in stripped:
            key, value = stripped.split(":", 1)
        elif "\uff1a" in stripped:
            key, value = stripped.split("\uff1a", 1)
        else:
            return None
        return key.strip(), value.strip()

    @staticmethod
    def _contains_any(text: str, needles) -> bool:
        return any(needle in text for needle in needles)

    @staticmethod
    def _is_section_header(line: str) -> bool:
        return bool(
            re.match(r"^\d+\.\s+\S+", line)
            or re.match(r"^Part\s+\d+\b", line, re.IGNORECASE)
            or re.match(r"^\u7b2c[\u4e00-\u9fa5\d]+\u90e8\u5206", line)
        )

    @staticmethod
    def _section_title(line: str) -> str:
        match = re.match(r"^\d+\.\s+(.+)", line)
        if match:
            return match.group(1).strip()
        match = re.match(r"^Part\s+\d+\s*[:\-]?\s*(.*)", line, re.IGNORECASE)
        if match and match.group(1).strip():
            return match.group(1).strip()
        return line.strip()

    @staticmethod
    def _strip_bullet(line: str) -> str:
        return re.sub(r"^[*\-\u2022\u25cf\u25c6\u25a0]+\s*", "", line.strip())


def parse_user_input(text: str, config=None, scene: str = "default") -> ParsedData:
    return TextParser(config, scene=scene).parse(text)
