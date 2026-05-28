import json

import pytest

from src.services.license_runtime import LicenseError, LicenseManager, build_device_fingerprint, sign_payload


def test_device_fingerprint_is_stable():
    first = build_device_fingerprint()
    second = build_device_fingerprint()

    assert first == second
    assert len(first) == 64


def test_signature_ignores_signature_field():
    payload = {"b": "2", "a": "1", "signature": "old"}

    assert sign_payload(payload, "secret") == sign_payload({"a": "1", "b": "2"}, "secret")


def test_signature_uses_java_compatible_boolean_values():
    payload = {"ok": True, "heartbeatIntervalSeconds": 300}
    equivalent = {"ok": "true", "heartbeatIntervalSeconds": "300"}

    assert sign_payload(payload, "secret") == sign_payload(equivalent, "secret")


def test_server_response_signature_is_verified(monkeypatch):
    monkeypatch.setenv("LICENSE_CLIENT_SECRET", "secret")
    manager = LicenseManager()
    response = {
        "ok": True,
        "deviceId": "device-1",
        "expiresAt": "2026-12-31T00:00:00Z",
        "heartbeatIntervalSeconds": 60,
    }
    response["signature"] = sign_payload(response, "secret")

    manager._verify_server_response(response)


def test_bad_server_response_signature_is_rejected(monkeypatch):
    monkeypatch.setenv("LICENSE_CLIENT_SECRET", "secret")
    manager = LicenseManager()

    with pytest.raises(Exception) as exc_info:
        manager._verify_server_response({"ok": True, "signature": "bad"})

    assert getattr(exc_info.value, "code") == "LICENSE_BAD_SIGNATURE"


def test_license_cache_round_trip(tmp_path, monkeypatch):
    cache_path = tmp_path / "license.dat"
    monkeypatch.setenv("LICENSE_CACHE_PATH", str(cache_path))
    manager = LicenseManager()

    manager.save_cache({"licenseKey": "LIC-1", "deviceId": "device-1"})

    assert json.loads(cache_path.read_text(encoding="utf-8"))["licenseKey"] == "LIC-1"
    assert manager.load_cache()["deviceId"] == "device-1"


def test_activation_saves_server_response(tmp_path, monkeypatch):
    monkeypatch.setenv("LICENSE_CACHE_PATH", str(tmp_path / "license.dat"))
    monkeypatch.setenv("LICENSE_CLIENT_SECRET", "secret")
    manager = LicenseManager()

    def fake_request(server_url, path, payload):
        assert server_url == "https://license.example.com"
        assert path == "/api/client/activate"
        assert payload["licenseKey"] == "LIC-123"
        assert payload["signature"]
        return {
            "deviceId": "device-1",
            "expiresAt": "2026-12-31T00:00:00Z",
            "heartbeatIntervalSeconds": 60,
            "signature": "server-signature",
        }

    monkeypatch.setattr(manager, "_request", fake_request)

    status = manager.activate("LIC-123", "https://license.example.com")

    assert status.authorized is True
    assert status.device_id == "device-1"
    assert manager.load_cache()["serverSignature"] == "server-signature"


def test_refresh_authorization_marks_remote_rejection_failed(tmp_path, monkeypatch):
    monkeypatch.setenv("LICENSE_ENFORCEMENT_ENABLED", "true")
    monkeypatch.setenv("LICENSE_CACHE_PATH", str(tmp_path / "license.dat"))
    manager = LicenseManager()
    manager.save_cache(
        {
            "licenseKey": "LIC-123",
            "deviceId": "device-1",
            "serverUrl": "https://license.example.com",
        }
    )

    def fake_validate():
        raise LicenseError("LICENSE_DISABLED", "授权码已被禁用")

    monkeypatch.setattr(manager, "validate", fake_validate)

    status = manager.refresh_authorization(force=True)

    assert status.authorized is False
    assert status.code == "LICENSE_DISABLED"
    assert status.message == "授权码已被禁用"
