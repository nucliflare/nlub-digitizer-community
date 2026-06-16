from __future__ import annotations

from PySide6.QtWidgets import QSlider, QSpinBox, QWidget

from nlab.hardware.digitizer.scope import (
    ListSpec,
    RangeSpec,
    Scope,
    ScopeParam,
    TriggerMode,
)
from nlab.ui.ui_scope_view import Ui_ScopeView


class ScopeController(QWidget):
    """View + controller for a single Scope channel.

    Loaded from ui_scope_view.ui.  Drop into any QTabWidget via addTab().
    Widget ranges and defaults are driven entirely by Scope.specs at runtime.
    """

    def __init__(self, scope: Scope, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scope = scope
        self._ui = Ui_ScopeView()
        self._ui.setupUi(self)
        self._apply_parameter_specs()   # set ranges/defaults before any signal is wired
        self._connect_signals()

    # ------------------------------------------------------------------
    # Spec application — runs before signals are connected
    # ------------------------------------------------------------------

    def _apply_parameter_specs(self) -> None:
        specs = self._scope.specs

        # ── Trigger level (RangeSpec) — spinbox + slider ──
        spec = specs[ScopeParam.TRIGGER_LEVEL]
        assert isinstance(spec, RangeSpec)
        self._apply_range_to_spinbox(self._ui.spinTriggerLevel, spec)
        self._apply_range_to_slider(self._ui.sliderTriggerLevel, spec)

        # ── DAC offset (RangeSpec) — spinbox + slider ──
        spec = specs[ScopeParam.DAC_VALUE]
        assert isinstance(spec, RangeSpec)
        self._apply_range_to_spinbox(self._ui.spinDacValue, spec)
        self._apply_range_to_slider(self._ui.sliderDacValue, spec)

        # ── Pretrigger samples (RangeSpec) — spinbox only ──
        spec = specs[ScopeParam.PRETRIGGER_SAMPLES]
        assert isinstance(spec, RangeSpec)
        self._apply_range_to_spinbox(self._ui.spinPretrigger, spec)

        # ── Frame samples (RangeSpec) — spinbox only ──
        spec = specs[ScopeParam.FRAME_SAMPLES]
        assert isinstance(spec, RangeSpec)
        self._apply_range_to_spinbox(self._ui.spinFrameSamples, spec)

        # ── Trigger mode (ListSpec) — combobox ──
        spec = specs[ScopeParam.EDGE_MODE]
        assert isinstance(spec, ListSpec)
        if spec.default in spec.items:
            self._ui.comboTriggerMode.setCurrentIndex(
                list(spec.items).index(spec.default)
            )

        # ── DMA enable (ListSpec) — checkbox ──
        spec = specs[ScopeParam.DMA_ENABLED]
        assert isinstance(spec, ListSpec)
        self._ui.cbDmaEnable.setChecked(bool(spec.default))

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
            self._ui.sliderTriggerLevel,
            self._ui.spinTriggerLevel,
            lambda v: self._scope.set_trigger_level(v),
        )
        self._wire_slider_spinbox(
            self._ui.sliderDacValue,
            self._ui.spinDacValue,
            lambda v: self._scope.set_dac_value(v),
        )

        self._ui.spinPretrigger.valueChanged.connect(
            lambda v: self._scope.set_pretrigger_samples(v)
        )
        self._ui.spinFrameSamples.valueChanged.connect(
            lambda v: self._scope.set_frame_samples(v)
        )
        self._ui.comboTriggerMode.currentIndexChanged.connect(
            lambda i: self._scope.set_trigger_mode(TriggerMode(i))
        )
        self._ui.cbDmaEnable.toggled.connect(
            lambda v: self._scope.set_dma_enable(v)
        )
        self._ui.btnStart.clicked.connect(self._on_start)
        self._ui.btnStop.clicked.connect(self._on_stop)
        self._ui.btnAcquireFrame.clicked.connect(self._on_acquire_frame)

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
        self._ui.btnStart.setEnabled(False)
        self._ui.btnStop.setEnabled(True)

    def _on_stop(self) -> None:
        self._scope.stop()
        self._ui.btnStart.setEnabled(True)
        self._ui.btnStop.setEnabled(False)

    def _on_acquire_frame(self) -> None:
        _frame = self._scope.acquire_frame()
        # TODO: pass frame to waveformDisplay plot widget
