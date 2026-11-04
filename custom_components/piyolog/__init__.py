"""The PiyoLog integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MINUTES, DOMAIN
from .coordinator import PiyologCoordinator
from .frontend import async_register_frontend, async_register_lovelace_resources
from .websocket_api import async_register_websocket_commands

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

type PiyologConfigEntry = ConfigEntry[PiyologCoordinator]

_SETUP_FLAG = "global_setup_done"


async def async_setup_entry(hass: HomeAssistant, entry: PiyologConfigEntry) -> bool:
    """Set up PiyoLog from a config entry."""
    await _async_global_setup(hass)
    minutes = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MINUTES)
    coordinator = PiyologCoordinator(
        hass, entry, update_interval=timedelta(minutes=minutes)
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_global_setup(hass: HomeAssistant) -> None:
    """Register WebSocket commands and the Lovelace card (once per run)."""
    data = hass.data.setdefault(DOMAIN, {})
    if data.get(_SETUP_FLAG):
        return
    data[_SETUP_FLAG] = True
    async_register_websocket_commands(hass)
    try:
        await async_register_frontend(hass)
    except Exception:  # noqa: BLE001 - the card is optional, sensors are not
        _LOGGER.exception("Failed to register the PiyoLog Lovelace card")
    await async_register_lovelace_resources(hass)


async def _async_update_listener(hass: HomeAssistant, entry: PiyologConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: PiyologConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


_LOGGER = logging.getLogger(__name__)

__all__ = ["DOMAIN"]
