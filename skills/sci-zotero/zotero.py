#!/usr/bin/env python3
"""Zotero CLI — interact with Zotero libraries via the Web API v3.

Skill-local .env values:
    ZOTERO_API_KEY   — API key (required; create at zotero.org/settings/keys/new)
    ZOTERO_USER_ID   — Numeric user ID for personal library
    ZOTERO_GROUP_ID  — Numeric group ID (use instead of USER_ID for group libraries)

Usage:
    python zotero.py <command> [options]

Commands:
    items       List library items (top-level by default)
    search      Search items by query string
    get         Get full details for an item by key
    collections List collections
    tags        List tags
    children    List child items (attachments/notes) for an item
    add-doi     Add an item by DOI
    add-isbn    Add an item by ISBN
    add-pmid    Add an item by PubMed ID
    check-pdfs  Report which items have/lack PDF attachments
    crossref    Cross-reference a text file of citations against the library
    find-dois   Find and add missing DOIs via CrossRef lookup
    fetch-pdfs  Fetch open-access PDFs and attach to Zotero items
"""

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_BASE = "https://api.zotero.org"

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent


def _load_env_file(path):
    values = {}
    if not path.exists():
        return values
    try:
        with path.open("r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip().strip('"').strip("'")
    except OSError as exc:
        print(f"Warning: failed to load local env from {path}: {exc}", file=sys.stderr)
    return values


LOCAL_ENV = {}
for _env_path in (ROOT_DIR / ".env", ROOT_DIR / "skills" / "sci-zotero" / ".env"):
    LOCAL_ENV.update(_load_env_file(_env_path))


def get_config_value(name, default=""):
    return LOCAL_ENV.get(name) or os.environ.get(name, default)


def get_config():
    api_key = get_config_value("ZOTERO_API_KEY")
    if not api_key:
        print("Error: ZOTERO_API_KEY is not configured in skills/sci-zotero/.env", file=sys.stderr)
        print("Create a key at https://www.zotero.org/settings/keys/new", file=sys.stderr)
        sys.exit(1)

    user_id = get_config_value("ZOTERO_USER_ID")
    group_id = get_config_value("ZOTERO_GROUP_ID")
    if not user_id and not group_id:
        print("Error: Set ZOTERO_USER_ID or ZOTERO_GROUP_ID", file=sys.stderr)
        sys.exit(1)

    prefix = f"/users/{user_id}" if user_id else f"/groups/{group_id}"
    return api_key, prefix


_MAX_RETRIES = 2
_RETRY_CODES = {429, 503}


def api_request(path, api_key, method="GET", data=None, content_type=None, params=None):
    """Make a Zotero API request with retry on transient failures. Returns (response_body, headers)."""
    url = API_BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)

    headers = {
        "Zotero-API-Key": api_key,
        "Zotero-API-Version": "3",
    }
    if content_type:
        headers["Content-Type"] = content_type

    body = None
    if data is not None:
        if isinstance(data, str):
            body = data.encode("utf-8")
        elif isinstance(data, bytes):
            body = data
        else:
            body = json.dumps(data).encode("utf-8")
            if not content_type:
                headers["Content-Type"] = "application/json"

    for attempt in range(_MAX_RETRIES + 1):
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_body = resp.read().decode("utf-8")
                resp_headers = dict(resp.headers)
                return resp_body, resp_headers
        except urllib.error.HTTPError as e:
            if e.code in _RETRY_CODES and attempt < _MAX_RETRIES:
                delay = (attempt + 1) * 2
                print(f"⚠  HTTP {e.code} — retrying in {delay}s...", file=sys.stderr)
                time.sleep(delay)
                continue
            print(f"API Error {e.code}: {e.reason}", file=sys.stderr)
            sys.exit(1)
        except urllib.error.URLError as e:
            if attempt < _MAX_RETRIES:
                delay = (attempt + 1) * 2
                time.sleep(delay)
                continue
            print(f"Network error: {e.reason}", file=sys.stderr)
            sys.exit(1)
    sys.exit(1)


