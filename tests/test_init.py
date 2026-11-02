"""Tests for the aquark_modbus setup, unload, and data update coordinator.

The coordinator tests build the coordinator directly (rather than through
``init_integration``) so it can be verified in isolation; the setup tests go
through the full ``hass.config_entries`` path with the mock Modbus unit.
"""

from __future__ import annotations

from unittest import mock

import pytest
from aquark_modbus import Chlorinator, DeviceType
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from modbus_connection import ModbusConnectionError, ModbusTimeoutError
from modbus_connection.mock import MockModbusConnection
from pytest_homeassistant_custom_component.common import MockConfigEntry
from semver import Version

from custom_components.aquark_modbus.const import DOMAIN, unique_id_for
from custom_components.aquark_modbus.coordinator import AquarkDataUpdateCoordinator
from tests.conftest import (
    DEFAULT_UNIT,
    TCP_HOST,
    TCP_PORT,
    serial_entry_data,
    tcp_entry_data,
)


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


async def test_setup_and_unload(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """The entry loads, exposes the coordinator, and unloads cleanly."""
    entry = init_integration
    assert isinstance(entry.runtime_data, AquarkDataUpdateCoordinator)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_serial_entry_sets_up(
    hass: HomeAssistant,
    mock_get_unit: mock.MagicMock,
    mock_connection: MockModbusConnection,
) -> None:
    """A serial connection goes through the ``ModbusSerialParams`` branch."""
    data = serial_entry_data()
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=data,
        unique_id=unique_id_for(data),
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert isinstance(entry.runtime_data, AquarkDataUpdateCoordinator)


async def test_not_ready_on_connection_error(
    hass: HomeAssistant,
    mock_get_unit: mock.MagicMock,
    mock_connection: MockModbusConnection,
) -> None:
    """A dead link defers the setup so Home Assistant retries with backoff."""
    mock_connection.for_unit(DEFAULT_UNIT).fail_requests(ModbusConnectionError())
    entry = _make_entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_not_ready_on_timeout(
    hass: HomeAssistant,
    mock_get_unit: mock.MagicMock,
    mock_connection: MockModbusConnection,
) -> None:
    """A silent unit (timeout) defers the setup the same way."""
    mock_connection.for_unit(DEFAULT_UNIT).fail_requests(ModbusTimeoutError())
    entry = _make_entry(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY


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
