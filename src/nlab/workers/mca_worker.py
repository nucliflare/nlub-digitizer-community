from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import numpy as np
from PySide6.QtCore import QTimer, Signal, Slot

from nlab.hardware.digitizer.mca import MultiChannelAnalyzer
from nlab.workers.base_worker import BaseWorker

log = logging.getLogger(__name__)


@dataclass
class MCAReadback:
    histogram: np.ndarray
    debug1: np.ndarray
    debug2: np.ndarray
    count_rate: int = 0
    pulse_deadtime: int = 0
    events_lost: int = 0
    elapsed_time: int = 0
    pulse_overrange: int = 0
    pulse_pileup: int = 0
    energy_overrange: int = 0
    energy_estimation_error: int = 0
    throughput_error: int = 0


class MCAWorker(BaseWorker):
    """Periodically reads histogram, debug waveforms, and statistics.

    Create, ``moveToThread``, connect ``thread.started`` to ``run``,
    then emit ``request_stop`` to shut down.
    """

    readback = Signal(object)
    request_stop = Signal()
    change_interval = Signal(int)

    def __init__(
        self,
        mca: MultiChannelAnalyzer,
        interval_ms: int = 200,
    ) -> None:
        super().__init__()
        self._mca = mca
        self._interval_ms = interval_ms
        self._timer: QTimer | None = None

    def run(self) -> None:
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
        self.request_stop.connect(self._stop)
        self.change_interval.connect(self._set_interval)
        self._timer.start(self._interval_ms)

    @Slot(int)
    def _set_interval(self, ms: int) -> None:
        if self._timer is not None:
            self._timer.setInterval(ms)

    @Slot()
    def _stop(self) -> None:
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        self.finished.emit()

    def _tick(self) -> None:
        try:
            histogram = self._mca.acquire_spectrum()
            debug1, debug2 = self._mca.acquire_waveforms()
            stats = self._mca.statistics

            rb = MCAReadback(
                histogram=histogram,
                debug1=debug1,
                debug2=debug2,
                count_rate=stats.get_count_rate(),
                pulse_deadtime=stats.get_pulse_deadtime(),
                events_lost=stats.get_events_lost(),
                elapsed_time=stats.get_elapsed_time(),
                pulse_overrange=stats.get_pulse_overrange(),
                pulse_pileup=stats.get_pulse_pileup(),
                energy_overrange=stats.get_energy_overrange(),
                energy_estimation_error=stats.get_energy_estimation_error(),
                throughput_error=stats.get_throughput_error(),
            )
        except Exception:
            log.exception("MCA readback failed")
            return
        self.readback.emit(rb)
