#!/usr/bin/env python
"""Run scenario backtest on projected paths."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.projection import ProjectionService, ScenarioSpec
from services.scenario_backtest import ScenarioBacktestService


def parse_scenarios(raw: str | None) -> list[ScenarioSpec]:
    if not raw:
        return []
    specs = []
    for item in raw.split(";"):
        parts = item.strip().split(",")
        if parts and parts[0]:
            specs.append(ScenarioSpec(name=parts[0], price_shock_pct=float(parts[1]) if len(parts) > 1 else 0.0))
    return specs


def main():
    parser = argparse.ArgumentParser(description="Scenario backtest on projected price paths.")
    parser.add_argument("--asset", default="ETHUSD")
    parser.add_argument("--horizon", type=int, default=30)
    parser.add_argument("--scenarios", default=None, help="name,pct;name,pct")
    parser.add_argument("--history-days", type=int, default=60)
    args = parser.parse_args()

    proj = ProjectionService().project_forward(
        asset_symbol=args.asset,
        horizon_days=args.horizon,
        scenarios=parse_scenarios(args.scenarios),
        persist=False,
    )
    outcomes = ScenarioBacktestService().backtest_projection_result(proj, history_days=args.history_days)
    print(
        json.dumps(
            [
                {
                    "scenario": o.scenario_name,
                    "return_pct": o.return_pct,
                    "equity_final": o.equity_final,
                    "trades": o.trades,
                }
                for o in outcomes
            ],
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
