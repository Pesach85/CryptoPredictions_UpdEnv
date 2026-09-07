"""Lightweight market fetch helpers (no matplotlib / sklearn)."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import requests

from core.market_ids import COINGECKO_SYMBOL_TO_ID


_ID_TO_SYMBOL = {v: k for k, v in COINGECKO_SYMBOL_TO_ID.items()}
# Prefer BTC over XBT for exchange tickers.
_ID_TO_SYMBOL["bitcoin"] = "BTC"


def coin_id_to_symbol(coin_id: str) -> str:
    result = _ID_TO_SYMBOL.get(coin_id)
    if result is None:
        raise ValueError(f"Unknown coin_id: {coin_id}. Add it to COINGECKO_SYMBOL_TO_ID.")
    return result


def fetch_api_daily_close(coin_id: str, start_dt: datetime, end_dt: datetime) -> pd.Series:
    """Fetch daily close series: CoinGecko → Yahoo → CryptoCompare."""
    from_ts = int(start_dt.replace(tzinfo=timezone.utc).timestamp())
    to_ts = int(end_dt.replace(tzinfo=timezone.utc).timestamp())

    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart/range"
        response = requests.get(
            url,
            params={"vs_currency": "usd", "from": from_ts, "to": to_ts},
            timeout=45,
        )
        response.raise_for_status()
        payload = response.json()

        prices = payload.get("prices", [])
        if prices:
            frame = pd.DataFrame(prices, columns=["ts_ms", "price"])
            frame["date"] = (
                pd.to_datetime(frame["ts_ms"], unit="ms", utc=True).dt.tz_convert(None).dt.floor("D")
            )
            return (
                frame.sort_values("date")
                .groupby("date", as_index=True)["price"]
                .last()
                .astype(float)
            )
    except Exception:
        pass

    symbol = coin_id_to_symbol(coin_id)

    try:
        yahoo_symbol = f"{symbol}-USD"
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}"
        response = requests.get(
            url,
            params={"period1": from_ts, "period2": to_ts, "interval": "1d"},
            timeout=45,
        )
        response.raise_for_status()
        payload = response.json()

        result = payload.get("chart", {}).get("result", [])
        if result:
            timestamps = result[0].get("timestamp", [])
            closes = result[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
            frame = pd.DataFrame({"ts": timestamps, "close": closes}).dropna().copy()
            if not frame.empty:
                frame["date"] = (
                    pd.to_datetime(frame["ts"], unit="s", utc=True).dt.tz_convert(None).dt.floor("D")
                )
                return frame.set_index("date")["close"].astype(float)
    except Exception:
        pass

    url = "https://min-api.cryptocompare.com/data/v2/histoday"
    response = requests.get(
        url,
        params={"fsym": symbol, "tsym": "USD", "limit": 2000, "toTs": to_ts},
        timeout=45,
    )
    response.raise_for_status()
    payload = response.json()

    rows = payload.get("Data", {}).get("Data", [])
    frame = pd.DataFrame(rows)
    if frame.empty or "time" not in frame.columns or "close" not in frame.columns:
        raise ValueError("CryptoCompare returned no usable daily series.")

    frame["date"] = pd.to_datetime(frame["time"], unit="s", utc=True).dt.tz_convert(None).dt.floor("D")
    frame = frame[(frame["time"] >= from_ts) & (frame["time"] <= to_ts)]
    frame = frame.dropna(subset=["close"])
    if frame.empty:
        raise ValueError("CryptoCompare returned empty close series for selected date range.")

    return frame.set_index("date")["close"].astype(float)
