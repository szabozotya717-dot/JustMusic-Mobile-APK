[app]

title = JustMusic!
package.name = justmusic
package.domain = hu.zs420ller

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,json,lrc

version = 1.0.0

requirements = python3,kivy

orientation = portrait
fullscreen = 0

icon.filename = %(source.dir)s/icon.png

android.permissions = READ_MEDIA_AUDIO,READ_EXTERNAL_STORAGE
android.api = 36
android.minapi = 24
android.ndk = 28c
android.archs = arm64-v8a
android.accept_sdk_license = True

p4a.branch = develop

[buildozer]
log_level = 2
warn_on_root = 1
