"""Config flow for the Aquark (Modbus) integration.

The user picks how the chlorinator is reached (a Modbus TCP gateway or a serial
port), supplies the link settings plus the Modbus unit ID, and the flow then
probes the device over a temporary Modbus unit before the entry is created. A
device that does not answer like an Aquark board, or a link that is down, is
reported as a retryable error instead of aborting the flow.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, override

import probatio
from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SerialPortSelector,
    TextSelector,
)

from aquark_modbus import AquarkError, Chlorinator, NotAnAquarkDeviceError

from .const import (
    CONF_CONNECTION,
    CONF_DEVICE,
    CONF_HOST,
    CONF_PORT,
    CONF_SERIAL,
    CONF_TCP,
    CONF_UNIT,
    DEFAULT_TCP_PORT,
    DEFAULT_UNIT,
    DOMAIN,
    unique_id_for,
)
from .helpers import create_modbus_params

_LOGGER = logging.getLogger(__name__)

# The board reports no model name to use as a title, so every entry shares one.
DEFAULT_TITLE = "Aquark chlorinator"

# The Modbus unit ID and TCP port are 16-bit values; the selectors render a
# boxed number input and the coercion keeps the stored data an int.
UNIT_ID_SELECTOR = probatio.All(
    NumberSelector(NumberSelectorConfig(mode=NumberSelectorMode.BOX, min=1, max=247)),
    probatio.Coerce(int),
)
PORT_SELECTOR = probatio.All(
    NumberSelector(NumberSelectorConfig(mode=NumberSelectorMode.BOX, min=1, max=65535)),
    probatio.Coerce(int),
)
# A host selector coerces any string, so require a non-blank one explicitly.
HOST_SELECTOR = probatio.All(
    TextSelector(),
    probatio.Check(lambda value: value.strip() != "", "Host is required"),
)

STEP_TCP_DATA_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_HOST): HOST_SELECTOR,
        probatio.Required(CONF_PORT, default=DEFAULT_TCP_PORT): PORT_SELECTOR,
        probatio.Required(CONF_UNIT, default=DEFAULT_UNIT): UNIT_ID_SELECTOR,
    }
)

STEP_SERIAL_DATA_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_DEVICE): SerialPortSelector(),
        probatio.Required(CONF_UNIT, default=DEFAULT_UNIT): UNIT_ID_SELECTOR,
    }
)


async def _async_probe(hass: HomeAssistant, data: Mapping[str, Any]) -> None:
    """Read the chlorinator behind these link settings, or raise."""
    params = create_modbus_params(data)
    async with async_get_temporary_unit(hass, params, data[CONF_UNIT]) as unit:
        await Chlorinator(unit).async_validate()


class AquarkModbusConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for an Aquark chlorinator."""

    VERSION = 1

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user pick how the chlorinator is reached."""
        return self.async_show_menu(
            step_id="user", menu_options=[CONF_TCP, CONF_SERIAL]
        )

    async def async_step_tcp(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a chlorinator behind a Modbus TCP gateway."""
        return await self._async_step_link(CONF_TCP, STEP_TCP_DATA_SCHEMA, user_input)

    async def async_step_serial(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a chlorinator on a serial port."""
        return await self._async_step_link(
            CONF_SERIAL, STEP_SERIAL_DATA_SCHEMA, user_input
        )

    async def _async_step_link(
        self,
        connection_type: str,
        schema: probatio.Schema,
        user_input: dict[str, Any] | None,
    ) -> ConfigFlowResult:
        """Ask for the link settings, then probe the chlorinator behind them."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {CONF_CONNECTION: connection_type, **user_input}
            # The board has no serial number, so the connection settings are the
            # identity; abort before probing if this device is already configured.
            await self.async_set_unique_id(unique_id_for(data))
            self._abort_if_unique_id_configured()
            errors = await self._async_validate(data)
            if not errors:
                return self.async_create_entry(title=DEFAULT_TITLE, data=data)

        return self.async_show_form(
            step_id=connection_type,
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )

    async def _async_validate(self, data: Mapping[str, Any]) -> dict[str, str]:
        """Probe the chlorinator, returning the errors to show, if any."""
        try:
            await _async_probe(self.hass, data)
        except NotAnAquarkDeviceError:
            return {"base": "not_an_aquark"}
        except AquarkError:
            return {"base": "cannot_connect"}
        except Exception:
            _LOGGER.exception("Unexpected error while probing the chlorinator")
            return {"base": "unknown"}
        return {}
