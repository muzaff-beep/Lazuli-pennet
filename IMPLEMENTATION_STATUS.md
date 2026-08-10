# Implementation Status — v0.4

## Completed

- All v0.3 shared-core, Debian, Android, responsive GUI, CLI, smoke, and CI work retained.
- Added `LegacyMigrationService` for one-way import of historical `networks.json` discovery output.
- Added common legacy shape/field normalization and BSSID deduplication.
- Added client/station list merging during duplicate normalization.
- Added SHA-256 migration index; repeated source imports are skipped unless forced.
- Original legacy JSON is copied into the new session's `raw/` artifacts.
- Added session integrity verification:
  - normalized networks file presence;
  - stored vs actual network count;
  - recorded artifact existence.
- Added CLI commands:
  - `migrate-legacy`;
  - `verify`;
  - `report --format bundle`.
- Added Debian Migration GUI screen with Inspect / Import / Verify operations.
- Added portable ZIP session bundle containing session metadata, normalized observations, verification output, and available raw artifacts.
- Version metadata bumped to `0.4.0`.

## Validation in this environment

- `python -m compileall -q lazulinet tests run_gui.py` — PASS.
- `python -m pytest -q` — PASS, **32 tests**.
- End-to-end legacy CLI smoke: dry-run → import → verify → ZIP bundle — PASS.
- `python -m pip wheel . --no-deps --no-build-isolation` — PASS.
- Built wheel reinstalled into an isolated target and imported as `lazulinet.__version__ == 0.4.0` — PASS.
- Migration tests cover field normalization, BSSID-keyed mappings, artifact preservation, dry-run behavior, candidate discovery, idempotency, and forced re-import.
- Report bundle test verifies normalized state + verification + raw artifact inclusion.
- No legacy security-sensitive module imports under `lazulinet/`.
- No `shell=True` calls under `lazulinet/`.

## Environment limitation

A real Kivy visual smoke run is still blocked in this container because Kivy is not installed and external package resolution was unavailable during the previous checkpoint. The provided Xvfb smoke script remains ready for a Debian environment with Kivy installed.

No physical Wi-Fi adapter or Android device is attached here, so hardware discovery and APK device behavior are not claimed as validated.

## External/device validation still required

### Debian

- Install Kivy and run `scripts/debian_smoke.sh`.
- Attach a supported Wi-Fi adapter.
- Verify actual interface mode state and passive discovery start/cancel/complete.
- Compare at least one real airodump CSV against normalized session output.
- Run `migrate-legacy --dry-run` and then import against the real original repository snapshot.

### Android

- Build the debug APK with Buildozer.
- Install on API 26+ device, prioritizing API 33+ validation.
- Validate runtime Wi-Fi/location permission behavior and Location Services diagnostics.
- Validate throttled/cached scan-result behavior on-device.
- Verify responsive phone UI.

## Next slice — v0.5

1. Merge the package into the actual `Lazuli-pennet-main` checkout when available.
2. Route its old root/Debian safe scan/report entry points onto `lazulinet-safe` services.
3. Run migration against real historical `networks.json` samples and retain them as regression fixtures.
4. Perform a real Debian Kivy + wireless-adapter smoke pass.
5. Build/install the Android debug APK and adapt scan result delivery to observed OEM/API behavior.
6. Add signed/hashed bundle manifest fields if the report bundle will be used as an evidence archive rather than an operator convenience export.
