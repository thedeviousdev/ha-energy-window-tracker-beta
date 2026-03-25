# Contributing

Thanks for contributing to Energy Window Tracker (Beta).

## Development Setup

1. Clone the repository.
2. Create and activate a Python virtual environment.
3. Install test/development dependencies:

```bash
pip install -r requirements_test.txt
```

## Run Checks Locally

Before opening a PR, run:

```bash
ruff check .
pytest -q
```

## Test Suite Scope

Tests are organized under `tests/` and cover:

- config flow behavior
- options flow behavior
- edge cases
- logging behavior
- integration setup/unload
- sensor behavior

The suite uses happy/unhappy naming to make intent clear.

## Coding Guidelines

- Keep changes focused and small when possible.
- Preserve existing behavior unless intentionally changed.
- Add or update tests for every behavior change.
- Prefer clear, descriptive names and avoid single-letter variables.

## Developer Notes

### Stable sensor IDs

Generated sensor `unique_id`s are designed to stay stable across UI reordering.
They are based on the config entry, a saved slot ID for each source row, and the window time ranges (not the source entity's internal ID). Older ID formats are migrated to keep existing dashboards working.

### Entry title behavior

The config entry title is taken from the first configured window name and updates when you rename that window in the edit flow.

## Pull Requests

- Use a descriptive title and summary.
- Include a short test plan (commands and outcomes).
- Ensure CI passes (Ruff and Pytest).
- If changing user-facing flow text, update both:
  - `custom_components/energy_window_tracker_beta/strings.json`
  - `custom_components/energy_window_tracker_beta/translations/en.json`

## Documentation

- Keep `README.md` user-focused (install/setup/usage/troubleshooting).
- Keep contributor workflows in this file.
