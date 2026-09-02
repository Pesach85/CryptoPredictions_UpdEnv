"""Volatility event forecasting — probability and timing of ±N% moves.

Uses OHLCV-only regime features (compression, impulse, volume, analog matching).
Simulation only — not investment advice. Not a trading signal service.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

import numpy as np
import pandas as pd

from core.io_ohlcv import load_local_ohlcv
from services.assets import resolve_data_path


@dataclass
class VolatilityEventForecast:
    asset_symbol: str
    as_of_date: str
    threshold_pct: float
    current_price: float
    probability_7d: float
    probability_14d: float
    probability_21d: float
    expected_magnitude_pct: float
    direction_bias: Literal["up", "down", "neutral"]
    direction_up_prob: float
    most_probable_window: str
    window_start_estimate: str
    window_end_estimate: str
    scenario_up_pct: float
    scenario_down_pct: float
    confidence: Literal["low", "medium", "high"]
    regime_label: str
    factors: dict[str, Any]
    analog_count: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_symbol": self.asset_symbol,
            "as_of_date": self.as_of_date,
            "threshold_pct": self.threshold_pct,
            "current_price": round(self.current_price, 4),
            "probabilities": {
                "7d_pct": round(self.probability_7d * 100, 1),
                "14d_pct": round(self.probability_14d * 100, 1),
                "21d_pct": round(self.probability_21d * 100, 1),
            },
            "expected_move_pct": round(self.expected_magnitude_pct, 1),
            "direction_bias": self.direction_bias,
            "direction_up_prob_pct": round(self.direction_up_prob * 100, 1),
            "most_probable_window": self.most_probable_window,
            "window_start_estimate": self.window_start_estimate,
            "window_end_estimate": self.window_end_estimate,
            "scenarios": {
                "upside_pct": round(self.scenario_up_pct, 1),
                "downside_pct": round(self.scenario_down_pct, 1),
            },
            "confidence": self.confidence,
            "regime_label": self.regime_label,
            "factors": self.factors,
            "analog_count": self.analog_count,
            "metadata": self.metadata,
            "disclaimer": "Simulation only — not investment advice.",
        }


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _atr_pct(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean() / df["close"] * 100.0


def _bb_width_pct(close: pd.Series, period: int = 20) -> pd.Series:
    ma = close.rolling(period).mean()
    std = close.rolling(period).std()
    return (2 * std / ma) * 100.0


def _detect_events(df: pd.DataFrame, threshold_pct: float) -> pd.Series:
    """Major move: |1d| >= threshold OR |3d cumulative| >= threshold * 1.2."""
    ret1 = df["close"].pct_change()
    ret3 = df["close"].pct_change(3)
    thr = threshold_pct / 100.0
    thr3 = thr * 1.2
    return (ret1.abs() >= thr) | (ret3.abs() >= thr3)


def _build_features(df: pd.DataFrame, threshold_pct: float) -> pd.DataFrame:
    out = df.copy()
    out["ret1"] = out["close"].pct_change()
    out["ret5"] = out["close"].pct_change(5)
    out["ret14"] = out["close"].pct_change(14)
    out["atr_pct"] = _atr_pct(out, 14)
    out["atr_ratio"] = out["atr_pct"] / out["atr_pct"].rolling(60).median()
    out["bb_width"] = _bb_width_pct(out["close"], 20)
    out["bb_pctile"] = out["bb_width"].rolling(120, min_periods=30).apply(
        lambda x: float(pd.Series(x).rank(pct=True).iloc[-1]), raw=False
    )
    out["realized_vol_14"] = out["ret1"].rolling(14).std() * np.sqrt(365) * 100
    out["vol_ratio"] = out["realized_vol_14"] / out["realized_vol_14"].rolling(90).median()
    out["rsi14"] = _rsi(out["close"], 14)
    out["ma20"] = out["close"].rolling(20).mean()
    out["dist_ma20_pct"] = (out["close"] / out["ma20"] - 1.0) * 100
    out["vol_z"] = (
        (out["volume"] - out["volume"].rolling(20).mean())
        / out["volume"].rolling(20).std().replace(0, np.nan)
    )
    out["range_pct"] = (out["high"] - out["low"]) / out["close"].shift(1) * 100
    out["compression"] = 1.0 - out["bb_pctile"].clip(0, 1)
    out["event"] = _detect_events(out, threshold_pct)

    # Days since last event
    event_idx = out.index[out["event"].fillna(False)]
    days_since = []
    last_ev = None
    for dt in out.index:
        past = event_idx[event_idx < dt]
        if len(past) == 0:
            days_since.append(np.nan)
        else:
            days_since.append((dt - past[-1]).days)
    out["days_since_event"] = days_since
    return out


def _forward_event_within(
    feats: pd.DataFrame, start_idx: int, horizon: int, threshold_pct: float
) -> tuple[bool, float, int | None]:
    """Return (hit, max_abs_move_pct, days_to_hit)."""
    if start_idx + 1 >= len(feats):
        return False, 0.0, None
    end = min(start_idx + horizon, len(feats) - 1)
    window = feats.iloc[start_idx + 1 : end + 1]
    if window.empty:
        return False, 0.0, None
    max_move = 0.0
    days_to_hit = None
    for i, (_, row) in enumerate(window.iterrows()):
        m1 = abs(float(row["ret1"])) * 100 if pd.notna(row["ret1"]) else 0.0
        ret3 = row.get("ret3")
        m3 = abs(float(ret3)) * 100 if pd.notna(ret3) else 0.0
        move = max(m1, m3)
        max_move = max(max_move, move)
        if move >= threshold_pct and days_to_hit is None:
            days_to_hit = i + 1
    hit = days_to_hit is not None or bool(window["event"].fillna(False).any())
    if hit and days_to_hit is None:
        first_ev = window[window["event"].fillna(False)].index[0]
        days_to_hit = (first_ev - feats.index[start_idx]).days
    return hit, max_move, days_to_hit


class VolatilityEventService:
    """Forecast timing and magnitude of the next ±threshold% volatility event."""

    MIN_HISTORY = 180
    ANALOG_TOP_K = 40

    def forecast(
        self,
        asset_symbol: str,
        threshold_pct: float = 10.0,
        as_of_date: str | None = None,
    ) -> VolatilityEventForecast:
        df = load_local_ohlcv(resolve_data_path(asset_symbol))
        if len(df) < self.MIN_HISTORY:
            raise ValueError(f"Need at least {self.MIN_HISTORY} daily bars for {asset_symbol}.")

        feats = _build_features(df, threshold_pct)
        feats["ret3"] = feats["close"].pct_change(3)

        if as_of_date:
            cutoff = pd.Timestamp(as_of_date)
            feats = feats.loc[:cutoff]
        if feats.empty:
            raise ValueError("No data on or before as_of_date.")

        as_of = feats.index[-1]
        row = feats.iloc[-1]
        current_price = float(row["close"])

        # --- analog matching on normalized feature vector ---
        feature_cols = [
            "atr_ratio",
            "bb_pctile",
            "vol_ratio",
            "rsi14",
            "dist_ma20_pct",
            "compression",
            "days_since_event",
            "ret14",
        ]
        hist = feats.iloc[60:-1].dropna(subset=feature_cols)
        if len(hist) < 50:
            raise ValueError("Insufficient feature history for analog matching.")

        target = row[feature_cols].astype(float)
        # z-score normalize using hist
        mu = hist[feature_cols].mean()
        sigma = hist[feature_cols].std().replace(0, 1)
        dists = ((hist[feature_cols] - mu) / sigma - (target - mu) / sigma).pow(2).sum(axis=1).pow(0.5)
        analog_idx = dists.nsmallest(min(self.ANALOG_TOP_K, len(dists))).index

        # Forward outcomes from analogs
        horizons = [7, 14, 21]
        hits = {h: [] for h in horizons}
        moves = []
        up_count = 0
        down_count = 0
        days_to_hit: list[int] = []

        for dt in analog_idx:
            loc = feats.index.get_loc(dt)
            for h in horizons:
                hit, move, dth = _forward_event_within(feats, loc, h, threshold_pct)
                hits[h].append(hit)
            # 21d forward direction of max move
            if loc + 21 < len(feats):
                fwd = feats.iloc[loc + 1 : loc + 22]
                max_up = float(fwd["ret1"].max() * 100)
                max_dn = float(fwd["ret1"].min() * 100)
                if abs(max_up) >= abs(max_dn):
                    if abs(max_up) >= threshold_pct * 0.5:
                        up_count += 1
                else:
                    if abs(max_dn) >= threshold_pct * 0.5:
                        down_count += 1
                moves.append(max(abs(max_up), abs(max_dn)))
                hit21, _, dth = _forward_event_within(feats, loc, 21, threshold_pct)
                if hit21 and dth is not None:
                    days_to_hit.append(dth)

        prob7 = float(np.mean(hits[7])) if hits[7] else 0.0
        prob14 = float(np.mean(hits[14])) if hits[14] else 0.0
        prob21 = float(np.mean(hits[21])) if hits[21] else 0.0

        # --- regime scoring (deterministic analyst factors) ---
        factors: dict[str, Any] = {
            "atr_ratio": round(float(row["atr_ratio"]), 3) if pd.notna(row["atr_ratio"]) else None,
            "bb_width_pctile": round(float(row["bb_pctile"]), 3) if pd.notna(row["bb_pctile"]) else None,
            "realized_vol_ratio": round(float(row["vol_ratio"]), 3) if pd.notna(row["vol_ratio"]) else None,
            "rsi14": round(float(row["rsi14"]), 1) if pd.notna(row["rsi14"]) else None,
            "dist_ma20_pct": round(float(row["dist_ma20_pct"]), 2) if pd.notna(row["dist_ma20_pct"]) else None,
            "ret14_pct": round(float(row["ret14"]) * 100, 2) if pd.notna(row["ret14"]) else None,
            "days_since_last_event": int(row["days_since_event"]) if pd.notna(row["days_since_event"]) else None,
            "compression_score": round(float(row["compression"]), 3) if pd.notna(row["compression"]) else None,
        }

        score = 0.0
        reasons: list[str] = []

        # Compression → expansion (coiled spring)
        if pd.notna(row["bb_pctile"]) and row["bb_pctile"] < 0.25:
            score += 0.15
            reasons.append("Bollinger compression (low bandwidth percentile)")
        if pd.notna(row["atr_ratio"]) and row["atr_ratio"] < 0.85:
            score += 0.12
            reasons.append("ATR below 60d median — volatility contraction")

        # Post-impulse consolidation after Aug-style rally
        if pd.notna(row["ret14"]) and abs(row["ret14"]) >= 0.15:
            score += 0.18
            reasons.append("Strong 14d impulse (+/-15%) — elevated follow-through risk")
        if pd.notna(row["days_since_event"]) and row["days_since_event"] <= 14:
            score += 0.14
            reasons.append("Recent major event within 14d — cluster volatility regime")

        # Extended from MA → mean reversion risk
        if pd.notna(row["dist_ma20_pct"]) and abs(row["dist_ma20_pct"]) > 8:
            score += 0.10
            reasons.append("Price extended vs 20d MA")

        # Volume drying up in consolidation
        if pd.notna(row["vol_z"]) and row["vol_z"] < -0.5:
            score += 0.08
            reasons.append("Volume below average — pre-breakout pattern")

        # Long quiet period
        if pd.notna(row["days_since_event"]) and row["days_since_event"] > 30:
            score += 0.10
            reasons.append("Extended calm (>30d since last ±threshold event)")

        regime_score = min(score, 0.65)
        prob14_adj = min(0.92, prob14 * 0.55 + regime_score + 0.15)
        prob7_adj = min(0.85, prob7 * 0.5 + regime_score * 0.7)
        prob21_adj = min(0.95, prob21 * 0.5 + regime_score + 0.2)

        # Direction: mean reversion after extension vs momentum continuation
        dir_up = 0.5
        if pd.notna(row["dist_ma20_pct"]):
            if row["dist_ma20_pct"] > 10:
                dir_up = 0.35  # overextended → correction bias
            elif row["dist_ma20_pct"] < -8:
                dir_up = 0.65
        if pd.notna(row["ret14"]) and row["ret14"] > 0.12:
            dir_up = dir_up * 0.7 + 0.15  # recent rally → slight continuation then fade
        if up_count + down_count > 0:
            analog_up = up_count / (up_count + down_count)
            dir_up = dir_up * 0.5 + analog_up * 0.5

        if dir_up >= 0.55:
            direction: Literal["up", "down", "neutral"] = "up"
        elif dir_up <= 0.45:
            direction = "down"
        else:
            direction = "neutral"

        expected_mag = float(np.median(moves)) if moves else threshold_pct
        expected_mag = max(threshold_pct, min(expected_mag * 1.1, threshold_pct * 2.5))

        # Timing window from analog days-to-hit distribution
        if days_to_hit:
            med_days = int(np.median(days_to_hit))
            p25 = int(np.percentile(days_to_hit, 25))
            p75 = int(np.percentile(days_to_hit, 75))
        else:
            med_days = 10
            p25, p75 = 5, 18

        win_start = (as_of + pd.Timedelta(days=max(1, p25))).strftime("%Y-%m-%d")
        win_end = (as_of + pd.Timedelta(days=p75)).strftime("%Y-%m-%d")
        window_label = f"Day {p25}-{p75} from {as_of.date()} (~{win_start} to {win_end})"

        # Regime label
        if pd.notna(row["ret14"]) and row["ret14"] > 0.15 and pd.notna(row["days_since_event"]) and row["days_since_event"] <= 14:
            regime = "post_impulse_consolidation"
        elif pd.notna(row["compression"]) and row["compression"] > 0.7:
            regime = "volatility_compression"
        elif pd.notna(row["vol_ratio"]) and row["vol_ratio"] > 1.3:
            regime = "elevated_volatility"
        else:
            regime = "neutral_range"

        confidence: Literal["low", "medium", "high"]
        if len(analog_idx) >= 30 and prob14_adj >= 0.45:
            confidence = "high" if prob14_adj >= 0.6 else "medium"
        else:
            confidence = "low"

        # Aug 19 context note in metadata
        aug19 = pd.Timestamp("2026-08-19")
        post_rally_note = None
        if as_of >= aug19:
            seg = feats.loc[aug19:as_of]
            if len(seg) >= 2:
                cum = float(seg["close"].iloc[-1] / seg["close"].iloc[0] - 1) * 100
                post_rally_note = (
                    f"Since 2026-08-19: cumulative {cum:+.1f}%; "
                    f"last major daily move {factors.get('days_since_last_event')}d ago."
                )

        return VolatilityEventForecast(
            asset_symbol=asset_symbol,
            as_of_date=str(as_of.date()),
            threshold_pct=threshold_pct,
            current_price=current_price,
            probability_7d=prob7_adj,
            probability_14d=prob14_adj,
            probability_21d=prob21_adj,
            expected_magnitude_pct=expected_mag,
            direction_bias=direction,
            direction_up_prob=dir_up,
            most_probable_window=window_label,
            window_start_estimate=win_start,
            window_end_estimate=win_end,
            scenario_up_pct=expected_mag if direction != "down" else expected_mag * 0.7,
            scenario_down_pct=expected_mag if direction != "up" else expected_mag * 0.7,
            confidence=confidence,
            regime_label=regime,
            factors=factors,
            analog_count=len(analog_idx),
            metadata={
                "regime_reasons": reasons,
                "median_days_to_event_analogs": med_days,
                "post_rally_context": post_rally_note,
                "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            },
        )
