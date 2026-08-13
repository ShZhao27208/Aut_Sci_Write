"""Full-text retrieval, in descending order of fidelity.

Only four sources hand out machine-readable full text: PubMed Central and
Europe PMC (JATS XML), Elsevier (its own XML schema), and Springer Nature's
Open Access API (JATS). Everything else is metadata-only, so a paper that
misses all four falls back to a PDF download plus figure cropping.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import env, http, oa_package
from .metadata import PaperMetadata

PMC_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
EUROPEPMC_FULLTEXT = "https://www.ebi.ac.uk/europepmc/webservices/rest"
ELSEVIER_FULLTEXT = "https://api.elsevier.com/content/article/doi"
SPRINGER_OA_API = "https://api.springernature.com/openaccess/json"


@dataclass
class FullText:
    """Raw full text as retrieved, before any parsing."""

    source: str = ""
    format: str = ""  # "jats", "elsevier-xml", or "" when nothing was found
    xml: str = ""
    is_native_xml: bool = False
    pdf_url: str = ""
    attempts: list[str] = field(default_factory=list)
    errors: dict = field(default_factory=dict)

    @property
    def found(self) -> bool:
        return bool(self.xml)

    def note(self, source: str, outcome: str) -> None:
        self.attempts.append(f"{source}: {outcome}")


def retrieve(meta: PaperMetadata, *, verbose: bool = False) -> FullText:
    """Walk the full-text waterfall, stopping at the first source that answers."""
    result = FullText()
    providers = (
        ("pmc", _try_pmc),
        ("europepmc", _try_europepmc),
        ("elsevier", _try_elsevier),
        ("springer_oa", _try_springer_oa),
    )

    for name, provider in providers:
        if result.found:
            break
        try:
            provider(meta, result)
        except http.FetchError as exc:
            result.errors[name] = http.scrub(str(exc))
            result.note(name, "error")
        except Exception as exc:  # noqa: BLE001 - provider payloads vary
            result.errors[name] = f"{type(exc).__name__}: {http.scrub(str(exc))}"
            result.note(name, "error")
        if verbose:
            print(f"  [fulltext/{name}] {result.attempts[-1] if result.attempts else 'skipped'}",
                  flush=True)

    result.pdf_url = meta.oa_pdf_url
    return result


def _try_pmc(meta: PaperMetadata, result: FullText) -> None:
    """PMC JATS is the gold standard: full body, figure refs, structured refs."""
    if not meta.pmcid:
        result.note("pmc", "no PMCID")
        return
    params = {"db": "pmc", "id": meta.pmcid.replace("PMC", ""), "retmode": "xml"}
    if env.has("NCBI_API_KEY"):
        params["api_key"] = env.key("NCBI_API_KEY")
    if env.has("NCBI_EMAIL"):
        params["email"] = env.key("NCBI_EMAIL")
    params["tool"] = "sci-extract"

    xml = http.get_text(PMC_EFETCH, params=params)
    if not xml or "<article" not in xml:
        result.note("pmc", "no article element")
        return
    # An embargoed record returns a stub carrying only the citation.
    if "does not allow downloading of the full text" in xml or "<body" not in xml:
        result.note("pmc", "full text withheld (embargo or publisher opt-out)")
        return

    result.source = "pmc"
    result.format = "jats"
    result.xml = xml
    result.is_native_xml = True
    result.note("pmc", f"JATS XML, {len(xml)} bytes")


def _try_europepmc(meta: PaperMetadata, result: FullText) -> None:
    """Europe PMC mirrors PMC and additionally holds some non-PMC OA content."""
    pmcid = meta.pmcid
    if not pmcid:
        pmcid = _europepmc_lookup(meta)
    if not pmcid:
        result.note("europepmc", "no PMCID")
        return

    xml = http.get_text(f"{EUROPEPMC_FULLTEXT}/{pmcid}/fullTextXML")
    if not xml or "<article" not in xml or "<body" not in xml:
        result.note("europepmc", "no full text available")
        return

    result.source = "europepmc"
    result.format = "jats"
    result.xml = xml
    result.is_native_xml = True
    meta.pmcid = meta.pmcid or pmcid
    result.note("europepmc", f"JATS XML, {len(xml)} bytes")


def _europepmc_lookup(meta: PaperMetadata) -> str:
    """Europe PMC indexes some OA articles PMC itself does not; ask it directly."""
    if not meta.doi:
        return ""
    payload = http.get_json(
        f"{EUROPEPMC_FULLTEXT}/search",
        params={
            "query": f"DOI:{meta.doi}",
            "format": "json",
            "resultType": "core",
            "pageSize": "1",
        },
    )
    results = ((payload or {}).get("resultList") or {}).get("result") or []
    if not results:
        return ""
    record = results[0]
    if record.get("isOpenAccess") != "Y" and record.get("inEPMC") != "Y":
        return ""
    return str(record.get("pmcid") or "")


def _try_elsevier(meta: PaperMetadata, result: FullText) -> None:
    """Elsevier full text needs an entitled key; institutional token widens access."""
    api_key = env.key("ELSEVIER_API_KEY")
    if not api_key or not meta.doi:
        result.note("elsevier", "no key or DOI")
        return

    headers = {"X-ELS-APIKey": api_key, "Accept": "text/xml"}
    if env.has("ELSEVIER_INSTTOKEN"):
        headers["X-ELS-Insttoken"] = env.key("ELSEVIER_INSTTOKEN")

    xml = http.get_text(
        f"{ELSEVIER_FULLTEXT}/{meta.doi}", headers=headers, allow_404=True
    )
    if not xml or "<full-text-retrieval-response" not in xml:
        result.note("elsevier", "not entitled or no full text")
        return
    if "<xocs:rawtext" not in xml and "<ce:sections" not in xml and "<body" not in xml:
        result.note("elsevier", "metadata-only response")
        return

    result.source = "elsevier"
    result.format = "elsevier-xml"
    result.xml = xml
    result.is_native_xml = True
    result.note("elsevier", f"Elsevier XML, {len(xml)} bytes")


def _try_springer_oa(meta: PaperMetadata, result: FullText) -> None:
    """Springer's OA endpoint returns JATS for BMC, SpringerOpen, Nature OA."""
    api_key = env.springer_key()
    if not api_key or not meta.doi:
        result.note("springer_oa", "no key or DOI")
        return

    payload = http.get_json(
        SPRINGER_OA_API, params={"q": f"doi:{meta.doi}", "api_key": api_key, "p": "1"}
    )
    records = (payload or {}).get("records") or []
    if not records:
        result.note("springer_oa", "not in OA corpus")
        return

    xml = _springer_jats(records[0])
    if not xml:
        result.note("springer_oa", "record has no body")
        return

    result.source = "springer_oa"
    result.format = "jats"
    result.xml = xml
    result.is_native_xml = True
    result.note("springer_oa", f"JATS XML, {len(xml)} bytes")


