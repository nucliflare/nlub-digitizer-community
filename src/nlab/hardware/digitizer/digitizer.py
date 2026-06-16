from __future__ import annotations

from .backends.base import DigitizerBackend
from .backends.grpc_backend import GrpcDigitizerBackend
from .mca import MultiChannelAnalyzer
from .scope import Scope


class Digitizer:
    """Entry point for instrument access.

    Construct via a factory classmethod, then access subsystems through
    .scope and .mca. The same backend instance is shared by both.

    Hardware I/O uses explicit get_*/set_* methods rather than properties.
    This makes the I/O cost visible at call sites and avoids surprising side
    effects inside expressions.

    Example — gRPC::

        d = Digitizer.from_grpc(channel=1)
        d.scope.set_trigger_level(5000)
        d.scope.start()
        frame = d.scope.acquire_frame()

        d.mca.set_energy_bin(4)
        d.mca.start()
        spectrum = d.mca.acquire_spectrum()

    Example — future IIO (uncomment from_iio when available)::

        d = Digitizer.from_iio(channel=1)
    """

    def __init__(self, backend: DigitizerBackend) -> None:
        self._backend = backend
        self.scope = Scope(backend)
        self.mca = MultiChannelAnalyzer(backend)

    @classmethod
    def from_grpc(
        cls,
        channel: int,
        hostname: str = "192.168.10.20",
        port: int = 50050,
        connect_timeout: float = 2.0,
    ) -> Digitizer:
        return cls(GrpcDigitizerBackend(channel, hostname, port, connect_timeout))

    def close(self) -> None:
        """Close all hardware connections owned by this digitizer."""
        self._backend.close()

    def print_status(self) -> None:
        """Print full digitizer configuration (scope + MCA) to stdout."""
        print("═══════════════════════════════════════════════")
        print("  Digitizer status")
        print("═══════════════════════════════════════════════")
        self.scope.print_status()
        print()
        self.mca.print_status()
        print("═══════════════════════════════════════════════")

    # @classmethod
    # def from_iio(
    #     cls,
    #     channel: int,
    #     uri: str = "ip:192.168.10.20",
    # ) -> Digitizer:
    #     from .backends.iio_backend import IIODigitizerBackend
    #     return cls(IIODigitizerBackend(channel, uri))
