# Lesson: volatility UX mirrors across platforms

When shipping radar UX (heatmaps, pattern cards, Italian lay copy), keep a single
semantic source of truth:

- Python: `services/volatility_ux.py` for desktop + Streamlit
- Kotlin mirror: `ui/VolatilityUx.kt` + Compose `VolatilityResultPanel.kt`

Do not invent tick-level footprint / bid-ask from daily OHLCV — use **parameter
intensity grids** instead. Always keep simulation-only disclaimer visible.
