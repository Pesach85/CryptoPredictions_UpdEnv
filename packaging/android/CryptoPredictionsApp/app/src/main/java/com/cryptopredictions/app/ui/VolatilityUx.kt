package com.cryptopredictions.app.ui

import com.cryptopredictions.app.engine.VolatilityEngine
import kotlin.math.abs

/**
 * Kotlin mirror of services/volatility_ux.py — Italian educational copy + heat intensities.
 * Simulation only — not investment advice. OHLCV parameter heatmaps (not tick order-flow).
 */
object VolatilityUx {
    const val DISCLAIMER = "Simulation only — not investment advice. Uso educativo / gamificato."

    data class FactorHeatCell(
        val key: String,
        val labelIt: String,
        val value: Double?,
        val intensity: Float,
        val chipIt: String
    )

    data class PatternCard(
        val patternId: String,
        val titleIt: String,
        val arrow: String,
        val primaryIt: String,
        val secondaryIt: String,
        val projectionIt: String,
        val gamifiedHintIt: String
    )

    data class View(
        val heroTitleIt: String,
        val heroBodyIt: String,
        val pattern: PatternCard,
        val factorCells: List<FactorHeatCell>,
        val horizonProbsPct: Map<String, Float>,
        val scenarioProbsPct: Map<String, Float>,
        val directionBias: String,
        val directionBiasIt: String,
        val confidenceIt: String,
        val windowSummaryIt: String,
        val disclaimer: String = DISCLAIMER,
        val expectedMovePct: Double = 0.0,
        val analogCount: Int = 0,
        val regimeLabel: String = ""
    )

    private val factorOrder = listOf(
        "atr_ratio", "compression_score", "realized_vol_ratio", "bb_width_pctile",
        "rsi14", "dist_ma20_pct", "ret14_pct", "days_since_last_event"
    )

    private val factorLabels = mapOf(
        "atr_ratio" to "ATR vs mediana",
        "compression_score" to "Compressione",
        "realized_vol_ratio" to "Vol realizzata",
        "bb_width_pctile" to "Bande Bollinger",
        "rsi14" to "RSI 14",
        "dist_ma20_pct" to "Distanza MA20",
        "ret14_pct" to "Rendimento 14g",
        "days_since_last_event" to "Giorni da evento"
    )

    private fun clamp01(x: Double): Float = x.coerceIn(0.0, 1.0).toFloat()

    fun factorIntensity(key: String, value: Double?): Float {
        if (value == null) return 0f
        val v = value
        return when (key) {
            "atr_ratio" -> clamp01(abs(v - 1.0) / 0.8)
            "compression_score" -> clamp01(v)
            "realized_vol_ratio" -> clamp01((v - 0.7) / 1.0)
            "bb_width_pctile" -> clamp01(1.0 - v)
            "rsi14" -> clamp01(abs(v - 50.0) / 35.0)
            "dist_ma20_pct" -> clamp01(abs(v) / 12.0)
            "ret14_pct" -> clamp01(abs(v) / 20.0)
            "days_since_last_event" -> when {
                v <= 14 -> clamp01(1.0 - v / 14.0)
                v >= 30 -> clamp01(minOf(1.0, (v - 30) / 40.0 + 0.4))
                else -> 0.2f
            }
            else -> clamp01(abs(v) / (abs(v) + 1.0))
        }
    }

    private fun factorChip(key: String, value: Double?, intensity: Float): String {
        if (value == null) return "n/d"
        val level = when {
            intensity < 0.33f -> "calmo"
            intensity < 0.66f -> "medio"
            else -> "caldo"
        }
        if (key == "compression_score" && value >= 0.7) return "compresso ($level)"
        if (key == "rsi14") {
            return when {
                value >= 70 -> "ipercomprato"
                value <= 30 -> "ipervenduto"
                else -> "neutro ($level)"
            }
        }
        return level
    }

    fun biasIt(bias: String) = when (bias) {
        "up" -> "Rialzo"
        "down" -> "Ribasso"
        else -> "Neutro"
    }

    fun confidenceIt(c: String) = when (c) {
        "high" -> "alta"
        "medium" -> "media"
        else -> "bassa"
    }

