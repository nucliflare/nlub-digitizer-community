from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from PySide6.QtCore import QTimer, Signal, Slot

from nlab.hardware.digitizer.hv import HVSupply
from nlab.workers.base_worker import BaseWorker

log = logging.getLogger(__name__)


@dataclass
class PSUReadback:
    timestamp: float
    hv_voltage: float
    hv_compens_output: float
    temp_analog: float
    temp_digital: float
    temp_digital_status: int
    ads_temp: float
    sipm_voltage: float | None = None
    sipm_current: float | None = None
    sipm_overload: int | None = None
    sipm_compens_output: float | None = None


class PSUWorker(BaseWorker):
    """Periodically reads all HV/IDS registers in a background thread.

    Emits ``readback`` with a :class:`PSUReadback` on each tick.
    Create, ``moveToThread``, connect ``thread.started`` → ``run``,
    then call ``stop`` to shut down.
    """

    readback = Signal(object)
    change_interval = Signal(int)
    request_stop = Signal()

    def __init__(
        self,
        hv: HVSupply,
        read_sipm: bool,
        interval_ms: int = 1000,
    ) -> None:
        super().__init__()
        self._hv = hv
        self._read_sipm = read_sipm
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
            rb = PSUReadback(
                timestamp=now,
                hv_voltage=self._hv.get_hv_adc_voltage(),
                hv_compens_output=self._hv.get_hv_compens_output(),
                temp_analog=self._hv.get_temp_analog(),
                temp_digital=self._hv.get_temp_digital(),
                temp_digital_status=self._hv.get_temp_digital_status(),
                ads_temp=self._hv.get_ads_temp(),
            )
            if self._read_sipm:
                rb.sipm_voltage = self._hv.get_sipm_adc_voltage()
                rb.sipm_current = self._hv.get_sipm_adc_current()
                rb.sipm_overload = self._hv.get_sipm_overload()
                rb.sipm_compens_output = self._hv.get_sipm_compens_output()
        except Exception:
            log.exception("PSU readback failed")
            return
        self.readback.emit(rb)
