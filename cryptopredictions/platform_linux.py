"""Linux-specific helpers: XDG .desktop, icons, notify-send, tray path."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def xdg_data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))


def xdg_bin_home() -> Path:
    return Path.home() / ".local" / "bin"


def applications_dir() -> Path:
    d = xdg_data_home() / "applications"
    d.mkdir(parents=True, exist_ok=True)
    return d


def icons_dir(size: str = "256x256") -> Path:
    d = xdg_data_home() / "icons" / "hicolor" / size / "apps"
    d.mkdir(parents=True, exist_ok=True)
    return d


def desktop_dir() -> Path:
    # Prefer xdg-user-dir DESKTOP
    try:
        out = subprocess.check_output(["xdg-user-dir", "DESKTOP"], text=True).strip()
        if out:
            return Path(out)
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    return Path.home() / "Desktop"


def write_desktop_file(
    path: Path,
    *,
    name: str,
    exec_cmd: str,
    icon: str,
    comment: str = "CryptoPredictions research toolbox",
    categories: str = "Finance;Science;Education;",
    terminal: bool = False,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f"""[Desktop Entry]
Type=Application
Version=1.0
Name={name}
Comment={comment}
Exec={exec_cmd}
Icon={icon}
Terminal={"true" if terminal else "false"}
Categories={categories}
StartupWMClass=CryptoPredictions
Keywords=crypto;forecast;research;
"""
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def install_icon(src: Path, name: str = "cryptopredictions") -> Path:
    dest = icons_dir() / f"{name}.png"
    shutil.copy2(src, dest)
    # Update icon cache if tool exists
    try:
        subprocess.run(
            ["gtk-update-icon-cache", "-f", "-t", str(xdg_data_home() / "icons" / "hicolor")],
            check=False,
            capture_output=True,
        )
    except FileNotFoundError:
        pass
    return dest


def notify(title: str, body: str, icon: str | None = None) -> None:
    """Desktop notification via libnotify (notify-send)."""
    if not is_linux():
        return
    cmd = ["notify-send", title, body]
    if icon:
        cmd.extend(["-i", icon])
    try:
        subprocess.run(cmd, check=False)
    except FileNotFoundError:
        pass


def ensure_path_bin_symlink(target: Path, name: str = "cryptopredictions") -> Path:
    bin_dir = xdg_bin_home()
    bin_dir.mkdir(parents=True, exist_ok=True)
    link = bin_dir / name
    if link.exists() or link.is_symlink():
        link.unlink()
    link.symlink_to(target)
    return link
