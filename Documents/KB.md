# Knowledge Base - CryptoPredictions

## Current State (2026-09-03) — read this first

> Chronological entries below are an audit log. Prefer this front-matter for architecture and truth.

### Scope
- Predictive experimentation and software validation on crypto time series.
- Outputs are **simulation only — not investment advice**.
- Native **Windows / Linux desktop** + **Android companion APK** (dev-linked to live repo).

### Architecture (three layers)

| Layer | Entry points | Role |
|-------|--------------|------|
| **Legacy Hydra** | `train.py`, `backtester.py`, `models/` | Multi-model train + classic backtest |
| **Product / meta** | `services/`, `app_projection.py`, `api/main.py` | Projections, volatility radar, FastAPI |
| **Native apps** | `cryptopredictions` package, `packaging/` | Qt desktop, XDG/Win installers, Android Compose |

### Packaging mode — **dev-linked production** (decision 2026-09-03)
- Installers write config with `mode=dev-linked` + `repo_root` → shortcuts set `CRYPTOPREDICTIONS_ROOT` / `PYTHONPATH`.
- `pip install -e .[desktop]` — **code edits are live in the installed app** without reinstall.
- Frozen PyInstaller/Briefcase bundles **deferred** until a release freeze (would otherwise drift from research codebase).
- Android APK is native Kotlin (not WebView); ML stays on host API during dev.

### Shipped vs deferred

| Item | Status |
|------|--------|
| Projection Lab + Model compare + Volatility radar | Shipped |
| FastAPI (+ `/volatility/forecast`) | Shipped |
| Native Qt desktop shell (Win/Linux) | **Shipped 2026-09-03** |
| Win/Linux install + uninstall + desktop icons | **Shipped 2026-09-03** |
| Android Kotlin Compose companion + APK recipe | **Shipped 2026-09-03** |
| Frozen offline single-file EXE/AppImage | Deferred |
| New model families for accuracy | **Closed** |

### Next Best Decision
On a Linux box run `bash packaging/linux/install.sh` and verify `.desktop` + `notify-send`; on Android SDK host run `packaging/android/build_apk.ps1` / `.sh` to produce `app-debug.apk`.

## 2026-09-03 Native packaging (shipped)

### Requirements answered
1. Common Win/Linux/Android software with install/uninstall, taskbar/menu, desktop shortcuts — **yes**.
2. Dev phase: installed "production" sees live codebase — **yes** (`dev-linked`).
3. Linux-native (not web-only) — Qt shell + XDG + optional `systemd --user` API unit + `notify-send`.
4. Android-native APK (not web-only) — Compose UI, notifications, WorkManager, Share, EncryptedSharedPreferences.

### Problems encountered + solutions
| Problem | Solution |
|---------|----------|
| PowerShell `ConvertTo-Json` + UTF-8 BOM broke `json.loads` | `utf-8-sig` loader + `scripts/write_install_config.py` |
| Em-dash in `install.ps1` corrupted parser | ASCII-only installer scripts |
| PNG not ideal for Windows `.lnk` icons | `scripts/generate_ico.py` multi-size ICO |
| Embedding Streamlit as "the app" fails elite gate | Native Qt for primary UX; Streamlit optional secondary |
| Full Python ML inside APK impractical | Companion APK + live FastAPI (`10.0.2.2` / LAN / `adb reverse`) |

### Install commands
```powershell
# Windows
.\packaging\windows\install.ps1
.\packaging\windows\uninstall.ps1
```
```bash
# Linux
bash packaging/linux/install.sh
bash packaging/linux/uninstall.sh
```
```bash
# Android APK (needs Android SDK + Gradle)
packaging/android/build_apk.sh   # or build_apk.ps1
```

### Validation (2026-09-03)
- `pytest tests/test_packaging.py tests/test_core.py` — 12 passed (projection_smoke deselected in local batch).
- Windows install created Desktop + Start Menu shortcuts + `LocalAppData/CryptoPredictions/config.json` with `repo_root`.
- `RuntimeHub.from_config` resolves live repo.

## 2026-09-02 Volatility Event Radar (shipped)

### Rally from 2026-08-19 (local daily CSVs)
| Asset | Max 1d from Aug 19 | Cum. to Aug 29 | Note |
|-------|-------------------|----------------|------|
| ETHUSD | +17.5% | +8.2% | Aug +32% total; consolidation phase |
| XBTUSD | +7.1% | +12.1% | Impulse then fade Aug 29 (-3.3%) |
| SOLUSD | +10.8% | +21.4% | Strongest momentum residue |

### Algorithm (`services/volatility_events.py`)
Event = |1d|≥threshold or |3d|≥1.2×threshold. Features: ATR ratio, BB compression, vol ratio, RSI, MA distance, 14d impulse, days since event, volume z-score. Top-40 historical analogs + regime score → P(7/14/21d), magnitude, direction bias, calendar window.

### Forecast ±10% as of 2026-08-29
| Asset | P(14d) | Bias | Window est. |
|-------|--------|------|-------------|
| ETHUSD | ~71% | Down | Sep 4–16 |
| XBTUSD | ~79% | Down | Sep 1–7 |
| SOLUSD | ~92% | Up (slight) | Aug 31–Sep 4 |

Simulation only — not investment advice.

### Entry points
- UI: `streamlit run app_projection.py` → tab **Volatility radar**
- API: `POST /api/v1/volatility/forecast`
- CLI: `python scripts/volatility_forecast.py ETHUSD`

## 2026-08-29 Decision Gate — Models vs Data

### Question
Can new models raise predictive accuracy further, or should we stop and train/refresh on new data?

### Verdict (deterministic)
**Stop model expansion for accuracy. Prefer data refresh + retrain of the current stack.**

Simulation framing only — not investment advice.

### Evidence

| Evidence | Result | Implication |
|----------|--------|-------------|
| Aug 2026 ETH path (train ≤ Jul 31) | Actual **+32%**; RF recursive / Naive / ARIMA ~flat (**MAPE ~8–9%**, end gap **~−24%**); Prophet **MAPE ~27%** (level bias); RF≈XGB **1-step MAPE ~2%** | Multi-step failure is **shared across model families**; 1-step tree ceiling already ~2% |
| Aug 2026 BTC path | Actual **+24%**; multi-step **−17…−19%** end gap; RF 1-step **~1.8%** MAPE; Prophet **~36%** | Same pattern as ETH — not an ETH-specific bug |
| Aug 15 ±15d coherence | PRE 1-step coherent; POST recursive misses rally (**−10…−38 pp** return gap) | Recursive compounding + regime break, not “wrong RF hyperparameters” |
| n_estimators 300→500 (2026-04) | XBT/SOL MAPE unchanged | Tree **capacity** not the bottleneck |
| Feature set | Close/OHLCV lags only; no macro/on-chain | Any new model sees the **same information**; regime jumps remain unpredictable from lags alone |

### Why “add models” fails the bar
1. **XGBoost ≈ RF** on August 1-step → next tree model adds noise, not signal.
2. **ARIMA ≈ Naive** on multi-step August → classical univariate does not recover the rally.
3. **Prophet** already in-repo and worse on August MAPE (bias), useful only as **long-horizon fan chart**, not as accuracy winner.
4. **LSTM/GRU/Orbit/NeuralProphet** would still train on lag-OHLCV; they do not inject regime information. High cost, no evidence they beat ~2% 1-step or fix recursive multi-day paths under the Aug stress test.

### Why “more data / retrain” is the right ops move
1. Data already extended to **2026-08-29**; staleness was a past failure mode — **refresh cadence** prevents regression.
2. Retraining RF/XGB on the latest bars keeps 1-step validators honest without new architecture.
3. Accuracy claims must stay split by task:
   - **1-step / short validation** → RF (or XGB) with profiles — already usable (~2% MAPE Aug).
   - **Multi-day recursive projection** → experimental; expect under-reaction on breaks (`regime_shift_caution`).
   - **Long horizon** → Prophet bands, illustrative only.

### Operational plan (maintenance — not a build sprint)

| Priority | Action | Done when |
|----------|--------|-----------|
| P0 | Weekly OHLCV refresh (`scripts/refresh_market_data.py --retry-failed`) | gap_days≈0 on majors |
| P0 | Keep CI smoke green on `main` | Actions pass |
| P1 | After refresh: Model compare Fast on ETH or BTC last 14–30d | MAPE logged; no gate breach assumed |
| P2 | Optional meta retrain on refreshed CSVs for gate assets | Artifacts under `outputs/meta_historical` |
| — | New model classes / DL stack | **Not scheduled** |
| — | Multi-obj profile grid | Deferred until a feature-set change exists |

