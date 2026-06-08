"""Download papers from CNKI (知网) via FSSO/CARSI direct access or WebVPN proxy.

Usage:
    python cnki_download.py search "关键词" [--limit N]
    python cnki_download.py download <filename> [--dbcode CJFD]
    python cnki_download.py set-school "学校名称"
    python cnki_download.py set-mode fsso|webvpn
    python cnki_download.py status

Access modes:
    - fsso (default): Direct access to kns.cnki.net via CARSI/FSSO session cookie.
      Login at https://fsso.cnki.net → select school → CAS login → export cookie.
    - webvpn: Access via university WebVPN proxy (AES-encrypted URLs).
      Login at school's WebVPN portal → export cookie.

Requires:
    - Valid session cookies (from browser login)
    - requests, beautifulsoup4
    - pycryptodome (only for webvpn mode)
"""

from __future__ import annotations

import json
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from config import load_config, update_config, resolve_school, DATA_DIR, WEBVPN_DEFAULT_KEY, WEBVPN_DEFAULT_IV

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)

CNKI_BASE = "https://kns.cnki.net"
CNKI_SEARCH_API = f"{CNKI_BASE}/kns8s/brief/grid"
CNKI_SEARCH_PAGE = f"{CNKI_BASE}/kns8s/defaultresult/index"

CNKI_DEFAULT_KUAKUCODE = "YSTT4HG0,LSTPFY1C,JUP3MUPD,MPMFIG1A,EMRPGLPA,WQ0UVIAA,BLZOG7CK,PWFIRAGL,NN3FJMUV,NLBO1Z6R"
CNKI_DEFAULT_PRODUCTSTR = "YSTT4HG0,LSTPFY1C,RMJLXHZ3,JQIRZIYA,JUP3MUPD,1UR4K4HZ,BPBAFJ5S,R79MZMCB,MPMFIG1A,EMRPGLPA,J708GVCE,ML4DRIDX,WQ0UVIAA,NB3BWEHK,XVLO76FD,HR1YT1Z9,BLZOG7CK,PWFIRAGL,NN3FJMUV,NLBO1Z6R,"

FSSO_COOKIE_FILE = DATA_DIR / "fsso_cookies.json"
WEBVPN_COOKIE_FILE = DATA_DIR / "webvpn_cookies.json"


def _get_mode(config: dict[str, Any]) -> str:
    return config.get("cnki_mode", "fsso")


def _get_cookie_file(config: dict[str, Any]) -> Path:
    mode = _get_mode(config)
    if mode == "fsso":
        return Path(config.get("fsso_cookie_file", str(FSSO_COOKIE_FILE)))
    return Path(config.get("cookie_file", str(WEBVPN_COOKIE_FILE)))


def _get_session(config: dict[str, Any]) -> requests.Session:
    s = requests.Session()
    s.trust_env = False
    s.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    proxy = config.get("proxy", "")
    if proxy:
        s.proxies = {"http": proxy, "https": proxy}
    _load_cookies(s, config)
    return s


def _load_cookies(session: requests.Session, config: dict[str, Any]) -> None:
    cookie_file = _get_cookie_file(config)
    if not cookie_file.exists():
        return
    try:
        cookies = json.loads(cookie_file.read_text(encoding="utf-8"))
        for c in cookies:
            name = c.get("name", "")
            value = c.get("value", "")
            if name and value:
                kwargs: dict[str, Any] = {}
                if c.get("domain"):
                    kwargs["domain"] = c["domain"]
                if c.get("path"):
                    kwargs["path"] = c["path"]
                session.cookies.set(name, value, **kwargs)
    except Exception:
        pass


def _resolve_url(url: str, config: dict[str, Any]) -> str:
    """Resolve URL based on access mode. FSSO uses direct URL, WebVPN encrypts it."""
    mode = _get_mode(config)
    if mode == "fsso":
        return url
    from webvpn_crypto import convert_url
    host = config.get("webvpn_host", "")
    if not host:
        raise RuntimeError("WebVPN host not configured. Run: python cnki_download.py set-school 学校名称")
    key = config.get("webvpn_crypto_key", "") or WEBVPN_DEFAULT_KEY
    iv = config.get("webvpn_crypto_iv", "") or WEBVPN_DEFAULT_IV
    return convert_url(url, host, key, iv)


