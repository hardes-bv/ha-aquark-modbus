"""Base entity for the Aqaurk (Modbus) integration."""

from collections.abc import Awaitable
from dataclasses import dataclass
from typing import override

from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from aquark_modbus import AquarkConnectionError, AquarkError

from .const import DOMAIN
from .coordinator import AquarkCoordinator
from .helpers import error_detail


@dataclass(frozen=True, kw_only=True)
class AquarkEntityDescription(EntityDescription):
    """Which blocks of the chlorinator an entity reads."""

    # Attribute names on Chlorinator, like "readings".
    blocks: tuple[str, ...]


class AquarkEntity(CoordinatorEntity[AquarkCoordinator]):
    """An entity backed by one or more blocks of the chlorinator.

    Blocks are read independently, so an entity is unavailable when one of
    its own blocks failed to read, not when any block did.
    """

    _attr_has_entity_name = True
    entity_description: AquarkEntityDescription

    def __init__(
        self,
        coordinator: AquarkCoordinator,
        entity_description: AquarkEntityDescription,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        # The board reports no serial number.
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{entity_description.key}"
        )
        self._attr_device_info = coordinator.device_info

    @property
    @override
    def available(self) -> bool:
        """Whether every block of this entity answered the most recent poll."""
        return super().available and all(
            block in self.coordinator.data.updated
            for block in self.entity_description.blocks
        )

    async def _async_write(self, write: Awaitable[None]) -> None:
        """Send a write to the chlorinator, then refresh what it changed."""
        try:
            await write
        # except AquarkRefusedError as err:
        #     raise HomeAssistantError(
        #         translation_domain=DOMAIN,
        #         translation_key="write_refused",
        #         translation_placeholders={"error": error_detail(err)},
        #     ) from err
        except AquarkConnectionError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
                translation_placeholders={"error": error_detail(err)},
            ) from err
        except AquarkError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_value",
                translation_placeholders={"error": error_detail(err)},
            ) from err
        await self.coordinator.async_request_refresh()
