"""Shared HTTP session with retry, rate limiting, and credential scrubbing.

Every outbound request in the harvester goes through here so that API keys can
never leak into an error message or a saved log.
"""

from __future__ import annotations

import time
from typing import Any

import requests

from . import env

USER_AGENT = "sci-extract/2.0 (Aut_Sci_Write; academic research)"

DEFAULT_TIMEOUT = 40
MAX_RETRIES = 3
BACKOFF_BASE = 1.6

# A 429 means we are over a published quota; retrying in under a second just
# burns the attempt. These are seconds to wait per successive 429.
RATE_LIMIT_BACKOFF = (2.0, 6.0, 14.0)
# Longest Retry-After we will honour. Daily-quota APIs (OpenAlex bills per day
# and resets at midnight UTC) answer with tens of thousands of seconds; waiting
# is pointless, so anything beyond this fails immediately instead.
RETRY_AFTER_CEILING = 60.0

# Per-host minimum seconds between requests, to respect published rate limits.
_HOST_INTERVALS = {
    "eutils.ncbi.nlm.nih.gov": 0.35,
    "api.semanticscholar.org": 1.1,
    "api.crossref.org": 0.2,
    "api.openalex.org": 0.5,
    "export.arxiv.org": 3.0,
    "api.unpaywall.org": 0.2,
}

_last_request_at: dict[str, float] = {}


class FetchError(RuntimeError):
    """A request failed in a way the caller should surface but survive."""


def _scrub(text: str) -> str:
    """Replace any configured credential appearing in text with a placeholder."""
    result = str(text)
    for names in env.SOURCE_CREDENTIALS.values():
        for name in names:
            secret = env.key(name)
            if secret and len(secret) > 6 and secret in result:
                result = result.replace(secret, f"<{name}>")
    return result


def _throttle(host: str) -> None:
    interval = _HOST_INTERVALS.get(host)
    if not interval:
        return
    elapsed = time.monotonic() - _last_request_at.get(host, 0.0)
    if elapsed < interval:
        time.sleep(interval - elapsed)
    _last_request_at[host] = time.monotonic()


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


_SHARED = _session()


def request(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    accept: str = "",
    timeout: int = DEFAULT_TIMEOUT,
    allow_404: bool = True,
) -> requests.Response | None:
    """GET a URL with retry and throttling.

    Returns None for 401/403/404 (missing or gated content, an expected outcome)
    and raises FetchError only when the request could not be completed at all.
    """
    host = requests.utils.urlparse(url).netloc
    merged = dict(headers or {})
    if accept:
        merged["Accept"] = accept

    last_error = ""
    for attempt in range(MAX_RETRIES):
        _throttle(host)
        try:
            response = _SHARED.get(
                url, params=params, headers=merged, timeout=timeout, allow_redirects=True
            )
        except requests.RequestException as exc:
            last_error = _scrub(str(exc))
            time.sleep(BACKOFF_BASE**attempt)
            continue

        if response.status_code in (401, 403, 404, 410):
            if allow_404:
                return None
            raise FetchError(f"{response.status_code} for {_scrub(url)}")

        if response.status_code == 429 or response.status_code >= 500:
            last_error = f"HTTP {response.status_code}"
            retry_after = response.headers.get("Retry-After")
            if (retry_after or "").isdigit():
                delay = float(retry_after)
                if delay > RETRY_AFTER_CEILING:
                    # A quota that resets hours from now cannot be waited out, so
                    # sleeping the ceiling three times only delays the same
                    # failure. Report it in terms the caller can act on.
                    raise FetchError(
                        f"HTTP 429 for {_scrub(url)}: quota exhausted, "
                        f"server asks for {int(delay)}s"
                    )
            elif response.status_code == 429:
                # Rate limits need real breathing room, not a sub-second retry.
                delay = RATE_LIMIT_BACKOFF[min(attempt, len(RATE_LIMIT_BACKOFF) - 1)]
            else:
                delay = BACKOFF_BASE**attempt
            time.sleep(min(delay, 30))
            continue

        if not response.ok:
            raise FetchError(f"HTTP {response.status_code} for {_scrub(url)}")

        return response

    raise FetchError(f"request failed after {MAX_RETRIES} attempts: {last_error}")


def get_json(url: str, **kwargs) -> dict | None:
    """GET and parse JSON, tolerating a non-JSON body by returning None."""
    kwargs.setdefault("accept", "application/json")
    response = request(url, **kwargs)
    if response is None:
        return None
    try:
        return response.json()
    except ValueError:
        return None


def get_text(url: str, **kwargs) -> str | None:
    response = request(url, **kwargs)
    if response is None:
        return None
    response.encoding = response.encoding or "utf-8"
    return response.text


def get_bytes(url: str, **kwargs) -> bytes | None:
    response = request(url, **kwargs)
    return response.content if response is not None else None


def scrub(text: str) -> str:
    """Public wrapper so callers can sanitize their own messages."""
    return _scrub(text)
