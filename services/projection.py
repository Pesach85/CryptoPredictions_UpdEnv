from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from meta_historical_test import (
    build_supervised,
    build_supervised_enhanced,
    build_supervised_focused,
    load_local_close_series,
    load_local_ohlcv,
)
from path_definition import ROOT_DIR
from services.assets import get_asset_profile, list_available_assets, resolve_data_path


@dataclass
class ScenarioSpec:
    name: str
    price_shock_pct: float = 0.0
    volatility_multiplier: float = 1.0
    volume_multiplier: float = 1.0
    shock_day: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProjectionResult:
    asset_symbol: str
    as_of_date: str
    horizon_days: int
    profile: dict[str, Any]
    base_path: pd.DataFrame
    scenario_paths: dict[str, pd.DataFrame] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_artifact(self, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        run_dir = out_dir / f"{self.asset_symbol}_{run_id}"
        run_dir.mkdir(parents=True, exist_ok=True)

        self.base_path.to_csv(run_dir / "base_projection.csv", index=False)
        for name, frame in self.scenario_paths.items():
            safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in name)
            frame.to_csv(run_dir / f"scenario_{safe}.csv", index=False)

        payload = {
            "asset_symbol": self.asset_symbol,
            "as_of_date": self.as_of_date,
            "horizon_days": self.horizon_days,
            "profile": self.profile,
            "metadata": self.metadata,
            "scenarios": [name for name in self.scenario_paths],
            "disclaimer": "Simulation only — not investment advice.",
        }
        with open(run_dir / "projection_report.json", "w", encoding="utf-8") as fp:
            json.dump(payload, fp, indent=2)
        return run_dir


