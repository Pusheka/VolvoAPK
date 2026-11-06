import os
import time
import json
import threading
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout

# ВАЖНО: Използваме kivy_garden.webview вместо несъществуващия kivy.uix.webbrowser
from kivy_garden.webview import WebView

try:
    from jnius import autoclass
    BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
    BluetoothDevice = autoclass('android.bluetooth.BluetoothDevice')
    java_uuid = autoclass('java.util.UUID').fromString("00001101-0000-1000-8000-00805F9B34FB")
    IS_ANDROID = True
except Exception as e:
    print(f"Bluetooth init error: {e}")
    IS_ANDROID = False

class JsBridge:
    """Този клас свързва JavaScript с Python"""
    def __init__(self, app):
        self.app = app
        
    def sendCommand(self, cmd):
        print(f"Команда от JS: {cmd}")
        # Тук можеш да добавиш логика за изпращане на команда по Bluetooth
        if self.app.is_connected and self.app.output_stream:
            try:
                self.app.output_stream.write((cmd + "\n").encode('utf-8'))
                self.app.output_stream.flush()
            except Exception as e:
                print(f"Грешка при изпращане: {e}")

    def sendOTAFile(self, length, byte_array):
        print(f"Получен OTA файл с размер: {length} байта")
        # Тук добави логика за OTA ъпдейт

class VolvoTelematicsApp(App):
    def build(self):
        self.title = "Volvo Telematics Pro"
        self.layout = BoxLayout(orientation='vertical')
        
        # 1. Зареждане на HTML файла
        html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'index.html')
        if not os.path.exists(html_path):
            # Ако файлът не е в assets, го търсим в главната папка
            html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')

        self.webview = WebView(url="file://" + html_path)
        
        # 2. Свързване на JS Bridge (ВАЖНО!)
        self.webview.bind(on_load=self.on_webview_load)
        self.layout.add_widget(self.webview)
        
        self.bt_socket = None
        self.output_stream = None
        self.is_connected = False
        
        if IS_ANDROID:
            threading.Thread(target=self.init_bluetooth, daemon=True).start()
        else:
            Clock.schedule_once(lambda dt: self.update_status("Симулация (Само за Android)"), 1)
            
        return self.layout

    def on_webview_load(self, webview, url):
        # Инжектираме нашия Python обект в JavaScript
        self.webview.evaluate_javascript("""
            window.AndroidBridge = {
                sendCommand: function(cmd) { 
                    window.location.href = 'py://sendCommand/' + cmd; 
                },
                sendOTAFile: function(len, arr) { 
                    window.location.href = 'py://ota/' + len; 
                }
            };
        """)
        print("WebView зареден и Bridge инжектиран.")

    def update_status(self, text, is_error=False):
        err_flag = "true" if is_error else "false"
        # Извикваме JS функцията setStatus в HTML-а
        js_code = f"setStatus('{text}', {err_flag});"
        if hasattr(self, 'webview'):
            self.webview.evaluate_javascript(js_code)

    def send_js_data(self, json_str):
        safe_str = json_str.replace("'", "\\'")
        js_code = f"updateData('{safe_str}');"
        if hasattr(self, 'webview'):
            self.webview.evaluate_javascript(js_code)

    def init_bluetooth(self):
        Clock.schedule_once(lambda dt: self.update_status("Търсене на Volvo-Telematics-BT..."), 0)
        try:
            adapter = BluetoothAdapter.getDefaultAdapter()
            if not adapter or not adapter.isEnabled():
                Clock.schedule_once(lambda dt: self.update_status("Bluetooth е изключен!", True), 0)
                return

            devices = adapter.getBondedDevices().toArray()
            target_device = None
            for d in devices:
                if "Volvo-Telematics-BT" in d.getName():
                    target_device = d
                    break

            if not target_device:
                Clock.schedule_once(lambda dt: self.update_status("Устройството Volvo-Telematics-BT не е сдвоено!", True), 0)
                return

            Clock.schedule_once(lambda dt: self.update_status(f"Свързване с {target_device.getName()}..."), 0)
            
            self.bt_socket = target_device.createRfcommSocketToServiceRecord(java_uuid)
            adapter.cancelDiscovery()
            self.bt_socket.connect()
            
            self.output_stream = self.bt_socket.getOutputStream()
            input_stream = self.bt_socket.getInputStream()
            
            self.is_connected = True
            Clock.schedule_once(lambda dt: self.update_status("Свързан успешно през Bluetooth!"), 0)

            buffer = b""
            while self.is_connected:
                if input_stream.available() > 0:
                    data = input_stream.read()
                    if data != -1:
                        buffer += bytes([data])
                        if b'\n' in buffer:
                            line, buffer = buffer.split(b'\n', 1)
                            line_str = line.decode('utf-8', errors='ignore').strip()
                            if line_str.startswith('{'):
                                Clock.schedule_once(lambda dt, s=line_str: self.send_js_data(s), 0)
        except Exception as e:
            err_msg = str(e)
            self.is_connected = False
            Clock.schedule_once(lambda dt, err=err_msg: self.update_status(f"Грешка: {err}", True), 0)

if __name__ == '__main__':
    VolvoTelematicsApp().run()