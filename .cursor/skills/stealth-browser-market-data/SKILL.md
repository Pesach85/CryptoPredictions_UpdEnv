---
name: stealth-browser-market-data
description: >-
  Fetches crypto market data from anti-bot protected websites using stealth-browser-mcp.
  Use when CoinGecko/CryptoCompare APIs are rate-limited, when scraping exchange pages,
  or when the user references stealth-browser-mcp for live price data collection.
---

# Stealth Browser Market Data

## When to use

- API rate limits block `meta_historical_test.py` fetches
- Need OHLCV from exchange pages behind Cloudflare
- Reverse-engineering chart API endpoints on protected sites

**Repo:** https://github.com/vibheksoni/stealth-browser-mcp

## MCP setup (Windows)

```powershell
git clone https://github.com/vibheksoni/stealth-browser-mcp.git
cd stealth-browser-mcp
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Add to Cursor MCP config (`%APPDATA%\Cursor\User\globalStorage\cursor.mcp\mcp.json` or project `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "stealth-browser-mcp": {
      "command": "C:\\path\\to\\stealth-browser-mcp\\venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\stealth-browser-mcp\\src\\server.py", "--minimal"],
      "env": {
        "BROWSER_IDLE_TIMEOUT": "600"
      }
    }
  }
}
```

Use `--minimal` (20 tools) unless full network debugging is needed.

## Recommended tool flow

1. `spawn_browser()` — create instance
2. `navigate(url)` — target exchange or aggregator
3. `wait_for_element(selector)` — ensure page loaded
4. `list_network_requests()` — capture XHR/fetch with price data
5. `get_response_content(request_id)` — extract JSON payloads
6. `close_instance()` — always cleanup

For repeated API patterns, use `create_dynamic_hook()` to intercept and log responses.

## Integration with CryptoPredictions

1. Save JSON capture to `outputs/data_refresh/<ASSET>_capture.json`
2. Import directly (preferred):
   ```bash
   python scripts/refresh_market_data.py --asset ETHUSD --import-json outputs/data_refresh/ETHUSD_capture.json
   ```
3. Or convert first, then import CSV:
   ```bash
   python scripts/convert_stealth_capture.py --input outputs/data_refresh/ETHUSD_capture.json
   python scripts/refresh_market_data.py --asset ETHUSD --import-csv outputs/data_refresh/ETHUSD_import.csv
   ```
4. Re-run `meta_historical_test.py` or `project_forward.py`
5. Log source and fetch date in `Documents/KB.md`

**Note:** `capture.csv` in docs is a placeholder path — use real files under `outputs/data_refresh/`.

## Data schema (local CSV)

```
timestamp,open,high,low,close,volume
```

Normalize to daily bars before writing — see `meta_historical_test.load_local_ohlcv`.

## Guardrails

- Respect site terms of service and rate limits
- Never store credentials in repo
- Cache responses locally to avoid repeated scraping
- Frame all downstream use as research simulation, not trading advice
- Prefer public APIs (CoinGecko, CryptoCompare, Yahoo) before stealth scraping

## Skill from upstream repo

Upstream ships `skills/stealth-browser-mcp/SKILL.md` with full 97-tool reference. Symlink or copy into `~/.cursor/skills/` if needed.
