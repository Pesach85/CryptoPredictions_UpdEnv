param(
    [int]$KeepHydraDays = 30,
    [int]$KeepMetaHistoricalDays = 45,
    [int]$KeepLatestHydraDates = 1,
    [int]$KeepLatestMetaDates = 1,
    [int]$KeepHydraRunsPerDate = 8,
    [int]$KeepMetaRunsPerDate = 4,
    [switch]$Execute
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$dryRun = -not $Execute
$now = Get-Date

$stats = [ordered]@{
    ItemsPlanned = 0
    BytesPlanned = 0L
    ItemsRemoved = 0
    BytesRemoved = 0L
}

function Get-DirectorySizeBytes {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return 0L
    }

    $files = Get-ChildItem -LiteralPath $Path -Recurse -Force -ErrorAction SilentlyContinue |
        Where-Object { -not $_.PSIsContainer }

    if ($null -eq $files -or $files.Count -eq 0) {
        return 0L
    }

    $measure = $files | Measure-Object -Property Length -Sum
    if ($null -eq $measure -or -not ($measure.PSObject.Properties.Name -contains 'Sum') -or $null -eq $measure.Sum) {
        return 0L
    }

    return [Int64]$measure.Sum
}

function Try-ParseDateFolder {
    param([Parameter(Mandatory = $true)][string]$Name)
    try {
        return [DateTime]::ParseExact($Name, 'yyyy-MM-dd', [System.Globalization.CultureInfo]::InvariantCulture)
    } catch {
        return $null
    }
}

function Is-ExcludedPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    $normalized = $Path.ToLowerInvariant()
    $excludedRoots = @(
        (Join-Path $repoRoot '.venv').ToLowerInvariant(),
        (Join-Path $repoRoot '.git').ToLowerInvariant()
    )

    foreach ($root in $excludedRoots) {
        if ($normalized.StartsWith($root)) {
            return $true
        }
    }

    return $false
}

function Register-Removal {
    param(
        [Parameter(Mandatory = $true)][string]$Target,
        [Parameter(Mandatory = $true)][Int64]$SizeBytes,
        [Parameter(Mandatory = $true)][string]$Reason,
        [switch]$IsDirectory
    )

    $script:stats.ItemsPlanned += 1
    $script:stats.BytesPlanned += $SizeBytes

    if ($dryRun) {
        Write-Host ("DRY-RUN  remove [{0}] ({1:N2} MB) - {2}" -f $Target, ($SizeBytes / 1MB), $Reason) -ForegroundColor Yellow
        return
    }

    if (-not (Test-Path -LiteralPath $Target)) {
        return
    }

    if ($IsDirectory) {
        Remove-Item -LiteralPath $Target -Recurse -Force
    } else {
        Remove-Item -LiteralPath $Target -Force
    }

    $script:stats.ItemsRemoved += 1
    $script:stats.BytesRemoved += $SizeBytes
    Write-Host ("REMOVED  [{0}] ({1:N2} MB) - {2}" -f $Target, ($SizeBytes / 1MB), $Reason) -ForegroundColor Green
}

function Cleanup-PythonCaches {
    Write-Host "\n==> Scanning Python caches" -ForegroundColor Cyan

    $pycacheDirs = Get-ChildItem -Path $repoRoot -Directory -Recurse -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq '__pycache__' -and -not (Is-ExcludedPath -Path $_.FullName) }

    foreach ($dir in $pycacheDirs) {
        $size = Get-DirectorySizeBytes -Path $dir.FullName
        Register-Removal -Target $dir.FullName -SizeBytes $size -Reason '__pycache__ directory' -IsDirectory
    }

    $compiledFiles = Get-ChildItem -Path $repoRoot -File -Recurse -Force -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Extension -in @('.pyc', '.pyo') -and
            -not (Is-ExcludedPath -Path $_.FullName) -and
            $_.DirectoryName -notlike '*__pycache__*'
        }

    foreach ($file in $compiledFiles) {
        Register-Removal -Target $file.FullName -SizeBytes ([Int64]$file.Length) -Reason 'compiled python file'
    }
}

function Get-PreservedMetaHistoricalRuns {
    $preserved = @{}
    $readmePath = Join-Path $repoRoot 'README.md'
    if (-not (Test-Path -LiteralPath $readmePath)) {
        return $preserved
    }

    $pattern = 'outputs/meta_historical/\d{4}-\d{2}-\d{2}/\d{2}-\d{2}-\d{2}'
    $matches = Select-String -Path $readmePath -Pattern $pattern -AllMatches
    foreach ($line in $matches) {
        foreach ($match in $line.Matches) {
            $relative = $match.Value -replace '/', [string][IO.Path]::DirectorySeparatorChar
            $full = Join-Path $repoRoot $relative
            $preserved[$full.ToLowerInvariant()] = $true
        }
    }

    return $preserved
}

