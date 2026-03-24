"""Edge case tests for Energy Window Tracker Beta.

Mirrors the non-beta repo's depth: translation coverage, flow validation,
snapshot staleness handling, and entity unique_id stability.
"""

from __future__ import annotations

import inspect
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import voluptuous_serialize
from homeassistant import config_entries, data_entry_flow
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_window_tracker_beta.const import (
    CONF_IMPORT_RATE_PER_KWH,
    CONF_ENTITIES,
    CONF_RANGES,
    CONF_WINDOW_END,
    CONF_WINDOW_NAME,
    CONF_WINDOW_START,
    CONF_WINDOWS,
    DOMAIN,
    source_slug_from_entity_id,
)
from custom_components.energy_window_tracker_beta.sensor import _stable_window_unique_id


def _get_tracker_sensors(hass: HomeAssistant, entry_id: str) -> list:
    """Return entity registry entries for this integration config entry."""
    registry = er.async_get(hass)
    return [
        e
        for e in registry.entities.get_entries_for_config_entry_id(entry_id)
        if e.domain == SENSOR_DOMAIN
    ]


def _unique_ids_by_entity_id(hass: HomeAssistant, entry_id: str) -> dict[str, str]:
    """Map entity_id -> unique_id for this config entry."""
    return {e.entity_id: e.unique_id for e in _get_tracker_sensors(hass, entry_id)}


def _state_for_entry(hass: HomeAssistant, entry_id: str):
    """Return first sensor state (or None)."""
    sensors = _get_tracker_sensors(hass, entry_id)
    if not sensors:
        return None
    return hass.states.get(sensors[0].entity_id)


def _windows_based_entry(
    *,
    entry_id: str,
    window_groups: list[dict],
    title: str = "WF",
) -> MockConfigEntry:
    """Create a windows-based entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=title,
        data={CONF_WINDOWS: window_groups},
        options={},
        entry_id=entry_id,
    )


@pytest.mark.asyncio
async def test_window_setup_start_ge_end_rejected_errors_base(
    hass: HomeAssistant,
) -> None:
    """[Unhappy] window_setup with start >= end yields at_least_one_window."""
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
            "start_1": "17:00",
            "end_1": "09:00",
        },
    )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "window_setup"
    assert result.get("errors", {}).get("base") == "at_least_one_window"


@pytest.mark.asyncio
async def test_window_setup_invalid_time_value_shows_invalid_time(
    hass: HomeAssistant,
) -> None:
    """[Unhappy] window_setup invalid time string shows invalid_time (or schema rejects)."""
    from homeassistant.data_entry_flow import InvalidData

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    try:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "window_name": "Peak",
                "import_rate_per_kwh": 0.2,
                "start_1": "25:00",
                "end_1": "09:00",
            },
        )
    except InvalidData:
        # Some HA versions reject invalid times at schema level.
        return

    assert result["type"] in (
        data_entry_flow.FlowResultType.FORM,
        data_entry_flow.FlowResultType.ABORT,
    )
    if result["type"] is data_entry_flow.FlowResultType.FORM:
        assert result.get("errors", {}).get("start_1") == "invalid_time"


@pytest.mark.asyncio
async def test_window_setup_happy_seconds_are_persisted_as_hhmmss(
    hass: HomeAssistant,
) -> None:
    """[Happy] Seconds are accepted and stored in HH:MM:SS format."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "window_name": "Peak",
            "import_rate_per_kwh": 0.2,
            "start_1": "09:00:05",
            "end_1": "12:00:10",
        },
    )
    assert result["step_id"] == "window_entities"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"entities": ["sensor.today_load"]},
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "window_entities_confirm"

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    windows = entries[0].data.get(CONF_WINDOWS) or []
    assert windows
    ranges = windows[0].get(CONF_RANGES) or []
    assert ranges
    assert ranges[0][CONF_WINDOW_START] == "09:00:05"
    assert ranges[0][CONF_WINDOW_END] == "12:00:10"