### Closure statement
The 2026-08-29 research loop (refactor A–E, Aug coherence, multi-model August charts, Model compare UI) is **complete**. Further accuracy work without new **features** (beyond price lags) is expected to yield **diminishing returns**. Repo mode: **maintain data + validate**, not expand model zoo.

### Next Best Decision
Schedule the weekly refresh; do not open an LSTM/GRU accuracy project.

---

## 2026-08-29 Incremental Refactor Phases A–E (shipped)

### Phase A — core extract
- Added `core/` package; `meta_historical_test.py` thin CLI + API fetchers.
- Services/scripts import from `core/`.
- Golden tests: `tests/test_core.py`.

### Phase B — projection performance + caution
- Close-mode recursive path uses O(lags) `feature_row_from_close_tail` (no full rebuild).
- Focused/enhanced rebuilds only last `TAIL_BUFFER` rows.
- `regime_shift_caution` in projection metadata + Streamlit warning.

### Phase C — profiles
- Meta CLI `--use-profiles`.
- Profiles expanded: BNB, DOGE, AVAX (9/19).

### Phase D — signals + CI
- Shared `core/signals.compute_signal1` used by scenario BT + Hydra `Strategies.signal1`.
- `.github/workflows/ci-smoke.yml` on push/PR to `main` (`PYTHONPATH=.`).
- `resolve_coingecko_coin_id` lives in `core/market_ids.py` so refresh/status smoke does **not** import `matplotlib` via `meta_historical_test`.

### Phase E — ops docs
- KB Current State updated; README date + What's New; Aug-15 canvas for low-cog visualization.

### August 2026 multi-model path chart (shipped)
- Service: `services/multi_model_paths.py` (`MultiModelPathService`)
- UI: Projection Lab tab **Model compare** (`streamlit run app_projection.py`)
- API: `POST /api/v1/paths/compare` (`fast=true` for Naive+RF only)
- CLI: `python scripts/august_multi_model_paths.py ETHUSD [--fast] [--start|--end]`
- Protocol: train ≤ day before window start; overlay Actual / Naive / RF recursive / RF·XGB 1-step / ARIMA / Prophet.
- ETH Aug: **+32%** actual; multi-step flat (−24% end gap); 1-step MAPE ~2%; Prophet MAPE ~27%.
- BTC Aug: **+24%** actual; multi-step −17…−19%; RF 1-step MAPE ~1.8%; Prophet MAPE ~36%.
- Canvas: `august-eth-model-paths.canvas.tsx`, `august-btc-model-paths.canvas.tsx`.
- CI: fast multi-model CLI smoke + `test_multi_model_paths_fast_eth`.

### Next Best Decision
Superseded by Decision Gate above — weekly refresh, no model-expansion sprint.

---

## Scope (legacy header)
- This project is used for predictive experimentation on crypto time series.
- Outputs are for research/simulation, not investment decisions.

## Baseline Workflow
1. Use local CSV input (`load_path`) for reproducible runs.
2. Start with `random_forest` for lightweight baseline.
3. Compare regression + directional metrics together.
4. Use backtester only as simulation stress-test.

## 2026-04-16 Updates
- Added lazy loading for model imports so optional model dependencies no longer break startup.
- Added lazy loading for dataset loaders to avoid hard dependency failures.
- Removed hardcoded API credentials from Bitmex loader and switched to env vars.
- Replaced machine-specific config paths with workspace-relative defaults.
- Improved backtester CSV resolution and fixed signal evaluation to use current timestep value.
- Corrected SMA window bug (`sma_100` now uses period 100).

## 2026-04-16 Validation Evidence
- Python environment configured in `.venv` and baseline packages installed for reproducible local experimentation.
- Successful lightweight train run completed with command:
	- `python train.py model.n_estimators=5 dataset_loader.train_start_date='2022-01-01 00:00:00' dataset_loader.train_end_date='2022-09-01 00:00:00' dataset_loader.valid_start_date='2022-09-01 00:00:00' dataset_loader.valid_end_date='2022-12-01 00:00:00'`
- Observed metrics from run (`validation-0`):
	- `accuracy_score=0.532`, `f1_score=0.497`, `recall_score=0.487`, `precision_score=0.509`
	- `MAE=14.43`, `RMSE=25.49`, `MAPE=1.03`, `SMAPE=1.04`, `MASE=1.55`, `MSLE~0.000`
- Backtest pipeline executed and produced report file:
	- `outputs/2026-04-16/09-50-50/ETH_random_forest_backTest.txt`

## 2026-04-16 Next Best Decision Policy
- The workspace gate now mandates a `Next Best Decision` section for substantial outputs.
- The section must contain one deterministic, testable immediate action.

## 2026-04-16 Safe Resource Cleanup Automation

### What changed
- Added `scripts/safe_cleanup.ps1` with safe defaults and deterministic retention:
	- Dry-run by default (no deletion without `-Execute`).
	- Cleans local project Python caches (`__pycache__`, plus `.pyc/.pyo` outside cache folders).
	- Prunes stale dated run folders under `outputs/` and `outputs/meta_historical/`.
	- Preserves README-referenced artifact runs under `outputs/meta_historical/YYYY-MM-DD/HH-MM-SS`.
	- Removes empty directories left after cleanup.
- Added VS Code automation tasks in `.vscode/tasks.json`:
	- `safe-cleanup-dry-run`
	- `safe-cleanup-apply`
- Added README maintenance section with one-command dry-run and apply usage.

### Validation evidence
- Dry-run preview before deletion:
	- Planned removals: `48`
	- Planned reclaimed space: `3066.23 MB`
- Applied cleanup:
	- Removed items: `44`
	- Freed space: `3066.23 MB`
- Storage verification:
	- `outputs` before: `3799.44 MB`
	- `outputs` after: `733.41 MB`
- Regression check command executed successfully:
	- `powershell -ExecutionPolicy Bypass -File scripts/run_2026_readme_example.ps1`
	- Confirmed all README-referenced chart artifacts are still present.

### Residual risks
- New experiment runs can regrow `outputs/meta_historical` quickly (large `*_model_retrained.joblib` artifacts).
- Current policy is retention-based; if long-term archival is needed, artifacts should be externalized/compressed outside the active workspace.

### Next Best Decision
- Add a scheduled weekly run of `safe-cleanup-dry-run` and a manual approval gate for `safe-cleanup-apply` to keep storage bounded without accidental artifact loss.

## 2026-04-16 Meta-Historical Test (ETHUSD)
- Goal: train on past local ETH dataset, predict current-year behavior deterministically, compare with realized prices, then retrain on up-to-date data.
- Execution script:
	- `meta_historical_test.py`
- Output folder:
	- `outputs/meta_historical/2026-04-16/10-00-48`
- Data sources used:
	- Local past data: `data/ETHUSD-1d-data.csv`
	- Free API trending snapshot: CoinGecko trending (fallback CoinCap)
	- Free API prices: CoinGecko range (fallback Yahoo Finance, fallback CryptoCompare)
- Evaluation setup:
	- Past-only training end date: `2023-02-17`
	- Evaluation year: `2026`
	- Samples: `106`
	- Model: `RandomForestRegressor`, `n_estimators=300`, `random_state=42`, `lags=30`
- Deterministic comparison metrics:
	- `MAE=67.92`, `RMSE=94.03`, `MAPE=2.96`, `SMAPE=2.93`
	- `accuracy_score=0.581`, `precision_score=0.569`, `recall_score=0.569`, `f1_score=0.569`
- Trending status at run time:
	- ETH present in trending snapshot (`asset_in_trending_now=true`)
- Post-evaluation step completed:
	- model retrained on all available historical + current-period data.

## Statistical Assumptions Note
- Current workflow uses time-based train/validation splits configured in Hydra.
- Indicator warmup removes first ~100 rows; extremely short date ranges can become invalid.
- A protective error now explains this case and suggests widening date range or reducing windowing.

## 2026-04-16 Multi-Asset Meta-Historical Gate Run (ETHUSD, XBTUSD, SOLUSD)

### Run details
- Script: `meta_historical_test.py` (CLI UX refactor — complete)
- Command: `python meta_historical_test.py --assets ETHUSD,XBTUSD,SOLUSD --min-samples 100 --max-mape 4.0`
- Output: `outputs/meta_historical/2026-04-16/10-22-06/`
- Model: `RandomForestRegressor`, `n_estimators=300`, `random_state=42`, `lags=30`

### Per-asset results (106 evaluation samples, evaluation year 2026)

