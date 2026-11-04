"""Binary sensor platform for the PiyoLog integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import PiyologConfigEntry
from .coordinator import PiyologCoordinator
from .sensor import PiyologEntity


class PiyologSleepingSensor(PiyologEntity, BinarySensorEntity):
    """Whether the child is currently asleep."""

    _attr_translation_key = "sleeping"

    def __init__(
        self, coordinator: PiyologCoordinator, entry: PiyologConfigEntry
    ) -> None:
        super().__init__(coordinator, entry, "sleeping", platform_domain="binary_sensor")

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.currently_sleeping

    @property
    def icon(self) -> str:
        return "mdi:sleep" if self.is_on else "mdi:sleep-off"

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        since = self.coordinator.data.sleeping_since
        return {"sleeping_since": since.isoformat() if since else None}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PiyologConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the PiyoLog sleeping binary sensor."""
    async_add_entities([PiyologSleepingSensor(entry.runtime_data, entry)])
