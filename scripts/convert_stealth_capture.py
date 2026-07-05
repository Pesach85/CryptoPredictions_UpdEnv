#!/usr/bin/env python
"""Convert stealth-browser JSON network capture to importable OHLCV CSV."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.stealth_capture import capture_to_import_csv, load_capture_file


def main():
    parser = argparse.ArgumentParser(description="Convert stealth-browser JSON capture to OHLCV CSV.")
    parser.add_argument("--input", required=True, help="Path to JSON capture file")
    parser.add_argument("--output", help="Output CSV path (default: outputs/data_refresh/<stem>_import.csv)")
    parser.add_argument("--preview", action="store_true", help="Print row count and date range only")
    args = parser.parse_args()

    input_path = Path(args.input)
    ohlcv = load_capture_file(input_path)

    if args.preview:
        print(
            json.dumps(
                {
                    "rows": len(ohlcv),
                    "start": str(ohlcv.index.min().date()),
                    "end": str(ohlcv.index.max().date()),
                    "last_close": float(ohlcv["close"].iloc[-1]),
                },
                indent=2,
            )
        )
        return

    output_path = Path(args.output) if args.output else ROOT / "outputs" / "data_refresh" / f"{input_path.stem}_import.csv"
    written = capture_to_import_csv(ohlcv, output_path)
    print(json.dumps({"status": "ok", "csv_path": str(written), "rows": len(ohlcv)}, indent=2))


if __name__ == "__main__":
    main()
