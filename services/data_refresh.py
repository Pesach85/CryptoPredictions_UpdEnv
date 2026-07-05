"""Incremental OHLCV refresh via public APIs with manual/stealth-browser fallback."""

from __future__ import annotations

import json
import shutil
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from meta_historical_test import load_local_ohlcv, resolve_coingecko_coin_id, sanitize_symbol
from path_definition import ROOT_DIR
from services.assets import list_available_assets, resolve_data_path
from services.stealth_capture import capture_to_import_csv, load_capture_file
from services.yahoo_fetch import asset_to_yahoo_ticker, fetch_yahoo_daily_ohlcv

DATA_DIR = Path(ROOT_DIR) / "data"
REFRESH_LOG = Path(ROOT_DIR) / "outputs" / "data_refresh"
CAPTURE_DIR = REFRESH_LOG
DEFAULT_DELAY_SEC = 1.5


def _csv_timestamp_col(df: pd.DataFrame) -> str:
    for candidate in ["timestamp", "Date", "date", "datetime"]:
        for col in df.columns:
            if col.lower() == candidate.lower():
                return col
    return df.columns[0]


def _ohlcv_to_csv_rows(ohlcv: pd.DataFrame) -> pd.DataFrame:
    out = ohlcv.reset_index().rename(columns={"date": "timestamp"})
    out["timestamp"] = pd.to_datetime(out["timestamp"]).dt.strftime("%Y-%m-%d 00:00:00")
    return out[["timestamp", "open", "high", "low", "close", "volume"]]


def merge_ohlcv_into_csv(asset_symbol: str, new_ohlcv: pd.DataFrame, backup: bool = True) -> dict[str, Any]:
    symbol = sanitize_symbol(asset_symbol)
    csv_path = resolve_data_path(symbol)
    if backup:
        backup_path = csv_path.with_suffix(f".bak_{datetime.utcnow().strftime('%Y%m%d')}")
        shutil.copy2(csv_path, backup_path)

    local = load_local_ohlcv(csv_path)
    combined = pd.concat([local, new_ohlcv])
    combined = combined[~combined.index.duplicated(keep="last")].sort_index()
    merged = _ohlcv_to_csv_rows(combined)

    raw = pd.read_csv(csv_path)
    ts_col = _csv_timestamp_col(raw)
    if ts_col != "timestamp":
        merged = merged.rename(columns={"timestamp": ts_col})

    col_map = {c.lower(): c for c in raw.columns}
    for std_col in ["open", "high", "low", "close", "volume"]:
        if std_col in merged.columns and std_col in col_map and col_map[std_col] != std_col:
            merged = merged.rename(columns={std_col: col_map[std_col]})

    merged.to_csv(csv_path, index=False)
    return {
        "asset": symbol,
        "csv_path": str(csv_path),
        "rows_before": int(len(local)),
        "rows_after": int(len(combined)),
        "new_rows": int(len(combined) - len(local)),
        "start": str(combined.index.min().date()),
        "end": str(combined.index.max().date()),
    }


def _close_series_to_ohlcv(close_series: pd.Series, last_volume: float, last_close: float) -> pd.DataFrame:
    rows = []
    prev = last_close
    for dt, close in close_series.items():
        close = float(close)
        daily_ret = (close / prev) - 1.0 if prev else 0.0
        spread = abs(daily_ret) * 0.25
        rows.append(
            {
                "date": dt,
                "open": prev,
                "high": max(prev, close) * (1 + spread),
                "low": min(prev, close) * (1 - spread),
                "close": close,
                "volume": last_volume,
            }
        )
        prev = close
    return pd.DataFrame(rows).set_index("date")


def refresh_asset_via_api(asset_symbol: str, backup: bool = True) -> dict[str, Any]:
    symbol = sanitize_symbol(asset_symbol)
    local = load_local_ohlcv(resolve_data_path(symbol))
    last_date = local.index.max()
    start = last_date + timedelta(days=1)
    end = datetime.now(timezone.utc)
    if start.date() >= end.date():
        return {"asset": symbol, "status": "already_current", "end": str(last_date.date())}

    errors: list[str] = []

    # Attempt 1: Yahoo Finance OHLCV (most reliable for bulk refresh)
    try:
        ticker = asset_to_yahoo_ticker(symbol)
        new_data = fetch_yahoo_daily_ohlcv(ticker, start.to_pydatetime(), end)
        new_data = new_data[new_data.index > last_date]
        if not new_data.empty:
            result = merge_ohlcv_into_csv(symbol, new_data, backup=backup)
            result["status"] = "updated"
            result["source"] = f"yahoo_ohlcv:{ticker}"
            return result
        errors.append(f"yahoo:{ticker} returned no rows after {last_date.date()}")
    except Exception as exc:
        errors.append(f"yahoo: {exc}")

    # Attempt 2: CoinGecko close → synthetic OHLCV
    try:
        from meta_historical_test import fetch_api_daily_close

        coin_id = resolve_coingecko_coin_id(symbol)
        close_series = fetch_api_daily_close(coin_id, start.to_pydatetime(), end)
        close_series = close_series[close_series.index > last_date]
        if not close_series.empty:
            new_data = _close_series_to_ohlcv(
                close_series,
                last_volume=float(local["volume"].iloc[-1]),
                last_close=float(local["close"].iloc[-1]),
            )
            result = merge_ohlcv_into_csv(symbol, new_data, backup=backup)
            result["status"] = "updated"
            result["source"] = "coingecko_close_synthetic_ohlcv"
            result["warnings"] = errors
            return result
    except Exception as exc:
        errors.append(f"coingecko: {exc}")

    result = {
        "asset": symbol,
        "status": "error",
        "error": "; ".join(errors),
        "stealth_capture_path": str(CAPTURE_DIR / f"{symbol}_capture.json"),
        "stealth_hint": (
            f"Save Yahoo chart JSON to {CAPTURE_DIR / f'{symbol}_capture.json'} then run: "
            f"python scripts/refresh_market_data.py --asset {symbol} --import-json {CAPTURE_DIR / f'{symbol}_capture.json'}"
        ),
    }
    return result


