# CryptoPredictions Android — on-device first

## Why not “FastAPI-only APK”? (quality-gate correction)

A thin Retrofit client around FastAPI **failed** the product requirement:
*majority of functions inside the APK with Android-native systems*.

| Constraint | Implication |
|------------|-------------|
| Desktop stack is Python (sklearn / Prophet / pandas) | Cannot ship unmodified inside ART without Chaquopy/BeeWare (heavy, fragile) |
| Volatility radar + path compare | **Pure math on OHLCV** → portable to Kotlin |
| RF recursive / Prophet long-horizon | Still Python-heavy → **optional remote**, not the default |

**Decision (2026-09-03):** APK is **local-first**. On-device Kotlin engines are the primary path. FastAPI is an optional bridge for heavy models only.

## On-device capabilities (no network)

| Feature | Implementation |
|---------|----------------|
| Volatility event radar | `engine/VolatilityEngine.kt` (port of `services/volatility_events.py`) |
| August path compare | `engine/PathCompareEngine.kt` (Naive / EWMA / LinReg 1-step) |
| Bundled OHLCV | `assets/ohlcv/*.csv` (last ~900 daily bars, 6 majors) |
| Notifications | `NotificationChannel` + `WorkManager` **on-device** probe |
| Share | `Intent.ACTION_SEND` |
| Secure prefs | EncryptedSharedPreferences (mode + optional API URL) |

## Optional remote

Settings → Compute mode **Remote API** for host-side RF/Prophet when the PC runs `cryptopredictions api`.

## Build APK

```powershell
# refresh bundled CSVs from repo data/
python scripts/sync_android_ohlcv.py
# SDK auto-detected from ANDROID_HOME or D:\Android\Sdk / %LOCALAPPDATA%\Android\Sdk
.\packaging\android\build_apk.ps1
```

Requires **JDK 17+** + Android SDK (`compileSdk 34`). Gradle wrapper is committed under `CryptoPredictionsApp/`; `local.properties` is generated and gitignored.

Debug APK: `CryptoPredictionsApp/app/build/outputs/apk/debug/app-debug.apk`
APK: `app/build/outputs/apk/debug/app-debug.apk`
