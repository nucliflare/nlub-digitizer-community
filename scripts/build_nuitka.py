"""Build a standalone folder distribution using Nuitka.

Prerequisites (all in [dev] extras):
    pip install -e ".[dev]"

Run from the project root with the venv active:
    python scripts/build_exe.py

Output: dist/main.dist/nlab.exe  (Windows)  /  dist/main.dist/nlab  (Linux/macOS)
The whole main.dist/ folder must ship together — nlab.exe alone won't run.

Nuitka notes
------------
- --standalone:            folder-based dist, not a single bundled binary.
                        --onefile (single .exe) was tried first but its
                        runtime self-extraction step failed outright on this
                        project (Windows "Bad Image" error) — --standalone
                        has no extraction step and is what actually works.
- --enable-plugin=pyside6: required for PySide6 apps
- --windows-console-mode=disable: no console window on Windows
- --include-module=PySide6.QtOpenGL(Widgets): pyqtgraph imports these for
                        optional GPU acceleration; Nuitka's static analyzer
                        doesn't discover them on its own and the build
                        crashes at import time without this.
- --nofollow-import-to / --include-data-dir for grpc/generated: the protoc-
                        generated *_pb2.py files use bare `import x_pb2`
                        (pre-3.20 protoc codegen style) instead of relative
                        imports — see grpc/generated/__init__.py. The app
                        works around this at runtime by inserting that
                        directory into sys.path, which only works if those
                        files exist as real on-disk .py files; compiling
                        them into the binary (Nuitka's default) hides them
                        from that sys.path trick entirely. Excluding the
                        package from compilation and copying it as plain
                        data preserves the working dev-mode behavior.
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
ICON = ROOT / "resources" / "icons" / "ewt.ico"
GENERATED_PROTO_DIR = ROOT / "src" / "nlab" / "hardware" / "grpc" / "generated"
DIST = ROOT / "dist"

args = [
    sys.executable, "-m", "nuitka",
    "--standalone",
    "--enable-plugin=pyside6",
    "--windows-console-mode=disable",
    f"--windows-icon-from-ico={ICON}",
    f"--output-dir={DIST}",
    "--output-filename=nlab",
    # Include the whole package so all submodules are found at runtime:
    "--include-package=nlab",
    # pyqtgraph's optional OpenGL acceleration path — not auto-discovered:
    "--include-module=PySide6.QtOpenGL",
    "--include-module=PySide6.QtOpenGLWidgets",
    # Keep the generated gRPC stubs as plain files (see module docstring)
    # rather than compiled-in, so their bare `import x_pb2` style still
    # resolves via the sys.path trick in grpc/generated/__init__.py:
    "--nofollow-import-to=nlab.hardware.grpc.generated",
    f"--include-data-dir={GENERATED_PROTO_DIR}=nlab/hardware/grpc/generated",
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
