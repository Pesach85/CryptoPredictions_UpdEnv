"""Platform paths, config persistence, and live-repo resolution."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal


Mode = Literal["dev-linked", "frozen"]


@dataclass
class AppConfig:
    mode: Mode = "dev-linked"
    repo_root: str | None = None
    python_executable: str | None = None
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    streamlit_port: int = 8501
    auto_start_api: bool = True
    auto_start_streamlit: bool = False
    created_at: str = ""
    notes: str = "Simulation only — not investment advice."

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


def platform_name() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform == "darwin":
        return "macos"
    return sys.platform


def config_dir() -> Path:
    """XDG on Linux, LocalAppData on Windows, ~/Library on macOS."""
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "CryptoPredictions"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "CryptoPredictions"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "cryptopredictions"
    return Path.home() / ".config" / "cryptopredictions"


def data_dir() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "CryptoPredictions" / "data"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "CryptoPredictions" / "data"
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "cryptopredictions"
    return Path.home() / ".local" / "share" / "cryptopredictions"


def cache_dir() -> Path:
    if sys.platform.startswith("win"):
        return config_dir() / "cache"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "CryptoPredictions"
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg) / "cryptopredictions"
    return Path.home() / ".cache" / "cryptopredictions"


def config_path() -> Path:
    return config_dir() / "config.json"


def load_config() -> AppConfig:
    path = config_path()
    if not path.exists():
        return AppConfig()
    try:
        # utf-8-sig: Windows PowerShell Set-Content -Encoding UTF8 writes BOM
        return AppConfig.from_dict(json.loads(path.read_text(encoding="utf-8-sig")))
    except (json.JSONDecodeError, TypeError, ValueError):
        return AppConfig()


def save_config(cfg: AppConfig) -> Path:
    d = config_dir()
    d.mkdir(parents=True, exist_ok=True)
    path = config_path()
    path.write_text(json.dumps(cfg.to_dict(), indent=2), encoding="utf-8")
    return path


def discover_repo_root(explicit: str | Path | None = None) -> Path:
    """Resolve live codebase root for dev-linked mode."""
    if explicit:
        p = Path(explicit).resolve()
        if (p / "services").is_dir() and (p / "api").is_dir():
            return p
        raise FileNotFoundError(f"Not a CryptoPredictions repo: {p}")

    env = os.environ.get("CRYPTOPREDICTIONS_ROOT")
    if env:
        return discover_repo_root(env)

    cfg = load_config()
    if cfg.repo_root:
        return discover_repo_root(cfg.repo_root)

    # Walk up from this file: cryptopredictions/paths.py -> repo root
    here = Path(__file__).resolve().parent.parent
    if (here / "services").is_dir() and (here / "api").is_dir():
        return here

    raise FileNotFoundError(
        "Cannot locate CryptoPredictions repo. Set CRYPTOPREDICTIONS_ROOT "
        "or run packaging installer in dev-linked mode."
    )


def ensure_sys_path(repo_root: Path | None = None) -> Path:
    """Insert live repo on sys.path so installed launcher uses current source."""
    root = repo_root or discover_repo_root()
    root_s = str(root)
    if root_s not in sys.path:
        sys.path.insert(0, root_s)
    os.environ.setdefault("CRYPTOPREDICTIONS_ROOT", root_s)
    os.environ.setdefault("PYTHONPATH", root_s)
    return root
