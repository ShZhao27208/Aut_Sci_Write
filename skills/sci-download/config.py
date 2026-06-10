"""Configuration management for Aut_Sci_Download.

API keys are stored in the unified ~/.aut_sci_write/.env file.
Other settings (school, output_dir, proxy) stay in config.json under DATA_DIR.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent

DATA_DIR = Path(os.environ.get("AUT_SCI_DATA_DIR", str(Path.home() / ".aut_sci_write")))
CONFIG_FILE = DATA_DIR / "sci-download" / "config.json"


def _init_shared_env():
    """Import unified env config from _shared module."""
    shared_path = _SCRIPT_DIR.parent / "_shared" / "env_config.py"
    if shared_path.exists():
        spec = importlib.util.spec_from_file_location("_shared.env_config", shared_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    return None


_ENV_MOD = _init_shared_env()
ENV_FILE = _ENV_MOD.ENV_FILE if _ENV_MOD else DATA_DIR / ".env"

ENV_KEYS = [
    "ELSEVIER_API_KEY",
    "ELSEVIER_INSTTOKEN",
    "SPRINGER_API_KEY",
    "IEEE_API_KEY",
    "UNPAYWALL_EMAIL",
    "NCBI_API_KEY",
    "SEMANTIC_SCHOLAR_API_KEY",
]

ENV_TEMPLATE = """\
# Aut_Sci_Download API Keys
# Elsevier: https://dev.elsevier.com/ (free)
ELSEVIER_API_KEY=
ELSEVIER_INSTTOKEN=
# Springer Nature: https://dev.springernature.com/ (free, OA only)
SPRINGER_API_KEY=
# IEEE Xplore: https://developer.ieee.org/ (free tier)
IEEE_API_KEY=
# Unpaywall: just your email address
UNPAYWALL_EMAIL=
# NCBI/PubMed: https://www.ncbi.nlm.nih.gov/account/settings/ (free)
NCBI_API_KEY=
"""

WEBVPN_DEFAULT_KEY = "wrdvpnisthebest!"
WEBVPN_DEFAULT_IV = "wrdvpnisthebest!"

_ENV_TO_CONFIG = {
    "ELSEVIER_API_KEY": "elsevier_api_key",
    "ELSEVIER_INSTTOKEN": "elsevier_insttoken",
    "SPRINGER_API_KEY": "springer_api_key",
    "IEEE_API_KEY": "ieee_api_key",
    "UNPAYWALL_EMAIL": "unpaywall_email",
    "NCBI_API_KEY": "ncbi_api_key",
    "SEMANTIC_SCHOLAR_API_KEY": "semantic_scholar_api_key",
}

DEFAULT_CONFIG: dict[str, Any] = {
    "elsevier_api_key": "",
    "elsevier_insttoken": "",
    "springer_api_key": "",
    "ieee_api_key": "",
    "unpaywall_email": "",
    "ncbi_api_key": "",
    "semantic_scholar_api_key": "",
    "webvpn_school": "",
    "webvpn_host": "",
    "webvpn_crypto_key": "",
    "webvpn_crypto_iv": "",
    "output_dir": str(Path.home() / "papers"),
    "proxy": "",
    "cookie_file": str(DATA_DIR / "webvpn_cookies.json"),
}


def _parse_env(path: Path) -> dict[str, str]:
    """Parse a .env file into a dict. Ignores comments and empty lines."""
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^([A-Z_]+)\s*=\s*(.*?)$", line)
        if m:
            env[m.group(1)] = m.group(2).strip().strip("\"'")
    return env


def _ensure_env_file() -> None:
    """Ensure unified .env exists (delegated to shared module)."""
    if _ENV_MOD:
        _ENV_MOD.ensure_env_dir()
    else:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not ENV_FILE.exists():
            ENV_FILE.write_text(ENV_TEMPLATE, encoding="utf-8")


def _write_env_key(key: str, value: str) -> None:
    """Set a key in the .env file, preserving other entries."""
    _ensure_env_file()
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    found = False
    for i, line in enumerate(lines):
        if re.match(rf"^{re.escape(key)}\s*=", line):
            lines[i] = f"{key}={value}"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_config() -> dict[str, Any]:
    """Load config from config.json, then overlay API keys from .env."""
    config = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            existing = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                config.update(existing)
        except Exception:
            pass
    env = _parse_env(ENV_FILE)
    for env_key, config_key in _ENV_TO_CONFIG.items():
        val = env.get(env_key, "")
        if val:
            config[config_key] = val
    return config


def save_config(config: dict[str, Any]) -> None:
    """Save non-secret config to config.json (API keys go to .env)."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    json_config = {k: v for k, v in config.items() if k not in _ENV_TO_CONFIG.values() or not v}
    for env_key, config_key in _ENV_TO_CONFIG.items():
        json_config.pop(config_key, None)
    CONFIG_FILE.write_text(json.dumps(json_config, indent=2, ensure_ascii=False), encoding="utf-8")


def update_config(key: str, value: str) -> dict[str, Any]:
    """Update a config value. API keys are written to .env, others to config.json."""
    config_to_env = {v: k for k, v in _ENV_TO_CONFIG.items()}
    if key in config_to_env:
        _write_env_key(config_to_env[key], value)
    else:
        config = load_config()
        if key in config and isinstance(config[key], bool):
            config[key] = value.lower() in ("true", "1", "yes")
        else:
            config[key] = value
        save_config(config)
    return load_config()


def get_schools_file() -> Path:
    return Path(__file__).parent / "schools.json"


def resolve_school(school_name: str) -> dict[str, str] | None:
    """Look up a school in schools.json, return {host, crypto_key, crypto_iv} or None."""
    schools_file = get_schools_file()
    if not schools_file.exists():
        return None
    data = json.loads(schools_file.read_text(encoding="utf-8"))
    for province, schools in data.items():
        if school_name in schools:
            entry = schools[school_name]
            return {
                "host": f"https://{entry['host']}",
                "crypto_key": entry.get("crypto_key", WEBVPN_DEFAULT_KEY),
                "crypto_iv": entry.get("crypto_iv", WEBVPN_DEFAULT_IV),
            }
    return None
