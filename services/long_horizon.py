"""Long-horizon projections via Prophet (default) and optional Orbit."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from meta_historical_test import load_local_close_series
from path_definition import ROOT_DIR
from services.assets import get_asset_profile, resolve_data_path

ModelKind = Literal["prophet", "orbit"]


@dataclass
class LongHorizonResult:
    asset_symbol: str
    as_of_date: str
    horizon_days: int
    model: str
    forecast: pd.DataFrame
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_artifact(self, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        run_dir = out_dir / f"{self.asset_symbol}_long_{run_id}"
        run_dir.mkdir(parents=True, exist_ok=True)
        self.forecast.to_csv(run_dir / "long_horizon_forecast.csv", index=False)
        return run_dir


class LongHorizonService:
    """Prophet/Orbit fan charts for 90–365 day horizons."""

    OUTPUT_ROOT = Path(ROOT_DIR) / "outputs" / "projections" / "long_horizon"
    MIN_HORIZON = 90
    MAX_HORIZON = 365

    def _load_close(self, asset_symbol: str, as_of_date: str | None) -> pd.Series:
        close = load_local_close_series(resolve_data_path(asset_symbol))
        if as_of_date:
            close = close[close.index <= pd.Timestamp(as_of_date)]
        if len(close) < 60:
            raise ValueError("Need at least 60 daily observations for long-horizon models.")
        return close.sort_index()

    def _prophet_forecast(self, close: pd.Series, horizon_days: int) -> pd.DataFrame:
        from prophet import Prophet

        frame = close.reset_index()
        frame.columns = ["ds", "y"]
        model = Prophet(
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=True,
            interval_width=0.80,
        )
        model.fit(frame)
        future = model.make_future_dataframe(periods=horizon_days, freq="D")
        forecast = model.predict(future)
        forecast = forecast.tail(horizon_days).copy()
        return pd.DataFrame(
            {
                "date": pd.to_datetime(forecast["ds"]),
                "forecast_close": forecast["yhat"].astype(float),
                "interval_low": forecast["yhat_lower"].astype(float),
                "interval_high": forecast["yhat_upper"].astype(float),
                "step": range(1, horizon_days + 1),
            }
        )

    def _orbit_forecast(self, close: pd.Series, horizon_days: int) -> pd.DataFrame:
        from orbit.models import DLT

        frame = close.reset_index()
        frame.columns = ["date", "close"]
        model = DLT(
            response_col="close",
            date_col="date",
            estimator="lgt",
            seasonality=365,
            seed=42,
            n_bootstrap_draws=200,
        )
        model.fit(df=frame)
        future_dates = pd.date_range(start=frame["date"].max() + pd.Timedelta(days=1), periods=horizon_days, freq="D")
        future_df = pd.DataFrame({"date": future_dates})
        predicted = model.predict(df=future_df, point_method="mean")
        low_col = "prediction_5" if "prediction_5" in predicted.columns else "prediction"
        high_col = "prediction_95" if "prediction_95" in predicted.columns else "prediction"
        return pd.DataFrame(
            {
                "date": future_dates,
                "forecast_close": predicted["prediction"].astype(float).values,
                "interval_low": predicted[low_col].astype(float).values,
                "interval_high": predicted[high_col].astype(float).values,
                "step": range(1, horizon_days + 1),
            }
        )

    def project(
        self,
        asset_symbol: str,
        horizon_days: int = 180,
        as_of_date: str | None = None,
        model: ModelKind = "prophet",
        persist: bool = True,
    ) -> LongHorizonResult:
        if horizon_days < self.MIN_HORIZON or horizon_days > self.MAX_HORIZON:
            raise ValueError(f"horizon_days must be between {self.MIN_HORIZON} and {self.MAX_HORIZON}.")

        close = self._load_close(asset_symbol, as_of_date)
        as_of = str(close.index.max().date())

        if model == "orbit":
            try:
                forecast = self._orbit_forecast(close, horizon_days)
            except ImportError as exc:
                raise ImportError("orbit-ml not installed. pip install orbit-ml or use model='prophet'.") from exc
        else:
            forecast = self._prophet_forecast(close, horizon_days)

        result = LongHorizonResult(
            asset_symbol=asset_symbol.upper(),
            as_of_date=as_of,
            horizon_days=horizon_days,
            model=model,
            forecast=forecast,
            metadata={
                "last_observed_close": float(close.iloc[-1]),
                "training_rows": int(len(close)),
                "method": f"long_horizon_{model}",
                "profile": get_asset_profile(asset_symbol),
                "disclaimer": "Simulation only — not investment advice.",
            },
        )
        if persist:
            run_dir = result.to_artifact(self.OUTPUT_ROOT)
            result.metadata["artifact_dir"] = str(run_dir)
        return result