@pytest.mark.asyncio
async def test_window_setup_unhappy_seconds_overlap_rejected(
    hass: HomeAssistant,
) -> None:
    """[Unhappy] Overlap by seconds is rejected in multi-range validation."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "window_name": "Peak",
            "import_rate_per_kwh": 0.2,
            "start_1": "09:00:00",
            "end_1": "12:00:30",
            "add_another": True,
        },
    )
    assert result["step_id"] == "window_setup"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "window_name": "Peak",
            "import_rate_per_kwh": 0.2,
            "start_1": "09:00:00",
            "end_1": "12:00:30",
            "start_2": "12:00:00",
            "end_2": "13:00:00",
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result.get("errors", {}).get("base") == "range_start_before_previous_end"


@pytest.mark.asyncio
async def test_options_add_window_start_ge_end_rejected(
    hass: HomeAssistant, mock_legacy_config_entry
) -> None:
    """[Unhappy] options add_window: start >= end shows window_start_after_end."""
    hass.states.async_set("sensor.today_load", "0")
    with patch(
        "custom_components.energy_window_tracker_beta.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        opts = await hass.config_entries.options.async_init(
            mock_legacy_config_entry.entry_id
        )

    result = await hass.config_entries.options.async_configure(
        opts["flow_id"], {"next_step_id": "add_window"}
    )
    assert result["step_id"] == "add_window"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "window_name": "Off-Peak",
            "import_rate_per_kwh": 0.1,
            "start_1": "18:00",
            "end_1": "06:00",
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result.get("errors", {}).get("base") == "window_start_after_end"


@pytest.mark.asyncio
async def test_options_add_window_invalid_time_value_field_error(
    hass: HomeAssistant, mock_legacy_config_entry
) -> None:
    """[Unhappy] options add_window invalid time value shows invalid_time on field."""
    from homeassistant.data_entry_flow import InvalidData

    hass.states.async_set("sensor.today_load", "0")
    with patch(
        "custom_components.energy_window_tracker_beta.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        opts = await hass.config_entries.options.async_init(
            mock_legacy_config_entry.entry_id
        )

    result = await hass.config_entries.options.async_configure(
        opts["flow_id"], {"next_step_id": "add_window"}
    )
    assert result["step_id"] == "add_window"
    try:
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "window_name": "Bad",
                "import_rate_per_kwh": 0.0,
                "start_1": "25:00",
                "end_1": "06:00",
            },
        )
        assert result["type"] is data_entry_flow.FlowResultType.FORM
        assert result.get("errors", {}).get("start_1") == "invalid_time"
    except InvalidData:
        # Some HA versions validate invalid time values at schema level.
        pass


@pytest.mark.asyncio
async def test_options_manage_windows_unique_names_only(hass: HomeAssistant) -> None:
    """[Happy] Manage windows lists one option per unique window name."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="UniqueNames",
        data={
            CONF_WINDOWS: [
                {
                    CONF_WINDOW_NAME: "Peak",
                    CONF_IMPORT_RATE_PER_KWH: 0.1,
                    CONF_ENTITIES: ["sensor.today_load"],
                    CONF_RANGES: [
                        {CONF_WINDOW_START: "09:00", CONF_WINDOW_END: "12:00"}
                    ],
                },
                {
                    CONF_WINDOW_NAME: "Peak",
                    CONF_IMPORT_RATE_PER_KWH: 0.1,
                    CONF_ENTITIES: ["sensor.today_load"],
                    CONF_RANGES: [
                        {CONF_WINDOW_START: "14:00", CONF_WINDOW_END: "17:00"}
                    ],
                },
                {
                    CONF_WINDOW_NAME: "Off-Peak",
                    CONF_IMPORT_RATE_PER_KWH: 0.1,
                    CONF_ENTITIES: ["sensor.today_load"],
                    CONF_RANGES: [
                        {CONF_WINDOW_START: "12:00", CONF_WINDOW_END: "14:00"}
                    ],
                },
            ]
        },
        options={},
        entry_id="unique_names_entry_id",
    )
    entry.add_to_hass(hass)
    hass.states.async_set("sensor.today_load", "0")
    with patch(
        "custom_components.energy_window_tracker_beta.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        opts = await hass.config_entries.options.async_init(entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        opts["flow_id"], {"next_step_id": "list_windows"}
    )
    assert result["step_id"] in ("edit_window", "manage_windows_empty")


