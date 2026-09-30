#!/usr/bin/env bash
# Build the Linux packages of VoidLoop.
#
#   packaging/linux/build.sh [pyinstaller|tar|deb|appimage|all]      (default: all)
#
# Output goes to ./out. Needs Python 3.8+ with `pip install -r requirements.txt pyinstaller`,
# dpkg-deb for the .deb, and (for the AppImage) either FUSE or APPIMAGE_EXTRACT_AND_RUN=1.
set -euo pipefail

cd "$(dirname "$0")/../.."
ROOT="$PWD"
VERSION="$(python3 -c "import re;print(re.search(r'__version__ = \"([^\"]+)\"', open('VoidLoop/__init__.py').read()).group(1))")"
ARCH="$(uname -m)"
case "$ARCH" in x86_64) DEB_ARCH=amd64 ;; aarch64) DEB_ARCH=arm64 ;; *) DEB_ARCH="$ARCH" ;; esac
OUT="$ROOT/out"
DIST="$ROOT/dist/VoidLoop"
mkdir -p "$OUT"

build_pyinstaller() {
    python3 -m PyInstaller --noconfirm --clean --distpath "$ROOT/dist" --workpath "$ROOT/build" packaging/voidloop.spec
    cp LICENSE THIRD_PARTY_NOTICES.md "$DIST/"
}

make_tar() {
    local stage="$ROOT/build/tar/VoidLoop-$VERSION-linux-$ARCH"
    rm -rf "$stage" && mkdir -p "$stage"
    cp -r "$DIST" "$stage/VoidLoop"
    cp packaging/linux/voidloop.desktop packaging/linux/voidloop.png packaging/linux/install.sh "$stage/"
    cp README.md README.it.md LICENSE THIRD_PARTY_NOTICES.md "$stage/" 2>/dev/null || true
    chmod +x "$stage/install.sh" "$stage/VoidLoop/VoidLoop"
    tar -C "$ROOT/build/tar" -czf "$OUT/VoidLoop-$VERSION-linux-$ARCH.tar.gz" "VoidLoop-$VERSION-linux-$ARCH"
    echo "built $OUT/VoidLoop-$VERSION-linux-$ARCH.tar.gz"
}

make_deb() {
    command -v dpkg-deb >/dev/null || { echo "dpkg-deb not found, skipping .deb"; return 0; }
    local pkg="$ROOT/build/deb/voidloop_${VERSION}_${DEB_ARCH}"
    rm -rf "$pkg" && mkdir -p "$pkg/DEBIAN" "$pkg/opt/voidloop" "$pkg/usr/bin" "$pkg/usr/share/applications" \
        "$pkg/usr/share/icons/hicolor/512x512/apps" "$pkg/usr/share/doc/voidloop"
    cp -r "$DIST/." "$pkg/opt/voidloop/"
    ln -s /opt/voidloop/VoidLoop "$pkg/usr/bin/voidloop"
    cp packaging/linux/voidloop.desktop "$pkg/usr/share/applications/voidloop.desktop"
    cp packaging/linux/voidloop.png "$pkg/usr/share/icons/hicolor/512x512/apps/voidloop.png"
    cp LICENSE "$pkg/usr/share/doc/voidloop/copyright"
    cp THIRD_PARTY_NOTICES.md "$pkg/usr/share/doc/voidloop/"
    local size; size="$(du -sk "$pkg/opt" | cut -f1)"
    cat > "$pkg/DEBIAN/control" <<CONTROL
Package: voidloop
Version: $VERSION
Section: games
Priority: optional
Architecture: $DEB_ARCH
Installed-Size: $size
Maintainer: BitJacker <165490134+BitJacker@users.noreply.github.com>
Homepage: https://github.com/BitJacker/VoidLoop
Recommends: libasound2 | libasound2t64, libpulse0, libx11-6
Description: Neon cyber-survival arcade shooter
 VoidLoop is a fast top-down arcade shooter set in a digital simulation:
 six animated sectors, six bosses, five game modes, local co-op and a story
 in four languages (Italian, English, Spanish, French).
CONTROL
    chmod 0755 "$pkg/opt/voidloop/VoidLoop"
    dpkg-deb --build --root-owner-group "$pkg" "$OUT/voidloop_${VERSION}_${DEB_ARCH}.deb" >/dev/null
    echo "built $OUT/voidloop_${VERSION}_${DEB_ARCH}.deb"
}

make_appimage() {
    local tool="${APPIMAGETOOL:-}"
    if [ -z "$tool" ]; then
        tool="$ROOT/build/appimagetool-$ARCH.AppImage"
        if [ ! -x "$tool" ]; then
            curl -fsSL -o "$tool" "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$ARCH.AppImage"
            chmod +x "$tool"
        fi
    fi
    local app="$ROOT/build/AppDir"
    rm -rf "$app" && mkdir -p "$app/usr/lib/voidloop"
    cp -r "$DIST/." "$app/usr/lib/voidloop/"
    cp packaging/linux/voidloop.desktop "$app/voidloop.desktop"
    cp packaging/linux/voidloop.png "$app/voidloop.png"
    cp packaging/linux/voidloop.png "$app/.DirIcon"
    cat > "$app/AppRun" <<'APPRUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/lib/voidloop/VoidLoop" "$@"
APPRUN
    chmod +x "$app/AppRun"
    APPIMAGE_EXTRACT_AND_RUN=1 ARCH="$ARCH" "$tool" "$app" "$OUT/VoidLoop-$VERSION-$ARCH.AppImage"
    echo "built $OUT/VoidLoop-$VERSION-$ARCH.AppImage"
}

what="${1:-all}"
case "$what" in
    pyinstaller) build_pyinstaller ;;
    tar) make_tar ;;
    deb) make_deb ;;
    appimage) make_appimage ;;
    all) build_pyinstaller; make_tar; make_deb; make_appimage ;;
    *) echo "usage: $0 [pyinstaller|tar|deb|appimage|all]"; exit 2 ;;
esac
