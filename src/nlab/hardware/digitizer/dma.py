"""ZMQ-based DMA streaming for scope waveforms and MCA list-mode events.

These classes manage ZMQ SUB socket connections to the digitizer's
streaming endpoints.  They are transport-layer components, analogous
to GrpcIDSBackend -- independent connections instantiated alongside
the main gRPC backend.
"""

from __future__ import annotations

import logging
import struct
import threading
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np
import zmq

log = logging.getLogger(__name__)

SCOPE_DMA_BASE_PORT = 50152
MCA_DMA_BASE_PORT = 50162

STREAM_START = b"StreamSTART\x00"
STREAM_END = b"StreamEND\x00"

EVENT_STRUCT = struct.Struct("<BBHHHQ")
EVENT_SIZE = EVENT_STRUCT.size  # 14

FILE_HEADER_STRUCT = struct.Struct("<4sHBBdI4x")  # 24 bytes
FILE_MAGIC = b"NDMA"
FILE_VERSION = 1

# Each raw scope DMA frame is prefixed with a per-frame timestamp: the first
# 4 int16 slots (8 bytes) are a little-endian uint64, the remaining
# (frame_samples - SCOPE_TIMESTAMP_WORDS) slots are the int16 waveform.
SCOPE_TIMESTAMP_WORDS = 4

_EVENT_DTYPE = np.dtype([
    ("marker", np.uint8),
    ("zc_offset", np.uint8),
    ("zc_estimation", np.uint16),
    ("short_energy", np.uint16),
    ("energy", np.uint16),
    ("timestamp", np.uint64),
])


def _write_file_header(f, channel: int, frame_samples: int = 0) -> None:
    header = FILE_HEADER_STRUCT.pack(
        FILE_MAGIC, FILE_VERSION, channel, 0, time.time(), frame_samples,
    )
    f.write(header)
    f.flush()


class ScopeDmaStreamer:
    """Manages ZMQ SUB connection for scope DMA waveform streaming.

    Not a backend -- a standalone connection manager.  Create via
    Digitizer, use from a dedicated worker thread.
    """

    def __init__(self, channel: int, hostname: str = "192.168.10.20") -> None:
        self._channel = channel
        self._hostname = hostname
        self._port = SCOPE_DMA_BASE_PORT + channel - 1
        self._endpoint = f"tcp://{hostname}:{self._port}"

    def stream_to_file(
        self,
        filepath: Path,
        frame_samples: int,
        stop_event: threading.Event,
        on_ready: Callable[[], None] | None = None,
        on_progress: Callable[[int], None] | None = None,
    ) -> int:
        """Connect, signal ready, wait for StreamSTART, write frames until StreamEND or stop.

        *on_ready* is called after the ZMQ socket is connected and
        subscribed — the caller should enable DMA on the hardware at
        this point so the StreamSTART sentinel is not missed.

        Returns total bytes written.  Runs in caller's thread --
        creates and destroys its own ZMQ context (thread-local).
        """
        ctx = zmq.Context()
        socket = ctx.socket(zmq.SUB)
        socket.setsockopt(zmq.LINGER, 0)      # don't block ctx.term() on unsent messages
        socket.setsockopt(zmq.SUBSCRIBE, b"")
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)

        log.debug("Scope DMA [worker 2a]: connecting ZMQ SUB to %s", self._endpoint)
        socket.connect(self._endpoint)
        time.sleep(0.2)
        log.debug("Scope DMA [worker 2b]: ZMQ connected, emitting ready "
                  "(controller will enable DMA + call start)")
        if on_ready is not None:
            on_ready()

        total_bytes = 0
        frame_count = 0
        started = False

        try:
            with open(filepath, "wb") as f:
                log.info("Scope DMA: recording to %s", filepath)
                _write_file_header(f, self._channel, frame_samples)
                log.debug("Scope DMA [worker 6/6]: polling for StreamSTART "
                          "(waiting for HW start_irq after scope.start())")

                while not stop_event.is_set():
                    events = dict(poller.poll(100))
                    if socket not in events:
                        continue

                    message = socket.recv()

                    if not started:
                        if message == STREAM_START:
                            log.info("Scope DMA: StreamSTART received "
                                     "(HW start_irq fired, DMA engine running)")
                            started = True
                            continue
                        if message != STREAM_END and len(message) > len(STREAM_START):
                            log.warning("Scope DMA: data arrived before StreamSTART "
                                        "(%d bytes) — server missed sentinel, "
                                        "treating as stream active", len(message))
                            started = True
                            f.write(message)
                            total_bytes += len(message)
                            frame_count += 1
                            continue
                        log.debug("Scope DMA: pre-start message, %d bytes (ignoring)",
                                  len(message))
                        continue

                    if message == STREAM_END:
                        log.info("Scope DMA: StreamEND received "
                                 "(HW stop_irq fired, scope.stop() was called)")
                        break

                    f.write(message)
                    total_bytes += len(message)
                    frame_count += 1
                    if frame_count == 1:
                        log.debug("Scope DMA: first data frame received, %d bytes "
                                  "(DMA transfers active)", len(message))

                    if on_progress is not None:
                        on_progress(total_bytes)

        except zmq.ZMQError:
            log.exception("Scope DMA: ZMQ error during streaming")
            raise
        finally:
            reason = "stop_event" if stop_event.is_set() else "StreamEND"
            log.info("Scope DMA: finished -- %d frames, %d bytes to %s (reason: %s)",
                     frame_count, total_bytes, filepath, reason)
            socket.close()
            ctx.term()

        return total_bytes


