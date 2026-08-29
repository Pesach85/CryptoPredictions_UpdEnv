"""Shared trading signal helpers (simulation only)."""

from __future__ import annotations

import pandas as pd


def compute_signal1(df: pd.DataFrame, predicted_col: str = "predicted_mean", close_col: str = "Close") -> pd.Series:
    """Buy(2)/sell(1)/hold(0) when predicted mean exceeds previous close."""
    position = False
    signal = [0] * len(df)
    closes = df[close_col].values
    preds = df[predicted_col].values
    for i in range(1, len(signal)):
        if preds[i] > closes[i - 1]:
            if not position:
                signal[i] = 2
                position = True
        elif position:
            signal[i] = 1
            position = False
    return pd.Series(signal, index=df.index, name="signal1")
