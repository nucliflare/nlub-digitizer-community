from __future__ import annotations

import logging
import time

from nlab_modbus.core.base_modbus_device import BaseModbusDevice
from PySide6.QtCore import QTimer, Signal, Slot

from nlab.workers.base_worker import BaseWorker

log = logging.getLogger(__name__)


class ExternalDeviceWorker(BaseWorker):
    """Periodically reads one external Modbus device's telemetry registers.

    Mirrors PSUWorker's QTimer-based polling pattern. Uses the device's
    read_snapshot() — a single block transaction over its input registers —
    rather than per-register reads, to minimize traffic on the shared bus.
    Emits ``readback`` with (timestamp, {register_name: engineering_value}).
    """

    readback = Signal(float, dict)
    change_interval = Signal(int)
    request_stop = Signal()

    def __init__(self, device: BaseModbusDevice, interval_ms: int = 1000) -> None:
        super().__init__()
        self._device = device
        self._interval_ms = interval_ms
        self._t0 = 0.0
        self._timer: QTimer | None = None

    def run(self) -> None:
        self._t0 = time.monotonic()
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
        self.change_interval.connect(self._set_interval)
        self.request_stop.connect(self._stop)
        self._timer.start(self._interval_ms)

    @Slot()
    def _stop(self) -> None:
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        self.finished.emit()

    @Slot(int)
    def _set_interval(self, ms: int) -> None:
        if self._timer is not None:
            self._timer.setInterval(ms)

    def _tick(self) -> None:
        now = time.monotonic() - self._t0
        try:
            snapshot = self._device.read_snapshot()
        except Exception:
            log.exception("External device readback failed: %s", self._device.connection_info())
            return
        self.readback.emit(now, snapshot)
