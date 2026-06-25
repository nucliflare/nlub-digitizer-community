from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSettings, Qt, QThread, QThreadPool
from PySide6.QtWidgets import QDockWidget, QMainWindow, QWidget

from nlab.controllers.mca_controller import MCAController
from nlab.controllers.psu_controller import PSUController
from nlab.controllers.scope_controller import ScopeController
from nlab.hardware.digitizer.digitizer import Digitizer

if TYPE_CHECKING:
    from nlab.app import MainAppWindow


class MainWindowController:
    """Handles all business logic for MainAppWindow.

    Owns the DeviceManager and measurement thread lifecycle.
    Each channel's Scope and MCA views live in QDockWidgets so they can be
    floated onto a second monitor and re-docked freely.
    """

    def __init__(
        self,
        window: MainAppWindow,
        host: str = "",
        port: int = 50051,
        channels: int = 2,
    ) -> None:
        self._window = window
        self._host = host
        self._port = port
        self._channels = channels
        self._devices: list[Digitizer] = []

        for ch in range(1, 1 + self._channels):
            device = Digitizer.from_grpc(channel=ch, hostname=self._host, port=self._port)
            self._devices.append(device)

        self._scope_controllers: list[ScopeController] = []
        self._mca_controllers: list[MCAController] = []
        self._psu_controllers: list[PSUController] = []
        self._thread: QThread | None = None

        self._scope_dock_host = self._make_dock_host()
        self._mca_dock_host = self._make_dock_host()
        self._psu_dock_host = self._make_dock_host()
        self._build_channel_docks()
        self._restore_dock_state()
        self._connect_signals()

    # ------------------------------------------------------------------
    # Dock construction
    # ------------------------------------------------------------------

    @staticmethod
    def _make_dock_host() -> QMainWindow:
        """A QMainWindow used as an embedded dock-area panel."""
        host = QMainWindow()
        host.setWindowFlags(Qt.WindowType.Widget)
        host.setDockOptions(QMainWindow.DockOption.AllowTabbedDocks | QMainWindow.DockOption.AllowNestedDocks | QMainWindow.DockOption.AnimatedDocks)
        return host

    @staticmethod
    def _make_dock(obj_name: str, title: str, widget: QWidget) -> QDockWidget:
        dock = QDockWidget(title)
        dock.setObjectName(obj_name)
        dock.setWidget(widget)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        return dock

    @staticmethod
    def _populate_dock_host(host: QMainWindow, docks: list[QDockWidget]) -> None:
        """Add docks to host, tabified, with the first tab raised.

        All docks must be registered via addDockWidget before tabifyDockWidget
        is called — Qt requires both arguments to already belong to the host.
        """
        if not docks:
            return
        for dock in docks:
            host.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        for i in range(1, len(docks)):
            host.tabifyDockWidget(docks[i - 1], docks[i])
        docks[0].raise_()

    def _build_channel_docks(self) -> None:
        scope_docks: list[QDockWidget] = []
        mca_docks: list[QDockWidget] = []
        psu_docks: list[QDockWidget] = []

        for idx, device in enumerate(self._devices):
            ch_label = f"Ch {idx + 1}"

            scope_ctrl = ScopeController(device.scope)
            self._scope_controllers.append(scope_ctrl)
            scope_docks.append(self._make_dock(f"scope_ch{idx + 1}", ch_label, scope_ctrl))

            mca_ctrl = MCAController(device.mca)
            self._mca_controllers.append(mca_ctrl)
            mca_docks.append(self._make_dock(f"mca_ch{idx + 1}", ch_label, mca_ctrl))

            if device.hv is not None:
                psu_ctrl = PSUController(device.hv)
                self._psu_controllers.append(psu_ctrl)
                psu_docks.append(self._make_dock(f"psu_ch{idx + 1}", ch_label, psu_ctrl))

        self._populate_dock_host(self._scope_dock_host, scope_docks)
        self._populate_dock_host(self._mca_dock_host, mca_docks)
        self._populate_dock_host(self._psu_dock_host, psu_docks)

        self._window.ui.layoutTabScope.addWidget(self._scope_dock_host)
        self._window.ui.layoutTabMCA.addWidget(self._mca_dock_host)
        self._window.ui.layoutTabPSU.addWidget(self._psu_dock_host)

    # ------------------------------------------------------------------
    # Dock state persistence
    # ------------------------------------------------------------------

    # Bump suffix when dock object names or topology change so stale layouts
    # are silently discarded rather than corrupting the initial tab arrangement.
    _DOCK_STATE_KEY_SCOPE = "docks/v2/scope"
    _DOCK_STATE_KEY_MCA = "docks/v2/mca"
    _DOCK_STATE_KEY_PSU = "docks/v2/psu"

    def _save_dock_state(self) -> None:
        settings = QSettings()
        settings.setValue(self._DOCK_STATE_KEY_SCOPE, self._scope_dock_host.saveState())
        settings.setValue(self._DOCK_STATE_KEY_MCA, self._mca_dock_host.saveState())
        settings.setValue(self._DOCK_STATE_KEY_PSU, self._psu_dock_host.saveState())

    def _restore_dock_state(self) -> None:
        settings = QSettings()
        if state := settings.value(self._DOCK_STATE_KEY_SCOPE):
            if not self._scope_dock_host.restoreState(state):
                settings.remove(self._DOCK_STATE_KEY_SCOPE)
        if state := settings.value(self._DOCK_STATE_KEY_MCA):
            if not self._mca_dock_host.restoreState(state):
                settings.remove(self._DOCK_STATE_KEY_MCA)
        if state := settings.value(self._DOCK_STATE_KEY_PSU):
            if not self._psu_dock_host.restoreState(state):
                settings.remove(self._DOCK_STATE_KEY_PSU)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Persist dock layout, stop all workers, close all devices."""
        self._save_dock_state()

        # 1. Stop scope timers — no new workers will be submitted
        for ctrl in self._scope_controllers:
            ctrl._refresh_timer.stop()

        # 2. Signal PSU workers to stop (non-blocking)
        for ctrl in self._psu_controllers:
            if ctrl._worker is not None:
                ctrl._worker.request_stop.emit()

        # 3. Stop MCA workers (blocking — app is shutting down)
        for ctrl in self._mca_controllers:
            ctrl.stop_worker_sync()

        # 4. Wait for in-flight scope workers to finish
        QThreadPool.globalInstance().waitForDone(3000)

        # 5. Wait for PSU threads to exit, then drop references
        for ctrl in self._psu_controllers:
            if ctrl._worker_thread is not None:
                if not ctrl._worker_thread.wait(3000):
                    ctrl._worker_thread.terminate()
                    ctrl._worker_thread.wait()
                ctrl._worker_thread = None
            ctrl._worker = None

        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()
            self._thread = None

        # 5. All workers done — safe to close hardware
        for device in self._devices:
            device.close()
        self._devices.clear()

    def _connect_signals(self) -> None:
        pass
