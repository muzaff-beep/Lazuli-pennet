# LazuliNet GUI Development — v0.2

This package implements the first GUI architecture slice from the 2026-08-10 LazuliNet architecture baseline.

## Implemented

- Shared typed domain models (`WirelessInterface`, `NetworkObservation`, `ScanSession`, `TaskState`).
- Session-scoped storage under `data/sessions/...` semantics instead of overwriting one `networks.json`.
- Robust `airodump-ng` CSV parsing through Python's `csv` module, including quoted ESSIDs and client association.
- Cancellable background `TaskRunner` with structured events.
- Debian interface adapter with typed, argv-only subprocess boundaries.
- Debian passive discovery adapter with cancellation and artifact preservation.
- Android safe `WifiManager` adapter through PyJNIus; no Termux shell execution.
- Shared Kivy screens: Dashboard, Interfaces, Discovery, Networks, Sessions, Reports, Logs, System.
- Android `buildozer.spec` packaging baseline.
- Unit tests for parser, sessions, task cancellation, interface parsing, validation, and service orchestration.

## Security boundary

The GUI does not import or expose the repository's legacy deauthentication, credential capture/cracking, WPS/PMKID, or rogue-AP modules. This development slice is limited to interface administration, passive discovery, persistence, reporting, logs, and health checks.

## Debian development

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements-gui.txt
python run_gui.py
```

Expected external Debian tools for real discovery:

- `iw`
- `ip`
- `airodump-ng`
- `sudo` when the process is not already root

The GUI performs a dependency preflight and uses non-interactive `sudo -n`; it does not prompt for a password from a background worker.

## Android development

The packaged Android adapter uses Android's `WifiManager` via PyJNIus for safe Wi-Fi scan results. It does not assume that a Kivy APK inherits the old Termux/root environment.

```bash
buildozer android debug
```

The System screen includes a runtime Wi-Fi permission request. Android's scan APIs are permission- and device-policy-dependent and may return cached/throttled results.

## Tests

```bash
python -m pytest
python -m compileall -q lazulinet run_gui.py
```

No wireless hardware is required for the unit suite.

## Drop-in integration with the original ZIP

Copy this package into the original repository root, then migrate the old CLI incrementally so both CLI and GUI call `lazulinet.application` services rather than the duplicated legacy modules.

Recommended next slice:

1. import representative real scan CSV fixtures from the original repository/environment;
2. add Debian integration tests with a fake process layer;
3. add Android device smoke testing for permissions and `WifiManager` result normalization;
4. converge the root/Debian safe CLI commands onto this shared core;
5. only then remove duplicated safe scanner/reporter code.