    private fun basePattern(regime: String): PatternCard = when (regime) {
        "volatility_compression" -> PatternCard(
            "compression_breakout",
            "Compressione · possibile breakout",
            "breakout",
            "Il mercato sembra “compresso”: range stretti, energia in accumulo.",
            "Storicamente, dopo compressioni simili, spesso arriva un movimento più ampio.",
            "Scenario educativo: allargamento del range entro 1–3 settimane (direzione da bias).",
            "Carta cheat-sheet: molla compressa — non è un segnale di trade."
        )
        "post_impulse_consolidation" -> PatternCard(
            "post_impulse",
            "Consolidamento post-impulso",
            "side",
            "Dopo un rally/shock recente, il prezzo digests lo sbalzo.",
            "Possibile prosecuzione o correzione: gli analoghi storici pesano entrambe le vie.",
            "Scenario educativo: consolidamento, poi un nuovo impulso (su o giù).",
            "Carta: pausa dopo lo sprint — come in un pattern di continuazione semplificato."
        )
        "elevated_volatility" -> PatternCard(
            "elevated_vol",
            "Volatilità alta",
            "side",
            "Oscillazioni più ampie del solito: il “terreno” è mosso.",
            "Eventi ±soglia restano plausibili su più finestre temporali.",
            "Scenario educativo: swing ampi; probabilità evento elevate su 14–21 giorni.",
            "Carta: mare mosso — osserva le barre di probabilità, non inseguire il prezzo."
        )
        else -> PatternCard(
            "neutral_range",
            "Range neutro / laterale",
            "side",
            "Nessun regime estremo dominante: il prezzo si muove in una fascia ordinaria.",
            "Le probabilità evento dipendono soprattutto dagli analoghi storici.",
            "Scenario educativo: movimento laterale con chance moderate di breakout soft.",
            "Carta: pianura — utile per imparare a leggere fattori e heatmap."
        )
    }

    private fun patternFor(regime: String, bias: String): PatternCard {
        val base = basePattern(regime)
        val arrow = when {
            base.arrow == "side" && bias == "up" -> "up"
            base.arrow == "side" && bias == "down" -> "down"
            else -> base.arrow
        }
        return base.copy(arrow = arrow)
    }

    private fun scenarioProbs(directionUp: Double, bias: String): Map<String, Float> {
        val up = directionUp.coerceIn(0.0, 1.0)
        val down = 1.0 - up
        val neutral = if (bias == "neutral") 0.28 else 0.12
        val scale = 1.0 - neutral
        return mapOf(
            "up" to (up * scale * 100).toFloat(),
            "down" to (down * scale * 100).toFloat(),
            "neutral" to (neutral * 100).toFloat()
        )
    }

    fun buildFactorCells(factors: Map<String, Double?>): List<FactorHeatCell> =
        factorOrder.map { key ->
            val v = factors[key]
            val intensity = factorIntensity(key, v)
            FactorHeatCell(
                key = key,
                labelIt = factorLabels[key] ?: key,
                value = v,
                intensity = intensity,
                chipIt = factorChip(key, v, intensity)
            )
        }

    fun fromForecast(r: VolatilityEngine.Forecast): View {
        val p7 = (r.probability7d * 100).toFloat()
        val p14 = (r.probability14d * 100).toFloat()
        val p21 = (r.probability21d * 100).toFloat()
        val pattern = patternFor(r.regimeLabel, r.directionBias)
        val heroBody =
            "${pattern.primaryIt} In sintesi: probabilità circa ${"%.0f".format(p14)}% di un movimento ≥ soglia entro 14 giorni, " +
                "magnitudine tipica ~${"%.0f".format(r.expectedMovePct)}%, bias ${biasIt(r.directionBias).lowercase()}. " +
                "È una simulazione educativa, non un consiglio di investimento."
        return View(
            heroTitleIt = "Cosa significa",
            heroBodyIt = heroBody,
            pattern = pattern,
            factorCells = buildFactorCells(r.factors),
            horizonProbsPct = mapOf("7d" to p7, "14d" to p14, "21d" to p21),
            scenarioProbsPct = scenarioProbs(r.directionUpProb, r.directionBias),
            directionBias = r.directionBias,
            directionBiasIt = biasIt(r.directionBias),
            confidenceIt = confidenceIt(r.confidence),
            windowSummaryIt = "Finestra più probabile: ${r.windowStart} → ${r.windowEnd}. (${r.mostProbableWindow})",
            expectedMovePct = r.expectedMovePct,
            analogCount = r.analogCount,
            regimeLabel = r.regimeLabel
        )
    }
}
