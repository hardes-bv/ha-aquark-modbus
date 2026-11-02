"""Sensor platform for the Aquark Modbus integration.

Publishes the firmware version reported in the chlorinator's model registers.
"""

from __future__ import annotations

from typing import Final, override

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import AquarkDataUpdateCoordinator
from .entity import AquarkEntity, model_sw_version

FIRMWARE_VERSION: Final = SensorEntityDescription(
    key="firmware_version",
    translation_key="firmware_version",
    icon="mdi:chip",
)


class FirmwareVersionSensor(AquarkEntity, SensorEntity):
    """The firmware version reported in the model registers."""

    def __init__(
        self,
        coordinator: AquarkDataUpdateCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description

    @property
    @override
    def native_value(self) -> str | None:
        """The firmware version, or ``None`` when the board reports none."""
        return model_sw_version(self.coordinator.data)

    @property
    @override
    def available(self) -> bool:
        """Unavailable until a usable firmware version has been reported."""
        return super().available and self.native_value is not None

    @property
    @override
    def unique_id(self) -> str:
        """One unique id per connection, derived from the config entry's."""
        return (
            f"{self.coordinator.config_entry.unique_id or ''}"
            f":{self.entity_description.key}"
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Aquark Modbus sensors from a config entry."""
    del hass
    coordinator: AquarkDataUpdateCoordinator = entry.runtime_data
    async_add_entities([FirmwareVersionSensor(coordinator, FIRMWARE_VERSION)])
