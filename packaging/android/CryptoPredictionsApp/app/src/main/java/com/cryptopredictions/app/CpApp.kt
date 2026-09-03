package com.cryptopredictions.app

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import java.util.concurrent.TimeUnit

class CpApp : Application() {
    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        scheduleVolatilityWorker()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Volatility alerts",
                NotificationManager.IMPORTANCE_DEFAULT
            ).apply {
                description = "Simulation-only volatility event notifications"
            }
            getSystemService(NotificationManager::class.java)
                .createNotificationChannel(channel)
        }
    }

    private fun scheduleVolatilityWorker() {
        val req = PeriodicWorkRequestBuilder<VolatilityWorker>(6, TimeUnit.HOURS)
            .build()
        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            "vol_probe",
            ExistingPeriodicWorkPolicy.KEEP,
            req
        )
    }

    companion object {
        const val CHANNEL_ID = "cp_volatility"
    }
}