def check_session(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Check if CNKI session cookies are valid."""
    if config is None:
        config = load_config()

    mode = _get_mode(config)
    cookie_file = _get_cookie_file(config)

    if not cookie_file.exists():
        login_hint = "https://fsso.cnki.net" if mode == "fsso" else config.get("webvpn_host", "WebVPN portal")
        return {"valid": False, "mode": mode, "error": f"Cookie file not found: {cookie_file}. Login at {login_hint} and export cookies."}

    session = _get_session(config)
    test_url = _resolve_url("https://kns.cnki.net/kns8/defaultresult/index", config)

    try:
        resp = session.get(test_url, timeout=15, allow_redirects=True)
        if resp.status_code == 200 and "cnki" in resp.text.lower():
            return {"valid": True, "mode": mode, "school": config.get("webvpn_school", "")}
        if "login" in resp.url.lower() or "fsso" in resp.url.lower() or "cas" in resp.url.lower():
            return {"valid": False, "mode": mode, "error": "Session expired — re-login required"}
        return {"valid": False, "mode": mode, "error": f"Unexpected response (HTTP {resp.status_code})"}
    except requests.RequestException as e:
        return {"valid": False, "mode": mode, "error": f"Connection failed: {e}"}


def search_cnki(
    keyword: str,
    limit: int = 10,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Search CNKI for papers via kns8s POST API.

    Returns:
        {success: bool, results: [{title, authors, journal, year, filename, dbcode, url}]}
    """
    if config is None:
        config = load_config()

    session = _get_session(config)

    # Step 1: visit search page to establish session cookies
    search_page_url = _resolve_url(CNKI_SEARCH_PAGE, config)
    try:
        session.get(search_page_url, timeout=15, allow_redirects=True)
    except requests.RequestException:
        pass

    # Step 2: POST search request with correct kns8s format
    query_json = {
        "Platform": "NZKPT",
        "Resource": "CROSSDB",
        "Classid": "WD0FTY92",
        "Products": "",
        "QNode": {
            "QGroup": [{
                "Key": "Subject",
                "Title": "",
                "Logic": 0,
                "Items": [{
                    "Field": "SU",
                    "Value": keyword,
                    "Operator": "TOPRANK",
                    "Logic": 0,
                    "Title": "主题",
                }],
                "ChildItems": [],
            }]
        },
        "ExScope": 1,
        "SearchType": 2,
        "Rlang": "CHINESE",
        "KuaKuCode": CNKI_DEFAULT_KUAKUCODE,
        "Expands": {},
        "View": "changeDBCh",
        "SearchFrom": 1,
    }

    post_data = {
        "boolSearch": "true",
        "QueryJson": json.dumps(query_json, ensure_ascii=False),
        "pageNum": "1",
        "pageSize": str(min(limit, 50)),
        "dstyle": "listmode",
        "boolSortSearch": "false",
        "productStr": CNKI_DEFAULT_PRODUCTSTR,
        "aside": f"(主题：{keyword})",
        "searchFrom": "资源范围：总库",
        "subject": "",
        "turnpage": "",
        "language": "CHS",
        "uniplatform": "NZKPT",
        "CurPage": "1",
    }

    search_api_url = _resolve_url(CNKI_SEARCH_API, config)
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": search_page_url,
        "X-Requested-With": "XMLHttpRequest",
    }

    try:
        resp = session.post(search_api_url, data=post_data, headers=headers, timeout=30)
    except requests.RequestException as e:
        return {"success": False, "error": f"Search request failed: {e}"}

    if resp.status_code != 200:
        return {"success": False, "error": f"HTTP {resp.status_code}"}

    if len(resp.text) < 200 or "no-content" in resp.text:
        error_match = re.search(r'value="([^"]+)"', resp.text)
        error_msg = error_match.group(1) if error_match else "Empty response"
        return {"success": False, "error": f"CNKI returned: {error_msg}"}

    soup = BeautifulSoup(resp.text, "html.parser")
    results = _parse_search_results(soup, limit)

    if not results:
        alt_results = _try_alternative_parse(resp.text, limit)
        if alt_results:
            results = alt_results

    return {"success": True, "keyword": keyword, "count": len(results), "results": results}


