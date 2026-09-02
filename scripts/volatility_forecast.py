"""CLI: volatility event forecast (timing and magnitude of next +/-N% move)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.volatility_events import VolatilityEventService


def main() -> None:
    parser = argparse.ArgumentParser(description="Volatility event radar (simulation only).")
    parser.add_argument("asset", nargs="?", default="ETHUSD")
    parser.add_argument("--threshold", type=float, default=10.0, help="Move threshold %")
    parser.add_argument("--as-of", default=None, help="YYYY-MM-DD cutoff")
    args = parser.parse_args()

    result = VolatilityEventService().forecast(
        asset_symbol=args.asset,
        threshold_pct=args.threshold,
        as_of_date=args.as_of,
    )
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
