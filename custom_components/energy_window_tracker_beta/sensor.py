"""Sensor platform for Energy Window Tracker."""

from __future__ import annotations

import hashlib
import logging
import re
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_COST,
    ATTR_SOURCE_ENTITY,
    ATTR_STATUS,
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
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
    source_slug_from_entity_id,
)

_MAIN_LOGGER = logging.getLogger("custom_components.energy_window_tracker_beta")

_RE_NON_SLUG = re.compile(r"[^a-z0-9_]+")


def _window_slug(window_name: str) -> str:
    """Make a stable slug for a window name (unique_id component)."""
    base = (window_name or "").strip().lower().replace(" ", "_")
    base = _RE_NON_SLUG.sub("_", base).strip("_")
    return (base or "window")[:48]


def _stable_window_unique_id(entry_id: str, source_slug: str, window_name: str) -> str:
    """Stable unique_id for a window sensor.

    Includes a short hash to avoid collisions when different names slugify the same.
    """
    slug = _window_slug(window_name)
    h = hashlib.md5(
        (window_name or "").encode("utf-8"), usedforsecurity=False
    ).hexdigest()[:8]
    return f"{entry_id}_{source_slug}_{slug}_{h}"


def _window_name_from_original_name(original_name: str, source_slug: str) -> str:
    """Best-effort extraction of window name from entity registry original_name.

    Older versions used name formats like "{source_slug} {window_name}" during setup,
    so entity registry original_name may include the source slug prefix.
    """
    name = (original_name or "").strip()
    prefix = f"{(source_slug or '').strip()} "
    if prefix.strip() and name.startswith(prefix):
        return name[len(prefix) :].strip()
    return name


@dataclass
class WindowConfig:
    """Configuration for a single window."""

    start_h: int
    start_m: int
    end_h: int
    end_m: int
    name: str
    index: int
    cost_per_kwh: float = 0.0


@dataclass
class WindowSnapshots:
    """Snapshot data for a single window."""

    snapshot_start: float | None
    snapshot_end: float | None


def _parse_hhmm(time_str: str) -> tuple[int, int]:
    """Parse 'HH:MM' or 'HH:MM:SS' into (hour, minute)."""
    parts = str(time_str).split(":")
    return int(parts[0]), int(parts[1])


def _parse_hhmm_safe(
    time_value: Any,
    fallback: str,
    window_name: str,
    which: str,
    range_index: int,
) -> tuple[int, int, str | None]:
    """Parse a time; on error/out-of-range, return fallback and a warning message."""
    raw = "" if time_value is None else str(time_value)
    s = raw.strip()
    if s.count(":") >= 2:
        s = s.rsplit(":", 1)[0]
    try:
        h, m = _parse_hhmm(s)
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h, m, None
    except (TypeError, ValueError, IndexError):
        pass
    # fallback is expected valid (HH:MM)
    fh, fm = _parse_hhmm(fallback)
    return (
        fh,
        fm,
        f"Invalid {which} time {raw!r} for {window_name} (range {range_index}); used {fallback}",
    )

def _time_str(h: int, m: int) -> str:
    """Format hour and minute as HH:MM."""
    return f"{h:02d}:{m:02d}"


