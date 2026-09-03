package com.cryptopredictions.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val Teal = Color(0xFF1971C2)
private val DarkBg = Color(0xFF121A22)

private val Light = lightColorScheme(primary = Teal)
private val Dark = darkColorScheme(primary = Teal, background = DarkBg, surface = DarkBg)

@Composable
fun CpTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (isSystemInDarkTheme()) Dark else Light,
        content = content
    )
}
