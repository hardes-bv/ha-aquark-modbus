"""Helpers shared by the setup and the config flow of the Aquark Modbus integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from modbus_connection import ModbusSerialParams, ModbusTcpParams

from .const import CONF_CONNECTION, CONF_DEVICE, CONF_HOST, CONF_PORT, CONF_TCP

if TYPE_CHECKING:
    from homeassistant.components.modbus.connection import ModbusParams


def create_modbus_params(data: Mapping[str, Any]) -> ModbusParams:
    """Build the Modbus connection parameters from the stored config entry data.

    The serial line settings of the board are fixed, so only the device is
    configured for a serial connection.
    """
    if data[CONF_CONNECTION] == CONF_TCP:
        return ModbusTcpParams(host=data[CONF_HOST], port=data[CONF_PORT])
    return ModbusSerialParams(device=data[CONF_DEVICE])
