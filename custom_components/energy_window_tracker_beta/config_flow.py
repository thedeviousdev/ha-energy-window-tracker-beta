"""Config flow for Energy Window Tracker (Beta).

Where translated strings show
-----------------------------
Form field labels (e.g. "1 - Start time", "2 - End time") appear in the UI when you:
- Add an entry: step "Add window" (windows) and "Add new window" (add_window)
- Configure an entry: "Add new window" and "Edit window" (add_window, edit_window)

Important: in Home Assistant flows, the visible *field label* comes from translations for
the field key under config.step.<step_id>.data.<field> / options.step.<step_id>.data.<field>.
For this integration, the time fields are keyed as start/end/start_1/end_1/... so translations
must include those keys (e.g. "start": "1 - Start time", "start_1": "2 - Start time", etc.).

_get_window_form_labels() builds helper strings too, but those are used as schema descriptions
and are not reliably shown as the field label for selector fields.

Translation files (strings.json, translations/en.json) therefore need start/end/start_1/end_1...
as well as start_time/end_time for these window steps.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol
from homeassistant import config_entries, data_entry_flow
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector
from homeassistant.helpers.storage import Store
from homeassistant.helpers.translation import async_get_translations

from .const import (
    CONF_COST_PER_KWH,
    CONF_ENTITIES,
    CONF_NAME,
    CONF_RANGES,
    CONF_SOURCE_ENTITY,
    CONF_SOURCES,
    CONF_WINDOW_END,
    CONF_WINDOW_NAME,
    CONF_WINDOW_START,
    CONF_WINDOWS,
    DEFAULT_ENTRY_TITLE_KEY,
    DEFAULT_NAME_KEY,
    DEFAULT_SOURCE_ENTITY,
    DEFAULT_WINDOW_END,
    DEFAULT_WINDOW_FALLBACK_KEY,
    DEFAULT_WINDOW_START,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
    source_slug_from_entity_id,
)

_MAIN_LOGGER = logging.getLogger("custom_components.energy_window_tracker_beta")


# Only accept HH:MM or H:MM so schema defaults are always valid
_RE_HHMM = re.compile(r"^(\d{1,2}):(\d{2})$")


def _is_valid_time_value(v: Any) -> bool:
    """Return True if value looks like a valid time input (HH:MM[:SS] string or dict)."""
    try:
        if v is None:
            return False
        if isinstance(v, dict):
            h = v.get("hour", v.get("hours"))
            m = v.get("minute", v.get("minutes"))
            if h is None or m is None:
                return False
            h_i, m_i = int(h), int(m)
            return 0 <= h_i <= 23 and 0 <= m_i <= 59
        s = str(v).strip()
        if not s:
            return False
        if s.count(":") >= 2:
            s = s.rsplit(":", 1)[0]
        if not _RE_HHMM.match(s):
            return False
        hh, mm = s.split(":")
        h_i, m_i = int(hh, 10), int(mm, 10)
        return 0 <= h_i <= 23 and 0 <= m_i <= 59
    except (TypeError, ValueError):
        return False


def _validate_time_fields(data: dict[str, Any], num_ranges: int) -> dict[str, str]:
    """Validate start/end fields; return voluptuous-style errors dict (field -> error_key)."""
    errors: dict[str, str] = {}
    keys = [("start", "end")]
    for i in range(1, num_ranges):
        keys.append((f"start_{i}", f"end_{i}"))
    for sk, ek in keys:
        if sk in data and not _is_valid_time_value(data.get(sk)):
            errors[sk] = "invalid_time"
        if ek in data and not _is_valid_time_value(data.get(ek)):
            errors[ek] = "invalid_time"
    return errors


def _time_to_str(t: Any) -> str:
    """Convert time object or string to HH:MM format. Never raises. Invalid -> 00:00."""

    def valid(s: str) -> str:
        s = (s or "").strip()
        # Accept HH:MM:SS or HH:MM (e.g. frontend may send 09:00:00 or 9:00:00)
        if s.count(":") >= 2:
            s = s.rsplit(":", 1)[
                0
            ]  # drop seconds: "09:00:00" -> "09:00", "9:00:00" -> "9:00"
        elif len(s) > 5:
            s = s[:5]
        if _RE_HHMM.match(s):
            parts = s.split(":")
            h, m = int(parts[0], 10), int(parts[1], 10)
            if 0 <= h <= 23 and 0 <= m <= 59:
                return f"{h:02d}:{m:02d}"
        return "00:00"

    try:
        if t is None:
            return "00:00"
        if isinstance(t, str):
            return valid(t)
        if isinstance(t, dict):
            h = t.get("hour", t.get("hours", 0))
            m = t.get("minute", t.get("minutes", 0))
            return f"{int(h) % 24:02d}:{int(m) % 60:02d}"
        if hasattr(t, "strftime"):
            return valid(t.strftime("%H:%M"))
        if hasattr(t, "hour") and hasattr(t, "minute"):
            return f"{int(t.hour):02d}:{int(t.minute):02d}"
        return valid(str(t))
    except (TypeError, ValueError, AttributeError, KeyError):
        return "00:00"


def _normalize_entity_selector_value(value: Any) -> str:
    """Normalize EntitySelector result to a single entity_id string (frontend may send list or dict)."""
    if value is None:
        _MAIN_LOGGER.debug("entity selector value: None -> ''")
        return ""
    if isinstance(value, str):
        out = value.strip()
        _MAIN_LOGGER.debug(
            "entity selector value: str %r -> %r",
            value[:80] if len(value) > 80 else value,
            out,
        )
        return out
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, str):
            out = first.strip()
            _MAIN_LOGGER.debug("entity selector value: list[str] -> %r", out)
            return out
        if isinstance(first, dict):
            out = _normalize_entity_selector_value(first.get("entity_id") or first.get("id") or "")
            _MAIN_LOGGER.debug("entity selector value: list[dict] -> %r", out)
            return out
        out = str(first).strip()
        _MAIN_LOGGER.debug("entity selector value: list[other] -> %r", out)
        return out
    if isinstance(value, dict):
        out = _normalize_entity_selector_value(value.get("entity_id") or value.get("id") or "")
        _MAIN_LOGGER.debug("entity selector value: dict -> %r", out)
        return out
    out = str(value).strip() if value else ""
    _MAIN_LOGGER.debug("entity selector value: type %s -> %r", type(value).__name__, out)
    return out


def _get_entity_friendly_name(
    hass: Any, entity_id: str, default: str | None = None
) -> str:
    """Get friendly name for an entity, fallback to entity id or default."""
    entity_id = _normalize_entity_selector_value(entity_id) or (entity_id if isinstance(entity_id, str) else "")
    try:
        state = hass.states.get(entity_id)
        if state:
            name = state.attributes.get("friendly_name")
            if name:
                return str(name)[:200]
        if entity_id:
            return str(entity_id.split(".")[-1].replace("_", " ").title())[:200]
    except (TypeError, AttributeError, KeyError):
        pass
    return default if default is not None else "Window"


def _normalize_windows_for_schema(raw: Any) -> list[dict[str, Any]]:
    """Return a list of dicts with name/start/end/cost_per_kwh for schema defaults. Never raises."""
    out: list[dict[str, Any]] = []
    if not isinstance(raw, list):
        return out
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        cost = 0.0
        if CONF_COST_PER_KWH in item and item[CONF_COST_PER_KWH] is not None:
            try:
                cost = max(0.0, float(item[CONF_COST_PER_KWH]))
            except (TypeError, ValueError):
                pass
        out.append(
            {
                CONF_WINDOW_NAME: str(item.get(CONF_WINDOW_NAME) or "")[:200],
                CONF_WINDOW_START: _time_to_str(item.get(CONF_WINDOW_START)),
                CONF_WINDOW_END: _time_to_str(item.get(CONF_WINDOW_END)),
                CONF_COST_PER_KWH: cost,
            }
        )
    return out


def _build_step_user_schema() -> vol.Schema:
    """Build step 1 schema: legacy-only fallback (not shown in normal flow)."""
    return vol.Schema(
        {
            vol.Optional(
                CONF_SOURCE_ENTITY,
                default=DEFAULT_SOURCE_ENTITY,
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
        }
    )


def _normalize_entities_selector_value(value: Any) -> list[str]:
    """Normalize EntitySelector result to list of entity ids."""
    if value is None:
        return []
    if isinstance(value, str):
        v = value.strip()
        return [v] if v else []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
            elif isinstance(item, dict):
                eid = item.get("entity_id") or item.get("id")
                if isinstance(eid, str) and eid.strip():
                    out.append(eid.strip())
        return out
    if isinstance(value, dict):
        eid = value.get("entity_id") or value.get("id")
        if isinstance(eid, str) and eid.strip():
            return [eid.strip()]
    return []


async def _get_config_defaults(hass: Any) -> dict[str, str]:
    """Load config.defaults from translations (entry_title, window_name, window_fallback)."""
    lang = hass.config.language or "en"
    try:
        trans = await async_get_translations(hass, lang, "config", [DOMAIN]) or {}
    except Exception:  # noqa: BLE001
        trans = {}
    return {
        "entry_title": trans.get(DEFAULT_ENTRY_TITLE_KEY) or "Energy Window Tracker (Beta)",
        "window_name": trans.get(DEFAULT_NAME_KEY) or "Window",
        "window_fallback": trans.get(DEFAULT_WINDOW_FALLBACK_KEY) or "Window {n}",
    }


def _data_key(step_id: str, field: str) -> str:
    """Translation key for step data field: step.<step_id>.data.<field>."""
    return f"step.{step_id}.data.{field}"


async def _get_window_form_labels(
    hass: Any,
    translation_domain: str,
    step_id: str,
    num_ranges: int | None = None,
) -> dict[str, str]:
    """Load translated labels for the single-window form (one name, one cost, N start/end pairs).
    Uses start_time and end_time from translations; builds labels as "{index} - Start time" etc.
    """
    lang = hass.config.language or "en"
    try:
        trans = await async_get_translations(hass, lang, translation_domain, [DOMAIN]) or {}
    except Exception:  # noqa: BLE001
        trans = {}
    labels: dict[str, str] = {}
    for key in ("window_name", "cost_per_kwh", "add_another", "delete_this_window"):
        k = _data_key(step_id, key)
        if k in trans:
            labels[key] = trans[k]
    start_time = trans.get(_data_key(step_id, "start_time")) or "Start time"
    end_time = trans.get(_data_key(step_id, "end_time")) or "End time"
    n_r = num_ranges if num_ranges is not None else 1
    if num_ranges is not None:
        for i in range(num_ranges):
            idx = i + 1
            if i == 0:
                labels["start"] = f"{idx} - {start_time}"
                labels["end"] = f"{idx} - {end_time}"
            else:
                labels[f"start_{i}"] = f"{idx} - {start_time}"
                labels[f"end_{i}"] = f"{idx} - {end_time}"
    else:
        labels["start"] = f"1 - {start_time}"
        labels["end"] = f"1 - {end_time}"
        for i in range(1, n_r):
            labels[f"start_{i}"] = f"{i + 1} - {start_time}"
            labels[f"end_{i}"] = f"{i + 1} - {end_time}"
    return labels


def _build_single_window_multi_range_schema(
    labels: dict[str, str],
    default_source_name: str | None,
    window_name: str,
    cost_per_kwh: float,
    ranges: list[dict[str, str]],
    include_add_another: bool,
    include_delete: bool = False,
    num_slots: int | None = None,
) -> vol.Schema:
    """Build schema: one window name, one cost, then start/end for range 0, start_1/end_1, ...
    Labels: "1 - Start time", "1 - End time", "2 - Start time", etc. (built in _get_window_form_labels).
    If num_slots is set, that many range slots are shown; otherwise max(1, len(ranges)).
    """
    schema_dict: dict[Any, Any] = {}
    if default_source_name is not None:
        schema_dict[vol.Optional("source_name", default=default_source_name)] = str
    schema_dict[
        vol.Optional("window_name", default=window_name or "", description=labels.get("window_name"))
    ] = str
    schema_dict[
        vol.Optional(
            CONF_COST_PER_KWH,
            default=cost_per_kwh,
            description=labels.get("cost_per_kwh"),
        )
    ] = selector.NumberSelector(
        selector.NumberSelectorConfig(min=0, max=100, step=0.001, mode="box")
    )
    num_ranges = num_slots if num_slots is not None else max(1, len(ranges))
    for i in range(num_ranges):
        if i == 0:
            sk, ek = "start", "end"
            s_def = _time_to_str(ranges[0].get("start") if ranges else DEFAULT_WINDOW_START)
            e_def = _time_to_str(ranges[0].get("end") if ranges else DEFAULT_WINDOW_END)
        else:
            sk, ek = f"start_{i}", f"end_{i}"
            r = ranges[i] if i < len(ranges) else {}
            s_def = _time_to_str(r.get("start") or DEFAULT_WINDOW_START)
            e_def = _time_to_str(r.get("end") or DEFAULT_WINDOW_END)
        # Labels built in _get_window_form_labels: "{index} - Start time" / "{index} - End time"
        start_desc = labels.get(sk) or labels.get("start") or "Start time"
        end_desc = labels.get(ek) or labels.get("end") or "End time"
        schema_dict[
            vol.Optional(sk, default=s_def, description=start_desc)
        ] = selector.TimeSelector()
        schema_dict[
            vol.Optional(ek, default=e_def, description=end_desc)
        ] = selector.TimeSelector()
    if include_add_another:
        schema_dict[
            vol.Optional("add_another", default=False, description=labels.get("add_another"))
        ] = bool
    if include_delete:
        schema_dict[
            vol.Optional("delete_this_window", default=False, description=labels.get("delete_this_window"))
        ] = bool
    return vol.Schema(schema_dict)


def _collect_ranges_from_single_window_form(
    data: dict[str, Any], num_ranges: int
) -> tuple[str, float, list[tuple[str, str]]]:
    """From form with window_name, cost_per_kwh, start, end, start_1, end_1, ... return (name, cost, [(start,end), ...])."""
    name = (data.get("window_name") or data.get("name") or "").strip()
    cost = _parse_cost(data.get(CONF_COST_PER_KWH))
    out: list[tuple[str, str]] = []
    start = _time_to_str(data.get("start") or "00:00")
    end = _time_to_str(data.get("end") or "00:00")
    if start < end:
        out.append((start, end))
    for i in range(1, num_ranges):
        start = _time_to_str(data.get(f"start_{i}") or "00:00")
        end = _time_to_str(data.get(f"end_{i}") or "00:00")
        if start < end:
            out.append((start, end))
    return name, cost, out


def _validate_ranges_chronological(ranges: list[tuple[str, str]]) -> str | None:
    """Return error key if ranges overlap or are not in order (each start must be >= previous end)."""
    if len(ranges) <= 1:
        return None
    for i in range(1, len(ranges)):
        if ranges[i][0] < ranges[i - 1][1]:
            return "range_start_before_previous_end"
    return None


def _parse_cost(v: Any) -> float:
    """Parse cost_per_kwh from user input; return 0 if missing or invalid."""
    if v is None:
        return 0.0
    try:
        return max(0.0, float(v))
    except (TypeError, ValueError):
        return 0.0


def _collect_windows_from_input(data: dict, num_rows: int, use_simple_keys: bool = False) -> list[dict[str, Any]]:
    """Collect windows from form data for rows 0..num_rows-1. Same-day only (start < end); no overnight."""
    windows = []
    for i in range(num_rows):
        if use_simple_keys and i == 0:
            start = _time_to_str(data.get("start") or "00:00")
            end = _time_to_str(data.get("end") or "00:00")
            name = (data.get("name") or "").strip()
            cost = _parse_cost(data.get(CONF_COST_PER_KWH))
        else:
            start = _time_to_str(data.get(f"w{i}_start", "00:00"))
            end = _time_to_str(data.get(f"w{i}_end", "00:00"))
            name = (data.get(f"w{i}_name") or "").strip()
            cost = _parse_cost(data.get(f"w{i}_{CONF_COST_PER_KWH}"))
        if start >= end:
            continue
        windows.append(
            {
                CONF_WINDOW_START: start,
                CONF_WINDOW_END: end,
                CONF_WINDOW_NAME: name or None,
                CONF_COST_PER_KWH: cost,
            }
        )
    return windows


def _get_window_rows_from_input(data: dict, num_rows: int, use_simple_keys: bool = False) -> list[dict[str, Any]]:
    """Get all row data from input for re-showing form after validation error."""
    rows = []
    for i in range(num_rows):
        if use_simple_keys and i == 0:
            rows.append({
                CONF_WINDOW_NAME: data.get("name") or "",
                CONF_WINDOW_START: _time_to_str(data.get("start") or "00:00"),
                CONF_WINDOW_END: _time_to_str(data.get("end") or "00:00"),
                CONF_COST_PER_KWH: _parse_cost(data.get(CONF_COST_PER_KWH)),
            })
        else:
            rows.append({
                CONF_WINDOW_NAME: data.get(f"w{i}_name") or "",
                CONF_WINDOW_START: _time_to_str(data.get(f"w{i}_start", "00:00")),
                CONF_WINDOW_END: _time_to_str(data.get(f"w{i}_end", "00:00")),
                CONF_COST_PER_KWH: _parse_cost(data.get(f"w{i}_{CONF_COST_PER_KWH}")),
            })
    return rows


class EnergyWindowConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Energy Window Tracker (Beta)."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self._source_entity: str | None = None
        self._pending_entry_title: str | None = None
        self._pending_sources: list[dict[str, Any]] | None = None
        self._edit_index: int = 0
        self._edit_window_name: str | None = None
        self._initial_window_name: str = ""
        self._initial_window_cost: float = 0.0
        self._initial_ranges: list[dict[str, str]] = []
        self._pending_add_name: str = ""
        self._pending_add_cost: float = 0.0
        self._pending_add_ranges: list[dict[str, str]] = []
        self._wf_windows: list[dict[str, Any]] = []
        self._wf_name: str = ""
        self._wf_cost: float = 0.0
        self._wf_ranges: list[dict[str, str]] = []

    def _get_pending_source(self) -> dict[str, Any]:
        """Get the single pending source (during initial flow before entry exists)."""
        if not self._pending_sources or not isinstance(self._pending_sources[0], dict):
            raise ValueError("No pending source")
        return self._pending_sources[0]

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step 1: window-first flow starts directly at window definition."""
        _MAIN_LOGGER.warning(
            "config flow step user: user_input=%s",
            "submitted" if user_input is not None else "show form",
        )
        return await self.async_step_wf_window(user_input)

    async def async_step_wf_window(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Window-first setup: define a window and one or more ranges."""
        errors: dict[str, str] = {}
        num_ranges = len(self._wf_ranges) + 1
        labels = await _get_window_form_labels(self.hass, "config", "windows", num_ranges=num_ranges)
        if user_input is not None:
            time_errors = _validate_time_fields(user_input, num_ranges)
            if time_errors:
                schema = _build_single_window_multi_range_schema(
                    labels,
                    None,
                    (user_input.get("window_name") or "").strip(),
                    _parse_cost(user_input.get(CONF_COST_PER_KWH)),
                    self._wf_ranges,
                    include_add_another=True,
                    include_delete=False,
                    num_slots=num_ranges,
                )
                return self.async_show_form(step_id="wf_window", data_schema=schema, errors=time_errors)

            n_collect = len(self._wf_ranges) + 1 if self._wf_ranges else max(num_ranges, 1)
            w_name, cost, ranges = _collect_ranges_from_single_window_form(user_input, n_collect)
            if not ranges:
                errors["base"] = "at_least_one_window"
            else:
                range_error = _validate_ranges_chronological(ranges)
                if range_error:
                    errors["base"] = range_error
            if errors:
                schema = _build_single_window_multi_range_schema(
                    labels,
                    None,
                    w_name or "",
                    cost,
                    [{"start": s, "end": e} for s, e in ranges] or self._wf_ranges,
                    include_add_another=True,
                    include_delete=False,
                    num_slots=n_collect,
                )
                return self.async_show_form(step_id="wf_window", data_schema=schema, errors=errors)

            self._wf_name = w_name or ""
            self._wf_cost = cost
            self._wf_ranges = [{"start": s, "end": e} for s, e in ranges]
            if user_input.get("add_another"):
                schema = _build_single_window_multi_range_schema(
                    labels,
                    None,
                    self._wf_name,
                    self._wf_cost,
                    self._wf_ranges,
                    include_add_another=True,
                    include_delete=False,
                    num_slots=len(self._wf_ranges) + 1,
                )
                return self.async_show_form(step_id="wf_window", data_schema=schema, errors={})
            return await self.async_step_wf_entities()

        schema = _build_single_window_multi_range_schema(
            labels,
            None,
            self._wf_name,
            self._wf_cost,
            self._wf_ranges,
            include_add_another=True,
            include_delete=False,
            num_slots=num_ranges,
        )
        return self.async_show_form(step_id="wf_window", data_schema=schema, errors=errors)

    async def async_step_wf_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Window-first setup: select entities assigned to this window."""
        schema = vol.Schema(
            {
                vol.Required(CONF_ENTITIES): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", multiple=True)
                )
            }
        )
        if user_input is not None:
            entities = _normalize_entities_selector_value(user_input.get(CONF_ENTITIES))
            if not entities:
                return self.async_show_form(
                    step_id="wf_entities",
                    data_schema=schema,
                    errors={"base": "source_entity_required"},
                )
            self._wf_windows.append(
                {
                    CONF_WINDOW_NAME: self._wf_name or None,
                    CONF_COST_PER_KWH: self._wf_cost,
                    CONF_RANGES: list(self._wf_ranges),
                    CONF_ENTITIES: entities,
                }
            )
            self._wf_name = ""
            self._wf_cost = 0.0
            self._wf_ranges = []
            return await self.async_step_wf_more()
        return self.async_show_form(step_id="wf_entities", data_schema=schema, errors={})

    async def async_step_wf_more(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Window-first setup menu."""
        if user_input is not None:
            next_step = user_input.get("next_step_id")
            if next_step == "wf_window":
                return await self.async_step_wf_window()
            if next_step == "wf_done":
                return await self.async_step_wf_done()
        return {
            "type": data_entry_flow.FlowResultType.MENU,
            "flow_id": self.flow_id,
            "handler": self.handler,
            "step_id": "wf_more",
            "menu_options": {"wf_window": "✚ Add new window", "wf_done": "Done"},
            "title": "Configure Energy Window Tracker (Beta)",
        }

    async def async_step_wf_done(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Create entry for window-first setup."""
        defaults = await _get_config_defaults(self.hass)
        return self.async_create_entry(
            title=defaults["entry_title"],
            data={CONF_WINDOWS: self._wf_windows},
        )

    async def async_step_windows(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step 2: source name, one window name, one cost, N time ranges. 'Add another' for more ranges."""
        errors: dict[str, str] = {}
        source_entity = _normalize_entity_selector_value(self._source_entity) or ""
        _MAIN_LOGGER.warning(
            "config flow step windows: user_input=%s, source_entity=%r",
            "submitted" if user_input is not None else "None (show form)",
            source_entity,
        )
        num_ranges = len(self._initial_ranges) + 1
        defaults = await _get_config_defaults(self.hass)
        default_name = _get_entity_friendly_name(self.hass, source_entity, defaults["window_name"])
        labels = await _get_window_form_labels(self.hass, "config", "windows", num_ranges=num_ranges)

        if user_input is not None:
            _MAIN_LOGGER.warning(
                "config: windows - form submitted (add_another=%s)",
                bool(user_input.get("add_another")),
            )
            _MAIN_LOGGER.warning("config flow step windows: submitted keys=%s", list(user_input.keys()))
            time_errors = _validate_time_fields(user_input, num_ranges)
            if time_errors:
                ranges_for_form = [
                    {"start": user_input.get("start") or "00:00", "end": user_input.get("end") or "00:00"}
                ]
                for i in range(1, num_ranges):
                    ranges_for_form.append(
                        {
                            "start": user_input.get(f"start_{i}") or "00:00",
                            "end": user_input.get(f"end_{i}") or "00:00",
                        }
                    )
                err_labels = await _get_window_form_labels(self.hass, "config", "windows", num_ranges=num_ranges)
                schema = _build_single_window_multi_range_schema(
                    err_labels,
                    user_input.get("source_name") or default_name,
                    (user_input.get("window_name") or "").strip(),
                    _parse_cost(user_input.get(CONF_COST_PER_KWH)),
                    ranges_for_form,
                    include_add_another=True,
                    include_delete=False,
                    num_slots=num_ranges,
                )
                return self.async_show_form(step_id="windows", data_schema=schema, errors=time_errors)
            # After "Add another time range" the form has more slots; use that count when collecting
            num_ranges_for_collect = (
                len(self._initial_ranges) + 1 if self._initial_ranges else max(num_ranges, 1)
            )
            w_name, cost, ranges = _collect_ranges_from_single_window_form(
                user_input, num_ranges_for_collect
            )
            if not ranges:
                first_start = _time_to_str(user_input.get("start") or "00:00")
                first_end = _time_to_str(user_input.get("end") or "00:00")
                errors["base"] = "window_start_after_end" if first_start >= first_end else "at_least_one_window"
                ranges_for_form = [{"start": user_input.get("start") or "00:00", "end": user_input.get("end") or "00:00"}]
                for i in range(1, num_ranges_for_collect):
                    ranges_for_form.append({"start": user_input.get(f"start_{i}") or "00:00", "end": user_input.get(f"end_{i}") or "00:00"})
                err_labels = await _get_window_form_labels(
                    self.hass, "config", "windows", num_ranges=num_ranges_for_collect
                )
                schema = _build_single_window_multi_range_schema(
                    err_labels,
                    user_input.get("source_name") or default_name,
                    w_name or "",
                    cost,
                    ranges_for_form,
                    include_add_another=True,
                    include_delete=False,
                    num_slots=num_ranges_for_collect,
                )
                return self.async_show_form(step_id="windows", data_schema=schema, errors=errors)
            range_error = _validate_ranges_chronological(ranges)
            if range_error:
                errors["base"] = range_error
                ranges_for_form = [{"start": user_input.get("start") or "00:00", "end": user_input.get("end") or "00:00"}]
                for i in range(1, num_ranges_for_collect):
                    ranges_for_form.append({"start": user_input.get(f"start_{i}") or "00:00", "end": user_input.get(f"end_{i}") or "00:00"})
                err_labels = await _get_window_form_labels(
                    self.hass, "config", "windows", num_ranges=num_ranges_for_collect
                )
                schema = _build_single_window_multi_range_schema(
                    err_labels,
                    user_input.get("source_name") or default_name,
                    w_name or "",
                    cost,
                    ranges_for_form,
                    include_add_another=True,
                    include_delete=False,
                    num_slots=num_ranges_for_collect,
                )
                return self.async_show_form(step_id="windows", data_schema=schema, errors=errors)
            if user_input.get("add_another"):
                _MAIN_LOGGER.warning(
                    "config: windows - add another time range (total %s)",
                    len(ranges) + 1,
                )
                self._initial_window_name = w_name or ""
                self._initial_window_cost = cost
                self._initial_ranges = [{"start": s, "end": e} for s, e in ranges]
                num_ranges = len(self._initial_ranges) + 1
                labels = await _get_window_form_labels(self.hass, "config", "windows", num_ranges=num_ranges)
                schema = _build_single_window_multi_range_schema(
                    labels,
                    user_input.get("source_name") or default_name,
                    self._initial_window_name,
                    self._initial_window_cost,
                    self._initial_ranges,
                    include_add_another=True,
                    include_delete=False,
                    num_slots=num_ranges,
                )
                return self.async_show_form(step_id="windows", data_schema=schema, errors=errors)
            source_name = (user_input.get("source_name") or "").strip() or default_name
            source_name = (source_name or defaults["entry_title"]).strip()[:200]
            entry_title = source_name or defaults["entry_title"]
            existing = _entry_using_source_entity(self.hass, source_entity, exclude_entry_id=None)
            if existing is not None:
                err_labels = await _get_window_form_labels(
                    self.hass, "config", "windows", num_ranges=num_ranges_for_collect
                )
                schema = _build_single_window_multi_range_schema(
                    err_labels,
                    user_input.get("source_name") or default_name,
                    w_name or "",
                    cost,
                    [{"start": s, "end": e} for s, e in ranges],
                    include_add_another=True,
                    include_delete=False,
                    num_slots=num_ranges_for_collect,
                )
                return self.async_show_form(
                    step_id="windows",
                    data_schema=schema,
                    errors={"base": "source_already_in_use"},
                    description_placeholders={"entry_title": existing.title or defaults["entry_title"]},
                )
            windows = [
                {CONF_WINDOW_NAME: w_name or None, CONF_WINDOW_START: s, CONF_WINDOW_END: e, CONF_COST_PER_KWH: cost}
                for s, e in ranges
            ]
            _MAIN_LOGGER.warning(
                "config flow step windows: creating entry title=%r, source=%r, windows=%s",
                entry_title,
                source_entity,
                [w.get(CONF_WINDOW_NAME) for w in windows],
            )
            _MAIN_LOGGER.warning(
                "config: creating entry - title=%r source=%r %s window(s)",
                entry_title,
                source_entity,
                len(windows),
            )
            return self.async_create_entry(
                title=entry_title,
                data={
                    CONF_SOURCES: [
                        {
                            CONF_NAME: source_name,
                            CONF_SOURCE_ENTITY: source_entity,
                            CONF_WINDOWS: windows,
                        }
                    ]
                },
            )

        _MAIN_LOGGER.warning("config flow: showing form step_id=windows")
        schema = _build_single_window_multi_range_schema(
            labels,
            default_name,
            self._initial_window_name,
            self._initial_window_cost,
            self._initial_ranges,
            include_add_another=True,
            include_delete=False,
            num_slots=num_ranges,
        )
        return self.async_show_form(step_id="windows", data_schema=schema, errors=errors)

    async def async_step_configure_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Show Configure Energy Window Tracker (Beta) menu (after first window, before Done)."""
        _MAIN_LOGGER.warning(
            "config flow step configure_menu: user_input=%s",
            "submitted" if user_input is not None else "show menu",
        )
        if user_input is not None:
            next_step = user_input.get("next_step_id")
            _MAIN_LOGGER.warning("config flow step configure_menu: user selected next_step_id=%s", next_step)
            if next_step == "done":
                defaults = await _get_config_defaults(self.hass)
                title = self._pending_entry_title or defaults["entry_title"]
                _MAIN_LOGGER.warning("config flow configure_menu: creating entry title=%r", title)
                return self.async_create_entry(
                    title=title,
                    data={CONF_SOURCES: self._pending_sources or []},
                )
            if next_step in ("add_window", "list_windows", "source_entity"):
                return await getattr(self, f"async_step_{next_step}")(None)
        return self._async_show_configure_menu()

    def _async_show_configure_menu(self) -> config_entries.FlowResult:
        """Show the Configure Energy Window Tracker (Beta) menu (config flow)."""
        _MAIN_LOGGER.warning("config flow: showing menu step_id=configure_menu")
        return {
            "type": data_entry_flow.FlowResultType.MENU,
            "flow_id": self.flow_id,
            "handler": self.handler,
            "step_id": "configure_menu",
            "menu_options": _build_configure_menu_options_with_done(),
            "title": "Configure Energy Window Tracker (Beta)",
        }

    async def async_step_done(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Create entry and finish (from Configure menu Done)."""
        defaults = await _get_config_defaults(self.hass)
        title = self._pending_entry_title or defaults["entry_title"]
        _MAIN_LOGGER.warning("config flow step done: creating entry title=%r", title)
        return self.async_create_entry(
            title=title,
            data={CONF_SOURCES: self._pending_sources or []},
        )

    async def async_step_add_window(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Add a window (config flow, pending entry). One name, one cost, N ranges; Add another for more."""
        _MAIN_LOGGER.warning(
            "config flow step add_window: user_input=%s",
            "submitted" if user_input is not None else "show form",
        )
        self._get_pending_source()
        num_ranges = len(self._pending_add_ranges) + 1
        labels = await _get_window_form_labels(self.hass, "config", "add_window", num_ranges=num_ranges)

        if user_input is not None and "start" in user_input:
            # After "Add another time range" the form has more slots; use that count when collecting
            num_ranges_for_collect = (
                len(self._pending_add_ranges) + 1 if self._pending_add_ranges else max(num_ranges, 1)
            )
            time_errors = _validate_time_fields(user_input, num_ranges_for_collect)
            if time_errors:
                ranges_for_form = [
                    {"start": user_input.get("start") or "00:00", "end": user_input.get("end") or "00:00"}
                ]
                for i in range(1, num_ranges_for_collect):
                    ranges_for_form.append(
                        {
                            "start": user_input.get(f"start_{i}") or "00:00",
                            "end": user_input.get(f"end_{i}") or "00:00",
                        }
                    )
                schema = _build_single_window_multi_range_schema(
                    labels,
                    None,
                    (user_input.get("window_name") or "").strip(),
                    _parse_cost(user_input.get(CONF_COST_PER_KWH)),
                    ranges_for_form,
                    include_add_another=True,
                    include_delete=False,
                    num_slots=num_ranges_for_collect,
                )
                return self.async_show_form(step_id="add_window", data_schema=schema, errors=time_errors)
            w_name, cost, ranges = _collect_ranges_from_single_window_form(
                user_input, num_ranges_for_collect
            )
            if not ranges:
                first_start = _time_to_str(user_input.get("start") or "00:00")
                first_end = _time_to_str(user_input.get("end") or "00:00")
                errors = {"base": "window_start_after_end" if first_start >= first_end else "at_least_one_window"}
                ranges_for_form = [{"start": user_input.get("start") or "00:00", "end": user_input.get("end") or "00:00"}]
                for i in range(1, num_ranges_for_collect):
                    ranges_for_form.append({"start": user_input.get(f"start_{i}") or "00:00", "end": user_input.get(f"end_{i}") or "00:00"})
                schema = _build_single_window_multi_range_schema(
                    labels, None, w_name or "", cost, ranges_for_form, include_add_another=True, include_delete=False,
                    num_slots=num_ranges_for_collect,
                )
                return self.async_show_form(step_id="add_window", data_schema=schema, errors=errors)
            range_error = _validate_ranges_chronological(ranges)
            if range_error:
                errors = {"base": range_error}
                ranges_for_form = [{"start": user_input.get("start") or "00:00", "end": user_input.get("end") or "00:00"}]
                for i in range(1, num_ranges_for_collect):
                    ranges_for_form.append({"start": user_input.get(f"start_{i}") or "00:00", "end": user_input.get(f"end_{i}") or "00:00"})
                schema = _build_single_window_multi_range_schema(
                    labels, None, w_name or "", cost, ranges_for_form, include_add_another=True, include_delete=False,
                    num_slots=num_ranges_for_collect,
                )
                return self.async_show_form(step_id="add_window", data_schema=schema, errors=errors)
            if user_input.get("add_another"):
                _MAIN_LOGGER.warning(
                    "config: add_window - add another time range (total %s)",
                    len(ranges) + 1,
                )
                self._pending_add_name = w_name or ""
                self._pending_add_cost = cost
                self._pending_add_ranges = [{"start": s, "end": e} for s, e in ranges]
                num_ranges = len(self._pending_add_ranges) + 1
                labels = await _get_window_form_labels(self.hass, "config", "add_window", num_ranges=num_ranges)
                schema = _build_single_window_multi_range_schema(
                    labels, None, self._pending_add_name, self._pending_add_cost, self._pending_add_ranges,
                    include_add_another=True, include_delete=False,
                    num_slots=num_ranges,
                )
                return self.async_show_form(step_id="add_window", data_schema=schema)
            if not self._pending_sources:
                return await self.async_step_configure_menu(None)
            name = (w_name or "").strip() or None
            for s, e in ranges:
                self._pending_sources[0].setdefault(CONF_WINDOWS, []).append({
                    CONF_WINDOW_NAME: name,
                    CONF_WINDOW_START: s,
                    CONF_WINDOW_END: e,
                    CONF_COST_PER_KWH: cost,
                })
            self._pending_add_ranges = []
            self._pending_add_name = ""
            self._pending_add_cost = 0.0
            return await self.async_step_configure_menu(None)
        _MAIN_LOGGER.warning("config flow: showing form step_id=add_window")
        schema = _build_single_window_multi_range_schema(
            labels, None, self._pending_add_name, self._pending_add_cost, self._pending_add_ranges,
            include_add_another=True, include_delete=False,
            num_slots=num_ranges,
        )
        return self.async_show_form(step_id="add_window", data_schema=schema)

    async def async_step_manage_windows_empty(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """No windows yet in config flow; submit returns to Configure menu."""
        if user_input is not None:
            return await self.async_step_configure_menu(None)
        return self.async_show_form(
            step_id="manage_windows_empty",
            data_schema=vol.Schema({}),
        )

    async def async_step_list_windows(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage windows list (config flow, pending entry). One option per unique window name."""
        _MAIN_LOGGER.warning(
            "config flow step list_windows: user_input=%s",
            "submitted" if user_input is not None else "show list",
        )
        src = self._get_pending_source()
        windows = _normalize_windows_for_schema(src.get(CONF_WINDOWS) or [])
        if not windows:
            return await self.async_step_manage_windows_empty(None)
        if user_input is not None and "window_index" in user_input:
            raw = user_input.get("window_index")
            idx = int(raw[0] if isinstance(raw, list) else raw, 10)
            unique_names = _unique_window_names(windows)
            if 0 <= idx < len(unique_names):
                self._edit_window_name = unique_names[idx]
                _MAIN_LOGGER.warning("config flow step list_windows: user selected window %r", self._edit_window_name)
            return await self.async_step_edit_window(None)
        unique_names = _unique_window_names(windows)
        options = [{"value": str(i), "label": unique_names[i]} for i in range(len(unique_names))]
        _MAIN_LOGGER.warning("config flow: showing form step_id=list_windows")
        schema = vol.Schema({
            vol.Required("window_index"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=options),
            ),
        })
        return self.async_show_form(step_id="list_windows", data_schema=schema)

    async def async_step_edit_window(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Edit one named window (all its ranges). Config flow, pending entry."""
        _MAIN_LOGGER.warning(
            "config flow step edit_window: edit_name=%r user_input=%s",
            getattr(self, "_edit_window_name", None),
            "submitted" if user_input is not None else "show form",
        )
        src = self._get_pending_source()
        windows = _normalize_windows_for_schema(src.get(CONF_WINDOWS) or [])
        edit_name = self._edit_window_name
        if not edit_name:
            return await self.async_step_configure_menu(None)
        same_name = _windows_matching_edit_name(windows, edit_name)
        if not same_name:
            return await self.async_step_configure_menu(None)
        num_ranges = len(same_name)
        labels = await _get_window_form_labels(self.hass, "config", "edit_window", num_ranges=num_ranges)
        ranges_data = [{"start": _time_to_str(w.get(CONF_WINDOW_START) or ""), "end": _time_to_str(w.get(CONF_WINDOW_END) or "")} for w in same_name]
        cost = 0.0
        if same_name and CONF_COST_PER_KWH in same_name[0] and same_name[0][CONF_COST_PER_KWH] is not None:
            try:
                cost = max(0.0, float(same_name[0][CONF_COST_PER_KWH]))
            except (TypeError, ValueError):
                pass

        if user_input is not None:
            if user_input.get("delete_this_window"):
                raw_to_remove = (same_name[0].get(CONF_WINDOW_NAME) or "").strip()
                new_windows = [w for w in windows if (w.get(CONF_WINDOW_NAME) or "").strip() != raw_to_remove]
                self._pending_sources[0][CONF_WINDOWS] = new_windows
                return await self.async_step_configure_menu(None)
            num_ranges = max(num_ranges, 1)
            time_errors = _validate_time_fields(user_input, num_ranges)
            if time_errors:
                ranges_for_form = [
                    {"start": user_input.get("start") or "00:00", "end": user_input.get("end") or "00:00"}
                ]
                for i in range(1, num_ranges):
                    ranges_for_form.append(
                        {
                            "start": user_input.get(f"start_{i}") or "00:00",
                            "end": user_input.get(f"end_{i}") or "00:00",
                        }
                    )
                schema = _build_single_window_multi_range_schema(
                    labels,
                    None,
                    (user_input.get("window_name") or edit_name or "").strip(),
                    _parse_cost(user_input.get(CONF_COST_PER_KWH)),
                    ranges_for_form,
                    include_add_another=True,
                    include_delete=True,
                    num_slots=num_ranges,
                )
                return self.async_show_form(step_id="edit_window", data_schema=schema, errors=time_errors)
            w_name, cost_val, ranges_list = _collect_ranges_from_single_window_form(user_input, num_ranges)
            if not ranges_list:
                first_start = _time_to_str(user_input.get("start") or "00:00")
                first_end = _time_to_str(user_input.get("end") or "00:00")
                err = "window_start_after_end" if first_start >= first_end else "at_least_one_window"
                schema = _build_single_window_multi_range_schema(
                    labels, None, w_name or "", cost_val,
                    [{"start": user_input.get("start") or "00:00", "end": user_input.get("end") or "00:00"}],
                    include_add_another=True, include_delete=True,
                    num_slots=num_ranges,
                )
                return self.async_show_form(step_id="edit_window", data_schema=schema, errors={"base": err})
            range_error = _validate_ranges_chronological(ranges_list)
            if range_error:
                ranges_for_form = [{"start": user_input.get("start") or "00:00", "end": user_input.get("end") or "00:00"}]
                for i in range(1, num_ranges):
                    ranges_for_form.append({"start": user_input.get(f"start_{i}") or "00:00", "end": user_input.get(f"end_{i}") or "00:00"})
                schema = _build_single_window_multi_range_schema(
                    labels, None, w_name or "", cost_val, ranges_for_form,
                    include_add_another=True, include_delete=True,
                    num_slots=num_ranges,
                )
                return self.async_show_form(step_id="edit_window", data_schema=schema, errors={"base": range_error})
            if user_input.get("add_another"):
                _MAIN_LOGGER.warning(
                    "config: edit_window - add another time range for %r (total %s)",
                    edit_name,
                    len(ranges_list) + 1,
                )
                self._pending_add_name = w_name or ""
                self._pending_add_cost = cost_val
                self._pending_add_ranges = [{"start": s, "end": e} for s, e in ranges_list]
                num_ranges = len(self._pending_add_ranges) + 1
                labels = await _get_window_form_labels(self.hass, "config", "edit_window", num_ranges=num_ranges)
                schema = _build_single_window_multi_range_schema(
                    labels, None, self._pending_add_name, self._pending_add_cost, self._pending_add_ranges,
                    include_add_another=True, include_delete=True,
                    num_slots=num_ranges,
                )
                return self.async_show_form(step_id="edit_window", data_schema=schema)
            name = (w_name or "").strip() or None
            raw_to_replace = (same_name[0].get(CONF_WINDOW_NAME) or "").strip()
            new_windows = _replace_window_group_preserve_order(
                windows, raw_to_replace, name, ranges_list, cost_val
            )
            self._pending_sources[0][CONF_WINDOWS] = new_windows
            return await self.async_step_configure_menu(None)
        _MAIN_LOGGER.warning("config flow: showing form step_id=edit_window")
        schema = _build_single_window_multi_range_schema(
            labels, None, edit_name, cost, ranges_data, include_add_another=True, include_delete=True,
            num_slots=num_ranges,
        )
        return self.async_show_form(step_id="edit_window", data_schema=schema)

    async def async_step_source_entity(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Update energy source (config flow, pending entry)."""
        _MAIN_LOGGER.warning(
            "config flow step source_entity: user_input=%s",
            "submitted" if user_input is not None else "show form",
        )
        if user_input is not None and CONF_SOURCE_ENTITY in user_input:
            new_entity = user_input.get(CONF_SOURCE_ENTITY) or ""
            if new_entity and self._pending_sources:
                defaults = await _get_config_defaults(self.hass)
                name = (user_input.get(CONF_NAME) or "").strip() or _get_entity_friendly_name(
                    self.hass, new_entity, defaults["window_name"]
                )
                self._pending_sources[0][CONF_SOURCE_ENTITY] = new_entity
                self._pending_sources[0][CONF_NAME] = (name or defaults["entry_title"]).strip()[:200]
                if self._pending_entry_title:
                    self._pending_entry_title = self._pending_sources[0][CONF_NAME]
            return await self.async_step_configure_menu(None)
        src = self._get_pending_source()
        source_entity = str(src.get(CONF_SOURCE_ENTITY) or DEFAULT_SOURCE_ENTITY)
        defaults = await _get_config_defaults(self.hass)
        current_name = str(src.get(CONF_NAME) or "") or _get_entity_friendly_name(
            self.hass, source_entity, defaults["window_name"]
        )
        _MAIN_LOGGER.warning("config flow: showing form step_id=source_entity")
        return self.async_show_form(
            step_id="source_entity",
            data_schema=_build_source_entity_schema(source_entity, current_name),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> EnergyWindowOptionsFlow:
        """Get the options flow."""
        return EnergyWindowOptionsFlow(config_entry)


def _get_sources_from_entry(entry: config_entries.ConfigEntry) -> list[dict[str, Any]]:
    """Get list of sources from entry (CONF_SOURCES)."""
    current = {**entry.data, **(entry.options or {})}
    raw = current.get(CONF_SOURCES)
    if isinstance(raw, list):
        out = list(raw)
        _MAIN_LOGGER.warning("_get_sources_from_entry: entry_id=%s len(sources)=%s", entry.entry_id, len(out))
        return out
    _MAIN_LOGGER.warning("_get_sources_from_entry: entry_id=%s no list, returning []", entry.entry_id)
    return []


def _entry_using_source_entity(
    hass: Any,
    source_entity: str,
    exclude_entry_id: str | None = None,
) -> config_entries.ConfigEntry | None:
    """Return the config entry that uses this source entity, or None. Optionally exclude an entry (e.g. current when updating)."""
    if not source_entity:
        return None
    normalized = source_entity.strip()
    if not normalized:
        return None
    for entry in hass.config_entries.async_entries(DOMAIN):
        if exclude_entry_id and entry.entry_id == exclude_entry_id:
            continue
        for src in _get_sources_from_entry(entry):
            if not isinstance(src, dict):
                continue
            existing = str(src.get(CONF_SOURCE_ENTITY) or "").strip()
            if existing and existing == normalized:
                return entry
    return None


def _build_init_menu_options() -> dict[str, str]:
    """Build main menu as step_id -> label (dict so labels show without translation lookup)."""
    return {
        "add_window": "✚ Add new window",
        "list_windows": "✏️ Manage windows",
        "source_entity": "⚡️ Update energy source",
    }


def _build_configure_menu_options_with_done() -> dict[str, str]:
    """Same as init menu plus Done (for config flow after first window)."""
    return {
        **_build_init_menu_options(),
        "done": "Done",
    }


def _unique_window_names(windows: list[dict[str, Any]]) -> list[str]:
    """Unique window names in order of first occurrence; empty name becomes 'Window {n}'."""
    seen: set[str] = set()
    out: list[str] = []
    for i, w in enumerate(windows):
        name = (w.get(CONF_WINDOW_NAME) or "").strip() or f"Window {i + 1}"
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def _windows_matching_edit_name(windows: list[dict[str, Any]], edit_name: str) -> list[dict[str, Any]]:
    """Return windows whose effective display name matches edit_name (same logic as _unique_window_names).
    When user selects 'Window 1' from the list, edit_name is 'Window 1' but stored name may be ''; this
    finds the correct windows to edit."""
    seen: set[str] = set()
    for i, w in enumerate(windows):
        raw = (w.get(CONF_WINDOW_NAME) or "").strip()
        effective = raw or f"Window {i + 1}"
        if effective not in seen:
            seen.add(effective)
            if effective == edit_name:
                return [ww for ww in windows if (ww.get(CONF_WINDOW_NAME) or "").strip() == raw]
    return []


def _replace_window_group_preserve_order(
    windows: list[dict[str, Any]],
    raw_to_replace: str,
    new_name: str | None,
    ranges_list: list[tuple[str, str]],
    cost_per_kwh: float,
) -> list[dict[str, Any]]:
    """Replace all windows matching raw_to_replace, preserving the group's position."""
    target = (raw_to_replace or "").strip()
    replaced = False
    out: list[dict[str, Any]] = []

    for w in windows:
        raw = (w.get(CONF_WINDOW_NAME) or "").strip()
        if raw != target:
            out.append(w)
            continue
        if replaced:
            continue
        for s, e in ranges_list:
            out.append(
                {
                    CONF_WINDOW_NAME: new_name,
                    CONF_WINDOW_START: s,
                    CONF_WINDOW_END: e,
                    CONF_COST_PER_KWH: cost_per_kwh,
                }
            )
        replaced = True

    if not replaced:
        for s, e in ranges_list:
            out.append(
                {
                    CONF_WINDOW_NAME: new_name,
                    CONF_WINDOW_START: s,
                    CONF_WINDOW_END: e,
                    CONF_COST_PER_KWH: cost_per_kwh,
                }
            )
    return out


def _window_display_name(w: dict[str, Any], index: int, fallback_template: str) -> str:
    """Display name for a window (for list/dropdown labels)."""
    name = (w.get(CONF_WINDOW_NAME) or "").strip()
    return name or fallback_template.format(n=index + 1)


def _build_select_window_schema(
    windows: list[dict[str, Any]], fallback_template: str
) -> vol.Schema:
    """Build schema for 'select a window' form: one dropdown, then user is taken to edit that window."""
    options = [
        {"value": str(i), "label": _window_display_name(w, i, fallback_template)}
        for i, w in enumerate(windows)
    ]
    return vol.Schema(
        {
            vol.Required("window_index"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=options),
            ),
        }
    )


def _build_source_entity_schema(
    source_entity: str,
    current_source_name: str = "",
    include_remove_previous: bool = False,
) -> vol.Schema:
    """Build schema for changing the source entity and optional source name."""
    schema_dict: dict[Any, Any] = {
        vol.Required(
            CONF_SOURCE_ENTITY,
            default=source_entity or DEFAULT_SOURCE_ENTITY,
        ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
        vol.Optional(CONF_NAME, default=current_source_name or ""): str,
    }
    if include_remove_previous:
        schema_dict[vol.Optional("remove_previous_entities", default=False)] = bool
    return vol.Schema(schema_dict)


def _get_start_end_from_input(user_input: dict[str, Any]) -> tuple[str, str]:
    """Get start and end time strings from form input (keys 'start'/'end')."""
    start = _time_to_str(user_input.get("start") or "00:00")
    end = _time_to_str(user_input.get("end") or "00:00")
    return start, end


def _build_single_window_schema(
    window: dict[str, Any] | None = None,
    include_delete: bool = False,
) -> vol.Schema:
    """Build schema for add/edit single window. include_delete=True adds 'Delete this window' (edit only)."""
    w = window or {}
    name_val = str(w.get(CONF_WINDOW_NAME, ""))[:200]
    start_val = _time_to_str(w.get(CONF_WINDOW_START) or DEFAULT_WINDOW_START)
    end_val = _time_to_str(w.get(CONF_WINDOW_END) or DEFAULT_WINDOW_END)
    cost_val = 0.0
    if CONF_COST_PER_KWH in w and w[CONF_COST_PER_KWH] is not None:
        try:
            cost_val = max(0.0, float(w[CONF_COST_PER_KWH]))
        except (TypeError, ValueError):
            pass
    schema_dict: dict[Any, Any] = {
        vol.Optional(CONF_WINDOW_NAME, default=name_val): str,
        vol.Optional("start", default=start_val): selector.TimeSelector(),
        vol.Optional("end", default=end_val): selector.TimeSelector(),
        vol.Optional(
            CONF_COST_PER_KWH,
            default=cost_val,
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=0.001, mode="box")
        ),
    }
    if include_delete:
        schema_dict[vol.Optional("delete_this_window", default=False)] = bool
    return vol.Schema(schema_dict)


class EnergyWindowOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow: Configure Energy Window Tracker (Beta) — add/edit/delete windows, change source."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        super().__init__()
        self._config_entry = config_entry
        self._edit_index: int = 0
        self._edit_window_name: str | None = None
        self._delete_index: int = -1
        self._pending_add_name: str = ""
        self._pending_add_cost: float = 0.0
        self._pending_add_ranges: list[dict[str, str]] = []

    def _get_current_source(self) -> dict[str, Any]:
        """Get current source from entry."""
        sources = _get_sources_from_entry(self._config_entry)
        if not sources or not isinstance(sources[0], dict):
            raise ValueError("No source configured")
        return sources[0]

    async def _save_source(
        self,
        source_entity: str,
        windows: list[dict[str, Any]],
        source_name: str | None = None,
    ) -> dict[str, Any]:
        """Build and return the new options dict. Do not update or reload here.
        Callers return this via _async_create_options_entry so the flow result
        includes both 'data' and 'options' for reliable persistence.
        """
        if source_name is None or not source_name.strip():
            source_name = _get_entity_friendly_name(self.hass, source_entity)
        else:
            source_name = source_name.strip()[:200]
        new_source = {
            CONF_NAME: source_name,
            CONF_SOURCE_ENTITY: source_entity,
            CONF_WINDOWS: windows,
        }
        # Merge with existing options so we don't drop other keys (e.g. _retain_entity_unique_ids)
        new_options = {**(self._config_entry.options or {}), CONF_SOURCES: [new_source]}
        _MAIN_LOGGER.warning(
            "options flow: built options entry_id=%s source_entity=%r windows=%s",
            self._config_entry.entry_id,
            source_entity,
            [w.get(CONF_WINDOW_NAME) for w in windows],
        )
        return new_options

    def _async_create_options_entry(self, options: dict[str, Any]) -> config_entries.FlowResult:
        """Return a CreateEntry result with both data and options set.
        Some HA versions expect 'options' in the result for options flow persistence.
        """
        result = self.async_create_entry(title=None, data=options)
        result["options"] = options
        _MAIN_LOGGER.warning(
            "options flow: returning CreateEntry with data and options (entry_id=%s)",
            self._config_entry.entry_id,
        )
        return result

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Configure Energy Window Tracker (Beta): show menu (Add new window, Manage windows, Update energy source)."""
        _MAIN_LOGGER.warning(
            "options flow opened (entry_id=%s); enable debug for this integration to see step details",
            self._config_entry.entry_id,
        )
        try:
            return await self._async_step_manage_impl(user_input)
        except Exception as err:
            _MAIN_LOGGER.warning(
                "Energy Window Tracker (Beta) options flow failed: %s",
                err,
                exc_info=True,
            )
            raise

    def _async_show_menu(
        self,
        step_id: str,
        menu_options: list[str] | dict[str, str],
        description_placeholders: dict[str, str] | None = None,
        description: str | None = None,
        title: str | None = None,
    ) -> config_entries.FlowResult:
        """Show a menu step. menu_options: list of step_ids or dict step_id->label. Optional description/title override translation."""
        _MAIN_LOGGER.warning("options flow: showing menu step_id=%s", step_id)
        result: config_entries.FlowResult = {
            "type": data_entry_flow.FlowResultType.MENU,
            "flow_id": self.flow_id,
            "handler": self.handler,
            "step_id": step_id,
            "menu_options": menu_options,
        }
        if description_placeholders:
            result["description_placeholders"] = description_placeholders
        if description is not None:
            result["description"] = description
        if title is not None:
            result["title"] = title
        return result

    async def _async_step_manage_impl(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Show Configure Energy Window Tracker (Beta) menu."""
        _MAIN_LOGGER.warning("options flow step init: showing main menu")
        self._get_current_source()
        menu_options = _build_init_menu_options()
        return self._async_show_menu(
            step_id="init",
            menu_options=menu_options,
            description_placeholders={"windows_list": ""},
            title="Configure Energy Window Tracker (Beta)",
        )

    async def _async_step_manage_windows_impl(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Show Manage windows: one option per unique window name; select then edit that name's ranges."""
        _MAIN_LOGGER.warning(
            "options flow step manage_windows: user_input=%s",
            "submitted" if user_input is not None else "show list",
        )
        src = self._get_current_source()
        windows = _normalize_windows_for_schema(src.get(CONF_WINDOWS) or [])
        if not windows:
            if user_input is not None:
                return await self._async_step_manage_impl(None)
            _MAIN_LOGGER.warning("options flow: showing form step_id=manage_windows_empty")
            return self.async_show_form(
                step_id="manage_windows_empty",
                data_schema=vol.Schema({}),
            )
        if user_input is not None:
            raw = user_input.get("window_index")
            idx = int(raw[0] if isinstance(raw, list) else raw, 10)
            unique_names = _unique_window_names(windows)
            if 0 <= idx < len(unique_names):
                self._edit_window_name = unique_names[idx]
                _MAIN_LOGGER.warning("options flow step manage_windows: user selected window %r", self._edit_window_name)
            return await self.async_step_edit_window(None)
        unique_names = _unique_window_names(windows)
        options = [{"value": str(i), "label": unique_names[i]} for i in range(len(unique_names))]
        _MAIN_LOGGER.warning("options flow: showing form step_id=manage_windows (%s windows)", len(unique_names))
        schema = vol.Schema({
            vol.Required("window_index"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=options),
            ),
        })
        return self.async_show_form(step_id="manage_windows", data_schema=schema)

    async def async_step_list_windows(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Entry from main menu (menu option 'Manage windows'): show list or empty state."""
        return await self._async_step_manage_windows_impl(user_input)

    async def async_step_manage_windows_empty(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """No windows yet; submit returns to menu."""
        if user_input is not None:
            return await self._async_step_manage_impl(None)
        return self.async_show_form(
            step_id="manage_windows_empty",
            data_schema=vol.Schema({}),
        )

    async def async_step_manage_windows(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Show Manage windows list or empty state (e.g. when returning from edit/delete)."""
        return await self._async_step_manage_windows_impl(user_input)

    async def async_step_confirm_delete(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Confirm deletion of the window at _delete_index, then return to menu."""
        _MAIN_LOGGER.warning(
            "options: confirm_delete - %s",
            "confirmed" if user_input is not None else "show form",
        )
        _MAIN_LOGGER.warning(
            "options flow step confirm_delete: user_input=%s",
            "confirmed" if user_input is not None else "show confirm",
        )
        src = self._get_current_source()
        source_entity = str(src.get(CONF_SOURCE_ENTITY) or DEFAULT_SOURCE_ENTITY)
        windows = _normalize_windows_for_schema(src.get(CONF_WINDOWS) or [])
        idx = self._delete_index
        if idx < 0 or idx >= len(windows):
            return await self._async_step_manage_windows_impl(None)
        window_name = (windows[idx].get(CONF_WINDOW_NAME) or "").strip() or f"Window {idx + 1}"
        if user_input is not None:
            _MAIN_LOGGER.warning("options: window deleted - %r", window_name)
            _MAIN_LOGGER.warning("options flow step confirm_delete: deleting window %r", window_name)
            new_windows = [w for i, w in enumerate(windows) if i != idx]
            current_name = src.get(CONF_NAME) or None
            options_to_persist = await self._save_source(source_entity, new_windows, source_name=current_name)
            unique_id = f"{self._config_entry.entry_id}_{source_slug_from_entity_id(source_entity)}_{idx}"
            registry = er.async_get(self.hass)
            if entity_id := registry.async_get_entity_id("sensor", DOMAIN, unique_id):
                registry.async_remove(entity_id)
            return self._async_create_options_entry(options_to_persist)
        _MAIN_LOGGER.warning("options flow: showing form step_id=confirm_delete")
        return self.async_show_form(
            step_id="confirm_delete",
            data_schema=vol.Schema({}),
            description_placeholders={"window_name": window_name},
        )

    async def async_step_source_entity_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Redirect to source_entity form (no separate confirm step)."""
        return await self.async_step_source_entity(None)

    async def async_step_source_entity(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Change the source entity (form). Checkbox controls whether to remove previous entities."""
        _MAIN_LOGGER.warning(
            "options flow step source_entity: user_input=%s",
            "submitted" if user_input is not None else "show form",
        )
        src = self._get_current_source()
        source_entity = str(src.get(CONF_SOURCE_ENTITY) or DEFAULT_SOURCE_ENTITY)
        windows = _normalize_windows_for_schema(src.get(CONF_WINDOWS) or [])
        defaults = await _get_config_defaults(self.hass)
        current_name = str(src.get(CONF_NAME) or "") or _get_entity_friendly_name(
            self.hass, source_entity, defaults["window_name"]
        )

        if user_input is not None and CONF_SOURCE_ENTITY in user_input:
            new_entity = _normalize_entity_selector_value(
                user_input.get(CONF_SOURCE_ENTITY)
            ) or source_entity
            if not new_entity:
                return self.async_show_form(
                    step_id="source_entity",
                    data_schema=_build_source_entity_schema(
                        source_entity, current_name, include_remove_previous=True
                    ),
                )
            existing_entry = _entry_using_source_entity(
                self.hass, new_entity, exclude_entry_id=self._config_entry.entry_id
            )
            if existing_entry is not None:
                return self.async_show_form(
                    step_id="source_entity",
                    data_schema=_build_source_entity_schema(
                        source_entity, current_name, include_remove_previous=True
                    ),
                    errors={"base": "source_already_in_use"},
                    description_placeholders={
                        "entry_title": existing_entry.title or defaults["entry_title"]
                    },
                )
            remove_previous = bool(user_input.get("remove_previous_entities"))
            current_normalized = _normalize_entity_selector_value(source_entity) or source_entity
            if remove_previous and new_entity == current_normalized:
                return self.async_show_form(
                    step_id="source_entity",
                    data_schema=_build_source_entity_schema(
                        source_entity, current_name, include_remove_previous=True
                    ),
                    errors={"base": "remove_previous_but_source_unchanged"},
                )
            custom_name = (user_input.get(CONF_NAME) or "").strip()
            source_name = custom_name or _get_entity_friendly_name(
                self.hass, new_entity, defaults["window_name"]
            )

            if remove_previous:
                registry = er.async_get(self.hass)
                for entity_entry in registry.entities.get_entries_for_config_entry_id(
                    self._config_entry.entry_id
                ):
                    if entity_entry.domain == "sensor" and entity_entry.platform == DOMAIN:
                        registry.async_remove(entity_entry.entity_id)
            else:
                registry = er.async_get(self.hass)
                retain_ids = []
                for entity_entry in registry.entities.get_entries_for_config_entry_id(
                    self._config_entry.entry_id
                ):
                    if entity_entry.domain == "sensor" and entity_entry.platform == DOMAIN:
                        retain_ids.append(entity_entry.unique_id)
                self._retain_ids_after_save = retain_ids

            store = Store(
                self.hass,
                STORAGE_VERSION,
                f"{STORAGE_KEY}_{self._config_entry.entry_id}_{source_slug_from_entity_id(source_entity)}",
            )
            await store.async_save({})

            options_to_persist = await self._save_source(new_entity, windows, source_name=source_name)
            if getattr(self, "_retain_ids_after_save", None) is not None:
                options_to_persist = {**options_to_persist, "_retain_entity_unique_ids": self._retain_ids_after_save}
                del self._retain_ids_after_save
            return self._async_create_options_entry(options_to_persist)

        _MAIN_LOGGER.warning("options flow: showing form step_id=source_entity")
        return self.async_show_form(
            step_id="source_entity",
            data_schema=_build_source_entity_schema(
                source_entity, current_name, include_remove_previous=True
            ),
        )

    async def async_step_add_window(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Add a new window: one name, one cost, N ranges; Add another for more."""
        _MAIN_LOGGER.warning(
            "options flow step add_window: user_input=%s",
            "submitted" if user_input is not None else "show form",
        )
        src = self._get_current_source()
        source_entity = str(src.get(CONF_SOURCE_ENTITY) or DEFAULT_SOURCE_ENTITY)
        windows = _normalize_windows_for_schema(src.get(CONF_WINDOWS) or [])
        num_ranges = len(self._pending_add_ranges) + 1
        labels = await _get_window_form_labels(self.hass, "options", "add_window", num_ranges=num_ranges)

        if user_input is not None and "start" in user_input:
            _MAIN_LOGGER.warning(
                "options: add_window - form submitted (ranges=%s, add_another=%s)",
                num_ranges,
                bool(user_input.get("add_another")),
            )
            time_errors = _validate_time_fields(user_input, num_ranges)
            if time_errors:
                ranges_for_form = [
                    {"start": user_input.get("start") or "00:00", "end": user_input.get("end") or "00:00"}
                ]
                for i in range(1, num_ranges):
                    ranges_for_form.append(
                        {
                            "start": user_input.get(f"start_{i}") or "00:00",
                            "end": user_input.get(f"end_{i}") or "00:00",
                        }
                    )
                schema = _build_single_window_multi_range_schema(
                    labels,
                    None,
                    (user_input.get("window_name") or "").strip(),
                    _parse_cost(user_input.get(CONF_COST_PER_KWH)),
                    ranges_for_form,
                    include_add_another=True,
                    include_delete=False,
                    num_slots=num_ranges,
                )
                return self.async_show_form(step_id="add_window", data_schema=schema, errors=time_errors)
            w_name, cost, ranges_list = _collect_ranges_from_single_window_form(user_input, num_ranges)
            if not ranges_list:
                first_start = _time_to_str(user_input.get("start") or "00:00")
                first_end = _time_to_str(user_input.get("end") or "00:00")
                err = "window_start_after_end" if first_start >= first_end else "at_least_one_window"
                ranges_for_form = [{"start": user_input.get("start") or "00:00", "end": user_input.get("end") or "00:00"}]
                for i in range(1, num_ranges):
                    ranges_for_form.append({"start": user_input.get(f"start_{i}") or "00:00", "end": user_input.get(f"end_{i}") or "00:00"})
                schema = _build_single_window_multi_range_schema(
                    labels, None, w_name or "", cost, ranges_for_form, include_add_another=True, include_delete=False,
                    num_slots=num_ranges,
                )
                return self.async_show_form(step_id="add_window", data_schema=schema, errors={"base": err})
            range_error = _validate_ranges_chronological(ranges_list)
            if range_error:
                ranges_for_form = [{"start": user_input.get("start") or "00:00", "end": user_input.get("end") or "00:00"}]
                for i in range(1, num_ranges):
                    ranges_for_form.append({"start": user_input.get(f"start_{i}") or "00:00", "end": user_input.get(f"end_{i}") or "00:00"})
                schema = _build_single_window_multi_range_schema(
                    labels, None, w_name or "", cost, ranges_for_form, include_add_another=True, include_delete=False,
                    num_slots=num_ranges,
                )
                return self.async_show_form(step_id="add_window", data_schema=schema, errors={"base": range_error})
            if user_input.get("add_another"):
                _MAIN_LOGGER.warning(
                    "options: add_window - add another time range (total %s)",
                    len(ranges_list) + 1,
                )
                self._pending_add_name = w_name or ""
                self._pending_add_cost = cost
                self._pending_add_ranges = [{"start": s, "end": e} for s, e in ranges_list]
                num_ranges = len(self._pending_add_ranges) + 1
                labels = await _get_window_form_labels(self.hass, "options", "add_window", num_ranges=num_ranges)
                schema = _build_single_window_multi_range_schema(
                    labels, None, self._pending_add_name, self._pending_add_cost, self._pending_add_ranges,
                    include_add_another=True, include_delete=False,
                    num_slots=num_ranges,
                )
                return self.async_show_form(step_id="add_window", data_schema=schema)
            name = (w_name or "").strip() or None
            for s, e in ranges_list:
                windows.append({
                    CONF_WINDOW_START: s,
                    CONF_WINDOW_END: e,
                    CONF_WINDOW_NAME: name,
                    CONF_COST_PER_KWH: cost,
                })
            current_name = src.get(CONF_NAME) or None
            options_to_persist = await self._save_source(source_entity, windows, source_name=current_name)
            self._pending_add_ranges = []
            self._pending_add_name = ""
            self._pending_add_cost = 0.0
            _MAIN_LOGGER.warning("options flow step add_window: saved new window, %s total", len(windows))
            return self._async_create_options_entry(options_to_persist)

        _MAIN_LOGGER.warning("options flow: showing form step_id=add_window")
        schema = _build_single_window_multi_range_schema(
            labels, None, self._pending_add_name, self._pending_add_cost, self._pending_add_ranges,
            include_add_another=True, include_delete=False,
            num_slots=num_ranges,
        )
        return self.async_show_form(step_id="add_window", data_schema=schema)

    async def async_step_edit_window(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Edit one named window (all its ranges). One name, one cost, N ranges; Add another for more."""
        _MAIN_LOGGER.warning(
            "options flow step edit_window: edit_name=%r user_input=%s",
            getattr(self, "_edit_window_name", None),
            "submitted" if user_input is not None else "show form",
        )
        src = self._get_current_source()
        source_entity = str(src.get(CONF_SOURCE_ENTITY) or DEFAULT_SOURCE_ENTITY)
        windows = _normalize_windows_for_schema(src.get(CONF_WINDOWS) or [])
        edit_name = self._edit_window_name
        if not edit_name:
            return await self._async_step_manage_windows_impl(None)
        same_name = _windows_matching_edit_name(windows, edit_name)
        if not same_name:
            return await self._async_step_manage_windows_impl(None)
        num_ranges = len(same_name)
        labels = await _get_window_form_labels(self.hass, "options", "edit_window", num_ranges=num_ranges)
        ranges_data = [{"start": _time_to_str(w.get(CONF_WINDOW_START) or ""), "end": _time_to_str(w.get(CONF_WINDOW_END) or "")} for w in same_name]
        cost = 0.0
        if same_name and CONF_COST_PER_KWH in same_name[0] and same_name[0][CONF_COST_PER_KWH] is not None:
            try:
                cost = max(0.0, float(same_name[0][CONF_COST_PER_KWH]))
            except (TypeError, ValueError):
                pass

        if user_input is not None:
            _MAIN_LOGGER.warning(
                "options: edit_window - form submitted (window=%r, add_another=%s)",
                edit_name,
                bool(user_input.get("add_another")),
            )
            if user_input.get("delete_this_window"):
                _MAIN_LOGGER.warning("options: edit_window - deleting window %r", edit_name)
                _MAIN_LOGGER.warning("options flow step edit_window: user chose delete_this_window")
                self._delete_index = -1
                raw_to_remove = (same_name[0].get(CONF_WINDOW_NAME) or "").strip()
                new_windows = [w for w in windows if (w.get(CONF_WINDOW_NAME) or "").strip() != raw_to_remove]
                current_name = src.get(CONF_NAME) or None
                options_to_persist = await self._save_source(source_entity, new_windows, source_name=current_name)
                return self._async_create_options_entry(options_to_persist)
            # After "Add another time range" the form has more slots; use that count when collecting
            num_ranges_for_collect = (
                len(self._pending_add_ranges) + 1 if self._pending_add_ranges else max(num_ranges, 1)
            )
            time_errors = _validate_time_fields(user_input, num_ranges_for_collect)
            if time_errors:
                ranges_for_form = [
                    {"start": user_input.get("start") or "00:00", "end": user_input.get("end") or "00:00"}
                ]
                for i in range(1, num_ranges_for_collect):
                    ranges_for_form.append(
                        {
                            "start": user_input.get(f"start_{i}") or "00:00",
                            "end": user_input.get(f"end_{i}") or "00:00",
                        }
                    )
                err_labels = await _get_window_form_labels(
                    self.hass, "options", "edit_window", num_ranges=num_ranges_for_collect
                )
                schema = _build_single_window_multi_range_schema(
                    err_labels,
                    None,
                    (user_input.get("window_name") or edit_name or "").strip(),
                    _parse_cost(user_input.get(CONF_COST_PER_KWH)),
                    ranges_for_form,
                    include_add_another=True,
                    include_delete=True,
                    num_slots=num_ranges_for_collect,
                )
                return self.async_show_form(step_id="edit_window", data_schema=schema, errors=time_errors)
            w_name, cost_val, ranges_list = _collect_ranges_from_single_window_form(
                user_input, num_ranges_for_collect
            )
            if not ranges_list:
                first_start = _time_to_str(user_input.get("start") or "00:00")
                first_end = _time_to_str(user_input.get("end") or "00:00")
                err = "window_start_after_end" if first_start >= first_end else "at_least_one_window"
                ranges_for_form = [{"start": user_input.get("start") or "00:00", "end": user_input.get("end") or "00:00"}]
                for i in range(1, num_ranges_for_collect):
                    ranges_for_form.append({
                        "start": user_input.get(f"start_{i}") or "00:00",
                        "end": user_input.get(f"end_{i}") or "00:00",
                    })
                err_labels = await _get_window_form_labels(
                    self.hass, "options", "edit_window", num_ranges=num_ranges_for_collect
                )
                schema = _build_single_window_multi_range_schema(
                    err_labels, None, w_name or "", cost_val,
                    ranges_for_form,
                    include_add_another=True, include_delete=True,
                    num_slots=num_ranges_for_collect,
                )
                return self.async_show_form(step_id="edit_window", data_schema=schema, errors={"base": err})
            range_error = _validate_ranges_chronological(ranges_list)
            if range_error:
                ranges_for_form = [{"start": user_input.get("start") or "00:00", "end": user_input.get("end") or "00:00"}]
                for i in range(1, num_ranges_for_collect):
                    ranges_for_form.append({
                        "start": user_input.get(f"start_{i}") or "00:00",
                        "end": user_input.get(f"end_{i}") or "00:00",
                    })
                err_labels = await _get_window_form_labels(
                    self.hass, "options", "edit_window", num_ranges=num_ranges_for_collect
                )
                schema = _build_single_window_multi_range_schema(
                    err_labels, None, w_name or "", cost_val,
                    ranges_for_form,
                    include_add_another=True, include_delete=True,
                    num_slots=num_ranges_for_collect,
                )
                return self.async_show_form(step_id="edit_window", data_schema=schema, errors={"base": range_error})
            if user_input.get("add_another"):
                _MAIN_LOGGER.warning(
                    "options: edit_window - add another time range for %r (total %s)",
                    edit_name,
                    len(ranges_list) + 1,
                )
                self._pending_add_name = w_name or ""
                self._pending_add_cost = cost_val
                self._pending_add_ranges = [{"start": s, "end": e} for s, e in ranges_list]
                num_ranges = len(self._pending_add_ranges) + 1
                labels = await _get_window_form_labels(self.hass, "options", "edit_window", num_ranges=num_ranges)
                schema = _build_single_window_multi_range_schema(
                    labels, None, self._pending_add_name, self._pending_add_cost, self._pending_add_ranges,
                    include_add_another=True, include_delete=True,
                    num_slots=num_ranges,
                )
                return self.async_show_form(step_id="edit_window", data_schema=schema)
            name = (w_name or "").strip() or None
            raw_to_replace = (same_name[0].get(CONF_WINDOW_NAME) or "").strip()
            new_windows = _replace_window_group_preserve_order(
                windows, raw_to_replace, name, ranges_list, cost_val
            )
            current_name = src.get(CONF_NAME) or None
            options_to_persist = await self._save_source(source_entity, new_windows, source_name=current_name)
            self._pending_add_ranges = []
            self._pending_add_name = ""
            self._pending_add_cost = 0.0
            _MAIN_LOGGER.warning(
                "options flow step edit_window: saved window %r with %s time range(s)",
                edit_name,
                len(ranges_list),
            )
            return self._async_create_options_entry(options_to_persist)

        _MAIN_LOGGER.warning("options flow: showing form step_id=edit_window")
        schema = _build_single_window_multi_range_schema(
            labels, None, edit_name, cost, ranges_data, include_add_another=True, include_delete=True,
            num_slots=num_ranges,
        )
        return self.async_show_form(step_id="edit_window", data_schema=schema)
