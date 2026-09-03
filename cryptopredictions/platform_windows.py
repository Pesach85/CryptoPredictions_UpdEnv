"""Windows-specific helpers: shortcuts, Start Menu, uninstall registry keys."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_windows() -> bool:
    return sys.platform.startswith("win")


def desktop_dir() -> Path:
    return Path.home() / "Desktop"


def start_menu_dir() -> Path:
    programs = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    target = programs / "CryptoPredictions"
    target.mkdir(parents=True, exist_ok=True)
    return target


def create_shortcut(path: Path, target: str, arguments: str = "", icon: str | None = None, working_dir: str | None = None) -> Path:
    """Create a .lnk via PowerShell (no pywin32 required)."""
    if not is_windows():
        raise RuntimeError("create_shortcut is Windows-only")
    path.parent.mkdir(parents=True, exist_ok=True)
    icon_line = f'$s.IconLocation = "{icon}"' if icon else ""
    wd_line = f'$s.WorkingDirectory = "{working_dir}"' if working_dir else ""
    ps = f"""
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut("{path}")
$s.TargetPath = "{target}"
$s.Arguments = "{arguments}"
{icon_line}
{wd_line}
$s.Save()
"""
    import subprocess

    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        check=True,
        capture_output=True,
        text=True,
    )
    return path


def remove_shortcut(path: Path) -> None:
    if path.exists():
        path.unlink()


def write_uninstall_marker(install_root: Path, version: str) -> Path:
    """Simple uninstall metadata under LocalAppData (no admin registry required)."""
    from cryptopredictions.paths import config_dir

    marker = config_dir() / "uninstall.json"
    import json
    from datetime import datetime, timezone

    marker.write_text(
        json.dumps(
            {
                "install_root": str(install_root),
                "version": version,
                "installed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "desktop_shortcut": str(desktop_dir() / "CryptoPredictions.lnk"),
                "start_menu": str(start_menu_dir()),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return marker
