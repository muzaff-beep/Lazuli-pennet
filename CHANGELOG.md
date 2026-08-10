# Changelog

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

Security-sensitive legacy operations remain outside the GUI and shared safe CLI registry.
