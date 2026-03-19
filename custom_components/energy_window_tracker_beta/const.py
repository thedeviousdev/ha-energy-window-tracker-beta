"""Constants for the Energy Window Tracker Beta integration."""

import logging

DOMAIN = "energy_window_tracker_beta"

# Log level below DEBUG (10) for very verbose trace; set logger level to 5 to enable
TRACE = 5
if not hasattr(logging, "TRACE"):
    logging.TRACE = TRACE  # type: ignore[attr-defined]
    logging.addLevelName(TRACE, "TRACE")

CONF_SOURCE_ENTITY = "source_entity"
CONF_SOURCES = "sources"
CONF_NAME = "name"
CONF_WINDOWS = "windows"
CONF_WINDOW_START = "start"
CONF_WINDOW_END = "end"
CONF_WINDOW_NAME = "name"
CONF_COST_PER_KWH = "cost_per_kwh"
CONF_ENTITIES = "entities"
CONF_RANGES = "ranges"

DEFAULT_ENTRY_TITLE_KEY = "config.defaults.entry_title"
DEFAULT_NAME_KEY = "config.defaults.window_name"
DEFAULT_WINDOW_FALLBACK_KEY = "config.defaults.window_fallback"
DEFAULT_SOURCE_ENTITY = "sensor.today_load"
DEFAULT_WINDOW_START = "11:00"
DEFAULT_WINDOW_END = "14:00"

STORAGE_VERSION = 1
STORAGE_KEY = "energy_window_tracker_beta_snapshots"


def source_slug_from_entity_id(entity_id: str, fallback: str = "source_0") -> str:
    """Stable slug from entity_id for storage, unique_id, and entity name."""
    if not entity_id or not (e := entity_id.strip()):
        return fallback
    object_id = e.split(".", 1)[-1] if "." in e else e
    return object_id.replace(".", "_").replace(":", "_")[:64] or fallback


ATTR_SOURCE_ENTITY = "source_entity"
ATTR_STATUS = "status"
ATTR_COST = "cost"
