"""Local license activation/status endpoints.

These endpoints are intentionally tiny: they only talk to the external
authorization server and expose the local runtime status needed by the packaged
web UI.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.services.license_runtime import LicenseError, license_manager

router = APIRouter(prefix="/api/license", tags=["license"])


class LicenseActivationRequest(BaseModel):
    license_key: str = Field(..., min_length=1)
    server_url: str | None = Field(None, min_length=1)


def _status_payload():
    status = license_manager.get_status()
    return {
        "enabled": status.enabled,
        "authorized": status.authorized,
        "code": status.code,
        "message": status.message,
        "expiresAt": status.expires_at,
        "deviceId": status.device_id,
        "serverUrl": status.server_url,
        "lastValidatedAt": status.last_validated_at,
        "heartbeatIntervalSeconds": status.heartbeat_interval_seconds,
    }


@router.get("/status")
async def license_status():
    license_manager.refresh_authorization(force=True)
    return _status_payload()


@router.post("/activate")
async def activate_license(payload: LicenseActivationRequest):
    try:
        license_manager.activate(payload.license_key.strip(), payload.server_url.strip() if payload.server_url else None)
    except LicenseError as exc:
        license_manager.mark_failed(exc)
        raise HTTPException(
            status_code=403,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    return _status_payload()
