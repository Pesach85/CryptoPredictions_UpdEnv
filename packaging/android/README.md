# CryptoPredictions Android companion

Native **Kotlin + Jetpack Compose** client (Material 3) — not a WebView wrapper.

## Capabilities (Android-specific)

| Feature | Implementation |
|---------|----------------|
| Material 3 UI | Compose screens: Assets, Volatility radar, API status |
| Push-style alerts | `NotificationChannel` + local notification after forecast |
| Background check | `WorkManager` periodic volatility probe (when API reachable) |
| Share | `Intent.ACTION_SEND` of forecast JSON summary |
| Back / lifecycle | Compose Navigation + `Lifecycle` aware ViewModels |
| Secure prefs | EncryptedSharedPreferences for API base URL |
| Network | OkHttp + Retrofit against FastAPI (`/api/v1/...`) |

## Dev-linked mode

The APK does **not** embed the Python ML stack. In development:

1. Host machine runs live API: `cryptopredictions api --host 0.0.0.0 --port 8000`
2. Android emulator: base URL `http://10.0.2.2:8000`
3. Physical device: base URL `http://<LAN-IP>:8000` (same Wi-Fi)
4. USB: `adb reverse tcp:8000 tcp:8000` then `http://127.0.0.1:8000`

Code changes on the host repo are available immediately through the API (same `dev-linked` contract as desktop).

## Build APK

Requirements: JDK 17+, Android SDK 34, Gradle wrapper (included).

```bash
cd packaging/android/CryptoPredictionsApp
./gradlew assembleDebug          # Linux/macOS
gradlew.bat assembleDebug        # Windows
```

APK output:

`app/build/outputs/apk/debug/app-debug.apk`

Release (unsigned template):

```bash
./gradlew assembleRelease
```

## Install on device

```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```
