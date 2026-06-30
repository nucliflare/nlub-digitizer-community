from __future__ import annotations

import logging

from nlab_modbus.core.base_modbus_device import BaseModbusDevice
from nlab_modbus.core.register_specs import RegisterSpec, RegisterType
from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QDoubleSpinBox,
    QGroupBox,
    QHeaderView,
    QLabel,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from nlab.workers.external_device_worker import ExternalDeviceWorker

log = logging.getLogger(__name__)


def _is_boolean_spec(spec: RegisterSpec) -> bool:
    return spec.scale == 1.0 and spec.min == 0 and spec.max == 1


class ExternalDeviceController(QWidget):
    """View + controller for one external Modbus device (SiPM / Geiger / PMT HV PSU).

    Built generically from the device's REGISTER_MAP rather than a hand-built
    form per device type — holding registers become an editable settings
    table, input registers become a read-only, periodically-refreshed
    telemetry table. Works for any BaseModbusDevice subclass unchanged.
    """

    def __init__(self, device: BaseModbusDevice, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.device = device

        self._worker: ExternalDeviceWorker | None = None
        self._worker_thread: QThread | None = None
        self._row_by_name: dict[str, int] = {}

        self._build_ui()
        self._load_settings()
        self.start_polling()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        header = QLabel(f"{self.device.device_type.name}  —  {self.device.connection_info()}")
        header.setStyleSheet("font-weight: bold; padding: 2px;")
        layout.addWidget(header)

        settings_box = QGroupBox("Settings")
        settings_layout = QVBoxLayout(settings_box)
        self.settingsTable = self._make_table()
        settings_layout.addWidget(self.settingsTable)
        layout.addWidget(settings_box)

        telemetry_box = QGroupBox("Telemetry")
        telemetry_layout = QVBoxLayout(telemetry_box)
        self.telemetryTable = self._make_table(editable=False)
        telemetry_layout.addWidget(self.telemetryTable)
        layout.addWidget(telemetry_box)

        self._populate_settings_rows()
        self._populate_telemetry_rows()

    @staticmethod
    def _make_table(editable: bool = True) -> QTableWidget:
        table = QTableWidget(0, 3)
        table.setHorizontalHeaderLabels(["Register", "Value", "Unit"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        table.verticalHeader().setVisible(False)
        if not editable:
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        return table

    def _holding_specs(self) -> list[tuple[str, RegisterSpec]]:
        items = self.device.REGISTER_MAP.items()
        return [(n, s) for n, s in items if s.reg_type == RegisterType.HOLDING]

    def _input_specs(self) -> list[tuple[str, RegisterSpec]]:
        items = self.device.REGISTER_MAP.items()
        return [(n, s) for n, s in items if s.reg_type == RegisterType.INPUT]

    def _populate_settings_rows(self) -> None:
        specs = self._holding_specs()
        self.settingsTable.setRowCount(len(specs))
        for row, (name, spec) in enumerate(specs):
            self.settingsTable.setItem(row, 0, QTableWidgetItem(name))
            self.settingsTable.setItem(row, 2, QTableWidgetItem(spec.unit or ""))
            self.settingsTable.setCellWidget(row, 1, self._make_editor(name, spec))
            self._row_by_name[f"settings:{name}"] = row

    def _populate_telemetry_rows(self) -> None:
        specs = self._input_specs()
        self.telemetryTable.setRowCount(len(specs))
        for row, (name, spec) in enumerate(specs):
            self.telemetryTable.setItem(row, 0, QTableWidgetItem(name))
            self.telemetryTable.setItem(row, 1, QTableWidgetItem(""))
            self.telemetryTable.setItem(row, 2, QTableWidgetItem(spec.unit or ""))
            self._row_by_name[f"telemetry:{name}"] = row

    def _make_editor(self, name: str, spec: RegisterSpec) -> QAbstractSpinBox | QCheckBox:
        if _is_boolean_spec(spec):
            box = QCheckBox()
            box.toggled.connect(lambda v, n=name: self._on_setting_changed(n, int(v)))
            return box
        editor: QAbstractSpinBox
        if spec.scale != 1.0:
            double_editor = QDoubleSpinBox()
            double_editor.setDecimals(4)
            double_editor.setRange(spec.min * spec.scale, spec.max * spec.scale)
            double_editor.setSingleStep(spec.scale)
            double_editor.editingFinished.connect(
                lambda n=name, e=double_editor: self._on_setting_changed(n, e.value()))
            editor = double_editor
        else:
            int_editor = QSpinBox()
            int_editor.setRange(spec.min, spec.max)
            int_editor.editingFinished.connect(
                lambda n=name, e=int_editor: self._on_setting_changed(n, e.value()))
            editor = int_editor
        return editor

    # ------------------------------------------------------------------
    # Initial hardware readout
    # ------------------------------------------------------------------

    def _load_settings(self) -> None:
        try:
            values = self.device.get_all_holding_registers()
        except Exception:
            log.exception("Failed to read initial settings for %s", self.device.connection_info())
            return
        for name, value in values.items():
            row = self._row_by_name.get(f"settings:{name}")
            if row is None:
                continue
            widget = self.settingsTable.cellWidget(row, 1)
            if widget is None:
                continue
            widget.blockSignals(True)
            try:
                if isinstance(widget, QCheckBox):
                    widget.setChecked(bool(value))
                elif isinstance(widget, QDoubleSpinBox | QSpinBox):
                    widget.setValue(value)
            finally:
                widget.blockSignals(False)

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def _on_setting_changed(self, name: str, value: int | float) -> None:
        log.debug("%s: %s=%s", self.device.connection_info(), name, value)
        try:
            self.device.write(name, value)
        except Exception:
            log.exception("Write failed for %s.%s", self.device.connection_info(), name)

    # ------------------------------------------------------------------
    # Polling start / stop
    # ------------------------------------------------------------------

    def start_polling(self, interval_ms: int = 1000) -> None:
        self._worker = ExternalDeviceWorker(self.device, interval_ms=interval_ms)
        self._worker_thread = QThread(self)
        self._worker.moveToThread(self._worker_thread)

        self._worker_thread.started.connect(self._worker.run)
        self._worker.readback.connect(self._on_readback)
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)
        self._worker_thread.finished.connect(self._on_polling_finished)

        self._worker_thread.start()
        log.info("External device polling started: %s", self.device.connection_info())

    def _on_polling_finished(self) -> None:
        self._worker = None
        self._worker_thread = None

    def stop_polling_sync(self) -> None:
        """Blocking stop for use during application shutdown only."""
        worker = self._worker
        thread = self._worker_thread
        if worker is not None:
            worker.request_stop.emit()
        if thread is not None:
            if not thread.wait(3000):
                log.warning("External device worker thread did not stop in time, terminating")
                thread.terminate()
                thread.wait()
        self._worker_thread = None
        self._worker = None

    def _on_readback(self, _timestamp: float, snapshot: dict[str, int | float]) -> None:
        for name, value in snapshot.items():
            row = self._row_by_name.get(f"telemetry:{name}")
            if row is None:
                continue
            item = self.telemetryTable.item(row, 1)
            if item is None:
                continue
            text = f"{value:.4f}" if isinstance(value, float) else str(value)
            item.setText(text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
