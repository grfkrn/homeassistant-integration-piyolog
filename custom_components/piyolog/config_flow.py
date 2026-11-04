"""Config flow for the PiyoLog integration."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_FEED_URL,
    CONF_FEED_URL_LONG,
    CONF_SCAN_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    FEED_HOST,
    FEED_PERIODS,
)
from .feed import FeedHttpError, fetch_feed

_LOGGER = logging.getLogger(__name__)


def feed_id_from_url(url: str) -> str | None:
    """Extract the feed id from a feed URL, or None if the URL is invalid.

    Expected form: https://feed.piyolog.com/v1/feed/{period}/{feed_id}/{secret}
    """
    try:
        parsed = urlparse(url.strip())
    except (ValueError, AttributeError):
        return None
    if parsed.scheme != "https" or parsed.hostname != FEED_HOST:
        return None
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) != 5 or parts[0] != "v1" or parts[1] != "feed":
        return None
    if parts[2] not in FEED_PERIODS:
        return None
    feed_id, secret = parts[3], parts[4]
    if not feed_id or not secret:
        return None
    return feed_id


async def _validate_feed(hass, url: str) -> str | None:
    """Fetch the feed once; return an error key or None on success."""
    if feed_id_from_url(url) is None:
        return "invalid_url"
    session = async_get_clientsession(hass)
    try:
        await fetch_feed(session, url.strip())
    except FeedHttpError as err:
        return "feed_unavailable" if err.status == 404 else "cannot_connect"
    except Exception:  # noqa: BLE001 - mapped to a user-facing error below
        _LOGGER.debug("Feed validation failed", exc_info=True)
        return "cannot_connect"
    return None


class PiyologConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PiyoLog."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            feed_url = (user_input.get(CONF_FEED_URL) or "").strip()
            feed_url_long = (user_input.get(CONF_FEED_URL_LONG) or "").strip()
            name = (user_input.get(CONF_NAME) or "").strip() or DEFAULT_NAME

            error = await _validate_feed(self.hass, feed_url)
            if error:
                errors[CONF_FEED_URL] = error
            elif feed_url_long:
                error = await _validate_feed(self.hass, feed_url_long)
                if error:
                    errors[CONF_FEED_URL_LONG] = error

            if not errors:
                feed_id = feed_id_from_url(feed_url)
                await self.async_set_unique_id(feed_id)
                self._abort_if_unique_id_configured()
                data: dict[str, Any] = {CONF_NAME: name, CONF_FEED_URL: feed_url}
                if feed_url_long:
                    data[CONF_FEED_URL_LONG] = feed_url_long
                return self.async_create_entry(title=name, data=data)

        schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_FEED_URL): str,
                vol.Optional(CONF_FEED_URL_LONG, default=""): str,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return PiyologOptionsFlow()


class PiyologOptionsFlow(OptionsFlow):
    """Options for PiyoLog (polling interval of the main feed)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MINUTES
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=60)
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
