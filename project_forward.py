#!/usr/bin/env python
"""CLI for forward projections and what-if scenarios."""

import argparse
import json
from pathlib import Path

from services.projection import ProjectionService, ScenarioSpec


def parse_scenarios(raw: str | None) -> list[ScenarioSpec]:
    if not raw:
        return []
    specs = []
    for item in raw.split(";"):
        item = item.strip()
        if not item:
            continue
        parts = item.split(",")
        name = parts[0]
        shock = float(parts[1]) if len(parts) > 1 else 0.0
        specs.append(ScenarioSpec(name=name, price_shock_pct=shock))
    return specs


def main():
    parser = argparse.ArgumentParser(
        description="Forward crypto price projection with optional what-if scenarios (simulation only)."
    )
    parser.add_argument("--asset", default="ETHUSD", help="Asset symbol, e.g. ETHUSD")
    parser.add_argument("--horizon", type=int, default=30, help="Projection horizon in days")
    parser.add_argument("--as-of", default=None, help="As-of date YYYY-MM-DD (default: last available)")
    parser.add_argument("--lags", type=int, default=None, help="Override lag count")
    parser.add_argument("--features", choices=["close", "focused", "enhanced"], default=None)
    parser.add_argument("--n-estimators", type=int, default=None)
    parser.add_argument(
        "--scenarios",
        default=None,
        help="Semicolon-separated scenarios as name,pct_shock (e.g. 'Bear,-20;Bull,15')",
    )
    parser.add_argument("--no-save", action="store_true", help="Skip writing artifacts")
    args = parser.parse_args()

    service = ProjectionService()
    result = service.project_forward(
        asset_symbol=args.asset,
        horizon_days=args.horizon,
        as_of_date=args.as_of,
        lags=args.lags,
        feature_mode=args.features,
        n_estimators=args.n_estimators,
        scenarios=parse_scenarios(args.scenarios),
        persist=not args.no_save,
    )

    summary = {
        "asset": result.asset_symbol,
        "as_of_date": result.as_of_date,
        "horizon_days": result.horizon_days,
        "profile": result.profile,
        "last_observed_close": result.metadata["last_observed_close"],
        "end_forecast": float(result.base_path["forecast_close"].iloc[-1]),
        "scenarios": list(result.scenario_paths.keys()),
        "artifact_dir": result.metadata.get("artifact_dir"),
        "disclaimer": "Simulation only — not investment advice.",
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
