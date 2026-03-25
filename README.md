# Energy Window Tracker (Beta)

[![Tests](https://img.shields.io/github/actions/workflow/status/thedeviousdev/ha-energy-window-tracker-beta/pytest.yml?label=tests&logo=githubactions)](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/actions/workflows/pytest.yml)
[![Ruff](https://img.shields.io/github/actions/workflow/status/thedeviousdev/ha-energy-window-tracker-beta/ruff.yml?label=ruff&logo=ruff)](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/actions/workflows/ruff.yml)
[![Release](https://img.shields.io/github/v/release/thedeviousdev/ha-energy-window-tracker-beta?label=release)](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom%20Integration-41BDF5?logo=homeassistantcommunitystore&logoColor=white)](https://hacs.xyz/)

Energy Window Tracker (Beta) helps you track energy usage inside time windows you define. It reads a cumulative sensor, takes snapshots, and reports usage during and after each configured window.

You can use multiple source entities, multiple ranges. The integration stores configured times as `HH:MM:SS`.

## Requirements

You need Home Assistant with custom integrations enabled, plus a **cumulative** energy sensor (kWh) that increases over time. **Daily “today” meters** (reset at midnight) and **lifetime / total** counters (monotonic since install or inverter lifetime) are both valid sources; see [Energy source: today vs totals](#energy-source-today-vs-totals).

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
In the setup form, choose a name, set cost per kWh if you want, and add one or more ranges with `Start time #N` and `End time #N`.  
Then pick one or more source entities and click **Add**.

After entities are added, you will see a confirmation screen where you can jump straight back to editing.

## Managing Configuration

Open the integration and choose **Configure** to edit windows or update source entities.  
When editing a window, remove a time range by **clearing** that row’s start and/or end time (empty fields drop the range). From **Configure** (Options), if you clear every range and save, you are prompted to confirm deleting the window.  
Saving changes shows a success confirmation and returns you to the configure menu.

## Energy source: today vs totals

You may use **either**:

- **Today** (or other daily-reset) sensors whose value is cumulative **since the last reset** (often midnight), or  
- **Total / lifetime** sensors whose value is cumulative **since install** (or since the inverter began reporting totals).

The integration derives window usage from **differences** between snapshots, so both kinds work as long as the entity is **monotonic** across the window (aside from known resets you account for).

**Use one style consistently** when you relate this integration’s output to **other** energy entities (import, export, load, battery, templates, or dashboards). Mixing **today** for one metric and **lifetime totals** for another without aligning them to the same period or basis will produce **misleading or inconsistent comparisons** (“dirty” data). Prefer the same counter class for every quantity in a given balance or formula.

**Trade-offs:** Today-style counters are easy to reason about for same-calendar-day windows but **reset at midnight** (windows that cross midnight need care). Lifetime totals behave well for **deltas over arbitrary intervals**; numeric magnitude does not meaningfully affect Home Assistant database size compared to how often states change.

## Notes and Behavior

- **Generated sensor entity IDs** use a stable registry `unique_id` built from your **config entry id**, a persisted **source slot id** (UUID per energy sensor row), and a **UUID v5** derived from the window’s **time ranges** — not the source entity’s object id. Reordering sources in the UI does **not** change those ids as long as each row keeps its slot id. After upgrading, existing entities are **migrated** from older slug-, index-, and hash-suffix ids so dashboards keep working.
- Validation enforces chronological ranges, including seconds precision.
- From **Configure** (Options), removing all ranges and saving prompts confirmation to delete that window; during initial setup the edit flow requires at least one valid range.
- The integration entry title is derived from the first configured window name and updates when you rename the window in the edit flow.
- The integration interprets window times using Home Assistant's configured local timezone.

## Contributing

For testing and development workflows, see `CONTRIBUTING.md`.

## Troubleshooting

If UI labels appear as raw keys, restart Home Assistant to refresh translation cache.

If source values are not updating as expected, check that the entity exists, has a numeric state, is cumulative, and your ranges are valid/in order. If comparisons to other sensors look wrong, confirm you are not mixing **today** and **lifetime** bases without converting them consistently (see [Energy source: today vs totals](#energy-source-today-vs-totals)).

### Home Assistant timezone
Window logic uses your Home Assistant instance timezone.
You can check it in Home Assistant under `Settings -> System -> General`.

For bugs and feature requests, use:

- [Issues](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues)
- [Repository](https://github.com/thedeviousdev/ha-energy-window-tracker-beta)
