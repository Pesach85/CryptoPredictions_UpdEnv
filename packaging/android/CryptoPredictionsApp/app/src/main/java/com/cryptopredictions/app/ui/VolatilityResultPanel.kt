package com.cryptopredictions.app.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.cryptopredictions.app.engine.VolatilityEngine
import kotlin.math.abs

/** Structured volatility result UX — heatmap + pattern + probabilities. */
@Composable
fun VolatilityResultPanel(
    forecast: VolatilityEngine.Forecast,
    onShare: (String) -> Unit
) {
    val ux = VolatilityUx.fromForecast(forecast)
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(
            ux.disclaimer,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.error
        )

        // Hero — Cosa significa
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.primaryContainer
            )
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text(ux.heroTitleIt, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Text(ux.heroBodyIt, style = MaterialTheme.typography.bodyMedium)
                Text(
                    "Engine: ${forecast.engine} · Confidenza ${ux.confidenceIt} · analoghi ${ux.analogCount}",
                    style = MaterialTheme.typography.labelSmall
                )
            }
        }

        // Pattern card (gamified)
        PatternCardView(ux.pattern, forecast.regimeLabel)

        // Horizon probabilities
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Probabilità evento (±soglia)", style = MaterialTheme.typography.titleMedium)
                ProbBar("7 giorni", ux.horizonProbsPct["7d"] ?: 0f, Color(0xFF5B8DEF))
                ProbBar("14 giorni", ux.horizonProbsPct["14d"] ?: 0f, Color(0xFF3D6BC8))
                ProbBar("21 giorni", ux.horizonProbsPct["21d"] ?: 0f, Color(0xFF254A9B))
                Text(
                    "Magnitudine tipica ~${"%.1f".format(ux.expectedMovePct)}%",
                    style = MaterialTheme.typography.bodySmall
                )
            }
        }

        // Direction + scenario probs
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Bias e scenari", style = MaterialTheme.typography.titleMedium)
                Row(verticalAlignment = Alignment.CenterVertically) {
                    BiasArrow(ux.directionBias)
                    Spacer(modifier = Modifier.width(12.dp))
                    Text(
                        "Bias: ${ux.directionBiasIt}",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold
                    )
                }
                ProbBar("Scenario rialzo", ux.scenarioProbsPct["up"] ?: 0f, Color(0xFF2E7D32))
                ProbBar("Scenario ribasso", ux.scenarioProbsPct["down"] ?: 0f, Color(0xFFC62828))
                ProbBar("Scenario neutro", ux.scenarioProbsPct["neutral"] ?: 0f, Color(0xFF757575))
                Text(
                    "Scenari educativi (non probabilità di profitto).",
                    style = MaterialTheme.typography.labelSmall
                )
            }
        }

        // Calendar window timeline
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Finestra temporale", style = MaterialTheme.typography.titleMedium)
                WindowTimeline(forecast.windowStart, forecast.windowEnd, forecast.asOfDate)
                Text(ux.windowSummaryIt, style = MaterialTheme.typography.bodySmall)
            }
        }

        // Factor heatmap grid
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Heatmap fattori (intensità)", style = MaterialTheme.typography.titleMedium)
                Text(
                    "Griglia stile footprint sui parametri OHLCV — non order-flow tick.",
                    style = MaterialTheme.typography.labelSmall
                )
                FactorHeatmapGrid(ux.factorCells)
            }
        }

        Button(
            onClick = {
                onShare(
                    buildString {
                        appendLine("CryptoPredictions (${forecast.engine}) — simulation only")
                        appendLine("${forecast.assetSymbol} as-of ${forecast.asOfDate}")
                        appendLine("Pattern: ${ux.pattern.titleIt}")
                        appendLine(
                            "P14=${"%.0f".format(forecast.probability14d * 100)}% bias=${forecast.directionBias}"
                        )
                        appendLine("Window: ${forecast.mostProbableWindow}")
                    }
                )
            },
            modifier = Modifier.fillMaxWidth()
        ) { Text("Condividi sintesi") }

        Text(ux.disclaimer, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.error)
    }
}

