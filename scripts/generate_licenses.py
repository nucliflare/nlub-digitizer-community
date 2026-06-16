"""Generate LICENSES_THIRD_PARTY.txt from installed packages.

Requires pip-licenses (included in the [dev] extras):
    python scripts/generate_licenses.py
"""

import subprocess
import sys
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent.parent / "LICENSES_THIRD_PARTY.txt"


def _find_exe(name: str) -> Path:
    scripts_dir = Path(sys.executable).parent
    suffix = ".exe" if sys.platform == "win32" else ""
    exe = scripts_dir / f"{name}{suffix}"
    if not exe.exists():
        raise FileNotFoundError(
            f"{exe} not found — make sure the venv is active and pip-licenses is installed."
        )
    return exe


def main() -> None:
    print("Collecting third-party licenses...")
    exe = _find_exe("pip-licenses")
    subprocess.run(
        [
            str(exe),
            "--format=plain-vertical",
            "--with-license-file",
            "--no-license-path",
            "--output-file", str(OUTPUT),
        ],
        check=True,
    )
    print(f"Written to {OUTPUT}")


if __name__ == "__main__":
    main()
