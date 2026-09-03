"""Write installer config.json (called from packaging/*/install.*)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config-dir", required=True)
    p.add_argument("--repo-root", required=True)
    p.add_argument("--python", required=True)
    args = p.parse_args()
    cfg_dir = Path(args.config_dir)
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg = {
        "mode": "dev-linked",
        "repo_root": str(Path(args.repo_root).resolve()),
        "python_executable": str(Path(args.python).resolve()),
        "api_host": "127.0.0.1",
        "api_port": 8000,
        "streamlit_port": 8501,
        "auto_start_api": True,
        "auto_start_streamlit": False,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "notes": "Simulation only - not investment advice.",
    }
    (cfg_dir / "config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print(cfg_dir / "config.json")


if __name__ == "__main__":
    main()
