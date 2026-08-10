[app]
title = LazuliNet
package.name = lazulinet
package.domain = com.lamatech
source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,svg,json,txt
source.exclude_dirs = tests,scripts,.github,modules,debian,android,packaging,dist,build,.git,.venv,.venv-linux
version = 0.4.0
requirements = python3==3.14.2,kivy==2.3.1,pyjnius==1.7.0
orientation = portrait
fullscreen = 0
android.permissions = android.permission.ACCESS_WIFI_STATE,android.permission.CHANGE_WIFI_STATE,android.permission.ACCESS_FINE_LOCATION,android.permission.NEARBY_WIFI_DEVICES
android.api = 35
android.minapi = 26
android.ndk = 28c
android.ndk_api = 26
android.archs = arm64-v8a,armeabi-v7a
android.accept_sdk_license = True

# Reproducible python-for-Android toolchain.
# Stable release v2026.05.09 resolves to commit:
# 58d21141f17c889bf8585f5665921d72028f8831
p4a.branch = develop
p4a.commit = 58d21141f17c889bf8585f5665921d72028f8831
p4a.bootstrap = sdl2


[buildozer]
log_level = 2
warn_on_root = 1
