from __future__ import annotations

import logging

from PySide6.QtCore import QSettings
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox

from nlab import __version__
from nlab.controllers.main_window_controller import MainWindowController
from nlab.ui.ui_main_window import Ui_MainWindow
from nlab.views.license_dialog import LicenseDialog

_ABOUT_TEXT = f"""\
<b>Nuclear Lab Digitizer — Community Edition</b><br>
Version {__version__}<br>
<br>
A PySide6 desktop application for real-time data acquisition and<br>
pulse-shape analysis with EWT digitizer hardware.<br>
<br>
Organization: EWT<br>
License: GPL-3.0-or-later<br>
<br>
Source: <a href="https://github.com/ewt/nlab-community">github.com/ewt/nlab-community</a>
"""

_KEY_SHOW_LOG = "developer/show_system_log"
_KEY_DEBUG_MODE = "developer/debug_mode"
_KEY_DMA_FOLDER = "dma/save_folder"


class MainAppWindow(QMainWindow):
    """Top-level application window. Owns the UI and its controller."""

    def __init__(self, host: str = "", port: int = 50051, channels: int = 2) -> None:
        super().__init__()
        self._setup_ui()
        self.setWindowTitle(f"Nuclear Lab Digitizer — {host}:{port}")
        self._controller = MainWindowController(self, host=host, port=port, channels=channels)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self._save_developer_settings()
        self._controller.shutdown()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.resize(1024, 768)

        self.ui.actionExit.triggered.connect(self.close)
        self.ui.actionResetDocks.triggered.connect(self._on_reset_docks)
        self.ui.actionDmaSaveFolder.triggered.connect(self._on_dma_save_folder)
        self.ui.actionAbout.triggered.connect(self._on_about)
        self.ui.actionThirdPartyLicenses.triggered.connect(self._on_third_party_licenses)
        self.ui.actionShowSystemLog.toggled.connect(self._on_show_system_log_toggled)
        self.ui.actionDebugMode.toggled.connect(self._on_debug_mode_toggled)

        self._restore_developer_settings()

    # ------------------------------------------------------------------
    # QSettings persistence for developer panel state
    # ------------------------------------------------------------------

    def _restore_developer_settings(self) -> None:
        settings = QSettings()
        show_log = settings.value(_KEY_SHOW_LOG, False, type=bool)
        debug_mode = settings.value(_KEY_DEBUG_MODE, False, type=bool)

        # Suppress intermediate toggled signals while restoring state.
        self.ui.actionShowSystemLog.blockSignals(True)
        self.ui.actionDebugMode.blockSignals(True)

        self.ui.actionShowSystemLog.setChecked(show_log)
        self.ui.actionDebugMode.setChecked(debug_mode)
        self._set_log_tab_visible(show_log)
        if debug_mode:
            logging.getLogger().setLevel(logging.DEBUG)

        self.ui.actionShowSystemLog.blockSignals(False)
        self.ui.actionDebugMode.blockSignals(False)

    def _save_developer_settings(self) -> None:
        settings = QSettings()
        settings.setValue(_KEY_SHOW_LOG, self.ui.actionShowSystemLog.isChecked())
        settings.setValue(_KEY_DEBUG_MODE, self.ui.actionDebugMode.isChecked())

    def _set_log_tab_visible(self, visible: bool) -> None:
        idx = self.ui.mainTabs.indexOf(self.ui.tabSystemLog)
        self.ui.mainTabs.setTabVisible(idx, visible)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_show_system_log_toggled(self, checked: bool) -> None:
        self._set_log_tab_visible(checked)

    def _on_debug_mode_toggled(self, checked: bool) -> None:
        level = logging.DEBUG if checked else logging.INFO
        logging.getLogger().setLevel(level)
        logging.getLogger(__name__).info("Debug mode %s (log level: %s)",
                                         "enabled" if checked else "disabled",
                                         logging.getLevelName(level))
        if checked and not self.ui.actionShowSystemLog.isChecked():
            self.ui.actionShowSystemLog.setChecked(True)

    def _on_reset_docks(self) -> None:
        self._controller.reset_dock_layout()

    def _on_dma_save_folder(self) -> None:
        current = QSettings().value(_KEY_DMA_FOLDER, "measurements")
        folder = QFileDialog.getExistingDirectory(self, "DMA Save Folder", str(current))
        if folder:
            QSettings().setValue(_KEY_DMA_FOLDER, folder)
            logging.getLogger(__name__).info("DMA save folder set to: %s", folder)

    def _on_about(self) -> None:
        QMessageBox.about(self, "About Nuclear Lab Digitizer", _ABOUT_TEXT)

    def _on_third_party_licenses(self) -> None:
        LicenseDialog(self).exec()
