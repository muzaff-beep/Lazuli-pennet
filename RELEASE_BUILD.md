# LazuliNet executable builds

The repository now contains real platform build automation.

## GitHub Actions output

Workflow: `.github/workflows/platform-builds.yml`

### Android
Artifact: `lazulinet-android-apk`

Contains the installable debug APK and `SHA256SUMS-android.txt`.
The APK targets Android API 35, minimum API 26, and builds ARM64 + ARMv7 ABIs.

### Linux
Artifact: `lazulinet-linux-x86_64`

Contains:
- `LazuliNet-0.4.0-x86_64.AppImage`
- `LazuliNet_0.4.0_amd64.deb`
- checksums
- frozen/AppImage smoke-test logs

The Linux app is frozen with PyInstaller, so end users do not need Python or
Kivy installed. Passive Debian discovery still depends on host wireless tooling
and privileges where the relevant feature requires it; the GUI itself launches
without those tools and reports missing capabilities in System Health.

## Runtime boundary

The packaged Android source excludes the repository's legacy `modules/`,
`debian/`, and `android/` trees. It packages only the shared safe GUI/core and
its Android `WifiManager` adapter.
