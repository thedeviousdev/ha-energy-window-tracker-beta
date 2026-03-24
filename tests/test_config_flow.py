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
async def test_user_flow_happy_starts_on_window_setup_step(hass: HomeAssistant) -> None:
    """[Happy] User flow starts directly on window setup."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "window_setup"


@pytest.mark.asyncio
async def test_window_setup_unhappy_overlap_ranges_rejected(
    hass: HomeAssistant,
) -> None:
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
async def test_window_entities_unhappy_requires_at_least_one_entity(
    hass: HomeAssistant,
) -> None:
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
async def test_options_flow_happy_opens_from_window_setup_entry(
    hass: HomeAssistant, mock_window_setup_entry
) -> None:
    """[Happy] Options flow loads for a windows-based-created entry."""
    result = await hass.config_entries.options.async_init(
        mock_window_setup_entry.entry_id
    )
    assert result["type"] is data_entry_flow.FlowResultType.MENU
    assert result["step_id"] == "init"
    assert result.get("title") == "Peak"


@pytest.mark.asyncio
async def test_options_source_entity_unhappy_unchanged_with_remove_previous_rejected(
    hass: HomeAssistant, mock_legacy_config_entry
) -> None:
    """[Unhappy] Selecting same source + remove_previous_entities is rejected."""
    result = await hass.config_entries.options.async_init(
        mock_legacy_config_entry.entry_id
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "source_entity"}
    )
    assert result["step_id"] == "source_entity"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_SOURCE_ENTITY: "sensor.today_load",
            "remove_previous_entities": True,
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "source_entity"
    assert (
        result.get("errors", {}).get("base") == "remove_previous_but_source_unchanged"
    )


@pytest.mark.asyncio
async def test_options_source_entity_unhappy_already_in_use_rejected(
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

    result = await hass.config_entries.options.async_init(
        mock_legacy_config_entry.entry_id
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "source_entity"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_SOURCE_ENTITY: "sensor.today_import",
            "remove_previous_entities": False,
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "source_entity"
    assert result.get("errors", {}).get("base") == "source_already_in_use"


@pytest.mark.asyncio
async def test_options_source_entity_happy_multiple_sources_prompts_selection_first(
    hass: HomeAssistant,
) -> None:
    """[Happy] Multi-source entries show source selection before source editor form."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Energy Window Tracker (Beta)",
        data={
            CONF_WINDOWS: [
                {
                    CONF_WINDOW_NAME: "Peak",
                    CONF_COST_PER_KWH: 0.2,
                    "entities": ["sensor.today_load", "sensor.today_import"],
                    "ranges": [
                        {CONF_WINDOW_START: "09:00:00", CONF_WINDOW_END: "11:00:00"}
                    ],
                }
            ]
        },
        options={},
        entry_id="multi_source_manage",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "source_entity"}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "select_source_entity"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"source_entity_to_manage": "sensor.today_import"}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "source_entity"


@pytest.mark.asyncio
async def test_options_add_window_happy_path_persists(
    hass: HomeAssistant, mock_legacy_config_entry
) -> None:
    """[Happy] Options add_window persists new range rows."""
    with patch.object(hass.config_entries, "async_reload", new_callable=AsyncMock):
        result = await hass.config_entries.options.async_init(
            mock_legacy_config_entry.entry_id
        )
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
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "options_saved"
    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    assert result["type"] is data_entry_flow.FlowResultType.MENU
    assert result["step_id"] == "init"
    entry = hass.config_entries.async_get_entry(mock_legacy_config_entry.entry_id)
    assert entry is not None
    source_rows = (
        entry.options.get(CONF_SOURCES) or entry.data.get(CONF_SOURCES) or []
    )[0]
    windows = source_rows[CONF_WINDOWS]
    assert any(
        w.get(CONF_WINDOW_NAME) == "Off-Peak"
        and w.get(CONF_WINDOW_START) == "00:00:00"
        and w.get(CONF_WINDOW_END) == "07:00:00"
        for w in windows
    )


@pytest.mark.asyncio
async def test_options_add_window_unhappy_duplicate_name_rejected(
    hass: HomeAssistant, mock_legacy_config_entry
) -> None:
    """[Unhappy] Add window rejects duplicate window names."""
    result = await hass.config_entries.options.async_init(mock_legacy_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_window"}
    )
    assert result["step_id"] == "add_window"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "window_name": "Peak",
            CONF_COST_PER_KWH: 0.1,
            "start_1": "00:00",
            "end_1": "07:00",
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "add_window"
    assert result.get("errors", {}).get("base") == "duplicate_window_name"