def _parse_windows(config: dict[str, Any]) -> tuple[list[WindowConfig], dict[str, list[str]]]:
    """Parse window config from entry data."""
    windows_data = config.get(CONF_WINDOWS) or []
    _MAIN_LOGGER.warning("_parse_windows: len(windows_data)=%s", len(windows_data))
    windows: list[WindowConfig] = []
    warnings_by_name: dict[str, list[str]] = {}
    for i, p in enumerate(windows_data):
        name = p.get(CONF_WINDOW_NAME) or f"Window {i + 1}"
        start_h, start_m, w1 = _parse_hhmm_safe(
            p.get(CONF_WINDOW_START) or "11:00",
            "11:00",
            name,
            "start",
            i + 1,
        )
        end_h, end_m, w2 = _parse_hhmm_safe(
            p.get(CONF_WINDOW_END) or "14:00",
            "14:00",
            name,
            "end",
            i + 1,
        )
        if w1:
            warnings_by_name.setdefault(name, []).append(w1)
        if w2:
            warnings_by_name.setdefault(name, []).append(w2)
        cost_per_kwh = 0.0
        if CONF_COST_PER_KWH in p and p[CONF_COST_PER_KWH] is not None:
            try:
                cost_per_kwh = max(0.0, float(p[CONF_COST_PER_KWH]))
            except (TypeError, ValueError):
                pass
        windows.append(
            WindowConfig(
                start_h=start_h,
                start_m=start_m,
                end_h=end_h,
                end_m=end_m,
                name=name,
                index=i,
                cost_per_kwh=cost_per_kwh,
            )
        )
    return windows, warnings_by_name


