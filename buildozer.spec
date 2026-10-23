[app]
title = JustMusic!
package.name = justmusic
package.domain = hu.zs420ller
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,json,lrc
version = 1.8.6
# v1.8.6 REV7: kompakt feliratok, vékony ikonok, javított vezérlők és lockscreen fallback
android.numeric_version = 1080607
requirements = python3,kivy,pyjnius,mutagen
# Foreground MediaSession lives in another Android process.
services = music:music_service.py:foreground:foregroundServiceType=mediaPlayback
orientation = portrait
fullscreen = 0
icon.filename = %(source.dir)s/icon.png
android.permissions = POST_NOTIFICATIONS,INTERNET,READ_MEDIA_AUDIO,READ_EXTERNAL_STORAGE,BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_CONNECT,BLUETOOTH_SCAN,WAKE_LOCK,FOREGROUND_SERVICE,FOREGROUND_SERVICE_MEDIA_PLAYBACK
android.api = 36
android.minapi = 24
android.ndk = 28c
android.archs = arm64-v8a
android.accept_sdk_license = True
p4a.branch = develop

[buildozer]
log_level = 2
warn_on_root = 1
