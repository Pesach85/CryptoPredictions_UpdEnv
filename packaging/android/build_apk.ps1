#Requires -Version 5.1
# Bootstrap Gradle wrapper if needed, then assembleDebug APK (Windows).
$ErrorActionPreference = "Stop"
$Root = Join-Path $PSScriptRoot "CryptoPredictionsApp"
Set-Location $Root

if (-not (Test-Path ".\gradlew.bat")) {
  Write-Host "==> Generating Gradle wrapper (requires gradle on PATH)"
  $gradle = Get-Command gradle -ErrorAction SilentlyContinue
  if (-not $gradle) {
    throw "Install Gradle 8.7+ or Android Studio, then re-run packaging/android/build_apk.ps1"
  }
  & gradle wrapper --gradle-version 8.7
}

.\gradlew.bat assembleDebug --stacktrace
Write-Host "APK: $Root\app\build\outputs\apk\debug\app-debug.apk"
