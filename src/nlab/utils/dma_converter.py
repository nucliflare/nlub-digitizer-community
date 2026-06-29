"""Convert raw DMA binary files to HDF5 for scientific analysis."""

from __future__ import annotations

import logging
import struct
from pathlib import Path

import h5py
import numpy as np

from nlab.hardware.digitizer.dma import (
    FILE_HEADER_STRUCT,
    FILE_MAGIC,
    EVENT_SIZE,
    _EVENT_DTYPE,
)

log = logging.getLogger(__name__)


def read_file_header(f) -> dict:
    raw = f.read(FILE_HEADER_STRUCT.size)
    if len(raw) < FILE_HEADER_STRUCT.size:
        raise ValueError("File too short for header")
    magic, version, channel, _, timestamp, frame_samples = FILE_HEADER_STRUCT.unpack(raw)
    if magic != FILE_MAGIC:
        raise ValueError(f"Invalid magic: {magic!r}, expected {FILE_MAGIC!r}")
    return {
        "version": version,
        "channel": channel,
        "timestamp": timestamp,
        "frame_samples": frame_samples,
    }


def convert_listmode(src: Path, dst: Path) -> int:
    """Convert MCA listmode binary to HDF5. Returns event count."""
    with open(src, "rb") as f:
        header = read_file_header(f)
        raw_data = f.read()

    n_events = len(raw_data) // EVENT_SIZE
    if len(raw_data) % EVENT_SIZE != 0:
        log.warning("Listmode file size not aligned to event size, truncating %d trailing bytes",
                    len(raw_data) % EVENT_SIZE)
    events = np.frombuffer(raw_data[:n_events * EVENT_SIZE], dtype=_EVENT_DTYPE)

    with h5py.File(dst, "w") as h5:
        h5.attrs["source_file"] = str(src)
        h5.attrs["format_version"] = header["version"]
        h5.attrs["channel"] = header["channel"]
        h5.attrs["recording_timestamp"] = header["timestamp"]
        h5.attrs["total_events"] = n_events

        ds = h5.create_dataset("events", data=events, compression="gzip", compression_opts=4)
        ds.attrs["fields"] = "marker, zc_offset, zc_estimation, short_energy, energy, timestamp"
        ds.attrs["timestamp_unit"] = "8 ns ticks"

        h5.create_dataset("energy", data=events["energy"], compression="gzip", compression_opts=4)
        h5.create_dataset("timestamp", data=events["timestamp"], compression="gzip", compression_opts=4)

        psd_zc = events["zc_offset"].astype(np.float64) + (
            events["zc_estimation"].view(np.int16).astype(np.float64) / 2**14
        )
        h5.create_dataset("psd_zc", data=psd_zc, compression="gzip", compression_opts=4)

    log.info("Converted %d listmode events: %s -> %s", n_events, src, dst)
    return n_events


def convert_scope(src: Path, dst: Path) -> int:
    """Convert scope DMA binary to HDF5. Returns frame count."""
    with open(src, "rb") as f:
        header = read_file_header(f)
        raw_data = f.read()

    frame_bytes = header["frame_samples"]
    if frame_bytes == 0:
        raise ValueError("Scope file has frame_samples=0 in header, cannot determine frame size")

    n_frames = len(raw_data) // frame_bytes
    if len(raw_data) % frame_bytes != 0:
        log.warning("Scope file size not aligned to frame size, truncating %d trailing bytes",
                    len(raw_data) % frame_bytes)

    samples_per_frame = frame_bytes // 2
    waveforms = np.frombuffer(raw_data[:n_frames * frame_bytes], dtype=np.int16).reshape(n_frames, samples_per_frame)
    time_ns = np.arange(0, 8 * samples_per_frame, 8)

    with h5py.File(dst, "w") as h5:
        h5.attrs["source_file"] = str(src)
        h5.attrs["format_version"] = header["version"]
        h5.attrs["channel"] = header["channel"]
        h5.attrs["recording_timestamp"] = header["timestamp"]
        h5.attrs["frame_samples"] = header["frame_samples"]
        h5.attrs["total_frames"] = n_frames
        h5.attrs["samples_per_frame"] = samples_per_frame

        h5.create_dataset("waveforms", data=waveforms, compression="gzip", compression_opts=4)
        h5["waveforms"].attrs["unit"] = "ADC counts (int16)"
        h5.create_dataset("time_ns", data=time_ns)
        h5["time_ns"].attrs["unit"] = "nanoseconds"

    log.info("Converted %d scope frames (%d samples each): %s -> %s",
             n_frames, samples_per_frame, src, dst)
    return n_frames