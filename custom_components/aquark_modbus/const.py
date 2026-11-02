"""Constants for the Aquark Modbus integration."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

from aquark_modbus import DeviceType

DOMAIN: Final = "aquark_modbus"
"""Integration domain; must match ``manifest.json``."""

# Config entry data keys, in the shape the config flow stores them.
CONF_CONNECTION: Final = "connection"  # one of ``CONF_TCP`` / ``CONF_SERIAL``
CONF_HOST: Final = "host"
CONF_PORT: Final = "port"
CONF_UNIT: Final = "unit"
CONF_DEVICE: Final = "device"

CONF_TCP: Final = "tcp"
CONF_SERIAL: Final = "serial"

DEFAULT_UNIT: Final = 8
"""Default Modbus unit ID for the config flow."""

DEFAULT_TCP_PORT: Final = 502
"""Default TCP port for the config flow."""

UPDATE_INTERVAL: Final = timedelta(seconds=30)
"""Coordinator poll interval."""

DEVICE_TYPE_NAMES: Final[dict[DeviceType, str]] = {
    DeviceType.MR_PURE: "Mr Pure",
    DeviceType.INVER_CLEAR: "Inver Clear",
    DeviceType.MR_PURE_PRO: "Mr Pure Pro",
}
"""Human-readable names for the ``DeviceType`` values."""

PLATFORMS: Final[list[Platform]] = [Platform.SENSOR]


def unique_id_for(data: Mapping[str, object]) -> str:
    """Build the config entry unique id from its stored data.

    Single source of truth shared by the config flow and the tests,
    so the two can never drift apart.
    """
    if (connection := data[CONF_CONNECTION]) == CONF_TCP:
        return f"tcp:{data[CONF_HOST]}:{data[CONF_PORT]}:{data[CONF_UNIT]}"
    if connection == CONF_SERIAL:
        return f"serial:{data[CONF_DEVICE]}:{data[CONF_UNIT]}"
    msg = f"Unknown connection type: {connection!r}"
    raise ValueError(msg)
