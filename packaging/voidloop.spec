# -*- mode: python ; coding: utf-8 -*-
# PyInstaller recipe for VoidLoop.
#
#   pyinstaller --noconfirm --clean packaging/voidloop.spec                   -> dist/VoidLoop/   (folder, fast start)
#   VOIDLOOP_ONEFILE=1 pyinstaller --noconfirm --clean packaging/voidloop.spec -> dist/VoidLoop(.exe)  (single file)
import os
import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent            # SPECPATH is provided by PyInstaller
ONEFILE = os.environ.get("VOIDLOOP_ONEFILE") == "1"
WINDOWS = sys.platform.startswith("win")
ICON = str(ROOT / "packaging" / "windows" / "voidloop.ico") if WINDOWS else None

datas = [
    (str(ROOT / "VoidLoop" / "lang"), "VoidLoop/lang"),
    (str(ROOT / "VoidLoop" / "assets"), "VoidLoop/assets"),
]

# Things the game never uses: keeps the download small.
excludes = [
    "tkinter", "unittest", "pydoc", "doctest", "test", "distutils", "setuptools", "pkg_resources", "pip",
    "numpy", "PIL", "fontTools", "pytest", "_pytest", "lib2to3", "curses", "sqlite3", "ensurepip",
    "xmlrpc", "asyncio", "concurrent", "multiprocessing", "email", "http", "html", "wsgiref",
    "pygame.tests", "pygame.examples", "pygame.docs", "pygame.camera", "pygame.midi", "pygame.sndarray", "pygame.surfarray",
]

a = Analysis(
    [str(ROOT / "play.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=["VoidLoop.selftest", "VoidLoop.scenes.title", "VoidLoop.scenes.play", "VoidLoop.scenes.story",
                   "VoidLoop.scenes.results", "VoidLoop.scenes.shop"],
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)

if ONEFILE:
    exe = EXE(
        pyz, a.scripts, a.binaries, a.datas, [],
        name="VoidLoop", debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
        console=False, disable_windowed_traceback=False, icon=ICON,
    )
else:
    exe = EXE(
        pyz, a.scripts, [], exclude_binaries=True,
        name="VoidLoop", debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
        console=False, disable_windowed_traceback=False, icon=ICON,
    )
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="VoidLoop")
