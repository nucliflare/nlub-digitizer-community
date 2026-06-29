from __future__ import annotations

import logging
import time
from enum import IntEnum
from pathlib import Path

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QRectF, QThread, QThreadPool, QTimer
from PySide6.QtWidgets import QFileDialog, QSlider, QSpinBox, QWidget

from nlab.hardware.digitizer.dma import ScopeDmaStreamer
from nlab.hardware.digitizer.scope import (
    ListSpec,
    RangeSpec,
    Scope,
    ScopeParam,
    TriggerMode,
)
from nlab.ui.ui_scope_view import Ui_ScopeView
from nlab.views.plot_viewbox import ModifierZoomViewBox
from nlab.workers.dma_workers import ScopeDmaWorker
from nlab.workers.scope_worker import ScopeWorker

log = logging.getLogger(__name__)


class DisplayMode(IntEnum):
    PERSISTENCE = 0
    RAW = 1


class ScopeController(QWidget):
    """View + controller for a single Scope channel.

    Loaded from ui_scope_view.ui.  Drop into any QTabWidget via addTab().
    Widget ranges and defaults are driven entirely by Scope.specs at runtime.
    """

    _Y_SCALE_FACTOR = 10
    _Y_MIN = -32_000
    _Y_MAX = 32_000

    def __init__(
        self,
        scope: Scope,
        scope_dma: ScopeDmaStreamer | None = None,
        channel: int = 1,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._scope = scope
        self._scope_dma = scope_dma
        self._channel = channel
        self.ui = Ui_ScopeView()
        self.ui.setupUi(self)

        self._acquiring = False
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._request_frame)

        self._dma_worker: ScopeDmaWorker | None = None
        self._dma_thread: QThread | None = None
        self._dma_filepath: Path | None = None
        self._dma_counter = 0

        self._apply_parameter_specs()
        self._send_defaults()
        self._load_hardware_state()
        self._setup_graph()
        self._connect_signals()

    # ------------------------------------------------------------------
    # Spec application
    # ------------------------------------------------------------------

    def _apply_parameter_specs(self) -> None:
        specs = self._scope.specs

        spec = specs[ScopeParam.TRIGGER_LEVEL]
        assert isinstance(spec, RangeSpec)
        self._apply_range_to_spinbox(self.ui.spinTriggerLevel, spec)
        self._apply_range_to_slider(self.ui.sliderTriggerLevel, spec)

        spec = specs[ScopeParam.DAC_VALUE]
        assert isinstance(spec, RangeSpec)
        self._apply_range_to_spinbox(self.ui.spinDacValue, spec)
        self._apply_range_to_slider(self.ui.sliderDacValue, spec)

        spec = specs[ScopeParam.PRETRIGGER_SAMPLES]
        assert isinstance(spec, RangeSpec)
        self._apply_range_to_spinbox(self.ui.spinPretrigger, spec)

        spec = specs[ScopeParam.FRAME_SAMPLES]
        assert isinstance(spec, RangeSpec)
        self._apply_range_to_spinbox(self.ui.spinFrameSamples, spec)

        spec = specs[ScopeParam.EDGE_MODE]
        assert isinstance(spec, ListSpec)
        if spec.default in spec.items:
            self.ui.comboTriggerMode.setCurrentIndex(list(spec.items).index(spec.default))

        spec = specs[ScopeParam.DMA_ENABLED]
        assert isinstance(spec, ListSpec)
        self.ui.cbDmaEnable.setChecked(bool(spec.default))

    @staticmethod
    def _apply_range_to_spinbox(spinbox: QSpinBox, spec: RangeSpec) -> None:
        spinbox.setMinimum(int(spec.min_val))
        spinbox.setMaximum(int(spec.max_val))
        spinbox.setSingleStep(int(spec.step) or 1)
        spinbox.setValue(int(spec.default))

    @staticmethod
    def _apply_range_to_slider(slider: QSlider, spec: RangeSpec) -> None:
        slider.setMinimum(int(spec.min_val))
        slider.setMaximum(int(spec.max_val))
        slider.setSingleStep(int(spec.step) or 1)
        slider.setValue(int(spec.default))

    # ------------------------------------------------------------------
    # Write defaults to hardware, then read back
    # ------------------------------------------------------------------

    def _send_defaults(self) -> None:
        specs = self._scope.specs
        self._scope.set_trigger_level(int(specs[ScopeParam.TRIGGER_LEVEL].default))
        self._scope.set_dac_value(int(specs[ScopeParam.DAC_VALUE].default))
        self._scope.set_pretrigger_samples(int(specs[ScopeParam.PRETRIGGER_SAMPLES].default))
        self._scope.set_frame_samples(int(specs[ScopeParam.FRAME_SAMPLES].default))
        self._scope.set_trigger_mode(TriggerMode(specs[ScopeParam.EDGE_MODE].default))
        self._scope.set_dma_enable(bool(specs[ScopeParam.DMA_ENABLED].default))

    def _load_hardware_state(self) -> None:
        self.ui.spinTriggerLevel.setValue(self._scope.get_trigger_level())
        self.ui.sliderTriggerLevel.setValue(self._scope.get_trigger_level())
        self.ui.spinDacValue.setValue(self._scope.get_dac_value())
        self.ui.sliderDacValue.setValue(self._scope.get_dac_value())
        self.ui.spinPretrigger.setValue(self._scope.get_pretrigger_samples())
        self.ui.spinFrameSamples.setValue(self._scope.get_frame_samples())
        self.ui.comboTriggerMode.setCurrentIndex(self._scope.get_trigger_mode().value)
        self.ui.cbDmaEnable.setChecked(self._scope.get_dma_enable())

    # ------------------------------------------------------------------
    # Signal wiring (identical to working version + DMA buttons)
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self._wire_slider_spinbox(
            self.ui.sliderTriggerLevel,
            self.ui.spinTriggerLevel,
            lambda v: self._scope.set_trigger_level(v),
        )
        self._wire_slider_spinbox(
            self.ui.sliderDacValue,
            self.ui.spinDacValue,
            lambda v: self._scope.set_dac_value(v),
        )

        self.ui.spinPretrigger.editingFinished.connect(lambda: self._scope.set_pretrigger_samples(self.ui.spinPretrigger.value()))
        self.ui.spinFrameSamples.editingFinished.connect(self._on_frame_samples_changed)
        self.ui.comboTriggerMode.currentIndexChanged.connect(lambda i: self._scope.set_trigger_mode(TriggerMode(i)))
        self.ui.cbDmaEnable.toggled.connect(lambda v: self._scope.set_dma_enable(v))
        self.ui.btnStart.clicked.connect(self._on_start)
        self.ui.btnStop.clicked.connect(self._on_stop)
        self.ui.btnAcquireFrame.clicked.connect(self._on_acquire_frame)

        self.ui.btnRecord.toggled.connect(self._on_record_toggled)
        self.ui.btnRecordFile.clicked.connect(self._on_record_file)

        self.ui.comboDisplayMode.currentIndexChanged.connect(self._on_display_mode_changed)
        self.ui.dialPersistence.valueChanged.connect(self._on_persistence_changed)
        self.ui.spinRefreshRate.valueChanged.connect(self._on_refresh_rate_changed)

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

        def on_spin_committed() -> None:
            set_fn(spinbox.value())  # type: ignore[operator]

        def on_slider_released() -> None:
            set_fn(spinbox.value())  # type: ignore[operator]

        spinbox.valueChanged.connect(on_spin_changed)
        spinbox.editingFinished.connect(on_spin_committed)
        slider.sliderReleased.connect(on_slider_released)

    # ------------------------------------------------------------------
    # Slots (restored to working version)
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        self._scope.start()
        self.ui.btnStart.setEnabled(False)
        self.ui.btnStop.setEnabled(True)
        self.ui.btnAcquireFrame.setEnabled(False)
        interval_ms = 1000 // self.ui.spinRefreshRate.value()
        self._refresh_timer.start(interval_ms)
        log.info("Scope ch%d: acquisition started (refresh %d ms)", self._channel, interval_ms)

    def _on_stop(self) -> None:
        self._refresh_timer.stop()
        if self.ui.btnRecord.isChecked():
            self.ui.btnRecord.setChecked(False)
        self._scope.stop()
        self._acquiring = False
        self.ui.btnStart.setEnabled(True)
        self.ui.btnStop.setEnabled(False)
        self.ui.btnAcquireFrame.setEnabled(True)
        log.info("Scope ch%d: acquisition stopped", self._channel)

    def _on_refresh_rate_changed(self, value: int) -> None:
        if self._refresh_timer.isActive():
            self._refresh_timer.setInterval(1000 // value)

    def _request_frame(self) -> None:
        if self._acquiring:
            return
        self._acquiring = True
        worker = ScopeWorker(self._scope)
        worker.signals.ready.connect(self._on_frame_received)
        QThreadPool.globalInstance().start(worker)

    def _on_frame_received(self, data: list[np.ndarray]) -> None:
        self._acquiring = False
        if data is None:
            return
        x_time, y_voltage = data
        if self._display_mode == DisplayMode.RAW:
            self._raw_curve.setData(x_time, y_voltage)
        else:
            self._rasterize_frame(y_voltage)
            self._persistence_img.setImage(self._persistence_buffer, autoLevels=False, levels=(0, 1))

    def _on_frame_samples_changed(self) -> None:
        value = self.ui.spinFrameSamples.value()
        self._scope.set_frame_samples(value)
        self._display_nx = value // 8
        self._display_ny = self._display_nx * self._Y_SCALE_FACTOR
        self._persistence_buffer = np.zeros((self._display_nx, self._display_ny), dtype=np.float32)
        self._update_axis_ranges()

    def _on_acquire_frame(self) -> None:
        raw_frame = self._scope.acquire_frame()
        value = self.ui.spinFrameSamples.value()
        frame = raw_frame[: value // 8]
        time_arr = np.arange(0, 8 * len(frame), 8)
        if self._display_mode == DisplayMode.RAW:
            self._raw_curve.setData(time_arr, frame)
        else:
            self._rasterize_frame(frame)
            self._persistence_img.setImage(self._persistence_buffer, autoLevels=False, levels=(0, 1))

    def _rasterize_frame(self, frame: np.ndarray) -> None:
        self._persistence_buffer *= self.persistence
        n_samples = len(frame)
        x_indices = np.linspace(0, self._display_nx - 1, n_samples).astype(int)
        y_indices = np.clip(
            ((frame.astype(np.float32) - self._Y_MIN) / (self._Y_MAX - self._Y_MIN) * (self._display_ny - 1)).astype(int),
            0,
            self._display_ny - 1,
        )
        self._persistence_buffer[x_indices, y_indices] = 1.0

    # ------------------------------------------------------------------
    # Graph setup
    # ------------------------------------------------------------------

    def _setup_graph(self) -> None:
        self._setup_plot_layout()
        self._setup_persistence_layer()
        self._setup_raw_layer()
        self._update_axis_ranges()
        self._set_display_mode(DisplayMode(self.ui.comboDisplayMode.currentIndex()))

    def _setup_plot_layout(self) -> None:
        layout = pg.GraphicsLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        self.ui.plotWaveform.setCentralItem(layout)
        self.ui.plotWaveform.setBackground("#f8f9fa")

        layout.addLabel("Amplitude", angle=-90)
        self._plot_item = layout.addPlot(viewBox=ModifierZoomViewBox())
        self._plot_item.showAxis("right")
        self._plot_item.showAxis("top")
        self._plot_item.showGrid(x=True, y=True, alpha=0.2)
        layout.nextRow()
        layout.addLabel("Time [ns]", col=1)

    def _setup_persistence_layer(self) -> None:
        self._display_nx = self.ui.spinFrameSamples.value() // 8
        self._display_ny = self._display_nx * self._Y_SCALE_FACTOR
        self._persistence_buffer = np.zeros((self._display_nx, self._display_ny), dtype=np.float32)
        self._persistence_img = pg.ImageItem()
        self._persistence_img.setImage(self._persistence_buffer, autoLevels=False, levels=(0, 1))
        self._persistence_img.setColorMap("viridis")
        self._plot_item.addItem(self._persistence_img)

    def _setup_raw_layer(self) -> None:
        self._raw_curve = self._plot_item.plot(pen=pg.mkPen("#00bfff", width=1))
        self._raw_curve.setVisible(False)

    def _update_axis_ranges(self) -> None:
        frame = self.ui.spinFrameSamples.value()
        vb = self._plot_item.getViewBox()
        vb.setXRange(0, frame, padding=0)
        vb.setYRange(self._Y_MIN, self._Y_MAX, padding=0)
        self._persistence_img.setRect(QRectF(0, self._Y_MIN, frame, self._Y_MAX - self._Y_MIN))

    # ------------------------------------------------------------------
    # Display mode
    # ------------------------------------------------------------------

    def _set_display_mode(self, mode: DisplayMode) -> None:
        self._display_mode = mode
        is_persistence = mode == DisplayMode.PERSISTENCE
        self._persistence_img.setVisible(is_persistence)
        self._raw_curve.setVisible(not is_persistence)
        self.ui.dialPersistence.setEnabled(is_persistence)
        self.ui.labelPersistenceValue.setEnabled(is_persistence)

    def _on_display_mode_changed(self, index: int) -> None:
        self._set_display_mode(DisplayMode(index))

    def _on_persistence_changed(self, value: int) -> None:
        self.ui.labelPersistenceValue.setText(f"{value / 1000:.3f}")

    @property
    def persistence(self) -> float:
        return self.ui.dialPersistence.value() / 1000.0

    # ------------------------------------------------------------------
    # DMA recording
    # ------------------------------------------------------------------

    def _generate_filepath(self) -> Path:
        measurements = Path("measurements")
        measurements.mkdir(exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        self._dma_counter += 1
        name = f"scope_ch{self._channel}_{ts}_{self._dma_counter:03d}.bin"
        filepath = measurements / name
        log.info("Scope DMA: auto-generated filepath: %s", filepath)
        return filepath

    def _on_record_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Scope DMA Recording",
            "",
            "Binary files (*.bin);;All files (*)",
        )
        if path:
            self._dma_filepath = Path(path)
            log.info("Scope DMA: user selected filepath: %s", self._dma_filepath)

    def _on_record_toggled(self, checked: bool) -> None:
        if checked:
            self._start_dma()
        else:
            self._stop_dma()

    def _start_dma(self) -> None:
        if self._scope_dma is None:
            log.warning("Scope DMA: no streamer configured")
            self.ui.btnRecord.setChecked(False)
            return

        filepath = self._dma_filepath or self._generate_filepath()
        frame_samples = self.ui.spinFrameSamples.value()
        log.debug("Scope ch%d DMA [1/6]: creating worker, file=%s, frame_samples=%d",
                  self._channel, filepath, frame_samples)

        self._dma_worker = ScopeDmaWorker(
            streamer=self._scope_dma,
            filepath=filepath,
            frame_samples=frame_samples,
        )
        self._dma_thread = QThread(self)
        self._dma_worker.moveToThread(self._dma_thread)

        self._dma_thread.started.connect(self._dma_worker.run)
        self._dma_worker.ready.connect(self._on_dma_ready)
        self._dma_worker.progress.connect(self._on_dma_progress)
        self._dma_worker.error.connect(self._on_dma_error)
        self._dma_worker.finished.connect(self._dma_thread.quit)
        self._dma_worker.finished.connect(self._dma_worker.deleteLater)
        self._dma_thread.finished.connect(self._dma_thread.deleteLater)
        self._dma_thread.finished.connect(self._on_dma_finished)

        self.ui.btnStart.setEnabled(False)
        self.ui.btnStop.setEnabled(False)
        self.ui.btnAcquireFrame.setEnabled(False)
        self.ui.lblRecordingStatus.setText("Connecting...")
        log.debug("Scope ch%d DMA [2/6]: starting worker thread (ZMQ connect + subscribe)",
                  self._channel)
        self._dma_thread.start()
        log.info("Scope DMA: worker started, waiting for socket ready, file=%s", filepath)

    def _on_dma_ready(self) -> None:
        log.debug("Scope ch%d DMA [3/6]: ZMQ socket ready, enabling DMA on hardware",
                  self._channel)
        self._scope.set_dma_enable(True)
        log.debug("Scope ch%d DMA [4/6]: DMA enabled, calling scope.start() -> set_enable(True) "
                  "(HW fires start_irq -> server sends StreamSTART)", self._channel)
        self._scope.start()
        log.debug("Scope ch%d DMA [5/6]: scope started, beginning display polling",
                  self._channel)
        interval_ms = 1000 // self.ui.spinRefreshRate.value()
        self._refresh_timer.start(interval_ms)
        self.ui.btnStop.setEnabled(True)
        self.ui.lblRecordingStatus.setText("Recording...")
        log.info("Scope ch%d: DMA enabled + acquisition started (socket was ready)", self._channel)

    def _stop_dma(self) -> None:
        log.debug("Scope ch%d DMA stop [1/4]: stopping display polling", self._channel)
        self._refresh_timer.stop()
        log.debug("Scope ch%d DMA stop [2/4]: signalling worker to stop (stop_event.set())",
                  self._channel)
        if self._dma_worker is not None:
            self._dma_worker.stop()
        log.debug("Scope ch%d DMA stop [3/4]: disabling DMA on hardware", self._channel)
        self._scope.set_dma_enable(False)
        log.debug("Scope ch%d DMA stop [4/4]: calling scope.stop() -> set_enable(False) "
                  "(HW fires stop_irq -> server sends StreamEND)", self._channel)
        self._scope.stop()
        self._acquiring = False
        self.ui.btnStart.setEnabled(True)
        self.ui.btnStop.setEnabled(False)
        self.ui.btnAcquireFrame.setEnabled(True)
        log.info("Scope ch%d: DMA disabled + acquisition stopped", self._channel)

    def _on_dma_progress(self, bytes_written: int) -> None:
        if bytes_written < 1024 * 1024:
            self.ui.lblRecordingStatus.setText(f"Recording: {bytes_written / 1024:.1f} KB")
        else:
            self.ui.lblRecordingStatus.setText(f"Recording: {bytes_written / (1024 * 1024):.1f} MB")

    def _on_dma_error(self, message: str) -> None:
        log.error("Scope DMA error: %s", message)
        self.ui.lblRecordingStatus.setText(f"Error: {message}")
        self.ui.btnRecord.setChecked(False)

    def _on_dma_finished(self) -> None:
        self._dma_worker = None
        self._dma_thread = None
        if not self.ui.btnRecord.isChecked():
            self.ui.lblRecordingStatus.setText("Stopped")
        log.info("Scope DMA: worker finished")

    def stop_dma_sync(self) -> None:
        """Blocking stop for use during application shutdown only."""
        worker = self._dma_worker
        thread = self._dma_thread
        if worker is not None:
            worker.stop()
        if thread is not None:
            if not thread.wait(3000):
                log.warning("Scope DMA thread did not stop in time, terminating")
                thread.terminate()
                thread.wait()
        self._dma_thread = None
        self._dma_worker = None
