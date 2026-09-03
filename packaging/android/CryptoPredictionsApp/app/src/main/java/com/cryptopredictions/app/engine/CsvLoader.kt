package com.cryptopredictions.app.engine

import android.content.Context
import java.io.BufferedReader
import java.io.InputStreamReader

object CsvLoader {
    val BUNDLED_ASSETS = listOf(
        "ETHUSD", "XBTUSD", "SOLUSD", "ADAUSD", "LTCUSD", "BNBUSD"
    )

    fun listBundled(context: Context): List<String> {
        val names = context.assets.list("ohlcv")?.toList().orEmpty()
        return names
            .filter { it.endsWith(".csv") }
            .map { it.removeSuffix(".csv") }
            .sorted()
    }

    fun loadAsset(context: Context, symbol: String): List<OhlcvBar> {
        val path = "ohlcv/$symbol.csv"
        context.assets.open(path).use { input ->
            val reader = BufferedReader(InputStreamReader(input))
            val header = reader.readLine() ?: throw IllegalArgumentException("Empty CSV: $path")
            val cols = header.split(",").map { it.trim().lowercase() }
            fun idx(vararg keys: String): Int {
                keys.forEach { k ->
                    val i = cols.indexOf(k)
                    if (i >= 0) return i
                }
                return -1
            }
            val iDate = idx("timestamp", "date", "datetime", "time")
            val iOpen = idx("open")
            val iHigh = idx("high")
            val iLow = idx("low")
            val iClose = idx("close")
            val iVol = idx("volume")
            require(iDate >= 0 && iClose >= 0) { "CSV needs date+close columns" }

            val rows = mutableListOf<OhlcvBar>()
            reader.lineSequence().forEach { line ->
                if (line.isBlank()) return@forEach
                val p = line.split(",")
                if (p.size <= maxOf(iDate, iClose)) return@forEach
                val dateRaw = p[iDate].trim().take(10)
                val close = p[iClose].toDoubleOrNull() ?: return@forEach
                val open = if (iOpen >= 0) p[iOpen].toDoubleOrNull() ?: close else close
                val high = if (iHigh >= 0) p[iHigh].toDoubleOrNull() ?: close else close
                val low = if (iLow >= 0) p[iLow].toDoubleOrNull() ?: close else close
                val vol = if (iVol >= 0) p[iVol].toDoubleOrNull() ?: 0.0 else 0.0
                rows.add(OhlcvBar(dateRaw, open, high, low, close, vol))
            }
            return rows.sortedBy { it.date }
        }
    }
}
