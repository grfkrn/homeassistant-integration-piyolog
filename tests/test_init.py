"""Tests for integration setup and entity states."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.piyolog.const import (
    CONF_FEED_URL,
    CONF_FEED_URL_LONG,
    DOMAIN,
)
from custom_components.piyolog.feed import parse_feed

from .fixtures import payload, rec
from .test_config_flow import FEED_ID, FEED_URL, FEED_URL_LONG


def _iso(dt) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _snapshots():
    now = dt_util.utcnow()
    main = parse_feed(
        payload(
            [
                rec("f1", _iso(now - timedelta(hours=1)), "Formula",
                    value={"value": 120, "unit": "ml"}),
                rec("s1", _iso(now - timedelta(minutes=30)), "Sleep"),
            ],
            generated_at=_iso(now),
        )
    )
    long = parse_feed(
        payload(
            [
                rec("w1", _iso(now - timedelta(hours=2)), "Weight",
                    value={"value": 6.3, "unit": "kg"}),
            ],
            generated_at=_iso(now),
        )
    )

    async def fake_fetch(session, url):
        return long if "/28d/" in url else main

    return fake_fetch


async def test_setup_creates_piyolog_entities(hass: HomeAssistant) -> None:
    dt_util.set_default_time_zone(ZoneInfo("UTC"))
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=FEED_ID,
        title="Test Baby",
        data={
            CONF_NAME: "Test Baby",
            CONF_FEED_URL: FEED_URL,
            CONF_FEED_URL_LONG: FEED_URL_LONG,
        },
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.piyolog.coordinator.fetch_feed",
        new=AsyncMock(side_effect=_snapshots()),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    weight = hass.states.get("sensor.piyolog_weight")
    assert weight is not None
    assert weight.state == "6.3"
    assert weight.attributes.get("measured_at") is not None

    last_formula = hass.states.get("sensor.piyolog_last_formula")
    assert last_formula is not None
    assert last_formula.state not in ("unknown", "unavailable")

    sleeping = hass.states.get("binary_sensor.piyolog_sleeping")
    assert sleeping is not None
    assert sleeping.state == "on"

    timeline = hass.states.get("sensor.piyolog_timeline")
    assert timeline is not None
    assert isinstance(timeline.attributes.get("records"), list)

    bf_total = hass.states.get("sensor.piyolog_today_breast_feeding_total")
    assert bf_total is not None
    assert float(bf_total.state) == 0.0
    assert bf_total.attributes.get("measured_count") == 0
    assert bf_total.attributes.get("count_today") == 0

    recent = hass.states.get("sensor.piyolog_recent_events")
    assert recent is not None
    recent_records = recent.attributes.get("records")
    assert isinstance(recent_records, list)
    assert len(recent_records) == 3
    assert recent.attributes.get("count") == 3
    assert recent.attributes.get("total_records") == 3

    last_update = hass.states.get("sensor.piyolog_last_update")
    assert last_update is not None
    assert last_update.attributes.get("record_count") == 3

    # Types with no records are unknown, not errors.
    assert hass.states.get("sensor.piyolog_last_poop").state == "unknown"

    # Regression: the MDI name is "emoticon-poop", not "emoticon-poo"
    # (the latter does not exist and renders as a blank icon).
    assert (
        hass.states.get("sensor.piyolog_last_poop").attributes.get("icon")
        == "mdi:emoticon-poop"
    )
    assert (
        hass.states.get("sensor.piyolog_today_poop_count").attributes.get("icon")
        == "mdi:emoticon-poop"
    )

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
