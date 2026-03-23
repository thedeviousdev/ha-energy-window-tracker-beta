"""Tests that verify expected logging for the beta integration.

Mirrors the non-beta repo's logging depth using caplog.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.energy_window_tracker_beta.const import (
    CONF_COST_PER_KWH,
    CONF_NAME,
    CONF_SOURCE_ENTITY,
    CONF_SOURCES,
    CONF_WINDOW_END,
    CONF_WINDOW_NAME,
    CONF_WINDOW_START,
    CONF_WINDOWS,
    DOMAIN,
)

COMPONENT_LOGGERS = (
    "custom_components.energy_window_tracker_beta",
    "custom_components.energy_window_tracker_beta.config_flow",
    "custom_components.energy_window_tracker_beta.sensor",
)


def _component_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    """Return log records emitted by our component."""
    return [r for r in caplog.records if r.name.startswith("custom_components.energy_window_tracker_beta")]


def _component_messages(caplog: pytest.LogCaptureFixture) -> str:
    """Return concatenated component log messages."""
    return " ".join(r.message for r in _component_records(caplog))


def _get_sensor_entity(hass: HomeAssistant, entry_id: str):
    """Return first sensor entity object for this config entry."""
    registry = er.async_get(hass)
    entities = [
        e
        for e in registry.entities.get_entries_for_config_entry_id(entry_id)
        if e.domain == SENSOR_DOMAIN
    ]
    if not entities:
        return None
    entity_id = entities[0].entity_id
    comp = hass.data.get("entity_components", {}).get(SENSOR_DOMAIN)
    if comp is None:
        return None
    return comp.get_entity(entity_id)


@pytest.mark.asyncio
async def test_setup_and_unload_logging(
    hass: HomeAssistant,
    mock_legacy_config_entry: ConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """[Happy] Setup and unload log entry_id and results."""
    for logger_name in COMPONENT_LOGGERS:
        caplog.set_level(logging.DEBUG, logger=logger_name)

    hass.states.async_set("sensor.today_load", "0")
    with patch(
        "custom_components.energy_window_tracker_beta.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(mock_legacy_config_entry.entry_id)
        await hass.async_block_till_done()

    messages = _component_messages(caplog)
    assert "init: Integration loaded - entry_id=" in messages
    assert "sensor: async_setup_entry - entry_id=" in messages
    assert "added" in messages

    caplog.clear()
    for logger_name in COMPONENT_LOGGERS:
        caplog.set_level(logging.DEBUG, logger=logger_name)

    assert await hass.config_entries.async_unload(mock_legacy_config_entry.entry_id)
    messages = _component_messages(caplog)
    assert "init: Entry removed/unloading - entry_id=" in messages
    assert "init: async_unload_entry - entry_id=" in messages
    assert "ok=" in messages


@pytest.mark.asyncio
async def test_config_flow_window_first_logging(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """[Happy] Window-first config flow logs user_input show form."""
    for logger_name in COMPONENT_LOGGERS:
        caplog.set_level(logging.DEBUG, logger=logger_name)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "wf_window"

    messages = _component_messages(caplog)
    assert "config flow step user: user_input=" in messages
    assert "show form" in messages


@pytest.mark.asyncio
async def test_options_flow_save_logging(
    hass: HomeAssistant,
    mock_legacy_config_entry: ConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """[Happy] Options flow save logs built options and completes."""
    for logger_name in COMPONENT_LOGGERS:
        caplog.set_level(logging.DEBUG, logger=logger_name)

    hass.states.async_set("sensor.today_load", "0")
    hass.states.async_set("sensor.today_import", "0")

    with patch(
        "custom_components.energy_window_tracker_beta.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ), patch(
        "custom_components.energy_window_tracker_beta.sensor.Store.async_save",
        new_callable=AsyncMock,
    ):
        opts_result = await hass.config_entries.options.async_init(
            mock_legacy_config_entry.entry_id
        )
        assert opts_result["type"] is data_entry_flow.FlowResultType.MENU

        result = await hass.config_entries.options.async_configure(
            opts_result["flow_id"], {"next_step_id": "source_entity"}
        )
        assert result["step_id"] == "source_entity"

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_SOURCE_ENTITY: "sensor.today_import",
                CONF_NAME: "Import",
                "remove_previous_entities": True,
            },
        )

    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    messages = _component_messages(caplog)
    assert "options flow: built options entry_id=" in messages
    assert "source_entity=" in messages


@pytest.mark.asyncio
async def test_sensor_setup_and_load_logging(
    hass: HomeAssistant,
    mock_legacy_config_entry: ConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """[Happy] Sensor setup and load logs appear."""
    for logger_name in COMPONENT_LOGGERS:
        caplog.set_level(logging.DEBUG, logger=logger_name)

    hass.states.async_set("sensor.today_load", "10.5")
    with patch(
        "custom_components.energy_window_tracker_beta.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(mock_legacy_config_entry.entry_id)
        await hass.async_block_till_done()

    messages = _component_messages(caplog)
    assert "sensor: async_setup_entry - adding" in messages
    assert "sensor: load -" in messages


@pytest.mark.asyncio
async def test_sensor_get_source_value_non_numeric_logging(
    hass: HomeAssistant,
    mock_legacy_config_entry: ConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """[Unhappy] Non-numeric source logs warning from get_source_value."""
    for logger_name in COMPONENT_LOGGERS:
        caplog.set_level(logging.DEBUG, logger=logger_name)

    hass.states.async_set("sensor.today_load", "not_a_number")
    with patch(
        "custom_components.energy_window_tracker_beta.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(mock_legacy_config_entry.entry_id)
        await hass.async_block_till_done()

    messages = _component_messages(caplog)
    assert "sensor: get_source_value" in messages
    assert "not numeric" in messages or "state not numeric" in messages


@pytest.mark.asyncio
async def test_sensor_midnight_reset_logging(
    hass: HomeAssistant,
    mock_legacy_config_entry: ConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """[Happy] _handle_midnight logs resetting message."""
    for logger_name in COMPONENT_LOGGERS:
        caplog.set_level(logging.DEBUG, logger=logger_name)

    hass.states.async_set("sensor.today_load", "0")
    with patch(
        "custom_components.energy_window_tracker_beta.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(mock_legacy_config_entry.entry_id)
        await hass.async_block_till_done()

    entity = _get_sensor_entity(hass, mock_legacy_config_entry.entry_id)
    if entity is None or not hasattr(entity, "_data"):
        pytest.skip("could not get sensor entity to call _handle_midnight")

    caplog.clear()
    for logger_name in COMPONENT_LOGGERS:
        caplog.set_level(logging.DEBUG, logger=logger_name)

    entity._data._handle_midnight(dt_util.now())
    messages = _component_messages(caplog)
    assert "_handle_midnight" in messages or "resetting snapshots" in messages


@pytest.mark.asyncio
async def test_sensor_save_logging(
    hass: HomeAssistant,
    mock_legacy_config_entry: ConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """[Happy] window start triggers save() and logs 'sensor: save'."""
    for logger_name in COMPONENT_LOGGERS:
        caplog.set_level(logging.DEBUG, logger=logger_name)

    hass.states.async_set("sensor.today_load", "5.0")
    with patch(
        "custom_components.energy_window_tracker_beta.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ), patch(
        "custom_components.energy_window_tracker_beta.sensor.Store.async_save",
        new_callable=AsyncMock,
    ):
        assert await hass.config_entries.async_setup(mock_legacy_config_entry.entry_id)
        await hass.async_block_till_done()

    entity = _get_sensor_entity(hass, mock_legacy_config_entry.entry_id)
    if entity is None or not hasattr(entity, "_data"):
        pytest.skip("could not get sensor entity to call _handle_window_start")

    # Trigger snapshot save path.
    caplog.clear()
    for logger_name in COMPONENT_LOGGERS:
        caplog.set_level(logging.DEBUG, logger=logger_name)

    window = entity._data._windows[0]
    entity._data._handle_window_start(window, dt_util.now())
    await hass.async_block_till_done()

    messages = _component_messages(caplog)
    assert "sensor: save" in messages or "snapshot_date" in messages


@pytest.mark.asyncio
async def test_sensor_cost_calc_fail_logging(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """[Unhappy] Cost calculation failure in _update_value logs warning."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="CostCalcFail",
        data={
            CONF_SOURCES: [
                {
                    CONF_SOURCE_ENTITY: "sensor.today_load",
                    CONF_NAME: "Energy",
                    CONF_WINDOWS: [
                        {
                            CONF_WINDOW_NAME: "Peak",
                            CONF_WINDOW_START: "09:00",
                            CONF_WINDOW_END: "17:00",
                            CONF_COST_PER_KWH: 0.15,
                        }
                    ],
                }
            ]
        },
        options={},
        entry_id="cost_calc_fail_entry",
    )
    entry.add_to_hass(hass)
    hass.states.async_set("sensor.today_load", "10")

    with patch(
        "custom_components.energy_window_tracker_beta.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entity = _get_sensor_entity(hass, entry.entry_id)
    if entity is None or not hasattr(entity, "_data"):
        pytest.skip("could not get sensor entity to run _update_value")

    def bad_get_window_value(window):
        return ("not_a_float", "during_window")

    entity._data.get_window_value = bad_get_window_value  # type: ignore[method-assign]

    caplog.clear()
    for logger_name in COMPONENT_LOGGERS:
        caplog.set_level(logging.DEBUG, logger=logger_name)

    entity._update_value()
    messages = _component_messages(caplog)
    assert "cost calc failed" in messages

