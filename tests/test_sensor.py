"""Tests for the Aquark Modbus sensor platform.

The firmware version sensor is the first entity the integration publishes:
it hosts the device, so these tests also verify the device registry is
populated from the model.
"""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceRegistry
from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy.assertion import SnapshotAssertion

from custom_components.aquark_modbus.const import DOMAIN, unique_id_for


async def test_firmware_version_value(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """The sensor reports the firmware version from the model registers."""
    state = hass.states.get("sensor.mr_pure_pro_firmware_version")
    assert state is not None
    assert state.state == "2.1.3"
    assert state.attributes["friendly_name"] == "Mr Pure Pro Firmware Version"


async def test_firmware_version_snapshot(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """The sensor state matches the snapshot."""
    state = hass.states.get("sensor.mr_pure_pro_firmware_version")
    assert state is not None
    assert state == snapshot


async def test_device_info(
    hass: HomeAssistant,
    device_registry: DeviceRegistry,
    init_integration: MockConfigEntry,
) -> None:
    """The device registry is populated from the model registers."""
    entry = init_integration
    device = device_registry.async_get_device_by_identifier(
        (DOMAIN, unique_id_for(entry.data)),
        config_entry_id=entry.entry_id,
    )
    assert device is not None
    assert device.manufacturer == "Aquark"
    assert device.model == "Mr Pure Pro"
    assert device.sw_version == "2.1.3"
    assert device.name == "Mr Pure Pro"


@pytest.mark.parametrize(
    "register_image",
    [
        {
            # No model registers (input 13..15): the board reports no
            # firmware version, so the sensor must not show a bogus one.
            "input": {address: 0 for address in range(13)},
            "discrete": {50: True},
            "holding": {address: 0 for address in range(8)},
        }
    ],
    indirect=True,
)
async def test_firmware_version_unavailable_when_missing(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Without model registers the firmware version sensor is unavailable."""
    state = hass.states.get("sensor.mr_pure_firmware_version")
    assert state is not None
    assert state.state == "unavailable"