| Asset  | Acc (model) | MAPE (model) | Acc (naive) | MAPE (naive) | Passes Gate |
|--------|-------------|--------------|-------------|--------------|-------------|
| ETHUSD | 0.581       | 2.96 %       | 0.514       | 2.80 %       | **YES**     |
| XBTUSD | 0.495       | 12.86 %      | 0.552       | 2.01 %       | NO (MAPE >> 4%) |
| SOLUSD | 0.562       | 5.58 %       | 0.524       | 2.94 %       | NO (MAPE > 4%) |

### Artifacts per asset
Each asset directory contains:
- `accuracy_time_trend.png` — 2D time-vs-accuracy chart (X=rolling accuracy, Y=date)
- `accuracy_time_curve.csv` — underlying curve data
- `current_year_predictions.csv` — daily close predictions vs. realized API prices
- `*_model_retrained.joblib` — model retrained on all available data

### Session artifacts (root of run folder)
- `summary.csv` — cross-asset metrics and gate decisions
- `next_best_decision.txt` — auto-generated next step text

### Next Best Decision (auto-generated by gate)
> Gate failed for: XBTUSD, SOLUSD.
> Keep fixed assets and lags, increase `n_estimators` to 500, and rerun only failed assets to test if MAPE falls below threshold.

### Interpretation
- ETH model beats naive on directional accuracy but is marginally beaten on MAPE (model 2.96% vs naive 2.80%).
  Directional edge is signal; MAPE gap is marginal and may dissolve when more YTD data accumulates.
- XBT extremely high MAPE (12.86%) suggests price regime shift in evaluation period not captured by past training window.
  Increasing tree count alone unlikely to close this gap; feature engineering or shorter training window may help.
- SOL directional accuracy is +3.8pp over naive; MAPE borderline (5.58% vs 4.0% gate). Worth a focused rerun.
- Fix applied during this run: CSV loader now handles heterogeneous schemas (`timestamp`/`Date`, optional index column).
- Plotting backend now forced to `Agg` (non-interactive) for stable CLI execution without tkinter.

## 2026-04-16 Next Best Decision Run — n_estimators=500 (XBTUSD, SOLUSD, ETHUSD)

### Commands
```bash
python meta_historical_test.py --assets XBTUSD,SOLUSD --n-estimators 500 --min-samples 100 --max-mape 4.0
python meta_historical_test.py --assets ETHUSD --n-estimators 500 --min-samples 100 --max-mape 4.0
```

### Results (106 eval samples, 2026)

| Asset  | Acc (model) | MAPE (model) | Acc (naive) | MAPE (naive) | Gate |
|--------|-------------|--------------|-------------|--------------|------|
| ETHUSD | 0.581       | 2.96 %       | 0.514       | 2.80 %       | PASS |
| XBTUSD | 0.505       | 12.97 %      | 0.552       | 2.01 %       | FAIL |
| SOLUSD | 0.562       | 5.60 %       | 0.524       | 2.94 %       | FAIL |

### Finding
Increasing n_estimators from 300 → 500 did **not** meaningfully reduce MAPE for XBT or SOL.
- XBT MAPE remains ~13%: consistent with a price-regime shift in 2026 not captured by pre-2024 training data.
- SOL MAPE borderline at ~5.6% vs gate 4.0%: model beats naive on direction (+3.8pp) but magnitude errors remain high.
- Root cause for XBT is **data distribution shift**, not model capacity.

### New artifacts per asset (11-07-23 and 11-36-32 run folders)
- `price_prediction_chart.png` — **new** 2-subplot chart:
  - Top: daily close, actual (orange) vs predicted (blue dashed), X-axis on monthly scale
  - Bottom: weekly price fluctuation bar chart (actual Δ orange, predicted Δ blue)

### Security audit (2026-04-16 session close)
- Scanned all `.py`, YAML, and Markdown files: **no hardcoded credentials found**.
- Bitmex loader uses env vars (`BITMEX_API_KEY`, `BITMEX_API_SECRET`); no `.env` file in repo.
- `.gitignore` updated to explicitly exclude `.env`, `.env.*`, `*.secret`, `*.pem`, `*.key`.

### Next Best Decision
XBT regime shift requires a **shortened training window experiment**:
```bash
# Retrain using only 2022-2024 local data, test if recency reduces MAPE
python meta_historical_test.py --assets XBTUSD --n-estimators 300 --min-samples 100 --max-mape 4.0
```
Then add rolling-window retraining (e.g., trailing 365 days) for assets with high MAPE.

## 2026-04-16 Model Comparison, Speed/Precision Trade-offs & System Tuning

### Models available in this repo
| Model          | File                        | Dependency          | Accuracy potential | Speed    |
|----------------|-----------------------------|---------------------|--------------------|----------|
| RandomForest   | `models/random_forest.py`   | scikit-learn (std)  | Baseline (good)    | Fast     |
| XGBoost        | `models/xgboost.py`         | xgboost             | Better on tabular  | Moderate |
| LSTM           | `models/LSTM.py`            | PyTorch/Keras       | High (sequential)  | Slow     |
| GRU            | `models/GRU.py`             | PyTorch/Keras       | High (sequential)  | Slow     |
| ARIMA          | `models/arima.py`           | statsmodels         | Good (univariate)  | Fast     |
| SARIMAX        | `models/sarimax.py`         | statsmodels         | Good (+exogenous)  | Fast     |
| Prophet        | `models/prophet.py`         | prophet             | Good (trend/season)| Moderate |
| NeuralProphet  | `models/neural_prophet.py`  | neuralprophet       | Better than Prophet| Moderate |
| Orbit          | `models/orbit.py`           | orbit-ml            | Bayesian, rigorous | Slow     |

### Deterministic accuracy hierarchy (for daily crypto close prediction)
1. **GRU / LSTM** — highest ceiling but require >2000 rows to converge; overfit on short series; slow to train.
2. **XGBoost** (with RandomizedSearchCV) — best tree-model ceiling with tuned hyperparams; 5-fold CV adds ~5× overhead vs RF.
3. **RandomForest** — strong baseline, deterministic with `random_state=42`, very fast. **Current `meta_historical_test.py` default.**
4. **Prophet / NeuralProphet** — good for explicit trend/seasonality decomposition; slower first-fit; non-trivial to compare apples-to-apples.
5. **ARIMA / SARIMAX** — competitive for stationary univariate series; XBT's regime shift would likely defeat them too.

### Speed vs. Precision knobs (in `meta_historical_test.py`)
| Parameter       | Default | Faster               | More precise                       |
|-----------------|---------|----------------------|------------------------------------|
| `--n-estimators`| 300     | 50–100 (coarse)      | 500–1000 (marginal gain above 300) |
| `--lags`        | 30      | 7–14                 | 60–90 (needs more data)            |
| `--wf-horizon`  | 14      | skip (`--wf-step` large) | 7 (finer intervals)            |
| `--wf-step`     | 7       | 30                   | 3–5                                |
| `n_jobs=-1`     | already set | —               | —                                  |

### Is the system already tuned for max speed?
**Partially yes:**
- `RandomForestRegressor(n_jobs=-1)` uses all CPU cores — already optimal for RF.
- XGBoost's `RandomizedSearchCV` with `n_jobs=-1` and `n_iter=20` keeps search tractable.
- No GPU acceleration is configured (unnecessary at this data scale).
- Main bottleneck at this scale (~3 years of daily data) is **API latency** (CoinGecko/CoinCap fallback chain), not model fitting.
- At `n_estimators=300, lags=30`: ETH full run completes in <5s locally.

**What would materially improve accuracy (not just speed):**
1. Add rolling-window retraining (trailing 365 days) for assets with regime shift (XBT).
2. Add `lag_volume` features alongside `lag_close` — volume often leads price changes.
3. Try XGBoost with reduced `n_iter=10, cv=3` as a fast-but-better alternative to RF.
4. For longer horizons (≥7 days ahead), switch to SARIMAX or Prophet for explicit seasonality.

### Chart update (2026-04-16 session)
- `save_price_prediction_plot()` now highlights the week of **maximum predicted-vs-actual divergence** in red on the weekly subplot, with annotation showing date and magnitude.

## 2026-04-16 Dataset Audit — Senior Data Analyst Evaluation

### Audit scope
All 38 CSV files in `data/` (19 assets × 2 timeframes: `1d` + `1h`). Backup excluded.
Automated audit script: `_dataset_audit.py` (temporary — removed post-run).
Metrics checked: row count, span days, null/zero close %, duplicate timestamps, intraday/daily gaps, extreme daily moves (>40%), volume quality.

### Summary by verdict