class McaDmaStreamer:
    """Manages ZMQ SUB connection for MCA list-mode DMA streaming.

    Not a backend -- a standalone connection manager.  Create via
    Digitizer, use from a dedicated worker thread.
    """

    def __init__(self, channel: int, hostname: str = "192.168.10.20") -> None:
        self._channel = channel
        self._hostname = hostname
        self._port = MCA_DMA_BASE_PORT + channel - 1
        self._endpoint = f"tcp://{hostname}:{self._port}"

    def stream_events(
        self,
        stop_event: threading.Event,
        filepath: Path | None = None,
        event_buffer: tuple[list, threading.Lock] | None = None,
        on_ready: Callable[[], None] | None = None,
        on_progress: Callable[[int], None] | None = None,
    ) -> int:
        """Connect, signal ready, wait for StreamSTART, read events until StreamEND or stop.

        *on_ready* is called after the ZMQ socket is connected and
        subscribed — the caller should enable DMA and start the
        measurement at this point so the StreamSTART sentinel is not missed.

        Events are simultaneously:
        - Written to *filepath* as raw binary (if provided)
        - Parsed and appended to *event_buffer* (if provided)

        Returns total event count.  Runs in caller's thread.
        """
        ctx = zmq.Context()
        socket = ctx.socket(zmq.SUB)
        socket.setsockopt(zmq.LINGER, 0)      # don't block ctx.term() on unsent messages
        socket.setsockopt(zmq.SUBSCRIBE, b"")
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)

        log.debug("MCA DMA [worker 2a]: connecting ZMQ SUB to %s", self._endpoint)
        socket.connect(self._endpoint)
        time.sleep(0.2)
        log.debug("MCA DMA [worker 2b]: ZMQ connected, emitting ready "
                  "(controller will enable DMA + call start)")
        if on_ready is not None:
            on_ready()

        total_events = 0
        msg_count = 0
        started = False
        file_handle = None

        try:
            if filepath is not None:
                file_handle = open(filepath, "wb")
                log.info("MCA DMA: recording to %s", filepath)
                _write_file_header(file_handle, self._channel)

            log.debug("MCA DMA [worker 6/6]: polling for StreamSTART "
                      "(waiting for HW list_start_irq after mca.start())")

            while not stop_event.is_set():
                events = dict(poller.poll(100))
                if socket not in events:
                    continue

                message = socket.recv()

                if not started:
                    if message == STREAM_START:
                        log.info("MCA DMA: StreamSTART received "
                                 "(HW list_start_irq fired, DMA engine running)")
                        started = True
                        continue
                    if message != STREAM_END and len(message) > len(STREAM_START):
                        log.warning("MCA DMA: data arrived before StreamSTART "
                                    "(%d bytes) — server missed sentinel, "
                                    "treating as stream active", len(message))
                        started = True
                        # Fall through to process this message as data
                    else:
                        log.debug("MCA DMA: pre-start message, %d bytes (ignoring)",
                                  len(message))
                        continue

                if message == STREAM_END:
                    log.info("MCA DMA: StreamEND received "
                             "(HW list_stop_irq fired, mca.stop() was called)")
                    break

                if file_handle is not None:
                    file_handle.write(message)

                n_events = len(message) // EVENT_SIZE
                if len(message) % EVENT_SIZE != 0:
                    log.warning(
                        "MCA DMA: message size %d not aligned to event size %d, truncating",
                        len(message), EVENT_SIZE,
                    )

                total_events += n_events
                msg_count += 1
                if msg_count == 1:
                    log.debug("MCA DMA: first event frame received, %d bytes, %d events "
                              "(DMA transfers active)", len(message), n_events)

                if event_buffer is not None and n_events > 0:
                    parsed = self.parse_events(message[:n_events * EVENT_SIZE])
                    buf, lock = event_buffer
                    with lock:
                        buf.append(parsed)

                if on_progress is not None:
                    on_progress(total_events)

        except zmq.ZMQError:
            log.exception("MCA DMA: ZMQ error during streaming")
            raise
        finally:
            reason = "stop_event" if stop_event.is_set() else "StreamEND"
            log.info("MCA DMA: finished -- %d events from %d messages (reason: %s)",
                     total_events, msg_count, reason)
            if file_handle is not None:
                file_handle.close()
                log.info("MCA DMA: file closed: %s", filepath)
            socket.close()
            ctx.term()

        return total_events

    @staticmethod
    def parse_events(raw: bytes) -> np.ndarray:
        """Parse raw binary into structured numpy array."""
        return np.frombuffer(raw, dtype=_EVENT_DTYPE)

    @staticmethod
    def compute_psd(events: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Compute PSD from structured event array.

        Returns (energy, psd_zc) arrays.
        """
        energy = events["energy"].astype(np.float64)
        psd_zc = events["zc_offset"].astype(np.float64) + (
            events["zc_estimation"].view(np.int16).astype(np.float64) / 2**14
        )
        return energy, psd_zc
