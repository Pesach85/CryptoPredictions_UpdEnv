package com.cryptopredictions.app.engine

/** Single daily OHLCV bar. */
data class OhlcvBar(
    val date: String,
    val open: Double,
    val high: Double,
    val low: Double,
    val close: Double,
    val volume: Double
)
