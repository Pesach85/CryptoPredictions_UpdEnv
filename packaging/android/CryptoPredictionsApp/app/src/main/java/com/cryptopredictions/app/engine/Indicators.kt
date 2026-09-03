package com.cryptopredictions.app.engine

import kotlin.math.abs
import kotlin.math.max
import kotlin.math.sqrt

/** Pure-Kotlin indicator helpers (no Python / no network). */
object Indicators {
    fun pctChange(closes: DoubleArray, lag: Int): DoubleArray {
        val out = DoubleArray(closes.size) { Double.NaN }
        for (i in lag until closes.size) {
            val prev = closes[i - lag]
            if (prev != 0.0) out[i] = closes[i] / prev - 1.0
        }
        return out
    }

    fun rollingMean(x: DoubleArray, w: Int): DoubleArray {
        val out = DoubleArray(x.size) { Double.NaN }
        var sum = 0.0
        var count = 0
        for (i in x.indices) {
            if (!x[i].isNaN()) {
                sum += x[i]
                count++
            }
            if (i >= w && !x[i - w].isNaN()) {
                sum -= x[i - w]
                count--
            }
            if (i >= w - 1 && count > 0) out[i] = sum / count
        }
        return out
    }

    fun rollingStd(x: DoubleArray, w: Int): DoubleArray {
        val out = DoubleArray(x.size) { Double.NaN }
        for (i in w - 1 until x.size) {
            var sum = 0.0
            var sum2 = 0.0
            var n = 0
            for (j in i - w + 1..i) {
                val v = x[j]
                if (!v.isNaN()) {
                    sum += v
                    sum2 += v * v
                    n++
                }
            }
            if (n >= max(2, w / 2)) {
                val mean = sum / n
                out[i] = sqrt(max(0.0, sum2 / n - mean * mean))
            }
        }
        return out
    }

    fun rollingMedian(x: DoubleArray, w: Int): DoubleArray {
        val out = DoubleArray(x.size) { Double.NaN }
        for (i in w - 1 until x.size) {
            val buf = ArrayList<Double>(w)
            for (j in i - w + 1..i) {
                val v = x[j]
                if (!v.isNaN()) buf.add(v)
            }
            if (buf.isEmpty()) continue
            buf.sort()
            out[i] = buf[buf.size / 2]
        }
        return out
    }

    fun rsi(closes: DoubleArray, period: Int = 14): DoubleArray {
        val out = DoubleArray(closes.size) { Double.NaN }
        if (closes.size <= period) return out
        var avgGain = 0.0
        var avgLoss = 0.0
        for (i in 1..period) {
            val d = closes[i] - closes[i - 1]
            if (d >= 0) avgGain += d else avgLoss -= d
        }
        avgGain /= period
        avgLoss /= period
        out[period] = if (avgLoss == 0.0) 100.0 else 100.0 - 100.0 / (1.0 + avgGain / avgLoss)
        for (i in period + 1 until closes.size) {
            val d = closes[i] - closes[i - 1]
            val gain = if (d > 0) d else 0.0
            val loss = if (d < 0) -d else 0.0
            avgGain = (avgGain * (period - 1) + gain) / period
            avgLoss = (avgLoss * (period - 1) + loss) / period
            out[i] = if (avgLoss == 0.0) 100.0 else 100.0 - 100.0 / (1.0 + avgGain / avgLoss)
        }
        return out
    }

    fun atrPct(bars: List<OhlcvBar>, period: Int = 14): DoubleArray {
        val n = bars.size
        val tr = DoubleArray(n) { Double.NaN }
        for (i in 1 until n) {
            val h = bars[i].high
            val l = bars[i].low
            val pc = bars[i - 1].close
            tr[i] = max(h - l, max(abs(h - pc), abs(l - pc)))
        }
        val atr = rollingMean(tr, period)
        val out = DoubleArray(n) { Double.NaN }
        for (i in atr.indices) {
            if (!atr[i].isNaN() && bars[i].close != 0.0) out[i] = atr[i] / bars[i].close * 100.0
        }
        return out
    }

    fun bbWidthPct(closes: DoubleArray, period: Int = 20): DoubleArray {
        val ma = rollingMean(closes, period)
        val sd = rollingStd(closes, period)
        val out = DoubleArray(closes.size) { Double.NaN }
        for (i in closes.indices) {
            if (!ma[i].isNaN() && !sd[i].isNaN() && ma[i] != 0.0) {
                out[i] = 2.0 * sd[i] / ma[i] * 100.0
            }
        }
        return out
    }

    /** Percentile rank of last value in trailing window [0,1]. */
    fun rollingPctile(x: DoubleArray, w: Int): DoubleArray {
        val out = DoubleArray(x.size) { Double.NaN }
        for (i in w - 1 until x.size) {
            val last = x[i]
            if (last.isNaN()) continue
            var below = 0
            var n = 0
            for (j in i - w + 1..i) {
                val v = x[j]
                if (!v.isNaN()) {
                    n++
                    if (v <= last) below++
                }
            }
            if (n > 0) out[i] = below.toDouble() / n
        }
        return out
    }
}
