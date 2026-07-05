---
name: crypto-predictions-projection
description: >-
  Runs forward crypto price projections and what-if scenarios in CryptoPredictions.
  Use when building projection features, scenario analysis, Streamlit UI, asset profiles,
  or when the user asks about future price paths, fan charts, or hypothetical shocks.
---

# CryptoPredictions Projection

## Scope

Experimental predictive research only — never frame outputs as investment advice.

## Architecture

| Component | Path |
|-----------|------|
| Projection engine | `services/projection.py` |
| Per-asset profiles | `config/asset_profiles.json` |
| Streamlit UI | `app_projection.py` |
| Headless CLI | `project_forward.py` |
| Historical validation | `meta_historical_test.py` |

## Per-asset heterogeneous strategy (from KB)

| Assets | lags | features |
|--------|------|----------|
| XBTUSD, LTCUSD | 30 | close |
| ETHUSD, ADAUSD, BCHUSD | 14 | close |
| SOLUSD | 14 | focused |

Profiles are codified in `config/asset_profiles.json`. Override via CLI/UI only when experimenting.

## Run projections

**Streamlit UI:**
```bash
streamlit run app_projection.py
```

**CLI:**
```bash
python project_forward.py --asset ETHUSD --horizon 30
python project_forward.py --asset SOLUSD --horizon 60 --scenarios "Bear,-20;Bull,15"
```

**Python API:**
```python
from services.projection import ProjectionService, ScenarioSpec

service = ProjectionService()
result = service.project_forward("ETHUSD", horizon_days=30)
scenarios = [ScenarioSpec(name="Crash", price_shock_pct=-25, shock_day=5)]
result = service.compare_scenarios("ETHUSD", 30, scenarios)
```

## What-if scenario types

| Field | Effect |
|-------|--------|
| `price_shock_pct` | Multiplicative shock on forecast day N |
| `volatility_multiplier` | Scales predicted daily deviation |
| `volume_multiplier` | Scales synthetic volume (enhanced mode) |
| `shock_day` | Day index (1-based) when price shock applies |

## Artifacts

Saved under `outputs/projections/<ASSET>_<timestamp>/`:
- `base_projection.csv`
- `scenario_*.csv`
- `projection_report.json`
- `<ASSET>_projection_model.joblib`

## Guardrails

1. Label all outputs "simulation only".
2. Recursive 1-step RF forecasts compound error beyond ~30 days — note limitation.
3. Update `Documents/KB.md` after non-trivial projection changes.
4. Prefer asset profiles over manual overrides unless A/B testing.
5. Include a `Next Best Decision` with one testable action.

## Extension roadmap

- ~~Wire Prophet/Orbit for native uncertainty bands on long horizons~~ → `services/long_horizon.py`
- ~~Scenario backtesting: feed projected paths into `backtest/strategies.py`~~ → `services/scenario_backtest.py`
- ~~API layer (FastAPI) reusing `ProjectionService`~~ → `api/main.py`
- ~~Live data refresh via stealth-browser MCP for protected exchange pages~~ → `services/data_refresh.py` + skill
- Automated profile calibration: `scripts/profile_grid_eval.py` (multi-objective, walk-forward) → `asset_profiles.json`
- Orbit long-horizon as default for assets with orbit-ml installed
- Webhook/scheduler for periodic `--all` data refresh

## Profile calibration note

Do not bulk-update `asset_profiles.json` from a MAPE-only grid. Use `scripts/profile_grid_eval.py` as input to a multi-objective review (MAPE + directional + walk-forward). See KB section "2026-07-05 Deep Acquisition/Train Evaluation".
