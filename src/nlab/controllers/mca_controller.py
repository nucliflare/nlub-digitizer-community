from __future__ import annotations

import logging

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QMenuBar, QSlider, QSpinBox, QWidget

from nlab.hardware.digitizer.mca import MultiChannelAnalyzer
from nlab.ui.ui_mca_view import Ui_MCAView
from nlab.views.plot_viewbox import ModifierZoomViewBox
from nlab.workers.mca_worker import MCAReadback, MCAWorker

log = logging.getLogger(__name__)

_DEBUG_SIGNAL_NAMES = [
    "Input signal",
    "Trigger signal",
    "Trapezoid signal",
    "Trapezoid energy window",
    "CFD signal",
    "CFD zc window",
    "CC gate",
    "PSD ZC window",
]

_BINNING_LABELS = ["1", "2", "4", "8", "16", "32", "64", "128", "256", "512"]


class MCAController(QWidget):
    """View + controller for a single MultiChannelAnalyzer channel."""

    def __init__(self, mca: MultiChannelAnalyzer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mca = mca
        self.ui = Ui_MCAView()
        self.ui.setupUi(self)

        self._worker: MCAWorker | None = None
        self._worker_thread: QThread | None = None

        self._populate_combos()
        self._setup_view_menu()
        self._setup_debug_plot()
        self._setup_histogram_plot()
        self._connect_signals()

    # ------------------------------------------------------------------
    # Combo population
    # ------------------------------------------------------------------

    def _populate_combos(self) -> None:
        for name in _DEBUG_SIGNAL_NAMES:
            self.ui.comboDebug1.addItem(name)
            self.ui.comboDebug2.addItem(name)
        self.ui.comboDebug2.setCurrentIndex(1)

        for label in _BINNING_LABELS:
            self.ui.comboBinning.addItem(label)

        for i in range(7):
            self.ui.comboTrapFt.addItem(str(i))

    # ------------------------------------------------------------------
    # View menu with ROI toggle
    # ------------------------------------------------------------------

    def _setup_view_menu(self) -> None:
        menu_bar = QMenuBar(self)
        menu_bar.setNativeMenuBar(False)
        view_menu = menu_bar.addMenu("View")
        self._roi_action = view_menu.addAction("Show ROI")
        self._roi_action.setCheckable(True)
        self._roi_action.toggled.connect(self._toggle_roi)
        self.ui.mainLayout.insertWidget(0, menu_bar)

    # ------------------------------------------------------------------
    # Debug plot (scope-like, two curves)
    # ------------------------------------------------------------------

    def _setup_debug_plot(self) -> None:
        layout = pg.GraphicsLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        self.ui.plotDebug.setCentralItem(layout)
        self.ui.plotDebug.setBackground("#f8f9fa")

        layout.addLabel("Amplitude", angle=-90)
        self._debug_plot = layout.addPlot(viewBox=ModifierZoomViewBox())
        self._debug_plot.showAxis("right")
        self._debug_plot.showAxis("top")
        self._debug_plot.showGrid(x=True, y=True, alpha=0.2)
        self._debug_plot.addLegend(offset=(10, 10))
        layout.nextRow()
        layout.addLabel("Time [ns]", col=1)

        self._debug1_curve = self._debug_plot.plot(
            pen=pg.mkPen("#00bfff", width=1),
            name="Debug 1",
        )
        self._debug2_curve = self._debug_plot.plot(
            pen=pg.mkPen("#ff8c00", width=1),
            name="Debug 2",
        )

    # ------------------------------------------------------------------
    # Histogram plot (channels vs counts, with ROI)
    # ------------------------------------------------------------------

    def _setup_histogram_plot(self) -> None:
        layout = pg.GraphicsLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        self.ui.plotHistogram.setCentralItem(layout)
        self.ui.plotHistogram.setBackground("#f8f9fa")

        layout.addLabel("Counts", angle=-90)
        self._hist_plot = layout.addPlot(viewBox=ModifierZoomViewBox())
        self._hist_plot.showAxis("right")
        self._hist_plot.showAxis("top")
        self._hist_plot.showGrid(x=True, y=True, alpha=0.2)
        layout.nextRow()
        layout.addLabel("Channel", col=1)

        self._hist_curve = self._hist_plot.plot(
            pen=pg.mkPen("#1f77b4", width=1),
            fillLevel=0,
            fillBrush=pg.mkBrush(31, 119, 180, 60),
            stepMode="center",
        )

        self._roi = pg.LinearRegionItem(values=[100, 200], movable=True)
        self._roi.setZValue(10)
        self._hist_plot.addItem(self._roi)
        self._roi.setVisible(False)

    def _toggle_roi(self, visible: bool) -> None:
        self._roi.setVisible(visible)

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self.ui.comboPulsePolarity.currentIndexChanged.connect(lambda i: self._mca.set_pulse_polarity(i))
        self.ui.comboBaseline.currentIndexChanged.connect(lambda i: self._mca.set_baseline_window(i))
        self.ui.comboDebug1.currentIndexChanged.connect(lambda i: self._mca.set_mem1_sig_select(i))
        self.ui.comboDebug2.currentIndexChanged.connect(lambda i: self._mca.set_mem2_sig_select(i))
        self.ui.spinPileupWindow.editingFinished.connect(lambda: self._mca.set_pileup_window(self.ui.spinPileupWindow.value()))
        self.ui.comboBinning.currentIndexChanged.connect(lambda i: self._mca.set_energy_bin(i))
        self.ui.cbExtTrigger.toggled.connect(lambda v: self._mca.set_ext_trig_enable(v))

        self.ui.spinTimeLimit.editingFinished.connect(lambda: self._mca.set_time_limit(self.ui.spinTimeLimit.value()))
        self.ui.btnStart.clicked.connect(self._on_start)
        self.ui.btnStop.clicked.connect(self._on_stop)
        self.ui.btnClearSpectrum.clicked.connect(self._on_clear_spectrum)

        self._wire_slider_spinbox(self.ui.sliderTriggerLevel, self.ui.spinTriggerLevel, lambda v: self._mca.set_trigger_level(v))
        self._wire_slider_spinbox(self.ui.sliderFrameSamples, self.ui.spinFrameSamples, lambda v: self._mca.set_frame_samples(v))
        self._wire_slider_spinbox(self.ui.sliderPretrigger, self.ui.spinPretrigger, lambda v: self._mca.set_pretrigger_samples(v))
        self.ui.comboTriggerSource.currentIndexChanged.connect(lambda i: self._mca.set_trg_source(i))
        self.ui.spinEdgeDetCoeff.editingFinished.connect(lambda: self._mca.set_edge_det_coeff(self.ui.spinEdgeDetCoeff.value()))

        self.ui.comboLpPreset.currentIndexChanged.connect(lambda i: self._mca.filters.lp.set_preset(i))

        self._wire_slider_spinbox(self.ui.sliderCrrc2Cdelay, self.ui.spinCrrc2Cdelay, lambda v: self._mca.filters.crrc2.set_Cdelay(v))
        self._wire_slider_spinbox(self.ui.sliderCrrc2Fdelay, self.ui.spinCrrc2Fdelay, lambda v: self._mca.filters.crrc2.set_Fdelay(v))
        self._wire_slider_spinbox(self.ui.sliderCrrc2Pzc, self.ui.spinCrrc2Pzc, lambda v: self._mca.filters.crrc2.set_pzc_coeff(v))

        self.ui.cbCfdEnable.toggled.connect(lambda v: self._mca.filters.cfd.set_enable(v))
        self.ui.spinCfdFactor.editingFinished.connect(lambda: self._mca.filters.cfd.set_factor(self.ui.spinCfdFactor.value()))
        self._wire_slider_spinbox(self.ui.sliderCfdDelay, self.ui.spinCfdDelay, lambda v: self._mca.filters.cfd.set_delay(v))
        self.ui.spinCfdTwLow.editingFinished.connect(lambda: self._mca.filters.cfd.set_time_window_low(self.ui.spinCfdTwLow.value()))
        self.ui.spinCfdTwHigh.editingFinished.connect(lambda: self._mca.filters.cfd.set_time_window_high(self.ui.spinCfdTwHigh.value()))

        self.ui.cbTrapezEnable.toggled.connect(lambda v: self._mca.filters.trapezoid.set_enable(v))
        self._wire_slider_spinbox(self.ui.sliderTrapR, self.ui.spinTrapR, lambda v: self._mca.filters.trapezoid.set_R(v))
        self._wire_slider_spinbox(self.ui.sliderTrapM, self.ui.spinTrapM, lambda v: self._mca.filters.trapezoid.set_M(v))
        self.ui.spinTrapT.editingFinished.connect(lambda: self._mca.filters.trapezoid.set_T(self.ui.spinTrapT.value()))
        self._wire_slider_spinbox(self.ui.sliderTrapE, self.ui.spinTrapE, lambda v: self._mca.filters.trapezoid.set_E(v))
        self.ui.comboTrapFt.currentIndexChanged.connect(lambda i: self._mca.filters.trapezoid.set_FT(i))

        self.ui.cbCcEnable.toggled.connect(lambda v: self._mca.filters.charge_comparison.set_enable(v))
        self.ui.spinCcTime.editingFinished.connect(lambda: self._mca.filters.charge_comparison.set_time(self.ui.spinCcTime.value()))
        self.ui.cbPsdZcEnable.toggled.connect(lambda v: self._mca.filters.psd_zc.set_enable(v))
        self.ui.comboPsdZcMode.currentIndexChanged.connect(lambda i: self._mca.filters.psd_zc.set_mode(i))
        self.ui.spinPsdZcLow.editingFinished.connect(lambda: self._mca.filters.psd_zc.set_time_window_low(self.ui.spinPsdZcLow.value()))
        self.ui.spinPsdZcHigh.editingFinished.connect(lambda: self._mca.filters.psd_zc.set_time_window_high(self.ui.spinPsdZcHigh.value()))

        self.ui.spinTempCoeff.editingFinished.connect(lambda: self._mca.set_temp_coeff(self.ui.spinTempCoeff.value()))
        self.ui.spinTempOffset.editingFinished.connect(lambda: self._mca.set_temp_offset(self.ui.spinTempOffset.value()))

    def _wire_slider_spinbox(
        self,
        slider: QSlider,
        spinbox: QSpinBox,
        set_fn: object,
    ) -> None:
        slider.valueChanged.connect(spinbox.setValue)

        def on_spin_changed(v: int) -> None:
            slider.blockSignals(True)
            slider.setValue(v)
            slider.blockSignals(False)

        spinbox.valueChanged.connect(on_spin_changed)
        spinbox.editingFinished.connect(lambda: set_fn(spinbox.value()))  # type: ignore[operator]
        slider.sliderReleased.connect(lambda: set_fn(spinbox.value()))  # type: ignore[operator]

    # ------------------------------------------------------------------
    # Start / Stop / Clear
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        self._mca.start()
        self.ui.btnStart.setEnabled(False)
        self.ui.btnStop.setEnabled(True)
        self._start_worker()

    def _on_stop(self) -> None:
        self._stop_worker()
        self._mca.stop()
        self.ui.btnStart.setEnabled(True)
        self.ui.btnStop.setEnabled(False)

    def _on_clear_spectrum(self) -> None:
        self._mca.clear_spectrum()

    # ------------------------------------------------------------------
    # Worker lifecycle
    # ------------------------------------------------------------------

    def _start_worker(self) -> None:
        self._worker = MCAWorker(self._mca, interval_ms=200)
        self._worker_thread = QThread(self)
        self._worker.moveToThread(self._worker_thread)

        self._worker_thread.started.connect(self._worker.run)
        self._worker.readback.connect(self._on_readback)
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)
        self._worker_thread.finished.connect(self._on_worker_finished)

        self._worker_thread.start()

    def _stop_worker(self) -> None:
        if self._worker is not None:
            self._worker.request_stop.emit()

    def _on_worker_finished(self) -> None:
        self._worker = None
        self._worker_thread = None

    def stop_worker_sync(self) -> None:
        """Blocking stop for use during application shutdown only."""
        if self._worker is not None:
            self._worker.request_stop.emit()
        if self._worker_thread is not None:
            if not self._worker_thread.wait(3000):
                log.warning("MCA worker thread did not stop in time, terminating")
                self._worker_thread.terminate()
                self._worker_thread.wait()
            self._worker_thread = None
            self._worker = None

    # ------------------------------------------------------------------
    # Readback handling
    # ------------------------------------------------------------------

    def _on_readback(self, rb: MCAReadback) -> None:
        self._update_debug_plot(rb.debug1, rb.debug2)
        self._update_histogram(rb.histogram)
        self._update_statistics(rb)

    def _update_debug_plot(self, debug1: np.ndarray, debug2: np.ndarray) -> None:
        print(debug1)
        print(sum(debug1))
        print(debug2)
        print(sum(debug2))
        if debug1 is not None and len(debug1) > 0:
            t1 = np.arange(0, 8 * len(debug1), 8)
            self._debug1_curve.setData(t1, debug1)
        if debug2 is not None and len(debug2) > 0:
            t2 = np.arange(0, 8 * len(debug2), 8)
            self._debug2_curve.setData(t2, debug2)

    def _update_histogram(self, histogram: np.ndarray) -> None:
        print(histogram)
        print(sum(histogram))
        if histogram is None or len(histogram) == 0:
            return
        channels = np.arange(len(histogram) + 1)
        self._hist_curve.setData(channels, histogram)

    def _update_statistics(self, rb: MCAReadback) -> None:
        self.ui.lblCountRate.setText(str(rb.count_rate))
        self.ui.lblDeadTime.setText(str(rb.pulse_deadtime))
        self.ui.lblElapsedTime.setText(str(rb.elapsed_time))
        self.ui.lblEventsLost.setText(str(rb.events_lost))
        self.ui.lblPulsePileup.setText(str(rb.pulse_pileup))
        self.ui.lblPulseOverrange.setText(str(rb.pulse_overrange))
        self.ui.lblEnergyOverrange.setText(str(rb.energy_overrange))
        self.ui.lblEnergyEstErr.setText(str(rb.energy_estimation_error))
        self.ui.lblThroughputErr.setText(str(rb.throughput_error))
