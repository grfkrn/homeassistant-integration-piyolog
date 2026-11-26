"""Tests for diagnostics redaction."""

from __future__ import annotations

from types import SimpleNamespace

from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant

from custom_components.piyolog.const import CONF_FEED_URL, CONF_FEED_URL_LONG
from custom_components.piyolog.diagnostics import (
    async_get_config_entry_diagnostics,
)

CHILD_NAME = "Test Child Name"
FEED_URL = "https://feed.piyolog.com/v1/feed/24h/abc/secretpart"


async def test_diagnostics_redact_title_name_and_feed_urls(
    hass: HomeAssistant,
) -> None:
    """The child's name (title / label) and feed URLs never leak."""
    entry = SimpleNamespace(
        title=CHILD_NAME,
        data={
            CONF_NAME: CHILD_NAME,
            CONF_FEED_URL: FEED_URL,
            CONF_FEED_URL_LONG: FEED_URL,
        },
        options={},
        runtime_data=SimpleNamespace(data=None),
    )
    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["entry"]["title"] == "**REDACTED**"
    assert result["entry"]["data"][CONF_NAME] == "**REDACTED**"
    assert result["entry"]["data"][CONF_FEED_URL] == "**REDACTED**"
    assert result["entry"]["data"][CONF_FEED_URL_LONG] == "**REDACTED**"
    assert CHILD_NAME not in str(result)
    assert "secretpart" not in str(result)
