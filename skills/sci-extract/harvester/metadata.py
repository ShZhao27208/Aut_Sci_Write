"""Cross-database metadata aggregation.

Queries every configured source for the same paper and merges the results into
one PaperMetadata record. Sources contribute what they are authoritative for:
Crossref for bibliographic truth, OpenAlex for topics and open-access status,
Semantic Scholar for citation context, PubMed for MeSH, WoS and Scopus for
indexed citation counts, Springer and Elsevier for publisher-side detail.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from . import env, http
from .identify import PaperRef, normalize_doi

CROSSREF_API = "https://api.crossref.org/works"
OPENALEX_API = "https://api.openalex.org/works"
S2_API = "https://api.semanticscholar.org/graph/v1/paper"
NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
UNPAYWALL_API = "https://api.unpaywall.org/v2"
ARXIV_API = "https://export.arxiv.org/api/query"
WOS_API = "https://api.clarivate.com/apis/wos-starter/v1/documents"
SCOPUS_API = "https://api.elsevier.com/content/abstract/doi"
SPRINGER_META_API = "https://api.springernature.com/meta/v2/json"
ELSEVIER_API = "https://api.elsevier.com/content/article/doi"


@dataclass
class Author:
    name: str = ""
    given: str = ""
    family: str = ""
    orcid: str = ""
    affiliations: List[str] = field(default_factory=list)
    is_corresponding: bool = False

    def display(self) -> str:
        if self.name:
            return self.name
        joined = f"{self.given} {self.family}".strip()
        return joined or "Unknown"


@dataclass
class PaperMetadata:
    """Union of everything every database knows about one paper."""

    doi: str = ""
    title: str = ""
    subtitle: str = ""
    abstract: str = ""
    authors: List[Author] = field(default_factory=list)
    journal: str = ""
    journal_abbrev: str = ""
    publisher: str = ""
    issn: List[str] = field(default_factory=list)
    volume: str = ""
    issue: str = ""
    pages: str = ""
    article_number: str = ""
    year: str = ""
    published_date: str = ""
    online_date: str = ""
    accepted_date: str = ""
    received_date: str = ""
    paper_type: str = ""
    language: str = ""
    keywords: List[str] = field(default_factory=list)
    mesh_terms: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    subjects: List[str] = field(default_factory=list)
    funders: List[Dict[str, Any]] = field(default_factory=list)
    license: str = ""
    is_open_access: bool = False
    oa_status: str = ""
    oa_pdf_url: str = ""
    pmid: str = ""
    pmcid: str = ""
    arxiv_id: str = ""
    scopus_id: str = ""
    wos_uid: str = ""
    citation_counts: Dict[str, int] = field(default_factory=dict)
    reference_count: int = 0
    references: List[Dict[str, str]] = field(default_factory=list)
    urls: Dict[str, str] = field(default_factory=dict)
    tldr: str = ""
    sources_consulted: List[str] = field(default_factory=list)
    source_errors: Dict[str, str] = field(default_factory=dict)
    raw_by_source: Dict[str, Any] = field(default_factory=dict)

    def author_names(self) -> List[str]:
        return [a.display() for a in self.authors]

    def first_author_family(self) -> str:
        if not self.authors:
            return "Unknown"
        first = self.authors[0]
        return first.family or first.display().split()[-1]

    def best_citation_count(self) -> Optional[int]:
        """Highest count across databases; they legitimately disagree."""
        return max(self.citation_counts.values()) if self.citation_counts else None

    def to_dict(self, include_raw: bool = False) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "doi": self.doi,
            "title": self.title,
            "subtitle": self.subtitle,
            "abstract": self.abstract,
            "authors": [
                {
                    "name": a.display(),
                    "given": a.given,
                    "family": a.family,
                    "orcid": a.orcid,
                    "affiliations": a.affiliations,
                    "is_corresponding": a.is_corresponding,
                }
                for a in self.authors
            ],
            "journal": self.journal,
            "journal_abbrev": self.journal_abbrev,
            "publisher": self.publisher,
            "issn": self.issn,
            "volume": self.volume,
            "issue": self.issue,
            "pages": self.pages,
            "article_number": self.article_number,
            "year": self.year,
            "published_date": self.published_date,
            "online_date": self.online_date,
            "accepted_date": self.accepted_date,
            "received_date": self.received_date,
            "paper_type": self.paper_type,
            "language": self.language,
            "keywords": self.keywords,
            "mesh_terms": self.mesh_terms,
            "topics": self.topics,
            "subjects": self.subjects,
            "funders": self.funders,
            "license": self.license,
            "is_open_access": self.is_open_access,
            "oa_status": self.oa_status,
            "oa_pdf_url": self.oa_pdf_url,
            "identifiers": {
                "pmid": self.pmid,
                "pmcid": self.pmcid,
                "arxiv_id": self.arxiv_id,
                "scopus_id": self.scopus_id,
                "wos_uid": self.wos_uid,
            },
            "citation_counts": self.citation_counts,
            "reference_count": self.reference_count,
            "references": self.references,
            "urls": self.urls,
            "tldr": self.tldr,
            "sources_consulted": self.sources_consulted,
            "source_errors": self.source_errors,
        }
        if include_raw:
            payload["raw_by_source"] = self.raw_by_source
        return payload


def _first_nonempty(*values: str) -> str:
    for value in values:
        if value:
            return str(value).strip()
    return ""


def _merge_list(target: List[str], incoming: List[str]) -> None:
    """Append unseen items, comparing case-insensitively, order preserved."""
    seen = {item.lower() for item in target}
    for item in incoming:
        cleaned = (item or "").strip()
        if cleaned and cleaned.lower() not in seen:
            target.append(cleaned)
            seen.add(cleaned.lower())


def _strip_jats(text: str) -> str:
    """Crossref and PubMed abstracts arrive with inline JATS tags."""
    import re

    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", " ", text)
    cleaned = cleaned.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    return re.sub(r"\s+", " ", cleaned).strip()


def _date_from_parts(parts: Any) -> str:
    """Crossref date-parts `[[2023, 4, 17]]` to `2023-04-17`."""
    try:
        values = parts["date-parts"][0] if isinstance(parts, dict) else parts[0]
    except (KeyError, IndexError, TypeError):
        return ""
    if not values:
        return ""
    padded = [str(values[0])]
    for element in values[1:3]:
        padded.append(f"{int(element):02d}")
    return "-".join(padded)


# ---------------------------------------------------------------- Crossref ---

def fetch_crossref(doi: str, meta: PaperMetadata) -> None:
    """Authoritative bibliographic record: title, journal, pagination, dates."""
    payload = http.get_json(f"{CROSSREF_API}/{doi}", params=_crossref_params())
    if not payload or "message" not in payload:
        return
    work = payload["message"]
    meta.raw_by_source["crossref"] = work
    meta.sources_consulted.append("crossref")

    titles = work.get("title") or []
    subtitles = work.get("subtitle") or []
    meta.title = _first_nonempty(meta.title, titles[0] if titles else "")
    meta.subtitle = _first_nonempty(meta.subtitle, subtitles[0] if subtitles else "")
    meta.abstract = _first_nonempty(meta.abstract, _strip_jats(work.get("abstract", "")))

    containers = work.get("container-title") or []
    short_containers = work.get("short-container-title") or []
    meta.journal = _first_nonempty(meta.journal, containers[0] if containers else "")
    meta.journal_abbrev = _first_nonempty(
        meta.journal_abbrev, short_containers[0] if short_containers else ""
    )
    meta.publisher = _first_nonempty(meta.publisher, work.get("publisher", ""))
    meta.volume = _first_nonempty(meta.volume, work.get("volume", ""))
    meta.issue = _first_nonempty(meta.issue, work.get("issue", ""))
    meta.pages = _first_nonempty(meta.pages, work.get("page", ""))
    meta.article_number = _first_nonempty(meta.article_number, work.get("article-number", ""))
    meta.paper_type = _first_nonempty(meta.paper_type, work.get("type", ""))
    meta.language = _first_nonempty(meta.language, work.get("language", ""))
    meta.reference_count = meta.reference_count or int(work.get("reference-count") or 0)

    _merge_list(meta.issn, work.get("ISSN") or [])
    _merge_list(meta.subjects, work.get("subject") or [])

    published = _date_from_parts(work.get("published") or work.get("issued") or {})
    meta.published_date = _first_nonempty(meta.published_date, published)
    meta.online_date = _first_nonempty(
        meta.online_date, _date_from_parts(work.get("published-online") or {})
    )
    meta.year = _first_nonempty(meta.year, published[:4] if published else "")

    licenses = work.get("license") or []
    if licenses and not meta.license:
        meta.license = licenses[0].get("URL", "")

    for funder in work.get("funder") or []:
        entry = {
            "name": funder.get("name", ""),
            "doi": funder.get("DOI", ""),
            "awards": funder.get("award") or [],
        }
        if entry["name"] and entry not in meta.funders:
            meta.funders.append(entry)

    if not meta.authors:
        meta.authors = [_crossref_author(a) for a in work.get("author") or []]

    if work.get("URL"):
        meta.urls.setdefault("doi", work["URL"])
    _collect_crossref_references(work, meta)


def _crossref_params() -> Dict[str, str]:
    email = env.contact_email()
    return {"mailto": email} if email else {}


def _crossref_author(entry: Dict[str, Any]) -> Author:
    affiliations = [
        a.get("name", "") for a in entry.get("affiliation") or [] if a.get("name")
    ]
    return Author(
        given=entry.get("given", ""),
        family=entry.get("family", ""),
        name=entry.get("name", ""),
        orcid=(entry.get("ORCID") or "").replace("http://orcid.org/", "").replace(
            "https://orcid.org/", ""
        ),
        affiliations=affiliations,
    )


def _collect_crossref_references(work: Dict[str, Any], meta: PaperMetadata) -> None:
    """Reference list is often the only machine-readable citation graph we get."""
    if meta.references:
        return
    for ref in work.get("reference") or []:
        entry = {
            "key": ref.get("key", ""),
            "doi": ref.get("DOI", ""),
            "title": ref.get("article-title", "") or ref.get("volume-title", ""),
            "journal": ref.get("journal-title", ""),
            "author": ref.get("author", ""),
            "year": ref.get("year", ""),
            "unstructured": ref.get("unstructured", ""),
        }
        if any(entry.values()):
            meta.references.append(entry)


# ---------------------------------------------------------------- OpenAlex ---

def fetch_openalex(doi: str, meta: PaperMetadata) -> None:
    """Topics, concepts, open-access location, and cross-database IDs."""
    email = env.key("OPENALEX_EMAIL") or env.contact_email()
    params = {"mailto": email} if email else {}
    work = http.get_json(f"{OPENALEX_API}/https://doi.org/{doi}", params=params)
    if not work or work.get("id") is None:
        return
    meta.raw_by_source["openalex"] = work
    meta.sources_consulted.append("openalex")

    meta.title = _first_nonempty(meta.title, work.get("title") or work.get("display_name") or "")
    meta.year = _first_nonempty(meta.year, str(work.get("publication_year") or ""))
    meta.published_date = _first_nonempty(meta.published_date, work.get("publication_date") or "")
    meta.paper_type = _first_nonempty(meta.paper_type, work.get("type") or "")
    meta.language = _first_nonempty(meta.language, work.get("language") or "")

    if work.get("cited_by_count") is not None:
        meta.citation_counts["openalex"] = int(work["cited_by_count"])
    meta.reference_count = meta.reference_count or len(work.get("referenced_works") or [])

    _merge_list(meta.topics, [t.get("display_name", "") for t in work.get("topics") or []])
    _merge_list(
        meta.topics, [c.get("display_name", "") for c in (work.get("concepts") or [])[:8]]
    )
    _merge_list(meta.keywords, [k.get("display_name", "") for k in work.get("keywords") or []])

    _openalex_venue(work, meta)
    _openalex_open_access(work, meta)
    _openalex_ids(work, meta)

    if not meta.abstract and work.get("abstract_inverted_index"):
        meta.abstract = _rebuild_inverted_abstract(work["abstract_inverted_index"])
    if not meta.authors:
        meta.authors = [_openalex_author(a) for a in work.get("authorships") or []]

    for grant in work.get("grants") or []:
        entry = {
            "name": grant.get("funder_display_name", ""),
            "doi": "",
            "awards": [grant["award_id"]] if grant.get("award_id") else [],
        }
        if entry["name"] and entry not in meta.funders:
            meta.funders.append(entry)


def _openalex_venue(work: Dict[str, Any], meta: PaperMetadata) -> None:
    location = work.get("primary_location") or {}
    source = location.get("source") or {}
    meta.journal = _first_nonempty(meta.journal, source.get("display_name", ""))
    meta.publisher = _first_nonempty(meta.publisher, source.get("host_organization_name", ""))
    _merge_list(meta.issn, source.get("issn") or [])

    biblio = work.get("biblio") or {}
    meta.volume = _first_nonempty(meta.volume, biblio.get("volume") or "")
    meta.issue = _first_nonempty(meta.issue, biblio.get("issue") or "")
    if not meta.pages and biblio.get("first_page"):
        last = biblio.get("last_page") or ""
        meta.pages = f"{biblio['first_page']}-{last}" if last else str(biblio["first_page"])


def _openalex_open_access(work: Dict[str, Any], meta: PaperMetadata) -> None:
    """OpenAlex is the most reliable single answer on OA status and PDF location."""
    oa = work.get("open_access") or {}
    if oa.get("is_oa"):
        meta.is_open_access = True
    meta.oa_status = _first_nonempty(meta.oa_status, oa.get("oa_status") or "")
    if oa.get("oa_url"):
        meta.urls.setdefault("openalex_oa", oa["oa_url"])

    best = work.get("best_oa_location") or {}
    meta.oa_pdf_url = _first_nonempty(
        meta.oa_pdf_url, best.get("pdf_url") or "", oa.get("oa_url") or ""
    )
    if best.get("license"):
        meta.license = _first_nonempty(meta.license, best["license"])
    if best.get("landing_page_url"):
        meta.urls.setdefault("oa_landing", best["landing_page_url"])


def _openalex_ids(work: Dict[str, Any], meta: PaperMetadata) -> None:
    ids = work.get("ids") or {}
    if ids.get("pmid"):
        meta.pmid = _first_nonempty(meta.pmid, str(ids["pmid"]).rsplit("/", 1)[-1])
    if ids.get("pmcid"):
        meta.pmcid = _first_nonempty(meta.pmcid, str(ids["pmcid"]).rsplit("/", 1)[-1].upper())
    if ids.get("openalex"):
        meta.urls.setdefault("openalex", ids["openalex"])


def _rebuild_inverted_abstract(index: Dict[str, List[int]]) -> str:
    """OpenAlex stores abstracts as {word: [positions]} for licensing reasons."""
    positions: Dict[int, str] = {}
    for word, spots in index.items():
        for spot in spots:
            positions[spot] = word
    if not positions:
        return ""
    return " ".join(positions[i] for i in sorted(positions))


def _openalex_author(entry: Dict[str, Any]) -> Author:
    author = entry.get("author") or {}
    name = author.get("display_name", "")
    parts = name.split()
    return Author(
        name=name,
        given=" ".join(parts[:-1]) if len(parts) > 1 else "",
        family=parts[-1] if parts else "",
        orcid=(author.get("orcid") or "").replace("https://orcid.org/", ""),
        affiliations=[i.get("display_name", "") for i in entry.get("institutions") or []],
        is_corresponding=bool(entry.get("is_corresponding")),
    )


# -------------------------------------------------------- Semantic Scholar ---

S2_FIELDS = (
    "title,abstract,venue,year,publicationDate,publicationTypes,journal,"
    "citationCount,influentialCitationCount,referenceCount,fieldsOfStudy,"
    "tldr,openAccessPdf,externalIds,authors.name,authors.affiliations"
)


def fetch_semantic_scholar(doi: str, meta: PaperMetadata) -> None:
    """Adds a TLDR summary, influential-citation count, and fields of study."""
    headers = {}
    api_key = env.key("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key
    work = http.get_json(f"{S2_API}/DOI:{doi}", params={"fields": S2_FIELDS}, headers=headers)
    if not work:
        return
    meta.raw_by_source["semantic_scholar"] = work
    meta.sources_consulted.append("semantic_scholar")

    meta.title = _first_nonempty(meta.title, work.get("title") or "")
    meta.abstract = _first_nonempty(meta.abstract, work.get("abstract") or "")
    meta.journal = _first_nonempty(meta.journal, (work.get("journal") or {}).get("name", ""),
                                   work.get("venue") or "")
    meta.year = _first_nonempty(meta.year, str(work.get("year") or ""))
    meta.published_date = _first_nonempty(meta.published_date, work.get("publicationDate") or "")

    if work.get("citationCount") is not None:
        meta.citation_counts["semantic_scholar"] = int(work["citationCount"])
    if work.get("influentialCitationCount") is not None:
        meta.citation_counts["s2_influential"] = int(work["influentialCitationCount"])
    meta.reference_count = meta.reference_count or int(work.get("referenceCount") or 0)

    _merge_list(meta.topics, work.get("fieldsOfStudy") or [])
    types = work.get("publicationTypes") or []
    meta.paper_type = _first_nonempty(meta.paper_type, types[0] if types else "")

    tldr = work.get("tldr") or {}
    meta.tldr = _first_nonempty(meta.tldr, tldr.get("text") or "")

    oa_pdf = work.get("openAccessPdf") or {}
    if oa_pdf.get("url"):
        meta.oa_pdf_url = _first_nonempty(meta.oa_pdf_url, oa_pdf["url"])
        meta.is_open_access = True

    external = work.get("externalIds") or {}
    meta.pmid = _first_nonempty(meta.pmid, str(external.get("PubMed") or ""))
    if external.get("PubMedCentral"):
        meta.pmcid = _first_nonempty(meta.pmcid, f"PMC{external['PubMedCentral']}".replace("PMCPMC", "PMC"))
    meta.arxiv_id = _first_nonempty(meta.arxiv_id, str(external.get("ArXiv") or ""))

    if not meta.authors:
        for entry in work.get("authors") or []:
            name = entry.get("name", "")
            parts = name.split()
            meta.authors.append(
                Author(
                    name=name,
                    given=" ".join(parts[:-1]) if len(parts) > 1 else "",
                    family=parts[-1] if parts else "",
                    affiliations=entry.get("affiliations") or [],
                )
            )


# ------------------------------------------------------------------ PubMed ---

def _ncbi_params(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    params = {"tool": "sci-extract"}
    if env.has("NCBI_API_KEY"):
        params["api_key"] = env.key("NCBI_API_KEY")
    if env.has("NCBI_EMAIL"):
        params["email"] = env.key("NCBI_EMAIL")
    params.update(extra or {})
    return params


def resolve_pubmed_ids(meta: PaperMetadata) -> None:
    """Fill in PMID and PMCID via the NCBI ID converter, needed for JATS access."""
    if meta.pmid and meta.pmcid:
        return
    probe = meta.pmcid or meta.pmid or meta.doi
    if not probe:
        return
    payload = http.get_json(
        "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/",
        params={"ids": probe, "format": "json", "tool": "sci-extract"},
    )
    for record in (payload or {}).get("records") or []:
        if record.get("pmid"):
            meta.pmid = _first_nonempty(meta.pmid, str(record["pmid"]))
        if record.get("pmcid"):
            meta.pmcid = _first_nonempty(meta.pmcid, str(record["pmcid"]).upper())
        if record.get("doi"):
            meta.doi = _first_nonempty(meta.doi, str(record["doi"]))


def fetch_pubmed(meta: PaperMetadata) -> None:
    """MeSH descriptors, publication types, and structured author affiliations."""
    if not meta.pmid:
        return
    xml = http.get_text(
        f"{NCBI_BASE}/efetch.fcgi",
        params=_ncbi_params({"db": "pubmed", "id": meta.pmid, "retmode": "xml"}),
    )
    if not xml:
        return
    meta.sources_consulted.append("pubmed")
    meta.raw_by_source["pubmed_xml"] = xml
    _parse_pubmed_xml(xml, meta)


def _parse_pubmed_xml(xml: str, meta: PaperMetadata) -> None:
    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        meta.source_errors["pubmed"] = "unparseable XML"
        return

    article = root.find(".//PubmedArticle")
    if article is None:
        return

    _merge_list(
        meta.mesh_terms,
        [d.get("UI", "") and (d.text or "") for d in article.findall(".//MeshHeading/DescriptorName")],
    )
    _merge_list(meta.keywords, [k.text or "" for k in article.findall(".//Keyword")])
    types = [t.text or "" for t in article.findall(".//PublicationType")]
    meta.paper_type = _first_nonempty(meta.paper_type, types[0] if types else "")

    if not meta.abstract:
        chunks = []
        for node in article.findall(".//Abstract/AbstractText"):
            label = node.get("Label")
            body = "".join(node.itertext()).strip()
            chunks.append(f"{label}: {body}" if label else body)
        meta.abstract = " ".join(c for c in chunks if c)

    journal = article.find(".//Journal/Title")
    if journal is not None:
        meta.journal = _first_nonempty(meta.journal, journal.text or "")
    abbrev = article.find(".//Journal/ISOAbbreviation")
    if abbrev is not None:
        meta.journal_abbrev = _first_nonempty(meta.journal_abbrev, abbrev.text or "")

    _merge_list(
        meta.subjects,
        [c.text or "" for c in article.findall(".//ChemicalList/Chemical/NameOfSubstance")],
    )
    _pubmed_affiliations(article, meta)


def _pubmed_affiliations(article, meta: PaperMetadata) -> None:
    """PubMed carries affiliation strings Crossref usually omits."""
    if not meta.authors:
        return
    by_family = {a.family.lower(): a for a in meta.authors if a.family}
    for node in article.findall(".//Author"):
        family_node = node.find("LastName")
        if family_node is None or not family_node.text:
            continue
        target = by_family.get(family_node.text.lower())
        if target is None:
            continue
        affiliations = [
            "".join(a.itertext()).strip()
            for a in node.findall("AffiliationInfo/Affiliation")
        ]
        _merge_list(target.affiliations, affiliations)


# --------------------------------------------------------------- Unpaywall ---

def fetch_unpaywall(doi: str, meta: PaperMetadata) -> None:
    """Independent OA verdict plus a legal PDF location when one exists."""
    email = env.key("UNPAYWALL_EMAIL") or env.contact_email()
    if not email:
        return
    work = http.get_json(f"{UNPAYWALL_API}/{doi}", params={"email": email})
    if not work:
        return
    meta.sources_consulted.append("unpaywall")
    meta.raw_by_source["unpaywall"] = work

    if work.get("is_oa"):
        meta.is_open_access = True
    meta.oa_status = _first_nonempty(meta.oa_status, work.get("oa_status") or "")
    meta.journal = _first_nonempty(meta.journal, work.get("journal_name") or "")
    meta.publisher = _first_nonempty(meta.publisher, work.get("publisher") or "")

    best = work.get("best_oa_location") or {}
    meta.oa_pdf_url = _first_nonempty(
        meta.oa_pdf_url, best.get("url_for_pdf") or "", best.get("url") or ""
    )
    if best.get("license"):
        meta.license = _first_nonempty(meta.license, best["license"])
    if best.get("url"):
        meta.urls.setdefault("unpaywall_oa", best["url"])


# ------------------------------------------------------------------- arXiv ---

def fetch_arxiv(arxiv_id: str, meta: PaperMetadata) -> None:
    """Preprint metadata; also the only place to get the arXiv category taxonomy."""
    import xml.etree.ElementTree as ET

    xml = http.get_text(ARXIV_API, params={"id_list": arxiv_id, "max_results": "1"})
    if not xml:
        return
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        meta.source_errors["arxiv"] = "unparseable Atom feed"
        return

    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    entry = root.find("atom:entry", ns)
    if entry is None:
        return
    meta.sources_consulted.append("arxiv")
    meta.raw_by_source["arxiv_xml"] = xml
    meta.arxiv_id = _first_nonempty(meta.arxiv_id, arxiv_id)

    title = entry.find("atom:title", ns)
    if title is not None and title.text:
        meta.title = _first_nonempty(meta.title, " ".join(title.text.split()))
    summary = entry.find("atom:summary", ns)
    if summary is not None and summary.text:
        meta.abstract = _first_nonempty(meta.abstract, " ".join(summary.text.split()))

    published = entry.find("atom:published", ns)
    if published is not None and published.text:
        meta.published_date = _first_nonempty(meta.published_date, published.text[:10])
        meta.year = _first_nonempty(meta.year, published.text[:4])

    doi_node = entry.find("arxiv:doi", ns)
    if doi_node is not None and doi_node.text:
        meta.doi = _first_nonempty(meta.doi, normalize_doi(doi_node.text))
    journal_ref = entry.find("arxiv:journal_ref", ns)
    if journal_ref is not None and journal_ref.text:
        meta.urls.setdefault("arxiv_journal_ref", journal_ref.text.strip())

    _merge_list(meta.topics, [c.get("term", "") for c in entry.findall("atom:category", ns)])
    if not meta.authors:
        for node in entry.findall("atom:author", ns):
            name_node = node.find("atom:name", ns)
            name = (name_node.text or "").strip() if name_node is not None else ""
            parts = name.split()
            affiliation = node.find("arxiv:affiliation", ns)
            meta.authors.append(
                Author(
                    name=name,
                    given=" ".join(parts[:-1]) if len(parts) > 1 else "",
                    family=parts[-1] if parts else "",
                    affiliations=[affiliation.text.strip()]
                    if affiliation is not None and affiliation.text
                    else [],
                )
            )
    meta.urls.setdefault("arxiv_abs", f"https://arxiv.org/abs/{arxiv_id}")
    meta.oa_pdf_url = _first_nonempty(meta.oa_pdf_url, f"https://arxiv.org/pdf/{arxiv_id}")
    meta.is_open_access = True
    meta.paper_type = _first_nonempty(meta.paper_type, "preprint")


# --------------------------------------------------- Web of Science (keyed) ---

def fetch_wos(doi: str, meta: PaperMetadata) -> None:
    """SCI-indexed record with the times-cited count used for quality filtering."""
    api_key = env.key("WOS_API_KEY")
    if not api_key:
        return
    payload = http.get_json(
        WOS_API,
        params={"q": f"DO=({doi})", "limit": "1", "db": "WOS"},
        headers={"X-ApiKey": api_key},
    )
    hits = (payload or {}).get("hits") or []
    if not hits:
        return
    record = hits[0]
    meta.sources_consulted.append("wos")
    meta.raw_by_source["wos"] = record

    meta.wos_uid = _first_nonempty(meta.wos_uid, record.get("uid") or "")
    citations = record.get("citations") or []
    for entry in citations:
        if entry.get("count") is not None:
            meta.citation_counts["wos"] = int(entry["count"])
            break

    source = record.get("source") or {}
    meta.journal = _first_nonempty(meta.journal, source.get("sourceTitle") or "")
    meta.volume = _first_nonempty(meta.volume, source.get("volume") or "")
    meta.issue = _first_nonempty(meta.issue, source.get("issue") or "")
    meta.year = _first_nonempty(meta.year, str(source.get("publishYear") or ""))
    types = record.get("types") or []
    meta.paper_type = _first_nonempty(meta.paper_type, types[0] if types else "")
    _merge_list(meta.keywords, (record.get("keywords") or {}).get("authorKeywords") or [])
    if meta.wos_uid:
        meta.urls.setdefault(
            "wos", f"https://www.webofscience.com/wos/woscc/full-record/{meta.wos_uid}"
        )


# ------------------------------------------------------------ Scopus (keyed) ---

def fetch_scopus(doi: str, meta: PaperMetadata) -> None:
    """Elsevier abstract record: Scopus ID, cited-by count, author keywords."""
    api_key = env.key("SCOPUS_API_KEY")
    if not api_key:
        return
    headers = {"X-ELS-APIKey": api_key, "Accept": "application/json"}
    if env.has("ELSEVIER_INSTTOKEN"):
        headers["X-ELS-Insttoken"] = env.key("ELSEVIER_INSTTOKEN")
    payload = http.get_json(f"{SCOPUS_API}/{doi}", headers=headers)
    record = ((payload or {}).get("abstracts-retrieval-response")) or {}
    if not record:
        return
    meta.sources_consulted.append("scopus")
    meta.raw_by_source["scopus"] = record

    core = record.get("coredata") or {}
    meta.scopus_id = _first_nonempty(meta.scopus_id, str(core.get("dc:identifier") or ""))
    if core.get("citedby-count") is not None:
        try:
            meta.citation_counts["scopus"] = int(core["citedby-count"])
        except (TypeError, ValueError):
            pass
    meta.title = _first_nonempty(meta.title, core.get("dc:title") or "")
    meta.abstract = _first_nonempty(meta.abstract, _strip_jats(core.get("dc:description") or ""))
    meta.journal = _first_nonempty(meta.journal, core.get("prism:publicationName") or "")
    meta.publisher = _first_nonempty(meta.publisher, core.get("dc:publisher") or "")
    meta.volume = _first_nonempty(meta.volume, core.get("prism:volume") or "")
    meta.pages = _first_nonempty(meta.pages, core.get("prism:pageRange") or "")
    meta.paper_type = _first_nonempty(meta.paper_type, core.get("subtypeDescription") or "")
    if core.get("openaccess") == "1":
        meta.is_open_access = True

    keywords = record.get("authkeywords") or {}
    entries = keywords.get("author-keyword") if isinstance(keywords, dict) else None
    if isinstance(entries, list):
        _merge_list(meta.keywords, [e.get("$", "") for e in entries if isinstance(e, dict)])


# ---------------------------------------------------------- Springer (keyed) ---

def fetch_springer(doi: str, meta: PaperMetadata) -> None:
    """Publisher-side record; also the gateway to Springer OA full text."""
    api_key = env.springer_key()
    if not api_key:
        return
    payload = http.get_json(
        SPRINGER_META_API, params={"q": f"doi:{doi}", "api_key": api_key, "p": "1"}
    )
    records = (payload or {}).get("records") or []
    if not records:
        return
    record = records[0]
    meta.sources_consulted.append("springer")
    meta.raw_by_source["springer"] = record

    meta.title = _first_nonempty(meta.title, record.get("title") or "")
    meta.abstract = _first_nonempty(meta.abstract, _strip_jats(record.get("abstract") or ""))
    meta.journal = _first_nonempty(meta.journal, record.get("publicationName") or "")
    meta.publisher = _first_nonempty(meta.publisher, record.get("publisher") or "")
    meta.volume = _first_nonempty(meta.volume, record.get("volume") or "")
    meta.issue = _first_nonempty(meta.issue, record.get("number") or "")
    meta.published_date = _first_nonempty(meta.published_date, record.get("publicationDate") or "")
    meta.paper_type = _first_nonempty(meta.paper_type, record.get("contentType") or "")
    meta.language = _first_nonempty(meta.language, record.get("language") or "")
    if record.get("openaccess") in ("true", True):
        meta.is_open_access = True

    for issn_key in ("issn", "eIssn", "printIssn", "electronicIssn"):
        if record.get(issn_key):
            _merge_list(meta.issn, [record[issn_key]])
    _merge_list(meta.keywords, record.get("keyword") or [])
    _merge_list(
        meta.subjects, [s for s in record.get("subjects") or [] if isinstance(s, str)]
    )
    for url_entry in record.get("url") or []:
        if isinstance(url_entry, dict) and url_entry.get("value"):
            meta.urls.setdefault("springer", url_entry["value"])


# ---------------------------------------------------------- Elsevier (keyed) ---

def fetch_elsevier(doi: str, meta: PaperMetadata) -> None:
    """ScienceDirect record; the same key unlocks full-text XML later."""
    api_key = env.key("ELSEVIER_API_KEY")
    if not api_key:
        return
    headers = {"X-ELS-APIKey": api_key, "Accept": "application/json"}
    if env.has("ELSEVIER_INSTTOKEN"):
        headers["X-ELS-Insttoken"] = env.key("ELSEVIER_INSTTOKEN")
    payload = http.get_json(f"{ELSEVIER_API}/{doi}", params={"view": "META"}, headers=headers)
    core = (((payload or {}).get("full-text-retrieval-response")) or {}).get("coredata") or {}
    if not core:
        return
    meta.sources_consulted.append("elsevier")
    meta.raw_by_source["elsevier"] = core

    meta.title = _first_nonempty(meta.title, core.get("dc:title") or "")
    meta.abstract = _first_nonempty(meta.abstract, _strip_jats(core.get("dc:description") or ""))
    meta.journal = _first_nonempty(meta.journal, core.get("prism:publicationName") or "")
    meta.publisher = _first_nonempty(meta.publisher, core.get("prism:publisher") or "")
    meta.volume = _first_nonempty(meta.volume, core.get("prism:volume") or "")
    meta.pages = _first_nonempty(meta.pages, core.get("prism:pageRange") or "")
    meta.published_date = _first_nonempty(meta.published_date, core.get("prism:coverDate") or "")
    if core.get("openaccess") in ("1", 1, True):
        meta.is_open_access = True
    if core.get("prism:copyright"):
        meta.license = _first_nonempty(meta.license, core["prism:copyright"])


# ------------------------------------------------------------- orchestration ---

# Order matters: Crossref establishes the bibliographic baseline, then each later
# source only fills gaps. Keyed sources run last so a missing key costs nothing.
_DOI_PIPELINE = (
    ("crossref", fetch_crossref),
    ("openalex", fetch_openalex),
    ("semantic_scholar", fetch_semantic_scholar),
    ("unpaywall", fetch_unpaywall),
    ("wos", fetch_wos),
    ("scopus", fetch_scopus),
    ("springer", fetch_springer),
    ("elsevier", fetch_elsevier),
)


def collect(ref: PaperRef, *, verbose: bool = False) -> PaperMetadata:
    """Query every reachable source for one paper and merge into one record."""
    meta = PaperMetadata(
        doi=ref.doi, arxiv_id=ref.arxiv_id, pmid=ref.pmid, pmcid=ref.pmcid, title=ref.title
    )

    if ref.arxiv_id:
        _run("arxiv", lambda: fetch_arxiv(ref.arxiv_id, meta), meta, verbose)

    if not meta.doi and (meta.pmid or meta.pmcid):
        _run("idconv", lambda: resolve_pubmed_ids(meta), meta, verbose)

    if meta.doi:
        for name, handler in _DOI_PIPELINE:
            _run(name, lambda h=handler: h(meta.doi, meta), meta, verbose)

    _run("idconv", lambda: resolve_pubmed_ids(meta), meta, verbose)
    if meta.pmid:
        _run("pubmed", lambda: fetch_pubmed(meta), meta, verbose)

    if meta.arxiv_id and "arxiv" not in meta.sources_consulted:
        _run("arxiv", lambda: fetch_arxiv(meta.arxiv_id, meta), meta, verbose)

    _finalize(meta)
    return meta


def _run(name: str, action, meta: PaperMetadata, verbose: bool) -> None:
    """Run one source fetch; a single source failing must not abort the harvest."""
    try:
        action()
    except http.FetchError as exc:
        meta.source_errors[name] = http.scrub(str(exc))
    except Exception as exc:  # noqa: BLE001 - third-party shapes vary widely
        meta.source_errors[name] = f"{type(exc).__name__}: {http.scrub(str(exc))}"
    if verbose:
        status = meta.source_errors.get(name, "ok")
        print(f"  [{name}] {status}", flush=True)


def _finalize(meta: PaperMetadata) -> None:
    """Derive fields that depend on the merged whole, and dedupe bookkeeping."""
    seen: List[str] = []
    for source in meta.sources_consulted:
        if source not in seen:
            seen.append(source)
    meta.sources_consulted = seen

    if not meta.year and meta.published_date:
        meta.year = meta.published_date[:4]
    if meta.doi:
        meta.urls.setdefault("doi", f"https://doi.org/{meta.doi}")
    if meta.pmcid:
        meta.urls.setdefault(
            "pmc", f"https://www.ncbi.nlm.nih.gov/pmc/articles/{meta.pmcid}/"
        )
    if meta.pmid:
        meta.urls.setdefault("pubmed", f"https://pubmed.ncbi.nlm.nih.gov/{meta.pmid}/")
    if meta.title:
        meta.title = " ".join(meta.title.split())


# ------------------------------------------------------------------- search ---

def search(query: str, *, limit: int = 10, exact_title: bool = False) -> List[Dict[str, Any]]:
    """Resolve a title or keyword query to candidate papers via OpenAlex + Crossref.

    Both are keyless, so search always works regardless of configuration.
    Results are deduplicated by DOI and ranked by title similarity when the
    caller signalled that the input was a full title.
    """
    candidates: List[Dict[str, Any]] = []
    for provider in (_search_openalex, _search_crossref):
        try:
            candidates.extend(provider(query, limit))
        except (http.FetchError, Exception):  # noqa: BLE001
            continue

    merged: Dict[str, Dict[str, Any]] = {}
    for item in candidates:
        key = (item.get("doi") or item.get("title", "")).lower()
        if not key:
            continue
        existing = merged.get(key)
        if existing is None:
            merged[key] = item
        elif (item.get("cited_by") or 0) > (existing.get("cited_by") or 0):
            merged[key] = item

    results = list(merged.values())
    if exact_title:
        target = _fold(query)
        results.sort(key=lambda r: _title_distance(_fold(r.get("title", "")), target))
    else:
        results.sort(key=lambda r: -(r.get("cited_by") or 0))
    return results[:limit]


def _search_openalex(query: str, limit: int) -> List[Dict[str, Any]]:
    email = env.key("OPENALEX_EMAIL") or env.contact_email()
    params = {"search": query, "per-page": str(min(limit * 2, 50))}
    if email:
        params["mailto"] = email
    payload = http.get_json(OPENALEX_API, params=params) or {}
    out = []
    for work in payload.get("results") or []:
        location = (work.get("primary_location") or {}).get("source") or {}
        out.append(
            {
                "title": work.get("title") or work.get("display_name") or "",
                "doi": normalize_doi(work.get("doi") or ""),
                "journal": location.get("display_name", ""),
                "year": str(work.get("publication_year") or ""),
                "authors": [
                    (a.get("author") or {}).get("display_name", "")
                    for a in (work.get("authorships") or [])[:6]
                ],
                "cited_by": work.get("cited_by_count") or 0,
                "is_oa": bool((work.get("open_access") or {}).get("is_oa")),
                "type": work.get("type") or "",
                "source": "openalex",
            }
        )
    return out


def _search_crossref(query: str, limit: int) -> List[Dict[str, Any]]:
    params = _crossref_params()
    params.update({"query.bibliographic": query, "rows": str(min(limit * 2, 50))})
    payload = http.get_json(CROSSREF_API, params=params) or {}
    out = []
    for work in (payload.get("message") or {}).get("items") or []:
        titles = work.get("title") or []
        containers = work.get("container-title") or []
        issued = _date_from_parts(work.get("issued") or {})
        out.append(
            {
                "title": titles[0] if titles else "",
                "doi": normalize_doi(work.get("DOI") or ""),
                "journal": containers[0] if containers else "",
                "year": issued[:4] if issued else "",
                "authors": [
                    f"{a.get('given', '')} {a.get('family', '')}".strip()
                    for a in (work.get("author") or [])[:6]
                ],
                "cited_by": work.get("is-referenced-by-count") or 0,
                "is_oa": bool(work.get("license")),
                "type": work.get("type") or "",
                "source": "crossref",
            }
        )
    return out


def _fold(text: str) -> str:
    import re

    return re.sub(r"[^a-z0-9 ]", "", (text or "").lower()).strip()


def _title_distance(candidate: str, target: str) -> float:
    """Cheap similarity: 0.0 is identical. Avoids a Levenshtein dependency."""
    if not candidate:
        return 1.0
    if candidate == target:
        return 0.0
    candidate_words = set(candidate.split())
    target_words = set(target.split())
    if not target_words:
        return 1.0
    overlap = len(candidate_words & target_words) / len(target_words)
    return 1.0 - overlap
