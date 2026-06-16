from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QTabWidget

from nlab.controllers.mca_controller import MCAController
from nlab.controllers.scope_controller import ScopeController
from nlab.hardware.digitizer.digitizer import Digitizer

if TYPE_CHECKING:
    from nlab.app import MainAppWindow


class MainWindowController:
    """Handles all business logic for MainAppWindow.

    Owns the DeviceManager and measurement thread lifecycle.
    """

    def __init__(self, window: MainAppWindow, host: str = "", port: int = 50051, channels: int = 2) -> None:
        self._window = window
        self._host = host
        self._port = port
        self._channels = channels
        self._devices: list[Digitizer] = []

        for ch in range(1, 1 + self._channels):
            device = Digitizer.from_grpc(channel=ch, hostname=self._host, port=self._port)
            self._devices.append(device)
            device.print_status()

        self._scope_controllers: list[ScopeController] = []
        self._mca_controllers: list[MCAController] = []
        self._thread: QThread | None = None

        self._build_channel_tabs()
        self._connect_signals()

    # ------------------------------------------------------------------
    # Tab construction
    # ------------------------------------------------------------------

    def _build_channel_tabs(self) -> None:
        scope_inner = QTabWidget()
        scope_inner.setTabPosition(QTabWidget.TabPosition.West)

        mca_inner = QTabWidget()
        mca_inner.setTabPosition(QTabWidget.TabPosition.West)

        for idx, device in enumerate(self._devices):
            ch_label = f"Ch {idx + 1}"

            scope_ctrl = ScopeController(device.scope, scope_inner)
            scope_inner.addTab(scope_ctrl, ch_label)
            self._scope_controllers.append(scope_ctrl)

            mca_ctrl = MCAController(device.mca, mca_inner)
            mca_inner.addTab(mca_ctrl, ch_label)
            self._mca_controllers.append(mca_ctrl)

        self._window._ui.layoutTabScope.addWidget(scope_inner)
        self._window._ui.layoutTabMCA.addWidget(mca_inner)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Stop any running thread, then close all device connections."""
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()
            self._thread = None
        for device in self._devices:
            device.close()
        self._devices.clear()

    def _connect_signals(self) -> None:
        pass
