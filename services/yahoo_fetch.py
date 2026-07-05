"""Yahoo Finance OHLCV fetcher — reliable fallback when CryptoCompare/CoinGecko rate-limit."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import requests

from meta_historical_test import sanitize_symbol

YAHOO_TICKERS: dict[str, str] = {
    "XBTUSD": "BTC-USD",
    "ETHUSD": "ETH-USD",
    "SOLUSD": "SOL-USD",
    "BNBUSD": "BNB-USD",
    "ADAUSD": "ADA-USD",
    "DOGEUSD": "DOGE-USD",
    "DOTUSD": "DOT-USD",
    "LTCUSD": "LTC-USD",
    "TRXUSD": "TRX-USD",
    "AVAXUSD": "AVAX-USD",
    "LINKUSD": "LINK-USD",
    "NEARUSD": "NEAR-USD",
    "APEUSD": "APE-USD",
    "CROUSD": "CRO-USD",
    "AXSUSD": "AXS-USD",
    "EOSUSD": "EOS-USD",
    "BCHUSD": "BCH-USD",
    "PEPEUSDT": "PEPE-USD",
    "APTUSD": "APT-USD",
}

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


def asset_to_yahoo_ticker(asset_symbol: str) -> str:
    symbol = sanitize_symbol(asset_symbol)
    if symbol in YAHOO_TICKERS:
        return YAHOO_TICKERS[symbol]
    base = symbol
    if base.endswith("USDT"):
        base = base[:-4]
    elif base.endswith("USD"):
        base = base[:-3]
    return f"{base}-USD"


def fetch_yahoo_daily_ohlcv(ticker: str, start_dt: datetime, end_dt: datetime) -> pd.DataFrame:
    from_ts = int(start_dt.replace(tzinfo=timezone.utc).timestamp())
    to_ts = int(end_dt.replace(tzinfo=timezone.utc).timestamp())

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    response = requests.get(
        url,
        params={"period1": from_ts, "period2": to_ts, "interval": "1d"},
        headers=DEFAULT_HEADERS,
        timeout=45,
    )
    response.raise_for_status()
    payload = response.json()

    result = payload.get("chart", {}).get("result", [])
    if not result:
        raise ValueError(f"Yahoo returned no chart data for {ticker}")

    block = result[0]
    timestamps = block.get("timestamp", [])
    quote = block.get("indicators", {}).get("quote", [{}])[0]
    if not timestamps:
        raise ValueError(f"Yahoo returned empty timestamps for {ticker}")

    frame = pd.DataFrame(
        {
            "ts": timestamps,
            "open": quote.get("open", []),
            "high": quote.get("high", []),
            "low": quote.get("low", []),
            "close": quote.get("close", []),
            "volume": quote.get("volume", []),
        }
    ).dropna(subset=["close"])

    if frame.empty:
        raise ValueError(f"Yahoo returned no usable OHLCV rows for {ticker}")

    frame["date"] = pd.to_datetime(frame["ts"], unit="s", utc=True).dt.tz_convert(None).dt.floor("D")
    ohlcv = frame.set_index("date")[["open", "high", "low", "close", "volume"]].astype(float)
    return ohlcv[(ohlcv.index >= pd.Timestamp(start_dt.date())) & (ohlcv.index <= pd.Timestamp(end_dt.date()))]
