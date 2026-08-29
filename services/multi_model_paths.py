"""Real vs multi-model price paths over a historical window (simulation only).

Train cutoff = day before window_start. Forecast window_start .. window_end
(or last available bar). Optional models skipped when deps are missing.
"""
from __future__ import annotations

import json
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor

from core.features import build_supervised, build_supervised_focused
from core.io_ohlcv import load_local_close_series
from core.metrics_ts import all_scores
from path_definition import ROOT_DIR
from services.assets import get_asset_profile, resolve_data_path
from services.projection import ProjectionService

OUT_DIR = Path(ROOT_DIR) / "outputs" / "analyses"

ALL_MODELS = (
    "naive",
    "rf_recursive",
    "rf_1step",
    "xgboost_1step",
    "arima",
    "prophet",
)
FAST_MODELS = ("naive", "rf_recursive", "rf_1step")


@dataclass
class MultiModelPathResult:
    asset_symbol: str
    cutoff: str
    window_start: str
    window_end: str
    frame: pd.DataFrame
    metrics: dict[str, dict[str, float]]
    profile: dict[str, Any]
    models_run: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        y_true = self.frame["actual"].values
        return {
            "asset": self.asset_symbol,
            "cutoff": self.cutoff,
            "range": [self.window_start, self.window_end],
            "profile": self.profile,
            "categories": [d.strftime("%m-%d") for d in self.frame.index],
            "series": {
                name: [None if pd.isna(v) else round(float(v), 2) for v in self.frame[name].values]
                for name in self.frame.columns
            },
            "metrics": self.metrics,
            "actual_end": round(float(y_true[-1]), 2),
            "actual_start": round(float(y_true[0]), 2),
            "actual_return_pct": round(float(y_true[-1] / y_true[0] - 1.0) * 100.0, 2),
            "models_run": self.models_run,
            "note": (
                f"Simulation only — not investment advice. Train <= {self.cutoff}."
            ),
            **self.metadata,
        }

    def persist(self, out_dir: Path | None = None) -> dict[str, str]:
        out = Path(out_dir) if out_dir else OUT_DIR
        out.mkdir(parents=True, exist_ok=True)
        tag = f"{self.window_start}_{self.window_end}".replace("-", "")
        stem = f"paths_{self.asset_symbol}_{tag}"
        csv_path = out / f"{stem}.csv"
        json_path = out / f"{stem}.json"
        self.frame.to_csv(csv_path, index_label="date")
        json_path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return {"csv": str(csv_path), "json": str(json_path)}


def _supervised(close: pd.Series, lags: int, features: str):
    if features == "focused":
        return build_supervised_focused(close, lags=lags)
    frame = build_supervised(close, lags=lags)
    cols = [f"lag_{i}" for i in range(1, lags + 1)]
    return frame, cols


def _path_frame(dates: pd.DatetimeIndex, values: np.ndarray, name: str) -> pd.Series:
    return pd.Series(values, index=dates, name=name)


