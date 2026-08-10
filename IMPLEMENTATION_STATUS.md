# Implementation Status — v0.3

## Completed

- Shared domain/application core retained from v0.2.
- Session repository now preserves normalized partial results on cancellation.
- Failed discovery sessions preserve raw diagnostic artifacts.
- Debian discovery adapter has injectable command/process timing boundaries.
- Debian sysfs fallback now filters out non-wireless interfaces when `iw` is unavailable.
- Fake-process Debian integration tests cover:
  - successful artifact parse;
  - cooperative cancellation;
  - process/stderr failure;
  - successful process with missing artifact.
- Android adapter has injectable `WifiManager` and timing boundaries.
- Android tests cover cached/throttled result normalization, channel filtering, and cancellation.
- Android System health reports Wi-Fi enabled and Location Services state where available.
- Shared `lazulinet-safe` CLI added as the safe CLI-convergence reference.
- GUI redesigned for responsive form factors:
  - Debian/wide: sidebar + table/row views;
  - Android/narrow: bottom nav + card views + More screen.
- Live discovery progress/event status is surfaced in the GUI.
- Networks/Reports can use preserved normalized data from cancelled sessions.
- Debian graphical smoke script added.
- Android Buildozer helper added.
- GitHub Actions core + Xvfb/Kivy smoke workflow added.
- Original-baseline migration guide added.

## Validation in this environment

- `python -m compileall -q lazulinet run_gui.py scripts/smoke_gui.py` — PASS.
- `python -m pytest` — PASS, 20 tests.
- `python -m lazulinet.cli --data-dir /tmp/lazulinet-cli-test sessions` — PASS.
- No legacy security-sensitive module imports under the new `lazulinet/` package.
- No `shell=True` calls under the new `lazulinet/` package.

## Environment limitation

A real Kivy visual smoke run could not be executed in this container because Kivy is not preinstalled and the container cannot currently resolve PyPI. `xvfb-run` is available, so `scripts/debian_smoke.sh` is ready to execute unchanged on a Debian checkout once Kivy is installed.

The container also has no wireless test adapter or `airodump-ng`, so real radio discovery is not claimed as validated here.

## External/device validation still required

### Debian

- Install Kivy and run `scripts/debian_smoke.sh`.
- Attach a supported Wi-Fi adapter.
- Verify actual interface mode changes.
- Verify passive discovery start/cancel/complete on hardware.
- Inspect one real generated airodump CSV against the normalized session output.

### Android

- Build the debug APK with Buildozer.
- Install on an API 26+ device, with priority on API 33+ validation.
- Validate runtime Wi-Fi/location permission behavior.
- Validate Location Services disabled/enabled diagnostics.
- Validate throttled/cached scan-result behavior.
- Verify responsive phone UI and OEM-specific scan result normalization.

## Next slice — v0.4

1. Merge this package into the actual `Lazuli-pennet-main` checkout when the original ZIP/repository is available again.
2. Add a one-way importer for old `networks.json` into session-scoped storage.
3. Route the old root/Debian **safe scan/report** commands onto the shared application services.
4. Run the Debian Kivy smoke test on a network-enabled/GUI-capable environment.
5. Run real Wi-Fi adapter validation and capture representative CSV fixtures.
6. Build and device-test the Android debug APK.
7. Refine permissions/result delivery around Android scan callbacks based on device behavior.
