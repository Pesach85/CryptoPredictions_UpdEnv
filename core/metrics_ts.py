"""Shared time-series scoring for meta/projection pipelines."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, mean_squared_error, precision_score, recall_score


def build_naive_prediction(feature_df: pd.DataFrame) -> np.ndarray:
    if "lag_1" in feature_df.columns:
        return feature_df["lag_1"].values.astype(float)
    return feature_df["lag_close_1"].values.astype(float)


def directional_scores(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    if len(y_true) < 2:
        return {
            "accuracy_score": float("nan"),
            "precision_score": float("nan"),
            "recall_score": float("nan"),
            "f1_score": float("nan"),
        }

    true_diff = np.diff(y_true)
    pred_diff = np.diff(y_pred)
    y_true_dir = true_diff > 0
    y_pred_dir = pred_diff > 0

    return {
        "accuracy_score": float(accuracy_score(y_true_dir, y_pred_dir)),
        "precision_score": float(precision_score(y_true_dir, y_pred_dir, zero_division=0)),
        "recall_score": float(recall_score(y_true_dir, y_pred_dir, zero_division=0)),
        "f1_score": float(f1_score(y_true_dir, y_pred_dir, zero_division=0)),
    }


def regression_scores(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    epsilon = 1e-9
    mape = np.mean(np.abs((y_true - y_pred) / np.maximum(np.abs(y_true), epsilon))) * 100.0
    smape = (
        np.mean(2.0 * np.abs(y_true - y_pred) / np.maximum(np.abs(y_true) + np.abs(y_pred), epsilon)) * 100.0
    )
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "MAPE": float(mape),
        "SMAPE": float(smape),
    }


def all_scores(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    scores = {}
    scores.update(regression_scores(y_true, y_pred))
    scores.update(directional_scores(y_true, y_pred))
    return scores