function Cleanup-TimeRunsInDatedFolders {
    param(
        [Parameter(Mandatory = $true)][string]$RootPath,
        [Parameter(Mandatory = $true)][int]$KeepRunsPerDate,
        [Parameter(Mandatory = $true)][string]$Label,
        [hashtable]$PreserveMap
    )

    if (-not (Test-Path -LiteralPath $RootPath)) {
        return
    }

    Write-Host ("\n==> Pruning per-date runs in {0}" -f $Label) -ForegroundColor Cyan

    foreach ($dateDir in (Get-ChildItem -LiteralPath $RootPath -Directory -Force -ErrorAction SilentlyContinue)) {
        if ($null -eq (Try-ParseDateFolder -Name $dateDir.Name)) {
            continue
        }

        $timeRuns = @()
        foreach ($runDir in (Get-ChildItem -LiteralPath $dateDir.FullName -Directory -Force -ErrorAction SilentlyContinue)) {
            if ($runDir.Name -match '^\d{2}-\d{2}-\d{2}$') {
                $timeRuns += $runDir
            }
        }

        if ($timeRuns.Count -le $KeepRunsPerDate) {
            continue
        }

        $sortedRuns = $timeRuns | Sort-Object Name -Descending
        $keepSet = @{}
        foreach ($keepRun in ($sortedRuns | Select-Object -First $KeepRunsPerDate)) {
            $keepSet[$keepRun.FullName.ToLowerInvariant()] = $true
        }

        foreach ($run in $sortedRuns) {
            $runKey = $run.FullName.ToLowerInvariant()
            if ($keepSet.ContainsKey($runKey)) {
                continue
            }
            if ($null -ne $PreserveMap -and $PreserveMap.ContainsKey($runKey)) {
                continue
            }

            $size = Get-DirectorySizeBytes -Path $run.FullName
            Register-Removal -Target $run.FullName -SizeBytes $size -Reason ("stale {0} run folder" -f $Label) -IsDirectory
        }
    }
}

function Cleanup-DatedOutputs {
    param(
        [Parameter(Mandatory = $true)][string]$RootPath,
        [Parameter(Mandatory = $true)][int]$KeepDays,
        [Parameter(Mandatory = $true)][int]$KeepLatestDates,
        [Parameter(Mandatory = $true)][string]$Label
    )

    if (-not (Test-Path -LiteralPath $RootPath)) {
        return
    }

    Write-Host ("\n==> Scanning {0}" -f $Label) -ForegroundColor Cyan

    $dateFolders = @()
    foreach ($dir in (Get-ChildItem -LiteralPath $RootPath -Directory -Force -ErrorAction SilentlyContinue)) {
        $parsedDate = Try-ParseDateFolder -Name $dir.Name
        if ($null -ne $parsedDate) {
            $dateFolders += [PSCustomObject]@{
                Directory = $dir
                Date = $parsedDate.Date
            }
        }
    }

    if ($dateFolders.Count -eq 0) {
        return
    }

    $sorted = $dateFolders | Sort-Object Date -Descending
    $keep = @($sorted | Select-Object -First $KeepLatestDates)
    $keepPaths = @{}
    foreach ($item in $keep) {
        $keepPaths[$item.Directory.FullName] = $true
    }

    $cutoff = $now.Date.AddDays(-1 * $KeepDays)

    foreach ($item in $sorted) {
        $fullPath = $item.Directory.FullName
        if ($keepPaths.ContainsKey($fullPath)) {
            continue
        }
        if ($item.Date -ge $cutoff) {
            continue
        }

        $size = Get-DirectorySizeBytes -Path $fullPath
        Register-Removal -Target $fullPath -SizeBytes $size -Reason ("{0} older than {1} days" -f $Label, $KeepDays) -IsDirectory
    }
}

function Cleanup-EmptyDirectories {
    Write-Host "\n==> Scanning empty directories" -ForegroundColor Cyan

    $emptyDirs = Get-ChildItem -Path $repoRoot -Directory -Recurse -Force -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending |
        Where-Object {
            -not (Is-ExcludedPath -Path $_.FullName) -and
            (Get-ChildItem -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue | Measure-Object).Count -eq 0
        }

    foreach ($dir in $emptyDirs) {
        Register-Removal -Target $dir.FullName -SizeBytes 0 -Reason 'empty directory' -IsDirectory
    }
}

Write-Host ("Safe cleanup started at {0}. Mode: {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $(if ($dryRun) { 'DRY-RUN' } else { 'EXECUTE' })) -ForegroundColor Magenta

Cleanup-PythonCaches

$outputsRoot = Join-Path $repoRoot 'outputs'
Cleanup-DatedOutputs -RootPath $outputsRoot -KeepDays $KeepHydraDays -KeepLatestDates $KeepLatestHydraDates -Label 'Hydra outputs'

$metaHistoricalRoot = Join-Path $outputsRoot 'meta_historical'
Cleanup-DatedOutputs -RootPath $metaHistoricalRoot -KeepDays $KeepMetaHistoricalDays -KeepLatestDates $KeepLatestMetaDates -Label 'Meta-historical outputs'

Cleanup-TimeRunsInDatedFolders -RootPath $outputsRoot -KeepRunsPerDate $KeepHydraRunsPerDate -Label 'Hydra outputs'

$preservedMetaRuns = Get-PreservedMetaHistoricalRuns
Cleanup-TimeRunsInDatedFolders -RootPath $metaHistoricalRoot -KeepRunsPerDate $KeepMetaRunsPerDate -Label 'Meta-historical outputs' -PreserveMap $preservedMetaRuns

Cleanup-EmptyDirectories

Write-Host "\n==> Summary" -ForegroundColor Cyan
Write-Host ("Planned removals : {0} items" -f $stats.ItemsPlanned)
Write-Host ("Planned space    : {0:N2} MB" -f ($stats.BytesPlanned / 1MB))

if ($dryRun) {
    Write-Host "No changes were applied. Re-run with -Execute to apply cleanup." -ForegroundColor Yellow
} else {
    Write-Host ("Removed items    : {0}" -f $stats.ItemsRemoved)
    Write-Host ("Freed space      : {0:N2} MB" -f ($stats.BytesRemoved / 1MB))
}
