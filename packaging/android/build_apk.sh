#!/usr/bin/env bash
# Bootstrap Gradle wrapper if missing, then assembleDebug APK.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/CryptoPredictionsApp" && pwd)"
cd "$ROOT"

if [[ ! -f gradlew ]]; then
  echo "==> Generating Gradle wrapper (requires gradle on PATH)"
  if ! command -v gradle >/dev/null 2>&1; then
    echo "ERROR: install Gradle 8.7+ or Android Studio, then re-run." >&2
    exit 1
  fi
  gradle wrapper --gradle-version 8.7
fi

chmod +x gradlew
./gradlew assembleDebug --stacktrace
echo "APK: $ROOT/app/build/outputs/apk/debug/app-debug.apk"
