# Changelog

## 0.4.0 — 2026-08-11

- Added one-way legacy `networks.json` migration service.
- Added normalization for common legacy field names and payload shapes.
- Added BSSID deduplication and client/station merging.
- Added SHA-256 migration index and default idempotent import behavior.
- Added `--force` migration override.
- Preserve imported JSON as a raw session artifact.
- Added session integrity verification.
- Added `migrate-legacy` and `verify` CLI commands.
- Added Debian Migration GUI screen with Inspect / Import / Verify actions.
- Added TXT / JSON / portable ZIP report choices.
- ZIP report bundles include session state, normalized observations, verification result, and available raw artifacts.
- Expanded automated suite to 32 tests.

Security-sensitive legacy operations remain outside the GUI and shared safe CLI registry.

## 0.3.0 — 2026-08-11

- Added responsive Kivy shell with Debian sidebar and Android/narrow bottom navigation.
- Added mobile card layouts for interfaces, networks, and sessions.
- Added live discovery progress/status rendering.
- Persist normalized partial observations for cancelled scans.
- Preserve raw diagnostic artifacts for failed scans.
- Added deterministic fake-process Debian integration tests.
- Added injectable Android `WifiManager` adapter and tests.
- Added Android Wi-Fi / Location Services health reporting.
- Added channel filtering for Android normalized scan results.
- Added shared `lazulinet-safe` CLI for safe CLI convergence.
- Added Debian GUI smoke script and Android Buildozer helper.
- Added GitHub Actions core tests and Kivy/Xvfb GUI smoke job.
- Added staged migration guide for the original `Lazuli-pennet-main` baseline.
- Fixed Debian sysfs fallback so non-wireless interfaces are not presented as Wi-Fi interfaces.
