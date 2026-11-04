"""Serve and register the bundled Lovelace cards.

The card JavaScript lives in ``frontend/`` next to this module. It is
served under ``/piyolog_static/`` and loaded through two independent
paths: ``add_extra_js_url`` (the app shell) and Lovelace resources (the
HACS path). The two paths deliberately use different query strings
(``?e=`` for the shell, ``?v=`` for resources): browsers key their
module map by full URL, and a module whose fetch failed once can stay
failed for the whole page session — with distinct URLs, one path's
failed fetch cannot poison the other, so the cards still load.
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
CARD_FILENAME = "piyolog-timeline-card.js"
ELAPSED_CARD_FILENAME = "piyolog-elapsed-card.js"
CARD_FILENAMES = (CARD_FILENAME, ELAPSED_CARD_FILENAME)


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
    # NOTE: the shell URLs use "?e=" on purpose — they must differ from
    # the Lovelace resource URLs ("?v=") so the two loading paths keep
    # independent module records (see the module docstring).
    add_extra_js_url(hass, f"{URL_BASE}/{CARD_FILENAME}?e={version}")
    add_extra_js_url(hass, f"{URL_BASE}/{ELAPSED_CARD_FILENAME}?e={version}")
    _LOGGER.debug("Registered PiyoLog Lovelace cards (version %s)", version)


async def async_register_lovelace_resources(hass: HomeAssistant) -> None:
    """Also register the cards as Lovelace resources (the HACS loading path).

    Extra JS URLs are baked into the frontend app shell; a client (notably
    the companion app) can keep serving a stale shell across restarts,
    leaving the elements undefined ("Custom element doesn't exist") even
    though the files themselves are served fine. Lovelace resources are
    fetched by the frontend itself on every load, so registering the same
    module URLs there makes the cards load like any HACS card. Only
    storage-backed resources are touched; YAML mode is left alone, and any
    failure just leaves the extra-JS path in place.
    """
    try:
        lovelace_data = hass.data.get("lovelace")
        resources = getattr(lovelace_data, "resources", None)
        if resources is None:
            _LOGGER.debug("Lovelace data unavailable; skipping resource registration")
            return
        from homeassistant.components.lovelace.resources import (
            ResourceStorageCollection,
        )

        if not isinstance(resources, ResourceStorageCollection):
            _LOGGER.debug("Lovelace resources are not storage-backed; skipping")
            return
        if not resources.loaded:
            await resources.async_load()
            resources.loaded = True
        integration = await async_get_integration(hass, DOMAIN)
        version = str(integration.version) if integration.version else "0"
        items = resources.async_items()
        for filename in CARD_FILENAMES:
            path = f"{URL_BASE}/{filename}"
            url = f"{path}?v={version}"
            existing = next(
                (
                    item
                    for item in items
                    if str(item.get("url", "")).split("?")[0] == path
                ),
                None,
            )
            if existing is None:
                await resources.async_create_item({"res_type": "module", "url": url})
                _LOGGER.info("Registered Lovelace resource %s", url)
            elif existing.get("url") != url:
                await resources.async_update_item(existing["id"], {"url": url})
                _LOGGER.info("Updated Lovelace resource %s", url)
        # Drop stale entries for this integration's old file names (e.g.
        # piyolog-card.js, renamed in v1.7.4): a leftover entry makes the
        # frontend fetch a file that no longer exists on every load.
        current_paths = {f"{URL_BASE}/{name}" for name in CARD_FILENAMES}
        for item in items:
            path = str(item.get("url", "")).split("?")[0]
            if path.startswith(f"{URL_BASE}/") and path not in current_paths:
                await resources.async_delete_item(item["id"])
                _LOGGER.info("Removed stale Lovelace resource %s", item.get("url"))
    except Exception:  # noqa: BLE001 - resources are a fallback path
        _LOGGER.warning("Failed to register PiyoLog Lovelace resources", exc_info=True)
