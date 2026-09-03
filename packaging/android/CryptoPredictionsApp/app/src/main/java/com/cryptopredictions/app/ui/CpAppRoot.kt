package com.cryptopredictions.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.cryptopredictions.app.data.ApiFactory
import com.cryptopredictions.app.data.Prefs
import com.cryptopredictions.app.engine.CsvLoader
import com.cryptopredictions.app.engine.PathCompareEngine
import com.cryptopredictions.app.engine.VolatilityEngine
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CpAppRoot(onShare: (String) -> Unit) {
    var tab by remember { mutableIntStateOf(0) }
    Scaffold(
        topBar = { TopAppBar(title = { Text("CryptoPredictions") }) },
        bottomBar = {
            NavigationBar {
                NavigationBarItem(
                    selected = tab == 0,
                    onClick = { tab = 0 },
                    icon = { Text("V") },
                    label = { Text("Radar") }
                )
                NavigationBarItem(
                    selected = tab == 1,
                    onClick = { tab = 1 },
                    icon = { Text("P") },
                    label = { Text("Paths") }
                )
                NavigationBarItem(
                    selected = tab == 2,
                    onClick = { tab = 2 },
                    icon = { Text("S") },
                    label = { Text("Settings") }
                )
            }
        }
    ) { pad ->
        Column(Modifier = Modifier.padding(pad).fillMaxSize().padding(16.dp)) {
            Text(
                "Simulation only — not investment advice.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.error
            )
            Spacer(Modifier = Modifier.height(8.dp))
            when (tab) {
                0 -> VolatilityScreen(onShare = onShare)
                1 -> PathsScreen()
                else -> SettingsScreen()
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun VolatilityScreen(onShare: (String) -> Unit) {
    val ctx = LocalContext.current
    val prefs = remember { Prefs(ctx) }
    val scope = rememberCoroutineScope()
    var assets by remember { mutableStateOf(CsvLoader.listBundled(ctx).ifEmpty { CsvLoader.BUNDLED_ASSETS }) }
    var asset by remember { mutableStateOf(prefs.watchAsset) }
    var expanded by remember { mutableStateOf(false) }
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var forecast by remember { mutableStateOf<VolatilityEngine.Forecast?>(null) }
    var mode by remember { mutableStateOf(prefs.computeMode) } // ondevice | remote

    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("Engine: ${if (mode == "ondevice") "ON-DEVICE Kotlin (no FastAPI)" else "Remote FastAPI"}")

        ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = it }) {
            OutlinedTextField(
                value = asset,
                onValueChange = {},
                readOnly = true,
                label = { Text("Asset") },
                trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded) },
                modifier = Modifier.menuAnchor().fillMaxWidth()
            )
            ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                assets.forEach { a ->
                    DropdownMenuItem(
                        text = { Text(a) },
                        onClick = {
                            asset = a
                            prefs.watchAsset = a
                            expanded = false
                        }
                    )
                }
            }
        }

        Button(
            onClick = {
                loading = true
                error = null
                scope.launch {
                    try {
                        forecast = withContext(Dispatchers.Default) {
                            if (mode == "ondevice") {
                                val bars = CsvLoader.loadAsset(ctx, asset)
                                VolatilityEngine.forecast(bars, asset, 10.0)
                            } else {
                                val api = ApiFactory.create(prefs.apiBaseUrl)
                                val r = api.volatilityForecast(
                                    mapOf("asset" to asset, "threshold_pct" to 10.0)
                                )
                                VolatilityEngine.Forecast(
                                    assetSymbol = r.asset_symbol ?: asset,
                                    asOfDate = r.as_of_date ?: "",
                                    thresholdPct = r.threshold_pct ?: 10.0,
                                    currentPrice = r.current_price ?: 0.0,
                                    probability7d = (r.probabilities?.get("7d_pct") ?: 0.0) / 100.0,
                                    probability14d = (r.probabilities?.get("14d_pct") ?: 0.0) / 100.0,
                                    probability21d = (r.probabilities?.get("21d_pct") ?: 0.0) / 100.0,
                                    expectedMovePct = r.expected_move_pct ?: 10.0,
                                    directionBias = r.direction_bias ?: "neutral",
                                    directionUpProb = 0.5,
                                    mostProbableWindow = r.most_probable_window ?: "",
                                    windowStart = r.window_start_estimate ?: "",
                                    windowEnd = r.window_end_estimate ?: "",
                                    scenarioUpPct = r.expected_move_pct ?: 10.0,
                                    scenarioDownPct = r.expected_move_pct ?: 10.0,
                                    confidence = r.confidence ?: "low",
                                    regimeLabel = r.regime_label ?: "neutral_range",
                                    factors = emptyMap(),
                                    regimeReasons = emptyList(),
                                    analogCount = 0,
                                    engine = "remote-fastapi"
                                )
                            }
                        }
                    } catch (e: Exception) {
                        error = e.message ?: e.toString()
                        forecast = null
                    } finally {
                        loading = false
                    }
                }
            },
            modifier = Modifier.fillMaxWidth()
        ) { Text("Analyze volatility event") }

        if (loading) CircularProgressIndicator()
        error?.let { Text(it, color = MaterialTheme.colorScheme.error) }

        forecast?.let { r ->
            Card(Modifier = Modifier.fillMaxWidth()) {
                Column(Modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("Engine: ${r.engine}", style = MaterialTheme.typography.labelMedium)
                    Text("Regime: ${r.regimeLabel}", style = MaterialTheme.typography.titleMedium)
                    Text(
                        "P7 / P14 / P21: ${"%.0f".format(r.probability7d * 100)} / " +
                            "${"%.0f".format(r.probability14d * 100)} / ${"%.0f".format(r.probability21d * 100)}"
                    )
                    Text("Expected move: ~${"%.1f".format(r.expectedMovePct)}%")
                    Text("Bias: ${r.directionBias}")
                    Text("Window: ${r.mostProbableWindow}")
                    Text("Confidence: ${r.confidence} · analogs: ${r.analogCount}")
                    if (r.regimeReasons.isNotEmpty()) {
                        Spacer(Modifier = Modifier.height(4.dp))
                        Text("Factors:", style = MaterialTheme.typography.labelLarge)
                        r.regimeReasons.forEach { Text("• $it") }
                    }
                    Spacer(Modifier = Modifier.height(8.dp))
                    Button(onClick = {
                        onShare(
                            buildString {
                                appendLine("CryptoPredictions (${r.engine}) — simulation only")
                                appendLine("${r.assetSymbol} as-of ${r.asOfDate}")
                                appendLine("P14=${"%.0f".format(r.probability14d * 100)}% bias=${r.directionBias}")
                                appendLine("Window: ${r.mostProbableWindow}")
                            }
                        )
                    }) { Text("Share") }
                }
            }
        }
        // keep mode in sync from settings via prefs re-read on recomposition tip:
        LaunchedEffect(Unit) { mode = prefs.computeMode }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PathsScreen() {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    var assets by remember { mutableStateOf(CsvLoader.listBundled(ctx)) }
    var asset by remember { mutableStateOf(assets.firstOrNull() ?: "ETHUSD") }
    var expanded by remember { mutableStateOf(false) }
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var result by remember { mutableStateOf<PathCompareEngine.SeriesResult?>(null) }

    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("On-device August path compare: Actual vs Naive / EWMA / LinReg 1-step.")
        ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = it }) {
            OutlinedTextField(
                value = asset,
                onValueChange = {},
                readOnly = true,
                label = { Text("Asset") },
                trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded) },
                modifier = Modifier.menuAnchor().fillMaxWidth()
            )
            ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                assets.forEach { a ->
                    DropdownMenuItem(text = { Text(a) }, onClick = { asset = a; expanded = false })
                }
            }
        }
        Button(
            onClick = {
                loading = true
                error = null
                scope.launch {
                    try {
                        result = withContext(Dispatchers.Default) {
                            PathCompareEngine.compareAugustWindow(CsvLoader.loadAsset(ctx, asset))
                        }
                    } catch (e: Exception) {
                        error = e.message
                        result = null
                    } finally {
                        loading = false
                    }
                }
            },
            modifier = Modifier.fillMaxWidth()
        ) { Text("Run on-device path compare") }
        if (loading) CircularProgressIndicator()
        error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        result?.let { r ->
            Card(Modifier = Modifier.fillMaxWidth()) {
                Column(Modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("${r.dates.first()} → ${r.dates.last()} · n=${r.dates.size}")
                    Text("Actual end: ${"%.2f".format(r.actual.last())}")
                    r.metrics.forEach { (k, v) ->
                        Text("$k MAPE: ${"%.2f".format(v["MAPE"] ?: 0.0)}%")
                    }
                    Text("Last Naive/EWMA/LinReg: ${"%.1f".format(r.naive.last())} / ${"%.1f".format(r.ewma.last())} / ${"%.1f".format(r.linreg1step.last())}")
                }
            }
        }
    }
}

