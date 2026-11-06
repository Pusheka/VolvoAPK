[app]
title = Volvo Telematics Pro
package.name = volvotelematics
package.domain = org.volvo

source.dir = .
# Включваме HTML файла и папката assets
source.include_exts = py,png,jpg,kv,html,js,css,json

version = 1.0.0
# ДОБАВЯМЕ kivy_garden.webview за HTML екрана!
requirements = python3==3.10.12,kivy==2.3.0,https://github.com/kivy-garden/webview/archive/refs/heads/master.zip,pyjnius,android

orientation = portrait
fullscreen = 0

android.permissions = BLUETOOTH, BLUETOOTH_ADMIN, BLUETOOTH_CONNECT, INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, ACCESS_FINE_LOCATION
android.api = 34
android.minapi = 21
android.archs = arm64-v8a
android.accept_sdk_license = True

# Използваме стабилни версии, за да не се бъгне компилацията
android.ndk = 25b
android.build_tools_version = 33.0.2

[buildozer]
log_level = 2
warn_on_root = 0
