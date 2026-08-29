"""Shared feature builders for meta/projection pipelines."""

from __future__ import annotations

import pandas as pd


def compute_ta_features(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """Compute RSI-14, MACD line, ATR-14 from OHLCV DataFrame."""
    df = ohlcv.copy()

    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(span=14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(span=14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-9)
    df["rsi_14"] = 100 - (100 / (1 + rs))

    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26

    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift(1)).abs()
    low_close = (df["low"] - df["close"].shift(1)).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr_14"] = true_range.rolling(14, min_periods=14).mean()
    df["returns"] = df["close"].pct_change()
    return df


def build_supervised(close_series: pd.Series, lags: int = 30) -> pd.DataFrame:
    df = pd.DataFrame({"close": close_series.sort_index()})
    for lag in range(1, lags + 1):
        df[f"lag_{lag}"] = df["close"].shift(lag)
    df = df.dropna().copy()
    df["target"] = df["close"]
    return df


def build_supervised_enhanced(ohlcv: pd.DataFrame, lags: int = 30) -> tuple[pd.DataFrame, list[str]]:
    df = compute_ta_features(ohlcv)
    df = df.dropna().copy()

    feature_cols: list[str] = []
    for lag in range(1, lags + 1):
        col = f"lag_close_{lag}"
        df[col] = df["close"].shift(lag)
        feature_cols.append(col)

    vol_mean = df["volume"].rolling(30, min_periods=1).mean().replace(0, 1)
    df["vol_norm"] = df["volume"] / vol_mean
    for lag in range(1, min(lags, 14) + 1):
        col = f"lag_vol_{lag}"
        df[col] = df["vol_norm"].shift(lag)
        feature_cols.append(col)

    for lag in range(1, min(lags, 14) + 1):
        col = f"lag_ret_{lag}"
        df[col] = df["returns"].shift(lag)
        feature_cols.append(col)

    for indicator in ["rsi_14", "macd", "atr_14"]:
        for lag in range(1, min(lags, 7) + 1):
            col = f"lag_{indicator}_{lag}"
            df[col] = df[indicator].shift(lag)
            feature_cols.append(col)

    df["target"] = df["close"]
    df = df.dropna().copy()
    return df, feature_cols


def build_supervised_focused(close_series: pd.Series, lags: int = 30) -> tuple[pd.DataFrame, list[str]]:
    """Focused feature set: close lags + RSI-14 + MACD + returns."""
    df = pd.DataFrame({"close": close_series.sort_index()})

    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(span=14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(span=14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-9)
    df["rsi_14"] = 100 - (100 / (1 + rs))

    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["returns"] = df["close"].pct_change()
    df = df.dropna().copy()

    feature_cols: list[str] = []
    for lag in range(1, lags + 1):
        col = f"lag_close_{lag}"
        df[col] = df["close"].shift(lag)
        feature_cols.append(col)

    for lag in range(1, min(lags, 7) + 1):
        col = f"lag_ret_{lag}"
        df[col] = df["returns"].shift(lag)
        feature_cols.append(col)

    for indicator in ["rsi_14", "macd"]:
        for lag in range(1, min(lags, 5) + 1):
            col = f"lag_{indicator}_{lag}"
            df[col] = df[indicator].shift(lag)
            feature_cols.append(col)

    df["target"] = df["close"]
    df = df.dropna().copy()
    return df, feature_cols


def feature_row_from_close_tail(closes: list[float], lags: int) -> list[float]:
    """O(lags) feature vector for close-only mode from newest-last close list."""
    if len(closes) < lags + 1:
        raise ValueError(f"Need at least {lags + 1} closes, got {len(closes)}")
    # target is last close; lags are previous closes
    return [closes[-(lag + 1)] for lag in range(1, lags + 1)]


def build_supervised_from_source(
    source: pd.Series | pd.DataFrame,
    lags: int,
    feature_mode: str,
    tail_rows: int | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Build supervised frame; optionally restrict to tail for faster recursive steps."""
    if tail_rows is not None and tail_rows > 0:
        source = source.tail(tail_rows)

    if feature_mode == "enhanced":
        if not isinstance(source, pd.DataFrame):
            raise ValueError("Enhanced feature mode requires OHLCV DataFrame.")
        return build_supervised_enhanced(source, lags=lags)

    close = source if isinstance(source, pd.Series) else source["close"]
    if feature_mode == "focused":
        return build_supervised_focused(close, lags=lags)

    supervised = build_supervised(close, lags=lags)
    feature_cols = [f"lag_{i}" for i in range(1, lags + 1)]
    return supervised, feature_cols
