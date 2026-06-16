"""Build a standalone single-file executable using Nuitka.

Prerequisites (all in [dev] extras):
    pip install -e ".[dev]"

Run from the project root with the venv active:
    python scripts/build_exe.py

Output: dist/nlab.exe  (Windows)  /  dist/nlab  (Linux/macOS)

Nuitka notes
------------
- --onefile:            bundle everything into one binary (slow first launch;
                        use --standalone for a folder-based dist instead)
- --enable-plugin=pyside6: required for PySide6 apps
- --windows-console-mode=disable: no console window on Windows
- Compilation takes several minutes on first run; subsequent runs are faster.

Alternative: PyInstaller
------------------------
If Nuitka is too complex for your workflow, PyInstaller is simpler:
    pip install pyinstaller
    pyinstaller --onefile --windowed --name nlab src/nlab/main.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENTRY = ROOT / "src" / "nlab" / "main.py"
ICON = ROOT / "resources" / "icons" / "app.ico"
DIST = ROOT / "dist"

args = [
    sys.executable, "-m", "nuitka",
    "--onefile",
    "--enable-plugin=pyside6",
    "--windows-console-mode=disable",
    f"--windows-icon-from-ico={ICON}",
    f"--output-dir={DIST}",
    "--output-filename=nlab",
    # Include the whole package so all submodules are found at runtime:
    "--include-package=nlab",
    # Embed resource data folders if needed:
    # f"--include-data-dir={ROOT / 'resources'}=resources",
    str(ENTRY),
]


def main() -> None:
    DIST.mkdir(exist_ok=True)
    print("Building with Nuitka — this may take a few minutes...")
    print("Command:", " ".join(str(a) for a in args))
    subprocess.run(args, check=True)
    print(f"\nBuild complete. Output in {DIST}/")


if __name__ == "__main__":
    main()
