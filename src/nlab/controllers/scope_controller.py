from __future__ import annotations

import logging
from enum import IntEnum

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QObject, QRectF, QRunnable, QThreadPool, QTimer, Signal
from PySide6.QtWidgets import QSlider, QSpinBox, QWidget

from nlab.hardware.digitizer.scope import (
    ListSpec,
    RangeSpec,
    Scope,
    ScopeParam,
    TriggerMode,
)
from nlab.ui.ui_scope_view import Ui_ScopeView

log = logging.getLogger(__name__)


class DisplayMode(IntEnum):
    PERSISTENCE = 0
    RAW = 1


class _FrameSignals(QObject):
    ready = Signal(object)


class _FrameWorker(QRunnable):
    def __init__(self, scope_controller: ScopeController) -> None:
        super().__init__()
        self.signals = _FrameSignals()
        self.controller = scope_controller
        self.setAutoDelete(True)

    def run(self) -> None:
        try:
            frame_size = self.controller.ui.spinFrameSamples.value()
            raw_frame = self.controller._scope.acquire_frame()[:frame_size]
            raw_time = raw_time = np.arange(0, 8 * len(raw_frame), 8)
            data = [raw_time, raw_frame]
            self.signals.ready.emit(data)
        except Exception:
            log.exception("Frame acquisition failed")
            self.signals.ready.emit(None)