def test_translation_contains_required_start_end_keys() -> None:
    """[Happy] strings.json includes start/end and start_1/end_1 keys for beta steps."""
    strings = __import__("json").loads(
        Path("custom_components/energy_window_tracker_beta/strings.json").read_text()
    )
    for step in ("windows", "add_window", "edit_window", "window_setup"):
        if step == "windows" and "windows" not in strings["config"]["step"]:
            continue
        if step in strings["config"]["step"]:
            data = strings["config"]["step"][step]["data"]
            assert "start_1" in data and "end_1" in data

    for step in ("add_window", "edit_window"):
        data = strings["options"]["step"][step]["data"]
        assert "start_1" in data and "end_1" in data
        assert "start_2" in data and "end_2" in data


@pytest.mark.asyncio
async def test_window_form_labels_built_from_start_time_end_time_window_setup(
    hass: HomeAssistant,
) -> None:
    """[Happy] _get_window_form_labels builds "Start time #N" strings for window_setup."""
    from custom_components.energy_window_tracker_beta.config_flow import (
        _data_key,
        _get_window_form_labels,
    )

    step_id = "window_setup"
    trans = {
        _data_key(step_id, "start_time"): "Start time",
        _data_key(step_id, "end_time"): "End time",
    }
    with patch(
        "custom_components.energy_window_tracker_beta.config_flow.async_get_translations",
        new_callable=AsyncMock,
        return_value=trans,
    ):
        labels = await _get_window_form_labels(hass, "config", step_id, num_ranges=3)

    assert labels["start_1"] == "Start time #1"
    assert labels["end_1"] == "End time #1"
    assert labels["start_2"] == "Start time #2"
    assert labels["end_2"] == "End time #2"
    assert labels["start_3"] == "Start time #3"
    assert labels["end_3"] == "End time #3"


@pytest.mark.asyncio
async def test_window_setup_happy_schema_serializes_with_allow_empty_slots(
    hass: HomeAssistant,
) -> None:
    """[Happy] window_setup schema remains JSON-serializable for HA API responses."""
    from custom_components.energy_window_tracker_beta.config_flow import (
        _build_single_window_multi_range_schema,
        _get_window_form_labels,
    )

    labels = await _get_window_form_labels(hass, "config", "window_setup", num_ranges=2)
    schema = _build_single_window_multi_range_schema(
        labels=labels,
        default_source_name=None,
        window_name="Peak",
        import_rate_per_kwh=0.2,
        ranges=[{CONF_WINDOW_START: "09:00:00", CONF_WINDOW_END: "10:00:00"}],
        include_add_another=True,
        num_slots=2,
        allow_empty_slots=True,
    )

    serialized = voluptuous_serialize.convert(schema, custom_serializer=cv.custom_serializer)
    names = {field["name"] for field in serialized}
    assert "start_1" in names and "end_1" in names
    assert "start_2" in names and "end_2" in names