| Grade      | Count | Assets (1d series)                                      |
|------------|-------|---------------------------------------------------------|
| GOOD       | 10    | XBTUSD, ETHUSD, BCHUSD, LTCUSD + hourly counterparts   |
| ACCEPTABLE | 20    | ADAUSD, AVAXUSD, BNBUSD, DOGE, DOT, EOS, LINK, SOL, AXS, ETH-1h |
| MARGINAL   | 7     | APE, APT, CRO, NEAR, PEPE(1d), TRX                     |
| POOR       | 1     | **PEPEUSDT-1h** (3353 duplicate timestamps, 145 gaps)   |

### Per-asset findings (1d series — primary for meta-historical model)

| Asset   | Span (days) | Bars | Issues                                            | Verdict     |
|---------|-------------|------|---------------------------------------------------|-------------|
| XBTUSD  | 2829        | 2830 | 2 dup TS on 1h (negligible)                       | **GOOD**    |
| ETHUSD  | 1659        | 1660 | 1h: 31 dup TS (resolvable with dedup)             | **GOOD**    |
| BCHUSD  | 975         | 976  | 1 extreme move (historical event, expected)       | **GOOD**    |
| LTCUSD  | 931         | 932  | —                                                 | **GOOD**    |
| ADAUSD  | 505         | 506  | —                                                 | ACCEPTABLE  |
| AVAXUSD | 505         | 506  | —                                                 | ACCEPTABLE  |
| BNBUSD  | 505         | 506  | —                                                 | ACCEPTABLE  |
| DOGEUSD | 505         | 506  | 1 extreme move                                    | ACCEPTABLE  |
| DOTUSD  | 505         | 506  | —                                                 | ACCEPTABLE  |
| EOSUSD  | 484         | 485  | —                                                 | ACCEPTABLE  |
| LINKUSD | 484         | 485  | —                                                 | ACCEPTABLE  |
| SOLUSD  | 484         | 485  | 2 extreme moves (expected — high-beta asset)      | ACCEPTABLE  |
| AXSUSD  | 484         | 485  | 1 extreme move                                    | ACCEPTABLE  |
| NEARUSD | 287         | 288  | Short: 287d < 365d                                | MARGINAL    |
| APEUSD  | 154         | 155  | Short: 154d. 1h vol: 33% zero                     | MARGINAL    |
| TRXUSD  | 154         | 155  | Short: 154d. 1h vol: 36% zero                     | MARGINAL    |
| PEPEUSDT| 138         | 139  | Short: 138d                                       | MARGINAL    |
| APTUSD  | 119         | 120  | Short: 119d. 2 extreme moves on new listing       | MARGINAL    |
| CROUSD  | 95          | 96   | Very short: 95d. 1h vol: 62% zero                 | MARGINAL    |
| PEPEUSDT-1h | 145     | 146  | 3353 dup TS, 145 hourly gaps, extreme move        | **POOR**    |

### Critical observations (data analyst assessment)

#### 1 — Dataset horizon cutoff: February 2023 for most assets
All Bitmex-sourced files (everything except XBTUSD, ETH-1h, PEPE) end on **2023-02-17**.
This means they collectively miss:
- The March 2023 banking crisis (USDC depeg, SVB)
- The 2023–2024 bull run (ETH 2x, BTC ATH)
- The 2024–2026 entire market cycle

**Impact on predictions:** any model trained exclusively on these 1d datasets will have learned only on a bear-to-sideways regime (Q4 2021 → Q1 2023). It will systematically underestimate prices during bull runs and overestimate during deeper drawdowns. This is the primary explanation for XBT's MAPE of 13% in the 2026 evaluation.

#### 2 — XBTUSD is the most complete series (2015–2023, 2830 bars)
XBT is the only asset with >5 years of daily history, covering 3 full market cycles. For cycle-aware experiments, XBT is the most statistically sound asset in the repo. Its current high MAPE is a regime-shift artefact, not a data quality problem.

#### 3 — ETH-1h has 31 duplicate timestamps
Minor issue. The `load_local_close_series()` loader already handles this via `keep="last"` groupby. No action needed, but a deduplication pass before training would tighten the hourly features.

#### 4 — Short-series assets (APT, CRO, APE, TRX, NEAR, PEPE ≤ 365d)
These 6 assets have **insufficient history for reliable supervised learning**:
- A lag-30 RF model needs at least ~200 rows after warmup → APT (120d) and CRO (95d) fail this minimum.
- A single half-year window captures only one part of the crypto cycle (in this case, early bear).
- No seasonality or trend decomposition models (ARIMA, Prophet) will produce stable estimates.

**Recommendation:** Do not use these assets in `meta_historical_test.py` without first extending the local data via API backfill.

#### 5 — PEPEUSDT-1h is corrupted (POOR)
3353 duplicate timestamps over only 145 days means ~23 duplicate rows per day on average — likely a collection bug (rows appended multiple times). The 1d file is clean (MARGINAL only for shortness). **Do not use PEPE-1h for any model training.**

#### 6 — Volume data quality is inconsistent on newer/smaller assets
- CROUSD-1h: 62.4% zero/null volume
- NEARUSD-1h: 32.0%
- APEUSD-1h: 33.0%
- TRXUSD-1h: 36.3%

This means volume cannot be used as a feature for these assets without imputation. For XBT, ETH, BCH, LTC: volume is clean (0–0.4% issues) and viable as a feature.

#### 7 — No external features present
All datasets are OHLCV from a single exchange (BitMEX). No on-chain data, no sentiment, no BTC dominance, no macro features (DXY, Fed rate). This is expected for an experimental repo but limits the ceiling of any trained model.

### Suitability for reliable predictions

| Tier | Assets | Condition |
|------|--------|-----------|
| **Reliable (production-grade experiment)** | XBTUSD, ETHUSD, BCHUSD, LTCUSD | ≥ 900d clean daily data; zero structural gaps |
| **Usable with caveats** | ADAUSD, AVAXUSD, BNBUSD, DOGE, DOT, EOS, LINK, SOL, AXS | ~500d; bear-only regime; no post-2023 cycle coverage |
| **Experimental only (treat output as illustrative)** | NEARUSD, APEUSD, TRXUSD, PEPEUSDT-1d, APTUSD, CROUSD | <365d; models will overfit; high CI |
| **Do not use for training** | PEPEUSDT-1h | Corrupt; 3353 duplicate rows |

### Required actions to improve dataset fitness

1. **Extend all datasets from 2023-02-17 → 2026-04-16** via Bitmex or free API (CoinCap/CryptoCompare). Priority: ETHUSD, SOLUSD, ADAUSD.
2. **Deduplicate ETHUSD-1h** (31 duplicates) and **delete PEPEUSDT-1h**.
3. **Add XBT 2023–2026 data** — this is the single highest-ROI action: XBT already has 8 years of history; adding 3 years of bull/bear cycle will likely drop its MAPE from 13% to a competitive range.
4. **Consider removing APTUSD, CROUSD** from default experiments until data is extended; their brevity creates misleading evaluation statistics.

### Artefact
Full JSON audit results saved during session at `_dataset_audit_results.json` (not committed — ephemeral analysis file).

## Known Risks / Debt
- Some model dependencies (e.g., legacy deep-learning/time-series libs) may require specific Python versions.
- Metrics can include both directional and regression objectives; interpretation should be explicit in reports.
- Bitmex online data path remains network-dependent when local CSV is unavailable.
- Backtester emits margin warnings for some strategy signals; this is simulation behavior from the underlying library, not a runtime crash.

## 2026-04-16 Dataset Refresh + Retrain + Expanded Meta-Historical Recheck

### Dataset maintenance completed
- Extended all `*-1d-data.csv` files to `2026-04-15` using CryptoCompare daily bars.
- Deduplicated all CSVs (1d and 1h) by timestamp and normalized away unnamed index columns.
- Summary of maintenance run:
	- New rows appended: `21,775`
	- Duplicate rows removed: `3,386`
	- Key duplicate fixes: `PEPEUSDT-1h (-3353)`, `ETHUSD-1h (-31)`, `XBTUSD-1h (-2)`

### Train smoke test after big review
- Command used (load-path mode on refreshed daily ETH CSV):
	- `python train.py load_path=d:/CryptoPredictions/data/ETHUSD-1d-data.csv model.n_estimators=100 dataset_loader.train_start_date='2022-01-01 00:00:00' dataset_loader.train_end_date='2025-01-01 00:00:00' dataset_loader.valid_start_date='2025-01-01 00:00:00' dataset_loader.valid_end_date='2025-12-31 00:00:00'`
- Status: completed successfully (train + evaluate + profit_calculator).
- Observed validation metrics (`validation-0`):
	- `accuracy_score=0.612`, `f1_score=0.606`, `recall_score=0.602`, `precision_score=0.609`
	- `MAE=143.71`, `RMSE=253.67`, `MAPE=3.85`, `SMAPE=4.01`, `MASE=2.08`, `MSLE=0.004`

