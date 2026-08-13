"""PMC Open Access cloud service client.

NLM distributes every Open Access / author-manuscript article as a set of
individual objects in a public, no-auth S3 bucket:

    PMC<id>.<version>/PMC<id>.<version>.json   manifest
    PMC<id>.<version>/PMC<id>.<version>.xml    JATS full text
    PMC<id>.<version>/PMC<id>.<version>.pdf    publisher PDF
    PMC<id>.<version>/<original-figure-name>   figures and supplements

This is the sanctioned bulk-access route and the only stable one. Scraping the
PMC article page instead trips a reCAPTCHA interstitial after a few requests,
and the legacy FTP ``oa_package`` tarballs were moved to ``deprecated/`` and are
scheduled for deletion in August 2026. The bucket gives us the JATS, the PDF and
every figure at publication resolution from one manifest lookup.

Docs: https://pmc.ncbi.nlm.nih.gov/tools/pmcaws/
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import http

BUCKET = "https://pmc-oa-opendata.s3.amazonaws.com"

# The bucket key carries a version suffix that is not derivable from the PMCID,
# so it has to be discovered through the list API.
_PREFIX_RE = re.compile(r"<Prefix>(PMC\d+\.(\d+))/</Prefix>")

_MEDIA_RE = re.compile(r"s3://[^/]+/[^/]+/([^\"?]+)")


@dataclass
class OAPackage:
    """Everything the cloud service knows about one article."""

    pmcid: str
    key: str = ""
    version: int = 0
    xml_url: str = ""
    pdf_url: str = ""
    text_url: str = ""
    media: dict[str, str] = field(default_factory=dict)
    title: str = ""
    doi: str = ""
    pmid: str = ""
    license_code: str = ""
    is_open_access: bool = False
    is_manuscript: bool = False
    is_retracted: bool = False
    errors: list[str] = field(default_factory=list)

    @property
    def found(self) -> bool:
        return bool(self.key)

    def media_for(self, filename: str) -> str | None:
        """Resolve a JATS graphic href to a bucket URL.

        JATS ``xlink:href`` values sometimes carry an extension and sometimes
        omit it, so fall back to a stem match. Prefer raster over vector when a
        stem has several representations, since the bucket ships the same figure
        as both ``.jpg`` and ``.gif`` in some packages and the JPEG is the
        higher-resolution one.
        """
        if not filename:
            return None
        direct = self.media.get(filename)
        if direct:
            return direct
        stem = filename.rsplit(".", 1)[0].lower()
        matches = [
            (name, url)
            for name, url in self.media.items()
            if name.rsplit(".", 1)[0].lower() == stem
        ]
        if not matches:
            return None
        matches.sort(key=lambda item: _media_rank(item[0]))
        return matches[0][1]


def _media_rank(name: str) -> int:
    lowered = name.lower()
    for rank, suffix in enumerate((".jpg", ".jpeg", ".png", ".tif", ".tiff", ".gif")):
        if lowered.endswith(suffix):
            return rank
    return 99


def fetch(pmcid: str, *, verbose: bool = False) -> OAPackage:
    """Look up an article in the OA bucket. Never raises."""
    normalized = _normalize(pmcid)
    pkg = OAPackage(pmcid=normalized)
    if not normalized:
        pkg.errors.append("no PMCID available")
        return pkg

    key = _discover_key(normalized, pkg)
    if not key:
        return pkg
    pkg.key = key
    try:
        pkg.version = int(key.split(".")[-1])
    except ValueError:
        pkg.version = 0

    manifest = _load_manifest(key, pkg)
    if manifest is None:
        return pkg

    pkg.title = str(manifest.get("title") or "")
    pkg.doi = str(manifest.get("doi") or "")
    pmid = manifest.get("pmid")
    pkg.pmid = str(pmid) if pmid else ""
    pkg.license_code = str(manifest.get("license_code") or "")
    pkg.is_open_access = bool(manifest.get("is_pmc_openaccess"))
    pkg.is_manuscript = bool(manifest.get("is_manuscript"))
    pkg.is_retracted = bool(manifest.get("is_retracted"))

    pkg.xml_url = _to_https(key, manifest.get("xml_url"))
    pkg.pdf_url = _to_https(key, manifest.get("pdf_url"))
    pkg.text_url = _to_https(key, manifest.get("text_url"))
    for entry in manifest.get("media_urls") or []:
        name = _basename(entry)
        if name:
            pkg.media[name] = _to_https(key, entry)

    if verbose:
        print(
            f"  [oa-bucket] {key} license={pkg.license_code or '?'} "
            f"media={len(pkg.media)} xml={'y' if pkg.xml_url else 'n'}"
        )
    return pkg


def _discover_key(pmcid: str, pkg: OAPackage) -> str:
    """Find the highest available version prefix for a PMCID."""
    url = f"{BUCKET}/?list-type=2&prefix={pmcid}.&delimiter=/&max-keys=20"
    try:
        listing = http.get_text(url)
    except http.FetchError as exc:
        pkg.errors.append(f"bucket listing failed: {exc}")
        return ""
    if not listing:
        pkg.errors.append("not in the PMC Open Access Subset")
        return ""
    versions = [
        (int(version), prefix) for prefix, version in _PREFIX_RE.findall(listing)
    ]
    if not versions:
        pkg.errors.append("not in the PMC Open Access Subset")
        return ""
    versions.sort()
    return versions[-1][1]


def _load_manifest(key: str, pkg: OAPackage) -> dict | None:
    url = f"{BUCKET}/{key}/{key}.json"
    try:
        data = http.get_json(url)
    except http.FetchError as exc:
        pkg.errors.append(f"manifest fetch failed: {exc}")
        return None
    if not isinstance(data, dict):
        pkg.errors.append("manifest missing or malformed")
        return None
    return data


def _to_https(key: str, s3_url: str | None) -> str:
    """Rewrite an ``s3://`` manifest URL to the public HTTPS endpoint.

    The manifest appends ``?md5=...`` as an integrity hint, not a query the
    bucket understands, so it is dropped.
    """
    name = _basename(s3_url)
    return f"{BUCKET}/{key}/{name}" if name else ""


def _basename(s3_url: str | None) -> str:
    if not s3_url:
        return ""
    match = _MEDIA_RE.match(s3_url)
    if match:
        return match.group(1)
    return s3_url.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]


def _normalize(pmcid: str) -> str:
    if not pmcid:
        return ""
    text = pmcid.strip().upper()
    text = text.removeprefix("PMC")
    digits = "".join(ch for ch in text if ch.isdigit())
    return f"PMC{digits}" if digits else ""
