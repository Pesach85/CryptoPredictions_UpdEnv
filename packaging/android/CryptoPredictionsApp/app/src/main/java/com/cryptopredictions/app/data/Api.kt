package com.cryptopredictions.app.data

import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import java.util.concurrent.TimeUnit

data class HealthResponse(val status: String?, val disclaimer: String?)
data class AssetsResponse(val assets: List<String>)
data class VolatilityResponse(
    val asset_symbol: String?,
    val as_of_date: String?,
    val threshold_pct: Double?,
    val current_price: Double?,
    val probabilities: Map<String, Double>?,
    val expected_move_pct: Double?,
    val direction_bias: String?,
    val most_probable_window: String?,
    val window_start_estimate: String?,
    val window_end_estimate: String?,
    val confidence: String?,
    val regime_label: String?,
    val disclaimer: String?
)

interface CpApi {
    @GET("/api/v1/health")
    suspend fun health(): HealthResponse

    @GET("/api/v1/assets")
    suspend fun listAssets(): AssetsResponse

    @POST("/api/v1/volatility/forecast")
    suspend fun volatilityForecast(@Body body: Map<String, @JvmSuppressWildcards Any>): VolatilityResponse
}

object ApiFactory {
    fun create(baseUrl: String): CpApi {
        val moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build()
        val client = OkHttpClient.Builder()
            .connectTimeout(20, TimeUnit.SECONDS)
            .readTimeout(60, TimeUnit.SECONDS)
            .addInterceptor(HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BASIC
            })
            .build()
        return Retrofit.Builder()
            .baseUrl(if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/")
            .client(client)
            .addConverterFactory(MoshiConverterFactory.create(moshi))
            .build()
            .create(CpApi::class.java)
    }
}
