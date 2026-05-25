param(
  [string]$Python = "python",
  [string]$Npm = "npm",
  [switch]$Console
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Name = "honestTai-Tool-Xianyu"

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
  @modeArgs `
  --add-data "dist;dist" `
  --add-data "static;static" `
  --add-data ".env.example;." `
  --collect-data goofish_cli `
  --collect-submodules goofish_cli `
  --hidden-import win32timezone `
  desktop_launcher.py

Write-Host "Done: $(Join-Path $Root "release\$Name\$Name.exe")"
