[app]
title = LazuliNet
package.name = lazulinet
package.domain = com.lamatech
source.dir = .
source.include_exts = py,kv,png,jpg,json,txt
version = 0.2.0
requirements = python3,kivy,pyjnius
orientation = portrait
fullscreen = 0
android.permissions = ACCESS_WIFI_STATE,CHANGE_WIFI_STATE,ACCESS_FINE_LOCATION,NEARBY_WIFI_DEVICES
android.api = 35
android.minapi = 26
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
