---
name: elite-quality-gate
description: >-
  Elite / high quality gate for CryptoPredictions delivery: native-first
  (not web-wrapper-only), validate every step with tools, update KB with
  decisions/problems/solutions, commit push, intelligent cleanup. Use when the
  user says quality gate, elite grade, high quality, packaging, Windows/Linux/
  Android install, on-device APK, or demands maximum precision validation.
---

# Elite quality gate

## Standard of proof

A change is not done until:

1. **Behaviour matches the ask** (e.g. Android majority on-device ≠ Retrofit-only client).
2. **Step validation** — tests or CLI smoke run; failures reported with output.
3. **KB updated** — decisions, solutions, problems, one Next Best Decision.
4. **Ship hygiene** — commit (when asked or when user said commit/push), push if requested, ignore build junk (`*.egg-info`, Android `build/`).
5. **Simulation-only** framing preserved in UI/API/docs.

## Platform gate (packaging)

| Surface | Pass criteria |
|---------|----------------|
| Windows/Linux desktop | Install + uninstall + desktop/menu icons; `dev-linked` live repo |
| Desktop UX | Native shell (Qt) primary; Streamlit optional secondary |
| Android | **On-device** Kotlin engines for radar/paths by default; FastAPI optional |
| Linux-native extras | XDG `.desktop`, icons, optional `systemd --user`, `notify-send` |

Fail gate if “native app” is only a WebView/API shell without the majority of user-facing analytics on-device (Android) or in-process (desktop).

## Validation commands (pick what applies)

```bash
# Unit
pytest -q tests/test_core.py tests/test_packaging.py -k "not projection_smoke"

# Domain
python scripts/volatility_forecast.py ETHUSD --threshold 10
python scripts/august_multi_model_paths.py ETHUSD --fast --no-persist

# Packaging Windows
powershell -File packaging/windows/install.ps1 -SkipPip

# Android assets
python scripts/sync_android_ohlcv.py
```

## Delivery checklist

- [ ] Requirement vs implementation gap closed (honest if residual)
- [ ] Tool-backed verification
- [ ] `Documents/KB.md` Current State / Decision note
- [ ] README / AGENT_GUIDE if entry points changed
- [ ] `.gitignore` covers generated install/build artifacts
- [ ] Commit message focuses on why; push only if requested or prior pattern in session

## Remediations already encoded

- Android FastAPI-only companion → fixed with `VolatilityEngine` / `PathCompareEngine` + bundled OHLCV (see KB 2026-09-03 correction).
- PowerShell BOM / em-dash installer bugs → `write_install_config.py` + ASCII installers.
