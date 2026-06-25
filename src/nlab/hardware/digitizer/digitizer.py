from __future__ import annotations

from .backends.base import DigitizerBackend, IDSBackend
from .backends.grpc_backend import GrpcDigitizerBackend
from .scope import Scope
from .mca import MultiChannelAnalyzer
from .hv import HVSupply


class Digitizer:
    """Entry point for instrument access.

    Construct via a factory classmethod, then access subsystems through
    .scope, .mca, and .hv.  The scope/mca share one gRPC service
    (DPP_reg_access on port 50050); the HV supply uses a separate IDS
    service (IDS_access on port 50040) on the **same physical device**.
    The split is a legacy issue that will be merged in a future firmware
    revision.

    Hardware I/O uses explicit get_*/set_* methods rather than properties.
    This makes the I/O cost visible at call sites and avoids surprising side
    effects inside expressions.

    Example — gRPC::

        d = Digitizer.from_grpc(channel=1)
        d.scope.set_trigger_level(5000)
        d.mca.set_energy_bin(4)
        d.hv.set_voltage(30.0)

    Example — without HV (e.g. bench testing DPP only)::

        d = Digitizer.from_grpc(channel=1, with_ids=False)
        # d.hv is None
    """

    def __init__(
        self,
        backend: DigitizerBackend,
        ids_backend: IDSBackend | None = None,
    ) -> None:
        self._backend = backend
        self._ids_backend = ids_backend
        self.scope = Scope(backend)
        self.mca   = MultiChannelAnalyzer(backend)
        self.hv: HVSupply | None = HVSupply(ids_backend) if ids_backend else None

    def close(self) -> None:
        if self.hv is not None:
            self.hv.safe_shutdown()
        self._backend.close()
        if self._ids_backend is not None:
            self._ids_backend.close()

    @classmethod
    def from_grpc(
        cls,
        channel: int,
        hostname: str = "192.168.10.20",
        port: int = 50050,
        *,
        ids_port: int = 50040,
        with_ids: bool = True,
    ) -> Digitizer:
        """Create a Digitizer backed by gRPC.

        Both the DPP and IDS services run on the same device (same
        hostname, different ports).  Pass with_ids=False to skip the
        IDS connection (d.hv will be None).
        """
        from .backends.grpc_ids_backend import GrpcIDSBackend

        dpp = GrpcDigitizerBackend(channel, hostname, port)
        ids = GrpcIDSBackend(channel, hostname, ids_port) if with_ids else None
        return cls(dpp, ids)

    # @classmethod
    # def from_iio(
    #     cls,
    #     channel: int,
    #     uri: str = "ip:192.168.10.20",
    # ) -> Digitizer:
    #     from .backends.iio_backend import IIODigitizerBackend
    #     return cls(IIODigitizerBackend(channel, uri))
