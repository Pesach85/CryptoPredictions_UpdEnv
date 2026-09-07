#Requires -Version 5.1
# Bootstrap Gradle wrapper if needed, then assembleDebug APK (Windows).
$ErrorActionPreference = "Stop"

# Prefer explicit ANDROID_HOME; fall back to common local SDK paths.
if (-not $env:ANDROID_HOME) {
  foreach ($candidate in @(
      "D:\Android\Sdk",
      "$env:LOCALAPPDATA\Android\Sdk",
      "$env:USERPROFILE\AppData\Local\Android\Sdk"
    )) {
    if (Test-Path $candidate) {
      $env:ANDROID_HOME = $candidate
      break
    }
  }
}
if ($env:ANDROID_HOME) {
  $env:ANDROID_SDK_ROOT = $env:ANDROID_HOME
  Write-Host "==> ANDROID_HOME=$env:ANDROID_HOME"
} else {
  Write-Warning "ANDROID_HOME not set and no SDK found under D:\Android\Sdk or %LOCALAPPDATA%\Android\Sdk"
}

$Root = Join-Path $PSScriptRoot "CryptoPredictionsApp"
Set-Location $Root

$localProps = Join-Path $Root "local.properties"
if (-not (Test-Path $localProps) -and $env:ANDROID_HOME) {
  $sdkEscaped = ($env:ANDROID_HOME -replace '\\', '\\')
  Set-Content -Path $localProps -Value "sdk.dir=$sdkEscaped" -Encoding ASCII
  Write-Host "==> Wrote local.properties"
}

if (-not (Test-Path ".\gradlew.bat")) {
  Write-Host "==> Generating Gradle wrapper (requires gradle on PATH)"
  $gradle = Get-Command gradle -ErrorAction SilentlyContinue
  if (-not $gradle) {
    throw "Install Gradle 8.7+ or Android Studio, then re-run packaging/android/build_apk.ps1"
  }
  & gradle wrapper --gradle-version 8.7
}

.\gradlew.bat assembleDebug --stacktrace
$apk = Join-Path $Root "app\build\outputs\apk\debug\app-debug.apk"
Write-Host "APK: $apk"
if (-not (Test-Path $apk)) { throw "APK not produced" }
