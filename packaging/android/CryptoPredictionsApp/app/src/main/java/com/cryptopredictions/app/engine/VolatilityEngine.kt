package com.cryptopredictions.app.engine

import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/**
 * On-device port of services/volatility_events.py — no FastAPI required.
 * Simulation only — not investment advice.
 */
object VolatilityEngine {
    private const val MIN_HISTORY = 180
    private const val ANALOG_TOP_K = 40

    data class Forecast(
        val assetSymbol: String,
        val asOfDate: String,
        val thresholdPct: Double,
        val currentPrice: Double,
        val probability7d: Double,
        val probability14d: Double,
        val probability21d: Double,
        val expectedMovePct: Double,
        val directionBias: String,
        val directionUpProb: Double,
        val mostProbableWindow: String,
        val windowStart: String,
        val windowEnd: String,
        val scenarioUpPct: Double,
        val scenarioDownPct: Double,
        val confidence: String,
        val regimeLabel: String,
        val factors: Map<String, Double?>,
        val regimeReasons: List<String>,
        val analogCount: Int,
        val engine: String = "on-device-kotlin"
    )

    fun forecast(bars: List<OhlcvBar>, asset: String, thresholdPct: Double = 10.0): Forecast {
        require(bars.size >= MIN_HISTORY) { "Need >= $MIN_HISTORY bars, got ${bars.size}" }
        val n = bars.size
        val closes = DoubleArray(n) { bars[it].close }
        val volumes = DoubleArray(n) { bars[it].volume }

        val ret1 = Indicators.pctChange(closes, 1)
        val ret3 = Indicators.pctChange(closes, 3)
        val ret14 = Indicators.pctChange(closes, 14)
        val atr = Indicators.atrPct(bars, 14)
        val atrMed60 = Indicators.rollingMedian(atr, 60)
        val atrRatio = DoubleArray(n) { i ->
            if (!atr[i].isNaN() && !atrMed60[i].isNaN() && atrMed60[i] != 0.0) atr[i] / atrMed60[i]
            else Double.NaN
        }
        val bb = Indicators.bbWidthPct(closes, 20)
        val bbPctile = Indicators.rollingPctile(bb, 120)
        val realized = DoubleArray(n) { Double.NaN }
        val retStd14 = Indicators.rollingStd(ret1, 14)
        for (i in realized.indices) {
            if (!retStd14[i].isNaN()) realized[i] = retStd14[i] * sqrt(365.0) * 100.0
        }
        val volMed90 = Indicators.rollingMedian(realized, 90)
        val volRatio = DoubleArray(n) { i ->
            if (!realized[i].isNaN() && !volMed90[i].isNaN() && volMed90[i] != 0.0) realized[i] / volMed90[i]
            else Double.NaN
        }
        val rsi = Indicators.rsi(closes, 14)
        val ma20 = Indicators.rollingMean(closes, 20)
        val distMa = DoubleArray(n) { i ->
            if (!ma20[i].isNaN() && ma20[i] != 0.0) (closes[i] / ma20[i] - 1.0) * 100.0
            else Double.NaN
        }
        val volMean = Indicators.rollingMean(volumes, 20)
        val volStd = Indicators.rollingStd(volumes, 20)
        val volZ = DoubleArray(n) { i ->
            if (!volMean[i].isNaN() && !volStd[i].isNaN() && volStd[i] != 0.0)
                (volumes[i] - volMean[i]) / volStd[i]
            else Double.NaN
        }
        val compression = DoubleArray(n) { i ->
            if (!bbPctile[i].isNaN()) 1.0 - bbPctile[i].coerceIn(0.0, 1.0) else Double.NaN
        }

        val thr = thresholdPct / 100.0
        val thr3 = thr * 1.2
        val event = BooleanArray(n) { i ->
            (!ret1[i].isNaN() && abs(ret1[i]) >= thr) || (!ret3[i].isNaN() && abs(ret3[i]) >= thr3)
        }
        val daysSince = DoubleArray(n) { Double.NaN }
        var lastEv = -1
        for (i in 0 until n) {
            if (lastEv >= 0) daysSince[i] = (i - lastEv).toDouble()
            // event day itself counts after marking previous
            if (event[i]) lastEv = i
        }

        val last = n - 1
        fun feat(i: Int): DoubleArray = doubleArrayOf(
            atrRatio[i], bbPctile[i], volRatio[i], rsi[i],
            distMa[i], compression[i], daysSince[i], ret14[i]
        )

        // History pool for analogs
        val histIdx = ArrayList<Int>()
        for (i in 60 until last) {
            val f = feat(i)
            if (f.all { !it.isNaN() }) histIdx.add(i)
        }
        require(histIdx.size >= 50) { "Insufficient feature history" }

        val target = feat(last)
        // z-score normalize
        val dim = 8
        val mu = DoubleArray(dim)
        val sigma = DoubleArray(dim) { 1.0 }
        for (d in 0 until dim) {
            var s = 0.0
            var s2 = 0.0
            for (i in histIdx) {
                val v = feat(i)[d]
                s += v
                s2 += v * v
            }
            val m = histIdx.size.toDouble()
            mu[d] = s / m
            sigma[d] = sqrt(max(1e-12, s2 / m - mu[d] * mu[d])).coerceAtLeast(1e-6)
        }
        fun z(f: DoubleArray, d: Int) = (f[d] - mu[d]) / sigma[d]

        data class Dist(val idx: Int, val d: Double)
        val dists = histIdx.map { i ->
            val f = feat(i)
            var sum = 0.0
            for (d in 0 until dim) {
                val diff = z(f, d) - z(target, d)
                sum += diff * diff
            }
            Dist(i, sqrt(sum))
        }.sortedBy { it.d }.take(min(ANALOG_TOP_K, histIdx.size))

        fun forwardHit(start: Int, horizon: Int): Triple<Boolean, Double, Int?> {
            if (start + 1 >= n) return Triple(false, 0.0, null)
            val end = min(start + horizon, n - 1)
            var maxMove = 0.0
            var daysTo: Int? = null
            for (i in start + 1..end) {
                val m1 = if (!ret1[i].isNaN()) abs(ret1[i]) * 100 else 0.0
                val m3 = if (!ret3[i].isNaN()) abs(ret3[i]) * 100 else 0.0
                val move = max(m1, m3)
                maxMove = max(maxMove, move)
                if (move >= thresholdPct && daysTo == null) daysTo = i - start
            }
            val hit = daysTo != null || (start + 1..end).any { event[it] }
            return Triple(hit, maxMove, daysTo)
        }

        val hits7 = ArrayList<Boolean>()
        val hits14 = ArrayList<Boolean>()
        val hits21 = ArrayList<Boolean>()
        val moves = ArrayList<Double>()
        var upCount = 0
        var downCount = 0
        val daysToHit = ArrayList<Int>()

        for (a in dists) {
            val loc = a.idx
            hits7.add(forwardHit(loc, 7).first)
            hits14.add(forwardHit(loc, 14).first)
            hits21.add(forwardHit(loc, 21).first)
            if (loc + 21 < n) {
                var maxUp = 0.0
                var maxDn = 0.0
                for (i in loc + 1..loc + 21) {
                    if (!ret1[i].isNaN()) {
                        maxUp = max(maxUp, ret1[i] * 100)
                        maxDn = min(maxDn, ret1[i] * 100)
                    }
                }
                if (abs(maxUp) >= abs(maxDn)) {
                    if (abs(maxUp) >= thresholdPct * 0.5) upCount++
                } else {
                    if (abs(maxDn) >= thresholdPct * 0.5) downCount++
                }
                moves.add(max(abs(maxUp), abs(maxDn)))
                val (_, _, dth) = forwardHit(loc, 21)
                if (dth != null) daysToHit.add(dth)
            }
        }

        fun meanBool(xs: List<Boolean>) = if (xs.isEmpty()) 0.0 else xs.count { it }.toDouble() / xs.size

        var score = 0.0
        val reasons = ArrayList<String>()
        val bbP = bbPctile[last]
        val atrR = atrRatio[last]
        val r14 = ret14[last]
        val dse = daysSince[last]
        val dma = distMa[last]
        val vz = volZ[last]

        if (!bbP.isNaN() && bbP < 0.25) {
            score += 0.15; reasons.add("Bollinger compression (low bandwidth percentile)")
        }
        if (!atrR.isNaN() && atrR < 0.85) {
            score += 0.12; reasons.add("ATR below 60d median - volatility contraction")
        }
        if (!r14.isNaN() && abs(r14) >= 0.15) {
            score += 0.18; reasons.add("Strong 14d impulse (+/-15%) - elevated follow-through risk")
        }
        if (!dse.isNaN() && dse <= 14) {
            score += 0.14; reasons.add("Recent major event within 14d - cluster volatility regime")
        }
        if (!dma.isNaN() && abs(dma) > 8) {
            score += 0.10; reasons.add("Price extended vs 20d MA")
        }
        if (!vz.isNaN() && vz < -0.5) {
            score += 0.08; reasons.add("Volume below average - pre-breakout pattern")
        }
        if (!dse.isNaN() && dse > 30) {
            score += 0.10; reasons.add("Extended calm (>30d since last +/-threshold event)")
        }

        val regimeScore = min(score, 0.65)
        val prob7 = min(0.85, meanBool(hits7) * 0.5 + regimeScore * 0.7)
        val prob14 = min(0.92, meanBool(hits14) * 0.55 + regimeScore + 0.15)
        val prob21 = min(0.95, meanBool(hits21) * 0.5 + regimeScore + 0.2)

        var dirUp = 0.5
        if (!dma.isNaN()) {
            if (dma > 10) dirUp = 0.35
            else if (dma < -8) dirUp = 0.65
        }
        if (!r14.isNaN() && r14 > 0.12) dirUp = dirUp * 0.7 + 0.15
        if (upCount + downCount > 0) {
            val analogUp = upCount.toDouble() / (upCount + downCount)
            dirUp = dirUp * 0.5 + analogUp * 0.5
        }
        val bias = when {
            dirUp >= 0.55 -> "up"
            dirUp <= 0.45 -> "down"
            else -> "neutral"
        }

        var expected = if (moves.isNotEmpty()) {
            moves.sorted()[moves.size / 2]
        } else thresholdPct
        expected = max(thresholdPct, min(expected * 1.1, thresholdPct * 2.5))

        val (p25, p75, med) = if (daysToHit.isNotEmpty()) {
            val sorted = daysToHit.sorted()
            Triple(
                sorted[(sorted.size * 0.25).toInt().coerceAtMost(sorted.lastIndex)],
                sorted[(sorted.size * 0.75).toInt().coerceAtMost(sorted.lastIndex)],
                sorted[sorted.size / 2]
            )
        } else Triple(5, 18, 10)

        val asOf = bars[last].date
        val winStart = shiftDate(asOf, max(1, p25))
        val winEnd = shiftDate(asOf, p75)
        val windowLabel = "Day $p25-$p75 from $asOf (~$winStart to $winEnd)"

        val regime = when {
            !r14.isNaN() && r14 > 0.15 && !dse.isNaN() && dse <= 14 -> "post_impulse_consolidation"
            !compression[last].isNaN() && compression[last] > 0.7 -> "volatility_compression"
            !volRatio[last].isNaN() && volRatio[last] > 1.3 -> "elevated_volatility"
            else -> "neutral_range"
        }
        val confidence = when {
            dists.size >= 30 && prob14 >= 0.6 -> "high"
            dists.size >= 30 && prob14 >= 0.45 -> "medium"
            else -> "low"
        }

        fun rd(v: Double, d: Int = 3): Double? =
            if (v.isNaN()) null else String.format("%.${d}f", v).toDouble()

        return Forecast(
            assetSymbol = asset,
            asOfDate = asOf,
            thresholdPct = thresholdPct,
            currentPrice = closes[last],
            probability7d = prob7,
            probability14d = prob14,
            probability21d = prob21,
            expectedMovePct = expected,
            directionBias = bias,
            directionUpProb = dirUp,
            mostProbableWindow = windowLabel,
            windowStart = winStart,
            windowEnd = winEnd,
            scenarioUpPct = if (bias != "down") expected else expected * 0.7,
            scenarioDownPct = if (bias != "up") expected else expected * 0.7,
            confidence = confidence,
            regimeLabel = regime,
            factors = mapOf(
                "atr_ratio" to rd(atrR),
                "bb_width_pctile" to rd(bbP),
                "realized_vol_ratio" to rd(volRatio[last]),
                "rsi14" to rd(rsi[last], 1),
                "dist_ma20_pct" to rd(dma, 2),
                "ret14_pct" to rd(if (r14.isNaN()) Double.NaN else r14 * 100, 2),
                "days_since_last_event" to if (dse.isNaN()) null else dse,
                "compression_score" to rd(compression[last])
            ),
            regimeReasons = reasons,
            analogCount = dists.size
        )
    }

    /** Naive calendar shift for daily series (approx; ignores weekends gaps in CSV). */
    private fun shiftDate(iso: String, days: Int): String {
        val parts = iso.split("-")
        if (parts.size < 3) return iso
        val y = parts[0].toInt()
        val m = parts[1].toInt()
        val d = parts[2].toInt()
        val cal = java.util.Calendar.getInstance()
        cal.set(y, m - 1, d)
        cal.add(java.util.Calendar.DAY_OF_MONTH, days)
        return String.format(
            "%04d-%02d-%02d",
            cal.get(java.util.Calendar.YEAR),
            cal.get(java.util.Calendar.MONTH) + 1,
            cal.get(java.util.Calendar.DAY_OF_MONTH)
        )
    }
}