class WindowData:
    """Shared snapshot data and time handlers for all window sensors."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        source_entity: str,
        windows: list[WindowConfig],
        store: Store,
        tz: datetime.tzinfo | None = None,
        config_warnings_by_name: dict[str, list[str]] | None = None,
    ) -> None:
        self.hass = hass
        self._entry_id = entry_id
        self._source_entity = source_entity
        self._windows = windows
        self._store = store
        self._tz = tz or dt_util.get_default_time_zone()
        self._config_warnings_by_name = config_warnings_by_name or {}
        self._snapshots: dict[int, WindowSnapshots] = {
            w.index: WindowSnapshots(snapshot_start=None, snapshot_end=None)
            for w in windows
        }
        self._snapshot_date: str | None = None
        self._update_callbacks: list[callback] = []

    def _now(self) -> datetime:
        """Current time in the integration timezone (HA config time_zone)."""
        return dt_util.now(self._tz)

    def add_update_callback(self, cb: callback) -> None:
        """Register a callback to run when snapshots change."""
        self._update_callbacks.append(cb)

    def _notify_update(self) -> None:
        """Notify all sensors to update."""
        for cb in self._update_callbacks:
            cb()

    def get_source_value(self) -> float | None:
        """Get current source entity value."""
        state = self.hass.states.get(self._source_entity)
        if state is None or state.state in ("unknown", "unavailable"):
            return None
        try:
            return float(state.state)
        except (ValueError, TypeError):
            _MAIN_LOGGER.warning(
                "sensor: get_source_value - %s state not numeric: %r",
                self._source_entity,
                state.state if state else None,
            )
            return None

    def _snapshots_valid_today(self) -> bool:
        """Return True if stored snapshots are from today (invalid for 'today' sources otherwise).

        Uses HA config timezone so 'today' matches the frontend date.
        """
        if not self._snapshot_date:
            return False
        return self._snapshot_date == self._now().date().isoformat()

    def get_window_value(self, window: WindowConfig) -> tuple[float | None, str]:
        """Get energy value and status for a window (same-day only; start < end).

        All times use the HA config timezone: window start/end and "now" are in
        local time, so 11:00–14:00 means 11am–2pm local.
        """
        total = self.get_source_value()
        now = self._now()
        current_minutes = now.hour * 60 + now.minute
        if not self._snapshots_valid_today():
            snap = WindowSnapshots(None, None)
        else:
            snap = self._snapshots.get(window.index) or WindowSnapshots(None, None)
        start_min = window.start_h * 60 + window.start_m
        end_min = window.end_h * 60 + window.end_m
        in_window = start_min <= current_minutes < end_min
        window_ended = current_minutes >= end_min

        if total is None:
            return None, "unavailable"

        if not in_window and not window_ended:
            return 0.0, "before_window"
        if in_window:
            if snap and snap.snapshot_start is not None:
                value = max(0.0, total - snap.snapshot_start)
                return round(value, 3), "during_window"
            return 0.0, "during_window (no snapshot)"
        if (
            window_ended
            and snap
            and snap.snapshot_start is not None
            and snap.snapshot_end is not None
        ):
            value = max(0.0, snap.snapshot_end - snap.snapshot_start)
            return round(value, 3), "after_window"
        if window_ended and snap and snap.snapshot_start is not None:
            return max(
                0.0, total - snap.snapshot_start
            ), "after_window (missing end snapshot)"
        return 0.0, "after_window (no snapshots)"

    def take_late_start_snapshot(self, window_index: int) -> bool:
        """If we're during the window with no start snapshot, use 0 as baseline so the window shows current total.

        (Using current value as baseline would zero the display until more energy is used.)
        """
        if self.get_source_value() is None:
            return False
        snap = self._snapshots.get(window_index) or WindowSnapshots(None, None)
        if snap.snapshot_start is not None:
            return False
        now = self._now()
        current_minutes = now.hour * 60 + now.minute
        for w in self._windows:
            if w.index != window_index:
                continue
            start_min = w.start_h * 60 + w.start_m
            end_min = w.end_h * 60 + w.end_m
            in_window = start_min <= current_minutes < end_min
            if not in_window:
                return False
            if not self._snapshot_date:
                self._snapshot_date = self._now().date().isoformat()
            self._snapshots[window_index] = WindowSnapshots(
                snapshot_start=0.0,
                snapshot_end=None,
            )
            self._schedule_save()
            return True
        return False

    async def load(self) -> None:
        """Load snapshots from storage. Discard if snapshot_date is not today (e.g. after restart)."""
        stored = await self._store.async_load()
        today = self._now().date().isoformat()
        if stored:
            self._snapshot_date = stored.get("snapshot_date")
            if self._snapshot_date != today:
                self._snapshot_date = today
                self._snapshots = {
                    w.index: WindowSnapshots(snapshot_start=None, snapshot_end=None)
                    for w in self._windows
                }
                _MAIN_LOGGER.warning(
                    "sensor: load - %s stored date %s != today %s, cleared snapshots",
                    self._source_entity,
                    stored.get("snapshot_date"),
                    today,
                )
            else:
                snapshots_data = stored.get("windows") or {}
                loaded = 0
                for w in self._windows:
                    if str(w.index) in snapshots_data:
                        sd = snapshots_data[str(w.index)]
                        self._snapshots[w.index] = WindowSnapshots(
                            snapshot_start=sd.get("snapshot_start"),
                            snapshot_end=sd.get("snapshot_end"),
                        )
                        loaded += 1
                _MAIN_LOGGER.warning("sensor: load - %s snapshot_date=%s loaded %s window(s)", self._source_entity, self._snapshot_date, loaded)
        else:
            self._snapshot_date = today
            _MAIN_LOGGER.warning("sensor: load - %s no stored data", self._source_entity)

    async def save(self) -> None:
        """Persist snapshots to storage."""
        snapshots_data = {
            str(idx): {
                "snapshot_start": s.snapshot_start,
                "snapshot_end": s.snapshot_end,
            }
            for idx, s in self._snapshots.items()
        }
        await self._store.async_save(
            {"windows": snapshots_data, "snapshot_date": self._snapshot_date}
        )
        _MAIN_LOGGER.warning("sensor: save - %s snapshot_date=%s %s window(s)", self._source_entity, self._snapshot_date, len(snapshots_data))

    def _handle_window_start(self, window: WindowConfig, now: datetime) -> None:
        """Snapshot at window start."""
        local_now = self._now()
        self._snapshot_date = local_now.date().isoformat()
        _MAIN_LOGGER.debug(
            "sensor: window '%s' start fired at callback_now=%s local_now=%s tz=%s",
            window.name,
            now.isoformat() if now.tzinfo else now.isoformat() + " (naive)",
            local_now.isoformat(),
            getattr(self._tz, "key", str(self._tz)),
        )
        value = self.get_source_value()
        if value is not None:
            self._snapshots[window.index] = WindowSnapshots(
                snapshot_start=value,
                snapshot_end=None,
            )
            _MAIN_LOGGER.warning("sensor: window '%s' start - %.3f kWh", window.name, value)
            self._schedule_save()
        self._notify_update()

    def _handle_window_end(self, window: WindowConfig, now: datetime) -> None:
        """Snapshot at window end."""
        value = self.get_source_value()
        if value is not None:
            snap = self._snapshots.get(window.index) or WindowSnapshots(None, None)
            self._snapshots[window.index] = WindowSnapshots(
                snapshot_start=snap.snapshot_start,
                snapshot_end=value,
            )
            _MAIN_LOGGER.warning("sensor: window '%s' end - %.3f kWh", window.name, value)
            self._schedule_save()
        self._notify_update()

    def _handle_midnight(self, now: datetime) -> None:
        """Reset snapshots at midnight (day always starts at 00:00 local)."""
        local_now = self._now()
        _MAIN_LOGGER.debug(
            "sensor: midnight fired at callback_now=%s local_now=%s tz=%s",
            now.isoformat() if now.tzinfo else str(now) + " (naive)",
            local_now.isoformat(),
            getattr(self._tz, "key", str(self._tz)),
        )
        _MAIN_LOGGER.warning("sensor: _handle_midnight - resetting snapshots for %s", self._source_entity)
        self._snapshots = {
            w.index: WindowSnapshots(snapshot_start=None, snapshot_end=None)
            for w in self._windows
        }
        self._snapshot_date = local_now.date().isoformat()
        self._schedule_save()
        self._notify_update()

    def _schedule_save(self) -> None:
        """Schedule save() on the event loop (time handlers may run from a thread)."""
        self.hass.loop.call_soon_threadsafe(
            lambda: self.hass.async_create_task(self.save())
        )


def _get_sources_from_config(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Return sources from either legacy source-first or window-first config."""
    raw = config.get(CONF_SOURCES)
    if isinstance(raw, list) and raw:
        return [raw[0]]  # Only first source; one entry = one source

    windows = config.get(CONF_WINDOWS)
    if isinstance(windows, list) and windows:
        by_entity: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
        for i, w in enumerate(windows):
            if not isinstance(w, dict):
                continue
            entities = w.get(CONF_ENTITIES)
            ranges = w.get(CONF_RANGES)
            if not isinstance(entities, list) or not isinstance(ranges, list):
                continue
            name = (w.get(CONF_WINDOW_NAME) or f"Window {i + 1}") or f"Window {i + 1}"
            cost = 0.0
            try:
                if w.get(CONF_COST_PER_KWH) is not None:
                    cost = max(0.0, float(w.get(CONF_COST_PER_KWH)))
            except (TypeError, ValueError):
                cost = 0.0
            range_rows: list[dict[str, Any]] = []
            for r in ranges:
                if not isinstance(r, dict):
                    continue
                start = str(r.get(CONF_WINDOW_START) or "").strip()
                end = str(r.get(CONF_WINDOW_END) or "").strip()
                if not start or not end or start >= end:
                    continue
                range_rows.append(
                    {
                        CONF_WINDOW_NAME: name,
                        CONF_WINDOW_START: start,
                        CONF_WINDOW_END: end,
                        CONF_COST_PER_KWH: cost,
                    }
                )
            if not range_rows:
                continue
            for entity_id in entities:
                if not isinstance(entity_id, str) or not entity_id.strip():
                    continue
                eid = entity_id.strip()
                by_entity.setdefault(eid, []).extend(range_rows)

        out: list[dict[str, Any]] = []
        for entity_id, entity_windows in by_entity.items():
            out.append(
                {
                    CONF_SOURCE_ENTITY: entity_id,
                    CONF_NAME: entity_id.split(".", 1)[-1].replace("_", " ").title(),
                    CONF_WINDOWS: entity_windows,
                }
            )
        return out
    return []


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform (one or more sources under this entry)."""
    _MAIN_LOGGER.warning("sensor: async_setup_entry - entry_id=%s, setting up entities", entry.entry_id)
    config = {**entry.data, **entry.options}
    sources = _get_sources_from_config(config)
    if not sources:
        _MAIN_LOGGER.warning("sensor: async_setup_entry - no sources in config")
        return

    hass.data.setdefault(DOMAIN, {})
    entry_data: dict[str, WindowData] = {}
    hass.data[DOMAIN][entry.entry_id] = entry_data
    all_sensors: list[WindowEnergySensor] = []

    for source_index, source_config in enumerate(sources):
        if not isinstance(source_config, dict):
            _MAIN_LOGGER.warning("sensor: async_setup_entry - source %s is not a dict", source_index)
            continue
        source_entity = source_config.get(CONF_SOURCE_ENTITY)
        if not source_entity:
            _MAIN_LOGGER.warning("sensor: async_setup_entry - source %s has no source_entity", source_index)
            continue
        if not isinstance(source_entity, str):
            _MAIN_LOGGER.warning(
                "sensor: async_setup_entry - source %s source_entity type=%s, coercing to str",
                source_index,
                type(source_entity).__name__,
            )
            source_entity = source_entity[0] if isinstance(source_entity, list) and source_entity else str(source_entity)
        source_name = source_config.get(CONF_NAME) or "Window"
        windows, warnings_by_name = _parse_windows(source_config)
        if not windows:
            continue

        slug = source_slug_from_entity_id(source_entity, f"source_{source_index}")
        store = Store(
            hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY}_{entry.entry_id}_{slug}",
        )
        # Preserve existing unique_ids by window name so entity_ids don't reshuffle
        # when window order changes (older versions used index-based unique_ids).
        registry = er.async_get(hass)
        existing_unique_id_by_name: dict[str, str] = {}
        for entity_entry in registry.entities.get_entries_for_config_entry_id(entry.entry_id):
            if entity_entry.domain != "sensor" or entity_entry.platform != DOMAIN:
                continue
            if not entity_entry.unique_id.startswith(f"{entry.entry_id}_{slug}_"):
                continue
            if entity_entry.original_name:
                key = _window_name_from_original_name(entity_entry.original_name, slug)
                if key and key not in existing_unique_id_by_name:
                    existing_unique_id_by_name[key] = entity_entry.unique_id
        # Use HA configured timezone so window start/end and "today" match the frontend
        tz_str = getattr(hass.config, "time_zone", None) or "UTC"
        tz = await hass.async_add_executor_job(dt_util.get_time_zone, tz_str)
        if tz is None:
            tz = dt_util.get_default_time_zone()
        data = WindowData(
            hass=hass,
            entry_id=entry.entry_id,
            source_entity=source_entity,
            windows=windows,
            store=store,
            tz=tz,
            config_warnings_by_name=warnings_by_name,
        )
        await data.load()
        entry_data[slug] = data

        # Group time ranges by window name: one sensor per name, value = sum over its ranges
        by_name: OrderedDict[str, list[WindowConfig]] = OrderedDict()
        for w in windows:
            by_name.setdefault(w.name, []).append(w)

        for name_index, (window_name, ranges) in enumerate(by_name.items()):
            _MAIN_LOGGER.warning(
                "sensor: async_setup_entry - creating sensor source=%r window=%r ranges=%s",
                source_entity,
                window_name,
                len(ranges),
            )
            sensor = WindowEnergySensor(
                hass=hass,
                entry_id=entry.entry_id,
                config_name=source_name,
                window_name=window_name,
                ranges=ranges,
                data=data,
                all_windows=windows,
                is_first=(name_index == 0),
                source_slug=slug,
                source_index=source_index,
                name_index=name_index,
                existing_unique_id=existing_unique_id_by_name.get(window_name),
            )
            all_sensors.append(sensor)

    # Remove entities for windows that no longer exist (or old source after change)
    # unless they are in the retain list (user chose not to remove when changing source).
    retain_ids = set(entry.options.get("_retain_entity_unique_ids") or [])
    if retain_ids:
        new_options = {k: v for k, v in (entry.options or {}).items() if k != "_retain_entity_unique_ids"}
        hass.config_entries.async_update_entry(entry, options=new_options or None)
    current_unique_ids = {sensor.unique_id for sensor in all_sensors}
    registry = er.async_get(hass)
    for entity_entry in registry.entities.get_entries_for_config_entry_id(
        entry.entry_id
    ):
        if (
            entity_entry.domain == "sensor"
            and entity_entry.platform == DOMAIN
            and entity_entry.unique_id not in current_unique_ids
            and entity_entry.unique_id not in retain_ids
        ):
            _MAIN_LOGGER.warning(
                "sensor: removing orphaned entity %s (unique_id: %s)",
                entity_entry.entity_id,
                entity_entry.unique_id,
            )
            registry.async_remove(entity_entry.entity_id)

    _MAIN_LOGGER.warning(
        "sensor: async_setup_entry - adding %s entities: %s",
        len(all_sensors),
        [s.unique_id for s in all_sensors],
    )
    _MAIN_LOGGER.warning(
        "sensor: async_setup_entry - adding %s entity(ies): %s",
        len(all_sensors),
        [s._window_name for s in all_sensors],
    )
    _MAIN_LOGGER.warning(
        "sensor: async_setup_entry - entry_id=%s, added %s sensor(s)",
        entry.entry_id,
        len(all_sensors),
    )
    async_add_entities(all_sensors, update_before_add=True)


class WindowEnergySensor(RestoreSensor):
    """Sensor that shows energy consumed during a specific time window."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_icon = "mdi:clock-outline"
    _attr_should_poll = True
    _attr_scan_interval = timedelta(seconds=30)

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        config_name: str,
        window_name: str,
        ranges: list[WindowConfig],
        data: WindowData,
        all_windows: list[WindowConfig],
        is_first: bool = False,
        source_slug: str | None = None,
        source_index: int = 0,
        name_index: int = 0,
        existing_unique_id: str | None = None,
    ) -> None:
        self.hass = hass
        self._entry_id = entry_id
        self._window_name = window_name
        self._ranges = ranges
        self._data = data
        self._all_windows = all_windows
        self._is_first = is_first
        self._attr_name = f"{source_slug} {window_name}" if source_slug else window_name
        if source_slug:
            self._attr_unique_id = existing_unique_id or _stable_window_unique_id(
                entry_id, source_slug, window_name
            )
        else:
            self._attr_unique_id = existing_unique_id or f"{entry_id}_{name_index}"
        self._last_source_value: float | None = None
        self._last_status: str | None = None

    async def async_added_to_hass(self) -> None:
        """Restore state and register listeners."""
        _MAIN_LOGGER.warning("sensor: added to hass - %r entity_id=%s", self._window_name, self.entity_id)
        await super().async_added_to_hass()

        # Friendly name is window name only (entity_id already includes source from __init__ name).
        self._attr_name = self._window_name

        if (last := await self.async_get_last_sensor_data()) is not None:
            self._attr_native_value = last.native_value

        self._data.add_update_callback(self._handle_data_update)

        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._data._source_entity],
                lambda e: self._handle_data_update(),
            )
        )

        if self._is_first:
            unsubs = []
            for w in self._all_windows:
                unsubs.append(
                    async_track_time_change(
                        self.hass,
                        lambda t, window=w: self._data._handle_window_start(window, t),
                        hour=w.start_h,
                        minute=w.start_m,
                        second=0,
                    )
                )
                unsubs.append(
                    async_track_time_change(
                        self.hass,
                        lambda t, window=w: self._data._handle_window_end(window, t),
                        hour=w.end_h,
                        minute=w.end_m,
                        second=0,
                    )
                )
            unsubs.append(
                async_track_time_change(
                    self.hass,
                    self._data._handle_midnight,
                    hour=0,
                    minute=0,
                    second=2,
                )
            )
            for unsub in unsubs:
                self.async_on_remove(unsub)

        self._update_value()
        if self.entity_id:
            self.async_write_ha_state()

    async def async_update(self) -> None:
        """Poll source and refresh displayed value; write if value, status, or source changed."""
        old_value = self._attr_native_value
        old_status = self._last_status
        old_source = self._last_source_value
        self._update_value()
        value_or_status_changed = old_value != self._attr_native_value or old_status != self._last_status
        source_changed = old_source != self._last_source_value
        if self.entity_id and (value_or_status_changed or source_changed):
            self.async_write_ha_state()

    @callback
    def _handle_data_update(self) -> None:
        """Update value when source entity state or snapshot data changes; write if value, status, or source changed."""
        old_value = self._attr_native_value
        old_status = self._last_status
        old_source = self._last_source_value
        self._update_value()
        value_or_status_changed = old_value != self._attr_native_value or old_status != self._last_status
        source_changed = old_source != self._last_source_value
        if self.entity_id and (value_or_status_changed or source_changed):
            if value_or_status_changed:
                _MAIN_LOGGER.debug(
                    "sensor: state updated - %r (value or status changed)",
                    self._window_name,
                )
            # Must run on event loop; callback can be invoked from another thread (e.g. time_change)
            self.hass.add_job(self.async_write_ha_state)

    def _update_value(self) -> None:
        total_value: float | None = None
        combined_status = "before_window"
        total_cost = 0.0
        range_attrs: list[dict[str, str]] = []
        rates: list[float] = []

        for r in self._ranges:
            value, status = self._data.get_window_value(r)
            if status == "during_window (no snapshot)":
                if self._data.take_late_start_snapshot(r.index):
                    value, status = self._data.get_window_value(r)
            if value is not None:
                try:
                    total_value = (total_value or 0.0) + float(value)
                except (TypeError, ValueError):
                    pass
            if r.cost_per_kwh > 0 and value is not None:
                try:
                    total_cost += round(float(value) * r.cost_per_kwh, 2)
                except (TypeError, ValueError) as e:
                    _MAIN_LOGGER.warning(
                        "sensor: _update_value - cost calc failed window=%r value=%r: %s",
                        r.name,
                        value,
                        e,
                    )
            if r.cost_per_kwh and r.cost_per_kwh > 0:
                rates.append(r.cost_per_kwh)
            range_attrs.append({
                "start": _time_str(r.start_h, r.start_m),
                "end": _time_str(r.end_h, r.end_m),
            })
            if status.startswith("during_window"):
                combined_status = status
            elif status.startswith("after_window") and not combined_status.startswith("during_window"):
                combined_status = status

        self._attr_native_value = round(total_value, 3) if total_value is not None else None
        attrs: dict[str, Any] = {
            ATTR_SOURCE_ENTITY: self._data._source_entity,
            ATTR_STATUS: combined_status,
            "ranges": range_attrs,
        }
        if (cw := self._data._config_warnings_by_name.get(self._window_name)):
            attrs["config_warnings"] = list(cw)
        if rates:
            # Always expose cost when rate is configured so automations can track a running balance.
            attrs[ATTR_COST] = round(total_cost, 2)
            uniq_rates = sorted({round(float(x), 6) for x in rates})
            attrs["cost_per_kwh"] = uniq_rates[0] if len(uniq_rates) == 1 else uniq_rates
        self._attr_extra_state_attributes = attrs
        self._last_source_value = self._data.get_source_value()
        self._last_status = combined_status

