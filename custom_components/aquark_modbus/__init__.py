"""Integrate Aquark chlorinators over Modbus into Home Assistant."""

from homeassistant.components.modbus import async_get_unit
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from aquark_modbus import Chlorinator

from .const import CONF_UNIT_ID
from .coordinator import AquarkConfigEntry, AquarkCoordinator
from .helpers import create_modbus_params

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: AquarkConfigEntry) -> bool:
    """Set up a Aquark chlorinator from a config entry."""
    unit = async_get_unit(
        hass, entry, create_modbus_params(entry.data), entry.data[CONF_UNIT_ID]
    )
    coordinator = AquarkCoordinator(hass, entry, Chlorinator(unit))
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AquarkConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
