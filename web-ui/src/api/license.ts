export interface LicenseStatus {
  enabled: boolean
  authorized: boolean
  code: string
  message: string
  expiresAt?: string | null
  deviceId?: string | null
  serverUrl?: string | null
  lastValidatedAt?: string | null
  heartbeatIntervalSeconds?: number
}

export async function getLicenseStatus(): Promise<LicenseStatus> {
  const response = await fetch('/api/license/status')
  if (!response.ok) {
    throw new Error(`License status failed: ${response.status}`)
  }
  return response.json()
}

export async function activateLicense(payload: {
  licenseKey: string
  serverUrl?: string
}): Promise<LicenseStatus> {
  const response = await fetch('/api/license/activate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      license_key: payload.licenseKey,
      server_url: payload.serverUrl,
    }),
  })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = body.detail || body
    throw new Error(detail.message || detail.detail || '授权激活失败')
  }
  return body
}
