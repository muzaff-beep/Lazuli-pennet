# LazuliNet GUI Development — v0.4

A shared GUI/application layer for Debian and Android LazuliNet runtimes, continuing the 2026-08-10 architecture baseline.

## Architecture

```text
Kivy GUI / lazulinet-safe CLI
            ↓
    Application Services
            ↓
        TaskRunner
            ↓
      Typed Adapter Ports
       ↙             ↘
Debian adapters    Android adapter
       ↓             ↓
Linux tooling     WifiManager/PyJNIus
            ↓
   Session Repository
            ↓
 Legacy one-way importer
```

The GUI and safe CLI do not call the legacy root/Debian scanner modules or Android Termux monolith directly.

## v0.4 functionality

### Shared core

- Typed `WirelessInterface`, `NetworkObservation`, `ScanRequest`, `ScanSession`, `TaskEvent`, and state enums.
- Typed validation/errors.
- Session-scoped atomic JSON storage.
- Raw artifact preservation on completed, cancelled, failed, and imported sessions.
- Partial normalized observations retained on cancellation.
- Cancellable background `TaskRunner` with structured events.
- Session verification for observation counts and recorded artifacts.
- TXT, JSON, and portable ZIP session reports.

### Legacy data migration

v0.4 adds a one-way compatibility layer for historical safe discovery output:

- scans known old `networks.json` locations;
- accepts list, `{ "networks": [...] }`, BSSID-keyed mapping, and common legacy field names;
- normalizes BSSID, ESSID/SSID, channel, security, signal, counters, and client/station lists;
- deduplicates repeated BSSID records and merges clients;
- copies the original JSON into the new session `raw/` directory;
- uses SHA-256 source indexing so repeated imports are skipped by default;
- supports explicit `--force` re-import;
- never imports or executes legacy Python modules.

### Debian

- `iw` interface inspection plus wireless-only `/sys/class/net` fallback.
- Managed/monitor state handling through validated argv-only process calls.
- Dependency and privilege preflight.
- Passive `airodump-ng` discovery adapter.
- Proper Python CSV parsing, including quoted ESSIDs containing commas and station/client association.
- Injectable process/command boundary for deterministic integration testing.

### Android

- Packaged-app adapter uses Android `WifiManager` via PyJNIus; it does not inherit the old Termux shell environment.
- Runtime Wi-Fi permission request surface.
- Wi-Fi enabled and Location Services health state.
- SSID/BSSID/channel/signal normalization.
- Optional channel filtering.
- Cached/throttled scan-result behavior is represented explicitly in normalized metadata.

### GUI

One `ScreenManager` powers both form factors.

**Debian / wide window**

- full left sidebar;
- desktop network/session table layouts;
- wider interface control rows;
- Migration screen for old `networks.json` discovery output.

**Android / narrow window**

- bottom navigation: Home / Interfaces / Scan / Networks / More;
- card-based interface, network, and session views;
- touch-sized controls;
- More screen for Sessions / Reports / Logs / System.

Screens:

1. Dashboard
2. Interfaces
3. Discovery
4. Networks
5. Sessions
6. Reports
7. Migration (Debian)
8. Logs
9. System
10. Mobile More navigation

## Shared safe CLI

The CLI calls the same services as the GUI:

```bash
python -m lazulinet.cli health
python -m lazulinet.cli interfaces
python -m lazulinet.cli sessions
python -m lazulinet.cli scan wlan0 --duration 30
python -m lazulinet.cli report --format bundle
python -m lazulinet.cli verify
python -m lazulinet.cli migrate-legacy /path/to/Lazuli-pennet-main --dry-run
python -m lazulinet.cli migrate-legacy /path/to/Lazuli-pennet-main
```

Installed entry point:

```bash
lazulinet-safe health
```

A prebuilt pure-Python core wheel is included in `dist/` for environments where the core/CLI should be installed before GUI dependencies:

```bash
python -m pip install dist/lazulinet_gui-0.4.0-py3-none-any.whl
```

Kivy remains an optional GUI dependency and is not embedded in that wheel.

## Debian development

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e '.[gui,dev]'
python run_gui.py
```

Real passive discovery expects the applicable Debian runtime dependencies, notably `iw`, `ip`, and `airodump-ng`, plus appropriate device privilege.

### Debian smoke test

```bash
./scripts/debian_smoke.sh
```

It runs compilation, tests, Kivy import, and an Xvfb GUI construction test at desktop and phone dimensions.

## Android development

```bash
./scripts/android_debug_build.sh
```

Equivalent direct command:

```bash
buildozer android debug
```

`buildozer.spec` targets API 35, minimum API 26, arm64-v8a, and declares the Wi-Fi/location permissions required by the current adapter path.

## Tests

```bash
python -m compileall -q lazulinet run_gui.py scripts/smoke_gui.py
python -m pytest
```

Current suite covers parser edge cases, task cancellation, session persistence/verification, Debian process lifecycle, Android fake-`WifiManager` behavior, safe CLI behavior, legacy migration/idempotency, and report bundle composition.

## CI

`.github/workflows/gui-core.yml` contains Python 3.10/3.12 core tests and a Kivy + Xvfb responsive GUI smoke job.

## Original repository migration

See [`MIGRATION_v0.4.md`](MIGRATION_v0.4.md).

## Security boundary

The GUI/service registry does not import or expose the repository's legacy deauthentication, credential capture/cracking, WPS/PMKID, or rogue-AP modules. v0.4 remains limited to interface administration, passive discovery, persistence, reporting, migration of historical discovery output, logs, and health checks.
