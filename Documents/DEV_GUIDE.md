# Developer Guide

## Goal
Maintain and extend CryptoPredictions for predictive experimentation quality.

## Setup (Research Baseline)
1. Create and activate a Python virtual environment.
2. Install required packages for baseline models.
3. Use `train.py` with Hydra defaults or CLI overrides.

## Suggested Baseline Commands
- Train with defaults:
  - `python train.py`
- Train with explicit path/model:
  - `python train.py model=random_forest load_path=./data/ETHUSD-1h-data.csv`
- Run backtest on latest generated CSV:
  - `python backtester.py`
- Run deterministic meta-historical validation:
  - `python meta_historical_test.py`

## Meta CLI UX (Recommended)
- Single-asset default (fast start):
  - `python meta_historical_test.py`
- Multi-asset run with deterministic gate (recommended daily check):
  - `python meta_historical_test.py --assets ETHUSD,XBTUSD,SOLUSD --min-samples 100 --max-mape 4.0`
- Tune model/detail level:
  - `python meta_historical_test.py --assets ETHUSD,XBTUSD,SOLUSD --lags 30 --n-estimators 500 --accuracy-window 14 --wf-horizon 14 --wf-step 7`

## Engineering Standards
- Avoid hardcoded absolute paths.
- Avoid committing credentials/secrets.
- Keep optional model dependencies isolated from baseline flow.
- Prefer deterministic settings for comparisons (`random_state`).

## Reporting Standards
For every experiment include:
- Configuration used (model, split, indicators, window size)
- Metrics (regression + directional)
- Notable failures/edge cases
- Next experiment hypothesis
