import json
from pathlib import Path

from path_definition import ROOT_DIR

PROFILES_PATH = Path(ROOT_DIR) / "config" / "asset_profiles.json"
DATA_DIR = Path(ROOT_DIR) / "data"


def load_asset_profiles() -> dict:
    with open(PROFILES_PATH, encoding="utf-8") as fp:
        return json.load(fp)


def get_asset_profile(asset_symbol: str) -> dict:
    profiles = load_asset_profiles()
    symbol = asset_symbol.upper().strip()
    profile = profiles.get(symbol, profiles["default"]).copy()
    profile["asset_symbol"] = symbol
    return profile


def list_available_assets(interval: str = "1d") -> list[str]:
    suffix = f"-{interval}-data.csv"
    assets = []
    for path in sorted(DATA_DIR.glob(f"*{suffix}")):
        name = path.name.replace(suffix, "")
        assets.append(name)
    return assets


def resolve_data_path(asset_symbol: str, interval: str = "1d") -> Path:
    path = DATA_DIR / f"{asset_symbol.upper()}-{interval}-data.csv"
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    return path
