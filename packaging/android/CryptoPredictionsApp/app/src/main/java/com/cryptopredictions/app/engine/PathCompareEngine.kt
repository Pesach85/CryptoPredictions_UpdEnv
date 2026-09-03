package com.cryptopredictions.app.engine

import kotlin.math.abs

/**
 * On-device multi-path compare (Naive + EWMA + linear-regression 1-step).
 * Heavy Python models (RF/XGB/Prophet) remain optional via remote API.
 * Simulation only — not investment advice.
 */
object PathCompareEngine {
    data class SeriesResult(
        val dates: List<String>,
        val actual: List<Double>,
        val naive: List<Double>,
        val ewma: List<Double>,
        val linreg1step: List<Double>,
        val metrics: Map<String, Map<String, Double>>
    )

    fun compareAugustWindow(
        bars: List<OhlcvBar>,
        windowStart: String = "2026-08-01",
        windowEnd: String = "2026-08-29"
    ): SeriesResult {
        val train = bars.filter { it.date < windowStart }
        require(train.isNotEmpty()) { "No training history before $windowStart" }
        val window = bars.filter { it.date >= windowStart && it.date <= windowEnd }
        require(window.size >= 5) { "Window too short" }

        val lastTrain = train.last().close
        val actual = window.map { it.close }
        val dates = window.map { it.date }
        val naive = List(window.size) { lastTrain }

        // EWMA multi-step from train end
        val alpha = 0.2
        var ewmaLevel = train.takeLast(20).map { it.close }.average()
        val ewma = ArrayList<Double>(window.size)
        for (i in window.indices) {
            // pure forecast path: no peeking actuals after train
            ewma.add(ewmaLevel)
            // mild drift from last train returns
            val trainRets = train.takeLast(15).zipWithNext { a, b -> b.close / a.close - 1.0 }
            val drift = if (trainRets.isEmpty()) 0.0 else trainRets.average() * alpha
            ewmaLevel *= (1.0 + drift)
        }

        // Linear regression 1-step using lag features (actual lags = leakage-safe train, then use real lags in window)
        val lags = 7
        val closesAll = bars.map { it.close }
        fun rowAt(idx: Int): DoubleArray? {
            if (idx < lags) return null
            return DoubleArray(lags) { k -> closesAll[idx - 1 - k] }
        }
        // Train on indices where date < windowStart
        val trainIdx = bars.indices.filter { bars[it].date < windowStart && it >= lags }
        require(trainIdx.size >= 30) { "Not enough supervised rows" }
        val xTrain = trainIdx.map { rowAt(it)!! }
        val yTrain = trainIdx.map { closesAll[it] }
        val beta = ridgeFit(xTrain, yTrain, l2 = 1e-2)

        val linreg = ArrayList<Double>()
        for (i in bars.indices) {
            if (bars[i].date < windowStart || bars[i].date > windowEnd) continue
            val x = rowAt(i) ?: continue
            linreg.add(dot(beta, x))
        }
        while (linreg.size < window.size) linreg.add(linreg.lastOrNull() ?: lastTrain)

        fun mape(pred: List<Double>): Double {
            var s = 0.0
            var n = 0
            for (i in actual.indices) {
                if (actual[i] != 0.0) {
                    s += abs(actual[i] - pred[i]) / abs(actual[i])
                    n++
                }
            }
            return if (n == 0) 0.0 else s / n * 100.0
        }

        val metrics = mapOf(
            "naive" to mapOf("MAPE" to mape(naive)),
            "ewma" to mapOf("MAPE" to mape(ewma)),
            "linreg_1step" to mapOf("MAPE" to mape(linreg.take(actual.size)))
        )
        return SeriesResult(dates, actual, naive, ewma, linreg.take(actual.size), metrics)
    }

    private fun ridgeFit(xs: List<DoubleArray>, ys: List<Double>, l2: Double): DoubleArray {
        val p = xs[0].size
        // beta = (X'X + l2 I)^-1 X'y  via Gaussian elimination
        val xtx = Array(p) { DoubleArray(p) }
        val xty = DoubleArray(p)
        for (i in xs.indices) {
            val x = xs[i]
            val y = ys[i]
            for (a in 0 until p) {
                xty[a] += x[a] * y
                for (b in 0 until p) xtx[a][b] += x[a] * x[b]
            }
        }
        for (a in 0 until p) xtx[a][a] += l2
        return solve(xtx, xty)
    }

    private fun solve(aIn: Array<DoubleArray>, bIn: DoubleArray): DoubleArray {
        val n = bIn.size
        val a = Array(n) { aIn[it].clone() }
        val b = bIn.clone()
        for (col in 0 until n) {
            var pivot = col
            for (r in col + 1 until n) if (abs(a[r][col]) > abs(a[pivot][col])) pivot = r
            val tmp = a[col]; a[col] = a[pivot]; a[pivot] = tmp
            val tb = b[col]; b[col] = b[pivot]; b[pivot] = tb
            val div = a[col][col]
            if (abs(div) < 1e-12) continue
            for (c in col until n) a[col][c] /= div
            b[col] /= div
            for (r in 0 until n) {
                if (r == col) continue
                val f = a[r][col]
                for (c in col until n) a[r][c] -= f * a[col][c]
                b[r] -= f * b[col]
            }
        }
        return b
    }

    private fun dot(w: DoubleArray, x: DoubleArray): Double {
        var s = 0.0
        for (i in w.indices) s += w[i] * x[i]
        return s
    }
}
