"""Compile Qt Designer .ui files and .qrc resource files to Python modules.

Run from the project root after activating the venv:
    python scripts/build_ui.py

Why the post-processing step?
pyside6-uic emits a bare `import resources_rc` at the top of every compiled
file that references a .qrc.  That works only if resources_rc.py sits on
sys.path as a top-level module, which it doesn't in a src-layout package.
We rewrite it to a relative import so the package resolves it correctly.
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI_SRC = ROOT / "forms"
UI_OUT = ROOT / "src" / "nlab" / "ui"
RES_SRC = ROOT / "resources"
RES_OUT = ROOT / "src" / "nlab" / "ui"

# pyside6-uic always writes this bare import; we patch it to a relative one.
_RC_IMPORT_RE = re.compile(r"^import (\w+_rc)$", re.MULTILINE)
_RC_IMPORT_SUB = r"from . import \1"


def _tool(name: str) -> Path:
    scripts_dir = Path(sys.executable).parent
    suffix = ".exe" if sys.platform == "win32" else ""
    exe = scripts_dir / f"{name}{suffix}"
    if not exe.exists():
        raise FileNotFoundError(
            f"{exe} not found — make sure the venv is activated and PySide6 is installed."
        )
    return exe


def _patch_rc_imports(path: Path) -> None:
    """Replace bare `import foo_rc` with `from . import foo_rc`."""
    original = path.read_text(encoding="utf-8")
    patched = _RC_IMPORT_RE.sub(_RC_IMPORT_SUB, original)
    if patched != original:
        path.write_text(patched, encoding="utf-8")
        print(f"    patched rc import in {path.name}")


def compile_ui() -> None:
    uic = _tool("pyside6-uic")
    ui_files = list(UI_SRC.glob("*.ui"))
    if not ui_files:
        print("No .ui files found in", UI_SRC)
        return
    for ui_file in ui_files:
        out = UI_OUT / f"ui_{ui_file.stem}.py"
        print(f"  {ui_file.name}  ->  {out.relative_to(ROOT)}")
        subprocess.run([str(uic), str(ui_file), "-o", str(out)], check=True)
        _patch_rc_imports(out)


def compile_resources() -> None:
    rcc = _tool("pyside6-rcc")
    qrc_files = list(RES_SRC.glob("*.qrc"))
    if not qrc_files:
        print("No .qrc files found in", RES_SRC)
        return
    for qrc_file in qrc_files:
        out = RES_OUT / f"{qrc_file.stem}_rc.py"
        print(f"  {qrc_file.name}  ->  {out.relative_to(ROOT)}")
        subprocess.run([str(rcc), str(qrc_file), "-o", str(out)], check=True)


def main() -> None:
    UI_OUT.mkdir(parents=True, exist_ok=True)
    # Resources must be compiled first so the .qrc files exist when uic runs
    print("Compiling resource files...")
    compile_resources()
    print("Compiling UI files...")
    compile_ui()
    print("Done.")


if __name__ == "__main__":
    main()