@pytest.mark.asyncio
async def test_options_edit_window_happy_preserves_other_sources(
    hass: HomeAssistant,
) -> None:
    """[Happy] Editing a window updates only selected source; others are preserved."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Energy Window Tracker (Beta)",
        data={
            CONF_SOURCES: [
                {
                    CONF_SOURCE_ENTITY: "sensor.today_load",
                    CONF_NAME: "Load",
                    CONF_WINDOWS: [
                        {
                            CONF_WINDOW_NAME: "Peak",
                            CONF_WINDOW_START: "09:00",
                            CONF_WINDOW_END: "11:00",
                            CONF_COST_PER_KWH: 0.2,
                        }
                    ],
                },
                {
                    CONF_SOURCE_ENTITY: "sensor.today_import",
                    CONF_NAME: "Import",
                    CONF_WINDOWS: [
                        {
                            CONF_WINDOW_NAME: "Import Peak",
                            CONF_WINDOW_START: "12:00",
                            CONF_WINDOW_END: "14:00",
                            CONF_COST_PER_KWH: 0.3,
                        }
                    ],
                },
            ]
        },
        options={},
        entry_id="legacy_multi_source_edit",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "list_windows"}
    )
    assert result["step_id"] == "edit_window"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "window_name": "Peak",
            CONF_COST_PER_KWH: 0.25,
            "start_1": "09:00",
            "end_1": "12:00",
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "options_saved"

    saved_entry = hass.config_entries.async_get_entry(entry.entry_id)
    assert saved_entry is not None
    sources = (
        saved_entry.options.get(CONF_SOURCES)
        or saved_entry.data.get(CONF_SOURCES)
        or []
    )
    assert len(sources) == 2
    by_entity = {
        src.get(CONF_SOURCE_ENTITY): src
        for src in sources
        if isinstance(src, dict) and src.get(CONF_SOURCE_ENTITY)
    }
    assert "sensor.today_load" in by_entity
    assert "sensor.today_import" in by_entity
    assert (
        by_entity["sensor.today_load"][CONF_WINDOWS][0][CONF_WINDOW_END] == "12:00:00"
    )
    assert (
        by_entity["sensor.today_import"][CONF_WINDOWS][0][CONF_WINDOW_NAME]
        == "Import Peak"
    )


@pytest.mark.asyncio
async def test_options_edit_window_unhappy_rename_to_existing_name_rejected(
    hass: HomeAssistant,
) -> None:
    """[Unhappy] Renaming a window to an existing window name is rejected."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Energy Window Tracker (Beta)",
        data={
            CONF_SOURCES: [
                {
                    CONF_SOURCE_ENTITY: "sensor.today_load",
                    CONF_NAME: "Load",
                    CONF_WINDOWS: [
                        {
                            CONF_WINDOW_NAME: "Peak",
                            CONF_WINDOW_START: "09:00",
                            CONF_WINDOW_END: "11:00",
                            CONF_COST_PER_KWH: 0.2,
                        },
                        {
                            CONF_WINDOW_NAME: "Off-Peak",
                            CONF_WINDOW_START: "12:00",
                            CONF_WINDOW_END: "14:00",
                            CONF_COST_PER_KWH: 0.1,
                        },
                    ],
                }
            ]
        },
        options={},
        entry_id="legacy_duplicate_rename",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "list_windows"}
    )
    assert result["step_id"] == "edit_window"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "window_name": "Off-Peak",
            CONF_COST_PER_KWH: 0.2,
            "start_1": "09:00",
            "end_1": "11:00",
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "edit_window"
    assert result.get("errors", {}).get("base") == "duplicate_window_name"