@Composable
private fun ProbBar(label: String, pct: Float, color: Color) {
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(label, style = MaterialTheme.typography.bodySmall)
            Text("${"%.0f".format(pct)}%", style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold)
        }
        LinearProgressIndicator(
            progress = { (pct / 100f).coerceIn(0f, 1f) },
            modifier = Modifier.fillMaxWidth().height(10.dp),
            color = color,
            trackColor = MaterialTheme.colorScheme.surfaceVariant
        )
    }
}

@Composable
private fun PatternCardView(pattern: VolatilityUx.PatternCard, regime: String) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.secondaryContainer
        )
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            PatternArrowCanvas(pattern.arrow)
            Spacer(modifier = Modifier.width(12.dp))
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(pattern.titleIt, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Text(pattern.secondaryIt, style = MaterialTheme.typography.bodySmall)
                Text(pattern.projectionIt, style = MaterialTheme.typography.bodyMedium)
                Text(pattern.gamifiedHintIt, style = MaterialTheme.typography.labelSmall)
                Text("Regime tecnico: $regime", style = MaterialTheme.typography.labelSmall)
            }
        }
    }
}

@Composable
private fun PatternArrowCanvas(arrow: String) {
    val color = when (arrow) {
        "up" -> Color(0xFF2E7D32)
        "down" -> Color(0xFFC62828)
        "breakout" -> Color(0xFF1565C0)
        else -> Color(0xFF6A1B9A)
    }
    Canvas(modifier = Modifier.size(56.dp)) {
        val w = size.width
        val h = size.height
        when (arrow) {
            "up" -> {
                val path = Path().apply {
                    moveTo(w * 0.5f, h * 0.15f)
                    lineTo(w * 0.85f, h * 0.55f)
                    lineTo(w * 0.65f, h * 0.55f)
                    lineTo(w * 0.65f, h * 0.85f)
                    lineTo(w * 0.35f, h * 0.85f)
                    lineTo(w * 0.35f, h * 0.55f)
                    lineTo(w * 0.15f, h * 0.55f)
                    close()
                }
                drawPath(path, color)
            }
            "down" -> {
                val path = Path().apply {
                    moveTo(w * 0.5f, h * 0.85f)
                    lineTo(w * 0.85f, h * 0.45f)
                    lineTo(w * 0.65f, h * 0.45f)
                    lineTo(w * 0.65f, h * 0.15f)
                    lineTo(w * 0.35f, h * 0.15f)
                    lineTo(w * 0.35f, h * 0.45f)
                    lineTo(w * 0.15f, h * 0.45f)
                    close()
                }
                drawPath(path, color)
            }
            "breakout" -> {
                // Triangle pointing up-right (ascending triangle vibe)
                val path = Path().apply {
                    moveTo(w * 0.12f, h * 0.8f)
                    lineTo(w * 0.88f, h * 0.8f)
                    lineTo(w * 0.88f, h * 0.2f)
                    close()
                }
                drawPath(path, color.copy(alpha = 0.85f))
                drawLine(Color.White, Offset(w * 0.2f, h * 0.55f), Offset(w * 0.75f, h * 0.35f), strokeWidth = 4f)
            }
            else -> {
                // Sideways double arrow
                drawLine(color, Offset(w * 0.15f, h * 0.5f), Offset(w * 0.85f, h * 0.5f), strokeWidth = 6f)
                val left = Path().apply {
                    moveTo(w * 0.15f, h * 0.5f)
                    lineTo(w * 0.3f, h * 0.35f)
                    moveTo(w * 0.15f, h * 0.5f)
                    lineTo(w * 0.3f, h * 0.65f)
                }
                drawPath(left, color, style = Stroke(width = 6f))
                val right = Path().apply {
                    moveTo(w * 0.85f, h * 0.5f)
                    lineTo(w * 0.7f, h * 0.35f)
                    moveTo(w * 0.85f, h * 0.5f)
                    lineTo(w * 0.7f, h * 0.65f)
                }
                drawPath(right, color, style = Stroke(width = 6f))
            }
        }
    }
}

