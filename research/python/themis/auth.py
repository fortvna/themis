"""OAuth device-code login for live compilers. Tokens live only in ~/.themis/auth.json."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUTH_PATH = Path.home() / ".themis" / "auth.json"
PROVIDERS = ("xai", "openai")

XAI_CLIENT_ID = "b1a00492-073a-47ea-816f-4c329264a828"
XAI_SCOPE = "openid profile email offline_access grok-cli:access api:access"
XAI_DEVICE_URL = "https://auth.x.ai/oauth2/device/code"
XAI_TOKEN_URL = "https://auth.x.ai/oauth2/token"
XAI_GRANT_DEVICE = "urn:ietf:params:oauth:grant-type:device_code"
GROK_RESPONSES_URL = "https://cli-chat-proxy.grok.com/v1/responses"
GROK_CLI_VERSION = "0.2.114"
GROK_MODEL = "grok-4"

DEVICE_ENDPOINTS = {
    "xai": {
        "verification_url": "https://accounts.x.ai/oauth2/device",
        "device_code_url": XAI_DEVICE_URL,
        "token_url": XAI_TOKEN_URL,
        "client_id": XAI_CLIENT_ID,
        "scope": XAI_SCOPE,
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


def _now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


def load_auth(path: Path | None = None) -> dict[str, Any]:
    p = path or AUTH_PATH
    if not p.exists():
        return {k: {"logged_in": False} for k in PROVIDERS}
    data = json.loads(p.read_text())
    if not isinstance(data, dict):
        return {k: {"logged_in": False} for k in PROVIDERS}
    return data


def save_auth(data: dict[str, Any], path: Path | None = None) -> Path:
    """Persist auth including access/refresh tokens. Mode 0600. Never strip tokens."""
    p = path or AUTH_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    out: dict[str, Any] = {}
    for k in PROVIDERS:
        rec = dict(data.get(k) or {})
        out[k] = rec
    p.write_text(json.dumps(out, indent=2) + "\n")
    p.chmod(0o600)
    return p


def _record(provider: str, path: Path | None = None) -> dict[str, Any]:
    return dict(load_auth(path).get(provider) or {})


def _has_live_token(rec: dict[str, Any]) -> bool:
    if rec.get("stub"):
        return False
    return bool(rec.get("access_token") or rec.get("refresh_token"))


def is_logged_in(provider: str, path: Path | None = None) -> bool:
    if provider not in PROVIDERS:
        raise AuthError(f"unknown provider {provider}")
    rec = _record(provider, path)
    if _has_live_token(rec):
        return True
    return bool(rec.get("logged_in")) and not rec.get("stub", True) and bool(rec.get("token_present"))


def _form_post(url: str, data: dict[str, str], headers: dict[str, str] | None = None) -> tuple[int, dict[str, Any]]:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("Accept", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            try:
                payload = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                payload = {"raw": raw}
            return int(resp.status), payload
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"error": raw}
        return int(e.code), payload


def _json_post(url: str, payload: dict[str, Any], headers: dict[str, str]) -> tuple[int, Any]:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode()
            try:
                data = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                data = {"raw": raw}
            return int(resp.status), data
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {"error": raw}
        return int(e.code), data


def _store_xai_tokens(payload: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    data = load_auth(path)
    expires_in = payload.get("expires_in")
    try:
        expires_at = _now_ts() + float(expires_in) if expires_in is not None else None
    except (TypeError, ValueError):
        expires_at = None
    rec = {
        "logged_in": True,
        "stub": False,
        "token_present": True,
        "logged_in_at": _now(),
        "token_type": payload.get("token_type"),
        "expires_in": expires_in,
        "expires_at": expires_at,
        "scope": payload.get("scope"),
        "access_token": payload.get("access_token"),
        "refresh_token": payload.get("refresh_token") or (_record("xai", path).get("refresh_token")),
        "id_token": payload.get("id_token"),
    }
    data["xai"] = rec
    data["openai"] = data.get("openai") or {"logged_in": False}
    save_auth(data, path)
    return rec


def login(provider: str, path: Path | None = None) -> dict[str, Any]:
    """Device-code OAuth. xai is live. openai stays a no-network stub."""
    if provider not in PROVIDERS:
        raise AuthError(f"unknown provider {provider}; expected xai|openai")
    if provider == "openai":
        ep = DEVICE_ENDPOINTS[provider]
        data = load_auth(path)
        data[provider] = {
            "logged_in": True,
            "stub": True,
            "token_present": False,
            "logged_in_at": _now(),
            "note": "openai device-code stub; no vendor call",
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
            "message": "stub login for openai. no vendor OAuth call. no spend.",
        }
    rec = _record("xai", path)
    if _has_live_token(rec):
        return {
            "provider": "xai",
            "logged_in": True,
            "stub": False,
            "token_present": True,
            "message": "already logged in to xai. tokens kept in ~/.themis/auth.json.",
        }
    status, payload = _form_post(
        XAI_DEVICE_URL,
        {"client_id": XAI_CLIENT_ID, "scope": XAI_SCOPE},
    )
    if status != 200 or not payload.get("device_code"):
        raise AuthError(f"xai device-code request failed status={status} error={payload.get('error')}")
    device_code = payload["device_code"]
    interval = max(int(payload.get("interval") or 5), 5)
    expires_in = int(payload.get("expires_in") or 1800)
    verify = payload.get("verification_uri") or payload.get("verification_url") or DEVICE_ENDPOINTS["xai"]["verification_url"]
    user_code = payload.get("user_code")
    complete = payload.get("verification_uri_complete")
    print(f"xai login: open {verify} and enter code {user_code}")
    if complete:
        print(f"or open {complete}")
    deadline = time.time() + expires_in
    while time.time() < deadline:
        t_status, t_payload = _form_post(
            XAI_TOKEN_URL,
            {
                "grant_type": XAI_GRANT_DEVICE,
                "client_id": XAI_CLIENT_ID,
                "device_code": device_code,
            },
        )
        err = t_payload.get("error") if isinstance(t_payload, dict) else None
        if t_status == 200 and t_payload.get("access_token"):
            _store_xai_tokens(t_payload, path)
            return {
                "provider": "xai",
                "logged_in": True,
                "stub": False,
                "token_present": True,
                "verification_url": verify,
                "user_code": user_code,
                "message": "authorized. tokens in ~/.themis/auth.json mode 0600.",
            }
        if err in ("authorization_pending", "slow_down"):
            if err == "slow_down":
                interval += 5
            time.sleep(interval)
            continue
        raise AuthError(f"xai login failed status={t_status} error={err or t_payload}")
    raise AuthError("xai device-code expired. Amir must re-approve.")


def logout(provider: str, path: Path | None = None) -> dict[str, Any]:
    if provider not in PROVIDERS:
        raise AuthError(f"unknown provider {provider}")
    data = load_auth(path)
    data[provider] = {"logged_in": False, "stub": False, "token_present": False, "logged_out_at": _now()}
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
                "logged_in": is_logged_in(k, path) if k in PROVIDERS else False,
                "stub": bool(rec.get("stub")),
                "token_present": bool(rec.get("access_token") or rec.get("token_present")),
            }
        )
    return rows


def require_login(provider: str, path: Path | None = None) -> None:
    if provider not in PROVIDERS:
        raise AuthError(f"unknown provider {provider}")
    rec = _record(provider, path)
    if not _has_live_token(rec):
        raise AuthError(
            f"not logged in for {provider}. themis login {provider}. no fallback to mock."
        )


def refresh_access_token(provider: str = "xai", path: Path | None = None) -> str:
    if provider != "xai":
        raise AuthError(f"refresh not implemented for {provider}")
    rec = _record(provider, path)
    refresh = rec.get("refresh_token")
    if not refresh:
        raise AuthError("not logged in for xai. themis login xai. no fallback to mock.")
    status, payload = _form_post(
        XAI_TOKEN_URL,
        {
            "grant_type": "refresh_token",
            "client_id": XAI_CLIENT_ID,
            "refresh_token": refresh,
        },
    )
    if status != 200 or not payload.get("access_token"):
        raise AuthError(f"xai refresh failed status={status} error={payload.get('error')}")
    _store_xai_tokens(payload, path)
    return str(payload["access_token"])


def get_access_token(provider: str = "xai", path: Path | None = None) -> str:
    require_login(provider, path)
    rec = _record(provider, path)
    token = rec.get("access_token")
    exp = rec.get("expires_at")
    if token and exp:
        try:
            if float(exp) - 60 < _now_ts():
                token = None
        except (TypeError, ValueError):
            pass
    if not token:
        token = refresh_access_token(provider, path)
    if not token:
        raise AuthError(f"not logged in for {provider}. themis login {provider}. no fallback to mock.")
    return str(token)


def _extract_text(payload: Any) -> str:
    if isinstance(payload, str):
        return payload
    if not isinstance(payload, dict):
        return ""
    if isinstance(payload.get("output_text"), str) and payload["output_text"].strip():
        return payload["output_text"]
    parts: list[str] = []
    for item in payload.get("output") or []:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if isinstance(content, str):
            parts.append(content)
            continue
        for c in content or []:
            if isinstance(c, dict) and c.get("text"):
                parts.append(str(c["text"]))
            elif isinstance(c, str):
                parts.append(c)
    if parts:
        return "\n".join(parts)
    choices = payload.get("choices") or []
    if choices and isinstance(choices[0], dict):
        msg = choices[0].get("message") or {}
        if isinstance(msg, dict) and msg.get("content"):
            return str(msg["content"])
    return json.dumps(payload)


def grok_complete(system: str, user: str, *, path: Path | None = None, model: str | None = None) -> str:
    """POST cli-chat-proxy /v1/responses with the OAuth access token. Refresh on 401."""
    model = model or GROK_MODEL
    token = get_access_token("xai", path)

    def _headers(tok: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {tok}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-XAI-Token-Auth": "xai-grok-cli",
            "x-grok-client-identifier": "grok-shell",
            "x-grok-client-version": GROK_CLI_VERSION,
            "User-Agent": f"xai-grok-workspace/{GROK_CLI_VERSION}",
            "x-grok-model-override": model,
        }

    body = {
        "model": model,
        "instructions": system,
        "input": user,
        "stream": False,
        "temperature": 0,
    }
    status, payload = _json_post(GROK_RESPONSES_URL, body, _headers(token))
    if status == 401:
        token = refresh_access_token("xai", path)
        status, payload = _json_post(GROK_RESPONSES_URL, body, _headers(token))
    if status == 401:
        raise AuthError("xai 401 after refresh. Amir must re-approve. no fallback to mock.")
    if status < 200 or status >= 300:
        err = payload.get("error") if isinstance(payload, dict) else payload
        raise AuthError(f"grok responses failed status={status} error={err}")
    text = _extract_text(payload).strip()
    if not text:
        raise AuthError("grok responses returned empty text. no fallback to mock.")
    return text
