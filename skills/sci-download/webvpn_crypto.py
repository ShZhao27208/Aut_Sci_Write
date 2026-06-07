"""WebVPN URL encryption using AES-CFB.

Converts regular URLs to WebVPN proxy URLs by encrypting the hostname
with AES-128-CFB (128-bit segment). Each university may have its own
key/iv pair; defaults to the standard "wrdvpnisthebest!" key.
"""

from __future__ import annotations

import binascii
import urllib.parse


def convert_url(
    url: str,
    webvpn_base: str,
    key: str = "wrdvpnisthebest!",
    iv: str = "wrdvpnisthebest!",
) -> str:
    """Convert a regular URL to a WebVPN-proxied URL.

    Args:
        url: Original URL (e.g. https://kns.cnki.net/kns8/...)
        webvpn_base: WebVPN base (e.g. https://webvpn.tsinghua.edu.cn)
        key: AES-128 key (16 bytes as string)
        iv: AES-128 IV (16 bytes as string)

    Returns:
        WebVPN-proxied URL
    """
    from Crypto.Cipher import AES

    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname
    port = parsed.port
    path = parsed.path
    query = parsed.query

    if not hostname:
        return url

    key_bytes = key.encode("utf-8")[:16]
    iv_bytes = iv.encode("utf-8")[:16]

    cipher = AES.new(key_bytes, AES.MODE_CFB, iv_bytes, segment_size=128)
    encrypted = cipher.encrypt(hostname.encode("utf-8"))

    encrypted_hex = binascii.hexlify(iv_bytes).decode() + binascii.hexlify(encrypted).decode()

    scheme_part = scheme
    if port:
        scheme_part = f"{scheme}-{port}"

    result = f"{webvpn_base.rstrip('/')}/{scheme_part}/{encrypted_hex}{path}"
    if query:
        result += f"?{query}"
    return result
