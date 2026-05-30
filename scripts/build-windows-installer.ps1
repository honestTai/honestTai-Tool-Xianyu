param(
  [string]$Python = "python",
  [string]$Npm = "npm",
  [string]$InnoSetupCompiler = "",
  [string]$LicenseServerUrl = "https://www.javatzt.cn/license",
  [string]$LicenseClientSecret = "change-this-client-secret",
  [string]$LicenseEnforcementEnabled = "true",
  [switch]$Console,
  [switch]$SkipExeBuild
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Name = "honestTai-Tool-Xianyu"
$BuildScript = Join-Path $PSScriptRoot "build-windows-exe.ps1"
$InstallerScript = Join-Path $PSScriptRoot "installer\honesttai-tool-xianyu.iss"

$LicenseEnforcementEnabled = $LicenseEnforcementEnabled.Trim().ToLowerInvariant()

function Resolve-InnoSetupCompiler {
  param([string]$ConfiguredPath)

  if (-not [string]::IsNullOrWhiteSpace($ConfiguredPath)) {
    if (-not (Test-Path $ConfiguredPath)) {
      throw "Inno Setup compiler not found: $ConfiguredPath"
    }
    return $ConfiguredPath
  }

  $command = Get-Command "iscc.exe" -ErrorAction SilentlyContinue
  if ($command) {
    return $command.Source
  }

  $candidates = @(
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
  )

  foreach ($candidate in $candidates) {
    if (Test-Path $candidate) {
      return $candidate
    }
  }

  throw "Inno Setup 6 was not found. Install it or pass -InnoSetupCompiler `"C:\Path\To\ISCC.exe`"."
}

if ([string]::IsNullOrWhiteSpace($LicenseServerUrl)) {
  $LicenseServerUrl = "https://www.javatzt.cn/license"
}

if (-not $SkipExeBuild) {
  $exeArgs = @(
    "-Python", $Python,
    "-Npm", $Npm,
    "-LicenseServerUrl", $LicenseServerUrl,
    "-LicenseEnforcementEnabled", $LicenseEnforcementEnabled
  )
  if (-not [string]::IsNullOrWhiteSpace($LicenseClientSecret)) {
    $exeArgs += @("-LicenseClientSecret", $LicenseClientSecret)
  }
  if ($Console) {
    $exeArgs += "-Console"
  }

  & $BuildScript @exeArgs
}

$iscc = Resolve-InnoSetupCompiler $InnoSetupCompiler
$outputDir = Join-Path $Root "release\installer"
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

& $iscc `
  "/DMyAppRoot=$Root" `
  "/DMyAppName=$Name" `
  "/DMyAppVersion=2.0.0" `
  $InstallerScript

Write-Host "Done: $(Join-Path $outputDir "$Name-Setup.exe")"