def _parse_search_results(soup: BeautifulSoup, limit: int) -> list[dict[str, str]]:
    """Parse CNKI search result page HTML (kns8s format)."""
    results: list[dict[str, str]] = []
    rows = soup.select("table.result-table-list tbody tr")
    if not rows:
        rows = soup.select(".result-table-list tr.odd, .result-table-list tr.even")

    for row in rows[:limit]:
        title_tag = row.select_one("td.name a.fz14")
        if not title_tag:
            title_tag = row.select_one("td.name a")
        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        href = title_tag.get("href", "")
        if href and not href.startswith("http"):
            href = f"{CNKI_BASE}{href}"

        authors_tag = row.select_one("td.author")
        authors = authors_tag.get_text(strip=True) if authors_tag else ""

        journal_tag = row.select_one("td.source a")
        journal = journal_tag.get_text(strip=True) if journal_tag else ""

        year_tag = row.select_one("td.date")
        year = year_tag.get_text(strip=True) if year_tag else ""

        filename = _extract_filename(href)
        dbcode = _extract_dbcode(href)

        results.append({
            "title": title,
            "authors": authors,
            "journal": journal,
            "year": year,
            "filename": filename,
            "dbcode": dbcode,
            "url": href,
        })

    return results


def _try_alternative_parse(html: str, limit: int) -> list[dict[str, str]]:
    """Fallback parser using regex when structured HTML fails."""
    results: list[dict[str, str]] = []
    # Match both kcms2 and old kcms URL formats
    pattern = re.compile(
        r'<a[^>]*href="([^"]*(?:kcms2/article/abstract|kcms/detail)[^"]*)"[^>]*class="fz14"[^>]*>(.*?)</a>',
        re.DOTALL,
    )
    for match in pattern.finditer(html):
        if len(results) >= limit:
            break
        href = match.group(1)
        if not href.startswith("http"):
            href = f"{CNKI_BASE}{href}"
        title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
        if title:
            results.append({
                "title": title,
                "authors": "",
                "journal": "",
                "year": "",
                "filename": _extract_filename(href),
                "dbcode": _extract_dbcode(href),
                "url": href,
            })
    return results


def _extract_filename(url: str) -> str:
    m = re.search(r"[?&](?:filename|FileName)=([^&]+)", url, re.IGNORECASE)
    if m:
        return m.group(1)
    # kcms2 URL: /kcms2/article/abstract?v=xxx&filename=YYY or just v= with no filename
    m = re.search(r"/kcms2/article/abstract\?v=([^&]+)", url)
    if m and "filename" not in url.lower():
        return m.group(1)
    return ""


def _extract_dbcode(url: str) -> str:
    m = re.search(r"[?&]dbcode=([^&]+)", url, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"[?&]dbname=([^&]+)", url, re.IGNORECASE)
    if m:
        return m.group(1)
    return "CJFD"


