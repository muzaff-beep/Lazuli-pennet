# LazuliNet GUI Development — v0.3

A shared GUI/application layer for the Debian and Android LazuliNet runtimes, based on the 2026-08-10 architecture baseline.

## Architecture implemented

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
```

The GUI and safe CLI do not call the legacy root/Debian scanner modules or Android Termux monolith directly.

## v0.3 functionality

### Shared core

- Typed `WirelessInterface`, `NetworkObservation`, `ScanRequest`, `ScanSession`, `TaskEvent`, and state enums.
- Typed validation/errors.
- Session-scoped atomic JSON storage.
- Raw artifact preservation on completed, cancelled, and failed discovery lifecycles.
- Partial normalized observations are retained on cancellation.
- Cancellable background `TaskRunner` with structured events.
- TXT and JSON reporting.

### Debian

- `iw` interface inspection plus `/sys/class/net` fallback.
- Managed/monitor state handling through validated argv-only process calls.
- Dependency and privilege preflight.
- Wireless-only sysfs fallback (Ethernet interfaces are not surfaced as Wi-Fi adapters).
- Passive `airodump-ng` discovery adapter.
- Proper Python CSV parsing, including quoted ESSIDs containing commas and station/client association.
- Injectable process/command boundary for deterministic integration testing.

### Android

- Packaged-app adapter uses Android `WifiManager` via PyJNIus; it does not inherit the old Termux shell environment.
- Runtime Wi-Fi permission request surface.
- Wi-Fi enabled and Location Services health state.
- SSID/BSSID/channel/signal normalization.
- Optional channel filtering over returned observations.
- Tolerates a throttled/failed `startScan()` request by marking whether the scan was initiated and normalizing available scan results.

### GUI

One `ScreenManager` powers both form factors.

**Debian / wide window**

- full left sidebar;
- desktop network/session table layouts;
- wider interface control rows.

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
7. Logs
8. System
9. Mobile More navigation

## Safe CLI convergence seam

The new CLI calls the exact same services as the GUI:

```bash
python -m lazulinet.cli health
python -m lazulinet.cli interfaces
python -m lazulinet.cli sessions
python -m lazulinet.cli scan wlan0 --duration 30
python -m lazulinet.cli report
```

When installed as a package:

```bash
lazulinet-safe health
```

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

It runs compilation, unit/integration tests, Kivy import, and an Xvfb GUI construction test at both desktop and phone dimensions.

## Android development

```bash
./scripts/android_debug_build.sh
```

Equivalent direct command:

```bash
buildozer android debug
```

`buildozer.spec` targets API 35, minimum API 26, arm64-v8a, and declares Wi-Fi/location permissions required by the current adapter path.

Device validation still needs to verify runtime permissions, Location Services, scan throttling/cached-result behavior, and normalization on the actual OEM Android build.

## Tests

```bash
python -m compileall -q lazulinet run_gui.py scripts/smoke_gui.py
python -m pytest
```

Current suite covers:

- parser edge cases;
- AP/client association;
- validation;
- session round-trip;
- cancelled partial persistence;
- failed raw-artifact preservation;
- task completion/cancellation;
- Debian process success/cancel/failure/no-artifact paths;
- Android channel conversion;
- Android fake-WifiManager normalization/filtering/cancellation;
- safe CLI session/report behavior.

## CI

`.github/workflows/gui-core.yml` contains:

- Python 3.10 + 3.12 core tests;
- Kivy install + Xvfb responsive GUI smoke test.

## Original repository migration

See [`MIGRATION_v0.3.md`](MIGRATION_v0.3.md).

The migration is staged intentionally: add the new package beside the legacy code, route safe CLI functions through the shared services, validate Debian/Android, then retire duplicated safe scanner/reporter code.

## Security boundary

The GUI/service registry does not import or expose the repository's legacy deauthentication, credential capture/cracking, WPS/PMKID, or rogue-AP modules. v0.3 is limited to interface administration, passive discovery, persistence, reporting, logs, and health checks.
