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
import androidx.compose.ui.Modifier.modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.cryptopredictions.app.data.ApiFactory
import com.cryptopredictions.app.data.Prefs
import com.cryptopredictions.app.data.VolatilityResponse
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CpAppRoot(onShare: (String) -> Unit) {
    var tab by remember { mutableIntStateOf(0) }
    Scaffold(
        topBar = {
            TopAppBar(title = { Text("CryptoPredictions") })
        },
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
    var assets by remember { mutableStateOf(listOf("ETHUSD", "XBTUSD", "SOLUSD")) }
    var asset by remember { mutableStateOf(prefs.watchAsset) }
    var expanded by remember { mutableStateOf(false) }
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var result by remember { mutableStateOf<VolatilityResponse?>(null) }

    LaunchedEffect(Unit) {
        try {
            assets = ApiFactory.create(prefs.apiBaseUrl).listAssets().assets
        } catch (_: Exception) { /* keep defaults */ }
    }

    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
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
                        result = ApiFactory.create(prefs.apiBaseUrl).volatilityForecast(
                            mapOf("asset" to asset, "threshold_pct" to 10.0)
                        )
                    } catch (e: Exception) {
                        error = e.message ?: e.toString()
                        result = null
                    } finally {
                        loading = false
                    }
                }
            },
            modifier = Modifier.fillMaxWidth()
        ) { Text("Analyze volatility event") }

        if (loading) CircularProgressIndicator()
        error?.let { Text(it, color = MaterialTheme.colorScheme.error) }

        result?.let { r ->
            Card(Modifier = Modifier.fillMaxWidth()) {
                Column(Modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("Regime: ${r.regime_label}", style = MaterialTheme.typography.titleMedium)
                    Text("P7 / P14 / P21: ${r.probabilities?.get("7d_pct")} / ${r.probabilities?.get("14d_pct")} / ${r.probabilities?.get("21d_pct")}")
                    Text("Expected move: ~${r.expected_move_pct}%")
                    Text("Bias: ${r.direction_bias}")
                    Text("Window: ${r.most_probable_window}")
                    Text("Confidence: ${r.confidence}")
                    Spacer(Modifier = Modifier.height(8.dp))
                    Button(onClick = {
                        val text = buildString {
                            appendLine("CryptoPredictions volatility (simulation only)")
                            appendLine("${r.asset_symbol} as-of ${r.as_of_date}")
                            appendLine("P14=${r.probabilities?.get("14d_pct")}% bias=${r.direction_bias}")
                            appendLine("Window: ${r.most_probable_window}")
                        }
                        onShare(text)
                    }) { Text("Share") }
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
    var health by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()

    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(
            "Dev-linked: point at the host FastAPI from the live repo. " +
                "Emulator default http://10.0.2.2:8000 — device: LAN IP or adb reverse.",
            style = MaterialTheme.typography.bodySmall
        )
        OutlinedTextField(
            value = url,
            onValueChange = { url = it },
            label = { Text("API base URL") },
            modifier = Modifier.fillMaxWidth()
        )
        Button(onClick = {
            prefs.apiBaseUrl = url
            scope.launch {
                health = try {
                    val h = ApiFactory.create(prefs.apiBaseUrl).health()
                    "OK: ${h.status} — ${h.disclaimer}"
                } catch (e: Exception) {
                    "FAIL: ${e.message}"
                }
            }
        }) { Text("Save & ping /health") }
        health?.let { Text(it) }
    }
}