def download_cnki(
    filename: str,
    dbcode: str = "CJFD",
    output_dir: str | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Download a paper from CNKI by filename/dbcode or direct kcms2 URL.

    Args:
        filename: CNKI filename (e.g. ZGTB202401001) or a full kcms2 URL
        dbcode: Database code (CJFD, CDMD, etc.)
        output_dir: Override output directory
        config: Config dict

    Returns:
        {success: bool, file?: str, filename: str, source: str, error?: str}
    """
    if config is None:
        config = load_config()

    session = _get_session(config)
    target_dir = Path(output_dir) if output_dir else Path(config["output_dir"]).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)

    # Determine if filename is actually a URL
    is_url = filename.startswith("http") or "kcms2/" in filename
    safe_name = re.sub(r'[^\w\-.]', '_', filename[:60]) if is_url else filename
    output_path = target_dir / f"cnki_{safe_name}.pdf"

    if output_path.exists() and output_path.stat().st_size >= 10_000:
        return {"success": True, "filename": filename, "file": str(output_path), "source": "local_cache"}

    # Build detail page URL
    if is_url:
        detail_url = filename if filename.startswith("http") else f"{CNKI_BASE}{filename}"
    else:
        # Try kcms2 first, fallback to old kcms
        detail_url = f"{CNKI_BASE}/kcms2/article/abstract?dbcode={dbcode}&dbname={dbcode}&filename={filename}"

    resolved_detail = _resolve_url(detail_url, config)

    try:
        resp = session.get(resolved_detail, timeout=20, allow_redirects=True)
    except requests.RequestException as e:
        return {"success": False, "filename": filename, "source": "CNKI", "error": f"Detail page request failed: {e}"}

    # If kcms2 returns 404, try old kcms format
    if resp.status_code == 404 and not is_url:
        detail_url = f"{CNKI_BASE}/kcms/detail/detail.aspx?dbcode={dbcode}&filename={filename}"
        resolved_detail = _resolve_url(detail_url, config)
        try:
            resp = session.get(resolved_detail, timeout=20, allow_redirects=True)
        except requests.RequestException as e:
            return {"success": False, "filename": filename, "source": "CNKI", "error": f"Detail page request failed: {e}"}

    if resp.status_code != 200:
        return {"success": False, "filename": filename, "source": "CNKI", "error": f"Detail page HTTP {resp.status_code}"}

    if "login" in resp.url.lower() or "fsso" in resp.url.lower():
        return {"success": False, "filename": filename, "source": "CNKI", "error": "Session expired — re-login required"}

    pdf_url = _find_pdf_in_detail_page(resp.text, filename, dbcode)
    if not pdf_url:
        return {"success": False, "filename": filename, "source": "CNKI", "error": "No PDF/CAJ download link found on detail page"}

    return _download_pdf_link(session, pdf_url, output_path, filename, config)


def _find_pdf_in_detail_page(html: str, filename: str, dbcode: str) -> str | None:
    """Extract PDF/CAJ download URL from CNKI article detail page."""
    soup = BeautifulSoup(html, "html.parser")

    # Priority 1: bar.cnki.net PDF download (most reliable on current CNKI)
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "bar.cnki.net" in href and "order" in href:
            text = a.get_text(strip=True).lower()
            if "pdf" in text:
                return href

    # Priority 2: classic PDF download button
    pdf_link = soup.select_one("a#pdfDown, a.btn-dlpdf")
    if pdf_link:
        href = pdf_link.get("href", "")
        if href and not href.startswith("javascript") and "ai.cnki.net" not in href:
            if href.startswith("/"):
                return f"{CNKI_BASE}{href}"
            return href

    # Priority 3: operate-btn section
    for a in soup.select(".operate-btn a[href]"):
        href = a.get("href", "")
        text = a.get_text(strip=True).lower()
        if "pdf" in text and href and not href.startswith("javascript") and "ai.cnki.net" not in href:
            if href.startswith("/"):
                return f"{CNKI_BASE}{href}"
            return href

    # Priority 4: bar.cnki.net CAJ download (fallback)
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "bar.cnki.net" in href and "order" in href:
            text = a.get_text(strip=True).lower()
            if "caj" in text:
                return href

    # Priority 5: classic CAJ download button
    caj_link = soup.select_one("a#cajDown")
    if caj_link:
        href = caj_link.get("href", "")
        if href and not href.startswith("javascript") and "ai.cnki.net" not in href:
            if href.startswith("/"):
                return f"{CNKI_BASE}{href}"
            return href

    # Priority 6: any bar.cnki.net order link
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "bar.cnki.net" in href and "order" in href:
            return href

    return None


def _download_pdf_link(
    session: requests.Session,
    pdf_url: str,
    output_path: Path,
    filename: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Download PDF/CAJ from resolved URL."""
    resolved_url = _resolve_url(pdf_url, config)
    headers = {"Referer": f"{CNKI_BASE}/kcms2/article/abstract?v={filename}"}

    try:
        resp = session.get(resolved_url, headers=headers, timeout=60, allow_redirects=True, stream=True)
    except requests.RequestException as e:
        return {"success": False, "filename": filename, "source": "CNKI", "error": f"PDF download failed: {e}"}

    if resp.status_code != 200:
        return {"success": False, "filename": filename, "source": "CNKI", "error": f"PDF HTTP {resp.status_code}"}

    content = resp.content

    # Detect file type
    is_pdf = content[:5] == b"%PDF-"
    is_caj = content[:4] in (b"CAJ-", b"\xc8\xaf\xc8\xaf")

    if not is_pdf and not is_caj:
        if b"login" in content[:2000].lower() or b"cas" in content[:2000].lower():
            return {"success": False, "filename": filename, "source": "CNKI", "error": "Session expired — redirected to login"}
        if len(content) < 1000:
            return {"success": False, "filename": filename, "source": "CNKI", "error": f"Response is not a valid PDF/CAJ ({len(content)} bytes, starts with {content[:20]!r})"}

    if len(content) < 10_000:
        return {"success": False, "filename": filename, "source": "CNKI", "error": f"File too small ({len(content)} bytes)"}

    # Use correct extension
    if is_caj:
        output_path = output_path.with_suffix(".caj")

    output_path.write_bytes(content)
    return {"success": True, "filename": filename, "file": str(output_path), "source": "CNKI", "size_bytes": len(content), "format": "CAJ" if is_caj else "PDF"}


def set_school(school_name: str) -> dict[str, Any]:
    """Configure WebVPN school for CNKI access."""
    info = resolve_school(school_name)
    if not info:
        return {"success": False, "error": f"School '{school_name}' not found in schools.json"}

    update_config("webvpn_school", school_name)
    update_config("webvpn_host", info["host"])
    update_config("webvpn_crypto_key", info.get("crypto_key", WEBVPN_DEFAULT_KEY))
    update_config("webvpn_crypto_iv", info.get("crypto_iv", WEBVPN_DEFAULT_IV))
    return {"success": True, "school": school_name, "host": info["host"]}


def set_mode(mode: str) -> dict[str, Any]:
    """Switch between FSSO and WebVPN access modes."""
    mode = mode.lower().strip()
    if mode not in ("fsso", "webvpn"):
        return {"success": False, "error": f"Invalid mode '{mode}'. Use 'fsso' or 'webvpn'."}
    update_config("cnki_mode", mode)
    return {"success": True, "mode": mode}


def status(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Show current CNKI configuration and session status."""
    if config is None:
        config = load_config()

    mode = _get_mode(config)
    cookie_file = _get_cookie_file(config)

    info: dict[str, Any] = {
        "mode": mode,
        "school": config.get("webvpn_school", ""),
        "cookie_file": str(cookie_file),
        "cookie_exists": cookie_file.exists(),
        "output_dir": config.get("output_dir", ""),
        "proxy": config.get("proxy", ""),
    }

    if mode == "fsso":
        info["login_url"] = "https://fsso.cnki.net"
        info["instructions"] = (
            "1. Open https://fsso.cnki.net in browser\n"
            "2. Select your institution and login via CAS/Shibboleth\n"
            "3. Export cookies (use browser extension like EditThisCookie)\n"
            f"4. Save as JSON to: {cookie_file}"
        )
    else:
        host = config.get("webvpn_host", "")
        info["webvpn_host"] = host
        info["instructions"] = (
            f"1. Open {host} in browser\n"
            "2. Login with university credentials\n"
            "3. Export cookies (use browser extension)\n"
            f"4. Save as JSON to: {cookie_file}"
        )

    return info


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Download papers from CNKI (知网)")
    sub = parser.add_subparsers(dest="command")

    p_search = sub.add_parser("search", help="Search CNKI")
    p_search.add_argument("keyword", help="Search keyword")
    p_search.add_argument("--limit", "-n", type=int, default=10)

    p_dl = sub.add_parser("download", help="Download by filename")
    p_dl.add_argument("filename", help="CNKI filename (e.g. ZGTB202401001)")
    p_dl.add_argument("--dbcode", default="CJFD", help="Database code")
    p_dl.add_argument("--output-dir", "-o", help="Output directory")

    p_school = sub.add_parser("set-school", help="Set WebVPN school")
    p_school.add_argument("school", help="School name (Chinese)")

    p_mode = sub.add_parser("set-mode", help="Set access mode")
    p_mode.add_argument("mode", choices=["fsso", "webvpn"])

    sub.add_parser("status", help="Show config and session status")
    sub.add_parser("check", help="Check if session cookies are valid")

    args = parser.parse_args()

    if args.command == "search":
        result = search_cnki(args.keyword, limit=args.limit)
    elif args.command == "download":
        result = download_cnki(args.filename, dbcode=args.dbcode, output_dir=args.output_dir)
    elif args.command == "set-school":
        result = set_school(args.school)
    elif args.command == "set-mode":
        result = set_mode(args.mode)
    elif args.command == "status":
        result = status()
    elif args.command == "check":
        result = check_session()
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    success = result.get("success", result.get("valid", True))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
