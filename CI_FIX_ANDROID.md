# Android CI hardening

The uploaded Android Actions log does not contain a terminal build failure.
It ends while python-for-Android is configuring CPython for the Android target.

Changes in this revision:

- updates `actions/setup-java@v4` to `actions/setup-java@v5`;
- keeps Eclipse Temurin / Java 17;
- installs the current python-for-Android Ubuntu prerequisite set;
- adds a 90-minute Android job timeout;
- captures the complete Buildozer output to `buildozer.log`;
- uploads `buildozer.log` even if the APK build fails;
- preserves Buildozer's own exit code despite the `yes | ... | tee` pipeline;
- retains the Linux PyInstaller-under-Xvfb fix.

The Android runtime still packages only the safe LazuliNet GUI/core path.
