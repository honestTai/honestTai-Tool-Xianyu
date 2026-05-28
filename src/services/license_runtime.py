"""HTTP license client used by the packaged desktop executable.

The authorization server and admin UI live in a separate repository.  This
module intentionally contains only the customer-runtime pieces that the Xianyu
exe must carry: device fingerprinting, activation, validation, heartbeat, and a
small local cache.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import platform
import secrets
import socket
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_ID = "honestTai-Tool-Xianyu"
APP_VERSION = "2.0.0"
DEFAULT_HEARTBEAT_SECONDS = 300
DEFAULT_CLIENT_SECRET = "honesttai-xianyu-license-client-v1"
_DOTENV_LOADED = False


class LicenseError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class LicenseStatus:
    enabled: bool
    authorized: bool
    code: str
    message: str
    expires_at: str | None = None
    device_id: str | None = None
    server_url: str | None = None
    last_validated_at: str | None = None
    heartbeat_interval_seconds: int = DEFAULT_HEARTBEAT_SECONDS


def _truthy(value: str | None) -> bool | None:
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return None


def _runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def _load_dotenv_once() -> None:
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    _DOTENV_LOADED = True
    try:
        from dotenv import load_dotenv

        load_dotenv(_runtime_dir() / ".env", override=False)
    except Exception:
        pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_windows_machine_guid() -> str:
    if sys.platform != "win32":
        return ""
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
            value, _ = winreg.QueryValueEx(key, "MachineGuid")
            return str(value)
    except Exception:
        return ""


def _device_seed() -> str:
    parts = [
        APP_ID,
        _read_windows_machine_guid(),
        platform.node(),
        platform.machine(),
        platform.processor(),
        os.getenv("PROCESSOR_IDENTIFIER", ""),
        os.getenv("COMPUTERNAME", ""),
    ]
    return "|".join(part.strip() for part in parts if part and part.strip())


def build_device_fingerprint() -> str:
    seed = _device_seed() or f"{APP_ID}|{socket.gethostname()}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _canonical_payload(payload: dict[str, Any]) -> str:
    items = []
    for key in sorted(payload):
        if key == "signature":
            continue
        items.append(f"{key}={_canonical_value(payload[key])}")
    return "&".join(items)


def _canonical_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return str(value)


def sign_payload(payload: dict[str, Any], secret: str) -> str:
    canonical = _canonical_payload(payload)
    digest = hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


class LicenseManager:
    def __init__(self) -> None:
        self._status = LicenseStatus(
            enabled=self.is_enabled(),
            authorized=False,
            code="LICENSE_UNKNOWN",
            message="授权状态尚未校验",
        )

    @property
    def cache_path(self) -> Path:
        _load_dotenv_once()
        configured = os.getenv("LICENSE_CACHE_PATH", "").strip()
        if configured:
            return Path(configured)
        return _runtime_dir() / "state" / "license.dat"

    @property
    def client_secret(self) -> str:
        _load_dotenv_once()
        return os.getenv("LICENSE_CLIENT_SECRET", DEFAULT_CLIENT_SECRET)

    @property
    def configured_server_url(self) -> str:
        _load_dotenv_once()
        return os.getenv("LICENSE_SERVER_URL", "").strip().rstrip("/")

    def is_enabled(self) -> bool:
        _load_dotenv_once()
        configured = _truthy(os.getenv("LICENSE_ENFORCEMENT_ENABLED"))
        if configured is not None:
            return configured
        return bool(getattr(sys, "frozen", False))

    def get_status(self) -> LicenseStatus:
        if not self.is_enabled():
            return LicenseStatus(
                enabled=False,
                authorized=True,
                code="LICENSE_DISABLED",
                message="授权校验未启用",
            )
        cache = self.load_cache()
        if self._status.authorized:
            return self._status
        if cache:
            return LicenseStatus(
                enabled=True,
                authorized=False,
                code=self._status.code,
                message=self._status.message,
                expires_at=cache.get("expiresAt"),
                device_id=cache.get("deviceId"),
                server_url=cache.get("serverUrl"),
                last_validated_at=cache.get("lastValidatedAt"),
                heartbeat_interval_seconds=int(cache.get("heartbeatIntervalSeconds") or DEFAULT_HEARTBEAT_SECONDS),
            )
        return LicenseStatus(
            enabled=True,
            authorized=False,
            code="LICENSE_NOT_ACTIVATED",
            message="尚未激活授权",
            server_url=self.configured_server_url or None,
        )

    def load_cache(self) -> dict[str, Any] | None:
        try:
            if not self.cache_path.exists():
                return None
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def save_cache(self, payload: dict[str, Any]) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _request(self, server_url: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        server = server_url.strip().rstrip("/")
        if not server:
            raise LicenseError("LICENSE_SERVER_MISSING", "未配置授权服务器地址")
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{server}{path}",
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            try:
                payload = json.loads(detail)
                code = str(payload.get("code") or payload.get("error") or "LICENSE_REJECTED")
                message = str(payload.get("message") or payload.get("detail") or "授权服务器拒绝请求")
            except Exception:
                code = "LICENSE_REJECTED"
                message = detail or "授权服务器拒绝请求"
            raise LicenseError(code, message) from exc
        except Exception as exc:
            raise LicenseError("LICENSE_SERVER_UNAVAILABLE", f"无法连接授权服务器: {exc}") from exc

        try:
            parsed = json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise LicenseError("LICENSE_BAD_RESPONSE", "授权服务器返回了无效响应") from exc
        if not isinstance(parsed, dict):
            raise LicenseError("LICENSE_BAD_RESPONSE", "授权服务器返回了无效响应")
        self._verify_server_response(parsed)
        return parsed

    def _verify_server_response(self, payload: dict[str, Any]) -> None:
        signature = str(payload.get("signature") or "")
        if not signature:
            raise LicenseError("LICENSE_BAD_SIGNATURE", "授权服务器响应缺少签名")
        expected = sign_payload(payload, self.client_secret)
        if not hmac.compare_digest(signature, expected):
            raise LicenseError("LICENSE_BAD_SIGNATURE", "授权服务器响应签名无效")

    def _base_payload(self, license_key: str | None = None, device_id: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "appId": APP_ID,
            "appVersion": APP_VERSION,
            "deviceFingerprint": build_device_fingerprint(),
            "deviceName": platform.node() or socket.gethostname(),
            "timestamp": int(time.time()),
            "nonce": secrets.token_hex(16),
        }
        if license_key:
            payload["licenseKey"] = license_key
        if device_id:
            payload["deviceId"] = device_id
        payload["signature"] = sign_payload(payload, self.client_secret)
        return payload

    def activate(self, license_key: str, server_url: str | None = None) -> LicenseStatus:
        target_server = (server_url or self.configured_server_url).strip().rstrip("/")
        response = self._request(target_server, "/api/client/activate", self._base_payload(license_key=license_key))
        cache = {
            "licenseKey": license_key,
            "deviceId": response.get("deviceId"),
            "serverUrl": target_server,
            "expiresAt": response.get("expiresAt"),
            "lastValidatedAt": _utc_now(),
            "heartbeatIntervalSeconds": int(response.get("heartbeatIntervalSeconds") or DEFAULT_HEARTBEAT_SECONDS),
            "serverSignature": response.get("signature"),
        }
        self.save_cache(cache)
        self._mark_authorized(cache, "LICENSE_VALID", str(response.get("message") or "授权激活成功"))
        return self._status

    def validate(self) -> LicenseStatus:
        cache = self.load_cache()
        if not cache:
            raise LicenseError("LICENSE_NOT_ACTIVATED", "尚未激活授权")
        response = self._request(
            str(cache.get("serverUrl") or self.configured_server_url),
            "/api/client/validate",
            self._base_payload(
                license_key=str(cache.get("licenseKey") or ""),
                device_id=str(cache.get("deviceId") or ""),
            ),
        )
        cache.update(
            {
                "expiresAt": response.get("expiresAt") or cache.get("expiresAt"),
                "lastValidatedAt": _utc_now(),
                "heartbeatIntervalSeconds": int(response.get("heartbeatIntervalSeconds") or cache.get("heartbeatIntervalSeconds") or DEFAULT_HEARTBEAT_SECONDS),
                "serverSignature": response.get("signature") or cache.get("serverSignature"),
            }
        )
        self.save_cache(cache)
        self._mark_authorized(cache, "LICENSE_VALID", str(response.get("message") or "授权有效"))
        return self._status

    def heartbeat_once(self) -> LicenseStatus:
        cache = self.load_cache()
        if not cache:
            raise LicenseError("LICENSE_NOT_ACTIVATED", "尚未激活授权")
        response = self._request(
            str(cache.get("serverUrl") or self.configured_server_url),
            "/api/client/heartbeat",
            self._base_payload(
                license_key=str(cache.get("licenseKey") or ""),
                device_id=str(cache.get("deviceId") or ""),
            ),
        )
        cache.update(
            {
                "expiresAt": response.get("expiresAt") or cache.get("expiresAt"),
                "lastValidatedAt": _utc_now(),
                "heartbeatIntervalSeconds": int(response.get("heartbeatIntervalSeconds") or cache.get("heartbeatIntervalSeconds") or DEFAULT_HEARTBEAT_SECONDS),
                "serverSignature": response.get("signature") or cache.get("serverSignature"),
            }
        )
        self.save_cache(cache)
        self._mark_authorized(cache, "LICENSE_VALID", str(response.get("message") or "授权心跳正常"))
        return self._status

    def ensure_startup_authorized(self, *, interactive: bool = False) -> LicenseStatus:
        if not self.is_enabled():
            self._status = LicenseStatus(
                enabled=False,
                authorized=True,
                code="LICENSE_DISABLED",
                message="授权校验未启用",
            )
            return self._status

        if not self.load_cache() and interactive:
            self._interactive_activate()

        try:
            return self.validate()
        except LicenseError as exc:
            self._mark_failed(exc)
            raise

    def _interactive_activate(self) -> None:
        try:
            import tkinter as tk
            from tkinter import messagebox, simpledialog

            root = tk.Tk()
            root.withdraw()
            server_url = self.configured_server_url
            if not server_url:
                server_url = simpledialog.askstring("授权服务器", "请输入授权服务器地址:", parent=root) or ""
            license_key = simpledialog.askstring("软件授权", "请输入授权码:", parent=root) or ""
            if not server_url.strip() or not license_key.strip():
                raise LicenseError("LICENSE_NOT_ACTIVATED", "未输入授权服务器或授权码")
            self.activate(license_key.strip(), server_url.strip())
            messagebox.showinfo("软件授权", "授权激活成功", parent=root)
            root.destroy()
        except LicenseError:
            raise
        except Exception as exc:
            raise LicenseError("LICENSE_ACTIVATION_FAILED", f"授权激活失败: {exc}") from exc

    def _mark_authorized(self, cache: dict[str, Any], code: str, message: str) -> None:
        self._status = LicenseStatus(
            enabled=True,
            authorized=True,
            code=code,
            message=message,
            expires_at=cache.get("expiresAt"),
            device_id=cache.get("deviceId"),
            server_url=cache.get("serverUrl"),
            last_validated_at=cache.get("lastValidatedAt"),
            heartbeat_interval_seconds=int(cache.get("heartbeatIntervalSeconds") or DEFAULT_HEARTBEAT_SECONDS),
        )

    def _mark_failed(self, exc: LicenseError) -> None:
        current = self.get_status()
        self._status = LicenseStatus(
            enabled=True,
            authorized=False,
            code=exc.code,
            message=exc.message,
            expires_at=current.expires_at,
            device_id=current.device_id,
            server_url=current.server_url,
            last_validated_at=current.last_validated_at,
            heartbeat_interval_seconds=current.heartbeat_interval_seconds,
        )

    def mark_failed(self, exc: LicenseError) -> None:
        self._mark_failed(exc)


license_manager = LicenseManager()
