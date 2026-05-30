from __future__ import annotations

import json
import re
import shutil
from html import escape
from pathlib import Path

from .models import Deck, Slide

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
THEMES_DIR = PACKAGE_ROOT / "themes"
TEMPLATES_DIR = PACKAGE_ROOT / "templates"


def render_deck(deck: Deck, output: str | Path, *, single_file: bool = False) -> Path:
    output_path = Path(output)
    if output_path.suffix.lower() == ".html":
        output_path = output_path.with_suffix("")

    output_path.mkdir(parents=True, exist_ok=True)
    assets_dir = output_path / "assets"
    (assets_dir / "figures").mkdir(parents=True, exist_ok=True)
    (assets_dir / "style.css").write_text(_load_theme(deck.theme), encoding="utf-8")
    (assets_dir / "deck.js").write_text((TEMPLATES_DIR / "deck.js").read_text(encoding="utf-8"), encoding="utf-8")
    (output_path / "deck.json").write_text(json.dumps(deck.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    html = _render_html(deck, assets_prefix="assets/", embed_assets=False, output_dir=output_path)
    (output_path / "index.html").write_text(html, encoding="utf-8")
    return output_path / "index.html"


def _render_html(deck: Deck, *, assets_prefix: str, embed_assets: bool, output_dir: Path) -> str:
    template = (TEMPLATES_DIR / "index.html.j2").read_text(encoding="utf-8")
    slide_html = "\n".join(_render_slide(deck, slide, index, output_dir, assets_prefix) for index, slide in enumerate(deck.slides, start=1))
    if embed_assets:
        css_block = f"<style>\n{_load_theme(deck.theme)}\n</style>"
        js_block = f"<script>\n{(TEMPLATES_DIR / 'deck.js').read_text(encoding='utf-8')}\n</script>"
    else:
        css_block = f'<link rel="stylesheet" href="{assets_prefix}style.css">'
        js_block = f'<script src="{assets_prefix}deck.js"></script>'
    # Single-pass substitution: re.sub scans left-to-right and never re-scans
    # inserted text, so a value (e.g. the title) containing a literal sentinel
    # like "__SLIDES__" cannot corrupt a later replacement.
    replacements = {
        "__TITLE__": escape(deck.title),
        "__AUTHOR__": escape(deck.author),
        "__SLIDE_COUNT__": str(len(deck.slides)),
        "__STYLE_BLOCK__": css_block,
        "__SLIDES__": slide_html,
        "__SCRIPT_BLOCK__": js_block,
    }
    pattern = re.compile("|".join(re.escape(token) for token in replacements))
    return pattern.sub(lambda m: replacements[m.group(0)], template)


def _render_slide(deck: Deck, slide: Slide, index: int, output_dir: Path, assets_prefix: str) -> str:
    item_count = len(slide.bullets)
    density = "is-sparse" if 0 < item_count <= 3 else "is-dense" if item_count >= 5 else "is-balanced"
    classes = f"slide slide-{escape(slide.type)} {density} items-{item_count} {_title_fit_class(slide)} {_motif_class(slide)}"
    if slide.layout:
        classes += f" layout-{escape(slide.layout)}"
    attrs = f'class="{classes}" data-slide="{index}" data-type="{escape(slide.type)}"'
    renderers = {"toc": _toc, "section": _section, "split": _split, "summary": _summary, "ending": _ending}
    if slide.type == "cover":
        body = _cover(slide, deck)
    elif slide.type == "figure":
        body = _figure(deck, slide, output_dir, assets_prefix)
    else:
        body = renderers.get(slide.type, _content)(slide)
    notes = f'<aside class="notes">{escape(slide.notes)}</aside>' if slide.notes else ""
    return f"<section {attrs}>\n{body}\n{notes}\n</section>"


def _cover(slide: Slide, deck: Deck) -> str:
    author = slide.data.get("author") or deck.author
    affiliation = slide.data.get("affiliation") or slide.subtitle or deck.affiliation
    date = slide.data.get("date") or deck.date
    meta_items = [
        ("Presenter", author),
        ("Affiliation", affiliation),
        ("Date", date),
    ]
    meta_html = "".join(
        f'<div><span>{escape(label)}</span><strong>{escape(value)}</strong></div>'
        for label, value in meta_items if value
    )
    meta_block = f'<div class="cover-meta">{meta_html}</div>' if meta_html else ""
    return f'<div class="cover-shell"><p class="eyebrow">Academic Presentation</p><h1>{escape(slide.title)}</h1><p class="subtitle">{escape(slide.subtitle)}</p>{meta_block}</div>'


def _toc(slide: Slide) -> str:
    items = "".join(f"<li><span>{i:02d}</span>{escape(item)}</li>" for i, item in enumerate(slide.bullets, start=1))
    return f'<div class="slide-header"><p>Outline</p><h2>{escape(slide.title or "Outline")}</h2></div><ol class="toc-list">{items}</ol>'


def _section(slide: Slide) -> str:
    return f'<div class="section-shell"><p>{escape(slide.subtitle)}</p><h2>{escape(slide.title)}</h2></div>'


def _content(slide: Slide) -> str:
    return f'<div class="slide-header"><p>Key Points</p><h2>{_inline(slide.title)}</h2></div><div class="content-card">{_bullet_list(slide.bullets)}</div>'


def _figure(deck: Deck, slide: Slide, output_dir: Path, assets_prefix: str) -> str:
    image_html = ""
    if slide.image:
        image_src = _prepare_image(slide.image, output_dir, assets_prefix, deck.metadata.get("source_path", ""))
        image_html = f'<figure><img src="{escape(image_src)}" alt="{escape(slide.caption or slide.title)}"><figcaption>{_inline(slide.caption)}</figcaption></figure>'
    return f'<div class="slide-header"><p>Figure</p><h2>{_inline(slide.title)}</h2></div><div class="figure-grid"><div class="figure-copy">{_bullet_list(slide.bullets)}</div>{image_html}</div>'


def _split(slide: Slide) -> str:
    midpoint = max(1, len(slide.bullets) // 2)
    return f'<div class="slide-header"><p>Comparison</p><h2>{escape(slide.title)}</h2></div><div class="split-grid"><div>{_bullet_list(slide.bullets[:midpoint])}</div><div>{_bullet_list(slide.bullets[midpoint:])}</div></div>'


def _summary(slide: Slide) -> str:
    return f'<div class="slide-header"><p>Summary</p><h2>{_inline(slide.title or "Summary")}</h2></div><div class="summary-card">{_bullet_list(slide.bullets)}</div>'


def _ending(slide: Slide) -> str:
    return f'<div class="ending-shell"><h2>{escape(slide.title or "Thank You")}</h2><p>{escape(slide.subtitle or "Questions and discussion")}</p></div>'


def _bullet_list(items: list[str]) -> str:
    if not items:
        return ""
    plain_class = " bullet-list-plain" if len(items) <= 2 else ""
    return f'<ol class="bullet-list{plain_class}">' + "".join(f"<li>{_inline(item)}</li>" for item in items) + "</ol>"


def _inline(text: str) -> str:
    """Escape text, then allow small, safe emphasis markers for presentation use."""
    value = escape(text or "")
    value = re.sub(r"\*\*(.+?)\*\*", r'<span class="text-highlight">\1</span>', value)
    value = re.sub(r"==(.+?)==", r'<span class="text-highlight">\1</span>', value)
    return value


def _motif_class(slide: Slide) -> str:
    title = f"{slide.title} {slide.subtitle}".lower()
    text = f"{title} {' '.join(slide.bullets)}".lower()
    priority_checks = (
        ("motif-bio", ("bio", "therapy", "medical", "mri", "drug", "imaging")),
        ("motif-application", ("application", "display", "photonics", "sensing", "security")),
        ("motif-hybrid", ("hybrid", "functional", "quantum dot", "graphene", "gold")),
        ("motif-risk", ("risk", "limitation", "bottleneck", "problem", "challenge")),
        ("motif-control", ("strategy", "control", "tune", "enhance")),
        ("motif-mechanism", ("mechanism", "energy", "photon", "lanthanide", "emission")),
    )
    for motif, words in priority_checks:
        if any(word in title for word in words):
            return motif
    if any(word in text for word in ("bio", "therapy", "medical", "mri", "drug", "imaging")):
        return "motif-bio"
    if any(word in text for word in ("application", "display", "photonics", "sensing", "security")):
        return "motif-application"
    if any(word in text for word in ("hybrid", "functional", "quantum dot", "graphene", "gold")):
        return "motif-hybrid"
    if any(word in text for word in ("risk", "limitation", "bottleneck", "problem", "challenge")):
        return "motif-risk"
    if any(word in text for word in ("strategy", "control", "tune", "enhance")):
        return "motif-control"
    if any(word in text for word in ("mechanism", "energy", "photon", "lanthanide", "emission")):
        return "motif-mechanism"
    return "motif-general"


def _title_fit_class(slide: Slide) -> str:
    """Add coarse title-length classes so CSS can shrink long headings."""
    title_weight = _text_width_weight(slide.title)
    subtitle_weight = _text_width_weight(slide.subtitle) * 0.6
    weight = max(title_weight, subtitle_weight)
    if weight >= 82:
        return "title-fit-xxlong"
    if weight >= 58:
        return "title-fit-xlong"
    if weight >= 38:
        return "title-fit-long"
    return "title-fit-normal"


def _text_width_weight(text: str) -> float:
    total = 0.0
    for char in text or "":
        codepoint = ord(char)
        if char.isspace():
            total += 0.35
        elif (
            0x1100 <= codepoint <= 0x11FF
            or 0x2E80 <= codepoint <= 0xA4CF
            or 0xAC00 <= codepoint <= 0xD7AF
            or 0xF900 <= codepoint <= 0xFAFF
            or 0xFF00 <= codepoint <= 0xFFEF
        ):
            total += 1.0
        else:
            total += 0.55
    return total


def _prepare_image(image: str, output_dir: Path, assets_prefix: str, source_path: str = "") -> str:
    image_path = Path(image)
    if image.startswith(("http://", "https://", "data:")):
        return image
    if not image_path.is_absolute() and source_path:
        candidate = Path(source_path).parent / image_path
        if candidate.exists():
            image_path = candidate
    if image_path.exists() and assets_prefix:
        target = output_dir / "assets" / "figures" / image_path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            if image_path.resolve() != target.resolve():
                shutil.copy2(image_path, target)
            return f"{assets_prefix}figures/{target.name}"
        except OSError:
            return image
    return image


def _load_theme(theme: str) -> str:
    path = THEMES_DIR / f"{theme}.css"
    if not path.exists():
        path = THEMES_DIR / "academic-blue.css"
    return path.read_text(encoding="utf-8")
