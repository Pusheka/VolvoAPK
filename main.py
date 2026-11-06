import os
import threading
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

try:
    from jnius import autoclass
    from android.runnable import run_on_ui_thread
    
    # Android класове
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    WebView = autoclass('android.webkit.WebView')
    WebViewClient = autoclass('android.webkit.WebViewClient')
    BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
    java_uuid = autoclass('java.util.UUID').fromString("00001101-0000-1000-8000-00805F9B34FB")
    IS_ANDROID = True
except Exception as e:
    print(f"Грешка при инициализация: {e}")
    IS_ANDROID = False

class VolvoTelematicsApp(App):
    def build(self):
        self.title = "Volvo Telematics Pro"
        self.layout = BoxLayout(orientation='vertical')
        
        # Място за WebView (зарежда се след малко)
        self.placeholder = Label(text="Зареждане на интерфейса...")
        self.layout.add_widget(self.placeholder)
        
        self.bt_socket = None
        self.output_stream = None
        self.is_connected = False
        
        if IS_ANDROID:
            Clock.schedule_once(self.setup_android_webview, 0.5)
            threading.Thread(target=self.init_bluetooth, daemon=True).start()
        else:
            self.placeholder.text = "Симулация (Само за Android)"
            
        return self.layout

    @run_on_ui_thread
    def setup_android_webview(self, dt):
        try:
            # 1. Създаваме WebView
            self.webview = WebView(PythonActivity.mActivity)
            self.webview.getSettings().setJavaScriptEnabled(True)
            self.webview.setWebViewClient(WebViewClient())
            
            # 2. Зареждаме HTML файла
            html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'index.html')
            if not os.path.exists(html_path):
                html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')
            self.webview.loadUrl("file://" + html_path)
            
            # 3. Вграждаме WebView в Android Layout (най-сигурният начин)
            activity = PythonActivity.mActivity
            layout = activity.getWindow().getDecorView().findViewById(0x01020002) # android.R.id.content
            layout.addView(self.webview)
            
            # Махаме Kivy placeholder-а (оставяме WebView да заеме целия екран)
            self.layout.remove_widget(self.placeholder)
            
        except Exception as e:
            print(f"Грешка при създаване на WebView: {e}")
            self.placeholder.text = f"Грешка: {e}"

    def update_status(self, text, is_error=False):
        err_flag = "true" if is_error else "false"
        js_code = f"setStatus('{text}', {err_flag});"
        if hasattr(self, 'webview') and IS_ANDROID:
            self.webview.evaluateJavascript(js_code, None)

    def send_js_data(self, json_str):
        safe_str = json_str.replace("'", "\\'")
        js_code = f"updateData('{safe_str}');"
        if hasattr(self, 'webview') and IS_ANDROID:
            self.webview.evaluateJavascript(js_code, None)

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
            
            self.bt_socket = target_device.createInsecureRfcommSocketToServiceRecord(java_uuid)
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