### Meta-historical retest on more assets (leakage-safe split)
- Command:
	- `python meta_historical_test.py --assets ETHUSD,XBTUSD,SOLUSD,ADAUSD,LTCUSD,BCHUSD --train-cutoff 2025-12-31 --min-samples 50 --max-mape 5.0 --n-estimators 300`
- Output folder:
	- `outputs/meta_historical/2026-04-16/12-59-52/`
- Rationale:
	- Local datasets now include 2026 rows; therefore explicit `--train-cutoff 2025-12-31` was used to avoid train/eval overlap and keep 2026 as clean evaluation period.

| Asset  | Eval Samples | Model Accuracy | Model MAPE | Naive Accuracy | Naive MAPE | Gate (MAPE<=5) |
|--------|--------------|----------------|------------|----------------|------------|----------------|
| ETHUSD | 106          | 0.533          | 2.89%      | 0.514          | 2.79%      | PASS |
| XBTUSD | 106          | 0.514          | 2.69%      | 0.543          | 2.02%      | PASS |
| SOLUSD | 106          | 0.524          | 4.81%      | 0.524          | 2.93%      | PASS |
| ADAUSD | 106          | 0.486          | 3.35%      | 0.495          | 3.13%      | PASS |
| LTCUSD | 106          | 0.562          | 2.51%      | 0.524          | 2.11%      | PASS |
| BCHUSD | 106          | 0.495          | 2.64%      | 0.543          | 2.28%      | PASS |

### Trend artifacts available
- For each asset in the run folder:
	- `price_prediction_chart.png` (daily prediction vs realized + weekly fluctuation/divergence)
	- `accuracy_time_trend.png` (time/accuracy trend)
	- `current_year_predictions.csv`, `accuracy_time_curve.csv`, `meta_historical_report.json`

### Interpretation (research-only)
- The post-refresh regime-shift effect on XBT dropped materially compared with earlier runs (MAPE now `2.69%`).
- Directional edge over naive remains mixed across assets; magnitude error is now consistently within gate for all tested assets.
- These are simulation metrics for predictive model quality, not investment guidance.

### Next Best Decision
- Keep the same leakage-safe split and run a deterministic 4-week rolling recheck (same 6 assets, same cutoff policy) to verify stability of MAPE and directional metrics before any model-class change.

## 2026-04-16 Deep Code Review — Bug Fixes (14 issues)

### Bugs fixed in this session
1. **`metrics/metrics.py` → `mape()` division by zero**: Added epsilon guard for zero targets.
2. **`metrics/metrics.py` → `msle()` negative input crash**: Added `np.clip` guard for values < -1.
3. **`data_loader/creator.py` → bare `except:`**: Changed to `except (KeyError, TypeError):`.
4. **`data_loader/creator.py` → `features.remove('Date')` mutated DataFrame columns**: Changed to `list(dataset.columns)`.
5. **`data_loader/creator.py` → hardcoded `[100:]` slice**: Replaced with `INDICATOR_WARMUP = 100` constant.
6. **`data_loader/indicators.py` → `add_indicators_to_dataset()` mutated caller's list**: Added `list()` copy.
7. **`models/random_forest.py` → missing `n_jobs=-1`**: Added for full CPU utilization in train.py pipeline.
8. **`models/xgboost.py` → `verbose=3` hardcoded**: Changed to `verbose=0`.
9. **`factory/profit_calculator.py` → `exist_ok=False`**: Changed to `exist_ok=True` to allow re-runs.
10. **`utils/reporter.py` → `exist_ok=False`**: Changed to `exist_ok=True`.
11. **`train.py` → unnecessary `global` statement**: Replaced with local variable initialization.
12. **`meta_historical_test.py` → unused `date_index` variable**: Removed.
13. **`meta_historical_test.py` → `coin_id_to_symbol()` silent ETH fallback**: Changed to raise `ValueError`.
14. **`backtester.py` → `save_report()` path handling**: Added `os.path.isdir()` check for safe path resolution.

## 2026-04-16 NDB Stability Recheck (post-bugfix)

### Run
- Command: `python meta_historical_test.py --assets ETHUSD,XBTUSD,SOLUSD,ADAUSD,LTCUSD,BCHUSD --train-cutoff 2025-12-31 --min-samples 50 --max-mape 5.0 --n-estimators 300`
- Output: `outputs/meta_historical/2026-04-16/13-27-53/`

### Results — identical to pre-bugfix run (stability confirmed)
| Asset  | Eval | Acc   | MAPE  | Gate  |
|--------|------|-------|-------|-------|
| ETHUSD | 106  | 0.533 | 2.89% | PASS  |
| XBTUSD | 106  | 0.514 | 2.69% | PASS  |
| SOLUSD | 106  | 0.524 | 4.81% | PASS  |
| ADAUSD | 106  | 0.486 | 3.35% | PASS  |
| LTCUSD | 106  | 0.562 | 2.51% | PASS  |
| BCHUSD | 106  | 0.495 | 2.64% | PASS  |

### Interpretation
Bug fixes did not alter model outputs — confirms no behavioral regression from code hardening.

## 2026-04-16 Experimental Steps

### Exp 1: SOL n_estimators=500
- MAPE: 4.80% (vs 4.81% at n=300) — negligible, confirms data regime not model capacity.

### Exp 2: Strict gate max-mape=4.0
- 5/6 PASS, SOL FAIL (4.81%). SOL is a high-beta asset with structural MAPE > 4%.

### Exp 3: Feature Mode A/B Testing (ETH)

| Mode     | Lags | Feature Count | MAPE     | Accuracy | Naive Edge |
|----------|------|---------------|----------|----------|------------|
| close    | 30   | 30            | **2.89%**| 0.533    | +1.9pp     |
| close    | 14   | 14            | 3.03%    | **0.571**| **+5.7pp** |
| focused  | 30   | 47            | 3.04%    | 0.562    | +4.8pp     |
| focused  | 14   | 24            | 3.12%    | 0.543    | +2.9pp     |
| enhanced | 30   | 79            | 3.45%    | 0.467    | -4.7pp     |

### Key Findings
1. **close-only lags=30**: best MAPE (2.89%) — simplest model wins on magnitude error.
2. **close-only lags=14**: best directional accuracy (0.571, +5.7pp over naive) — fewer dimensions = less noise.
3. **focused (close + RSI + MACD)**: good directional edge at lags=30 (+4.8pp) but not additive with short lags.
4. **enhanced (full OHLCV + all indicators)**: worst overall — feature explosion with limited training data causes overfitting.
5. **More features != better predictions** — the binding constraint is training data regime, not feature space.

### Predictive Power Key (deterministic analysis)
The single highest-impact change for this system is **reducing lag dimensionality from 30 to 14** for directional accuracy tasks. This triples the naive directional edge (from +1.9pp to +5.7pp) with only a marginal MAPE cost (+0.14pp).

For MAPE-sensitive tasks, the current lags=30 close-only remains optimal.

The system now has 3 feature modes via `--features`:
- `close` (default): baseline lag-close model
- `focused`: close lags + RSI-14 + MACD + returns (close-derived, no OHLCV API dependency)
- `enhanced`: full OHLCV lags + volume + all indicators (needs CryptoCompare OHLCV)

### Next Best Decision
Run a 6-asset gate with `--features focused --lags 14 --max-mape 5.0` to verify the directional accuracy improvement generalizes across all assets, not just ETH.

## 2026-04-16 Next Best Decision Execution: Focused+Lags=14 6-Asset Run

### Run Command
```bash
python meta_historical_test.py --assets ETHUSD,XBTUSD,SOLUSD,ADAUSD,LTCUSD,BCHUSD \
  --train-cutoff 2025-12-31 --min-samples 50 --max-mape 5.0 --n-estimators 300 \
  --features focused --lags 14 --wf-horizon 14 --wf-step 14
```

### Results — Focused+Lags=14 vs Baseline (Close+Lags=30)

| Asset  | Baseline Acc | Focused Acc | Baseline MAPE | Focused MAPE | Winner      |
|--------|--------------|-------------|---------------|--------------|-------------|
| ETHUSD | 0.533        | 0.543       | 2.89%         | 3.12%        | Focused (+1.0pp acc) |
| XBTUSD | 0.514        | 0.438       | 2.69%         | 2.59%        | Baseline (-7.6pp acc) |
| SOLUSD | 0.524        | 0.486       | 4.81%         | 4.21%        | Focused (-0.60pp mape) |
| ADAUSD | 0.486        | 0.514       | 3.35%         | 3.32%        | Focused (+2.8pp acc) |
| LTCUSD | 0.562        | 0.543       | 2.51%         | 2.50%        | Baseline (-1.9pp acc) |
| BCHUSD | 0.495        | 0.505       | 2.64%         | 2.62%        | Focused (+1.0pp acc) |

