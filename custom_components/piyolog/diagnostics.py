"""Diagnostics support for the PiyoLog integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant

from . import PiyologConfigEntry
from .const import CONF_FEED_URL, CONF_FEED_URL_LONG

# The entry title and the configured name are the child's device label,
# so they can hold a child's name and must never leave the home
# unredacted in a diagnostics download.
TO_REDACT = {CONF_FEED_URL, CONF_FEED_URL_LONG, CONF_NAME, "title"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: PiyologConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry (feed URLs and names redacted)."""
    coordinator = entry.runtime_data
    data = coordinator.data
    return {
        "entry": async_redact_data(
            {
                "title": entry.title,
                "data": dict(entry.data),
                "options": dict(entry.options),
            },
            TO_REDACT,
        ),
        "feed": {
            "generated_at": data.generated_at.isoformat()
            if data and data.generated_at
            else None,
            "record_count": data.record_count if data else 0,
            "types_present": sorted(data.last_by_type) if data else [],
            "currently_sleeping": data.currently_sleeping if data else None,
        },
    }
