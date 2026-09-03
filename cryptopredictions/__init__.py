"""
CryptoPredictions — installable application package.

Modes
-----
dev-linked (default in development installs)
    Launcher reads config.repo_root and imports live source. Code edits are
    available immediately without reinstalling the desktop shortcuts.
frozen
    Future PyInstaller/Briefcase bundle; config.repo_root may be null.
"""

from __future__ import annotations

__version__ = "1.1.0"
__app_name__ = "CryptoPredictions"
__app_id__ = "com.cryptopredictions.app"
