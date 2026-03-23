# Energy Window Tracker (Beta)

[![Tests](https://img.shields.io/github/actions/workflow/status/thedeviousdev/ha-energy-window-tracker-beta/pytest.yml?label=tests&logo=githubactions)](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/actions/workflows/pytest.yml)
[![Ruff](https://img.shields.io/github/actions/workflow/status/thedeviousdev/ha-energy-window-tracker-beta/ruff.yml?label=ruff&logo=ruff)](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/actions/workflows/ruff.yml)
[![Release](https://img.shields.io/github/v/release/thedeviousdev/ha-energy-window-tracker-beta?label=release)](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/releases)
[![License](https://img.shields.io/github/license/thedeviousdev/ha-energy-window-tracker-beta)](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/blob/main/LICENSE)
[![HACS](https://img.shields.io/badge/HACS-Custom%20Integration-41BDF5?logo=homeassistantcommunitystore&logoColor=white)](https://hacs.xyz/)

Energy Window Tracker (Beta) helps you track energy usage inside time windows you define. It reads a cumulative sensor (for example `sensor.today_load`), takes snapshots, and reports usage during and after each configured window.

You can use multiple source entities, multiple ranges, and separate window names. The integration stores configured times as `HH:MM:SS`.

## Requirements

You need Home Assistant with custom integrations enabled, plus a cumulative source sensor that increases over time (for example `sensor.today_load` or `sensor.energy_today`).

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
When editing ranges, each row has a `❌ Delete?` option so removing a specific range is explicit.  
Saving changes shows a success confirmation and returns you to the configure menu.

## Notes and Behavior

- Validation enforces chronological ranges, including seconds precision.
- If all ranges for a window are removed in the edit flow, that window is removed.
- The integration entry title is derived from the first configured window name and updates when you rename the window in the edit flow.

## Contributing

For testing and development workflows, see `CONTRIBUTING.md`.

## Troubleshooting

If UI labels appear as raw keys, restart Home Assistant to refresh translation cache.

If source values are not updating as expected, check that the entity exists, has a numeric state, is cumulative, and your ranges are valid/in order.

For bugs and feature requests, use:

- [Issues](https://github.com/thedeviousdev/ha-energy-window-tracker-beta/issues)
- [Repository](https://github.com/thedeviousdev/ha-energy-window-tracker-beta)
