"""Golden unit tests for core I/O and features."""

from pathlib import Path

import numpy as np
import pandas as pd

from core.features import build_supervised, build_supervised_focused, feature_row_from_close_tail
from core.io_ohlcv import load_local_ohlcv, load_local_close_series
from core.metrics_ts import all_scores
from core.signals import compute_signal1
from services.projection import ProjectionService


ROOT = Path(__file__).resolve().parents[1]
ETH = ROOT / "data" / "ETHUSD-1d-data.csv"


def test_load_local_ohlcv_schema():
    df = load_local_ohlcv(ETH)
    assert list(df.columns) == ["close", "volume", "high", "low", "open"]
    assert df.index.name == "date" or isinstance(df.index, pd.DatetimeIndex)
    assert len(df) > 100
    assert df["close"].isna().sum() == 0


def test_build_supervised_close_and_focused():
    close = load_local_close_series(ETH).tail(200)
    sup = build_supervised(close, lags=14)
    assert "lag_1" in sup.columns
    assert len(sup) > 50
    focused, cols = build_supervised_focused(close, lags=14)
    assert "lag_close_1" in cols
    assert "lag_rsi_14_1" in cols
    assert len(focused) > 40


def test_feature_row_from_close_tail_matches_supervised():
    closes = [float(x) for x in range(1, 40)]
    row = feature_row_from_close_tail(closes, lags=5)
    # last close is 39 (target); lag_1=38 ... lag_5=34
    assert row == [38.0, 37.0, 36.0, 35.0, 34.0]


def test_all_scores_perfect_direction():
    y = np.array([1.0, 2.0, 3.0, 4.0])
    scores = all_scores(y, y)
    assert scores["MAPE"] == 0.0
    assert scores["accuracy_score"] == 1.0


def test_compute_signal1():
    df = pd.DataFrame(
        {
            "Close": [100.0, 101.0, 99.0, 98.0],
            "predicted_mean": [100.0, 102.0, 98.0, 97.0],
        }
    )
    sig = compute_signal1(df)
    assert list(sig.values) == [0, 2, 1, 0]


def test_projection_smoke_eth():
    result = ProjectionService().project_forward(
        "ETHUSD", horizon_days=7, as_of_date="2026-08-15", persist=False
    )
    assert len(result.base_path) == 7
    assert "regime_shift_caution" in result.metadata


def test_multi_model_paths_fast_eth():
    from services.multi_model_paths import FAST_MODELS, MultiModelPathService

    result = MultiModelPathService().run(
        "ETHUSD",
        window_start="2026-08-01",
        window_end="2026-08-10",
        models=FAST_MODELS,
        persist=False,
        n_estimators_override=50,
    )
    assert "actual" in result.frame.columns
    assert "rf_1step" in result.frame.columns
    assert "naive" in result.metrics
    assert result.cutoff == "2026-07-31"
    assert len(result.frame) >= 5
