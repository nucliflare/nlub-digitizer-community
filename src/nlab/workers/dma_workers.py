"""Background workers for DMA streaming.

Follow the BaseWorker + QThread pattern.  Because run() blocks in a
ZMQ poll loop the worker thread's Qt event loop never spins, so
signal-based stop does NOT work.  Use worker.stop() (direct call to
threading.Event.set()) instead.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from PySide6.QtCore import Signal

from nlab.hardware.digitizer.dma import McaDmaStreamer, ScopeDmaStreamer
from nlab.workers.base_worker import BaseWorker

log = logging.getLogger(__name__)


class ScopeDmaWorker(BaseWorker):
    """Streams scope DMA waveforms to a binary file.

    Emits ``ready`` once the ZMQ socket is connected and subscribed.
    The controller should enable DMA on the hardware in response so
    the StreamSTART sentinel is not missed.

    Stop with ``worker.stop()`` (direct call, not signal).
    """

    ready = Signal()
    progress = Signal(int)

    def __init__(
        self,
        streamer: ScopeDmaStreamer,
        filepath: Path,
        frame_samples: int,
    ) -> None:
        super().__init__()
        self._streamer = streamer
        self._filepath = filepath
        self._frame_samples = frame_samples
        self._stop_event = threading.Event()

    def run(self) -> None:
        log.info("ScopeDmaWorker: starting, file=%s", self._filepath)
        try:
            total = self._streamer.stream_to_file(
                filepath=self._filepath,
                frame_samples=self._frame_samples,
                stop_event=self._stop_event,
                on_ready=lambda: self.ready.emit(),
                on_progress=lambda n: self.progress.emit(n),
            )
            log.info("ScopeDmaWorker: completed, %d bytes written", total)
        except Exception:
            log.exception("ScopeDmaWorker: streaming failed")
            self.error.emit("Scope DMA streaming failed")
        finally:
            self.finished.emit()

    def stop(self) -> None:
        log.info("ScopeDmaWorker: stop requested")
        self._stop_event.set()


class McaDmaWorker(BaseWorker):
    """Streams MCA list-mode events via ZMQ.

    Emits ``ready`` once the ZMQ socket is connected and subscribed.
    The controller should enable DMA and start the measurement in
    response so the StreamSTART sentinel is not missed.

    Stop with ``worker.stop()`` (direct call, not signal).
    """

    ready = Signal()
    progress = Signal(int)

    def __init__(
        self,
        streamer: McaDmaStreamer,
        filepath: Path | None = None,
        event_buffer: tuple[list, threading.Lock] | None = None,
    ) -> None:
        super().__init__()
        self._streamer = streamer
        self._filepath = filepath
        self._event_buffer = event_buffer
        self._stop_event = threading.Event()

    def run(self) -> None:
        log.info("McaDmaWorker: starting, file=%s", self._filepath)
        try:
            total = self._streamer.stream_events(
                stop_event=self._stop_event,
                filepath=self._filepath,
                event_buffer=self._event_buffer,
                on_ready=lambda: self.ready.emit(),
                on_progress=lambda n: self.progress.emit(n),
            )
            log.info("McaDmaWorker: completed, %d events received", total)
        except Exception:
            log.exception("McaDmaWorker: streaming failed")
            self.error.emit("MCA DMA streaming failed")
        finally:
            self.finished.emit()

    def stop(self) -> None:
        log.info("McaDmaWorker: stop requested")
        self._stop_event.set()
