"""Sensor platform for the Aquark Modbus integration.

No sensors are published yet; the firmware-version sensor lands with the model
information. This stub keeps the entry's platform forward valid (a missing
platform module would fail the setup).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: Callable[[list[Any]], Awaitable[None]],
) -> bool:
    """Set up the sensor platform."""
    del hass, entry, async_add_entities
    return True
