"""Plain-language + pattern-card mapping for volatility radar UX.

Turns regime/factors/probabilities into Italian educational copy, factor
heat intensities, and scenario bars. Simulation only — not investment advice.
Not tick-level order flow; OHLCV parameter heatmaps only.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

DISCLAIMER = "Simulation only — not investment advice. Uso educativo / gamificato."

# Factor display order for heatmap grids
FACTOR_ORDER = (
    "atr_ratio",
    "compression_score",
    "realized_vol_ratio",
    "bb_width_pctile",
    "rsi14",
    "dist_ma20_pct",
    "ret14_pct",
    "days_since_last_event",
)

FACTOR_LABELS_IT: dict[str, str] = {
    "atr_ratio": "ATR vs mediana",
    "compression_score": "Compressione",
    "realized_vol_ratio": "Vol realizzata",
    "bb_width_pctile": "Bande Bollinger",
    "rsi14": "RSI 14",
    "dist_ma20_pct": "Distanza MA20",
    "ret14_pct": "Rendimento 14g",
    "days_since_last_event": "Giorni da evento",
}


@dataclass
class FactorHeatCell:
    key: str
    label_it: str
    value: float | None
    intensity: float  # 0..1 colour scale
    chip_it: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PatternCard:
    pattern_id: str
    title_it: str
    arrow: str  # up | down | side | breakout
    primary_it: str
    secondary_it: str
    projection_it: str
    gamified_hint_it: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VolatilityUxView:
    hero_title_it: str
    hero_body_it: str
    pattern: PatternCard
    factor_cells: list[FactorHeatCell]
    horizon_probs_pct: dict[str, float]
    scenario_probs_pct: dict[str, float]
    direction_bias: str
    direction_bias_it: str
    confidence_it: str
    window_summary_it: str
    disclaimer: str = DISCLAIMER
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hero_title_it": self.hero_title_it,
            "hero_body_it": self.hero_body_it,
            "pattern": self.pattern.to_dict(),
            "factor_cells": [c.to_dict() for c in self.factor_cells],
            "horizon_probs_pct": self.horizon_probs_pct,
            "scenario_probs_pct": self.scenario_probs_pct,
            "direction_bias": self.direction_bias,
            "direction_bias_it": self.direction_bias_it,
            "confidence_it": self.confidence_it,
            "window_summary_it": self.window_summary_it,
            "disclaimer": self.disclaimer,
            "extras": self.extras,
        }


_REGIME_PATTERNS: dict[str, PatternCard] = {
    "volatility_compression": PatternCard(
        pattern_id="compression_breakout",
        title_it="Compressione · possibile breakout",
        arrow="breakout",
        primary_it="Il mercato sembra “compresso”: range stretti, energia in accumulo.",
        secondary_it="Storicamente, dopo compressioni simili, spesso arriva un movimento più ampio.",
        projection_it="Scenario educativo: allargamento del range entro 1–3 settimane (direzione da bias).",
        gamified_hint_it="Carta cheat-sheet: molla compressa — non è un segnale di trade.",
    ),
    "post_impulse_consolidation": PatternCard(
        pattern_id="post_impulse",
        title_it="Consolidamento post-impulso",
        arrow="side",
        primary_it="Dopo un rally/shock recente, il prezzo digests lo sbalzo.",
        secondary_it="Possibile prosecuzione o correzione: gli analoghi storici pesano entrambe le vie.",
        projection_it="Scenario educativo: consolidamento, poi un nuovo impulso (su o giù).",
        gamified_hint_it="Carta: pausa dopo lo sprint — come in un pattern di continuazione semplificato.",
    ),
    "elevated_volatility": PatternCard(
        pattern_id="elevated_vol",
        title_it="Volatilità alta",
        arrow="side",
        primary_it="Oscillazioni più ampie del solito: il “terreno” è mosso.",
        secondary_it="Eventi ±soglia restano plausibili su più finestre temporali.",
        projection_it="Scenario educativo: swing ampi; probabilità evento elevate su 14–21 giorni.",
        gamified_hint_it="Carta: mare mosso — osserva le barre di probabilità, non inseguire il prezzo.",
    ),
    "neutral_range": PatternCard(
        pattern_id="neutral_range",
        title_it="Range neutro / laterale",
        arrow="side",
        primary_it="Nessun regime estremo dominante: il prezzo si muove in una fascia ordinaria.",
        secondary_it="Le probabilità evento dipendono soprattutto dagli analoghi storici.",
        projection_it="Scenario educativo: movimento laterale con chance moderate di breakout soft.",
        gamified_hint_it="Carta: pianura — utile per imparare a leggere fattori e heatmap.",
    ),
}


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def factor_intensity(key: str, value: float | None) -> float:
    """Map raw factor to 0..1 colour intensity (higher = more “hot” / noteworthy)."""
    if value is None:
        return 0.0
    v = float(value)
    if key == "atr_ratio":
        return _clamp01(abs(v - 1.0) / 0.8)
    if key == "compression_score":
        return _clamp01(v)
    if key == "realized_vol_ratio":
        return _clamp01((v - 0.7) / 1.0)
    if key == "bb_width_pctile":
        # Low percentile = compression (hot for breakout narrative)
        return _clamp01(1.0 - v)
    if key == "rsi14":
        return _clamp01(abs(v - 50.0) / 35.0)
    if key == "dist_ma20_pct":
        return _clamp01(abs(v) / 12.0)
    if key == "ret14_pct":
        return _clamp01(abs(v) / 20.0)
    if key == "days_since_last_event":
        # Recent event OR long quiet both noteworthy — U-shape
        if v <= 14:
            return _clamp01(1.0 - v / 14.0)
        if v >= 30:
            return _clamp01(min(1.0, (v - 30) / 40.0 + 0.4))
        return 0.2
    return _clamp01(abs(v) / (abs(v) + 1.0))


def factor_chip_it(key: str, value: float | None, intensity: float) -> str:
    if value is None:
        return "n/d"
    if intensity < 0.33:
        level = "calmo"
    elif intensity < 0.66:
        level = "medio"
    else:
        level = "caldo"
    if key == "compression_score" and value >= 0.7:
        return f"compresso ({level})"
    if key == "rsi14":
        if value >= 70:
            return "ipercomprato"
        if value <= 30:
            return "ipervenduto"
        return f"neutro ({level})"
    return level


def _bias_it(bias: str) -> str:
    return {"up": "Rialzo", "down": "Ribasso", "neutral": "Neutro"}.get(bias, bias)


def _confidence_it(conf: str) -> str:
    return {"low": "bassa", "medium": "media", "high": "alta"}.get(conf, conf)


def _pattern_for(regime: str, direction_bias: str) -> PatternCard:
    base = _REGIME_PATTERNS.get(regime, _REGIME_PATTERNS["neutral_range"])
    # Lightly tilt arrow from direction when not breakout
    arrow = base.arrow
    if arrow == "side" and direction_bias == "up":
        arrow = "up"
    elif arrow == "side" and direction_bias == "down":
        arrow = "down"
    if arrow == base.arrow and direction_bias == direction_bias:
        pass
    return PatternCard(
        pattern_id=base.pattern_id,
        title_it=base.title_it,
        arrow=arrow,
        primary_it=base.primary_it,
        secondary_it=base.secondary_it,
        projection_it=base.projection_it,
        gamified_hint_it=base.gamified_hint_it,
    )


def _scenario_probs(direction_up: float, bias: str) -> dict[str, float]:
    """Educational scenario mix: up / down / neutral (%)."""
    up = _clamp01(direction_up)
    down = 1.0 - up
    if bias == "neutral":
        neutral = 0.28
        scale = 1.0 - neutral
        return {
            "up": round(up * scale * 100, 1),
            "down": round(down * scale * 100, 1),
            "neutral": round(neutral * 100, 1),
        }
    # Small residual “uncertain” bucket
    neutral = 0.12
    scale = 1.0 - neutral
    return {
        "up": round(up * scale * 100, 1),
        "down": round(down * scale * 100, 1),
        "neutral": round(neutral * 100, 1),
    }


def _hero(regime: str, bias: str, p14_pct: float, expected_move: float) -> tuple[str, str]:
    title = "Cosa significa"
    pattern = _REGIME_PATTERNS.get(regime, _REGIME_PATTERNS["neutral_range"])
    body = (
        f"{pattern.primary_it} "
        f"In sintesi: probabilità circa {p14_pct:.0f}% di un movimento ≥ soglia entro 14 giorni, "
        f"magnitudine tipica ~{expected_move:.0f}%, bias { _bias_it(bias).lower() }. "
        f"È una simulazione educativa, non un consiglio di investimento."
    )
    return title, body


def build_factor_cells(factors: dict[str, Any] | None) -> list[FactorHeatCell]:
    factors = factors or {}
    cells: list[FactorHeatCell] = []
    for key in FACTOR_ORDER:
        raw = factors.get(key)
        try:
            val = float(raw) if raw is not None else None
        except (TypeError, ValueError):
            val = None
        intensity = factor_intensity(key, val)
        cells.append(
            FactorHeatCell(
                key=key,
                label_it=FACTOR_LABELS_IT.get(key, key),
                value=val,
                intensity=round(intensity, 3),
                chip_it=factor_chip_it(key, val, intensity),
            )
        )
    return cells


def build_volatility_ux(
    *,
    regime_label: str,
    direction_bias: str,
    direction_up_prob: float,
    confidence: str,
    probability_7d: float,
    probability_14d: float,
    probability_21d: float,
    expected_move_pct: float,
    window_start: str,
    window_end: str,
    most_probable_window: str,
    factors: dict[str, Any] | None = None,
    analog_count: int = 0,
    asset_symbol: str = "",
    as_of_date: str = "",
) -> VolatilityUxView:
    """Build shared UX view from forecast fields (Python engines / API dict)."""
    p7 = round(float(probability_7d) * 100, 1)
    p14 = round(float(probability_14d) * 100, 1)
    p21 = round(float(probability_21d) * 100, 1)
    hero_title, hero_body = _hero(regime_label, direction_bias, p14, expected_move_pct)
    pattern = _pattern_for(regime_label, direction_bias)
    window_it = (
        f"Finestra più probabile: {window_start} → {window_end}. "
        f"({most_probable_window})"
    )
    return VolatilityUxView(
        hero_title_it=hero_title,
        hero_body_it=hero_body,
        pattern=pattern,
        factor_cells=build_factor_cells(factors),
        horizon_probs_pct={"7d": p7, "14d": p14, "21d": p21},
        scenario_probs_pct=_scenario_probs(float(direction_up_prob), direction_bias),
        direction_bias=direction_bias,
        direction_bias_it=_bias_it(direction_bias),
        confidence_it=_confidence_it(confidence),
        window_summary_it=window_it,
        extras={
            "asset_symbol": asset_symbol,
            "as_of_date": as_of_date,
            "analog_count": analog_count,
            "regime_label": regime_label,
            "expected_move_pct": expected_move_pct,
        },
    )


def ux_from_forecast_dict(payload: dict[str, Any]) -> VolatilityUxView:
    """Accept VolatilityEventForecast.to_dict() or similar."""
    probs = payload.get("probabilities") or {}
    return build_volatility_ux(
        regime_label=str(payload.get("regime_label") or "neutral_range"),
        direction_bias=str(payload.get("direction_bias") or "neutral"),
        direction_up_prob=float(payload.get("direction_up_prob_pct", 50.0)) / 100.0,
        confidence=str(payload.get("confidence") or "low"),
        probability_7d=float(probs.get("7d_pct", 0)) / 100.0,
        probability_14d=float(probs.get("14d_pct", 0)) / 100.0,
        probability_21d=float(probs.get("21d_pct", 0)) / 100.0,
        expected_move_pct=float(payload.get("expected_move_pct") or 10.0),
        window_start=str(payload.get("window_start_estimate") or ""),
        window_end=str(payload.get("window_end_estimate") or ""),
        most_probable_window=str(payload.get("most_probable_window") or ""),
        factors=payload.get("factors") or {},
        analog_count=int(payload.get("analog_count") or 0),
        asset_symbol=str(payload.get("asset_symbol") or ""),
        as_of_date=str(payload.get("as_of_date") or ""),
    )


def ux_from_forecast_obj(forecast: Any) -> VolatilityUxView:
    """Accept VolatilityEventForecast dataclass instance."""
    if hasattr(forecast, "to_dict"):
        return ux_from_forecast_dict(forecast.to_dict())
    raise TypeError("forecast must expose to_dict()")
