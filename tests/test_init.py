"""Tests for Energy Window Tracker Beta integration init/unload behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_window_tracker_beta.const import CONF_SOURCES, DOMAIN


@pytest.mark.asyncio
async def test_setup_and_unload_happy_entry(
    hass: HomeAssistant,
    mock_legacy_config_entry: ConfigEntry,
) -> None:
    """[Happy] Setup and unload an entry via core config entries interface."""
    hass.states.async_set("sensor.today_load", "0")
    with patch(
        "custom_components.energy_window_tracker_beta.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(mock_legacy_config_entry.entry_id)
        await hass.async_block_till_done()

    assert DOMAIN in hass.data
    assert mock_legacy_config_entry.entry_id in hass.data[DOMAIN]

    assert await hass.config_entries.async_unload(mock_legacy_config_entry.entry_id)
    assert hass.data[DOMAIN].get(mock_legacy_config_entry.entry_id) is None


@pytest.mark.asyncio
async def test_unload_unhappy_when_not_loaded_succeeds(hass: HomeAssistant) -> None:
    """[Unhappy] Unloading an entry that was never set up does not crash."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Never Setup",
        data={CONF_SOURCES: []},
        options={},
        entry_id="never_setup_id",
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.async_unload(entry.entry_id)
    assert result is True


@pytest.mark.asyncio
async def test_update_options_unhappy_does_not_reload_when_not_loaded(
    hass: HomeAssistant,
    mock_legacy_config_entry: ConfigEntry,
) -> None:
    """[Unhappy] Update listener should not reload when entry isn't loaded."""
    from custom_components.energy_window_tracker_beta import async_update_options

    class _StubEntry:
        entry_id = "stub_entry_id"
        state = ConfigEntryState.SETUP_IN_PROGRESS

    with patch.object(hass.config_entries, "async_reload", new_callable=AsyncMock) as m:
        await async_update_options(hass, _StubEntry())  # type: ignore[arg-type]
    m.assert_not_called()

