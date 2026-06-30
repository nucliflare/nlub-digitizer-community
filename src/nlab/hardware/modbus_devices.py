from __future__ import annotations

import logging

from nlab_modbus.core.base_modbus_device import BaseModbusDevice
from nlab_modbus.core.enums import DeviceType
from nlab_modbus.services.manager import DeviceManager

log = logging.getLogger(__name__)

# ser2net TCP ports the digitizer bridges its RS-485 Modbus bus to (one bus,
# multiple daisy-chained devices distinguished by Modbus device_id).
REMOTE_PORTS: tuple[int, ...] = (5001, 5002)


class ExternalDevices:
    """Discovers and owns the digitizer's onboard Modbus instruments.

    The SiPM bias board, Geiger-Mueller probe, and PMT HV supply share the
    digitizer's RS-485 bus, bridged to TCP via ser2net — same host as the
    gRPC digitizer connection, different port(s).  Wraps nlab_modbus's
    DeviceManager so the rest of the app only deals with discovered device
    instances and never imports nlab_modbus or touches connection details
    directly.
    """

    def __init__(self) -> None:
        self._manager = DeviceManager()

    def discover(self, host: str, ports: tuple[int, ...] = REMOTE_PORTS) -> list[BaseModbusDevice]:
        """Scan the digitizer host for Modbus devices and connect to all found.

        Uses the manager's remote scan utility per candidate ser2net port;
        a port with nothing attached simply yields no devices. Returns every
        device discovered so far (cumulative across calls).
        """
        for port in ports:
            try:
                self._manager.scan_remote(host, port)
            except Exception:
                log.exception("Modbus scan failed on %s:%d", host, port)
        log.info("Discovered %d external Modbus device(s) on %s",
                  len(self._manager.all_devices), host)
        return self._manager.all_devices

    def by_type(self, device_type: DeviceType) -> list[BaseModbusDevice]:
        return self._manager.by_type(device_type)

    def close(self) -> None:
        self._manager.close_all()
