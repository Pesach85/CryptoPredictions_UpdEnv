"""Shared market id helpers."""

from __future__ import annotations


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
