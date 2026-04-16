param(
    [switch]$RunAll
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found at $pythonExe. Configure the virtual environment first."
}

$runs = @()
if ($RunAll) {
    $runs = @(
        "meta_historical_test.py --assets ETHUSD,XBTUSD,SOLUSD,ADAUSD,LTCUSD,BCHUSD --train-cutoff 2025-12-31 --min-samples 50 --max-mape 5.0 --n-estimators 300",
        "meta_historical_test.py --assets XBTUSD,LTCUSD --train-cutoff 2025-12-31 --min-samples 50 --max-mape 5.0 --n-estimators 300 --features close --lags 30",
        "meta_historical_test.py --assets ETHUSD,ADAUSD,BCHUSD --train-cutoff 2025-12-31 --min-samples 50 --max-mape 5.0 --n-estimators 300 --features close --lags 14",
        "meta_historical_test.py --assets SOLUSD --train-cutoff 2025-12-31 --min-samples 50 --max-mape 5.0 --n-estimators 300 --features focused --lags 14"
    )

    foreach ($cmdArgs in $runs) {
        Write-Host "`n==> Running: $cmdArgs" -ForegroundColor Cyan
        & $pythonExe $cmdArgs.Split(' ')
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed with exit code ${LASTEXITCODE}: $cmdArgs"
        }
    }

    Write-Host "`n==> Building divergence chart" -ForegroundColor Cyan
    & $pythonExe "divergence_visualization.py"
    if ($LASTEXITCODE -ne 0) {
        throw "divergence_visualization.py failed with exit code ${LASTEXITCODE}"
    }
} else {
    Write-Host "`nSkipping model reruns. Use -RunAll to rebuild all 2026 artifacts." -ForegroundColor Yellow
}

$expectedCharts = @(
    "outputs/meta_historical/2026-04-16/14-55-45/LTCUSD/price_prediction_chart.png",
    "outputs/meta_historical/2026-04-16/14-59-21/ETHUSD/price_prediction_chart.png",
    "outputs/meta_historical/best_asset_divergence_analysis.png"
)

$missing = @()
foreach ($chart in $expectedCharts) {
    if (-not (Test-Path $chart)) {
        $missing += $chart
    }
}

if ($missing.Count -gt 0) {
    Write-Host "`nMissing chart artifacts:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
    throw "README chart validation failed."
}

Write-Host "`nAll README-referenced 2026 chart artifacts are present." -ForegroundColor Green
$expectedCharts | ForEach-Object { Write-Host " - $_" }
