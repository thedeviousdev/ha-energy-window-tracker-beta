"""Tests for Energy Window Tracker Beta window setup."""

from __future__ import annotations

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.energy_window_tracker_beta.const import DOMAIN


@pytest.mark.asyncio
async def test_window_setup_happy_create_entry_and_sensor(hass: HomeAssistant) -> None:
    """[Happy] Window setup flow creates entry and corresponding sensor entity."""
    hass.states.async_set("sensor.today_load", "12.0")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "window_setup"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "window_name": "Peak",
            "cost_per_kwh": 0.2,
            "start_1": "09:00",
            "end_1": "11:00",
            "add_another": True,
        },
    )
    assert result["step_id"] == "window_setup"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "window_name": "Peak",
            "cost_per_kwh": 0.2,
            "start_1": "09:00",
            "end_1": "11:00",
            "start_2": "17:00",
            "end_2": "19:00",
        },
    )
    assert result["step_id"] == "window_entities"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"entities": ["sensor.today_load"]}
    )
    await hass.async_block_till_done()
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "window_entities_confirm"

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    entry = entries[0]
    entry_id = entry.entry_id
    assert entry.title == "Peak"

    windows = entry.data.get("windows") or []
    assert len(windows) == 1
    assert windows[0]["name"] == "Peak"
    assert windows[0]["entities"] == ["sensor.today_load"]
    assert len(windows[0]["ranges"]) == 2

    registry = er.async_get(hass)
    entities = [
        e
        for e in registry.entities.get_entries_for_config_entry_id(entry_id)
        if e.domain == SENSOR_DOMAIN
    ]
    assert len(entities) == 1

    # Clicking "Edit" should take the user back to the window_setup form.
    edit_result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert edit_result["type"] is data_entry_flow.FlowResultType.FORM
    assert edit_result["step_id"] == "window_setup"

    # Options flow should also load for windows-based entries.
    # Historically this integration only supported the legacy CONF_SOURCES format in options.
    options_result = await hass.config_entries.options.async_init(entry_id)
    assert options_result["type"] is data_entry_flow.FlowResultType.MENU
    assert options_result["step_id"] == "init"


@pytest.mark.asyncio
async def test_window_setup_happy_clear_extra_placeholder_range_slot_deletes_it(
    hass: HomeAssistant,
) -> None:
    """[Happy] Clearing an extra range slot should not persist a placeholder range."""
    hass.states.async_set("sensor.today_load", "12.0")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "window_setup"

    # Add another range slot.
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "window_name": "Peak",
            "cost_per_kwh": 0.2,
            "start_1": "09:00:00",
            "end_1": "11:00:00",
            "add_another": True,
        },
    )
    assert result["step_id"] == "window_setup"

    # Clear the extra placeholder range slot by submitting empty start/end.
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "window_name": "Peak",
            "cost_per_kwh": 0.2,
            "start_1": "09:00:00",
            "end_1": "11:00:00",
            "start_2": "",
            "end_2": "",
        },
    )
    assert result["step_id"] == "window_entities"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"entities": ["sensor.today_load"]}
    )
    await hass.async_block_till_done()
    assert result["step_id"] == "window_entities_confirm"

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    windows = entries[0].data.get("windows") or []
    assert len(windows) == 1
    assert windows[0]["name"] == "Peak"
    assert windows[0]["entities"] == ["sensor.today_load"]
    assert len(windows[0]["ranges"]) == 1
    assert windows[0]["ranges"][0]["start"] == "09:00:00"
    assert windows[0]["ranges"][0]["end"] == "11:00:00"