@pytest.mark.asyncio
async def test_options_source_entity_happy_update_preserves_other_sources(
    hass: HomeAssistant,
) -> None:
    """[Happy] Updating one source entity does not drop other source rows."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Energy Window Tracker (Beta)",
        data={
            CONF_SOURCES: [
                {
                    CONF_SOURCE_ENTITY: "sensor.today_load",
                    CONF_NAME: "Load",
                    CONF_WINDOWS: [
                        {
                            CONF_WINDOW_NAME: "Peak",
                            CONF_WINDOW_START: "09:00",
                            CONF_WINDOW_END: "11:00",
                            CONF_COST_PER_KWH: 0.2,
                        }
                    ],
                },
                {
                    CONF_SOURCE_ENTITY: "sensor.today_import",
                    CONF_NAME: "Import",
                    CONF_WINDOWS: [
                        {
                            CONF_WINDOW_NAME: "Import Peak",
                            CONF_WINDOW_START: "12:00",
                            CONF_WINDOW_END: "14:00",
                            CONF_COST_PER_KWH: 0.3,
                        }
                    ],
                },
            ]
        },
        options={},
        entry_id="legacy_multi_source_update",
    )
    entry.add_to_hass(hass)
    hass.states.async_set("sensor.today_export", "1.0")

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "source_entity"}
    )
    assert result["step_id"] == "select_source_entity"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"source_entity_to_manage": "sensor.today_load"}
    )
    assert result["step_id"] == "source_entity"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_SOURCE_ENTITY: "sensor.today_export",
            "remove_previous_entities": False,
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "options_saved"

    saved_entry = hass.config_entries.async_get_entry(entry.entry_id)
    assert saved_entry is not None
    sources = (
        saved_entry.options.get(CONF_SOURCES)
        or saved_entry.data.get(CONF_SOURCES)
        or []
    )
    assert len(sources) == 2
    entities = {
        src.get(CONF_SOURCE_ENTITY)
        for src in sources
        if isinstance(src, dict) and src.get(CONF_SOURCE_ENTITY)
    }
    assert "sensor.today_export" in entities
    assert "sensor.today_import" in entities


@pytest.mark.asyncio
async def test_options_edit_window_happy_windows_based_preserves_all_entities(
    hass: HomeAssistant,
) -> None:
    """[Happy] Editing a windows-based entry does not drop sibling source entities."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Peak",
        data={
            CONF_WINDOWS: [
                {
                    CONF_WINDOW_NAME: "Peak",
                    CONF_COST_PER_KWH: 0.2,
                    "entities": ["sensor.today_load", "sensor.today_import"],
                    "ranges": [
                        {CONF_WINDOW_START: "09:00:00", CONF_WINDOW_END: "11:00:00"}
                    ],
                }
            ]
        },
        options={},
        entry_id="windows_based_multi_entity_edit",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "list_windows"}
    )
    assert result["step_id"] == "edit_window"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "window_name": "Peak",
            CONF_COST_PER_KWH: 0.25,
            "start_1": "09:00:00",
            "end_1": "12:00:00",
        },
    )
    assert result["step_id"] == "options_saved"

    saved_entry = hass.config_entries.async_get_entry(entry.entry_id)
    assert saved_entry is not None
    sources = (
        saved_entry.options.get(CONF_SOURCES) or saved_entry.data.get(CONF_SOURCES) or []
    )
    entities = {
        src.get(CONF_SOURCE_ENTITY)
        for src in sources
        if isinstance(src, dict) and src.get(CONF_SOURCE_ENTITY)
    }
    assert entities == {"sensor.today_load", "sensor.today_import"}


@pytest.mark.asyncio
async def test_window_entities_happy_creates_one_window_per_selected_entity(
    hass: HomeAssistant,
) -> None:
    """[Happy] Window setup creates one configured-name window per selected entity."""
    hass.states.async_set("sensor.today_load", "12.0")
    hass.states.async_set("sensor.today_import", "7.0")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "window_name": "Peak",
            "cost_per_kwh": 0.2,
            "start_1": "09:00",
            "end_1": "11:00",
        },
    )
    assert result["step_id"] == "window_entities"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"entities": ["sensor.today_load", "sensor.today_import"]},
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "window_entities_confirm"

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    windows = entries[0].data.get(CONF_WINDOWS) or []
    assert len(windows) == 2
    entity_sets = [w.get("entities") for w in windows]
    assert ["sensor.today_load"] in entity_sets
    assert ["sensor.today_import"] in entity_sets
    names = {w.get(CONF_WINDOW_NAME) for w in windows}
    assert names == {"Peak"}


