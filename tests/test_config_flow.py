"""Tests for config_flow.py."""

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.piyolog.config_flow import feed_id_from_url
from custom_components.piyolog.const import (
    CONF_FEED_URL,
    CONF_FEED_URL_LONG,
    DOMAIN,
)
from custom_components.piyolog.feed import FeedHttpError, parse_feed

from .fixtures import payload, sample_records

FEED_ID = "11111111-2222-3333-4444-555555555555"
FEED_URL = f"https://feed.piyolog.com/v1/feed/24h/{FEED_ID}/dummy-secret"
FEED_ID_LONG = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
FEED_URL_LONG = f"https://feed.piyolog.com/v1/feed/28d/{FEED_ID_LONG}/dummy-secret-2"


def _snapshot():
    return parse_feed(payload(sample_records()))


# ---------------------------------------------------------------------------
# URL parsing (pure)
# ---------------------------------------------------------------------------


def test_feed_id_from_url_ok():
    assert feed_id_from_url(FEED_URL) == FEED_ID
    assert feed_id_from_url(FEED_URL_LONG) == FEED_ID_LONG


def test_feed_id_from_url_rejects_bad_urls():
    assert feed_id_from_url("https://example.com/v1/feed/24h/x/y") is None
    assert feed_id_from_url("http://feed.piyolog.com/v1/feed/24h/x/y") is None
    assert feed_id_from_url("https://feed.piyolog.com/v1/feed/99d/x/y") is None
    assert feed_id_from_url("https://feed.piyolog.com/v1/feed/24h/x") is None
    assert feed_id_from_url("not a url") is None
    assert feed_id_from_url("") is None


# ---------------------------------------------------------------------------
# Flow
# ---------------------------------------------------------------------------


async def test_flow_creates_entry(hass: HomeAssistant) -> None:
    with patch(
        "custom_components.piyolog.config_flow.fetch_feed",
        new=AsyncMock(return_value=_snapshot()),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == FlowResultType.FORM
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_NAME: "Test Baby", CONF_FEED_URL: FEED_URL, CONF_FEED_URL_LONG: ""},
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test Baby"
    assert result["data"][CONF_FEED_URL] == FEED_URL
    assert CONF_FEED_URL_LONG not in result["data"]


async def test_flow_invalid_url_does_not_fetch(hass: HomeAssistant) -> None:
    with patch(
        "custom_components.piyolog.config_flow.fetch_feed",
        new=AsyncMock(return_value=_snapshot()),
    ) as mock_fetch:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_NAME: "x", CONF_FEED_URL: "https://example.com/nope"},
        )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_FEED_URL: "invalid_url"}
    mock_fetch.assert_not_called()


async def test_flow_feed_404(hass: HomeAssistant) -> None:
    with patch(
        "custom_components.piyolog.config_flow.fetch_feed",
        new=AsyncMock(side_effect=FeedHttpError(404)),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_NAME: "x", CONF_FEED_URL: FEED_URL}
        )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_FEED_URL: "feed_unavailable"}


async def test_flow_duplicate_aborts(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=FEED_ID, data={})
    entry.add_to_hass(hass)
    with patch(
        "custom_components.piyolog.config_flow.fetch_feed",
        new=AsyncMock(return_value=_snapshot()),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_NAME: "x", CONF_FEED_URL: FEED_URL}
        )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