def api_get_json(path, api_key, params=None):
    """GET request, parse JSON, return list/dict."""
    body, headers = api_request(path, api_key, params=params)
    return json.loads(body) if body.strip() else {}, headers


def paginate_all(path, api_key, params=None):
    """Fetch all pages of a paginated endpoint."""
    params = dict(params or {})
    params.setdefault("limit", "100")
    all_items = []
    start = 0
    while True:
        params["start"] = str(start)
        items, headers = api_get_json(path, api_key, params=params)
        if not isinstance(items, list):
            return [items]
        all_items.extend(items)
        total = int(headers.get("Total-Results", len(all_items)))
        if len(all_items) >= total:
            break
        start = len(all_items)
    return all_items


def fmt_creators(creators):
    parts = []
    for c in creators[:3]:
        name = c.get("lastName", c.get("name", "?"))
        parts.append(name)
    if len(creators) > 3:
        parts.append("et al.")
    return ", ".join(parts)


def fmt_item_short(item):
    d = item["data"]
    creators = fmt_creators(d.get("creators", []))
    year = ""
    if d.get("date"):
        m = re.match(r"(\d{4})", d["date"])
        if m:
            year = m.group(1)
    return f"[{d.get('key', '?')}] {creators} ({year}) {d.get('title', 'untitled')} [{d.get('itemType', '?')}]"



def cmd_items(args):
    api_key, prefix = get_config()
    params = {"limit": str(args.limit), "sort": args.sort, "direction": args.direction}
    path = f"{prefix}/items/top"
    items, headers = api_get_json(path, api_key, params=params)
    print(f"Showing {len(items)} items\n")
    for item in items:
        if item["data"].get("itemType") != "attachment":
            print(fmt_item_short(item))


def cmd_search(args):
    api_key, prefix = get_config()
    params = {"q": args.query, "limit": "25"}
    items, _ = api_get_json(f"{prefix}/items", api_key, params=params)
    if not isinstance(items, list):
        items = [items]
    print(f"Found {len(items)} items\n")
    for item in items:
        print(fmt_item_short(item))


def cmd_get(args):
    api_key, prefix = get_config()
    item, _ = api_get_json(f"{prefix}/items/{args.key}", api_key)
    print(json.dumps(item, indent=2, ensure_ascii=False))


def cmd_collections(args):
    api_key, prefix = get_config()
    params = {"limit": str(args.limit)}
    collections, _ = api_get_json(f"{prefix}/collections/top", api_key, params=params)
    if not isinstance(collections, list):
        collections = [collections]
    for col in collections:
        d = col["data"]
        key = d.get("key", "?")
        name = d.get("name", "untitled")
        count = col.get("meta", {}).get("numItems", 0)
        print(f"[{key}] {name} ({count} items)")


def cmd_tags(args):
    api_key, prefix = get_config()
    tags = paginate_all(f"{prefix}/tags", api_key)
    for tag in tags:
        if isinstance(tag, dict):
            print(tag.get("tag", str(tag)))
        else:
            print(tag)


def cmd_children(args):
    api_key, prefix = get_config()
    children, _ = api_get_json(f"{prefix}/items/{args.key}/children", api_key)
    if not isinstance(children, list):
        children = [children]
    print(f"Children of {args.key}:\n")
    for child in children:
        d = child["data"]
        item_type = d.get("itemType", "?")
        title = d.get("title") or d.get("filename") or "untitled"
        key = d.get("key", "?")
        print(f"[{key}] {item_type}: {title}")


