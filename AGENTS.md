# AGENTS.md

This file guides AI coding agents (and humans) working in this repository.

## Project Overview

A [Home Assistant](https://www.home-assistant.io/) **custom integration** that connects
**Aquark pool chlorinators** to Home Assistant over **Modbus** (TCP or serial). It is
distributed via HACS (`hacs.json`) and lives in `custom_components/aquark_modbus/`.

The integration is a thin wrapper around the PyPI library **`aquark-modbus`** (pinned
to `==0.1.2` in `manifest.json` and `pyproject.toml`). All Modbus protocol knowledge
lives in the library; this repo only does Home Assistant wiring.

- Domain: `aquark_modbus`
- iot_class: `local_polling` (30 s poll, `UPDATE_INTERVAL` in `const.py`)
- Quality scale target: **bronze** (see `custom_components/aquark_modbus/quality_scale.yaml`)
- Codeowner: `@ringods`

## Repository Layout

```
custom_components/aquark_modbus/   # The integration
  __init__.py        # async_setup_entry / async_unload_entry, PLATFORMS list
  config_flow.py     # User flow: menu → tcp | serial, probes device before creating entry
  const.py           # DOMAIN, fixed serial line settings, defaults, poll interval
  coordinator.py     # AquarkDataUpdateCoordinator: polls Chlorinator, tracks per-block failures
  entity.py          # AquarkEntity base: per-block availability, shared write/error handling
  helpers.py         # create_modbus_params(), error_detail()
  sensor.py          # Sensor platform (pool_temperature, ph)
  manifest.json      # HA manifest: dependencies (modbus, usb), requirements
  quality_scale.yaml # HA quality-scale rule tracker (all rules currently "todo")
  translations/en.json  # (currently empty — see Known Issues)
  brand/             # HACS brand images
tests/
  conftest.py        # HA test fixtures + MockModbusConnection wiring
  test_config_flow.py  # (currently empty)
pyproject.toml       # uv project (package = false); dev group pins homeassistant
mise.toml            # Python 3.14.2
hacs.json            # HACS metadata
```

## Toolchain & Commands

- **Package manager: `uv`**. Run everything through it (e.g. `uv run python ...`).
- **Python 3.14.2**, pinned by `mise.toml` (mise manages the interpreter).
- The dev dependency group pins `homeassistant==2026.10.2`, `pytest`, and
  `pytest-homeassistant-custom-component` (HA's test plugin stack, incl.
  `pytest-asyncio`, `syrupy`, `respx`). It is built against the same HA version.
- pytest is configured in `pyproject.toml` under `[tool.pytest.ini_options]`
  (`testpaths = ["tests"]`, `asyncio_mode = "auto"` — required by
  `pytest-asyncio`).
- Run the test suite with:

```sh
uv run pytest -v
```

There is no linter/formatter/type-checker configured in `pyproject.toml` yet.

## Architecture (how the pieces fit)

1. **Config flow** (`config_flow.py`): user picks `tcp` or `serial` in a menu step.
   - TCP: host + port (default 502) + Modbus unit ID (default 8, range 1–247).
   - Serial: port only — the board's line settings are **fixed at 9600-8-N-1**
     (constants in `const.py`; don't make them user-configurable).
   - Before creating the entry, the flow **probes the device** via
     `homeassistant.components.modbus.async_get_temporary_unit` and distinguishes
     connection errors ("link down") from a silent unit ("link up, no Modbus
     answer") from a non-Aquark device.
   - The board has **no serial number**, so duplicate detection uses
     `IDENTITY_KEYS` (connection type + endpoint + unit ID) via
     `_async_abort_entries_match`.

2. **Setup** (`__init__.py`): builds `ModbusSerialParams`/`ModbusTcpParams` via
   `helpers.create_modbus_params`, gets a `ModbusUnit` from HA's built-in `modbus`
   component with `async_get_unit`, wraps it in `Chlorinator(unit)` from the
   `aquark-modbus` library, creates the coordinator, does a first refresh, stores
   it in `entry.runtime_data`, and forwards to `PLATFORMS`.

3. **Coordinator** (`coordinator.py`): `DataUpdateCoordinator[UpdateReport]`.
   The library polls **independent blocks** (e.g. `readings`, `settings`) and returns
   an `UpdateReport` with `updated` / `failed` sets. The coordinator:
   - raises `UpdateFailed` (with a translation key) if *no* block answered,
   - logs a block's **first failure and its recovery exactly once** each
     (`_failing` set in `_log_block_changes`).
   Partial block failure is **not** `UpdateFailed` — entities degrade individually.

4. **Entities** (`entity.py`): `AquarkEntity` (a `CoordinatorEntity`) declares the
   blocks it reads in `AquarkEntityDescription.blocks`. An entity is unavailable
   when **any of its own blocks** is in `coordinator.data.failed` — not when any
   block of the device failed. Unique ID = `<entry_id>_<entity_description.key>`.
   Writes go through `_async_write` which maps library exceptions to HA
   `HomeAssistantError` / `ServiceValidationError` and then requests a refresh.

5. **Sensors** (`sensor.py`): each sensor is an entity description with a
   `value_fn: Callable[[Chlorinator], float | int]` (the library object, not the
   raw report). Current sensors: `pool_temperature`, `ph`.

## The `aquark-modbus` library (installed, read it in `.venv` when unsure)

```python
from aquark_modbus import Chlorinator, AquarkError, AquarkConnectionError
```

- `Chlorinator(unit: ModbusUnit)` with sub-components (each a "block"):
  `model` (read once), `readings`, `status`, `settings`.
- `await chlorinator.async_update() -> UpdateReport` (all blocks),
  plus `async_update_readings()` / `async_update_settings()`.
- Exception hierarchy: `AquarkError` (base), `AquarkConnectionError` (transport
  down). `modbus_connection` (a separate lib) defines `ModbusTcpParams`,
  `ModbusSerialParams`, `UpdateReport`, and a `MockModbusConnection` for tests.
- `Readings` exposes `pool_temperature`, `ph`, `chlorine_production`, etc.

## Testing Conventions

Tests are plain pytest with `pytest-homeassistant-custom-component` (HA test
fixtures, `MockConfigEntry`, `enable_custom_integrations`). Key fixtures in
`tests/conftest.py`:

- **`mock_connection`** — a `MockModbusConnection` whose unit register map is
  parametrized via `register_image` (pass `@pytest.mark.parametrize("register_image", [...], indirect=True)`).
- **`init_integration`** — creates the mock config entry and sets it up.
- **`mock_get_unit` / `mock_temporary_unit`** — patch `async_get_unit` /
  `async_get_temporary_unit` so the integration talks to the mock.
- The integration must be loadable from `custom_components/`
  (`auto_enable_custom_integrations` fixture is autouse).
- Snapshots use `HomeAssistantSnapshotExtension` (syrupy).

When writing tests, patch **`custom_components.aquark_modbus`** paths (not any
other integration name — see Known Issues).

## Code Conventions

- **Strict typing**; use `@override` for all overridden methods/properties
  (the codebase is written for Python 3.14 — `type` aliases, `@dataclass(kw_only=True, frozen=True)`).
- Constants in `const.py`, typed `Final` where appropriate.
- Every HA error raised to the UI uses `translation_domain=DOMAIN` and a
  `translation_key` that **must exist in `translations/en.json`** (currently
  empty — add keys as you introduce them).
- Use `helpers.error_detail(err)` (`str(err.__cause__ or err)`) for
  `translation_placeholders` — the library's top-level message duplicates the
  translated text.
- Docstrings on modules, classes, and public methods; keep them short and
  factual.
- `manifest.json` is the source of truth for HA metadata; keep `requirements`
  and `pyproject.toml` dependencies in sync when bumping `aquark-modbus`.
- Bump the version in `manifest.json` on changes.
