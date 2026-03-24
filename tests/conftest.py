"""Pytest configuration for Energy Window Tracker Beta."""

from __future__ import annotations

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield


@pytest.fixture
def mock_legacy_config_entry(hass: HomeAssistant) -> ConfigEntry:
    """Window-first shape used by options flow tests."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Energy Window Tracker (Beta)",
        data={
            CONF_WINDOWS: [
                {
                    CONF_WINDOW_NAME: "Peak",
                    CONF_IMPORT_RATE_PER_KWH: 0.2,
                    CONF_ENTITIES: ["sensor.today_load"],
                    CONF_RANGES: [
                        {
                            CONF_WINDOW_START: "09:00",
                            CONF_WINDOW_END: "17:00",
                        }
                    ],
                }
            ]
        },
        options={},
        entry_id="legacy_entry_id",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def mock_window_setup_entry(hass: HomeAssistant) -> ConfigEntry:
    """Windows-based shape (windows with entities + ranges) used in beta flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Energy Window Tracker (Beta)",
        data={
            CONF_WINDOWS: [
                {
                    CONF_WINDOW_NAME: "Peak",
                    CONF_IMPORT_RATE_PER_KWH: 0.2,
                    CONF_ENTITIES: ["sensor.today_load"],
                    CONF_RANGES: [
                        {CONF_WINDOW_START: "09:00", CONF_WINDOW_END: "11:00"},
                        {CONF_WINDOW_START: "17:00", CONF_WINDOW_END: "19:00"},
                    ],
                }
            ]
        },
        options={},
        entry_id="window_setup_entry_id",
    )
    entry.add_to_hass(hass)
    return entry
