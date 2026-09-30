#!/usr/bin/env bash
# Per-user install of the VoidLoop tarball (no root needed):  ./install.sh   (remove with: ./install.sh --uninstall)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
APP="${XDG_DATA_HOME:-$HOME/.local/share}/voidloop-app"
BIN="$HOME/.local/bin"
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICONS="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/512x512/apps"

if [ "${1:-}" = "--uninstall" ]; then
    rm -rf "$APP" "$BIN/voidloop" "$APPS/voidloop.desktop" "$ICONS/voidloop.png"
    echo "VoidLoop removed (your saves in ~/.local/share/voidloop are untouched)."
    exit 0
fi

mkdir -p "$APP" "$BIN" "$APPS" "$ICONS"
rm -rf "$APP"/*
cp -r "$HERE/VoidLoop/." "$APP/"
ln -sf "$APP/VoidLoop" "$BIN/voidloop"
cp "$HERE/voidloop.png" "$ICONS/voidloop.png"
sed "s|^Exec=.*|Exec=$APP/VoidLoop|" "$HERE/voidloop.desktop" > "$APPS/voidloop.desktop"
command -v update-desktop-database >/dev/null && update-desktop-database "$APPS" 2>/dev/null || true
echo "VoidLoop installed. Start it from your applications menu or run: voidloop"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "(add $BIN to your PATH to use the 'voidloop' command)";; esac
