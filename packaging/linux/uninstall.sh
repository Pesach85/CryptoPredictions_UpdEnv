#!/usr/bin/env bash
# CryptoPredictions Linux uninstaller — removes XDG entries, launcher, config.
# Does NOT delete the git repository.
set -euo pipefail

APP_ID="cryptopredictions"
APP_NAME="CryptoPredictions"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/cryptopredictions"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
BIN_DIR="$HOME/.local/bin"

echo "==> CryptoPredictions Linux uninstall"

if [[ -f "$CONFIG_DIR/uninstall.meta" ]]; then
  # shellcheck disable=SC1090
  source "$CONFIG_DIR/uninstall.meta"
fi

systemctl --user disable --now cryptopredictions-api 2>/dev/null || true
rm -f "${SYSTEMD_UNIT:-$HOME/.config/systemd/user/cryptopredictions-api.service}"
rm -f "${LAUNCHER:-$BIN_DIR/$APP_ID}"
rm -f "${DESKTOP_FILE:-$DATA_HOME/applications/${APP_ID}.desktop}"

if command -v xdg-user-dir >/dev/null 2>&1; then
  DESKTOP_DIR="$(xdg-user-dir DESKTOP)"
else
  DESKTOP_DIR="$HOME/Desktop"
fi
rm -f "$DESKTOP_DIR/${APP_NAME}.desktop"
rm -f "$DATA_HOME/icons/hicolor/256x256/apps/${APP_ID}.png"
rm -f "$DATA_HOME/icons/hicolor/48x48/apps/${APP_ID}.png"

python3 -m pip uninstall -y cryptopredictions 2>/dev/null || true
rm -rf "$CONFIG_DIR"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$DATA_HOME/applications" 2>/dev/null || true
fi

echo "==> Uninstall complete. Source repo retained."
