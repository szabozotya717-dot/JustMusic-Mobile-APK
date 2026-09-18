[app]
title = JustMusic!
package.name = justmusic
package.domain = hu.zs420ller
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,json,lrc
version = 1.8.0
requirements = python3,kivy,pyjnius,mutagen
orientation = portrait
fullscreen = 0
icon.filename = %(source.dir)s/icon.png
android.permissions = POST_NOTIFICATIONS,INTERNET,READ_MEDIA_AUDIO,READ_EXTERNAL_STORAGE,BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_CONNECT,BLUETOOTH_SCAN
android.api = 36
android.minapi = 24
android.ndk = 28c
android.archs = arm64-v8a
android.accept_sdk_license = True
android.manifest.launch_mode = singleTop
p4a.branch = develop

[buildozer]
log_level = 2
warn_on_root = 1
