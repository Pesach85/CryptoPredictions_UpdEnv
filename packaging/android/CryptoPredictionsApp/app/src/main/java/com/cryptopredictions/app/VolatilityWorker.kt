package com.cryptopredictions.app

import android.app.NotificationManager
import android.content.Context
import androidx.core.app.NotificationCompat
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.cryptopredictions.app.data.Prefs
import com.cryptopredictions.app.engine.CsvLoader
import com.cryptopredictions.app.engine.VolatilityEngine

/** On-device volatility probe — no FastAPI required. */
class VolatilityWorker(
    appContext: Context,
    params: WorkerParameters
) : CoroutineWorker(appContext, params) {
    override suspend fun doWork(): Result {
        return try {
            val prefs = Prefs(applicationContext)
            val assets = CsvLoader.listBundled(applicationContext)
            val asset = prefs.watchAsset.ifBlank { assets.firstOrNull() ?: "ETHUSD" }
            val bars = CsvLoader.loadAsset(applicationContext, asset)
            val forecast = VolatilityEngine.forecast(bars, asset, 10.0)
            val p14 = forecast.probability14d * 100.0
            if (p14 >= 60.0) {
                val nm = applicationContext.getSystemService(NotificationManager::class.java)
                val n = NotificationCompat.Builder(applicationContext, CpApp.CHANNEL_ID)
                    .setSmallIcon(android.R.drawable.ic_dialog_info)
                    .setContentTitle("$asset volatility (on-device)")
                    .setContentText(
                        "P14=${"%.0f".format(p14)}% bias=${forecast.directionBias} (simulation only)"
                    )
                    .setPriority(NotificationCompat.PRIORITY_DEFAULT)
                    .build()
                nm.notify(1001, n)
            }
            Result.success()
        } catch (_: Exception) {
            Result.retry()
        }
    }
}
