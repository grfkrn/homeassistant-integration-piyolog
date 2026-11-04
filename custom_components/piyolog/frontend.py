"""Serve and register the bundled Lovelace cards.

The card JavaScript lives in ``frontend/`` next to this module. It is
served under ``/piyolog_static/`` and loaded on every frontend page via
``add_extra_js_url`` so ``custom:piyolog-card`` and
``custom:piyolog-elapsed-card`` are available in the card picker
without any manual resource registration.
"""

from __future__ import annotations

import logging
import os

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

URL_BASE = "/piyolog_static"
CARD_FILENAME = "piyolog-card.js"
ELAPSED_CARD_FILENAME = "piyolog-elapsed-card.js"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the card file and register it with the frontend (once)."""
    if hass.http is None:
        _LOGGER.debug("HTTP component unavailable; skipping card registration")
        return
    integration = await async_get_integration(hass, DOMAIN)
    version = str(integration.version) if integration.version else "0"
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    await hass.http.async_register_static_paths(
        [StaticPathConfig(URL_BASE, frontend_dir, cache_headers=False)]
    )
    add_extra_js_url(hass, f"{URL_BASE}/{CARD_FILENAME}?v={version}")
    add_extra_js_url(hass, f"{URL_BASE}/{ELAPSED_CARD_FILENAME}?v={version}")
    _LOGGER.debug("Registered PiyoLog Lovelace cards (version %s)", version)