def _external_get_json(url):
    """GET an external (non-Zotero) URL and return parsed JSON."""
    req = urllib.request.Request(url, headers={"User-Agent": "zotero-cli/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"External API error {e.code}: {url}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Network error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def _get_item_template(api_key, item_type):
    """Fetch a blank Zotero item template for the given itemType."""
    body, _ = api_request("/items/new", api_key, params={"itemType": item_type})
    return json.loads(body)


def cmd_add_doi(args):
    api_key, prefix = get_config()
    doi = args.identifier.strip()
    crossref_url = f"https://api.crossref.org/works/{urllib.parse.quote(doi, safe='')}"
    data = _external_get_json(crossref_url)
    work = data.get("message", {})
    template = _get_item_template(api_key, "journalArticle")
    template["title"] = (work.get("title") or [""])[0]
    template["DOI"] = doi
    template["url"] = work.get("URL", "")
    template["volume"] = work.get("volume", "")
    template["issue"] = work.get("issue", "")
    template["pages"] = work.get("page", "")
    template["publicationTitle"] = (work.get("container-title") or [""])[0]
    template["ISSN"] = (work.get("ISSN") or [""])[0]
    issued = work.get("issued", {}).get("date-parts", [[]])[0]
    template["date"] = "-".join(str(p) for p in issued) if issued else ""
    template["creators"] = []
    for author in work.get("author", []):
        template["creators"].append({
            "creatorType": "author",
            "firstName": author.get("given", ""),
            "lastName": author.get("family", ""),
        })
    body, _ = api_request(f"{prefix}/items", api_key, method="POST", data=[template])
    result = json.loads(body)
    new_key = (result.get("successful") or {}).get("0", {}).get("data", {}).get("key", "?")
    print(f"Added item: {new_key}")


def cmd_add_isbn(args):
    api_key, prefix = get_config()
    isbn = re.sub(r"[^0-9X]", "", args.identifier.upper())
    ol_url = (
        f"https://openlibrary.org/api/books"
        f"?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
    )
    data = _external_get_json(ol_url)
    book = data.get(f"ISBN:{isbn}")
    if not book:
        print(f"ISBN {isbn} not found in Open Library", file=sys.stderr)
        sys.exit(1)
    template = _get_item_template(api_key, "book")
    template["title"] = book.get("title", "")
    template["ISBN"] = isbn
    template["publisher"] = (book.get("publishers") or [{}])[0].get("name", "")
    template["place"] = (book.get("publish_places") or [{}])[0].get("name", "")
    template["date"] = book.get("publish_date", "")
    template["numPages"] = str(book.get("number_of_pages", ""))
    template["creators"] = []
    for author in book.get("authors", []):
        name = author.get("name", "")
        parts = name.rsplit(" ", 1)
        template["creators"].append({
            "creatorType": "author",
            "firstName": parts[0] if len(parts) > 1 else "",
            "lastName": parts[-1],
        })
    body, _ = api_request(f"{prefix}/items", api_key, method="POST", data=[template])
    result = json.loads(body)
    new_key = (result.get("successful") or {}).get("0", {}).get("data", {}).get("key", "?")
    print(f"Added item: {new_key}")


def cmd_add_pmid(args):
    api_key, prefix = get_config()
    pmid = args.identifier.strip()
    esummary_url = (
        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        f"?db=pubmed&id={pmid}&retmode=json"
    )
    data = _external_get_json(esummary_url)
    article = data.get("result", {}).get(pmid, {})
    if not article:
        print(f"PMID {pmid} not found", file=sys.stderr)
        sys.exit(1)
    template = _get_item_template(api_key, "journalArticle")
    template["title"] = article.get("title", "")
    template["publicationTitle"] = article.get("fulljournalname", "")
    template["volume"] = article.get("volume", "")
    template["issue"] = article.get("issue", "")
    template["pages"] = article.get("pages", "")
    template["date"] = article.get("pubdate", "")
    ids = {
        id_obj.get("idtype"): id_obj.get("value")
        for id_obj in article.get("articleids", [])
    }
    template["DOI"] = ids.get("doi", "")
    template["creators"] = []
    for author in article.get("authors", []):
        if author.get("authtype") == "Author":
            name = author.get("name", "")
            parts = name.split(" ", 1)
            template["creators"].append({
                "creatorType": "author",
                "lastName": parts[0],
                "firstName": parts[1] if len(parts) > 1 else "",
            })
    body, _ = api_request(f"{prefix}/items", api_key, method="POST", data=[template])
    result = json.loads(body)
    new_key = (result.get("successful") or {}).get("0", {}).get("data", {}).get("key", "?")
    print(f"Added item: {new_key}")


def cmd_check_pdfs(args):
    api_key, prefix = get_config()
    print("Fetching all top-level items...")
    items = paginate_all(f"{prefix}/items/top", api_key)
    has_pdf = []
    no_pdf = []
    for item in items:
        if item["data"].get("itemType") in ("attachment", "note"):
            continue
        key = item["data"]["key"]
        children, _ = api_get_json(f"{prefix}/items/{key}/children", api_key)
        if not isinstance(children, list):
            children = [children]
        pdf_found = any(
            c["data"].get("contentType") == "application/pdf"
            or c["data"].get("filename", "").lower().endswith(".pdf")
            for c in children
        )
        (has_pdf if pdf_found else no_pdf).append(item)
    print(f"\nItems WITH PDF ({len(has_pdf)}):")
    for item in has_pdf:
        print(f"  {fmt_item_short(item)}")
    print(f"\nItems WITHOUT PDF ({len(no_pdf)}):")
    for item in no_pdf:
        print(f"  {fmt_item_short(item)}")


def cmd_crossref(args):
    api_key, prefix = get_config()
    try:
        with open(args.file, encoding="utf-8") as f:
            citations = [line.strip() for line in f if line.strip()]
    except OSError as e:
        print(f"Cannot read file: {e}", file=sys.stderr)
        sys.exit(1)
    print("Fetching library items...")
    library_items = paginate_all(f"{prefix}/items/top", api_key)
    library_titles = {
        item["data"].get("title", "").lower(): item for item in library_items
    }
    matched = []
    missing = []
    for citation in citations:
        query = urllib.parse.quote(citation[:200])
        cr_url = f"https://api.crossref.org/works?query={query}&rows=1"
        try:
            data = _external_get_json(cr_url)
        except SystemExit:
            missing.append(citation)
            continue
        cr_items = data.get("message", {}).get("items", [])
        if not cr_items:
            missing.append(citation)
            continue
        cr_title = (cr_items[0].get("title") or [""])[0].lower()
        ratio = difflib.SequenceMatcher(None, citation.lower(), cr_title).ratio()
        if ratio > 0.6 and cr_title in library_titles:
            matched.append((citation, library_titles[cr_title]))
        else:
            missing.append(citation)
    print(f"\nMatched ({len(matched)}):")
    for citation, item in matched:
        print(f"  [IN LIBRARY] {fmt_item_short(item)}")
        print(f"    Citation: {citation[:80]}")
    print(f"\nMissing ({len(missing)}):")
    for citation in missing:
        print(f"  {citation[:100]}")


def cmd_find_dois(args):
    api_key, prefix = get_config()
    print("Fetching items without DOI...")
    items = paginate_all(f"{prefix}/items/top", api_key)
    no_doi = [
        item for item in items
        if not item["data"].get("DOI")
        and item["data"].get("itemType") not in ("attachment", "note")
    ]
    print(f"Found {len(no_doi)} items without DOI\n")
    updated = []
    for item in no_doi:
        d = item["data"]
        title = d.get("title", "")
        creators = d.get("creators", [])
        author = creators[0].get("lastName", "") if creators else ""
        if not title:
            continue
        query = urllib.parse.quote(f"{title} {author}"[:200])
        cr_url = f"https://api.crossref.org/works?query={query}&rows=1"
        try:
            data = _external_get_json(cr_url)
        except SystemExit:
            continue
        cr_items = data.get("message", {}).get("items", [])
        if not cr_items:
            continue
        cr_item = cr_items[0]
        cr_title = (cr_item.get("title") or [""])[0]
        ratio = difflib.SequenceMatcher(None, title.lower(), cr_title.lower()).ratio()
        doi = cr_item.get("DOI", "")
        if ratio > 0.85 and doi:
            patch = {"key": d["key"], "version": d["version"], "DOI": doi}
            api_request(f"{prefix}/items/{d['key']}", api_key, method="PATCH", data=patch)
            updated.append((fmt_item_short(item), doi))
            print(f"Updated DOI for: {d['key']} -> {doi}")
    print(f"\nTotal updated: {len(updated)}")


def cmd_fetch_pdfs(args):
    api_key, prefix = get_config()
    print("Fetching items without PDF attachments...")
    items = paginate_all(f"{prefix}/items/top", api_key)
    no_pdf = []
    for item in items:
        if item["data"].get("itemType") in ("attachment", "note"):
            continue
        key = item["data"]["key"]
        children, _ = api_get_json(f"{prefix}/items/{key}/children", api_key)
        if not isinstance(children, list):
            children = [children]
        has_pdf = any(
            c["data"].get("contentType") == "application/pdf"
            or c["data"].get("filename", "").lower().endswith(".pdf")
            for c in children
        )
        if not has_pdf and item["data"].get("DOI"):
            no_pdf.append(item)
    print(f"Found {len(no_pdf)} items with DOI but no PDF\n")
    success = []
    failed = []
    for item in no_pdf:
        d = item["data"]
        doi = d.get("DOI", "")
        unpaywall_url = (
            f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi, safe='')}"
            f"?email=zotero@example.com"
        )
        try:
            oa_data = _external_get_json(unpaywall_url)
        except SystemExit:
            failed.append(fmt_item_short(item))
            continue
        best_oa = oa_data.get("best_oa_location") or {}
        pdf_url = best_oa.get("url_for_pdf") or best_oa.get("url")
        if not pdf_url:
            failed.append(fmt_item_short(item))
            continue
        try:
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
            os.close(tmp_fd)
            pdf_req = urllib.request.Request(
                pdf_url, headers={"User-Agent": "zotero-cli/1.0"}
            )
            with urllib.request.urlopen(pdf_req, timeout=60) as resp:
                with open(tmp_path, "wb") as fh:
                    shutil.copyfileobj(resp, fh)
        except Exception as e:
            print(f"Download failed for {d['key']}: {e}", file=sys.stderr)
            failed.append(fmt_item_short(item))
            continue
        with open(tmp_path, "rb") as fh:
            pdf_bytes = fh.read()
        os.unlink(tmp_path)
        md5 = hashlib.md5(pdf_bytes).hexdigest()
        filename = re.sub(r'[\\/:*?"<>|]', "_", d.get("title", d["key"])[:60]) + ".pdf"
        attachment_template = _get_item_template(api_key, "attachment")
        attachment_template["linkMode"] = "imported_file"
        attachment_template["parentItem"] = d["key"]
        attachment_template["title"] = filename
        attachment_template["contentType"] = "application/pdf"
        body, _ = api_request(
            f"{prefix}/items", api_key, method="POST", data=[attachment_template]
        )
        att_result = json.loads(body)
        att_key = (
            (att_result.get("successful") or {}).get("0", {}).get("data", {}).get("key")
        )
        if not att_key:
            failed.append(fmt_item_short(item))
            continue
        auth_params = {
            "md5": md5,
            "filename": filename,
            "filesize": str(len(pdf_bytes)),
            "mtime": str(int(time.time() * 1000)),
        }
        auth_body, _ = api_request(
            f"{prefix}/items/{att_key}/file",
            api_key,
            method="POST",
            data=urllib.parse.urlencode(auth_params),
            content_type="application/x-www-form-urlencoded",
        )
        auth_data = json.loads(auth_body)
        if "exists" in auth_data:
            success.append(fmt_item_short(item))
            continue
        upload_url = auth_data.get("url", "")
        upload_params = auth_data.get("params", {})
        boundary = "----ZoteroBoundary"
        parts_enc = []
        for k, v in upload_params.items():
            parts_enc.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}"
            )
        parts_enc.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
            f"filename=\"{filename}\"\r\nContent-Type: application/pdf\r\n\r\n"
        )
        prefix_bytes = "\r\n".join(parts_enc).encode("utf-8")
        suffix_bytes = f"\r\n--{boundary}--\r\n".encode("utf-8")
        upload_body = prefix_bytes + pdf_bytes + suffix_bytes
        upload_req = urllib.request.Request(
            upload_url,
            data=upload_body,
            method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        try:
            with urllib.request.urlopen(upload_req, timeout=120):
                pass
        except urllib.error.HTTPError as e:
            if e.code not in (200, 201, 204):
                failed.append(fmt_item_short(item))
                continue
        upload_key = auth_data.get("uploadKey", "")
        api_request(
            f"{prefix}/items/{att_key}/file",
            api_key,
            method="POST",
            data=f"upload={upload_key}",
            content_type="application/x-www-form-urlencoded",
        )
        success.append(fmt_item_short(item))
        print(f"Attached PDF: {d['key']}")
    print(f"\nSuccess ({len(success)}):")
    for s in success:
        print(f"  {s}")
    print(f"\nFailed ({len(failed)}):")
    for entry in failed:
        print(f"  {entry}")


def main():
    parser = argparse.ArgumentParser(description="Zotero CLI")
    subparsers = parser.add_subparsers(dest="command")

    p = subparsers.add_parser("items", help="List top-level library items")
    p.add_argument("--limit", type=int, default=25)
    p.add_argument("--sort", default="dateModified")
    p.add_argument("--direction", default="desc")

    p = subparsers.add_parser("search", help="Search items by query string")
    p.add_argument("query", help="Search query")

    p = subparsers.add_parser("get", help="Get full details for an item")
    p.add_argument("key", help="Zotero item key")

    p = subparsers.add_parser("collections", help="List collections")
    p.add_argument("--limit", type=int, default=25)

    subparsers.add_parser("tags", help="List all tags")

    p = subparsers.add_parser("children", help="List child items (attachments/notes)")
    p.add_argument("key", help="Zotero item key")

    p = subparsers.add_parser("add-doi", help="Add an item by DOI")
    p.add_argument("identifier", help="DOI string")

    p = subparsers.add_parser("add-isbn", help="Add an item by ISBN")
    p.add_argument("identifier", help="ISBN string")

    p = subparsers.add_parser("add-pmid", help="Add an item by PubMed ID")
    p.add_argument("identifier", help="PubMed ID")

    subparsers.add_parser("check-pdfs", help="Report which items have/lack PDF attachments")

    p = subparsers.add_parser("crossref", help="Cross-reference citations file against library")
    p.add_argument("file", help="Path to text file with one citation per line")

    subparsers.add_parser("find-dois", help="Find and add missing DOIs via CrossRef")

    subparsers.add_parser("fetch-pdfs", help="Fetch open-access PDFs and attach to items")

    args = parser.parse_args()

    commands = {
        "items": cmd_items,
        "search": cmd_search,
        "get": cmd_get,
        "collections": cmd_collections,
        "tags": cmd_tags,
        "children": cmd_children,
        "add-doi": cmd_add_doi,
        "add-isbn": cmd_add_isbn,
        "add-pmid": cmd_add_pmid,
        "check-pdfs": cmd_check_pdfs,
        "crossref": cmd_crossref,
        "find-dois": cmd_find_dois,
        "fetch-pdfs": cmd_fetch_pdfs,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
