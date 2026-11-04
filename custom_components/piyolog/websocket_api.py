"""WebSocket API for the PiyoLog integration.

Serves feed records to the bundled Lovelace card. Sensor attributes
cannot carry a whole feed window (28 days is 1,000+ records), so the
card asks for one day at a time:

``piyolog/get_records`` with ``entity_id`` (any sensor of the config
entry, used to identify whose records to serve) and ``date``
(``YYYY-MM-DD``, local) returns that day's records with their original
feed times and values, plus the day's summary totals.
"""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .feed import entries_for_day

_LOGGER = logging.getLogger(__name__)


@callback
def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register the integration's WebSocket commands (once)."""
    websocket_api.async_register_command(hass, ws_get_records)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "piyolog/get_records",
        vol.Required("entity_id"): str,
        vol.Required("date"): str,
    }
)
@websocket_api.async_response
async def ws_get_records(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Return one day's feed records and summary for the Lovelace card."""
    registry = er.async_get(hass)
    entity_entry = registry.async_get(msg["entity_id"])
    if entity_entry is None or entity_entry.config_entry_id is None:
        connection.send_error(
            msg["id"], "entity_not_found", f"Unknown entity: {msg['entity_id']}"
        )
        return
    entry = hass.config_entries.async_get_entry(entity_entry.config_entry_id)
    coordinator = getattr(entry, "runtime_data", None) if entry else None
    if entry is None or entry.domain != DOMAIN or coordinator is None:
        connection.send_error(
            msg["id"], "not_piyolog", "The entity does not belong to a PiyoLog entry"
        )
        return
    try:
        day = datetime.strptime(msg["date"], "%Y-%m-%d").date()
    except ValueError:
        connection.send_error(
            msg["id"], "invalid_date", f"Invalid date: {msg['date']}"
        )
        return

    tz = dt_util.get_default_time_zone()
    entries = entries_for_day(coordinator.records, tz, day)
    summary: dict[str, Any] = {}
    for key, points in coordinator.data.daily_totals.items():
        for point in points:
            if point["start"].date() == day:
                summary[key] = point["value"]
                break
    connection.send_result(
        msg["id"],
        {
            "date": day.isoformat(),
            "entries": entries,
            "summary": summary,
            "generated_at": coordinator.data.generated_at.isoformat()
            if coordinator.data.generated_at
            else None,
        },
    )
