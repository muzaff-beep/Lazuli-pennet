# LazuliNet v0.4 Migration Guide

Target baseline: `Lazuli-pennet-main.zip`, revision marker `280c9ca1639a7e72d7f0705d5bac16e5f82d008c` from the 2026-08-10 architecture review.

## Objective

Move the safe/admin surface of the existing root, Debian, and Android implementations onto one shared application core while preserving historical passive-discovery data and keeping security-sensitive legacy modules outside the GUI/service registry.

## Add the shared package first

Copy these v0.4 paths into the original repository root:

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

The old files can remain untouched while parity is established.

## Import historical discovery data

Dry-run first:

```bash
python -m lazulinet.cli --data-dir ./lazulinet-data \
  migrate-legacy /path/to/Lazuli-pennet-main --dry-run
```

Then import:

```bash
python -m lazulinet.cli --data-dir ./lazulinet-data \
  migrate-legacy /path/to/Lazuli-pennet-main
```

The importer searches these known safe output locations:

```text
networks.json
output/networks.json
debian/networks.json
debian/output/networks.json
sessions/*/networks.json
data/sessions/*/networks.json
```

It reads JSON only. It never imports or executes the legacy scanner/attack modules.

Each imported source becomes a new structured session and the original JSON is copied to:

```text
<app-data>/sessions/<session-id>/raw/legacy-networks.json
```

A SHA-256 index prevents accidental repeated imports. Use `--force` only when a deliberate duplicate migration is required.

## Verify migrated sessions

```bash
python -m lazulinet.cli --data-dir ./lazulinet-data verify
```

Or a single session:

```bash
python -m lazulinet.cli --data-dir ./lazulinet-data verify <session-id>
```

Verification checks observation counts and recorded raw-artifact existence.

## Root CLI convergence

Current baseline entry point:

```text
lazulinet.py
```

Safe commands should be migrated to the shared services rather than importing the old scanner/reporter directly:

```text
old root CLI scan/report
        ↓
lazulinet.platform.factory.create_runtime()
        ↓
InterfaceService / DiscoveryService / ReportService
```

The `lazulinet-safe` CLI is the reference composition.

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

| Existing responsibility | v0.4 owner |
|---|---|
| interface enumeration | `lazulinet.platform.debian.interface.DebianInterfaceAdapter` |
| mode state/change | `DebianInterfaceAdapter` |
| passive discovery process | `lazulinet.platform.debian.discovery.DebianDiscoveryAdapter` |
| CSV normalization | `AirodumpCsvParser` |
| background lifecycle | `TaskRunner` |
| scan/session persistence | `SessionRepository` |
| historical data import | `LegacyMigrationService` |
| TXT/JSON/ZIP reports | `ReportService` |
| CLI composition | `lazulinet.cli` |
| GUI composition | `lazulinet.presentation.app` |

Keep the existing Debian modules until real-adapter smoke testing passes.

## Android convergence

Baseline:

```text
android/lazulinet_mobile.py
```

Do not import that monolith from the APK. The packaged GUI uses:

```text
Kivy GUI
  → shared application services
  → AndroidWifiAdapter
  → WifiManager / PyJNIus
```

The old Android script can remain as a separate legacy Termux entry point while the APK adapter is validated.

## Structured data layout

```text
<app-data>/
├── legacy_imports.json
├── sessions/
│   └── <session-id>/
│       ├── session.json
│       ├── networks.json
│       ├── raw/
│       └── logs/
└── reports/
    ├── report_<session-id>.txt
    ├── report_<session-id>.json
    └── bundle_<session-id>.zip
```

## Validation gates before removing old safe modules

1. `python -m pytest` passes.
2. `python -m compileall -q lazulinet run_gui.py scripts/smoke_gui.py` passes.
3. Migration dry-run sees the expected old output files.
4. Imported sessions pass `verify`.
5. `scripts/debian_smoke.sh` passes on Debian with Kivy.
6. A real wireless adapter is enumerated correctly.
7. Passive discovery can start, cancel, and preserve its session.
8. A completed scan produces normalized networks and a report bundle.
9. Android debug APK builds.
10. Runtime permission flow is validated on-device.
11. Android results normalize SSID/BSSID/channel/signal correctly.
12. Only then retire duplicated safe root/Debian scanner/reporter paths.

## Explicit non-goal

The v0.4 GUI/runtime does not wire legacy disruption, credential capture/cracking, WPS/PMKID, or rogue-AP operations.
