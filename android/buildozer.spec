[app]
title = Pali TTS
package.name = palitts
package.domain = org.sasanarakkha

source.dir = .
source.include_exts = py

version = 1.0

# Versions pinned for proven compatibility
requirements = python3==3.11,kivy==2.3.0,certifi

orientation = portrait
fullscreen = 0

android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 26
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a, armeabi-v7a

# Allow the app to receive text shared from other apps (Share Sheet)
android.manifest.intent_filters =
    <intent-filter>
        <action android:name="android.intent.action.SEND" />
        <category android:name="android.intent.category.DEFAULT" />
        <data android:mimeType="text/plain" />
    </intent-filter>

[buildozer]
log_level = 2
warn_on_root = 1
