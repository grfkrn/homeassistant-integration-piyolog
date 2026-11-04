"""Tests for the piyolog/get_records WebSocket command."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.piyolog.const import CONF_FEED_URL, DOMAIN
from custom_components.piyolog.feed import parse_feed

from .fixtures import payload, rec
from .test_config_flow import FEED_ID, FEED_URL


def _iso(dt) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


async def _setup(hass: HomeAssistant):
    """Set up an entry whose feed has Formula/Sleep/WakeUp near 'now'."""
    dt_util.set_default_time_zone(ZoneInfo("UTC"))
    now = dt_util.utcnow()
    times = {
        "Formula": now - timedelta(hours=1),
        "Sleep": now - timedelta(minutes=30),
        "WakeUp": now - timedelta(minutes=10),
    }
    snapshot = parse_feed(
        payload(
            [
                rec("f1", _iso(times["Formula"]), "Formula",
                    value={"value": 120, "unit": "ml"}),
                rec("s1", _iso(times["Sleep"]), "Sleep"),
                rec("w1", _iso(times["WakeUp"]), "WakeUp"),
            ],
            generated_at=_iso(now),
        )
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=FEED_ID,
        title="Test Baby",
        data={CONF_NAME: "Test Baby", CONF_FEED_URL: FEED_URL},
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.piyolog.coordinator.fetch_feed",
        new=AsyncMock(return_value=snapshot),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return times


async def test_get_records(hass: HomeAssistant, hass_ws_client) -> None:
    times = await _setup(hass)
    day = times["WakeUp"].date()
    expected_types = [t for t, dt in times.items() if dt.date() == day]

    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "piyolog/get_records",
            "entity_id": "sensor.piyolog_timeline",
            "date": day.isoformat(),
        }
    )
    resp = await client.receive_json()
    assert resp["success"], resp
    result = resp["result"]
    assert result["date"] == day.isoformat()
    # Newest first, and only records of that day.
    got_types = [e["type"] for e in result["entries"]]
    assert got_types == sorted(
        expected_types, key=lambda t: times[t], reverse=True
    )
    wake = result["entries"][got_types.index("WakeUp")]
    assert wake["duration_minutes"] == 20
    if "Formula" in expected_types:
        assert result["summary"]["formula_ml"] == 120.0


async def test_get_records_unknown_entity(
    hass: HomeAssistant, hass_ws_client
) -> None:
    await _setup(hass)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "piyolog/get_records",
            "entity_id": "sensor.does_not_exist",
            "date": "2026-09-09",
        }
    )
    resp = await client.receive_json()
    assert not resp["success"]
    assert resp["error"]["code"] == "entity_not_found"


async def test_get_records_invalid_date(
    hass: HomeAssistant, hass_ws_client
) -> None:
    await _setup(hass)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "piyolog/get_records",
            "entity_id": "sensor.piyolog_timeline",
            "date": "09/09/2026",
        }
    )
    resp = await client.receive_json()
    assert not resp["success"]
    assert resp["error"]["code"] == "invalid_date"
