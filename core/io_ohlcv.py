"""Shared I/O for local OHLCV CSVs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_local_ohlcv(csv_path: Path) -> pd.DataFrame:
    """Load OHLCV daily data from local CSV, normalized to date index."""
    df = pd.read_csv(csv_path)

    original_columns = list(df.columns)
    normalized_columns = [str(col).strip().lower() for col in original_columns]
    col_map = dict(zip(normalized_columns, original_columns))

    timestamp_col = None
    for candidate in ["timestamp", "date", "datetime", "time"]:
        if candidate in col_map:
            timestamp_col = col_map[candidate]
            break

    close_col = col_map.get("close")
    if timestamp_col is None or close_col is None:
        raise ValueError(
            f"CSV must include a datetime column (timestamp/date/datetime/time) and close column. Found columns: {original_columns}"
        )

    df["_timestamp"] = pd.to_datetime(df[timestamp_col], utc=True, errors="coerce")
    df["_close"] = pd.to_numeric(df[close_col], errors="coerce")
    df = df.dropna(subset=["_timestamp", "_close"]).copy()
    df["date"] = df["_timestamp"].dt.tz_convert(None).dt.floor("D")

    vol_col = col_map.get("volume")
    high_col = col_map.get("high")
    low_col = col_map.get("low")
    open_col = col_map.get("open")

    result = (
        df.sort_values("date")
        .groupby("date", as_index=True)
        .agg(
            close=("_close", "last"),
            volume=(vol_col, "sum") if vol_col else ("_close", lambda x: 0.0),
            high=(high_col, "max") if high_col else ("_close", "max"),
            low=(low_col, "min") if low_col else ("_close", "min"),
            open=(open_col, "first") if open_col else ("_close", "first"),
        )
        .astype(float)
    )
    return result


def load_local_close_series(csv_path: Path) -> pd.Series:
    return load_local_ohlcv(csv_path)["close"]
