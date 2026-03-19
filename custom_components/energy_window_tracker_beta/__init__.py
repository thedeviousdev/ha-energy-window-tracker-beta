"""Energy Window Tracker Beta integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_MAIN_LOGGER = logging.getLogger("custom_components.energy_window_tracker_beta")

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Energy Window Tracker Beta from a config entry."""
    _MAIN_LOGGER.warning("init: Integration loaded - entry_id=%s", entry.entry_id)
    hass.data.setdefault(DOMAIN, {})
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _MAIN_LOGGER.warning("init: Entry removed/unloading - entry_id=%s", entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    _MAIN_LOGGER.warning(
        "init: async_unload_entry - entry_id=%s ok=%s", entry.entry_id, unload_ok
    )
    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    if entry.state != ConfigEntryState.LOADED:
        return
    await hass.config_entries.async_reload(entry.entry_id)