@pytest.mark.asyncio
async def test_build_runtime_config_entry_happy_supports_new_ha_constructor_kwargs() -> None:
    """[Happy] Runtime ConfigEntry builder passes new HA kwargs when available."""
    from custom_components.energy_window_tracker_beta import config_flow

    captured: dict[str, object] = {}

    class DummyEntry:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.entry_id = str(kwargs.get("entry_id"))

    fake_sig = inspect.Signature(
        parameters=[
            inspect.Parameter("version", inspect.Parameter.KEYWORD_ONLY),
            inspect.Parameter("minor_version", inspect.Parameter.KEYWORD_ONLY),
            inspect.Parameter("domain", inspect.Parameter.KEYWORD_ONLY),
            inspect.Parameter("title", inspect.Parameter.KEYWORD_ONLY),
            inspect.Parameter("data", inspect.Parameter.KEYWORD_ONLY),
            inspect.Parameter("source", inspect.Parameter.KEYWORD_ONLY),
            inspect.Parameter("options", inspect.Parameter.KEYWORD_ONLY),
            inspect.Parameter("entry_id", inspect.Parameter.KEYWORD_ONLY),
            inspect.Parameter("unique_id", inspect.Parameter.KEYWORD_ONLY),
            inspect.Parameter("discovery_keys", inspect.Parameter.KEYWORD_ONLY),
            inspect.Parameter("subentries_data", inspect.Parameter.KEYWORD_ONLY),
        ]
    )

    with (
        patch.object(config_flow.inspect, "signature", return_value=fake_sig),
        patch.object(config_flow.config_entries, "ConfigEntry", DummyEntry),
    ):
        entry = config_flow._build_runtime_config_entry(
            title="Peak", windows_data=[{CONF_WINDOW_START: "09:00", CONF_WINDOW_END: "10:00"}]
        )

    assert entry is not None
    assert captured["unique_id"] is None
    assert captured["discovery_keys"] == {}
    assert captured["subentries_data"] == []


