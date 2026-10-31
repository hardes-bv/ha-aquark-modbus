"""Sensor platform for the Aquark (Modbus) integration."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import override

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
)

from aquark_modbus import Chlorinator

from .coordinator import AquarkConfigEntry, AquarkCoordinator
from .entity import AquarkEntity


@dataclass(frozen=True, kw_only=True)
class AquarkSensorEntityDescription(SensorEntityDescription):
    """Describe an Aquark sensor."""

    value_fn: Callable[[Chlorinator], float | int]


SENSORS: tuple[AquarkSensorEntityDescription, ...] = (
    AquarkSensorEntityDescription(
        key="pool_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda chlorinator: chlorinator.readings.pool_temperature,
    ),
    # AquarkSensorEntityDescription(
    #     key="chlorine_production",
    #     device_class=SensorDeviceClass.HUMIDITY,
    #     native_unit_of_measurement=UnitOfRatio.PERCENTAGE,
    #     state_class=SensorStateClass.MEASUREMENT,
    #     value_fn=lambda chlorinator: chlorinator.readings.chlorine_production,
    # ),
    AquarkSensorEntityDescription(
        key="ph",
        device_class=SensorDeviceClass.PH,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda chlorinator: chlorinator.readings.ph,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AquarkConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Aquark sensors."""
    coordinator = entry.runtime_data

    async_add_entities(
        AquarkSensor(coordinator, description) for description in SENSORS
    )


class AquarkSensor(AquarkEntity, SensorEntity):
    """A sensor of an Aquark chlorinator."""

    entity_description: AquarkSensorEntityDescription

    def __init__(
        self,
        coordinator: AquarkCoordinator,
        description: AquarkSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"

    @property
    @override
    def native_value(self) -> float | int:
        """Return the value of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)
