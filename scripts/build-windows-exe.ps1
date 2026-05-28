param(
  [string]$Python = "python",
  [string]$Npm = "npm",
  [string]$LicenseServerUrl = $env:LICENSE_SERVER_URL,
  [string]$LicenseClientSecret = $env:LICENSE_CLIENT_SECRET,
  [string]$LicenseEnforcementEnabled = "true",
  [string]$DistPath = "release",
  [switch]$Console
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Name = "honestTai-Tool-Xianyu"
$Icon = Join-Path $Root "assets\app-icon.ico"
$ReleaseEnvDir = Join-Path $Root "build\release-env"
$ReleaseEnv = Join-Path $ReleaseEnvDir ".env"

Set-Location $Root

if ([string]::IsNullOrWhiteSpace($LicenseClientSecret)) {
  $LicenseClientSecret = "honesttai-xianyu-license-client-v1"
}

if ($LicenseEnforcementEnabled -notin @("true", "false")) {
  throw "LicenseEnforcementEnabled must be true or false."
}

if ($LicenseEnforcementEnabled -eq "true" -and [string]::IsNullOrWhiteSpace($LicenseServerUrl)) {
  Write-Warning "LICENSE_SERVER_URL is empty. The packaged app will ask for the license server address if activation is required."
}

New-Item -ItemType Directory -Force -Path $ReleaseEnvDir | Out-Null
@(
  "SERVER_PORT=8000"
  "WEB_USERNAME=admin"
  "WEB_PASSWORD=admin123"
  "LICENSE_ENFORCEMENT_ENABLED=$LicenseEnforcementEnabled"
  "LICENSE_SERVER_URL=$($LicenseServerUrl.Trim())"
  "LICENSE_CLIENT_SECRET=$($LicenseClientSecret.Trim())"
) | Set-Content -Path $ReleaseEnv -Encoding UTF8

Write-Host "Installing Python dependencies..."
& $Python -m pip install -r requirements.txt

Write-Host "Installing frontend dependencies..."
Push-Location (Join-Path $Root "web-ui")
try {
  & $Npm install --ignore-scripts
  & $Npm run build
}
finally {
  Pop-Location
}

$modeArgs = @()
if (-not $Console) {
  $modeArgs += "--windowed"
}

Write-Host "Building $Name.exe..."
& $Python -m PyInstaller `
  --name $Name `
  --clean `
  --noconfirm `
  --onedir `
  --distpath $DistPath `
  --workpath "build" `
  --icon $Icon `
  @modeArgs `
  --add-data "dist;dist" `
  --add-data "static;static" `
  --add-data "assets;assets" `
  --add-data "$ReleaseEnv;." `
  --add-data ".env.example;." `
  --collect-data webview `
  --collect-submodules webview `
  --collect-data goofish_cli `
  --collect-submodules goofish_cli `
  --paths "third_party\goofish-cli\src" `
  --hidden-import clr `
  --hidden-import clr_loader `
  --hidden-import pythonnet `
  --hidden-import win32timezone `
  desktop_launcher.py

$PublishedDir = Join-Path $Root "$DistPath\$Name"
if (Test-Path $PublishedDir) {
  Copy-Item -Force -LiteralPath $ReleaseEnv -Destination (Join-Path $PublishedDir ".env")
}

Write-Host "Done: $(Join-Path $Root "$DistPath\$Name\$Name.exe")"
