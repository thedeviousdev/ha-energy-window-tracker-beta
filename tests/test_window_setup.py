"""Tests for Energy Window Tracker Beta window setup."""

from __future__ import annotations

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.energy_window_tracker_beta.const import (
    CONF_ENTITY_ID,
    CONF_SOURCE_SLOT_ID,
    DOMAIN,
)


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
            "import_rate_per_kwh": 0.2,
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
            "import_rate_per_kwh": 0.2,
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
    ent0 = windows[0]["entities"][0]
    assert isinstance(ent0, dict)
    assert ent0[CONF_ENTITY_ID] == "sensor.today_load"
    assert len(ent0[CONF_SOURCE_SLOT_ID]) >= 32
    assert len(windows[0]["ranges"]) == 2

    registry = er.async_get(hass)
    entities = [
        e
        for e in registry.entities.get_entries_for_config_entry_id(entry_id)
        if e.domain == SENSOR_DOMAIN
    ]
    assert len(entities) == 1

    # Clicking "Finish" should return to the configure menu.
    finish_result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert finish_result["type"] is data_entry_flow.FlowResultType.MENU
    assert finish_result["step_id"] == "configure_menu"
    assert finish_result.get("description")
    menu_options = finish_result.get("menu_options") or {}
    assert "done" not in menu_options

    # Options flow should also load for windows-based entries.
    options_result = await hass.config_entries.options.async_init(entry_id)
    assert options_result["type"] is data_entry_flow.FlowResultType.MENU
    assert options_result["step_id"] == "init"
    assert options_result.get("description")


@pytest.mark.asyncio
async def test_window_setup_happy_neutralize_extra_placeholder_range_slot_deletes_it(
    hass: HomeAssistant,
) -> None:
    """[Happy] Making an extra range slot invalid (start>=end) should not persist it."""
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
            "import_rate_per_kwh": 0.2,
            "start_1": "09:00:00",
            "end_1": "11:00:00",
            "add_another": True,
        },
    )
    assert result["step_id"] == "window_setup"

    # Neutralize the extra placeholder range slot by submitting start>=end.
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "window_name": "Peak",
            "import_rate_per_kwh": 0.2,
            "start_1": "09:00:00",
            "end_1": "11:00:00",
            "start_2": "17:00:00",
            "end_2": "17:00:00",
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
    ent0 = windows[0]["entities"][0]
    assert isinstance(ent0, dict)
    assert ent0[CONF_ENTITY_ID] == "sensor.today_load"
    assert len(ent0[CONF_SOURCE_SLOT_ID]) >= 32
    assert len(windows[0]["ranges"]) == 1
    assert windows[0]["ranges"][0]["start"] == "09:00:00"
    assert windows[0]["ranges"][0]["end"] == "11:00:00"