@pytest.mark.asyncio
async def test_options_edit_window_happy_delete_middle_range_preserves_flow(
    hass: HomeAssistant,
) -> None:
    """[Happy] Deleting an in-between range keeps edit flow stable and saves."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Energy Window Tracker (Beta)",
        data={
            CONF_SOURCES: [
                {
                    CONF_SOURCE_ENTITY: "sensor.today_load",
                    CONF_NAME: "Load",
                    CONF_WINDOWS: [
                        {
                            CONF_WINDOW_NAME: "Peak",
                            CONF_WINDOW_START: "09:00",
                            CONF_WINDOW_END: "10:00",
                            CONF_COST_PER_KWH: 0.2,
                        },
                        {
                            CONF_WINDOW_NAME: "Peak",
                            CONF_WINDOW_START: "11:00",
                            CONF_WINDOW_END: "12:00",
                            CONF_COST_PER_KWH: 0.2,
                        },
                        {
                            CONF_WINDOW_NAME: "Peak",
                            CONF_WINDOW_START: "13:00",
                            CONF_WINDOW_END: "14:00",
                            CONF_COST_PER_KWH: 0.2,
                        },
                    ],
                }
            ]
        },
        options={},
        entry_id="legacy_middle_delete",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "list_windows"}
    )
    assert result["step_id"] == "edit_window"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "window_name": "Peak",
            CONF_COST_PER_KWH: 0.2,
            "start_1": "09:00",
            "end_1": "10:00",
            "start_2": "11:00",
            "end_2": "11:00",
            "start_3": "13:00",
            "end_3": "14:00",
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "options_saved"

    saved_entry = hass.config_entries.async_get_entry(entry.entry_id)
    assert saved_entry is not None
    sources = (
        saved_entry.options.get(CONF_SOURCES)
        or saved_entry.data.get(CONF_SOURCES)
        or []
    )
    assert len(sources) == 1
    windows = sources[0][CONF_WINDOWS]
    assert len(windows) == 2
    assert windows[0][CONF_WINDOW_START] == "09:00:00"
    assert windows[0][CONF_WINDOW_END] == "10:00:00"
    assert windows[1][CONF_WINDOW_START] == "13:00:00"
    assert windows[1][CONF_WINDOW_END] == "14:00:00"


@pytest.mark.asyncio
async def test_options_edit_window_unhappy_delete_all_ranges_requires_confirmation(
    hass: HomeAssistant,
) -> None:
    """[Unhappy] Clearing all ranges first routes to delete confirmation step."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Energy Window Tracker (Beta)",
        data={
            CONF_SOURCES: [
                {
                    CONF_SOURCE_ENTITY: "sensor.today_load",
                    CONF_NAME: "Load",
                    CONF_WINDOWS: [
                        {
                            CONF_WINDOW_NAME: "Peak",
                            CONF_WINDOW_START: "09:00",
                            CONF_WINDOW_END: "10:00",
                            CONF_COST_PER_KWH: 0.2,
                        }
                    ],
                }
            ]
        },
        options={},
        entry_id="legacy_confirm_delete",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "list_windows"}
    )
    assert result["step_id"] == "edit_window"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "window_name": "Peak",
            CONF_COST_PER_KWH: 0.2,
            "start_1": "09:00",
            "end_1": "09:00",
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "confirm_delete_window"


@pytest.mark.asyncio
async def test_options_edit_window_happy_delete_all_ranges_after_confirmation(
    hass: HomeAssistant,
) -> None:
    """[Happy] Confirming delete after clearing all ranges removes the window."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Energy Window Tracker (Beta)",
        data={
            CONF_SOURCES: [
                {
                    CONF_SOURCE_ENTITY: "sensor.today_load",
                    CONF_NAME: "Load",
                    CONF_WINDOWS: [
                        {
                            CONF_WINDOW_NAME: "Peak",
                            CONF_WINDOW_START: "09:00",
                            CONF_WINDOW_END: "10:00",
                            CONF_COST_PER_KWH: 0.2,
                        }
                    ],
                }
            ]
        },
        options={},
        entry_id="legacy_confirm_delete_apply",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "list_windows"}
    )
    assert result["step_id"] == "edit_window"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "window_name": "Peak",
            CONF_COST_PER_KWH: 0.2,
            "start_1": "09:00",
            "end_1": "09:00",
        },
    )
    assert result["step_id"] == "confirm_delete_window"

    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "options_saved"

    saved_entry = hass.config_entries.async_get_entry(entry.entry_id)
    assert saved_entry is not None
    sources = (
        saved_entry.options.get(CONF_SOURCES)
        or saved_entry.data.get(CONF_SOURCES)
        or []
    )
    assert len(sources) == 1
    assert sources[0][CONF_WINDOWS] == []


@pytest.mark.asyncio
async def test_options_edit_window_happy_renaming_updates_entry_title(
    hass: HomeAssistant,
) -> None:
    """[Happy] Renaming the first window updates the config entry title."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Energy Window Tracker (Beta)",
        data={
            CONF_SOURCES: [
                {
                    CONF_SOURCE_ENTITY: "sensor.today_load",
                    CONF_NAME: "Load",
                    CONF_WINDOWS: [
                        {
                            CONF_WINDOW_NAME: "Peak",
                            CONF_WINDOW_START: "09:00",
                            CONF_WINDOW_END: "11:00",
                            CONF_COST_PER_KWH: 0.2,
                        }
                    ],
                }
            ]
        },
        options={},
        entry_id="legacy_title_rename",
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "list_windows"}
    )
    assert result["step_id"] == "edit_window"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "window_name": "Super Peak",
            CONF_COST_PER_KWH: 0.2,
            "start_1": "09:00",
            "end_1": "11:00",
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "options_saved"

    saved_entry = hass.config_entries.async_get_entry(entry.entry_id)
    assert saved_entry is not None
    assert saved_entry.title == "Super Peak"


