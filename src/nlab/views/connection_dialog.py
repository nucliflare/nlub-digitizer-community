from __future__ import annotations

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QWidget

from nlab.ui.ui_connection_dialog import Ui_ConnectionDialog
from nlab.utils.windows_icon import apply_taskbar_icon

_MAX_RECENT_IPS = 10
_DEFAULT_PORT = 50051
_DEFAULT_CHANNELS = 2

_KEY_RECENT_IPS = "connection/recent_ips"
_KEY_LAST_PORT = "connection/last_port"
_KEY_LAST_CHANNELS = "connection/last_channels"


class ConnectionDialog(QDialog):
    """Pre-launch dialog for entering device IP and port.

    IP history is persisted via QSettings so the last-used addresses are
    available in the drop-down on the next run.  Auto-discovery entries
    can be added later by populating the combo from a background scanner.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ui = Ui_ConnectionDialog()
        self._ui.setupUi(self)
        self._ui.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText("Connect")
        self._ui.buttonBox.accepted.connect(self._on_accept)
        self._ui.buttonBox.rejected.connect(self.reject)
        apply_taskbar_icon(self)
        self._load_settings()

    # ------------------------------------------------------------------
    # Public properties — read after exec() == Accepted
    # ------------------------------------------------------------------

    @property
    def ip(self) -> str:
        return self._ui.comboIp.currentText().strip()

    @property
    def port(self) -> int:
        return self._ui.spinPort.value()

    @property
    def channels(self) -> int:
        return self._ui.spinChannels.value()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load_settings(self) -> None:
        settings = QSettings()
        recent: list[str] = settings.value(_KEY_RECENT_IPS, [], type=list)  # type: ignore[assignment]
        self._ui.comboIp.addItems(recent)
        if recent:
            self._ui.comboIp.setCurrentIndex(0)
        self._ui.spinPort.setValue(int(settings.value(_KEY_LAST_PORT, _DEFAULT_PORT)))  # type: ignore[arg-type]
        self._ui.spinChannels.setValue(int(settings.value(_KEY_LAST_CHANNELS, _DEFAULT_CHANNELS)))  # type: ignore[arg-type]

    def _save_settings(self) -> None:
        settings = QSettings()
        recent: list[str] = settings.value(_KEY_RECENT_IPS, [], type=list)  # type: ignore[assignment]
        ip = self.ip
        if ip in recent:
            recent.remove(ip)
        recent.insert(0, ip)
        settings.setValue(_KEY_RECENT_IPS, recent[:_MAX_RECENT_IPS])
        settings.setValue(_KEY_LAST_PORT, self.port)
        settings.setValue(_KEY_LAST_CHANNELS, self.channels)

    def _on_accept(self) -> None:
        if not self.ip:
            self._ui.comboIp.lineEdit().setFocus()  # type: ignore[union-attr]
            return
        self._save_settings()
        self.accept()
