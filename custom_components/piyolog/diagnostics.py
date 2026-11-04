"""Diagnostics support for the PiyoLog integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import PiyologConfigEntry
from .const import CONF_FEED_URL, CONF_FEED_URL_LONG

TO_REDACT = {CONF_FEED_URL, CONF_FEED_URL_LONG}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: PiyologConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry (feed URLs redacted)."""
    coordinator = entry.runtime_data
    data = coordinator.data
    return {
        "entry": {
            "title": entry.title,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "feed": {
            "generated_at": data.generated_at.isoformat()
            if data and data.generated_at
            else None,
            "record_count": data.record_count if data else 0,
            "types_present": sorted(data.last_by_type) if data else [],
            "currently_sleeping": data.currently_sleeping if data else None,
        },
    }
