#!/usr/bin/env python
"""Dual-channel IIR average measurement at maximum rate.

Connects to two channels on a digitizer, reads get_iir_average() on both
as fast as possible for a fixed duration, and prints live stats.  At the
end a summary with per-channel measurement counts and average delta-t is
printed.

Usage:
    python examples/iir_average_dual_channel.py [--host HOST] [--port PORT] [--duration SECONDS]
"""

from __future__ import annotations

import argparse
import sys
import time

from nlab.hardware.digitizer import Digitizer


def main() -> None:
    parser = argparse.ArgumentParser(description="Dual-channel IIR average measurement")
    parser.add_argument("--host", default="192.168.10.134")
    parser.add_argument("--port", type=int, default=50050)
    parser.add_argument("--duration", type=float, default=120.0, help="Measurement duration in seconds")
    args = parser.parse_args()

    print(f"Connecting to {args.host}:{args.port} …")
    ch1 = Digitizer.from_grpc(channel=1, hostname=args.host, port=args.port)
    ch2 = Digitizer.from_grpc(channel=2, hostname=args.host, port=args.port)
    print("Connected.\n")

    ts_ch1: list[float] = []
    ts_ch2: list[float] = []
    vals_ch1: list[int] = []
    vals_ch2: list[int] = []

    t_start = time.perf_counter()
    deadline = t_start + args.duration
    n = 0

    try:
        while True:
            now = time.perf_counter()
            if now >= deadline:
                break

            v1 = ch1.mca.filters.lp.get_iir_average()
            t1 = time.perf_counter()
            ts_ch1.append(t1)
            vals_ch1.append(v1)

            v2 = ch2.mca.filters.lp.get_iir_average()
            t2 = time.perf_counter()
            ts_ch2.append(t2)
            vals_ch2.append(v2)

            n += 1
            elapsed = t2 - t_start
            print(
                f"  [{elapsed:7.2f}s / {args.duration:.0f}s]  "
                f"n={n}  Ch1={v1}  Ch2={v2}",
                end="\r",
            )

    except KeyboardInterrupt:
        print("\nInterrupted by user.")

    print()

    # ── Statistics ──────────────────────────────────────────────────
    wall = time.perf_counter() - t_start
    print(f"\n{'═' * 56}")
    print(f"  Measurement complete — {wall:.2f} s wall time")
    print(f"{'═' * 56}")

    for label, timestamps, values in [
        ("Ch 1", ts_ch1, vals_ch1),
        ("Ch 2", ts_ch2, vals_ch2),
    ]:
        count = len(timestamps)
        if count < 2:
            print(f"  {label}: {count} samples (not enough for delta-t stats)")
            continue
        deltas = [timestamps[i] - timestamps[i - 1] for i in range(1, count)]
        avg_dt = sum(deltas) / len(deltas)
        min_dt = min(deltas)
        max_dt = max(deltas)
        print(
            f"  {label}:  samples={count}"
            f"  avg_dt={avg_dt * 1e3:.3f} ms"
            f"  min_dt={min_dt * 1e3:.3f} ms"
            f"  max_dt={max_dt * 1e3:.3f} ms"
            f"  rate={count / wall:.1f} Hz"
        )
        if values:
            avg_val = sum(values) / len(values)
            print(f"         avg_value={avg_val:.1f}  min={min(values)}  max={max(values)}")

    print(f"{'═' * 56}")

    ch1.close()
    ch2.close()
    print("Disconnected.")


if __name__ == "__main__":
    main()
