"""Tests for the aquark_modbus data update coordinator.

These tests build the coordinator directly (rather than through
``init_integration``) so it can be verified in isolation, before the
integration's setup/unload code lands.
"""

from __future__ import annotations

import pytest
from aquark_modbus import Chlorinator, DeviceType
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from modbus_connection import ModbusConnectionError
from modbus_connection.mock import MockModbusConnection
from pytest_homeassistant_custom_component.common import MockConfigEntry
from semver import Version

from custom_components.aquark_modbus.const import DOMAIN
from custom_components.aquark_modbus.coordinator import AquarkDataUpdateCoordinator
from tests.conftest import DEFAULT_UNIT, TCP_HOST, TCP_PORT, tcp_entry_data


def _make_entry(hass: HomeAssistant) -> MockConfigEntry:
    """A mock TCP config entry, shaped like the one the flow will store."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=tcp_entry_data(),
        unique_id=f"tcp:{TCP_HOST}:{TCP_PORT}:{DEFAULT_UNIT}",
    )
    entry.add_to_hass(hass)
    return entry


def test_placeholder(hass: HomeAssistant) -> None:
    """Smoke test: the HA test instance is up and running."""
    assert hass.state == CoreState.running


async def test_coordinator_reads_model(
    hass: HomeAssistant,
    mock_connection: MockModbusConnection,
) -> None:
    """The coordinator decodes the model registers of a healthy device."""
    entry = _make_entry(hass)
    coordinator = AquarkDataUpdateCoordinator(
        hass, entry, Chlorinator(mock_connection.for_unit(DEFAULT_UNIT))
    )

    await coordinator.async_refresh()

    assert coordinator.last_update_success is True
    assert coordinator.data.version == Version(2, 1, 3)
    assert coordinator.data.device_type is DeviceType.MR_PURE_PRO


async def test_coordinator_update_failed_on_connection_error(
    hass: HomeAssistant,
    mock_connection: MockModbusConnection,
) -> None:
    """A dead link surfaces as ``UpdateFailed`` from the update method."""
    entry = _make_entry(hass)
    unit = mock_connection.for_unit(DEFAULT_UNIT)
    unit.fail_requests(ModbusConnectionError())
    coordinator = AquarkDataUpdateCoordinator(hass, entry, Chlorinator(unit))

    with pytest.raises(UpdateFailed, match="Unable to read the model"):
        await coordinator._async_update_data()