class ScopeController(QWidget):
    """View + controller for a single Scope channel.

    Loaded from ui_scope_view.ui.  Drop into any QTabWidget via addTab().
    Widget ranges and defaults are driven entirely by Scope.specs at runtime.
    """

    _DISPLAY_NX = 768
    _DISPLAY_NY = 768
    _Y_MIN = -32_000
    _Y_MAX = 32_000

    def __init__(self, scope: Scope, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scope = scope
        self.ui = Ui_ScopeView()
        self.ui.setupUi(self)

        self._acquiring = False
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._request_frame)

        self._apply_parameter_specs()
        self._setup_graph()
        self._connect_signals()

    # ------------------------------------------------------------------
    # Spec application — runs before signals are connected
    # ------------------------------------------------------------------

    def _apply_parameter_specs(self) -> None:
        specs = self._scope.specs

        # ── Trigger level (RangeSpec) — spinbox + slider ──
        spec = specs[ScopeParam.TRIGGER_LEVEL]
        assert isinstance(spec, RangeSpec)
        self._apply_range_to_spinbox(self.ui.spinTriggerLevel, spec)
        self._apply_range_to_slider(self.ui.sliderTriggerLevel, spec)

        # ── DAC offset (RangeSpec) — spinbox + slider ──
        spec = specs[ScopeParam.DAC_VALUE]
        assert isinstance(spec, RangeSpec)
        self._apply_range_to_spinbox(self.ui.spinDacValue, spec)
        self._apply_range_to_slider(self.ui.sliderDacValue, spec)

        # ── Pretrigger samples (RangeSpec) — spinbox only ──
        spec = specs[ScopeParam.PRETRIGGER_SAMPLES]
        assert isinstance(spec, RangeSpec)
        self._apply_range_to_spinbox(self.ui.spinPretrigger, spec)

        # ── Frame samples (RangeSpec) — spinbox only ──
        spec = specs[ScopeParam.FRAME_SAMPLES]
        assert isinstance(spec, RangeSpec)
        self._apply_range_to_spinbox(self.ui.spinFrameSamples, spec)

        # ── Trigger mode (ListSpec) — combobox ──
        spec = specs[ScopeParam.EDGE_MODE]
        assert isinstance(spec, ListSpec)
        if spec.default in spec.items:
            self.ui.comboTriggerMode.setCurrentIndex(list(spec.items).index(spec.default))

        # ── DMA enable (ListSpec) — checkbox ──
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
    # Signal wiring
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

        self.ui.spinPretrigger.valueChanged.connect(lambda v: self._scope.set_pretrigger_samples(v))
        self.ui.spinFrameSamples.valueChanged.connect(self._on_frame_samples_changed)
        self.ui.comboTriggerMode.currentIndexChanged.connect(lambda i: self._scope.set_trigger_mode(TriggerMode(i)))
        self.ui.cbDmaEnable.toggled.connect(lambda v: self._scope.set_dma_enable(v))
        self.ui.btnStart.clicked.connect(self._on_start)
        self.ui.btnStop.clicked.connect(self._on_stop)
        self.ui.btnAcquireFrame.clicked.connect(self._on_acquire_frame)

        self.ui.comboDisplayMode.currentIndexChanged.connect(self._on_display_mode_changed)
        self.ui.dialPersistence.valueChanged.connect(self._on_persistence_changed)
        self.ui.spinRefreshRate.valueChanged.connect(self._on_refresh_rate_changed)

    def _wire_slider_spinbox(
        self,
        slider: QSlider,
        spinbox: QSpinBox,
        set_fn: object,
    ) -> None:
        """Bidirectional sync with a single hardware call per user gesture.

        Slider drag updates spinbox display only; hardware is called on
        sliderReleased.  Spinbox changes update the slider display via
        blockSignals (no loop) and call hardware immediately.
        """
        slider.valueChanged.connect(spinbox.setValue)

        def on_spin_changed(v: int) -> None:
            slider.blockSignals(True)
            slider.setValue(v)
            slider.blockSignals(False)
            set_fn(v)  # type: ignore[operator]

        def on_slider_released() -> None:
            set_fn(spinbox.value())  # type: ignore[operator]

        spinbox.valueChanged.connect(on_spin_changed)
        slider.sliderReleased.connect(on_slider_released)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        self._scope.start()
        self.ui.btnStart.setEnabled(False)
        self.ui.btnStop.setEnabled(True)
        self.ui.btnAcquireFrame.setEnabled(False)
        interval_ms = 1000 // self.ui.spinRefreshRate.value()
        self._refresh_timer.start(interval_ms)

    def _on_stop(self) -> None:
        self._refresh_timer.stop()
        self._scope.stop()
        self._acquiring = False
        self.ui.btnStart.setEnabled(True)
        self.ui.btnStop.setEnabled(False)
        self.ui.btnAcquireFrame.setEnabled(True)

    def _on_refresh_rate_changed(self, value: int) -> None:
        if self._refresh_timer.isActive():
            self._refresh_timer.setInterval(1000 // value)

    def _request_frame(self) -> None:
        if self._acquiring:
            return
        self._acquiring = True
        worker = _FrameWorker(self)
        worker.signals.ready.connect(self._on_frame_received)
        QThreadPool.globalInstance().start(worker)

    def _on_frame_received(self, data: list[np.ndarray] | None) -> None:
        self._acquiring = False
        if data is None:
            return
        if self._display_mode == DisplayMode.RAW:
            self._raw_curve.setData(*data)
        else:
            self._rasterize_frame(data[1])
            self._persistence_img.setImage(self._persistence_buffer, autoLevels=False, levels=(0, 1))

    def _on_frame_samples_changed(self, value: int) -> None:
        self._scope.set_frame_samples(value)
        self._update_axis_ranges()

    def _on_acquire_frame(self) -> None:
        frame = self._scope.acquire_frame()
        if self._display_mode == DisplayMode.RAW:
            self._raw_curve.setData(frame)
        else:
            self._rasterize_frame(frame)
            self._persistence_img.setImage(self._persistence_buffer, autoLevels=False, levels=(0, 1))

    def _rasterize_frame(self, frame: np.ndarray) -> None:
        self._persistence_buffer *= self.persistence
        n_samples = len(frame)
        x_indices = np.linspace(0, self._DISPLAY_NX - 1, n_samples).astype(int)
        y_indices = np.clip(
            ((frame.astype(np.float32) - self._Y_MIN) / (self._Y_MAX - self._Y_MIN) * (self._DISPLAY_NY - 1)).astype(int),
            0,
            self._DISPLAY_NY - 1,
        )
        self._persistence_buffer[y_indices, x_indices] = 1.0

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
        self._plot_item = layout.addPlot()
        self._plot_item.showAxis("right")
        self._plot_item.showAxis("top")
        self._plot_item.showGrid(x=True, y=True, alpha=0.2)
        layout.nextRow()
        layout.addLabel("Time [ns]", col=1)

    def _setup_persistence_layer(self) -> None:
        self._persistence_buffer = np.zeros((self._DISPLAY_NY, self._DISPLAY_NX), dtype=np.float32)
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