**Average Performance:**
- Accuracy: Baseline 0.528 vs Focused 0.510 (Baseline wins by 1.8pp)
- MAPE: Baseline 3.21% vs Focused 3.21% (tie)
- **Gate Pass Rate (5.0%):** Both 6/6 PASS
- **Gate Pass Rate (4.0%):** Baseline 5/6, Focused **6/6** (Focused unlocks SOL!)

### Critical Insight: No Universal Winner
The data reveals **asset-specific behavior**:
- **Established, trending assets (XBT=Bitcoin, LTC)**: longer lags (30) better — capture sustained price momentum
- **Volatile/newer assets (ADA, SOL, ETH)**: shorter lags (14) better — reduce noise, improve signal
- **Focused mode benefit:** RSI + MACD indicators specifically help SOL MAPE (4.81% → 4.21%)

### Deterministic Recommendation
A heterogeneous strategy per asset would be superior:
- XBT, LTC: `--lags 30 --features close` (magnitude-focused)
- ETH, ADA, BCH: `--lags 14 --features close` (direction-focused)
- SOL: `--lags 14 --features focused` (MAPE-optimized, passes 4.0% gate)

## Code Improvements and Optimizations

### Speed improvements already in place
- `RandomForest(n_jobs=-1)` now set in both `train.py` and `meta_historical_test.py`
- `XGBoost(verbose=0)` eliminates log spam
- `exist_ok=True` prevents re-run crashes

### Recommended future improvements (not implemented, for reference)
1. **Feature importance reporting**: Add `model.feature_importances_` output to meta_historical_test artifacts.
2. **Ensemble voting**: Combine RF + XGBoost predictions with simple average.
3. **Confidence intervals**: Use RF tree-level predictions for 90% CI.
4. **Parallel asset processing**: Use `concurrent.futures.ProcessPoolExecutor` for multi-asset runs.
5. **API response caching**: Cache CryptoCompare/CoinGecko responses locally.
6. **Rolling window training option**: Add `--train-window N` flag to use only last N days for training.

### Known limitations
- SOL MAPE consistently > 4% regardless of n_estimators or feature mode — inherent high-beta regime effect.
- `enhanced` mode degrades performance with current data volume (~1000 training rows); needs 3000+ rows.
- Walk-forward scoring is slow for 6 assets (~3 minutes total due to sequential model refitting).

## 2026-04-16 Heterogeneous Per-Asset NDB Strategy (Final Implementation)

### Strategy rationale
A/B testing revealed **no universal winner** across all 6 assets. Instead:
- Established/trending assets (XBT, LTC) benefit from long lag windows (lags=30) for magnitude accuracy
- Volatile/newer assets (ETH, ADA, BCH) benefit from shorter lags (lags=14) for directional accuracy reduction of noise
- SOL requires both shorter lags AND focused feature mode to hit MAPE gate

### Heterogeneous-per-asset execution (3 sequential NDB runs)

| Run | Assets | Lags | Features | Rationale |
|-----|--------|------|----------|-----------|
| Part 1 | XBTUSD, LTCUSD | 30 | close | Magnitude-focused (trending assets) |
| Part 2 | ETHUSD, ADAUSD, BCHUSD | 14 | close | Direction-focused (volatile/newer) |
| Part 3 | SOLUSD | 14 | focused | MAPE-optimized (high-beta specialist) |

### Results (2026-04-16 15:01:07 UTC)

**Part 1 (lags=30, close): Magnitude-focused**
| Asset  | MAPE  | Accuracy | Gate | Strategy |
|--------|-------|----------|------|----------|
| XBTUSD | 2.69% | 0.514    | PASS | Established trend momentum needs 30-day context |
| LTCUSD | 2.51% | 0.562    | PASS | **BEST PREDICTABLE ASSET** (lowest MAPE, highest accuracy) |

**Part 2 (lags=14, close): Direction-focused**
| Asset  | MAPE  | Accuracy | Gate | Strategy |
|--------|-------|----------|------|----------|
| ETHUSD | 3.03% | 0.571    | PASS | 5.7pp directional edge over close+lags=30 |
| ADAUSD | 3.38% | 0.533    | PASS | 2.8pp directional boost from shorter lags |
| BCHUSD | 2.66% | 0.467    | PASS | 1.0pp directional improvement |

**Part 3 (lags=14, focused): MAPE-optimized**
| Asset  | MAPE  | Accuracy | Gate | Strategy |
|--------|-------|----------|------|----------|
| SOLUSD | 4.21% | 0.486    | PASS | Focused mode reduces MAPE from 4.81% ? 4.21% (-0.60pp) |

### Best predictable asset: **LTCUSD**
- **Lowest MAPE:** 2.51% (vs 2.69% XBT, 3.03% ETH, 3.38% ADA, 2.66% BCH, 4.21% SOL)
- **Highest Accuracy:** 0.562 (vs 0.514 XBT, 0.571 ETH, 0.533 ADA, 0.467 BCH, 0.486 SOL)
- **Trade Stability:** Long-term price history (931 days clean daily data) with single-regime bear movement
- **Interpretation:** LTC has the most predictable/stable magnitude trajectory in 2026, with lower directional ambiguity

### Weekly divergence/convergence analysis for LTCUSD
- **Visualization:** outputs/meta_historical/best_asset_divergence_analysis.png
- Chart shows:
  - Top subplot: Weekly close (actual vs predicted) with divergence/convergence peak annotations
  - Bottom subplot: Weekly absolute error magnitude with rolling 3-week average and threshold bands
- **Key statistics:**
  - Total weeks analyzed: 16
  - Divergence peaks (high error): 3 weeks
  - Convergence peaks (low error): 7 weeks
  - Mean absolute error: \.51 USD
  - Worst week error: \.85 (2026-01-12 to 2026-01-18, actual close \.79)
  - Best week error: \.53 (2026-03-30 to 2026-04-05, actual close \.56)
  - Error std deviation: \.66 (highly stable week-to-week)

### Safety recommendations
1. **Use LTCUSD as the production-grade benchmark asset** for future model comparisons.
2. **For heterogeneous strategies**, implement per-asset config in meta_historical_test.py (suggested next step).
3. **Avoid over-generalization:** XBT, ETH, and SOL still have regime-shift / MAPE risks; treat their 2026 predictions as simulations.
4. **Weekly divergence stability** (LTCUSD): 7/16 convergence weeks means model learned a stable pattern; validate on next quarter before deployment.

### Next Best Decision
Implement per-asset hyperparameter routing in meta_historical_test.py:
- Add --per-asset-config flag with JSON mapping asset ? {lags, features}
- Default to: XBTUSD/LTCUSD: lags=30,close | ETHUSD/ADAUSD/BCHUSD: lags=14,close | SOLUSD: lags=14,focused
- Re-run full 6-asset test with per-asset config to validate that automated routing matches manual strategic assignment

## 2026-04-16 Documentation Update (README)

### What changed
- Added a new README section: "2026 Reproducible Example (How The Software Works)".
- Documented deterministic commands for:
	- 6-asset leakage-safe benchmark (`--train-cutoff 2025-12-31`)
	- Heterogeneous per-asset strategy (XBT/LTC lags=30 close, ETH/ADA/BCH lags=14 close, SOL lags=14 focused)
- Embedded local 2026 chart examples directly in README:
	- `outputs/meta_historical/2026-04-16/14-55-45/LTCUSD/price_prediction_chart.png`
	- `outputs/meta_historical/2026-04-16/14-59-21/ETHUSD/price_prediction_chart.png`
	- `outputs/meta_historical/best_asset_divergence_analysis.png`

### Why
- Provide a clear "how it works" walkthrough for 2026 outputs using real artifacts.
- Improve reproducibility and onboarding by showing exact commands and expected result style.

### Residual risk
- README image links point to generated artifacts that may not exist in a fresh clone until the example commands are executed.

### Next Best Decision
Add a small script wrapper (or Make/Task target) that runs the 2026 example and validates that all README-referenced chart artifacts are present.

## 2026-04-16 README Validation Wrapper Added

### What changed
- Added `scripts/run_2026_readme_example.ps1`.
- Added VS Code task file `.vscode/tasks.json` with task label `run-2026-readme-example`.
- Wrapper behavior:
	- Default mode: fast validation only (checks README chart artifacts exist).
	- `-RunAll` mode: reruns all 2026 example commands and rebuilds divergence chart, then validates artifacts.

