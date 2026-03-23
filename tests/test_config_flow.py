"""Config flow tests for Energy Window Tracker Beta."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

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


@pytest.mark.asyncio
async def test_user_flow_starts_on_window_setup_step(hass: HomeAssistant) -> None:
    """[Happy] User flow starts directly on window setup."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "window_setup"


@pytest.mark.asyncio
async def test_window_setup_overlap_ranges_rejected(hass: HomeAssistant) -> None:
    """[Unhappy] Overlapping ranges show base error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "window_name": "Peak",
            "cost_per_kwh": 0.2,
            "start_1": "09:00",
            "end_1": "12:00",
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
            "end_1": "12:00",
            "start_2": "11:00",
            "end_2": "14:00",
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result.get("errors", {}).get("base") == "range_start_before_previous_end"


@pytest.mark.asyncio
async def test_window_entities_requires_at_least_one_entity(hass: HomeAssistant) -> None:
    """[Unhappy] window_entities validates empty selection."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "window_name": "Peak",
            "cost_per_kwh": 0.2,
            "start_1": "09:00",
            "end_1": "12:00",
        },
    )
    assert result["step_id"] == "window_entities"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"entities": []},
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "window_entities"
    assert result.get("errors", {}).get("base") == "source_entity_required"


@pytest.mark.asyncio
async def test_options_flow_opens_from_window_setup_entry(
    hass: HomeAssistant, mock_window_setup_entry
) -> None:
    """[Happy] Options flow loads for a windows-based-created entry."""
    result = await hass.config_entries.options.async_init(mock_window_setup_entry.entry_id)
    assert result["type"] is data_entry_flow.FlowResultType.MENU
    assert result["step_id"] == "init"


@pytest.mark.asyncio
async def test_options_source_entity_unchanged_with_remove_previous_rejected(
    hass: HomeAssistant, mock_legacy_config_entry
) -> None:
    """[Unhappy] Selecting same source + remove_previous_entities is rejected."""
    result = await hass.config_entries.options.async_init(mock_legacy_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "source_entity"}
    )
    assert result["step_id"] == "source_entity"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_SOURCE_ENTITY: "sensor.today_load",
            CONF_NAME: "Energy",
            "remove_previous_entities": True,
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "source_entity"
    assert result.get("errors", {}).get("base") == "remove_previous_but_source_unchanged"


@pytest.mark.asyncio
async def test_options_source_entity_already_in_use_rejected(
    hass: HomeAssistant, mock_legacy_config_entry
) -> None:
    """[Unhappy] Updating source entity to one used by another entry is rejected."""
    other = MockConfigEntry(
        domain=DOMAIN,
        title="Other",
        data={
            CONF_SOURCES: [
                {
                    CONF_SOURCE_ENTITY: "sensor.today_import",
                    CONF_NAME: "Other",
                    CONF_WINDOWS: [
                        {
                            CONF_WINDOW_NAME: "Other Peak",
                            CONF_WINDOW_START: "10:00",
                            CONF_WINDOW_END: "11:00",
                        }
                    ],
                }
            ]
        },
        options={},
        entry_id="other_entry",
    )
    other.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_legacy_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "source_entity"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_SOURCE_ENTITY: "sensor.today_import",
            CONF_NAME: "New Name",
            "remove_previous_entities": False,
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "source_entity"
    assert result.get("errors", {}).get("base") == "source_already_in_use"


@pytest.mark.asyncio
async def test_options_add_window_happy_path_persists(
    hass: HomeAssistant, mock_legacy_config_entry
) -> None:
    """[Happy] Options add_window persists new range rows."""
    with patch.object(hass.config_entries, "async_reload", new_callable=AsyncMock):
        result = await hass.config_entries.options.async_init(mock_legacy_config_entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "add_window"}
        )
        assert result["step_id"] == "add_window"

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "window_name": "Off-Peak",
                CONF_COST_PER_KWH: 0.1,
                "start_1": "00:00",
                "end_1": "07:00",
            },
        )
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    entry = hass.config_entries.async_get_entry(mock_legacy_config_entry.entry_id)
    assert entry is not None
    source_rows = (entry.options.get(CONF_SOURCES) or entry.data.get(CONF_SOURCES) or [])[0]
    windows = source_rows[CONF_WINDOWS]
    assert any(
        w.get(CONF_WINDOW_NAME) == "Off-Peak"
        and w.get(CONF_WINDOW_START) == "00:00"
        and w.get(CONF_WINDOW_END) == "07:00"
        for w in windows
    )
