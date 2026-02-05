import socket
import threading
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from kivy.utils import platform

# --- CONFIG ---
SERVER_IP = '0.0.0.0'
TCP_PORT = 8000
UDP_PORT = 8001
CYBER_GREEN = (0, 1, 0.4, 1)

class ServerApp(App):
    def build(self):
        Window.clearcolor = (0.05, 0.05, 0.05, 1)
        self.tcp_clients = []
        self.udp_clients = set()
        self.running = False
        
        # PREVENT SLEEP (Android)
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.INTERNET, Permission.ACCESS_NETWORK_STATE])
            try:
                from jnius import autoclass
                activity = autoclass('org.kivy.android.PythonActivity').mActivity
                activity.getWindow().addFlags(128) # FLAG_KEEP_SCREEN_ON
            except: pass

        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        layout.add_widget(Label(text="[ DROID SHIELD HQ ]", font_size='28sp', color=CYBER_GREEN, size_hint=(1, 0.15)))
        
        self.ip_lbl = Label(text="FETCHING IP...", color=(0.7,0.7,0.7,1), size_hint=(1, 0.1))
        layout.add_widget(self.ip_lbl)
        self.get_ip()
        
        self.log_box = TextInput(readonly=True, background_color=(0,0,0,1), foreground_color=CYBER_GREEN, size_hint=(1, 0.5))
        layout.add_widget(self.log_box)
        
        self.btn = Button(text="ACTIVATE SERVER", background_color=CYBER_GREEN, bold=True, size_hint=(1, 0.2))
        self.btn.bind(on_press=self.toggle_server)
        layout.add_widget(self.btn)
        
        return layout

    def get_ip(self):
        threading.Thread(target=self._ip_thread, daemon=True).start()
    
    def _ip_thread(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]; s.close()
        except: ip = "127.0.0.1"
        Clock.schedule_once(lambda dt: setattr(self.ip_lbl, 'text', f"HQ IP: {ip}"))

    def log(self, msg):
        Clock.schedule_once(lambda dt: setattr(self.log_box, 'text', self.log_box.text + msg + "\n"))

    def toggle_server(self, i):
        if not self.running:
            self.running = True
            self.btn.text = "STOP SERVER"; self.btn.background_color = (1,0,0,1)
            threading.Thread(target=self.tcp_listen, daemon=True).start()
            threading.Thread(target=self.udp_listen, daemon=True).start()
            self.log("[*] SERVER ONLINE")
        else:
            self.running = False
            self.btn.text = "ACTIVATE SERVER"; self.btn.background_color = CYBER_GREEN
            self.log("[!] SERVER STOPPING...")

    def tcp_listen(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((SERVER_IP, TCP_PORT)); s.listen(5)
        while self.running:
            try:
                c, a = s.accept()
                self.tcp_clients.append(c)
                self.log(f"[+] TCP AGENT: {a[0]}")
                threading.Thread(target=self.handle_tcp, args=(c,), daemon=True).start()
            except: break
        s.close()

    def handle_tcp(self, c):
        while self.running:
            try:
                data = c.recv(1024)
                if not data: break
                for client in self.tcp_clients:
                    if client != c: client.send(data)
            except: break
        if c in self.tcp_clients: self.tcp_clients.remove(c)

    def udp_listen(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind((SERVER_IP, UDP_PORT))
        while self.running:
            try:
                data, addr = s.recvfrom(4096)
                if addr not in self.udp_clients: self.udp_clients.add(addr)
                for client in list(self.udp_clients):
                    if client != addr: s.sendto(data, client)
            except: pass
        s.close()

if __name__ == '__main__': ServerApp().run()