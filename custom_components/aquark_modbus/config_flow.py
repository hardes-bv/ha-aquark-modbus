"""Config flow for Aquark (Modbus) devices.

Placeholder: HA requires the ``config_flow`` platform to exist when setting up
an entry (a missing module puts the entry in ``SETUP_ERROR``). The real user
flow (menu → tcp | serial, with device validation) lands in plan step 5.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN


class AquarkModbusConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Aquark (Modbus)."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """User step; not wired up yet."""
        return self.async_abort(reason="not_supported_yet")
