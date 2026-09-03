"""Sync trimmed daily OHLCV CSVs into Android assets/ohlcv for on-device engines."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "packaging" / "android" / "CryptoPredictionsApp" / "app" / "src" / "main" / "assets" / "ohlcv"
ASSETS = ["ETHUSD", "XBTUSD", "SOLUSD", "ADAUSD", "LTCUSD", "BNBUSD"]
TAIL = 900


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for asset in ASSETS:
        src = DATA / f"{asset}-1d-data.csv"
        if not src.exists():
            print(f"skip missing {asset}")
            continue
        df = pd.read_csv(src).tail(TAIL)
        dest = OUT / f"{asset}.csv"
        df.to_csv(dest, index=False)
        print(f"{asset}: {len(df)} rows -> {dest.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
