"""Config flow for the Aquark (Modbus) integration."""

import logging
from collections.abc import Mapping
from typing import Any, override

import probatio
from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_DEVICE, CONF_HOST, CONF_PORT, CONF_TYPE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SerialPortSelector,
    TextSelector,
)

from aquark_modbus import AquarkConnectionError, AquarkError, Chlorinator

from .const import (
    CONF_UNIT_ID,
    DEFAULT_PORT,
    DEFAULT_UNIT_ID,
    DOMAIN,
    TYPE_SERIAL,
    TYPE_TCP,
)
from .helpers import create_modbus_params

_LOGGER = logging.getLogger(__name__)

# The board reports no model, so every entry gets the same default title.
DEFAULT_TITLE = "Aquark chlorinator"

UNIT_ID_SELECTOR = probatio.All(
    NumberSelector(NumberSelectorConfig(mode=NumberSelectorMode.BOX, min=1, max=247)),
    probatio.Coerce(int),
)

STEP_TCP_DATA_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_HOST): TextSelector(),
        probatio.Required(CONF_PORT, default=DEFAULT_PORT): probatio.All(
            NumberSelector(
                NumberSelectorConfig(mode=NumberSelectorMode.BOX, min=1, max=65535)
            ),
            probatio.Coerce(int),
        ),
        probatio.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): UNIT_ID_SELECTOR,
    }
)

STEP_SERIAL_DATA_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_DEVICE): SerialPortSelector(),
        probatio.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): UNIT_ID_SELECTOR,
    }
)

# The link settings that identify one chlorinator, by connection type.
IDENTITY_KEYS = {
    TYPE_TCP: (CONF_TYPE, CONF_HOST, CONF_PORT, CONF_UNIT_ID),
    TYPE_SERIAL: (CONF_TYPE, CONF_DEVICE, CONF_UNIT_ID),
}


class _UnitSilentError(Exception):
    """The link is up, but the chlorinator behind it does not answer."""


async def _async_probe(hass: HomeAssistant, data: Mapping[str, Any]) -> None:
    """Read the chlorinator behind these link settings, or raise."""
    params = create_modbus_params(data)
    async with async_get_temporary_unit(hass, params, data[CONF_UNIT_ID]) as unit:
        try:
            await Chlorinator(unit).async_validate()
        except AquarkConnectionError as err:
            if unit.connected:
                raise _UnitSilentError from err
            raise


class AquarkConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for a Aquark chlorinator."""

    VERSION = 1

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user pick how the chlorinator is reached."""
        return self.async_show_menu(
            step_id="user", menu_options=[TYPE_TCP, TYPE_SERIAL]
        )

    async def async_step_tcp(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a chlorinator behind a Modbus TCP gateway."""
        return await self._async_step_link(TYPE_TCP, STEP_TCP_DATA_SCHEMA, user_input)

    async def async_step_serial(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a chlorinator on a serial port."""
        return await self._async_step_link(
            TYPE_SERIAL, STEP_SERIAL_DATA_SCHEMA, user_input
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
            data = {CONF_TYPE: connection_type, **user_input}
            # The board has no serial number to use as a unique ID.
            self._async_abort_entries_match(
                {key: data[key] for key in IDENTITY_KEYS[connection_type]}
            )
            errors = await self._async_validate(data)
            if not errors:
                return self.async_create_entry(title=DEFAULT_TITLE, data=data)

        return self.async_show_form(
            step_id=connection_type,
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )

    async def _async_validate(self, data: dict[str, Any]) -> dict[str, str]:
        """Probe the chlorinator, returning the errors to show, if any."""
        try:
            await _async_probe(self.hass, data)
        except _UnitSilentError:
            return {"base": "unit_silent"}
        except AquarkConnectionError:
            return {"base": "cannot_connect"}
        except AquarkError:
            return {"base": "not_an_aquark_chlorinator"}
        except HomeAssistantError:
            # Another config entry holds this connection with other settings.
            return {"base": "link_in_use"}
        except Exception:
            _LOGGER.exception("Unexpected exception")
            return {"base": "unknown"}
        return {}
