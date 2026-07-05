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
- Streamlit UI: `streamlit run app_projection.py`
- CLI: `python project_forward.py --asset ETHUSD --horizon 30`
- FastAPI: `uvicorn api.main:app --reload --port 8000`
- Long horizon CLI: Prophet 90–365d via `LongHorizonService`
- Scenario backtest: `python scenario_backtest.py --asset ETHUSD --horizon 30`
- Data refresh: `python scripts/refresh_market_data.py --asset ETHUSD`
- Service API: `services/projection.py`, `services/long_horizon.py`, `services/scenario_backtest.py`, `services/data_refresh.py`
- Per-asset profiles: `config/asset_profiles.json`
- Skills: `.cursor/skills/crypto-predictions-projection/`, `.cursor/skills/stealth-browser-market-data/`

## Required Agent Behavior
1. Validate assumptions before editing.
2. Keep experiments reproducible.
3. Prefer minimal, testable code changes.
4. Update `Documents/KB.md` after non-trivial modifications.
5. Always include a `Next Best Decision` section with exactly one immediate, testable action.

## Validation Minimum
- Run static error checks or one executable baseline training run.
- Report metric outputs and limitations.

## Non-Investment Constraint
All outputs must be framed as experimental predictive analysis and software validation.
