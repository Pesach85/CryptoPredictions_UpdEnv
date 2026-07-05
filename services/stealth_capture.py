"""Parse stealth-browser network captures (JSON) into OHLCV DataFrames."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def _rows_from_cryptocompare(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("Data", {}).get("Data", [])
    if not rows and isinstance(payload.get("Data"), list):
        rows = payload["Data"]
    out = []
    for row in rows:
        if not isinstance(row, dict) or "time" not in row:
            continue
        out.append(
            {
                "timestamp": pd.to_datetime(int(row["time"]), unit="s", utc=True),
                "open": float(row.get("open", row.get("close", 0))),
                "high": float(row.get("high", row.get("close", 0))),
                "low": float(row.get("low", row.get("close", 0))),
                "close": float(row["close"]),
                "volume": float(row.get("volumeto", row.get("volumefrom", 0))),
            }
        )
    return out


def _rows_from_coingecko(payload: dict[str, Any]) -> list[dict[str, Any]]:
    prices = payload.get("prices", [])
    out = []
    for ts_ms, price in prices:
        out.append(
            {
                "timestamp": pd.to_datetime(int(ts_ms), unit="ms", utc=True),
                "open": float(price),
                "high": float(price),
                "low": float(price),
                "close": float(price),
                "volume": 0.0,
            }
        )
    return out


def _rows_from_yahoo(payload: dict[str, Any]) -> list[dict[str, Any]]:
    result = payload.get("chart", {}).get("result", [])
    if not result:
        return []
    block = result[0]
    timestamps = block.get("timestamp", [])
    quote = block.get("indicators", {}).get("quote", [{}])[0]
    opens = quote.get("open", [])
    highs = quote.get("high", [])
    lows = quote.get("low", [])
    closes = quote.get("close", [])
    volumes = quote.get("volume", [])
    out = []
    for i, ts in enumerate(timestamps):
        if closes[i] is None:
            continue
        out.append(
            {
                "timestamp": pd.to_datetime(int(ts), unit="s", utc=True),
                "open": float(opens[i] if opens[i] is not None else closes[i]),
                "high": float(highs[i] if highs[i] is not None else closes[i]),
                "low": float(lows[i] if lows[i] is not None else closes[i]),
                "close": float(closes[i]),
                "volume": float(volumes[i] if volumes[i] is not None else 0),
            }
        )
    return out


def parse_stealth_capture(payload: dict[str, Any] | list[Any]) -> pd.DataFrame:
    """Detect capture format and return normalized OHLCV rows."""
    if isinstance(payload, list):
        if payload and isinstance(payload[0], dict) and "time" in payload[0]:
            payload = {"Data": {"Data": payload}}
        else:
            raise ValueError("Unsupported JSON list format.")

    parsers = [
        ("cryptocompare", _rows_from_cryptocompare),
        ("coingecko", _rows_from_coingecko),
        ("yahoo", _rows_from_yahoo),
    ]
    for name, parser in parsers:
        rows = parser(payload)
        if rows:
            frame = pd.DataFrame(rows)
            frame["date"] = frame["timestamp"].dt.tz_convert(None).dt.floor("D")
            ohlcv = (
                frame.groupby("date", as_index=True)
                .agg(
                    open=("open", "first"),
                    high=("high", "max"),
                    low=("low", "min"),
                    close=("close", "last"),
                    volume=("volume", "sum"),
                )
                .astype(float)
            )
            return ohlcv

    raise ValueError(
        "Unrecognized capture format. Expected CryptoCompare histoday, CoinGecko prices, or Yahoo chart JSON."
    )


def load_capture_file(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {path.resolve()}\n"
            f"Save stealth-browser output first, e.g. outputs/data_refresh/ETHUSD_capture.json\n"
            f"Then: python scripts/convert_stealth_capture.py --input <json> --output <csv>"
        )
    with open(path, encoding="utf-8") as fp:
        payload = json.load(fp)
    # Some MCP tools wrap body in { "content": "..." }
    if isinstance(payload, dict) and "body" in payload and isinstance(payload["body"], str):
        payload = json.loads(payload["body"])
    return parse_stealth_capture(payload)


def capture_to_import_csv(ohlcv: pd.DataFrame, output_path: str | Path) -> Path:
    out = ohlcv.reset_index().rename(columns={"date": "timestamp"})
    out["timestamp"] = pd.to_datetime(out["timestamp"]).dt.strftime("%Y-%m-%d 00:00:00")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out[["timestamp", "open", "high", "low", "close", "volume"]].to_csv(output_path, index=False)
    return output_path
