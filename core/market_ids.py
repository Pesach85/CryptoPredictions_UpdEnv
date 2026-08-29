"""Shared market id helpers."""

from __future__ import annotations

import requests


def sanitize_symbol(asset_symbol: str) -> str:
    return asset_symbol.upper().strip().replace("/", "")


def parse_assets(assets_arg: str) -> list[str]:
    assets = [sanitize_symbol(x) for x in assets_arg.split(",") if x.strip()]
    if not assets:
        raise ValueError("At least one asset must be provided.")
    return assets


COINGECKO_SYMBOL_TO_ID = {
    "BTC": "bitcoin",
    "XBT": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "ADA": "cardano",
    "XRP": "ripple",
    "DOGE": "dogecoin",
    "DOT": "polkadot",
    "LTC": "litecoin",
    "TRX": "tron",
    "AVAX": "avalanche-2",
    "LINK": "chainlink",
    "NEAR": "near",
    "APE": "apecoin",
    "CRO": "crypto-com-chain",
    "AXS": "axie-infinity",
    "EOS": "eos",
    "BCH": "bitcoin-cash",
    "PEPE": "pepe",
    "APT": "aptos",
}


def symbol_base(asset_symbol: str) -> str:
    symbol = asset_symbol.upper().strip()
    if symbol.endswith("USDT"):
        return symbol[:-4]
    if symbol.endswith("USD"):
        return symbol[:-3]
    return symbol


def resolve_coingecko_coin_id(asset_symbol: str) -> str:
    """Map asset symbol to CoinGecko coin id (local table, then API search)."""
    symbol = symbol_base(asset_symbol)

    if symbol in COINGECKO_SYMBOL_TO_ID:
        return COINGECKO_SYMBOL_TO_ID[symbol]

    search_url = "https://api.coingecko.com/api/v3/search"
    response = requests.get(search_url, params={"query": symbol}, timeout=30)
    response.raise_for_status()
    payload = response.json()

    for coin in payload.get("coins", []):
        if str(coin.get("symbol", "")).upper() == symbol:
            return str(coin["id"])

    raise ValueError(f"Unable to resolve CoinGecko id for symbol: {asset_symbol}")
