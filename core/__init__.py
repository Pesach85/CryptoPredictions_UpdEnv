"""Shared core for meta-historical and projection pipelines."""

from core.features import (
    build_supervised,
    build_supervised_enhanced,
    build_supervised_focused,
    build_supervised_from_source,
    compute_ta_features,
    feature_row_from_close_tail,
)
from core.io_ohlcv import load_local_close_series, load_local_ohlcv
from core.market_ids import parse_assets, sanitize_symbol, symbol_base
from core.metrics_ts import all_scores, build_naive_prediction, directional_scores, regression_scores
from core.signals import compute_signal1

__all__ = [
    "load_local_ohlcv",
    "load_local_close_series",
    "compute_ta_features",
    "build_supervised",
    "build_supervised_enhanced",
    "build_supervised_focused",
    "build_supervised_from_source",
    "feature_row_from_close_tail",
    "all_scores",
    "build_naive_prediction",
    "directional_scores",
    "regression_scores",
    "compute_signal1",
    "sanitize_symbol",
    "parse_assets",
    "symbol_base",
]
