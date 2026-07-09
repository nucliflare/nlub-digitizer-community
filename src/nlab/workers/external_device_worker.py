from __future__ import annotations

import logging
import time

from nlab_modbus.core.base_modbus_device import BaseModbusDevice
from PySide6.QtCore import QTimer, Signal, Slot

from nlab.workers.base_worker import BaseWorker

log = logging.getLogger(__name__)

# After this many consecutive failures, suppress per-tick tracebacks and only
# log a single warning every _WARN_EVERY ticks (to avoid flooding the log when
# another program steals the Modbus TCP connection).
_SILENCE_AFTER = 3
_WARN_EVERY = 30   # ~30 s at 1 s poll rate
_RECONNECT_EVERY = 10  # attempt client.connect() every 10 failures


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
        self._consecutive_failures = 0

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
        except Exception as exc:
            self._consecutive_failures += 1
            n = self._consecutive_failures
            info = self._device.connection_info()

            if n == 1:
                log.exception("External device readback failed: %s", info)
            elif n < _SILENCE_AFTER:
                log.error("External device readback failed (%d): %s — %s", n, info, exc)
            elif n % _RECONNECT_EVERY == 0:
                log.warning(
                    "External device unreachable (%d consecutive failures): %s — "
                    "attempting reconnect", n, info,
                )
                self._try_reconnect()
            elif n % _WARN_EVERY == 0:
                log.warning("External device still unreachable (%d failures): %s", n, info)
            return

        if self._consecutive_failures > 0:
            log.info(
                "External device recovered after %d failure(s): %s",
                self._consecutive_failures, self._device.connection_info(),
            )
            self._consecutive_failures = 0

        self.readback.emit(now, snapshot)

    def _try_reconnect(self) -> None:
        try:
            client = self._device.client
            client.close()
            client.connect()
            log.debug("External device reconnect attempt sent: %s",
                      self._device.connection_info())
        except Exception as exc:
            log.debug("External device reconnect attempt failed: %s — %s",
                      self._device.connection_info(), exc)