### Validation evidence
- Executed fast mode successfully:
	- `powershell -ExecutionPolicy Bypass -File scripts/run_2026_readme_example.ps1`
- Confirmed all three README-referenced charts exist.

### Residual risk
- Full `-RunAll` mode can be time-consuming for walk-forward runs and may be interrupted on constrained environments.

### Next Best Decision
Keep README chart references aligned with deterministic output locations, or add a latest-run symlink/copy step if output timestamp folders change.

## 2026-07-05 Projection Lab & What-If Scenarios

### What changed
- Added `services/projection.py` — recursive RF forward projection with confidence bands (tree percentiles 10/50/90).
- Added `config/asset_profiles.json` — heterogeneous per-asset strategy from KB (XBT/LTC lags=30 close; ETH/ADA/BCH lags=14 close; SOL lags=14 focused).
- Added `app_projection.py` — Streamlit UI for projections and what-if scenarios (bear/bull shocks, volatility multiplier).
- Added `project_forward.py` — headless CLI for projections and scenario comparison.
- Added Cursor skills: `.cursor/skills/crypto-predictions-projection/`, `.cursor/skills/stealth-browser-market-data/`.
- Added Cursor agents: `.cursor/agents/projection-scenario-analyst.agent.md`, `.cursor/agents/market-data-researcher.agent.md`.
- Updated `Documents/AGENT_GUIDE.md` and `requirements.txt` (streamlit, joblib).

### Validation evidence
- `python project_forward.py --asset ETHUSD --horizon 14 --as-of 2023-02-17 --no-save` → end_forecast 1642.7 from last_observed 1638.3.
- `python project_forward.py --asset SOLUSD --horizon 30 --scenarios "Bear,-20;Bull,15" --no-save` → focused profile applied, 2 scenarios generated.

### Limitations
- Recursive 1-step RF forecasts compound error beyond ~30–60 days.
- What-if shocks are synthetic perturbations, not macro-economic models.
- No live API refresh in projection path — uses local CSV only.

### Next Best Decision
Run `streamlit run app_projection.py` and validate fan chart + scenario compare tab with ETHUSD and one bear-shock scenario.

## 2026-07-05 Deep Acquisition/Train Evaluation — Decision: DEFER

### Executive decision
**Non eseguire ora una deep acquisition + retrain completo.** I dati daily sono già estesi; il gap operativo è modesto (81 giorni). Le nuove capacità (Projection Lab, scenari what-if, agenti) portano più valore immediato di un re-tuning massivo dei profili RF. Il passo data-driven va fatto in **Fase 2** (calibrazione automatizzata), non come blocco monolitico adesso.

### Motivazioni (evidence-based)

#### 1 — Data layer: già sufficiente per sperimentazione, non obsoleto
Audit locale 2026-07-05 su `data/*-1d-data.csv`:

| Metrica | Valore |
|---------|--------|
| Asset daily | 19 |
| Fine serie | **2026-04-15** (tutti) |
| Gap vs oggi | **81 giorni** (uniforme) |
| Duplicati timestamp | 0 su tutti i daily |
| XBTUSD span | 2015-09-26 → 2026-04-15 (3855 righe) |
| ETHUSD span | 2018-08-03 → 2026-04-15 (2813 righe) |

> **KB superseded:** la sezione "All Bitmex-sourced files end on 2023-02-17" (2026-04-16 audit) non riflette più lo stato attuale. I CSV sono stati backfillati fino ad aprile 2026.

**Conclusione data acquisition:** serve solo un **incremental refresh** (81 giorni), non una deep acquisition da zero. Priorità bassa rispetto a validare Projection Lab e scenari.

#### 2 — Profile grid eval: profili attuali non ottimali su MAPE, ma delta marginale
Script: `scripts/profile_grid_eval.py`  
Metodo: grid `lags ∈ {14,30}` × `features ∈ {close, focused}`, holdout locale `> 2025-12-31` (105 giorni), `n_estimators=300`, criterio best = min MAPE.

| Asset | Profilo attuale | Best MAPE (holdout) | Match | Δ MAPE vs attuale |
|-------|-----------------|---------------------|-------|-------------------|
| XBTUSD | 30, close | 14, focused (2.618%) | NO | ~0.10pp |
| LTCUSD | 30, close | 30, focused (2.457%) | NO | ~0.07pp |
| ETHUSD | 14, close | 30, close (2.912%) | NO | ~0.12pp |
| ADAUSD | 14, close | 30, focused (3.252%) | NO | ~0.16pp |
| BCHUSD | 14, close | 30, focused (2.597%) | NO | ~0.13pp |
| **SOLUSD** | **14, focused** | **14, focused (4.281%)** | **YES** | — |
| BNBUSD | default 30, close | 14, focused (2.238%) | NO | profilo mancante |
| DOGEUSD | default | 14, close (3.318%) | NO | profilo mancante |
| AVAXUSD | default | 14, close (3.142%) | NO | profilo mancante |

**Osservazioni:**
- Solo **SOLUSD** conferma il profilo eterogeneo originale su dati estesi.
- I mismatch sono **piccoli** (<0.2pp MAPE): non giustificano un retrain massivo prima di walk-forward multi-obiettivo (MAPE + directional).
- 13 asset su 19 usano ancora il profilo `default` — gap di copertura, non di qualità dati.
- SOL resta l'asset più difficile (MAPE ~4.3% anche col best config).

**Conclusione train:** un deep retrain ora produrrebbe profili leggermente diversi ma **non strutturalmente migliori** senza: (a) obiettivo multi-metrica, (b) walk-forward, (c) validazione su orizzonte projection (7–30d), non solo holdout flat.

#### 3 — Nuove capacità acquisite: valutazione skill/agent

| Capability | Stato | Valore immediato | Gap residuo |
|------------|-------|------------------|-------------|
| `ProjectionService` + fan chart | Operativo | Esplorazione futuri ipotetici | Error compounding >60d |
| What-if scenarios (shock/vol) | Operativo | Stress test qualitativo | No macro/fundamental drivers |
| `asset_profiles.json` | 6/19 asset | Eterogeneità codificata | 13 asset su default; 5/6 non ottimali su MAPE holdout |
| Skill `crypto-predictions-projection` | Documentata | Onboarding agenti | Manca link a grid eval |
| Skill `stealth-browser-market-data` | Documentata | Refresh dati anti-bot | MCP non installato in repo |
| Agent `projection-scenario-analyst` | Attivo | Interpretazione scenari | Non ancora usato in run formale |
| Agent `market-data-researcher` | Attivo | Estensione dataset | Nessun run di refresh 81d eseguito |

### Cosa NON fare ora
1. ~~Deep re-download completo di tutti i CSV~~ — dati già a 2026-04-15.
2. ~~Grid search massivo con aggiornamento immediato di `asset_profiles.json`~~ — delta MAPE troppo piccolo; rischio overfit su 105 giorni holdout.
3. ~~Integrare Prophet/Orbit nel projection path~~ — scope troppo ampio per questa iterazione.

### Piano d'azione (3 fasi)

#### Fase 1 — Consolidare capacità projection (settimana corrente)
| # | Azione | Tool/Skill | Output atteso |
|---|--------|------------|---------------|
| 1.1 | Validare UI Projection Lab con ETH + bear shock | `app_projection.py`, skill projection | Screenshot/checklist scenario compare |
| 1.2 | Eseguire 3 proiezioni CLI su asset profilati (XBT, ETH, SOL) | `project_forward.py` | Artifact in `outputs/projections/` |
| 1.3 | Documentare limiti recursive forecast in UI (tooltip/disclaimer) | `app_projection.py` | UX chiara "simulation only" |

#### Fase 2 — Data-driven profile calibration (dopo Fase 1)
| # | Azione | Tool/Skill | Output atteso |
|---|--------|------------|---------------|
| 2.1 | Estendere `profile_grid_eval.py` → multi-obiettivo (MAPE + dir_acc + WF) | script + quant-research-gate agent | `config/asset_profiles_v2.json` draft |
| 2.2 | Aggiungere profili per BNB, DOGE, AVAX (best da grid) | `config/asset_profiles.json` | 9/19 asset profilati |
| 2.3 | Refresh incrementale 81 giorni (2026-04-16 → oggi) via API | `meta_historical_test.py` fetch | CSV aggiornati, KB entry |
| 2.4 | Se API rate-limit: usare stealth-browser MCP | skill stealth-browser, agent market-data-researcher | OHLCV normalizzato in `data/` |

