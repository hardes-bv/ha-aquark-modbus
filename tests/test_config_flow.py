"""Tests for the Aquark (Modbus) config flow.

The flow is exercised end to end: the user picks a connection type in the menu,
fills in the link settings, and the flow probes the (mock) device before it
creates the entry. Probe failures are retryable form errors; a device that is
already configured aborts the flow.
"""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from modbus_connection import (
    ModbusConnectionError,
    ModbusExceptionError,
    ModbusTimeoutError,
)
from modbus_connection.mock import MockModbusConnection
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aquark_modbus.const import (
    CONF_DEVICE,
    CONF_HOST,
    CONF_PORT,
    CONF_UNIT,
    DOMAIN,
)
from tests.conftest import (
    DEFAULT_UNIT,
    TCP_HOST,
    TCP_PORT,
    serial_entry_data,
    tcp_entry_data,
)

DEFAULT_TITLE = "Aquark chlorinator"
SERIAL_DEVICE = "/dev/ttyUSB0"

# Every test runs with both the temporary unit (used by the probe) and the entry
# unit (used when the created entry is set up) pointed at the mock connection, so
# nothing can touch the real network.
pytestmark = pytest.mark.usefixtures("mock_temporary_unit", "mock_get_unit")


def tcp_input(**overrides: Any) -> dict[str, Any]:
    """Valid TCP form input, matching the conftest defaults."""
    data = {CONF_HOST: TCP_HOST, CONF_PORT: TCP_PORT, CONF_UNIT: DEFAULT_UNIT}
    data.update(overrides)
    return data


def serial_input(**overrides: Any) -> dict[str, Any]:
    """Valid serial form input, matching the conftest defaults."""
    data = {CONF_DEVICE: SERIAL_DEVICE, CONF_UNIT: DEFAULT_UNIT}
    data.update(overrides)
    return data


async def _start(hass: HomeAssistant, step: str) -> str:
    """Open the user flow and pick a connection type; return the flow id."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": step}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == step
    return result["flow_id"]


async def test_full_flow_tcp(hass: HomeAssistant) -> None:
    """The menu leads to a TCP entry shaped like the conftest data."""
    flow_id = await _start(hass, "tcp")
    result = await hass.config_entries.flow.async_configure(flow_id, tcp_input())

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == DEFAULT_TITLE
    assert result["data"] == tcp_entry_data()
    assert result["result"].unique_id == f"tcp:{TCP_HOST}:{TCP_PORT}:{DEFAULT_UNIT}"


async def test_full_flow_serial(hass: HomeAssistant) -> None:
    """The menu leads to a serial entry shaped like the conftest data."""
    flow_id = await _start(hass, "serial")
    result = await hass.config_entries.flow.async_configure(flow_id, serial_input())

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == DEFAULT_TITLE
    assert result["data"] == serial_entry_data()
    assert result["result"].unique_id == f"serial:{SERIAL_DEVICE}:{DEFAULT_UNIT}"


async def test_abort_already_configured(hass: HomeAssistant) -> None:
    """The same device on the same link cannot be added twice."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=tcp_entry_data(),
        unique_id=f"tcp:{TCP_HOST}:{TCP_PORT}:{DEFAULT_UNIT}",
    )
    entry.add_to_hass(hass)

    flow_id = await _start(hass, "tcp")
    result = await hass.config_entries.flow.async_configure(flow_id, tcp_input())

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_not_an_aquark(
    hass: HomeAssistant, mock_connection: MockModbusConnection
) -> None:
    """A device that refuses the registers is reported, then the retry works."""
    unit = mock_connection.for_unit(DEFAULT_UNIT)
    unit.fail_requests(ModbusExceptionError(2))

    flow_id = await _start(hass, "tcp")
    result = await hass.config_entries.flow.async_configure(flow_id, tcp_input())

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "not_an_aquark"}

    # The user can retry once the right device answers.
    unit.fail_requests(None)
    result = await hass.config_entries.flow.async_configure(flow_id, tcp_input())
    assert result["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(ModbusConnectionError(), id="connection_error"),
        pytest.param(ModbusTimeoutError(), id="timeout"),
    ],
)
async def test_cannot_connect(
    hass: HomeAssistant,
    mock_connection: MockModbusConnection,
    error: Exception,
) -> None:
    """A dead link or a silent unit is reported, then the retry works."""
    unit = mock_connection.for_unit(DEFAULT_UNIT)
    unit.fail_requests(error)

    flow_id = await _start(hass, "tcp")
    result = await hass.config_entries.flow.async_configure(flow_id, tcp_input())

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    unit.fail_requests(None)
    result = await hass.config_entries.flow.async_configure(flow_id, tcp_input())
    assert result["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.parametrize(
    "user_input",
    [
        pytest.param(tcp_input(host=""), id="empty_host"),
        pytest.param(tcp_input(host="   "), id="blank_host"),
        pytest.param(tcp_input(unit=0), id="unit_too_small"),
        pytest.param(tcp_input(unit=248), id="unit_too_large"),
        pytest.param(tcp_input(port=0), id="port_too_small"),
        pytest.param(tcp_input(port=65536), id="port_too_large"),
    ],
)
async def test_invalid_user_input(
    hass: HomeAssistant, user_input: dict[str, Any]
) -> None:
    """Invalid link settings are rejected before a probe is attempted."""
    flow_id = await _start(hass, "tcp")

    with pytest.raises(InvalidData):
        await hass.config_entries.flow.async_configure(flow_id, user_input)
