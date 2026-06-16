from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QDialog, QWidget

from nlab.ui.ui_license_dialog import Ui_LicenseDialog

# Dev: project root / packaged: next to the executable
_CANDIDATES: list[Path] = [
    Path(__file__).parents[3] / "LICENSES_THIRD_PARTY.txt",
    Path(sys.executable).parent / "LICENSES_THIRD_PARTY.txt",
]

_PLACEHOLDER = "(LICENSES_THIRD_PARTY.txt not found — run scripts/generate_licenses.py)"


def _load_licenses() -> str:
    for path in _CANDIDATES:
        if path.is_file():
            return path.read_text(encoding="utf-8", errors="replace")
    return _PLACEHOLDER


class LicenseDialog(QDialog):
    """Scrollable viewer for third-party license notices."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ui = Ui_LicenseDialog()
        self._ui.setupUi(self)

        font = QFont("Consolas", 9)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._ui.textLicenses.setFont(font)
        self._ui.textLicenses.setPlainText(_load_licenses())

        self._ui.buttonBox.rejected.connect(self.reject)
