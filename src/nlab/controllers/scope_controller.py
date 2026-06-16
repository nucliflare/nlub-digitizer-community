from __future__ import annotations

from PySide6.QtWidgets import QWidget

from nlab.hardware.digitizer.scope import Scope, TriggerMode
from nlab.ui.ui_scope_view import Ui_ScopeView


class ScopeController(QWidget):
    """View + controller for a single Scope channel.

    Loaded from ui_scope_view.ui.  Drop into any QTabWidget via addTab().
    """

    def __init__(self, scope: Scope, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scope = scope
        self._ui = Ui_ScopeView()
        self._ui.setupUi(self)
        self._connect_signals()

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self._ui.btnStart.clicked.connect(self._on_start)
        self._ui.btnStop.clicked.connect(self._on_stop)
        self._ui.btnAcquireFrame.clicked.connect(self._on_acquire_frame)

        self._ui.spinTriggerLevel.valueChanged.connect(
            lambda v: self._scope.set_trigger_level(v)
        )
        self._ui.comboTriggerMode.currentIndexChanged.connect(
            lambda i: self._scope.set_trigger_mode(TriggerMode(i))
        )
        self._ui.spinDacValue.valueChanged.connect(
            lambda v: self._scope.set_dac_value(v)
        )
        self._ui.spinPretrigger.valueChanged.connect(
            lambda v: self._scope.set_pretrigger_samples(v)
        )
        self._ui.spinFrameSamples.valueChanged.connect(
            lambda v: self._scope.set_frame_samples(v)
        )
        self._ui.cbDmaEnable.toggled.connect(
            lambda v: self._scope.set_dma_enable(v)
        )

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        self._scope.start()
        self._ui.btnStart.setEnabled(False)
        self._ui.btnStop.setEnabled(True)

    def _on_stop(self) -> None:
        self._scope.stop()
        self._ui.btnStart.setEnabled(True)
        self._ui.btnStop.setEnabled(False)

    def _on_acquire_frame(self) -> None:
        _frame = self._scope.acquire_frame()
        # TODO: pass frame to waveformDisplay plot widget