class MultiModelPathService:
    """Compare actual closes to Naive / RF / XGB / ARIMA / Prophet over a window."""

    def run(
        self,
        asset_symbol: str,
        window_start: str = "2026-08-01",
        window_end: str | None = None,
        models: Iterable[str] | None = None,
        persist: bool = False,
        n_estimators_override: int | None = None,
    ) -> MultiModelPathResult:
        start = pd.Timestamp(window_start)
        cutoff = start - pd.Timedelta(days=1)
        selected = tuple(models) if models is not None else ALL_MODELS
        unknown = set(selected) - set(ALL_MODELS)
        if unknown:
            raise ValueError(f"Unknown models: {sorted(unknown)}. Allowed: {ALL_MODELS}")

        profile = get_asset_profile(asset_symbol)
        close = load_local_close_series(resolve_data_path(asset_symbol)).sort_index()
        end = pd.Timestamp(window_end) if window_end else close.index.max()
        window = close.loc[(close.index >= start) & (close.index <= end)]
        if window.empty:
            raise ValueError(f"No bars for {asset_symbol} in {start.date()} .. {end.date()}")
        if close.loc[:cutoff].empty:
            raise ValueError(f"No training history on or before {cutoff.date()}")

        idx = window.index
        horizon = int(len(idx))
        lags = int(profile["lags"])
        features = str(profile["features"])
        n_est = int(n_estimators_override or profile["n_estimators"])

        series: dict[str, pd.Series] = {"actual": window.rename("actual")}
        skipped: list[str] = []

        if "naive" in selected:
            last = float(close.loc[:cutoff].iloc[-1])
            series["naive"] = _path_frame(idx, np.full(horizon, last), "naive")

        if "rf_recursive" in selected:
            series["rf_recursive"] = self._rf_recursive(
                asset_symbol, horizon, str(cutoff.date()), profile, n_est
            ).reindex(idx).ffill().bfill()

        if "rf_1step" in selected:
            series["rf_1step"] = self._onestep_tree(
                close,
                idx,
                lags,
                features,
                cutoff,
                RandomForestRegressor(n_estimators=n_est, random_state=42, n_jobs=-1),
                "rf_1step",
            )

        if "xgboost_1step" in selected:
            xgb = self._xgb_onestep(close, idx, lags, features, cutoff)
            if xgb is None:
                skipped.append("xgboost_1step")
            else:
                series[xgb.name] = xgb.reindex(idx)

        if "arima" in selected:
            arima = self._arima_path(close, idx, cutoff)
            if arima is None:
                skipped.append("arima")
            else:
                series["arima"] = arima

        if "prophet" in selected:
            prophet = self._prophet_path(close, idx, cutoff)
            if prophet is None:
                skipped.append("prophet")
            else:
                series["prophet"] = prophet

        frame = pd.concat(series.values(), axis=1)
        metrics = self._metrics(frame)
        result = MultiModelPathResult(
            asset_symbol=asset_symbol,
            cutoff=str(cutoff.date()),
            window_start=str(idx.min().date()),
            window_end=str(idx.max().date()),
            frame=frame,
            metrics=metrics,
            profile=profile,
            models_run=[c for c in frame.columns if c != "actual"],
            metadata={
                "skipped_models": skipped,
                "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            },
        )
        if persist:
            paths = result.persist()
            result.metadata["artifact_paths"] = paths
        return result

    @staticmethod
    def _rf_recursive(
        asset: str, horizon: int, as_of: str, profile: dict, n_estimators: int
    ) -> pd.Series:
        result = ProjectionService().project_forward(
            asset_symbol=asset,
            horizon_days=horizon,
            as_of_date=as_of,
            lags=profile["lags"],
            feature_mode=profile["features"],
            n_estimators=n_estimators,
            persist=False,
        )
        path = result.base_path.copy()
        path["date"] = pd.to_datetime(path["date"])
        return path.set_index("date")["forecast_close"].rename("rf_recursive")

    @staticmethod
    def _onestep_tree(
        close: pd.Series,
        idx: pd.DatetimeIndex,
        lags: int,
        features: str,
        cutoff: pd.Timestamp,
        model,
        name: str,
    ) -> pd.Series:
        sup, cols = _supervised(close, lags, features)
        train = sup.loc[sup.index <= cutoff]
        if train.empty:
            raise ValueError("Empty supervised train set for 1-step model.")
        model.fit(train[cols].values, train["target"].values)
        window = sup.loc[idx.intersection(sup.index)]
        preds = model.predict(window[cols].values)
        return _path_frame(window.index, preds, name)

    def _xgb_onestep(
        self,
        close: pd.Series,
        idx: pd.DatetimeIndex,
        lags: int,
        features: str,
        cutoff: pd.Timestamp,
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
            name = "xgboost_1step"
        except ImportError:
            model = GradientBoostingRegressor(random_state=42)
            name = "gbm_1step"
        return self._onestep_tree(close, idx, lags, features, cutoff, model, name)

    @staticmethod
    def _arima_path(
        close: pd.Series, idx: pd.DatetimeIndex, cutoff: pd.Timestamp
    ) -> pd.Series | None:
        try:
            from statsmodels.tsa.statespace.sarimax import SARIMAX
        except ImportError:
            return None
        hist = close.loc[:cutoff].astype(float)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fit = SARIMAX(
                hist, order=(2, 1, 2), enforce_stationarity=False, enforce_invertibility=False
            ).fit(disp=False)
            fc = fit.forecast(steps=len(idx))
        return _path_frame(idx, np.asarray(fc, dtype=float), "arima")

    @staticmethod
    def _prophet_path(
        close: pd.Series, idx: pd.DatetimeIndex, cutoff: pd.Timestamp
    ) -> pd.Series | None:
        try:
            from prophet import Prophet
        except ImportError:
            return None
        hist = close.loc[:cutoff].reset_index()
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
            future = pd.DataFrame({"ds": idx})
            pred = model.predict(future)
        return _path_frame(idx, pred["yhat"].astype(float).values, "prophet")

    @staticmethod
    def _metrics(frame: pd.DataFrame) -> dict[str, dict[str, float]]:
        metrics: dict[str, dict[str, float]] = {}
        for col in frame.columns:
            if col == "actual":
                continue
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
        return metrics
