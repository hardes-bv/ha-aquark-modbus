"""Shared fixtures for the aquark_modbus integration tests.

Built on `pytest-homeassistant-custom-component`: the `hass` fixture boots a
real Home Assistant instance, and custom integrations are discovered via
`import custom_components` (the repository root is on `sys.path` because
`tests/` is a package).

The `mock_get_unit` / `mock_temporary_unit` fixtures patch the integration's
own imports of `homeassistant.components.modbus.async_get_unit` /
`async_get_temporary_unit`, so those names must be imported at module level in
the integration once it is implemented.

NOTE: `ModbusParams` is imported only for typing. Importing
`homeassistant.components.modbus` at runtime is deferred to the integration
itself (its setup pulls in the modbus backend), so the conftest must not do it.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator, Mapping
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, cast
from unittest import mock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from modbus_connection.mock import MockModbusConnection, MockModbusUnit
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.syrupy import (
    HomeAssistantSnapshotExtension,
)
from syrupy.assertion import SnapshotAssertion

if TYPE_CHECKING:
    from homeassistant.components.modbus.connection import ModbusParams

DOMAIN = "aquark_modbus"
"""Integration domain; keep in sync with ``manifest.json`` until const.py exists."""

DEFAULT_UNIT = 8
"""Modbus unit ID, the config flow default."""

TCP_HOST = "192.168.1.50"
"""Default host for mock TCP entries."""

TCP_PORT = 502
"""Default port for mock TCP entries."""

# Config entry data keys, in the shape the config flow stores them.
CONF_CONNECTION = "connection"  # "tcp" | "serial"
CONF_HOST = "host"
CONF_PORT = "port"
CONF_UNIT = "unit"
CONF_DEVICE = "device"

type RegisterImage = Mapping[str, Mapping[int, int | bool]]


def tcp_entry_data(
    host: str = TCP_HOST,
    port: int = TCP_PORT,
    unit: int = DEFAULT_UNIT,
) -> dict[str, Any]:
    """Config entry data for a TCP connection, as stored by the config flow."""
    return {
        CONF_CONNECTION: "tcp",
        CONF_HOST: host,
        CONF_PORT: port,
        CONF_UNIT: unit,
    }


def serial_entry_data(
    device: str = "/dev/ttyUSB0",
    unit: int = DEFAULT_UNIT,
) -> dict[str, Any]:
    """Config entry data for a serial connection, as stored by the config flow."""
    return {
        CONF_CONNECTION: "serial",
        CONF_DEVICE: device,
        CONF_UNIT: unit,
    }


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Make custom integrations in ``custom_components/`` loadable in every test."""


@pytest.fixture
def snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Snapshot assertion configured with the Home Assistant extension."""
    return snapshot.use_extension(HomeAssistantSnapshotExtension)


@pytest.fixture
def register_image(request: pytest.FixtureRequest) -> RegisterImage:
    """Register map for the mocked device: a healthy Mr Pure Pro, firmware 2.1.3.

    Override per test with::

        @pytest.mark.parametrize("register_image", [{...}], indirect=True)
    """
    if (param := getattr(request, "param", None)) is not None:
        return param
    return {
        "input": {
            # Readings, input space 0..12
            0: 750,  # ORP in mV
            1: 750,  # pH, x100 -> 7.50
            2: 1200,  # electrical conductivity in ppm
            3: 265,  # pool temperature, x10 -> 26.5 °C
            4: 350,  # controller temperature, x10 -> 35.0 °C
            5: 80,  # chlorine production in %
            6: 2,  # water quality: PERFECT
            7: 20,  # electrolytic plate specifications in g
            8: 2000,  # SJ in mV
            9: 100,  # SI
            10: 200,  # SV
            11: 150,  # electrolytic current, x100 -> 1.50 A
            12: 1200,  # electrolytic voltage, x100 -> 12.00 V
            # Model, input space 13..15
            13: 2,  # firmware version major
            14: (1 << 8) | 3,  # firmware version minor/patch -> 2.1.3
            15: 6,  # device type: MR_PURE_PRO
        },
        "discrete": {
            50: True,  # flow switch closed; all fault flags stay off
        },
        "holding": {
            # Settings, holding space 0..7
            0: 1,  # operating mode: AUTO_MODE
            1: 8,  # parallel address, matching the unit ID
            2: 750,  # ideal ORP in mV
            3: 745,  # ideal pH, x100 -> 7.45
            4: 50,  # pool volume in m³
            5: 0,  # timer disabled
            6: 8 << 8,  # power on at 08:00 (hour:minute register)
            7: 20 << 8,  # power off at 20:00 (hour:minute register)
        },
    }


@pytest.fixture
def mock_connection(
    mock_modbus_connection: MockModbusConnection,
    register_image: RegisterImage,
) -> MockModbusConnection:
    """A ``MockModbusConnection`` with ``register_image`` loaded on the default unit."""
    unit = mock_modbus_connection.for_unit(DEFAULT_UNIT)
    # `load_raw` is typed with `int | str` keys; our images use plain `int` keys.
    unit.load_raw(cast("Mapping[str, Mapping[int | str, int | bool]]", register_image))
    return mock_modbus_connection


@pytest.fixture
def mock_get_unit(mock_connection: MockModbusConnection) -> Generator[mock.MagicMock]:
    """Point ``async_get_unit`` at the mock connection."""

    def _async_get_unit(
        hass: HomeAssistant,
        entry: MockConfigEntry,
        params: ModbusParams,
        unit_id: int,
    ) -> MockModbusUnit:
        return mock_connection.for_unit(unit_id)

    with mock.patch(
        "custom_components.aquark_modbus.async_get_unit",
        side_effect=_async_get_unit,
    ) as patched:
        yield patched


@pytest.fixture
def mock_temporary_unit(
    mock_connection: MockModbusConnection,
) -> Generator[mock.MagicMock]:
    """Point ``async_get_temporary_unit`` at the mock connection."""

    @asynccontextmanager
    async def _temporary_unit(
        hass: HomeAssistant,
        params: ModbusParams,
        unit_id: int,
    ) -> AsyncGenerator[MockModbusUnit]:
        yield mock_connection.for_unit(unit_id)

    # Patched on ``config_flow`` because that is where the name is imported;
    # the package ``__init__`` does not import ``async_get_temporary_unit``.
    with mock.patch(
        "custom_components.aquark_modbus.config_flow.async_get_temporary_unit",
        side_effect=_temporary_unit,
    ) as patched:
        yield patched


@pytest.fixture
async def init_integration(
    hass: HomeAssistant,
    mock_get_unit: mock.MagicMock,
) -> AsyncGenerator[MockConfigEntry]:
    """Create a mock TCP config entry and set up the integration."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=tcp_entry_data(),
        unique_id=f"tcp:{TCP_HOST}:{TCP_PORT}:{DEFAULT_UNIT}",
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    yield entry
