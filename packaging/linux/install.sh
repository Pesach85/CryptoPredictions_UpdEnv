#!/usr/bin/env bash
# CryptoPredictions Linux installer — XDG desktop entry, icons, ~/.local/bin
# Dev-linked: config.repo_root points at this checkout; edits apply immediately.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
APP_ID="cryptopredictions"
APP_NAME="CryptoPredictions"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/cryptopredictions"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
BIN_DIR="$HOME/.local/bin"
PYTHON="${PYTHON:-}"

echo "==> CryptoPredictions Linux install (dev-linked)"
echo "    REPO_ROOT=$REPO_ROOT"

if [[ ! -d "$REPO_ROOT/services" ]]; then
  echo "ERROR: not a CryptoPredictions repo: $REPO_ROOT" >&2
  exit 1
fi

if [[ -z "$PYTHON" ]]; then
  if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    PYTHON="$REPO_ROOT/.venv/bin/python"
  else
    PYTHON="$(command -v python3)"
  fi
fi
echo "    PYTHON=$PYTHON"

"$PYTHON" "$REPO_ROOT/scripts/generate_icons.py"
ICON_SRC="$REPO_ROOT/packaging/icons/cryptopredictions.png"

mkdir -p "$CONFIG_DIR" "$BIN_DIR" \
  "$DATA_HOME/applications" \
  "$DATA_HOME/icons/hicolor/256x256/apps" \
  "$DATA_HOME/icons/hicolor/48x48/apps"

"$PYTHON" "$REPO_ROOT/scripts/write_install_config.py" \
  --config-dir "$CONFIG_DIR" \
  --repo-root "$REPO_ROOT" \
  --python "$PYTHON"

echo "==> pip install -e .[desktop]"
"$PYTHON" -m pip install -e "$REPO_ROOT[desktop]" --upgrade

cp -f "$ICON_SRC" "$DATA_HOME/icons/hicolor/256x256/apps/${APP_ID}.png"
if [[ -f "$REPO_ROOT/packaging/icons/cryptopredictions_48.png" ]]; then
  cp -f "$REPO_ROOT/packaging/icons/cryptopredictions_48.png" \
    "$DATA_HOME/icons/hicolor/48x48/apps/${APP_ID}.png"
fi

LAUNCHER="$BIN_DIR/$APP_ID"
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
export CRYPTOPREDICTIONS_ROOT="$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT\${PYTHONPATH:+:\$PYTHONPATH}"
exec "$PYTHON" -m cryptopredictions desktop "\$@"
EOF
chmod +x "$LAUNCHER"

DESKTOP_FILE="$DATA_HOME/applications/${APP_ID}.desktop"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=$APP_NAME
Comment=Crypto research projections (simulation only)
Exec=$LAUNCHER
Icon=$APP_ID
Terminal=false
Categories=Finance;Science;Education;
StartupWMClass=CryptoPredictions
Keywords=crypto;forecast;research;
EOF
chmod +x "$DESKTOP_FILE"

# Desktop shortcut (XDG user dir)
if command -v xdg-user-dir >/dev/null 2>&1; then
  DESKTOP_DIR="$(xdg-user-dir DESKTOP)"
else
  DESKTOP_DIR="$HOME/Desktop"
fi
if [[ -d "$DESKTOP_DIR" ]]; then
  cp -f "$DESKTOP_FILE" "$DESKTOP_DIR/${APP_NAME}.desktop"
  chmod +x "$DESKTOP_DIR/${APP_NAME}.desktop"
  # Mark trusted on GNOME if gio available
  if command -v gio >/dev/null 2>&1; then
    gio set "$DESKTOP_DIR/${APP_NAME}.desktop" metadata::trusted true 2>/dev/null || true
  fi
fi

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$DATA_HOME/applications" 2>/dev/null || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -f -t "$DATA_HOME/icons/hicolor" 2>/dev/null || true
fi

# Optional: user systemd unit for API (Linux-native, not web-only)
SYSTEMD_USER="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER"
cat > "$SYSTEMD_USER/cryptopredictions-api.service" <<EOF
[Unit]
Description=CryptoPredictions FastAPI (dev-linked)
After=network.target

[Service]
Type=simple
WorkingDirectory=$REPO_ROOT
Environment=CRYPTOPREDICTIONS_ROOT=$REPO_ROOT
Environment=PYTHONPATH=$REPO_ROOT
ExecStart=$PYTHON -m uvicorn api.main:app --host 127.0.0.1 --port 8000
Restart=on-failure

[Install]
WantedBy=default.target
EOF

cat > "$CONFIG_DIR/uninstall.meta" <<EOF
REPO_ROOT=$REPO_ROOT
DESKTOP_FILE=$DESKTOP_FILE
DESKTOP_LINK=$DESKTOP_DIR/${APP_NAME}.desktop
LAUNCHER=$LAUNCHER
SYSTEMD_UNIT=$SYSTEMD_USER/cryptopredictions-api.service
CONFIG_DIR=$CONFIG_DIR
EOF

echo "==> Install complete."
echo "    Launcher: $LAUNCHER"
echo "    Menu:     $DESKTOP_FILE"
echo "    Optional API service: systemctl --user enable --now cryptopredictions-api"
echo "    Uninstall: $REPO_ROOT/packaging/linux/uninstall.sh"
