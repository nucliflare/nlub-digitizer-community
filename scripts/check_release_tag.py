"""Fail CI if the pushed git tag doesn't match nlab._version.__version__.

Keeps the git tag and src/nlab/_version.py as a single source of truth:
whichever remote (Gitea or GitHub) receives the tag push, the build
refuses to run on a mismatch instead of shipping a mislabeled artifact.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from nlab._version import __version__  # noqa: E402

tag = os.environ.get("GITHUB_REF_NAME", "")
expected = f"v{__version__}"

if tag != expected:
    print(f"Tag '{tag}' does not match package version '{expected}' (src/nlab/_version.py)")
    sys.exit(1)

print(f"Tag '{tag}' matches package version '{expected}'.")
