from __future__ import annotations

from PySide6.QtWidgets import QWidget

from nlab.hardware.digitizer.mca import MultiChannelAnalyzer
from nlab.ui.ui_mca_view import Ui_MCAView


class MCAController(QWidget):
    """View + controller for a single MultiChannelAnalyzer channel.

    Loaded from ui_mca_view.ui.  Drop into any QTabWidget via addTab().
    """

    def __init__(self, mca: MultiChannelAnalyzer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mca = mca
        self._ui = Ui_MCAView()
        self._ui.setupUi(self)
        self._connect_signals()

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self._ui.btnStart.clicked.connect(self._on_start)
        self._ui.btnStop.clicked.connect(self._on_stop)
        self._ui.btnClearSpectrum.clicked.connect(self._on_clear_spectrum)

        self._ui.spinTriggerLevel.valueChanged.connect(
            lambda v: self._mca.set_trigger_level(v)
        )
        self._ui.comboPulsePolarity.currentIndexChanged.connect(
            lambda i: self._mca.set_pulse_polarity(i)
        )
        self._ui.spinBaselineWindow.valueChanged.connect(
            lambda v: self._mca.set_baseline_window(v)
        )
        self._ui.spinPretrigger.valueChanged.connect(
            lambda v: self._mca.set_pretrigger_samples(v)
        )
        self._ui.spinFrameSamples.valueChanged.connect(
            lambda v: self._mca.set_frame_samples(v)
        )
        self._ui.spinTimeLimit.valueChanged.connect(
            lambda v: self._mca.set_time_limit(v)
        )
        self._ui.spinEnergyBin.valueChanged.connect(
            lambda v: self._mca.set_energy_bin(v)
        )
        self._ui.spinPileupWindow.valueChanged.connect(
            lambda v: self._mca.set_pileup_window(v)
        )

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        self._mca.start()
        self._ui.btnStart.setEnabled(False)
        self._ui.btnStop.setEnabled(True)

    def _on_stop(self) -> None:
        self._mca.stop()
        self._ui.btnStart.setEnabled(True)
        self._ui.btnStop.setEnabled(False)

    def _on_clear_spectrum(self) -> None:
        self._mca.clear_spectrum()

    def update_statistics(self) -> None:
        """Call from a periodic timer to refresh the Statistics group."""
        stats = self._mca.stats
        self._ui.lblCountRate.setText(str(stats.get_count_rate()))
        self._ui.lblElapsedTime.setText(str(stats.get_elapsed_time()))
        self._ui.lblEventsLost.setText(str(stats.get_events_lost()))
