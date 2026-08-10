# Implementation Status — v0.2

## Completed in this slice

- Shared domain models and typed errors.
- Input validation for interfaces, channels, and durations.
- Session-scoped repository with atomic JSON writes.
- Cancellable background TaskRunner and structured events.
- Robust airodump-ng CSV parser with quoted ESSID support and client association.
- Debian interface inspection/mode adapter using argv-only subprocess calls.
- Debian passive discovery adapter with cancellation and raw artifact preservation.
- Android WifiManager/PyJNIus discovery adapter with no shell execution.
- Shared Kivy GUI screens and runtime factory.
- TXT/JSON report generation from normalized sessions.
- Buildozer Android packaging baseline.
- Hardware-independent unit test suite.

## Validation performed

- `python -m compileall -q lazulinet run_gui.py` — PASS
- `python -m pytest` — PASS, 8 tests
- Static check for `shell=True` under `lazulinet/` — none
- Static check for legacy attack/crack/rogue-AP references under `lazulinet/` — none

## Not yet validated in this environment

- Kivy visual runtime (Kivy is not installed in the execution container).
- Real Debian wireless hardware / airodump-ng integration.
- Android APK build with Buildozer.
- Android device permission flow and WifiManager scan-result behavior.

## Next slice

1. Integrate this package into the original Lazuli-pennet repository checkout.
2. Add real-world scan CSV fixtures from the existing CLI output.
3. Add fake-process integration tests for Debian discovery cancellation/failure paths.
4. Run the Kivy GUI on Debian and refine responsive desktop/touch layout.
5. Build/install Android debug APK and validate runtime permissions and scan normalization.
6. Converge safe CLI scan/report paths onto the same application services.
