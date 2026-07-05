"""Backtest trading signals on projected price paths (simulation only)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from backtesting import Backtest, Strategy

from meta_historical_test import load_local_ohlcv
from path_definition import ROOT_DIR
from services.assets import resolve_data_path
from services.projection import ProjectionResult, ScenarioSpec


@dataclass
class ScenarioBacktestResult:
    asset_symbol: str
    scenario_name: str
    stats: dict[str, Any]
    equity_final: float
    return_pct: float
    trades: int
    metadata: dict[str, Any] = field(default_factory=dict)


def projection_path_to_backtest_df(
    historical: pd.DataFrame,
    projection: pd.DataFrame,
    history_days: int = 60,
) -> pd.DataFrame:
    """Merge historical OHLCV tail with projected path for signal simulation."""
    hist = historical.tail(history_days).copy()
    hist = hist.reset_index().rename(columns={"date": "Date", "close": "Close", "high": "High", "low": "Low", "open": "Open", "volume": "Volume"})

    proj = projection.copy()
    proj["Date"] = pd.to_datetime(proj["date"])
    spread = (proj["interval_high"] - proj["interval_low"]).fillna(0) * 0.5
    proj_rows = pd.DataFrame(
        {
            "Date": proj["Date"],
            "Close": proj["forecast_close"],
            "Open": proj["forecast_close"].shift(1).fillna(hist["Close"].iloc[-1]),
            "High": proj["forecast_close"] + spread,
            "Low": proj["forecast_close"] - spread,
            "Volume": hist["Volume"].iloc[-1],
            "predicted_mean": proj["forecast_close"],
            "predicted_high": proj.get("interval_high", proj["forecast_close"] + spread),
            "predicted_low": proj.get("interval_low", proj["forecast_close"] - spread),
        }
    )

    combined = pd.concat([hist, proj_rows], ignore_index=True)
    combined = combined.drop_duplicates(subset=["Date"], keep="last").sort_values("Date")
    combined = combined.set_index("Date")
    combined.columns = [c if c in ("Open", "High", "Low", "Close", "Volume") else c for c in combined.columns]
    return combined


class _ProjectionSignalStrategy(Strategy):
    def init(self):
        self.signal = self.I(lambda: self.data.Signal1)

    def next(self):
        sig = int(self.signal[-1])
        if sig == 2 and not self.position:
            self.buy()
        elif sig == 1 and self.position:
            self.position.close()


def _compute_signal1(df: pd.DataFrame) -> pd.Series:
    position = False
    signal = [0] * len(df)
    closes = df["Close"].values
    preds = df["predicted_mean"].values
    for i in range(1, len(signal)):
        if preds[i] > closes[i - 1]:
            if not position:
                signal[i] = 2
                position = True
        elif position:
            signal[i] = 1
            position = False
    return pd.Series(signal, index=df.index, name="signal1")


def run_scenario_backtest(
    asset_symbol: str,
    projection: pd.DataFrame,
    scenario_name: str = "base",
    history_days: int = 60,
    cash: float = 100_000,
    commission: float = 0.002,
) -> ScenarioBacktestResult:
    historical = load_local_ohlcv(resolve_data_path(asset_symbol))
    bt_df = projection_path_to_backtest_df(historical, projection, history_days=history_days)
    bt_df["Signal1"] = _compute_signal1(bt_df)

    bt = Backtest(bt_df, _ProjectionSignalStrategy, cash=cash, commission=commission)
    stats = bt.run()
    stats_dict = {k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in stats.items() if k != "_strategy"}

    return ScenarioBacktestResult(
        asset_symbol=asset_symbol.upper(),
        scenario_name=scenario_name,
        stats=stats_dict,
        equity_final=float(stats["Equity Final [$]"]),
        return_pct=float(stats["Return [%]"]),
        trades=int(stats["# Trades"]),
        metadata={"history_days": history_days, "rows": len(bt_df)},
    )


class ScenarioBacktestService:
    OUTPUT_ROOT = Path(ROOT_DIR) / "outputs" / "scenario_backtests"

    def backtest_projection_result(
        self,
        result: ProjectionResult,
        history_days: int = 60,
        persist: bool = True,
    ) -> list[ScenarioBacktestResult]:
        outcomes: list[ScenarioBacktestResult] = []
        paths = {"base": result.base_path, **result.scenario_paths}
        for name, path_df in paths.items():
            outcomes.append(
                run_scenario_backtest(
                    asset_symbol=result.asset_symbol,
                    projection=path_df,
                    scenario_name=name,
                    history_days=history_days,
                )
            )

        if persist:
            run_dir = self.OUTPUT_ROOT / f"{result.asset_symbol}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            run_dir.mkdir(parents=True, exist_ok=True)
            summary = [
                {
                    "scenario": o.scenario_name,
                    "return_pct": o.return_pct,
                    "equity_final": o.equity_final,
                    "trades": o.trades,
                }
                for o in outcomes
            ]
            with open(run_dir / "scenario_backtest_summary.json", "w", encoding="utf-8") as fp:
                json.dump(
                    {
                        "asset": result.asset_symbol,
                        "as_of_date": result.as_of_date,
                        "horizon_days": result.horizon_days,
                        "results": summary,
                        "disclaimer": "Simulation only — not investment advice.",
                    },
                    fp,
                    indent=2,
                )
        return outcomes

    def backtest_from_projection(
        self,
        asset_symbol: str,
        horizon_days: int = 30,
        scenarios: list[ScenarioSpec] | None = None,
        **kwargs: Any,
    ) -> list[ScenarioBacktestResult]:
        from services.projection import ProjectionService

        projection = ProjectionService().project_forward(
            asset_symbol=asset_symbol,
            horizon_days=horizon_days,
            scenarios=scenarios,
            persist=False,
            **kwargs,
        )
        return self.backtest_projection_result(projection)