def _springer_jats(record: dict) -> str:
    """Springer nests the JATS document under a `record.xml`-ish key by version."""
    for candidate in ("xml", "jats", "fullTextXml", "body"):
        value = record.get(candidate)
        if isinstance(value, str) and "<" in value and len(value) > 500:
            return value
    return ""


def resolve_pdf_urls(meta: PaperMetadata) -> list[str]:
    """PDF links worth trying, best first.

    All candidates are returned rather than only the top one. Publisher links
    from Unpaywall point at the version of record but are frequently refused to
    scripted clients, and when that happens a PMC copy of the same article still
    answers. The caller walks the list until a payload really starts with %PDF.
    """
    urls: list[str] = []
    if meta.oa_pdf_url:
        urls.append(meta.oa_pdf_url)
    if meta.pmcid:
        # The OA bucket serves the PDF as a plain object, so it comes before
        # ptpmcrender.fcgi, which redirects through an HTTP/2 endpoint that some
        # networks drop mid-stream. Both hold the published version, so they
        # outrank the arXiv preprint below.
        package = oa_package.fetch(meta.pmcid)
        if package.pdf_url:
            urls.append(package.pdf_url)
        urls.append(
            f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={meta.pmcid}&blobtype=pdf"
        )
    if meta.arxiv_id:
        urls.append(f"https://arxiv.org/pdf/{meta.arxiv_id}")
    seen: set = set()
    return [u for u in urls if not (u in seen or seen.add(u))]
