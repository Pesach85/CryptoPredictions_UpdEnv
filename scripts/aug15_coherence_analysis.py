"""Deterministic Aug-15 coherence analysis: PRE/POST 15-day windows vs RF profiles.

Simulation only — not investment advice.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from core.features import build_supervised, build_supervised_focused
from core.io_ohlcv import load_local_close_series
from core.metrics_ts import all_scores, build_naive_prediction
from services.assets import get_asset_profile, resolve_data_path
from services.projection import ProjectionService

ASSETS = ["XBTUSD", "ETHUSD", "SOLUSD", "LTCUSD", "ADAUSD", "BCHUSD"]
ANCHOR = pd.Timestamp("2026-08-15")
PRE_START = ANCHOR - pd.Timedelta(days=14)  # Aug 1 .. Aug 15 inclusive = 15 days
POST_END = ANCHOR + pd.Timedelta(days=14)  # Aug 16 .. Aug 29 available


def _supervised(close: pd.Series, lags: int, features: str):
    if features == "focused":
        return build_supervised_focused(close, lags=lags)
    frame = build_supervised(close, lags=lags)
    cols = [f"lag_{i}" for i in range(1, lags + 1)]
    return frame, cols


def eval_window(sup: pd.DataFrame, cols: list[str], model, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    mask = (sup.index >= start) & (sup.index <= end)
    window = sup.loc[mask]
    if len(window) < 5:
        return {"samples": int(len(window)), "error": "insufficient_samples"}
    y_true = window["target"].values
    y_pred = model.predict(window[cols].values)
    scores = all_scores(y_true, y_pred)
    naive = build_naive_prediction(window)
    naive_scores = all_scores(y_true, naive)
    actual_ret = float(y_true[-1] / y_true[0] - 1.0) * 100.0
    # path implied by successive 1-step preds starting from first actual
    pred_path = np.concatenate([[y_true[0]], y_pred[1:]])
    # better: cumulative direction of predicted day-over-day vs actual
    pred_end_proxy = float(y_pred[-1])
    pred_ret_proxy = float(pred_end_proxy / y_true[0] - 1.0) * 100.0
    return {
        "samples": int(len(window)),
        "start": str(window.index.min().date()),
        "end": str(window.index.max().date()),
        "MAPE": round(scores["MAPE"], 3),
        "dir_acc": round(scores["accuracy_score"], 3),
        "naive_MAPE": round(naive_scores["MAPE"], 3),
        "naive_dir_acc": round(naive_scores["accuracy_score"], 3),
        "dir_edge_pp": round((scores["accuracy_score"] - naive_scores["accuracy_score"]) * 100, 2),
        "actual_window_return_pct": round(actual_ret, 3),
        "pred_last_vs_first_actual_pct": round(pred_ret_proxy, 3),
        "return_gap_pp": round(pred_ret_proxy - actual_ret, 3),
        "first_close": float(y_true[0]),
        "last_actual": float(y_true[-1]),
        "last_pred": float(y_pred[-1]),
    }


def recursive_post(asset: str, profile: dict) -> dict:
    """Train <= Aug 15, project 14 steps, compare to realized Aug 16.."""
    svc = ProjectionService()
    result = svc.project_forward(
        asset_symbol=asset,
        horizon_days=14,
        as_of_date="2026-08-15",
        lags=profile["lags"],
        feature_mode=profile["features"],
        n_estimators=profile["n_estimators"],
        persist=False,
    )
    close = load_local_close_series(resolve_data_path(asset))
    actual = close[(close.index > ANCHOR) & (close.index <= POST_END)]
    pred = result.base_path.copy()
    pred["date"] = pd.to_datetime(pred["date"])
    merged = pred.merge(
        actual.rename("actual_close").reset_index().rename(columns={"date": "date"}),
        on="date",
        how="inner",
    )
    if merged.empty:
        return {"error": "no_overlap"}
    y_true = merged["actual_close"].values
    y_pred = merged["forecast_close"].values
    scores = all_scores(y_true, y_pred)
    # naive persistence from Aug 15 close
    last_obs = float(result.metadata["last_observed_close"])
    naive = np.full_like(y_true, last_obs)
    naive_scores = all_scores(y_true, naive)
    actual_ret = float(y_true[-1] / last_obs - 1.0) * 100.0
    pred_ret = float(y_pred[-1] / last_obs - 1.0) * 100.0
    # directional coherence of multi-day path: sign of end return
    sign_match = int(np.sign(actual_ret) == np.sign(pred_ret)) if actual_ret != 0 else int(pred_ret == 0)
    within_band = int(
        ((merged["actual_close"] >= merged["interval_low"]) & (merged["actual_close"] <= merged["interval_high"])).mean()
        * 100
    )
    return {
        "samples": int(len(merged)),
        "MAPE": round(scores["MAPE"], 3),
        "dir_acc": round(scores["accuracy_score"], 3) if len(y_true) > 1 else None,
        "naive_MAPE": round(naive_scores["MAPE"], 3),
        "actual_return_from_aug15_pct": round(actual_ret, 3),
        "pred_return_from_aug15_pct": round(pred_ret, 3),
        "return_gap_pp": round(pred_ret - actual_ret, 3),
        "end_direction_match": bool(sign_match),
        "pct_days_inside_80pct_band": within_band,
        "last_obs_aug15": last_obs,
        "last_actual": float(y_true[-1]),
        "last_pred": float(y_pred[-1]),
    }


def main():
    rows = []
    for asset in ASSETS:
        profile = get_asset_profile(asset)
        close = load_local_close_series(resolve_data_path(asset))
        # PRE: train strictly before PRE_START, eval PRE_START..ANCHOR with actual lags
        train_pre_end = PRE_START - pd.Timedelta(days=1)
        close_pre_train = close[close.index <= train_pre_end]
        close_through_anchor = close[close.index <= ANCHOR]
        close_full = close[close.index <= POST_END]

        lags, feat, nest = profile["lags"], profile["features"], profile["n_estimators"]
        sup_pre, cols = _supervised(close_through_anchor, lags, feat)
        train_pre = sup_pre[sup_pre.index <= train_pre_end]
        model_pre = RandomForestRegressor(n_estimators=nest, random_state=42, n_jobs=-1)
        model_pre.fit(train_pre[cols].values, train_pre["target"].values)
        pre = eval_window(sup_pre, cols, model_pre, PRE_START, ANCHOR)

        # POST 1-step (oracle lags): train <= ANCHOR, eval ANCHOR+1..POST_END
        sup_post, cols2 = _supervised(close_full, lags, feat)
        train_post = sup_post[sup_post.index <= ANCHOR]
        model_post = RandomForestRegressor(n_estimators=nest, random_state=42, n_jobs=-1)
        model_post.fit(train_post[cols2].values, train_post["target"].values)
        post_1step = eval_window(sup_post, cols2, model_post, ANCHOR + pd.Timedelta(days=1), POST_END)

        post_rec = recursive_post(asset, profile)

        rows.append(
            {
                "asset": asset,
                "profile": {"lags": lags, "features": feat},
                "pre_15d_1step": pre,
                "post_15d_1step_oracle_lags": post_1step,
                "post_14d_recursive": post_rec,
            }
        )

    out_dir = ROOT / "outputs" / "analyses"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "aug15_coherence_2026.json"
    payload = {
        "anchor": "2026-08-15",
        "pre_window": f"{PRE_START.date()} .. {ANCHOR.date()}",
        "post_window": f"{(ANCHOR + pd.Timedelta(days=1)).date()} .. {POST_END.date()}",
        "method": {
            "pre": "RF train < Aug 1; 1-step eval Aug 1-15 with actual lagged features (leakage-safe)",
            "post_1step": "RF train <= Aug 15; 1-step eval Aug 16+ with actual lags (upper bound)",
            "post_recursive": "RF train <= Aug 15; recursive forecast (true forward path used by Projection Lab)",
        },
        "disclaimer": "Simulation only — not investment advice.",
        "results": rows,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
