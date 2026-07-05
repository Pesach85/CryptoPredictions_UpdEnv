#!/usr/bin/env python
"""CLI to refresh local OHLCV CSVs via API or import stealth-browser captures."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.data_refresh import (
    CAPTURE_DIR,
    import_ohlcv_from_file,
    import_stealth_capture_json,
    list_capture_files,
    refresh_all_assets,
    refresh_asset_via_api,
    refresh_status,
    stealth_browser_instructions,
)


def main():
    parser = argparse.ArgumentParser(
        description="Refresh local crypto OHLCV datasets.",
        epilog=(
            "Examples:\n"
            "  python scripts/refresh_market_data.py --status\n"
            "  python scripts/refresh_market_data.py --asset ETHUSD\n"
            "  python scripts/refresh_market_data.py --all --delay 2.0\n"
            "  python scripts/refresh_market_data.py --retry-failed\n"
            "  python scripts/refresh_market_data.py --list-captures\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--asset", help="Single asset symbol, e.g. ETHUSD")
    parser.add_argument("--all", action="store_true", help="Refresh all daily assets")
    parser.add_argument("--status", action="store_true", help="Show data end date and gap per asset")
    parser.add_argument("--retry-failed", action="store_true", help="Retry assets not current from last --all log")
    parser.add_argument("--delay", type=float, default=1.5, help="Seconds between assets in --all (default 1.5)")
    parser.add_argument("--import-csv", metavar="PATH", help="Import OHLCV from CSV file")
    parser.add_argument("--import-json", metavar="PATH", help="Import OHLCV from stealth-browser JSON capture")
    parser.add_argument("--list-captures", action="store_true", help="List JSON files in outputs/data_refresh/")
    parser.add_argument("--no-backup", action="store_true", help="Skip .bak backup before merge")
    parser.add_argument("--stealth-help", action="store_true", help="Print stealth-browser fallback steps")
    args = parser.parse_args()

    backup = not args.no_backup

    if args.list_captures:
        files = list_capture_files()
        print(json.dumps({"capture_dir": str(CAPTURE_DIR), "files": files}, indent=2))
        return

    if args.status:
        print(json.dumps(refresh_status(), indent=2))
        return

    if args.stealth_help:
        asset = args.asset or "ETHUSD"
        print(stealth_browser_instructions(asset))
        return

    if args.import_json:
        if not args.asset:
            parser.error("--asset required with --import-json")
        try:
            result = import_stealth_capture_json(args.asset, args.import_json, backup=backup)
            print(json.dumps(result, indent=2))
        except FileNotFoundError as exc:
            print(json.dumps({"status": "error", "error": str(exc)}, indent=2))
            sys.exit(1)
        return

    if args.import_csv:
        if not args.asset:
            parser.error("--asset required with --import-csv")
        try:
            result = import_ohlcv_from_file(args.asset, args.import_csv, backup=backup)
            print(json.dumps(result, indent=2))
        except FileNotFoundError as exc:
            print(json.dumps({"status": "error", "error": str(exc)}, indent=2))
            sys.exit(1)
        return

    if args.retry_failed:
        stale = [r["asset"] for r in refresh_status() if r["needs_refresh"]]
        if not stale:
            print(json.dumps({"status": "ok", "message": "All assets already current"}, indent=2))
            return
        results = refresh_all_assets(assets=stale, backup=backup, delay_sec=args.delay)
        print(json.dumps(results, indent=2))
        return

    if args.all:
        results = refresh_all_assets(backup=backup, delay_sec=args.delay)
        errors = [r for r in results if r.get("status") == "error"]
        print(json.dumps(results, indent=2))
        if errors:
            print(f"\n{len(errors)} asset(s) failed. Retry with: python scripts/refresh_market_data.py --retry-failed")
        return

    if args.asset:
        result = refresh_asset_via_api(args.asset, backup=backup)
        print(json.dumps(result, indent=2))
        if result.get("status") == "error":
            print(stealth_browser_instructions(args.asset))
            sys.exit(1)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