@pytest.mark.asyncio
async def test_options_add_window_unhappy_duplicate_name_rejected_legacy_case(
    hass: HomeAssistant, mock_legacy_config_entry
) -> None:
    """[Unhappy] Adding another window with the same name is rejected."""
    result = await hass.config_entries.options.async_init(
        mock_legacy_config_entry.entry_id
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "add_window"}
    )
    assert result["step_id"] == "add_window"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "window_name": "Peak",
            CONF_COST_PER_KWH: 0.2,
            "start_1": "18:00",
            "end_1": "19:00",
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "add_window"
    assert result.get("errors", {}).get("base") == "duplicate_window_name"

    saved_entry = hass.config_entries.async_get_entry(mock_legacy_config_entry.entry_id)
    assert saved_entry is not None
    sources = (
        saved_entry.options.get(CONF_SOURCES)
        or saved_entry.data.get(CONF_SOURCES)
        or []
    )
    assert len(sources) == 1
    windows = sources[0][CONF_WINDOWS]
    peak_rows = [w for w in windows if w.get(CONF_WINDOW_NAME) == "Peak"]
    assert len(peak_rows) == 1


@pytest.mark.asyncio
async def test_window_setup_happy_same_name_with_multiple_entities_has_no_errors(
    hass: HomeAssistant,
) -> None:
    """[Happy] Same window name across multiple selected entities is allowed."""
    hass.states.async_set("sensor.today_load", "12.0")
    hass.states.async_set("sensor.today_import", "7.0")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "window_name": "Peak",
            "cost_per_kwh": 0.2,
            "start_1": "09:00",
            "end_1": "11:00",
        },
    )
    assert result["step_id"] == "window_entities"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"entities": ["sensor.today_load", "sensor.today_import"]},
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "window_entities_confirm"
    assert result.get("errors") in ({}, None)


@pytest.mark.asyncio
async def test_window_entities_happy_multiple_entities_creates_entry_and_sensors(
    hass: HomeAssistant,
) -> None:
    """[Happy] Selecting multiple entities on initial create completes successfully."""
    entity_ids = [
        "sensor.today_load",
        "sensor.today_battery_charge",
        "sensor.today_battery_discharge",
        "sensor.today_energy_export",
        "sensor.today_energy_import",
        "sensor.today_s_pv_generation",
    ]
    for eid in entity_ids:
        hass.states.async_set(eid, "1.0")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "window_name": "Peak",
            "cost_per_kwh": 0.2,
            "start_1": "09:00:00",
            "end_1": "11:00:00",
        },
    )
    assert result["step_id"] == "window_entities"

    with patch(
        "custom_components.energy_window_tracker_beta.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"entities": entity_ids},
        )
        await hass.async_block_till_done()

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "window_entities_confirm"

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) >= 1

    # One tracker sensor per selected entity.
    from homeassistant.helpers import entity_registry as er

    entry = entries[0]
    registry = er.async_get(hass)
    sensors = [
        e
        for e in registry.entities.get_entries_for_config_entry_id(entry.entry_id)
        if e.domain == "sensor"
    ]
    assert len(sensors) == len(entity_ids)


@pytest.mark.asyncio
async def test_window_entities_unhappy_setup_failed_shows_error(
    hass: HomeAssistant,
) -> None:
    """[Unhappy] If async_add fails, the flow returns window_entities with setup_failed."""
    hass.states.async_set("sensor.today_load", "1.0")
    entity_ids = ["sensor.today_load"]

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "window_name": "Peak",
            "cost_per_kwh": 0.2,
            "start_1": "09:00:00",
            "end_1": "11:00:00",
        },
    )
    assert result["step_id"] == "window_entities"

    with patch.object(
        hass.config_entries, "async_add", side_effect=RuntimeError("boom")
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"entities": entity_ids}
        )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "window_entities"
    assert result.get("errors", {}).get("base") == "setup_failed"
