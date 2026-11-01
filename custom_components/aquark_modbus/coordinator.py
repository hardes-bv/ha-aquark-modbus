"""Coordinator that reads the Aquark chlorinator's model information.

The integration is a thin wrapper around the ``aquark-modbus`` library, so this
class only bridges the library's one-time model read onto Home Assistant's
``DataUpdateCoordinator``.
"""

from __future__ import annotations

import logging
from typing import override

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from modbus_connection import ModbusError

from aquark_modbus import Chlorinator
from aquark_modbus.model import Model

from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class AquarkDataUpdateCoordinator(DataUpdateCoordinator[Model]):
    """Read the device's (static) model information via the ``Chlorinator``.

    The model registers are read once and never re-polled: the underlying
    ``Chlorinator.async_ensure_setup()`` is idempotent, so later refreshes are
    no-ops that simply return the already-decoded ``Model``.
    """

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        chlorinator: Chlorinator,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self._chlorinator = chlorinator

    @override
    async def _async_update_data(self) -> Model:
        """Read the model once; wrap any transport failure in ``UpdateFailed``."""
        try:
            await self._chlorinator.async_ensure_setup()
        except ModbusError as err:
            raise UpdateFailed(f"Unable to read the model: {err}") from err
        return self._chlorinator.model
