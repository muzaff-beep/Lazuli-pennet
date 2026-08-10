# CI Fix v2

This snapshot fixes the 2026-08-10 CI failures after package discovery was corrected.

## Root cause

The repository contained v0.4 tests/call sites, but two implementation files were still from v0.3:

- `SessionRepository.verify()` / `verify_all()` were missing.
- `ReportService.export_bundle()` was missing.

## Fix

- Restored `verify()` and `verify_all()` in `lazulinet/application/session_repository.py`.
- Restored `export_bundle()` in `lazulinet/application/report_service.py`.
- Retained explicit setuptools package discovery in `pyproject.toml`.
- Kept legacy root/Debian/Android source trees untouched.

## Local validation

- `python -m pytest -q` -> 32 passed
- `python -m compileall -q lazulinet run_gui.py scripts/smoke_gui.py` -> pass
