# LazuliNet Android Toolchain Lock

The Android build is pinned for reproducibility.

## python-for-Android

- Release: `v2026.05.09`
- Release commit: `58d21141f17c889bf8585f5665921d72028f8831`
- Branch used for checkout: `develop`
- Bootstrap: `sdl2`

The release includes Android API 35 updates and NDK r28c compatibility work.

## Android

- Target API: `35`
- Minimum API: `26`
- NDK: `28c`
- NDK API: `26`
- Architectures:
  - `arm64-v8a`
  - `armeabi-v7a`

## Runtime recipes

- Python: `3.14.2`
- Kivy: `2.3.1`
- PyJNIus: `1.7.0`

These versions match the recipes in the pinned python-for-Android commit.

## Host build tooling

The GitHub Actions Android job pins:

- Buildozer `1.6.0`
- Cython `0.29.34`
- setuptools `84.0.0`
- pip `26.2.1`
- virtualenv `21.7.4`
- Eclipse Temurin Java `17`

`actions/cache` hashes `buildozer.spec`, so changing any Android toolchain lock
causes a new Buildozer cache key.
