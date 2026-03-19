"""Tests for Energy Window Tracker Beta window-first setup."""

from __future__ import annotations

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.energy_window_tracker_beta.const import DOMAIN


@pytest.mark.asyncio
async def test_beta_window_first_create_entry_and_sensor(hass: HomeAssistant) -> None:
    """Window-first flow creates entry and corresponding sensor entity."""
    hass.states.async_set("sensor.today_load", "12.0")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "wf_window"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "window_name": "Peak",
            "cost_per_kwh": 0.2,
            "start": "09:00",
            "end": "11:00",
            "add_another": True,
        },
    )
    assert result["step_id"] == "wf_window"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "window_name": "Peak",
            "cost_per_kwh": 0.2,
            "start": "09:00",
            "end": "11:00",
            "start_1": "17:00",
            "end_1": "19:00",
        },
    )
    assert result["step_id"] == "wf_entities"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"entities": ["sensor.today_load"]}
    )
    assert result["type"] is data_entry_flow.FlowResultType.MENU
    assert result["step_id"] == "wf_more"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "wf_done"}
    )
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    windows = result["data"].get("windows") or []
    assert len(windows) == 1
    assert windows[0]["entities"] == ["sensor.today_load"]
    assert len(windows[0]["ranges"]) == 2

    entry_id = result["result"].entry_id
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    entities = [
        e
        for e in registry.entities.get_entries_for_config_entry_id(entry_id)
        if e.domain == SENSOR_DOMAIN
    ]
    assert len(entities) == 1

