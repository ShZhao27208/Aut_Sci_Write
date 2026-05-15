from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

from .models import Deck, Slide

MAX_BULLETS_PER_SLIDE = 5

META_KEYS = {
    "title": "title",
    "\u4e3b\u9898": "title",
    "\u984c\u76ee": "title",
    "author": "author",
    "\u6c47\u62a5\u4eba": "author",
    "presenter": "author",
    "affiliation": "affiliation",
    "\u5355\u4f4d": "affiliation",
    "date": "date",
    "\u65f6\u95f4": "date",
    "theme": "theme",
}
SECTION_RE = re.compile(r"^\s*(\d+)[\.)\u3001]\s*(.+?)\s*$")
BULLET_RE = re.compile(r"^\s*[-*+]\s+(.+?)\s*$")
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^\s{0,3}(#{1,3})\s+(.+?)\s*$")


def parse_deck(source: str | Path, *, source_path: str | Path | None = None) -> Deck:
    if isinstance(source, Path) or (isinstance(source, str) and Path(source).exists()):
        path = Path(source)
        text = path.read_text(encoding="utf-8")
        source_path = path
    else:
        text = str(source)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    stripped = text.strip()
    if not stripped:
        return Deck()
    if stripped.startswith("{"):
        return Deck.from_dict(json.loads(stripped))
    metadata, body = _extract_frontmatter(stripped)
    deck = _parse_markdown_slides(body, metadata) if _has_explicit_slide_breaks(body) or _looks_like_markdown_deck(body) else _parse_structured_outline(body, metadata)
    deck.metadata.setdefault("source_path", str(source_path) if source_path else "")
    return deck


def _extract_frontmatter(text: str) -> tuple[dict[str, str], str]:
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                return _parse_key_values(lines[1:index]), "\n".join(lines[index + 1 :]).strip()
    return {}, text.strip()


def _parse_key_values(lines: Iterable[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip().lower()] = value.strip().strip('"').strip("'")
    return values


def _normalize_metadata(raw: dict[str, str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for key, value in raw.items():
        normalized = META_KEYS.get(key.lower(), META_KEYS.get(key, key.lower()))
        values[normalized] = value
    return values


def _has_explicit_slide_breaks(text: str) -> bool:
    return any(line.strip() == "---" for line in text.splitlines())


def _looks_like_markdown_deck(text: str) -> bool:
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if HEADING_RE.match(line) or line.lower().startswith(("layout:", "type:")):
            return True
        return False
    return False


def _parse_markdown_slides(text: str, metadata: dict[str, str]) -> Deck:
    meta = _normalize_metadata(metadata)
    blocks = [block.strip() for block in re.split(r"^---\s*$", text, flags=re.MULTILINE) if block.strip()]
    slides = _split_overfull_slides([_parse_slide_block(block) for block in blocks])
    title = meta.get("title") or _first_title(slides) or "Untitled Deck"
    deck = Deck(title=title, author=meta.get("author", ""), affiliation=meta.get("affiliation", ""), date=meta.get("date", ""), theme=meta.get("theme", "academic-blue"), slides=slides)
    _ensure_cover_and_ending(deck)
    return deck


def _parse_slide_block(block: str) -> Slide:
    metadata, body = _extract_frontmatter(block)
    directive_metadata, body = _extract_slide_directives(body)
    meta = _normalize_metadata({**metadata, **directive_metadata})
    title = meta.get("title", "")
    subtitle = meta.get("subtitle", "")
    bullets: list[str] = []
    paragraphs: list[str] = []
    image = None
    caption = ""
    notes = ""
    in_notes = False
    for raw in body.splitlines():
        line = raw.rstrip()
        if line.strip() == ":::notes":
            in_notes = True
            continue
        if line.strip() == ":::" and in_notes:
            in_notes = False
            continue
        if in_notes:
            notes += ("\n" if notes else "") + line
            continue
        image_match = IMAGE_RE.search(line)
        if image_match:
            caption = image_match.group(1).strip()
            image = image_match.group(2).strip()
            continue
        heading_match = HEADING_RE.match(line)
        if heading_match and not title:
            title = heading_match.group(2).strip()
            continue
        bullet_match = BULLET_RE.match(line)
        if bullet_match:
            bullets.append(bullet_match.group(1).strip())
            continue
        if line.strip() and not line.lstrip().startswith("<!--"):
            paragraphs.append(line.strip())
    layout = meta.get("layout", "")
    slide_type = meta.get("type", "") or _infer_slide_type(title, bullets, image, layout)
    if paragraphs and not bullets:
        bullets = paragraphs[:6]
    elif paragraphs:
        bullets.extend(paragraphs[: max(0, 6 - len(bullets))])
    return Slide(type=slide_type, title=title, subtitle=subtitle, bullets=bullets, image=image, caption=caption, notes=notes, layout=layout)


def _extract_slide_directives(text: str) -> tuple[dict[str, str], str]:
    """Parse lightweight per-slide directives before the first content line.

    This keeps explicit Markdown slide separators simple while still allowing:
    layout: section
    subtitle: Part 1
    """
    lines = text.splitlines()
    values: dict[str, str] = {}
    body_start = 0
    directive_keys = {"layout", "type", "subtitle", *META_KEYS.keys()}
    for index, raw in enumerate(lines):
        line = raw.strip()
        if not line:
            body_start = index + 1
            continue
        if ":" not in line:
            break
        key, value = line.split(":", 1)
        normalized_key = key.strip().lower()
        if normalized_key not in directive_keys:
            break
        values[normalized_key] = value.strip().strip('"').strip("'")
        body_start = index + 1
    return values, "\n".join(lines[body_start:]).strip()


def _parse_structured_outline(text: str, metadata: dict[str, str]) -> Deck:
    meta = _normalize_metadata({**_extract_inline_metadata(text), **metadata})
    deck = Deck(title=meta.get("title", "Untitled Deck"), author=meta.get("author", ""), affiliation=meta.get("affiliation", ""), date=meta.get("date", ""), theme=meta.get("theme", "academic-blue"))
    sections: list[tuple[str, list[str]]] = []
    current_title = ""
    current_items: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or _is_metadata_line(line):
            continue
        section_match = SECTION_RE.match(line)
        if section_match:
            if current_title:
                sections.append((current_title, current_items))
            current_title = section_match.group(2).strip()
            current_items = []
            continue
        bullet_match = BULLET_RE.match(line)
        if bullet_match and current_title:
            current_items.append(bullet_match.group(1).strip())
    if current_title:
        sections.append((current_title, current_items))
    deck.slides.append(Slide(type="cover", title=deck.title, subtitle=deck.affiliation, data=_cover_data(deck)))
    if sections:
        deck.slides.append(Slide(type="toc", title="Outline", bullets=[title for title, _ in sections]))
    for index, (section_title, items) in enumerate(sections, start=1):
        deck.slides.append(Slide(type="section", title=section_title, subtitle=f"Part {index}"))
        for chunk in _chunks(items or ["Add key points for this section."], MAX_BULLETS_PER_SLIDE):
            deck.slides.append(Slide(type="content", title=section_title, bullets=chunk))
    deck.slides.append(Slide(type="ending", title="Thank You", subtitle="Questions and discussion"))
    return deck


def _extract_inline_metadata(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines()[:20]:
        line = raw.strip()
        if _is_metadata_line(line):
            key, value = re.split(r"[:\uff1a]", line, maxsplit=1)
            values[key.strip().lower()] = value.strip()
    return values


def _is_metadata_line(line: str) -> bool:
    if not re.search(r"[:\uff1a]", line):
        return False
    key = re.split(r"[:\uff1a]", line, maxsplit=1)[0].strip().lower()
    return key in META_KEYS


def _infer_slide_type(title: str, bullets: list[str], image: str | None, layout: str) -> str:
    lower_title = title.lower()
    if layout in {"cover", "toc", "section", "figure", "split", "summary", "ending"}:
        return layout
    if image:
        return "figure"
    if lower_title in {"thank you", "thanks", "questions", "q&a"}:
        return "ending"
    if "conclusion" in lower_title or "summary" in lower_title:
        return "summary"
    return "content"


def _ensure_cover_and_ending(deck: Deck) -> None:
    if not deck.slides or deck.slides[0].type != "cover":
        deck.slides.insert(0, Slide(type="cover", title=deck.title, subtitle=deck.affiliation, data=_cover_data(deck)))
    else:
        deck.slides[0].data = {**_cover_data(deck), **deck.slides[0].data}
    if deck.slides[-1].type != "ending":
        deck.slides.append(Slide(type="ending", title="Thank You", subtitle="Questions and discussion"))


def _first_title(slides: list[Slide]) -> str:
    for slide in slides:
        if slide.title:
            return slide.title
    return ""


def _chunks(items: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def _cover_data(deck: Deck) -> dict[str, str]:
    return {"author": deck.author, "affiliation": deck.affiliation, "date": deck.date}


def _split_overfull_slides(slides: list[Slide]) -> list[Slide]:
    result: list[Slide] = []
    for slide in slides:
        if slide.type not in {"content", "summary", "split"} or len(slide.bullets) <= MAX_BULLETS_PER_SLIDE:
            result.append(slide)
            continue
        for index, chunk in enumerate(_chunks(slide.bullets, MAX_BULLETS_PER_SLIDE), start=1):
            suffix = f" ({index})" if index > 1 else ""
            result.append(Slide(
                type=slide.type,
                title=f"{slide.title}{suffix}",
                subtitle=slide.subtitle,
                bullets=chunk,
                image=slide.image,
                caption=slide.caption,
                notes=slide.notes if index == 1 else "",
                layout=slide.layout,
                data=slide.data,
            ))
    return result
