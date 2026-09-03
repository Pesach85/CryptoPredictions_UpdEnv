#Requires -Version 5.1
<#
.SYNOPSIS
  CryptoPredictions Windows uninstaller.
#>
$ErrorActionPreference = "Stop"
$AppName = "CryptoPredictions"
$ConfigDir = Join-Path $env:LOCALAPPDATA $AppName
$Marker = Join-Path $ConfigDir "uninstall.json"

Write-Host "==> CryptoPredictions Windows uninstall" -ForegroundColor Cyan

if (Test-Path $Marker) {
  $meta = Get-Content $Marker -Raw | ConvertFrom-Json
  if ($meta.desktop_shortcut -and (Test-Path $meta.desktop_shortcut)) {
    Remove-Item $meta.desktop_shortcut -Force
    Write-Host "Removed desktop shortcut"
  }
  if ($meta.start_menu -and (Test-Path $meta.start_menu)) {
    Remove-Item $meta.start_menu -Recurse -Force
    Write-Host "Removed Start Menu folder"
  }
} else {
  $Desktop = [Environment]::GetFolderPath("Desktop")
  $lnk = Join-Path $Desktop "$AppName.lnk"
  if (Test-Path $lnk) { Remove-Item $lnk -Force }
  $StartMenu = Join-Path ([Environment]::GetFolderPath("StartMenu")) "Programs\$AppName"
  if (Test-Path $StartMenu) { Remove-Item $StartMenu -Recurse -Force }
}

# Editable package uninstall (best-effort)
try {
  $py = (Get-Command python -ErrorAction SilentlyContinue).Source
  if ($py) { & $py -m pip uninstall -y cryptopredictions 2>$null }
} catch {}

if (Test-Path $ConfigDir) {
  Remove-Item $ConfigDir -Recurse -Force
  Write-Host "Removed $ConfigDir"
}

Write-Host "==> Uninstall complete. Repo source files were NOT deleted." -ForegroundColor Green
