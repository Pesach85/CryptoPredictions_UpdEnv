# Agent Guide

## Purpose
Use this repository to evaluate predictive potential of models on crypto datasets.
Do not provide investment advice.

## Recommended Agent Entry
- Workspace instructions: `.github/copilot-instructions.md`
- Custom agent: `.github/agents/quant-research-gate.agent.md`
- Prompt shortcut: `.github/prompts/predictive-research-gate.prompt.md`
- Projection scenarios: `.cursor/agents/projection-scenario-analyst.agent.md`
- Market data collection: `.cursor/agents/market-data-researcher.agent.md`

## Projection & What-If Interface
- Native desktop: `cryptopredictions desktop` (after `packaging/*/install.*`)
- Streamlit UI: `streamlit run app_projection.py` (includes **Model compare** + **Volatility radar**)
- CLI: `python project_forward.py --asset ETHUSD --horizon 30`
- Multi-model paths: `python scripts/august_multi_model_paths.py ETHUSD --fast`
- Volatility: `python scripts/volatility_forecast.py ETHUSD`
- FastAPI: `uvicorn api.main:app --reload --port 8000` · `POST /api/v1/paths/compare` · `/volatility/forecast`
- Android: `packaging/android/` companion APK (points at live API)
- Packaging docs: `packaging/README.md`
- Per-asset profiles: `config/asset_profiles.json`
- Skills: `.cursor/skills/crypto-predictions-projection/`, `.cursor/skills/stealth-browser-market-data/`

## Required Agent Behavior
1. Validate assumptions before editing.
2. Keep experiments reproducible.
3. Prefer minimal, testable code changes.
4. Update `Documents/KB.md` after non-trivial modifications.
5. Always include a `Next Best Decision` section with exactly one immediate, testable action.
6. Respect the 2026-08-29 Decision Gate: do **not** open new model-family accuracy projects without new features; prefer data refresh + retrain.

## Validation Minimum
- Run static error checks or one executable baseline training run.
- Report metric outputs and limitations.
- CI smoke (`.github/workflows/ci-smoke.yml`): `pytest tests/test_core.py`, `project_forward.py` smoke, `refresh_market_data.py --status`. Needs `PYTHONPATH=.`; refresh must not pull heavy meta deps (CoinGecko id resolve is in `core/market_ids.py`).

## Non-Investment Constraint
All outputs must be framed as experimental predictive analysis and software validation.
