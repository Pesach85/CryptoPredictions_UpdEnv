#Requires -Version 5.1
<#
.SYNOPSIS
  CryptoPredictions Windows installer (dev-linked production mode).
#>
param(
  [string]$RepoRoot = "",
  [string]$Python = "",
  [switch]$SkipPip
)

$ErrorActionPreference = "Stop"
$AppName = "CryptoPredictions"

if (-not $RepoRoot) {
  $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$ConfigDir = Join-Path $env:LOCALAPPDATA $AppName
$IconSource = Join-Path $RepoRoot "packaging\icons\cryptopredictions.ico"
if (-not (Test-Path $IconSource)) {
  $IconSource = Join-Path $RepoRoot "packaging\icons\cryptopredictions.png"
}

Write-Host "==> CryptoPredictions Windows install (dev-linked)" -ForegroundColor Cyan
Write-Host "    RepoRoot = $RepoRoot"

if (-not (Test-Path (Join-Path $RepoRoot "services"))) {
  throw "RepoRoot does not look like CryptoPredictions: $RepoRoot"
}

if (-not $Python) {
  $venvPy = Join-Path $RepoRoot ".venv\Scripts\python.exe"
  if (Test-Path $venvPy) { $Python = $venvPy }
  else { $Python = (Get-Command python -ErrorAction Stop).Source }
}
Write-Host "    Python   = $Python"

& $Python (Join-Path $RepoRoot "scripts\generate_icons.py")
& $Python (Join-Path $RepoRoot "scripts\generate_ico.py")

New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null
& $Python (Join-Path $RepoRoot "scripts\write_install_config.py") `
  --config-dir $ConfigDir `
  --repo-root $RepoRoot `
  --python $Python

if (-not $SkipPip) {
  Write-Host "==> pip install -e .[desktop] (editable / live)" -ForegroundColor Cyan
  $spec = "$RepoRoot[desktop]"
  & $Python -m pip install -e $spec --upgrade
}

$LauncherDir = Join-Path $ConfigDir "bin"
New-Item -ItemType Directory -Force -Path $LauncherDir | Out-Null
$Launcher = Join-Path $LauncherDir "CryptoPredictions.cmd"
$launcherLines = @(
  "@echo off",
  "set CRYPTOPREDICTIONS_ROOT=$RepoRoot",
  "set PYTHONPATH=$RepoRoot",
  "`"$Python`" -m cryptopredictions desktop"
)
$launcherLines | Set-Content -Path $Launcher -Encoding ASCII

function New-CpShortcut([string]$Path, [string]$Target, [string]$Arguments, [string]$Icon) {
  $ws = New-Object -ComObject WScript.Shell
  $s = $ws.CreateShortcut($Path)
  $s.TargetPath = $Target
  $s.Arguments = $Arguments
  $s.WorkingDirectory = $RepoRoot
  if ($Icon -and (Test-Path $Icon)) { $s.IconLocation = "$Icon,0" }
  $s.Save()
}

$Desktop = [Environment]::GetFolderPath("Desktop")
$StartMenu = Join-Path ([Environment]::GetFolderPath("StartMenu")) "Programs\$AppName"
New-Item -ItemType Directory -Force -Path $StartMenu | Out-Null

$launcherArg = "/c `"$Launcher`""
New-CpShortcut -Path (Join-Path $Desktop "$AppName.lnk") -Target $env:ComSpec -Arguments $launcherArg -Icon $IconSource
New-CpShortcut -Path (Join-Path $StartMenu "$AppName.lnk") -Target $env:ComSpec -Arguments $launcherArg -Icon $IconSource

$uninstallPs1 = Join-Path $RepoRoot "packaging\windows\uninstall.ps1"
$unArg = "-NoProfile -ExecutionPolicy Bypass -File `"$uninstallPs1`""
New-CpShortcut -Path (Join-Path $StartMenu "$AppName Uninstall.lnk") -Target "powershell.exe" -Arguments $unArg -Icon $IconSource

$uninstall = [ordered]@{
  install_root = $RepoRoot
  config_dir = $ConfigDir
  launcher = $Launcher
  desktop_shortcut = (Join-Path $Desktop "$AppName.lnk")
  start_menu = $StartMenu
  version = "1.1.0"
  installed_at = (Get-Date).ToUniversalTime().ToString("o")
}
$uninstall | ConvertTo-Json -Depth 5 | Set-Content -Path (Join-Path $ConfigDir "uninstall.json") -Encoding UTF8

Write-Host "==> Install complete." -ForegroundColor Green
Write-Host "    Desktop shortcut + Start Menu entry created."
Write-Host "    Config: $ConfigDir\config.json"
Write-Host "    Launch: $Launcher"
Write-Host "    Uninstall: packaging\windows\uninstall.ps1"
