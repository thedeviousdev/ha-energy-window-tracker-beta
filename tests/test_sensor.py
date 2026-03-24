"""Sensor tests for Energy Window Tracker Beta."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_window_tracker_beta.const import (
    CONF_COST_PER_KWH,
    CONF_ENTITIES,
    CONF_RANGES,
    CONF_SOURCE_ENTITY,
    CONF_WINDOW_END,
    CONF_WINDOW_NAME,
    CONF_WINDOW_START,
    CONF_WINDOWS,
    DOMAIN,
)
from custom_components.energy_window_tracker_beta.sensor import (
    _get_sources_from_config,
    _parse_windows,
)


def _get_tracker_sensors(hass: HomeAssistant, entry_id: str) -> list:
    """Return registry entities belonging to this integration entry."""
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    return [
        e
        for e in registry.entities.get_entries_for_config_entry_id(entry_id)
        if e.domain == SENSOR_DOMAIN
    ]


def test_get_sources_from_config_happy_windows_based_conversion() -> None:
    """[Happy] Windows-based data converts into source rows grouped by entity."""
    config = {
        CONF_WINDOWS: [
            {
                CONF_WINDOW_NAME: "Peak",
                CONF_COST_PER_KWH: 0.2,
                CONF_ENTITIES: ["sensor.a", "sensor.b"],
                CONF_RANGES: [
                    {CONF_WINDOW_START: "09:00", CONF_WINDOW_END: "11:00"},
                    {CONF_WINDOW_START: "17:00", CONF_WINDOW_END: "19:00"},
                ],
            }
        ]
    }
    out = _get_sources_from_config(config)
    assert len(out) == 2
    assert {row[CONF_SOURCE_ENTITY] for row in out} == {"sensor.a", "sensor.b"}
    for row in out:
        assert len(row[CONF_WINDOWS]) == 2
        assert row[CONF_WINDOWS][0][CONF_WINDOW_NAME] == "Peak"
        assert row[CONF_WINDOWS][0][CONF_WINDOW_START] == "09:00:00"
        assert row[CONF_WINDOWS][0][CONF_WINDOW_END] == "11:00:00"


def test_get_sources_from_config_unhappy_invalid_ranges_filtered() -> None:
    """[Unhappy] Invalid ranges are dropped during windows-based conversion."""
    config = {
        CONF_WINDOWS: [
            {
                CONF_WINDOW_NAME: "Bad",
                CONF_ENTITIES: ["sensor.a"],
                CONF_RANGES: [
                    {CONF_WINDOW_START: "10:00", CONF_WINDOW_END: "09:00"},
                    {CONF_WINDOW_START: "11:00", CONF_WINDOW_END: ""},
                ],
            }
        ]
    }
    out = _get_sources_from_config(config)
    assert out == []


def test_parse_windows_unhappy_invalid_time_uses_fallback_and_warning() -> None:
    """[Unhappy] Invalid times in windows are handled safely."""
    windows, warnings = _parse_windows(
        {
            CONF_WINDOWS: [
                {
                    CONF_WINDOW_NAME: "Peak",
                    CONF_WINDOW_START: "25:00",
                    CONF_WINDOW_END: "99:00",
                }
            ]
        }
    )
    assert len(windows) == 1
    assert (
        windows[0].start_h == 11 and windows[0].start_m == 0 and windows[0].start_s == 0
    )
    assert windows[0].end_h == 14 and windows[0].end_m == 0 and windows[0].end_s == 0
    assert "Peak" in warnings
    assert len(warnings["Peak"]) >= 1


def test_parse_windows_happy_supports_seconds_precision() -> None:
    """[Happy] Window parser keeps seconds precision for start/end."""
    windows, warnings = _parse_windows(
        {
            CONF_WINDOWS: [
                {
                    CONF_WINDOW_NAME: "Peak",
                    CONF_WINDOW_START: "09:00:15",
                    CONF_WINDOW_END: "17:30:45",
                }
            ]
        }
    )
    assert not warnings
    assert len(windows) == 1
    assert (windows[0].start_h, windows[0].start_m, windows[0].start_s) == (9, 0, 15)
    assert (windows[0].end_h, windows[0].end_m, windows[0].end_s) == (17, 30, 45)


@pytest.mark.asyncio
async def test_sensor_setup_happy_windows_based_entry_creates_sensor(
    hass: HomeAssistant, mock_window_setup_entry
) -> None:
    """[Happy] Sensor setup works with windows-based entry data."""
    hass.states.async_set("sensor.today_load", "3.2")
    with patch(
        "custom_components.energy_window_tracker_beta.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(mock_window_setup_entry.entry_id)
        await hass.async_block_till_done()
    entities = _get_tracker_sensors(hass, mock_window_setup_entry.entry_id)
    assert len(entities) == 1
    state = hass.states.get(entities[0].entity_id)
    assert state is not None
    assert state.attributes.get("source_entity") == "sensor.today_load"
    assert isinstance(state.attributes.get("ranges"), list)


@pytest.mark.asyncio
async def test_sensor_setup_unhappy_source_unavailable(
    hass: HomeAssistant, mock_window_setup_entry
) -> None:
    """[Unhappy] Sensor still sets up and reports unavailable source state."""
    hass.states.async_set("sensor.today_load", "unavailable")
    with patch(
        "custom_components.energy_window_tracker_beta.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(mock_window_setup_entry.entry_id)
        await hass.async_block_till_done()
    entities = _get_tracker_sensors(hass, mock_window_setup_entry.entry_id)
    assert len(entities) == 1
    state = hass.states.get(entities[0].entity_id)
    assert state is not None
    assert state.state in ("unavailable", "unknown")


@pytest.mark.asyncio
async def test_sensor_setup_happy_windows_entry_multiple_windows(
    hass: HomeAssistant,
) -> None:
    """[Happy] Windows-based config with two named windows creates two sensors."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Two Windows",
        data={
            CONF_WINDOWS: [
                {
                    CONF_WINDOW_NAME: "Peak",
                    CONF_COST_PER_KWH: 0.2,
                    CONF_ENTITIES: ["sensor.today_load"],
                    CONF_RANGES: [
                        {
                            CONF_WINDOW_START: "09:00",
                            CONF_WINDOW_END: "12:00",
                        }
                    ],
                },
                {
                    CONF_WINDOW_NAME: "Off-Peak",
                    CONF_COST_PER_KWH: 0.1,
                    CONF_ENTITIES: ["sensor.today_load"],
                    CONF_RANGES: [
                        {
                            CONF_WINDOW_START: "12:00",
                            CONF_WINDOW_END: "17:00",
                        }
                    ],
                },
            ]
        },
        options={},
        entry_id="two_windows_entry",
    )
    entry.add_to_hass(hass)
    hass.states.async_set("sensor.today_load", "1.0")

    with patch(
        "custom_components.energy_window_tracker_beta.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    entities = _get_tracker_sensors(hass, entry.entry_id)
    assert len(entities) == 2


@pytest.mark.asyncio
async def test_sensor_setup_happy_friendly_name_uses_window_and_source_entity(
    hass: HomeAssistant,
) -> None:
    """[Happy] Friendly name is '<window> - <source friendly name>'."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Friendly Names",
        data={
            CONF_WINDOWS: [
                {
                    CONF_WINDOW_NAME: "ZEROHERO",
                    CONF_COST_PER_KWH: 0.2,
                    CONF_ENTITIES: ["sensor.today_load", "sensor.today_import"],
                    CONF_RANGES: [
                        {CONF_WINDOW_START: "09:00:00", CONF_WINDOW_END: "11:00:00"},
                        {CONF_WINDOW_START: "17:00:00", CONF_WINDOW_END: "19:00:00"},
                    ],
                }
            ]
        },
        options={},
        entry_id="friendly_name_multi_entity_multi_range",
    )
    entry.add_to_hass(hass)
    hass.states.async_set(
        "sensor.today_load",
        "1.0",
        {"friendly_name": "Today Sensor Load"},
    )
    hass.states.async_set(
        "sensor.today_import",
        "2.0",
        {"friendly_name": "Today Sensor Import"},
    )

    with patch(
        "custom_components.energy_window_tracker_beta.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entities = _get_tracker_sensors(hass, entry.entry_id)
    assert len(entities) == 2

    state_names = {
        hass.states.get(entity.entity_id).attributes.get("friendly_name")
        for entity in entities
        if hass.states.get(entity.entity_id) is not None
    }
    assert "ZEROHERO - Today Sensor Load" in state_names
    assert "ZEROHERO - Today Sensor Import" in state_names

    # unique_id should not be directly mapped to window name text.
    for entity in entities:
        assert "zerohero" not in entity.unique_id.lower()
