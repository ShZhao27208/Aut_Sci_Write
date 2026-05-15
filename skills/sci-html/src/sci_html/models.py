from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

SlideType = Literal["cover", "toc", "section", "content", "figure", "split", "comparison", "formula", "timeline", "summary", "ending"]


@dataclass
class Slide:
    type: SlideType = "content"
    title: str = ""
    subtitle: str = ""
    bullets: list[str] = field(default_factory=list)
    image: str | None = None
    caption: str = ""
    notes: str = ""
    layout: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Slide":
        known = {field.name for field in cls.__dataclass_fields__.values()}
        kwargs = {key: value for key, value in data.items() if key in known}
        extra = {key: value for key, value in data.items() if key not in known}
        kwargs.setdefault("data", {})
        if extra:
            kwargs["data"] = {**kwargs["data"], **extra}
        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Deck:
    title: str = "Untitled Deck"
    author: str = ""
    affiliation: str = ""
    date: str = ""
    theme: str = "academic-blue"
    slides: list[Slide] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Deck":
        slides = [Slide.from_dict(slide) for slide in data.get("slides", [])]
        return cls(
            title=data.get("title", "Untitled Deck"),
            author=data.get("author", ""),
            affiliation=data.get("affiliation", ""),
            date=data.get("date", ""),
            theme=data.get("theme", "academic-blue"),
            slides=slides,
            metadata=data.get("metadata", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "author": self.author,
            "affiliation": self.affiliation,
            "date": self.date,
            "theme": self.theme,
            "slides": [slide.to_dict() for slide in self.slides],
            "metadata": self.metadata,
        }
