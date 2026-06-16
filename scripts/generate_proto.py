"""Generate Python gRPC stubs from .proto source files.

Requires grpcio-tools (included in [dev] extras):
    python scripts/generate_proto.py

Output: src/nlab/hardware/grpc/generated/
Re-run whenever any .proto file changes.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROTO_SRC = ROOT / "src" / "nlab" / "hardware" / "grpc" / "proto"
PROTO_OUT = ROOT / "src" / "nlab" / "hardware" / "grpc" / "generated"


def main() -> None:
    proto_files = list(PROTO_SRC.glob("*.proto"))
    if not proto_files:
        print("No .proto files found in", PROTO_SRC)
        return

    PROTO_OUT.mkdir(exist_ok=True)

    print(f"Compiling {len(proto_files)} proto file(s)...")
    subprocess.run(
        [
            sys.executable, "-m", "grpc_tools.protoc",
            f"--proto_path={PROTO_SRC}",
            f"--python_out={PROTO_OUT}",
            f"--grpc_python_out={PROTO_OUT}",
            *[str(f) for f in proto_files],
        ],
        check=True,
    )
    print(f"Stubs written to {PROTO_OUT.relative_to(ROOT)}")
    print("Note: bare cross-imports in generated files are resolved at runtime")
    print("      by src/nlab/hardware/grpc/generated/__init__.py.")


if __name__ == "__main__":
    main()
