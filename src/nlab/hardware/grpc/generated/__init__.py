"""Auto-generated gRPC / protobuf stubs.

Older protoc (pre-3.20) emits bare `import xxx_pb2` for cross-proto
dependencies instead of relative or fully-qualified imports.  Inserting
this directory into sys.path before the first pb2 module is loaded lets
those bare imports resolve correctly without modifying the generated files.

Regenerate with:  python scripts/generate_proto.py
"""
import sys
from pathlib import Path

_generated_dir = str(Path(__file__).parent)
if _generated_dir not in sys.path:
    sys.path.insert(0, _generated_dir)
