# Energy Window Tracker (Beta)

[![Tests](https://img.shields.io/github/actions/workflow/status/thedeviousdev/ha-energy-window-tracker-beta/pytest.yml?label=tests&logo=githubactions)](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/actions/workflows/pytest.yml)
[![Ruff](https://img.shields.io/github/actions/workflow/status/thedeviousdev/ha-energy-window-tracker-beta/ruff.yml?label=ruff&logo=ruff)](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/actions/workflows/ruff.yml)
[![Release](https://img.shields.io/github/v/release/thedeviousdev/ha-energy-window-tracker-beta?label=release)](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom%20Integration-41BDF5?logo=homeassistantcommunitystore&logoColor=white)](https://hacs.xyz/)

Energy Window Tracker (Beta) helps you track energy usage inside time windows you define. It reads a cumulative sensor, takes snapshots, and reports usage during and after each configured window.

You can use multiple source entities, multiple ranges. The integration stores configured times as `HH:MM:SS`.

## Requirements

You need Home Assistant with custom integrations enabled, plus a **cumulative** energy sensor (kWh) that normally goes up over time. You can use either daily meters (reset at midnight) or lifetime/total counters; see [Energy source: today vs totals](#energy-source-today-vs-totals).

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant.
2. Add this repository as a custom integration.
3. Install **Energy Window Tracker (Beta)**.
4. Restart Home Assistant.

### Manual

1. Copy `custom_components/energy_window_tracker_beta` to:
   - `<config>/custom_components/energy_window_tracker_beta`
2. Restart Home Assistant.

## Setup

Go to **Settings -> Devices & Services -> Add Integration** and select **Energy Window Tracker (Beta)**.  
In setup, define your window and time range(s), then choose one or more source entities and click **Add**.  
You will then see a confirmation screen that lets you jump back into editing.

## Managing Configuration

Open the integration and choose **Configure** to edit windows or update source entities.  
When editing a window, remove a time range by **clearing** that row’s start and/or end time (empty fields drop the range). From **Configure** (Options), if you clear every range and save, you are prompted to confirm deleting the window.  
Saving changes shows a success confirmation and returns you to the configure menu.

## Energy source: today vs totals

You may use **either**:

- **Today** (or other daily-reset) sensors whose value is cumulative **since the last reset** (often midnight), or  
- **Total / lifetime** sensors whose value is cumulative **since install** (or since the inverter began reporting totals).

The integration calculates energy by looking at the difference between snapshots. Both sensor types work as long as the value normally moves upward during the window (except for resets you expect).

Use one style consistently when comparing with other energy values (import, export, load, battery, templates, dashboards). Mixing daily-reset values with lifetime totals can lead to confusing comparisons unless you first align them to the same period.

Trade-offs: daily-reset sensors are simple for same-day windows, but they reset at midnight. Lifetime totals are usually better for windows over any time span, including across midnight.

## Notes and Behavior

- Validation enforces chronological ranges, including seconds precision.
- Window logic uses your Home Assistant timezone (`Settings -> System -> General`).

## Contributing

For testing and development workflows, see `CONTRIBUTING.md`.

## Troubleshooting

If UI labels appear as raw keys, restart Home Assistant to refresh translation cache.

If source values are not updating as expected, check that the entity exists, has a numeric state, is cumulative, and your ranges are valid/in order. If comparisons to other sensors look wrong, confirm you are not mixing **today** and **lifetime** bases without converting them consistently (see [Energy source: today vs totals](#energy-source-today-vs-totals)).


For bugs and feature requests, use:

- [Issues](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues)
- [Repository](https://github.com/thedeviousdev/ha-energy-window-tracker-beta)
