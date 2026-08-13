"""Figure acquisition from the PMC Open Access bucket, with PDF cropping second.

A JATS `<graphic xlink:href="...">` holds a bare filename, not a URL, so the
filename has to be resolved against an index of real asset URLs. The PMC Open
Access cloud service publishes exactly that index per article (see
`oa_package`), which makes figure retrieval a manifest lookup rather than a
scrape. Articles outside the OA Subset have no such index, and for those the
figure regions are rendered out of the PDF instead: lower fidelity, but it is
the only image source that exists when the publisher ships none.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import http, oa_package
from .jats import Document, Figure
from .metadata import PaperMetadata

# Extensions publishers actually serve; anything else is a data file, not an image.
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff", ".webp", ".svg")

MIN_IMAGE_BYTES = 1200  # Anything smaller is an error page or a spacer.


@dataclass
class FigureReport:
    """Outcome of the figure pass."""

    saved: list[Figure] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    method: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.saved)


def download(
    doc: Document,
    meta: PaperMetadata,
    figures_dir: Path,
    *,
    pdf_path: Path | None = None,
    verbose: bool = False,
) -> FigureReport:
    """Fetch every figure image, preferring publisher originals over PDF crops."""
    report = FigureReport()
    _clear(figures_dir)
    figures_dir.mkdir(parents=True, exist_ok=True)

    candidates = [f for f in doc.figures if f.graphic_href]
    # Tables sometimes ship as images rather than markup.
    candidates += [t for t in doc.tables if t.graphic_href and not t.table_html]

    if candidates:
        package = _asset_index(meta, report, verbose)
        if package is not None:
            _from_publisher(candidates, package, figures_dir, report, verbose)

    if not report.saved and pdf_path and pdf_path.exists():
        _from_pdf(doc, pdf_path, figures_dir, report, verbose)

    if not report.method:
        report.method = "none"
    if not report.saved:
        # An empty figures/ directory reads as "images were expected here",
        # which misrepresents a paper whose images were never reachable.
        try:
            figures_dir.rmdir()
        except OSError:
            pass
    return report


def _from_publisher(
    figures: list[Figure],
    package: oa_package.OAPackage,
    figures_dir: Path,
    report: FigureReport,
    verbose: bool,
) -> None:
    """Resolve each graphic href against the OA bucket manifest."""
    for index, figure in enumerate(figures, start=1):
        urls = _candidate_urls(figure.graphic_href, package)
        if not urls:
            report.failed.append(f"{figure.display_label()}: no resolvable URL")
            continue

        payload, used_url = _first_image(urls)
        if payload is None:
            report.failed.append(f"{figure.display_label()}: all URLs failed")
            if verbose:
                print(f"  [figure] {figure.display_label()} unavailable", flush=True)
            continue

        suffix = _suffix_for(used_url, figure.graphic_href)
        name = _safe_name(figure, index, suffix)
        target = figures_dir / name
        target.write_bytes(payload)
        figure.local_path = f"figures/{name}"
        report.saved.append(figure)
        report.method = "publisher"
        if verbose:
            print(f"  [figure] {figure.display_label()} -> {name} ({len(payload)} B)", flush=True)


def _candidate_urls(href: str, package: oa_package.OAPackage) -> list[str]:
    """Every plausible URL for one graphic href, most likely first."""
    if href.startswith("http://") or href.startswith("https://"):
        return [href]

    url = package.media_for(href.split("/")[-1])
    return [url] if url else []


def _asset_index(
    meta: PaperMetadata, report: FigureReport, verbose: bool
) -> oa_package.OAPackage | None:
    """Load the OA bucket manifest that maps JATS filenames to asset URLs."""
    package = oa_package.fetch(meta.pmcid, verbose=verbose)
    if package.found and package.media:
        return package
    reason = package.errors[0] if package.errors else "manifest lists no media"
    report.notes.append(f"no publisher figure index: {reason}")
    return None


def _first_image(urls: list[str]) -> tuple[bytes | None, str]:
    """Return the first URL that yields a plausible image body."""
    for url in urls:
        try:
            payload = http.get_bytes(url)
        except http.FetchError:
            continue
        if payload and len(payload) >= MIN_IMAGE_BYTES and _looks_like_image(payload):
            return payload, url
    return None, ""


def _looks_like_image(payload: bytes) -> bool:
    """Magic-number check; publishers return HTML error pages with HTTP 200."""
    head = payload[:12]
    return (
        head.startswith(b"\xff\xd8\xff")  # JPEG
        or head.startswith(b"\x89PNG\r\n\x1a\n")  # PNG
        or head.startswith(b"GIF8")  # GIF
        or head.startswith(b"II*\x00")  # TIFF LE
        or head.startswith(b"MM\x00*")  # TIFF BE
        or head[:4] == b"RIFF"  # WebP
        or payload.lstrip()[:5].lower() == b"<?xml"  # SVG
        or payload.lstrip()[:4].lower() == b"<svg"
    )


def _suffix_for(url: str, href: str) -> str:
    for source in (url, href):
        lowered = source.lower()
        for suffix in IMAGE_SUFFIXES:
            if lowered.endswith(suffix):
                return suffix
    return ".jpg"


def _clear(figures_dir: Path) -> None:
    """Drop images from an earlier run before writing this one.

    Names are derived from figure labels, so a re-run that recovers fewer images
    would otherwise leave the extras behind and the capture would claim a figure
    count that disagrees with the directory. Only files are removed, and only
    from this one directory, so a nested path is left untouched.
    """
    if not figures_dir.is_dir():
        return
    for existing in figures_dir.iterdir():
        if existing.is_file():
            try:
                existing.unlink()
            except OSError:
                pass


def _safe_name(figure: Figure, index: int, suffix: str) -> str:
    """Filesystem-safe, sortable name derived from the figure label."""
    import re

    base = figure.label or figure.figure_id or f"{figure.kind}-{index}"
    slug = re.sub(r"[^A-Za-z0-9]+", "-", base).strip("-").lower() or f"item-{index}"
    prefix = "table" if figure.kind == "table" else "fig"
    if slug.startswith(("fig", "table")):
        return f"{index:02d}-{slug}{suffix}"
    return f"{index:02d}-{prefix}-{slug}{suffix}"


def _from_pdf(
    doc: Document, pdf_path: Path, figures_dir: Path, report: FigureReport, verbose: bool
) -> None:
    """Fallback: pull embedded raster images out of the PDF with PyMuPDF."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        report.notes.append("PyMuPDF not installed; PDF figure fallback unavailable")
        return

    try:
        document = fitz.open(pdf_path)
    except Exception as exc:  # noqa: BLE001 - fitz raises many concrete types
        report.notes.append(f"cannot open PDF: {exc}")
        return

    captions = [f for f in doc.figures] or []
    saved = 0
    try:
        for page_index in range(document.page_count):
            page = document[page_index]
            for image_index, info in enumerate(page.get_images(full=True)):
                xref = info[0]
                try:
                    pixmap = fitz.Pixmap(document, xref)
                except Exception:  # noqa: BLE001
                    continue
                if pixmap.width < 180 or pixmap.height < 180:
                    continue  # logos, icons, publisher furniture
                if pixmap.n - pixmap.alpha >= 4:
                    pixmap = fitz.Pixmap(fitz.csRGB, pixmap)

                saved += 1
                name = f"{saved:02d}-pdf-p{page_index + 1}-{image_index + 1}.png"
                pixmap.save(figures_dir / name)

                figure = captions[saved - 1] if saved <= len(captions) else Figure()
                entry = Figure(
                    label=figure.label or f"Image {saved}",
                    caption=figure.caption,
                    figure_id=figure.figure_id,
                    kind="figure",
                    local_path=f"figures/{name}",
                )
                report.saved.append(entry)
    finally:
        document.close()

    if saved:
        report.method = "pdf-embedded"
        report.notes.append(
            "Figures were extracted from the PDF, so captions are matched by order "
            "and may be approximate."
        )
    if verbose:
        print(f"  [figure] PDF fallback recovered {saved} images", flush=True)


def download_pdf(url: str, target: Path) -> Path | None:
    """Fetch the PDF itself, kept alongside the markdown for source checking."""
    try:
        payload = http.get_bytes(url)
    except http.FetchError:
        return None
    if not payload or not payload[:5].startswith(b"%PDF"):
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return target
