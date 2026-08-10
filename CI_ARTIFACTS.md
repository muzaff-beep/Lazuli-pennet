# GitHub Actions artifacts

The `LazuliNet GUI Core` workflow now publishes artifacts for every run.

## Diagnostic artifacts

- `pytest-results-python-3.10`
- `pytest-results-python-3.12`
- `kivy-smoke-log`

The diagnostic uploads use `if: always()` so logs/results are still retained
when the relevant test step fails after producing output.

## Distributable artifact

After both Python core-test jobs and the Kivy smoke job succeed, the
`build-artifacts` job uploads:

- `dist/lazulinet_gui-*.whl`
- `dist/Lazuli-pennet-<short-sha>.zip`
- `dist/SHA256SUMS.txt`

The GitHub artifact name is:

`lazulinet-build-<full-commit-sha>`

Retention:
- diagnostic artifacts: 14 days
- distributable build: 30 days

APK and Debian/AppImage artifacts are intentionally not fabricated here; they
should be uploaded from real platform build jobs when those jobs are added.
