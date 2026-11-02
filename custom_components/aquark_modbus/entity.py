"""Base entity for the Aquark Modbus integration.

Every entity of the integration sits on the one device per config entry, so
this base carries the shared
:class:`~homeassistant.helpers.device_registry.DeviceInfo`, built from the
model the coordinator read once at setup.
"""

from __future__ import annotations

from typing import Final, override

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from semver import Version

from aquark_modbus.model import Model

from .const import DEVICE_TYPE_NAMES, DOMAIN
from .coordinator import AquarkDataUpdateCoordinator

MANUFACTURER: Final = "Aquark"
"""Manufacturer name for the device registry."""

_MISSING_VERSION: Final = Version(0, 0, 0)
"""What all-zero model registers decode as; the board reports no firmware version."""


def model_sw_version(model: Model) -> str | None:
    """The firmware version for display, or ``None`` when absent.

    A board whose model registers all read as zero decodes as ``0.0.0`` rather
    than ``None``, so that is treated as "no version reported".
    """
    version = model.version
    if version is None or version == _MISSING_VERSION:
        return None
    return str(version)


class AquarkEntity(CoordinatorEntity[AquarkDataUpdateCoordinator], Entity):
    """Base class for the Aquark Modbus entities.

    The device information comes from the model the coordinator read at
    setup; the model is static, so it never changes while the entry is loaded.
    """

    _attr_has_entity_name = True

    @property
    @override
    def device_info(self) -> DeviceInfo:
        """Return the device registry information for this chlorinator."""
        model = self.coordinator.data
        device_type = model.device_type
        type_name = (
            DEVICE_TYPE_NAMES.get(device_type) if device_type is not None else None
        )
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.config_entry.unique_id or "")},
            name=type_name or self.coordinator.config_entry.title,
            manufacturer=MANUFACTURER,
            model=type_name,
            sw_version=model_sw_version(model),
        )