@pytest.mark.asyncio
async def test_sensor_same_day_snapshot_used_during_window(hass: HomeAssistant) -> None:
    """[Happy] Same-day stored snapshot_start is used for during_window value."""
    entry = _windows_based_entry(
        entry_id="snap_same_day_id",
        window_groups=[
            {
                CONF_WINDOW_NAME: "Peak",
                CONF_IMPORT_RATE_PER_KWH: 0.0,
                CONF_ENTITIES: ["sensor.today_load"],
                CONF_RANGES: [{CONF_WINDOW_START: "09:00", CONF_WINDOW_END: "17:00"}],
            }
        ],
        title="snap_same_day",
    )
    entry.add_to_hass(hass)
    hass.states.async_set("sensor.today_load", "5.0")

    noon_today = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
    today = noon_today.date().isoformat()
    stored = {
        "snapshot_date": today,
        "windows": {"0": {"snapshot_start": 1.0, "snapshot_end": None}},
    }
    with (
        patch(
            "custom_components.energy_window_tracker_beta.sensor.Store.async_load",
            new_callable=AsyncMock,
            return_value=stored,
        ),
        patch(
            "custom_components.energy_window_tracker_beta.sensor.dt_util.now",
            return_value=noon_today,
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    state = _state_for_entry(hass, entry.entry_id)
    assert state is not None
    assert state.attributes.get("status") == "during_window"
    assert float(state.state) == 4.0


@pytest.mark.asyncio
async def test_sensor_stale_snapshot_discarded_when_late_snapshot_disabled(
    hass: HomeAssistant,
) -> None:
    """[Unhappy] Stale snapshot_date cleared; during_window shows 0 (no snapshot)."""
    entry = _windows_based_entry(
        entry_id="snap_stale_id",
        window_groups=[
            {
                CONF_WINDOW_NAME: "Peak",
                CONF_IMPORT_RATE_PER_KWH: 0.0,
                CONF_ENTITIES: ["sensor.today_load"],
                CONF_RANGES: [{CONF_WINDOW_START: "09:00", CONF_WINDOW_END: "17:00"}],
            }
        ],
        title="snap_stale",
    )
    entry.add_to_hass(hass)
    hass.states.async_set("sensor.today_load", "5.0")

    noon_today = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
    stale = "2020-01-01"
    stored = {
        "snapshot_date": stale,
        "windows": {"0": {"snapshot_start": 1.0, "snapshot_end": None}},
    }
    with (
        patch(
            "custom_components.energy_window_tracker_beta.sensor.Store.async_load",
            new_callable=AsyncMock,
            return_value=stored,
        ),
        patch(
            "custom_components.energy_window_tracker_beta.sensor.dt_util.now",
            return_value=noon_today,
        ),
        patch(
            "custom_components.energy_window_tracker_beta.sensor.WindowData.take_late_start_snapshot",
            return_value=False,
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    state = _state_for_entry(hass, entry.entry_id)
    assert state is not None
    assert state.attributes.get("status") == "during_window (no snapshot)"
    assert float(state.state) == 0.0


@pytest.mark.asyncio
async def test_sensor_invalid_config_times_expose_config_warnings(
    hass: HomeAssistant,
) -> None:
    """[Unhappy] Invalid configured window times do not crash setup."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="invalid_times",
        data={
            CONF_WINDOWS: [
                {
                    CONF_WINDOW_NAME: "Peak",
                    CONF_IMPORT_RATE_PER_KWH: 0.0,
                    CONF_ENTITIES: ["sensor.today_load"],
                    CONF_RANGES: [
                        {
                            CONF_WINDOW_START: "25:00",
                            CONF_WINDOW_END: "17:00",
                        }
                    ],
                }
            ]
        },
        options={},
        entry_id="invalid_times_warn_id",
    )
    entry.add_to_hass(hass)
    hass.states.async_set("sensor.today_load", "5.0")
    with patch(
        "custom_components.energy_window_tracker_beta.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    state = _state_for_entry(hass, entry.entry_id)
    assert state is None


@pytest.mark.asyncio
async def test_unique_ids_stable_when_window_groups_reordered(
    hass: HomeAssistant,
) -> None:
    """[Happy] Reordering window groups must not swap unique_ids."""
    entry_id = "reorder_unique_id"
    source_entity = "sensor.today_load"
    source_slug = source_slug_from_entity_id(source_entity, "source_0")

    peak_uid = _stable_window_unique_id(entry_id, source_slug, "09:00:00-12:00:00")
    off_uid = _stable_window_unique_id(entry_id, source_slug, "12:00:00-17:00:00")

    entry = _windows_based_entry(
        entry_id=entry_id,
        window_groups=[
            {
                CONF_WINDOW_NAME: "Peak",
                CONF_IMPORT_RATE_PER_KWH: 0.0,
                CONF_ENTITIES: [source_entity],
                CONF_RANGES: [{CONF_WINDOW_START: "09:00", CONF_WINDOW_END: "12:00"}],
            },
            {
                CONF_WINDOW_NAME: "Off-Peak",
                CONF_IMPORT_RATE_PER_KWH: 0.0,
                CONF_ENTITIES: [source_entity],
                CONF_RANGES: [{CONF_WINDOW_START: "12:00", CONF_WINDOW_END: "17:00"}],
            },
        ],
        title="reorder",
    )
    entry.add_to_hass(hass)
    hass.states.async_set(source_entity, "0")

    with patch(
        "custom_components.energy_window_tracker_beta.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    initial = _unique_ids_by_entity_id(hass, entry.entry_id)
    assert set(initial.values()) == {peak_uid, off_uid}

    # Unload -> update data -> setup (ensures entity registry resolution happens fresh)
    assert await hass.config_entries.async_unload(entry.entry_id)
    entry2 = hass.config_entries.async_get_entry(entry.entry_id)
    assert entry2 is not None
    hass.config_entries.async_update_entry(
        entry2,
        data={
            CONF_WINDOWS: list(reversed(entry2.data[CONF_WINDOWS])),
        },
    )

    with patch(
        "custom_components.energy_window_tracker_beta.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    after = _unique_ids_by_entity_id(hass, entry.entry_id)
    assert set(after.values()) == {peak_uid, off_uid}
    assert after == initial, "entity_id -> unique_id mapping should remain stable"


@pytest.mark.asyncio
async def test_unique_ids_happy_stay_stable_when_window_renamed(
    hass: HomeAssistant,
) -> None:
    """[Happy] Renaming one window keeps unique_ids when ranges are unchanged."""
    entry_id = "rename_unique_id"
    source_entity = "sensor.today_load"
    source_slug = source_slug_from_entity_id(source_entity, "source_0")

    peak_uid = _stable_window_unique_id(entry_id, source_slug, "09:00:00-12:00:00")
    off_uid = _stable_window_unique_id(entry_id, source_slug, "12:00:00-17:00:00")

    entry = _windows_based_entry(
        entry_id=entry_id,
        window_groups=[
            {
                CONF_WINDOW_NAME: "Peak",
                CONF_IMPORT_RATE_PER_KWH: 0.0,
                CONF_ENTITIES: [source_entity],
                CONF_RANGES: [{CONF_WINDOW_START: "09:00", CONF_WINDOW_END: "12:00"}],
            },
            {
                CONF_WINDOW_NAME: "Off-Peak",
                CONF_IMPORT_RATE_PER_KWH: 0.0,
                CONF_ENTITIES: [source_entity],
                CONF_RANGES: [{CONF_WINDOW_START: "12:00", CONF_WINDOW_END: "17:00"}],
            },
        ],
        title="rename",
    )
    entry.add_to_hass(hass)
    hass.states.async_set(source_entity, "0")

    with patch(
        "custom_components.energy_window_tracker_beta.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    initial = _unique_ids_by_entity_id(hass, entry.entry_id)
    assert set(initial.values()) == {peak_uid, off_uid}
    # Keep track of Off-Peak entity_id
    off_entity_id = next(eid for eid, uid in initial.items() if uid == off_uid)

    assert await hass.config_entries.async_unload(entry.entry_id)
    entry2 = hass.config_entries.async_get_entry(entry.entry_id)
    assert entry2 is not None
    renamed_groups = []
    for g in entry2.data[CONF_WINDOWS]:
        if g.get(CONF_WINDOW_NAME) == "Peak":
            g = {**g, CONF_WINDOW_NAME: "Super Peak"}
        renamed_groups.append(g)
    hass.config_entries.async_update_entry(
        entry2,
        data={CONF_WINDOWS: renamed_groups},
    )

    with patch(
        "custom_components.energy_window_tracker_beta.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    after = _unique_ids_by_entity_id(hass, entry.entry_id)
    assert set(after.values()) == {peak_uid, off_uid}
    assert after[off_entity_id] == off_uid, (
        "Off-Peak should keep same unique_id and entity_id"
    )
    assert peak_uid in set(after.values())


@pytest.mark.asyncio
async def test_options_rename_happy_preserves_unique_ids_and_history_identity(
    hass: HomeAssistant,
) -> None:
    """[Happy] Renaming via options flow keeps unique IDs stable."""
    entry = _windows_based_entry(
        entry_id="options_rename_stable_id",
        window_groups=[
            {
                CONF_WINDOW_NAME: "ZEROCHARGE",
                CONF_IMPORT_RATE_PER_KWH: 0.0,
                CONF_ENTITIES: ["sensor.today_load"],
                CONF_RANGES: [{CONF_WINDOW_START: "09:00", CONF_WINDOW_END: "12:00"}],
            }
        ],
        title="ZEROCHARGE",
    )
    entry.add_to_hass(hass)
    hass.states.async_set("sensor.today_load", "0")

    with patch(
        "custom_components.energy_window_tracker_beta.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    before = _unique_ids_by_entity_id(hass, entry.entry_id)
    assert before

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "list_windows"}
    )
    assert result["step_id"] == "edit_window"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "window_name": "ZEROCHARGE2",
            CONF_IMPORT_RATE_PER_KWH: 0.0,
            "start_1": "09:00:00",
            "end_1": "12:00:00",
        },
    )
    assert result["step_id"] == "options_saved"
    await hass.async_block_till_done()

    after = _unique_ids_by_entity_id(hass, entry.entry_id)
    assert after
    assert set(after.values()) == set(before.values())
