param(
  [string]$Python = "python",
  [string]$Npm = "npm",
  [switch]$Console
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Name = "honestTai-Tool-Xianyu"
$Icon = Join-Path $Root "assets\app-icon.ico"

Set-Location $Root

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
  --distpath "release" `
  --workpath "build" `
  --icon $Icon `
  @modeArgs `
  --add-data "dist;dist" `
  --add-data "static;static" `
  --add-data "assets;assets" `
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

Write-Host "Done: $(Join-Path $Root "release\$Name\$Name.exe")"