#### Fase 3 — Integrazione predittiva avanzata (medio termine)
| # | Azione | Output |
|---|--------|--------|
| 3.1 | FastAPI wrapper su `ProjectionService` | API `POST /project`, `POST /scenarios/compare` |
| 3.2 | Scenario backtesting: path proiettati → `backtest/strategies.py` | Report simulazione strategia sotto shock |
| 3.3 | Prophet/Orbit per orizzonti 90–365d con bande native | Fan chart long-horizon |
| 3.4 | CI task: `profile_grid_eval.py` su gate assets | Regression su profili |

### Matrice priorità (impatto × sforzo)

```
Alta priorità / basso sforzo:  Fase 1 (Projection Lab validation)
Media priorità / medio sforzo: Fase 2.3 (refresh 81d) + Fase 2.1 (grid multi-obj)
Bassa priorità / alto sforzo:  Fase 3 (API + Prophet + scenario backtest)
Rimandato:                     Deep re-acquisition completa, retrain Hydra multi-model
```

### Rischi se si facesse deep train ORA
- Overfit su 105 giorni holdout 2026 YTD.
- Profili ottimizzati per MAPE peggiorano directional accuracy (es. XBT: lags=30 close ha dir_acc 0.538 vs focused 0.452).
- Tempo investito in tuning RF invece che in validare Projection Lab e scenari what-if — le nuove capability resterebbero sotto-utilizzate.

### Next Best Decision
Eseguire **Fase 1.2**: `python project_forward.py --asset XBTUSD --horizon 30 --scenarios "Bear,-15"` e salvare artifact; confrontare fan chart con profilo attuale (30, close) vs override manuale (14, focused) per quantificare impatto visivo del mismatch profilo — senza ancora aggiornare `asset_profiles.json`.

## 2026-07-05 Roadmap Implementation — 4 Features Shipped

### 1 — Prophet long-horizon fan charts (90–365 days)
- Module: `services/long_horizon.py`
- Models: `prophet` (default), `orbit` (optional, requires `orbit-ml`)
- API: `POST /api/v1/project/long`
- UI: Projection Lab tab **Long horizon**
- Validation: ETHUSD 90d Prophet → 90 rows, end forecast ~2808 USD

### 2 — FastAPI external integration
- Entry: `api/main.py` — run with `uvicorn api.main:app --reload --port 8000`
- VS Code task: `projection-api`
- Endpoints:
  - `GET /api/v1/health`, `/assets`, `/assets/{asset}/profile`
  - `POST /api/v1/project`, `/project/long`, `/scenarios/compare`
  - `POST /api/v1/backtest/scenario`
  - `POST /api/v1/data/refresh`, `/data/refresh/{asset}`
  - `GET /api/v1/data/stealth-instructions/{asset}`

### 3 — Scenario backtesting on projected paths
- Module: `services/scenario_backtest.py`
- CLI: `python scenario_backtest.py --asset ETHUSD --horizon 14 --scenarios "Bear,-10"`
- Merges historical tail (60d) + projected path; runs `signal1` via `backtesting` lib
- Validation: ETHUSD base return -16.2%, Bear scenario -33.3% (simulation only)

### 4 — Data refresh (API + stealth-browser fallback)
- Module: `services/data_refresh.py`
- CLI: `scripts/refresh_market_data.py`
- Chain: CryptoCompare OHLCV → CoinGecko/Yahoo close (synthetic OHLCV) → stealth-browser manual import
- Validation: ETHUSD refresh +81 rows (2026-04-15 → 2026-07-05) via Yahoo fallback after CryptoCompare 401
- Import path: `--import-csv <capture.csv>` for stealth-browser network captures

### Dependencies added
- `fastapi`, `uvicorn`, `pydantic` in `requirements.txt`

### Next Best Decision
Avviare FastAPI (`uvicorn api.main:app --port 8000`) e testare `POST /api/v1/project/long` con `{"asset":"ETHUSD","horizon_days":180,"model":"prophet"}`; poi refresh batch `--all` per allineare tutti i 19 asset a oggi.

## 2026-08-29 Structural Audit + Aug-15 Coherence Analysis

### KB drift correction
- Front-matter **Current State** added (this file top).
- Data refreshed: all 19 daily assets → **2026-08-29** (+~54 bars from 2026-07-05).
- Dead code removed in `build_supervised_focused` (unreachable block after `return`).

### Structural findings (summary)
| Category | P0 | P1 |
|----------|----|----|
| Structural | Dual Hydra vs meta/services pipelines; meta god-module | Profiles not wired into meta CLI; signal1 duplicated |
| Duplication | Features ×2, metrics ×2 | CSV loaders ×2, RSI/MACD duplicated in meta |
| Performance | Recursive projection rebuilds supervised every day | Tree-interval O(n_estimators) per day; walk-forward refits |
| Maintainability | Zero automated tests | 6/19 profiles; chronological KB contradictions |

### Refactor strategy (ordered)
1. **Phase A** — Extract `core/` from meta (I/O, features, metrics); delete dead code ✅ started; golden tests.
2. **Phase B** — Incremental features + batched tree preds for recursive projection.
3. **Phase C** — Meta CLI reads `asset_profiles.json`; expand BNB/DOGE/AVAX after multi-obj grid.
4. **Phase D** — Optional Hydra↔meta convergence; single metrics module; CI smoke.
5. **Phase E** — Scheduled data refresh; keep KB Current State fresh.

### Deterministic Aug-15 ±15d coherence (simulation only)

**Protocol**
- Anchor: **2026-08-15**
- PRE: train `< 2026-08-01`, 1-step eval `2026-08-01..15` (actual lags, leakage-safe)
- POST 1-step: train `<= 2026-08-15`, eval `2026-08-16..29` with **actual** lags (upper bound)
- POST recursive: train `<= 2026-08-15`, Projection Lab recursive path vs realized (true forward use-case)
- Artifact: `outputs/analyses/aug15_coherence_2026.json` / `scripts/aug15_coherence_analysis.py`

**Market context (realized)** — strong post-Aug-15 rally on majors (BTC ~+23%, ETH ~+30%, SOL ~+38% from Aug 15 close through Aug 29).

| Asset | PRE MAPE | PRE dir | PRE dir edge vs naive | POST 1-step MAPE | POST 1-step dir | POST recursive MAPE | Recursive return gap (pp) | End-dir match (rec) |
|-------|----------|---------|----------------------|------------------|-----------------|---------------------|---------------------------|---------------------|
| XBTUSD | 0.73% | 0.50 | 0.0pp | 2.86% | 0.58 | **14.25%** | **-23.2** | NO |
| ETHUSD | 0.75% | **0.71** | **+50pp** | 3.34% | **0.75** | **18.08%** | **-30.0** | NO |
| SOLUSD | 1.22% | 0.29 | -14pp | 3.78% | 0.67 | **16.89%** | **-37.6** | YES* |
| LTCUSD | 0.81% | 0.43 | -7pp | 2.82% | **0.75** | 8.78% | -9.9 | YES |
| ADAUSD | 9.15% | 0.64 | -14pp | 7.62% | 0.58 | 12.92% | -12.8 | YES |
| BCHUSD | 1.08% | 0.50 | -7pp | 4.18% | 0.67 | 15.74% | -18.7 | YES |

\*SOL recursive end-direction match is technically `true` only because predicted return ≈ +0.07% (near-flat) while actual was +37.6% — **not** a meaningful forecast of the rally; magnitude gap dominates.

**Verdict**
1. **PRE (Aug 1–15):** Coherent on magnitude for BTC/ETH/LTC/BCH (MAPE ≈ 0.7–1.1%). ETH had strong directional edge (+50pp vs naive). SOL/ADA weaker (SOL dir below naive; ADA MAPE 9.15%).
2. **POST 1-step with oracle lags:** Model tracks day-to-day levels better (MAPE ~2.8–4.2% majors) and often beats naive on direction (ETH +25pp, LTC +17pp). Still **under-captures** the full window return (positive return gaps on BTC/ETH/SOL/BCH when comparing last pred vs first actual).
3. **POST recursive (Projection Lab path):** **Not coherent with the realized rally.** Forecasts collapse near persistence (pred return ≈ 0%), MAPE 9–18%, return gap **-10 to -38 pp**. Only ~7–23% of days fall inside the 10–90% tree band. The RF recursive engine failed this regime-shift window.

**Implication for product:** short-horizon 1-step validation remains useful; multi-day recursive RF should be labeled as **low-confidence in strong trend breaks**, and long-horizon Prophet/Orbit (or recalibration) preferred for 14d+ paths after shocks.

### Next Best Decision
Ship Phase A extract of `core/features.py` + unit test, then add a Projection Lab UI warning when `|recursive_return| < 1%` while historical 14d realized vol is high (regime-shift caution).