def import_ohlcv_from_file(asset_symbol: str, import_path: str | Path, backup: bool = True) -> dict[str, Any]:
    """Import rows from CSV or stealth-browser JSON capture."""
    path = Path(import_path)
    if not path.exists():
        available = sorted(CAPTURE_DIR.glob("*.json")) if CAPTURE_DIR.exists() else []
        available_hint = "\n".join(f"  - {p.name}" for p in available[:10]) or "  (none — save capture from stealth-browser first)"
        raise FileNotFoundError(
            f"Import file not found: {path.resolve()}\n"
            f"ETHUSD is likely already current — try: python scripts/refresh_market_data.py --asset ETHUSD\n"
            f"Files in {CAPTURE_DIR}:\n{available_hint}\n"
            f"Example test file: outputs/data_refresh/ETHUSD_capture.example.json"
        )

    if path.suffix.lower() == ".json":
        ohlcv = load_capture_file(path)
    else:
        imported = pd.read_csv(path)
        ts_col = _csv_timestamp_col(imported)
        imported["_ts"] = pd.to_datetime(imported[ts_col], utc=True, errors="coerce")
        imported = imported.dropna(subset=["_ts"])
        imported["date"] = imported["_ts"].dt.tz_convert(None).dt.floor("D")
        close_col = next((c for c in imported.columns if c.lower() == "close"), None)
        if close_col is None:
            raise ValueError("Import CSV must include a close column.")
        ohlcv = imported.groupby("date", as_index=True).agg(
            open=(next((c for c in imported.columns if c.lower() == "open"), close_col), "first"),
            high=(next((c for c in imported.columns if c.lower() == "high"), close_col), "max"),
            low=(next((c for c in imported.columns if c.lower() == "low"), close_col), "min"),
            close=(close_col, "last"),
            volume=(next((c for c in imported.columns if c.lower() == "volume"), close_col), "sum"),
        ).astype(float)

    result = merge_ohlcv_into_csv(asset_symbol, ohlcv, backup=backup)
    result["status"] = "imported"
    result["source"] = str(path.resolve())
    return result


def import_stealth_capture_json(
    asset_symbol: str,
    json_path: str | Path,
    backup: bool = True,
    save_csv: bool = True,
) -> dict[str, Any]:
    path = Path(json_path)
    ohlcv = load_capture_file(path)
    csv_path = None
    if save_csv:
        csv_path = capture_to_import_csv(ohlcv, CAPTURE_DIR / f"{sanitize_symbol(asset_symbol)}_import.csv")
    result = merge_ohlcv_into_csv(asset_symbol, ohlcv, backup=backup)
    result["status"] = "imported"
    result["source"] = str(path.resolve())
    if csv_path:
        result["converted_csv"] = str(csv_path)
    return result


def refresh_all_assets(
    assets: list[str] | None = None,
    backup: bool = True,
    delay_sec: float = DEFAULT_DELAY_SEC,
) -> list[dict[str, Any]]:
    targets = assets or list_available_assets()
    results = []
    for i, asset in enumerate(targets):
        if i > 0 and delay_sec > 0:
            time.sleep(delay_sec)
        results.append(refresh_asset_via_api(asset, backup=backup))
    REFRESH_LOG.mkdir(parents=True, exist_ok=True)
    log_path = REFRESH_LOG / f"refresh_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_path, "w", encoding="utf-8") as fp:
        json.dump(results, fp, indent=2)
    return results


def refresh_status() -> list[dict[str, Any]]:
    today = datetime.now(timezone.utc).date()
    rows = []
    for asset in list_available_assets():
        local = load_local_ohlcv(resolve_data_path(asset))
        end = local.index.max().date()
        rows.append(
            {
                "asset": asset,
                "end": str(end),
                "gap_days": (today - end).days,
                "needs_refresh": end < today,
            }
        )
    return rows


def stealth_browser_instructions(asset_symbol: str) -> str:
    symbol = sanitize_symbol(asset_symbol)
    capture_json = CAPTURE_DIR / f"{symbol}_capture.json"
    import_csv = CAPTURE_DIR / f"{symbol}_import.csv"
    example = CAPTURE_DIR / f"{symbol}_capture.example.json"
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    return f"""
Stealth-browser fallback for {symbol} (only when API refresh returns status=error):

PREREQUISITE: file must exist before import — {capture_json}

1. spawn_browser() → navigate to https://finance.yahoo.com/quote/{asset_to_yahoo_ticker(symbol)}
2. list_network_requests() → find chart/v8/finance/chart JSON
3. Save response body to: {capture_json}
4. Import:
   python scripts/refresh_market_data.py --asset {symbol} --import-json {capture_json}

Test parser with example (does not update real data meaningfully):
   python scripts/convert_stealth_capture.py --input {example} --preview

API refresh (try first):
   python scripts/refresh_market_data.py --asset {symbol}

See .cursor/skills/stealth-browser-market-data/SKILL.md
"""


def list_capture_files() -> list[str]:
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    return [str(p) for p in sorted(CAPTURE_DIR.glob("*.json"))]
