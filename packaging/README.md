# CryptoPredictions — native packaging

## Decision (2026-09-03)

Ship a **dev-linked production** model:

| Layer | Technology | Why |
|-------|------------|-----|
| Desktop Win/Linux | **PySide6** native shell + local FastAPI | Not a WebView-only app; tray, menus, in-process Volatility radar |
| Install / uninstall | PowerShell (Win) + XDG shell (Linux) | Desktop icon, Start Menu / `.desktop`, clean uninstall without deleting git repo |
| Live code | `mode=dev-linked` + `pip install -e .` | Shortcuts set `CRYPTOPREDICTIONS_ROOT` / `PYTHONPATH` → edits apply immediately |
| Android | **Kotlin Compose** APK | Native notifications, WorkManager, Share, EncryptedSharedPreferences — talks to live API |

Frozen PyInstaller bundles are deferred until a release freeze; during active research, frozen copies would drift from the repo.

## Quick start

### Windows
```powershell
.\packaging\windows\install.ps1
# Desktop + Start Menu → CryptoPredictions
.\packaging\windows\uninstall.ps1
```

### Linux
```bash
bash packaging/linux/install.sh
# Optional API daemon:
systemctl --user enable --now cryptopredictions-api
bash packaging/linux/uninstall.sh
```

### Android
See `packaging/android/README.md`. Build APK with Android SDK + `./gradlew assembleDebug`.

## Icons
```bash
python scripts/generate_icons.py
```