@Composable
fun SettingsScreen() {
    val ctx = LocalContext.current
    val prefs = remember { Prefs(ctx) }
    var url by remember { mutableStateOf(prefs.apiBaseUrl) }
    var mode by remember { mutableStateOf(prefs.computeMode) }
    var health by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()

    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(
            "Default is ON-DEVICE: Volatility radar + path compare run inside the APK on bundled OHLCV. " +
                "Remote FastAPI is optional for heavy Python models (RF/Prophet).",
            style = MaterialTheme.typography.bodySmall
        )
        Text("Compute mode")
        androidx.compose.foundation.layout.Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilterChip(
                selected = mode == "ondevice",
                onClick = { mode = "ondevice"; prefs.computeMode = "ondevice" },
                label = { Text("On-device") }
            )
            FilterChip(
                selected = mode == "remote",
                onClick = { mode = "remote"; prefs.computeMode = "remote" },
                label = { Text("Remote API") }
            )
        }
        OutlinedTextField(
            value = url,
            onValueChange = { url = it },
            label = { Text("Optional API base URL") },
            modifier = Modifier.fillMaxWidth()
        )
        Button(onClick = {
            prefs.apiBaseUrl = url
            scope.launch {
                health = try {
                    val h = ApiFactory.create(prefs.apiBaseUrl).health()
                    "OK: ${h.status}"
                } catch (e: Exception) {
                    "FAIL (optional): ${e.message}"
                }
            }
        }) { Text("Save & ping remote /health") }
        health?.let { Text(it) }
        Text("Bundled assets: ${CsvLoader.listBundled(ctx).joinToString()}")
    }
}