@Composable
private fun BiasArrow(bias: String) {
    PatternArrowCanvas(
        when (bias) {
            "up" -> "up"
            "down" -> "down"
            else -> "side"
        }
    )
}

@Composable
private fun WindowTimeline(start: String, end: String, asOf: String) {
    Canvas(
        modifier = Modifier
            .fillMaxWidth()
            .height(48.dp)
    ) {
        val y = size.height * 0.55f
        val pad = 16f
        drawLine(Color(0xFF90A4AE), Offset(pad, y), Offset(size.width - pad, y), strokeWidth = 4f)
        // as-of marker
        drawCircle(Color(0xFF455A64), radius = 8f, center = Offset(pad + 8f, y))
        // window band
        val x0 = size.width * 0.35f
        val x1 = size.width * 0.85f
        drawRect(
            Color(0xFF5B8DEF).copy(alpha = 0.35f),
            topLeft = Offset(x0, y - 14f),
            size = Size(x1 - x0, 28f)
        )
        drawCircle(Color(0xFF1565C0), radius = 7f, center = Offset(x0, y))
        drawCircle(Color(0xFF0D47A1), radius = 7f, center = Offset(x1, y))
    }
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text("Oggi\n$asOf", style = MaterialTheme.typography.labelSmall)
        Text("Inizio\n$start", style = MaterialTheme.typography.labelSmall)
        Text("Fine\n$end", style = MaterialTheme.typography.labelSmall)
    }
}

@Composable
private fun FactorHeatmapGrid(cells: List<VolatilityUx.FactorHeatCell>) {
    val rows = cells.chunked(4)
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        rows.forEach { row ->
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                row.forEach { cell ->
                    HeatCell(cell, Modifier.weight(1f))
                }
                // pad incomplete row
                repeat(4 - row.size) {
                    Spacer(modifier = Modifier.weight(1f))
                }
            }
        }
    }
}

@Composable
private fun HeatCell(cell: VolatilityUx.FactorHeatCell, modifier: Modifier = Modifier) {
    val bg = heatColor(cell.intensity)
    Box(
        modifier = modifier
            .aspectRatio(1.1f)
            .background(bg, RoundedCornerShape(8.dp))
            .padding(6.dp)
    ) {
        Column(
            modifier = Modifier.align(Alignment.Center),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                cell.labelIt,
                style = MaterialTheme.typography.labelSmall,
                color = Color.White,
                fontWeight = FontWeight.SemiBold
            )
            Text(
                cell.value?.let { formatVal(it) } ?: "—",
                style = MaterialTheme.typography.bodySmall,
                color = Color.White
            )
            Text(cell.chipIt, style = MaterialTheme.typography.labelSmall, color = Color.White.copy(alpha = 0.9f))
        }
    }
}

private fun formatVal(v: Double): String =
    if (abs(v) >= 100) "%.0f".format(v) else if (abs(v) >= 10) "%.1f".format(v) else "%.2f".format(v)

private fun heatColor(intensity: Float): Color {
    // Cool (teal) → warm (amber) → hot (red) — ATAS-like intensity feel
    val t = intensity.coerceIn(0f, 1f)
    return when {
        t < 0.33f -> Color(
            red = 0.15f + t * 0.3f,
            green = 0.45f + t * 0.2f,
            blue = 0.55f
        )
        t < 0.66f -> Color(
            red = 0.85f,
            green = 0.55f + (t - 0.33f),
            blue = 0.12f
        )
        else -> Color(
            red = 0.85f + (t - 0.66f) * 0.15f,
            green = 0.25f * (1f - (t - 0.66f) / 0.34f),
            blue = 0.1f
        )
    }
}
