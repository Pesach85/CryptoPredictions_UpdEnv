"""CLI: real vs multi-model paths over a historical window.

Example:
  python scripts/august_multi_model_paths.py ETHUSD
  python scripts/august_multi_model_paths.py XBTUSD --start 2026-08-01 --end 2026-08-29
  python scripts/august_multi_model_paths.py ETHUSD --fast
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.multi_model_paths import ALL_MODELS, FAST_MODELS, MultiModelPathService


def main() -> None:
    parser = argparse.ArgumentParser(description="Real vs multi-model price paths (simulation only).")
    parser.add_argument("asset", nargs="?", default="ETHUSD")
    parser.add_argument("--start", default="2026-08-01", help="Window start (YYYY-MM-DD)")
    parser.add_argument("--end", default=None, help="Window end (default: last available bar)")
    parser.add_argument(
        "--models",
        default=None,
        help=f"Comma-separated subset of {','.join(ALL_MODELS)}",
    )
    parser.add_argument("--fast", action="store_true", help="Only naive + RF recursive + RF 1-step")
    parser.add_argument("--no-persist", action="store_true")
    args = parser.parse_args()

    if args.fast:
        models = FAST_MODELS
    elif args.models:
        models = [m.strip() for m in args.models.split(",") if m.strip()]
    else:
        models = None

    result = MultiModelPathService().run(
        asset_symbol=args.asset,
        window_start=args.start,
        window_end=args.end,
        models=models,
        persist=not args.no_persist,
    )
    payload = {
        "asset": result.asset_symbol,
        "cutoff": result.cutoff,
        "range": [result.window_start, result.window_end],
        "models_run": result.models_run,
        "metrics": result.metrics,
        "artifacts": result.metadata.get("artifact_paths"),
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
