package com.cryptopredictions.app.data

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.cryptopredictions.app.BuildConfig

class Prefs(context: Context) {
    private val master = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()
    private val sp = EncryptedSharedPreferences.create(
        context,
        "cp_secure_prefs",
        master,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )

    var apiBaseUrl: String
        get() = sp.getString(KEY_API, BuildConfig.DEFAULT_API_BASE) ?: BuildConfig.DEFAULT_API_BASE
        set(v) = sp.edit().putString(KEY_API, v.trimEnd('/')).apply()

    var watchAsset: String
        get() = sp.getString(KEY_ASSET, "ETHUSD") ?: "ETHUSD"
        set(v) = sp.edit().putString(KEY_ASSET, v).apply()

    /** ondevice (default) | remote */
    var computeMode: String
        get() = sp.getString(KEY_MODE, "ondevice") ?: "ondevice"
        set(v) = sp.edit().putString(KEY_MODE, v).apply()

    companion object {
        private const val KEY_API = "api_base"
        private const val KEY_ASSET = "watch_asset"
        private const val KEY_MODE = "compute_mode"
    }
}
