"""OAuth device-code login stubs. No paid API calls. Tokens never enter git."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUTH_PATH = Path.home() / ".themis" / "auth.json"
PROVIDERS = ("xai", "openai")

# Documented endpoints. Stubs do not call them. No spend.
DEVICE_ENDPOINTS = {
    "xai": {
        "verification_url": "https://auth.x.ai/device",
        "device_code_url": "https://auth.x.ai/oauth/device/code",
        "token_url": "https://auth.x.ai/oauth/token",
    },
    "openai": {
        "verification_url": "https://auth.openai.com/device",
        "device_code_url": "https://auth.openai.com/api/accounts/deviceauth",
        "token_url": "https://auth.openai.com/api/accounts/token",
    },
}


class AuthError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_auth(path: Path | None = None) -> dict[str, Any]:
    p = path or AUTH_PATH
    if not p.exists():
        return {k: {"logged_in": False} for k in PROVIDERS}
    data = json.loads(p.read_text())
    if not isinstance(data, dict):
        return {k: {"logged_in": False} for k in PROVIDERS}
    return data


def save_auth(data: dict[str, Any], path: Path | None = None) -> Path:
    p = path or AUTH_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    clean: dict[str, Any] = {}
    for k in PROVIDERS:
        rec = dict(data.get(k) or {})
        rec.pop("access_token", None)
        rec.pop("refresh_token", None)
        rec.pop("token", None)
        rec.pop("id_token", None)
        clean[k] = rec
    p.write_text(json.dumps(clean, indent=2) + "\n")
    p.chmod(0o600)
    return p


def is_logged_in(provider: str, path: Path | None = None) -> bool:
    if provider not in PROVIDERS:
        raise AuthError(f"unknown provider {provider}")
    rec = load_auth(path).get(provider) or {}
    return bool(rec.get("logged_in"))


def login(provider: str, path: Path | None = None) -> dict[str, Any]:
    """Device-code stub. Writes ~/.themis/auth.json. Does not network. Does not call a model."""
    if provider not in PROVIDERS:
        raise AuthError(f"unknown provider {provider}; expected xai|openai")
    ep = DEVICE_ENDPOINTS[provider]
    data = load_auth(path)
    data[provider] = {
        "logged_in": True,
        "stub": True,
        "token_present": False,
        "logged_in_at": _now(),
        "note": "device-code stub; no vendor call; no live compile; no spend",
        "verification_url": ep["verification_url"],
        "user_code": "THEMIS-STUB",
    }
    save_auth(data, path)
    return {
        "provider": provider,
        "logged_in": True,
        "stub": True,
        "verification_url": ep["verification_url"],
        "user_code": "THEMIS-STUB",
        "message": (
            f"stub login for {provider}. printed URL {ep['verification_url']} code THEMIS-STUB. "
            "no vendor OAuth call. no model call. no spend. "
            "live compile still refused until Amir leaves mock."
        ),
    }


def logout(provider: str, path: Path | None = None) -> dict[str, Any]:
    if provider not in PROVIDERS:
        raise AuthError(f"unknown provider {provider}")
    data = load_auth(path)
    data[provider] = {"logged_in": False, "logged_out_at": _now()}
    save_auth(data, path)
    return {"provider": provider, "logged_in": False}


def whoami(path: Path | None = None) -> list[dict[str, Any]]:
    data = load_auth(path)
    rows = []
    for k in PROVIDERS:
        rec = data.get(k) or {}
        rows.append(
            {
                "provider": k,
                "logged_in": bool(rec.get("logged_in")),
                "stub": bool(rec.get("stub")),
            }
        )
    return rows


def require_login(provider: str) -> None:
    if not is_logged_in(provider):
        raise AuthError(
            f"not logged in for {provider}. themis login {provider}. no fallback to mock."
        )
