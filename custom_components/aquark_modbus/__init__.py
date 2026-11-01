"""Integrate Aquark chlorinators over Modbus into Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.components.modbus import async_get_unit
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from modbus_connection import ModbusSerialParams, ModbusTcpParams

from aquark_modbus import Chlorinator

from .const import (
    CONF_CONNECTION,
    CONF_DEVICE,
    CONF_HOST,
    CONF_PORT,
    CONF_TCP,
    CONF_UNIT,
    PLATFORMS,
)
from .coordinator import AquarkDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Aquark (Modbus) from a config entry.

    A failed first refresh raises ``ConfigEntryNotReady`` (handled by
    ``async_config_entry_first_refresh``), so Home Assistant retries the setup
    with backoff instead of surfacing an error to the user.
    """
    data = entry.data
    if data[CONF_CONNECTION] == CONF_TCP:
        params = ModbusTcpParams(host=data[CONF_HOST], port=data[CONF_PORT])
    else:
        params = ModbusSerialParams(device=data[CONF_DEVICE])

    unit = async_get_unit(hass, entry, params, data[CONF_UNIT])
    coordinator = AquarkDataUpdateCoordinator(hass, entry, Chlorinator(unit))
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an Aquark (Modbus) config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
