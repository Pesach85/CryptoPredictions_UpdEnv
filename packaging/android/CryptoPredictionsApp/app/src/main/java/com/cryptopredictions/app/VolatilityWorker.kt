package com.cryptopredictions.app

import android.app.NotificationManager
import android.content.Context
import androidx.core.app.NotificationCompat
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.cryptopredictions.app.data.ApiFactory
import com.cryptopredictions.app.data.Prefs

class VolatilityWorker(
    appContext: Context,
    params: WorkerParameters
) : CoroutineWorker(appContext, params) {
    override suspend fun doWork(): Result {
        return try {
            val prefs = Prefs(applicationContext)
            val api = ApiFactory.create(prefs.apiBaseUrl)
            val assets = api.listAssets().assets
            val asset = prefs.watchAsset.ifBlank { assets.firstOrNull() ?: "ETHUSD" }
            val forecast = api.volatilityForecast(
                mapOf("asset" to asset, "threshold_pct" to 10.0)
            )
            val p14 = forecast.probabilities?.get("14d_pct") ?: 0.0
            if (p14 >= 60.0) {
                val nm = applicationContext.getSystemService(NotificationManager::class.java)
                val n = NotificationCompat.Builder(applicationContext, CpApp.CHANNEL_ID)
                    .setSmallIcon(android.R.drawable.ic_dialog_info)
                    .setContentTitle("$asset volatility radar")
                    .setContentText("P14=${p14}% bias=${forecast.direction_bias} (simulation only)")
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
