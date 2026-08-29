"""August 2026 real close vs multi-model forecast paths (simulation only).

Train cutoff: 2026-07-31. Forecast horizon: Aug 1 .. last available bar.
Models: Naive, RF recursive (profile), RF 1-step, XGBoost 1-step, ARIMA, Prophet
(optional deps skipped if missing).
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor

from core.features import build_supervised, build_supervised_focused
from core.io_ohlcv import load_local_close_series
from core.metrics_ts import all_scores
from services.assets import get_asset_profile, resolve_data_path
from services.projection import ProjectionService

CUTOFF = pd.Timestamp("2026-07-31")
AUG_START = pd.Timestamp("2026-08-01")
DEFAULT_ASSET = "ETHUSD"
OUT_DIR = Path(ROOT) / "outputs" / "analyses"


def _supervised(close: pd.Series, lags: int, features: str):
    if features == "focused":
        return build_supervised_focused(close, lags=lags)
    frame = build_supervised(close, lags=lags)
    cols = [f"lag_{i}" for i in range(1, lags + 1)]
    return frame, cols


def _path_frame(dates: pd.DatetimeIndex, values: np.ndarray, name: str) -> pd.Series:
    return pd.Series(values, index=dates, name=name)


def naive_path(close: pd.Series, aug_idx: pd.DatetimeIndex) -> pd.Series:
    last = float(close.loc[:CUTOFF].iloc[-1])
    return _path_frame(aug_idx, np.full(len(aug_idx), last), "naive")


def rf_recursive(asset: str, horizon: int) -> pd.Series:
    profile = get_asset_profile(asset)
    result = ProjectionService().project_forward(
        asset_symbol=asset,
        horizon_days=horizon,
        as_of_date=str(CUTOFF.date()),
        lags=profile["lags"],
        feature_mode=profile["features"],
        n_estimators=profile["n_estimators"],
        persist=False,
    )
    path = result.base_path.copy()
    path["date"] = pd.to_datetime(path["date"])
    return path.set_index("date")["forecast_close"].rename("rf_recursive")


def onestep_tree(
    close: pd.Series,
    aug_idx: pd.DatetimeIndex,
    lags: int,
    features: str,
    model,
    name: str,
) -> pd.Series:
    """1-step preds for August using actual lags (leakage-safe train on <= cutoff)."""
    sup, cols = _supervised(close, lags, features)
    train = sup.loc[sup.index <= CUTOFF]
    model.fit(train[cols].values, train["target"].values)
    window = sup.loc[aug_idx.intersection(sup.index)]
    preds = model.predict(window[cols].values)
    return _path_frame(window.index, preds, name)


def arima_path(close: pd.Series, aug_idx: pd.DatetimeIndex) -> pd.Series | None:
    try:
        from statsmodels.tsa.statespace.sarimax import SARIMAX
    except ImportError:
        return None
    hist = close.loc[:CUTOFF].astype(float)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = SARIMAX(hist, order=(2, 1, 2), enforce_stationarity=False, enforce_invertibility=False).fit(
            disp=False
        )
        fc = fit.forecast(steps=len(aug_idx))
    return _path_frame(aug_idx, np.asarray(fc, dtype=float), "arima")


def prophet_path(close: pd.Series, aug_idx: pd.DatetimeIndex) -> pd.Series | None:
    try:
        from prophet import Prophet
    except ImportError:
        return None
    hist = close.loc[:CUTOFF].reset_index()
    hist.columns = ["ds", "y"]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = Prophet(
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=True,
            interval_width=0.8,
        )
        model.fit(hist)
        future = pd.DataFrame({"ds": aug_idx})
        pred = model.predict(future)
    return _path_frame(aug_idx, pred["yhat"].astype(float).values, "prophet")


def xgb_onestep(
    close: pd.Series, aug_idx: pd.DatetimeIndex, lags: int, features: str
) -> pd.Series | None:
    try:
        from xgboost import XGBRegressor

        model = XGBRegressor(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
            n_jobs=-1,
            verbosity=0,
        )
    except ImportError:
        # Fallback still "in project spirit": sklearn GBM as tree booster stand-in
        model = GradientBoostingRegressor(random_state=42)
        name = "gbm_1step"
        return onestep_tree(close, aug_idx, lags, features, model, name)
    return onestep_tree(close, aug_idx, lags, features, model, "xgboost_1step")


def run(asset: str = DEFAULT_ASSET) -> dict:
    profile = get_asset_profile(asset)
    close = load_local_close_series(resolve_data_path(asset)).sort_index()
    close = close[close.index <= close.index.max()]
    aug = close.loc[(close.index >= AUG_START) & (close.index <= close.index.max())]
    if aug.empty:
        raise ValueError(f"No August bars for {asset}")
    aug_idx = aug.index
    horizon = int(len(aug_idx))

    series: dict[str, pd.Series] = {"actual": aug.rename("actual")}
    series["naive"] = naive_path(close, aug_idx)
    # Projection may land on calendar days missing from CSV (e.g. 08-28 vs 08-29 gap).
    series["rf_recursive"] = rf_recursive(asset, horizon).reindex(aug_idx).ffill().bfill()
    series["rf_1step"] = onestep_tree(
        close,
        aug_idx,
        profile["lags"],
        profile["features"],
        RandomForestRegressor(
            n_estimators=int(profile["n_estimators"]),
            random_state=42,
            n_jobs=-1,
        ),
        "rf_1step",
    )
    xgb = xgb_onestep(close, aug_idx, profile["lags"], profile["features"])
    if xgb is not None:
        series[xgb.name] = xgb.reindex(aug_idx)
    arima = arima_path(close, aug_idx)
    if arima is not None:
        series["arima"] = arima
    prophet = prophet_path(close, aug_idx)
    if prophet is not None:
        series["prophet"] = prophet

    frame = pd.concat(series.values(), axis=1)
    metrics = {}
    y_true = frame["actual"].values
    for col in frame.columns:
        if col == "actual":
            continue
        y_pred = frame[col].dropna()
        aligned = frame[["actual", col]].dropna()
        if len(aligned) < 3:
            continue
        scores = all_scores(aligned["actual"].values, aligned[col].values)
        metrics[col] = {
            "MAPE": round(scores["MAPE"], 3),
            "dir_acc": round(scores["accuracy_score"], 3),
            "end_pred": round(float(aligned[col].iloc[-1]), 4),
            "end_gap_pct": round(
                float(aligned[col].iloc[-1] / aligned["actual"].iloc[-1] - 1.0) * 100.0, 2
            ),
        }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / f"august_2026_paths_{asset}.csv"
    json_path = OUT_DIR / f"august_2026_paths_{asset}.json"
    frame.to_csv(csv_path, index_label="date")

    # Compact series for canvas (daily labels MM-DD, rounded closes)
    canvas = {
        "asset": asset,
        "cutoff": str(CUTOFF.date()),
        "range": [str(aug_idx.min().date()), str(aug_idx.max().date())],
        "profile": profile,
        "categories": [d.strftime("%m-%d") for d in aug_idx],
        "series": {
            name: [None if pd.isna(v) else round(float(v), 2) for v in frame[name].values]
            for name in frame.columns
        },
        "metrics": metrics,
        "actual_end": round(float(y_true[-1]), 2),
        "actual_start": round(float(y_true[0]), 2),
        "actual_return_pct": round(float(y_true[-1] / y_true[0] - 1.0) * 100.0, 2),
        "models_run": [c for c in frame.columns if c != "actual"],
        "note": "Simulation only — not investment advice. Train <= 2026-07-31.",
    }
    json_path.write_text(json.dumps(canvas, indent=2), encoding="utf-8")
    print(json.dumps({"csv": str(csv_path), "json": str(json_path), "metrics": metrics}, indent=2))
    return canvas


if __name__ == "__main__":
    asset = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ASSET
    run(asset)