class ProjectionService:
    """Forward projection and what-if scenario engine built on meta-historical features."""

    OUTPUT_ROOT = Path(ROOT_DIR) / "outputs" / "projections"

    def __init__(self, n_jobs: int = -1):
        self.n_jobs = n_jobs

    def list_assets(self, interval: str = "1d") -> list[str]:
        return list_available_assets(interval=interval)

    def get_profile(self, asset_symbol: str) -> dict:
        return get_asset_profile(asset_symbol)

    def _build_supervised_from_source(
        self,
        source: pd.Series | pd.DataFrame,
        lags: int,
        feature_mode: str,
    ) -> tuple[pd.DataFrame, list[str]]:
        if feature_mode == "enhanced":
            if not isinstance(source, pd.DataFrame):
                raise ValueError("Enhanced feature mode requires OHLCV DataFrame.")
            return build_supervised_enhanced(source, lags=lags)

        if not isinstance(source, pd.Series):
            source = source["close"]

        if feature_mode == "focused":
            return build_supervised_focused(source, lags=lags)

        supervised = build_supervised(source, lags=lags)
        feature_cols = [f"lag_{i}" for i in range(1, lags + 1)]
        return supervised, feature_cols

    def _load_initial_source(
        self,
        asset_symbol: str,
        feature_mode: str,
        as_of_date: pd.Timestamp | None,
    ) -> pd.Series | pd.DataFrame:
        csv_path = resolve_data_path(asset_symbol)
        if feature_mode == "enhanced":
            ohlcv = load_local_ohlcv(csv_path)
            if as_of_date is not None:
                ohlcv = ohlcv[ohlcv.index <= as_of_date]
            return ohlcv

        close_series = load_local_close_series(csv_path)
        if as_of_date is not None:
            close_series = close_series[close_series.index <= as_of_date]
        return close_series

    def _fit_model(
        self,
        supervised: pd.DataFrame,
        feature_cols: list[str],
        n_estimators: int,
    ) -> RandomForestRegressor:
        model = RandomForestRegressor(
            n_estimators=n_estimators,
            random_state=42,
            n_jobs=self.n_jobs,
        )
        model.fit(supervised[feature_cols].values, supervised["target"].values)
        return model

    def _tree_interval(self, model: RandomForestRegressor, features: np.ndarray) -> tuple[float, float, float]:
        tree_preds = np.array([tree.predict(features.reshape(1, -1))[0] for tree in model.estimators_])
        return (
            float(np.percentile(tree_preds, 10)),
            float(np.percentile(tree_preds, 50)),
            float(np.percentile(tree_preds, 90)),
        )

    def _append_close(self, series: pd.Series, date: pd.Timestamp, close: float) -> pd.Series:
        extended = series.copy()
        extended.loc[date] = float(close)
        return extended.sort_index()

    def _append_ohlcv(
        self,
        ohlcv: pd.DataFrame,
        date: pd.Timestamp,
        close: float,
        volume_multiplier: float = 1.0,
    ) -> pd.DataFrame:
        prev_close = float(ohlcv["close"].iloc[-1])
        daily_return = (close / prev_close) - 1.0 if prev_close else 0.0
        high = max(prev_close, close) * (1 + abs(daily_return) * 0.25)
        low = min(prev_close, close) * (1 - abs(daily_return) * 0.25)
        row = pd.DataFrame(
            {
                "open": [prev_close],
                "high": [high],
                "low": [low],
                "close": [close],
                "volume": [float(ohlcv["volume"].iloc[-1]) * volume_multiplier],
            },
            index=[date],
        )
        extended = pd.concat([ohlcv, row])
        return extended[~extended.index.duplicated(keep="last")].sort_index()

    def _recursive_forecast(
        self,
        source: pd.Series | pd.DataFrame,
        model: RandomForestRegressor,
        lags: int,
        feature_mode: str,
        start_date: pd.Timestamp,
        horizon_days: int,
        scenario: ScenarioSpec | None = None,
    ) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        working_source = source.copy()
        last_close = float(
            working_source["close"].iloc[-1] if isinstance(working_source, pd.DataFrame) else working_source.iloc[-1]
        )

        for step in range(1, horizon_days + 1):
            supervised, feature_cols = self._build_supervised_from_source(
                working_source, lags=lags, feature_mode=feature_mode
            )
            features = supervised.iloc[-1][feature_cols].values
            low, point, high = self._tree_interval(model, features)

            if scenario and scenario.volatility_multiplier != 1.0:
                deviation = point - last_close
                point = last_close + deviation * scenario.volatility_multiplier
                low = last_close + (low - last_close) * scenario.volatility_multiplier
                high = last_close + (high - last_close) * scenario.volatility_multiplier

            if scenario and scenario.price_shock_pct != 0.0 and step == max(1, scenario.shock_day):
                shock_factor = 1.0 + (scenario.price_shock_pct / 100.0)
                point *= shock_factor
                low *= shock_factor
                high *= shock_factor

            next_date = start_date + timedelta(days=step)
            rows.append(
                {
                    "date": next_date,
                    "forecast_close": point,
                    "interval_low": low,
                    "interval_high": high,
                    "step": step,
                }
            )

            if isinstance(working_source, pd.DataFrame):
                vol_mult = scenario.volume_multiplier if scenario else 1.0
                working_source = self._append_ohlcv(
                    working_source, next_date, point, volume_multiplier=vol_mult
                )
            else:
                working_source = self._append_close(working_source, next_date, point)

            last_close = point

        frame = pd.DataFrame(rows)
        frame["date"] = pd.to_datetime(frame["date"])
        return frame

    def project_forward(
        self,
        asset_symbol: str,
        horizon_days: int = 30,
        as_of_date: str | None = None,
        lags: int | None = None,
        feature_mode: str | None = None,
        n_estimators: int | None = None,
        scenarios: list[ScenarioSpec] | None = None,
        persist: bool = True,
    ) -> ProjectionResult:
        if horizon_days < 1 or horizon_days > 365:
            raise ValueError("horizon_days must be between 1 and 365.")

        profile = get_asset_profile(asset_symbol)
        lags = lags if lags is not None else profile["lags"]
        feature_mode = feature_mode or profile["features"]
        n_estimators = n_estimators if n_estimators is not None else profile["n_estimators"]

        as_of_ts = pd.Timestamp(as_of_date) if as_of_date else None
        source = self._load_initial_source(asset_symbol, feature_mode, as_of_ts)
        supervised, feature_cols = self._build_supervised_from_source(source, lags, feature_mode)
        if supervised.empty:
            raise ValueError("No supervised rows available for projection.")

        effective_as_of = str(supervised.index.max().date())
        model = self._fit_model(supervised, feature_cols, n_estimators)
        start_date = supervised.index.max()

        base_path = self._recursive_forecast(
            source=source,
            model=model,
            lags=lags,
            feature_mode=feature_mode,
            start_date=start_date,
            horizon_days=horizon_days,
            scenario=None,
        )
        base_path["scenario"] = "base"

        scenario_paths: dict[str, pd.DataFrame] = {}
        for scenario in scenarios or []:
            scenario_frame = self._recursive_forecast(
                source=source,
                model=model,
                lags=lags,
                feature_mode=feature_mode,
                start_date=start_date,
                horizon_days=horizon_days,
                scenario=scenario,
            )
            scenario_frame["scenario"] = scenario.name
            scenario_paths[scenario.name] = scenario_frame

        result = ProjectionResult(
            asset_symbol=asset_symbol.upper(),
            as_of_date=effective_as_of,
            horizon_days=horizon_days,
            profile={
                "lags": lags,
                "features": feature_mode,
                "n_estimators": n_estimators,
            },
            base_path=base_path,
            scenario_paths=scenario_paths,
            metadata={
                "training_rows": int(len(supervised)),
                "last_observed_close": float(supervised["target"].iloc[-1]),
                "method": "recursive_random_forest_1step",
                "disclaimer": "Simulation only — not investment advice.",
            },
        )

        if persist:
            run_dir = result.to_artifact(self.OUTPUT_ROOT)
            joblib.dump(model, run_dir / f"{asset_symbol}_projection_model.joblib")
            result.metadata["artifact_dir"] = str(run_dir)

        return result

    def compare_scenarios(
        self,
        asset_symbol: str,
        horizon_days: int,
        scenarios: list[ScenarioSpec],
        **kwargs: Any,
    ) -> ProjectionResult:
        return self.project_forward(
            asset_symbol=asset_symbol,
            horizon_days=horizon_days,
            scenarios=scenarios,
            **kwargs,
        )
