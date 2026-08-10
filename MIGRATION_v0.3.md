# LazuliNet v0.3 Migration Guide

Target baseline: `Lazuli-pennet-main.zip`, revision marker `280c9ca1639a7e72d7f0705d5bac16e5f82d008c` from the 2026-08-10 architecture review.

## Objective

Move the safe/admin surface of the existing root, Debian, and Android implementations onto one shared application core without importing the legacy security-sensitive modules into the GUI registry.

## Add the new shared package first

Copy these v0.3 paths into the original repository root:

```text
lazulinet/
run_gui.py
pyproject.toml
requirements-gui.txt
requirements-dev.txt
buildozer.spec
scripts/
tests/
.github/workflows/gui-core.yml
```

At this point the old files can remain untouched. The new package is intentionally namespaced under `lazulinet/` so it can coexist during migration.

## Root CLI convergence

Current baseline entry point:

```text
lazulinet.py
```

Safe commands should be migrated to the new services rather than importing the old scanner/reporter directly:

```text
old root CLI scan/report
        ↓
lazulinet.platform.factory.create_runtime()
        ↓
InterfaceService / DiscoveryService / ReportService
```

The v0.3 `lazulinet-safe` CLI demonstrates this composition and can be used as the reference implementation.

Do not migrate the legacy attack/crack paths into `lazulinet-safe` or the GUI.

## Debian convergence

Baseline files:

```text
debian/lazulinet.py
debian/modules/scanner.py
debian/modules/reporter.py
debian/modules/utils.py
```

Replacement ownership:

| Existing responsibility | v0.3 owner |
|---|---|
| interface enumeration | `lazulinet.platform.debian.interface.DebianInterfaceAdapter` |
| mode state/change | `DebianInterfaceAdapter` |
| passive discovery process | `lazulinet.platform.debian.discovery.DebianDiscoveryAdapter` |
| CSV normalization | `AirodumpCsvParser` |
| background lifecycle | `lazulinet.application.task_runner.TaskRunner` |
| scan/session persistence | `SessionRepository` |
| TXT/JSON reports | `ReportService` |
| CLI composition | `lazulinet.cli` |
| GUI composition | `lazulinet.presentation.app` |

Keep the existing Debian modules temporarily until parity is verified. Remove duplicated safe scanner/reporter code only after real-adapter smoke testing passes.

## Android convergence

Baseline:

```text
android/lazulinet_mobile.py
```

Do not import that monolith from the APK. Its Termux/root assumptions are a different runtime model.

The packaged GUI uses:

```text
Kivy GUI
  → shared application services
  → AndroidWifiAdapter
  → WifiManager / PyJNIus
```

The old Android script can remain as a separate legacy Termux entry point while the APK adapter is validated. This avoids carrying its process-local monitor state and shell-string execution model into the app.

## Data migration

Old scanners overwrite one `networks.json`. v0.3 writes session-scoped data:

```text
<app-data>/sessions/<session-id>/
├── session.json
├── networks.json
├── raw/
└── logs/
```

Do not overwrite or delete old output during the first migration pass. If historical `networks.json` import is desired, implement it as a one-way importer into a new session.

## Validation gates before removing old safe modules

1. `python -m pytest` passes.
2. `python -m compileall -q lazulinet run_gui.py scripts/smoke_gui.py` passes.
3. `scripts/debian_smoke.sh` passes on a Debian host with Kivy.
4. A real wireless adapter is enumerated correctly.
5. Passive discovery can start, cancel, and preserve its session.
6. A completed scan produces normalized networks and a report.
7. Android debug APK builds.
8. Runtime permission flow is validated on-device.
9. Android results normalize SSID/BSSID/channel/signal correctly.
10. Only after those checks should the duplicated safe root/Debian scanner/reporter paths be retired.

## Explicit non-goal

The v0.3 GUI/runtime does not wire legacy disruption, credential capture/cracking, WPS/PMKID, or rogue-AP operations. Those modules remain outside the default GUI/service registry.
