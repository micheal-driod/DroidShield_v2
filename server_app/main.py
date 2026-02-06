import socket
import threading
import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.clock import Clock, mainthread
from kivy.utils import platform

class ServerGUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=15, spacing=10, **kwargs)
        
        # --- HEADER ---
        self.add_widget(Label(text="[b]DROIDSHIELD HQ[/b]", markup=True, size_hint=(1, 0.1), font_size='24sp'))
        
        # --- CONTROLS ---
        # 1. IP Display
        self.ip_label = Label(text="Status: OFFLINE", color=(1, 0.5, 0, 1), font_size='18sp')
        self.add_widget(self.ip_label)
        
        # 2. Key Input
        key_box = BoxLayout(size_hint=(1, 0.1), spacing=5)
        key_box.add_widget(Label(text="Key:", size_hint=(0.3, 1)))
        self.key_input = TextInput(text="ALPHA-77", multiline=False)
        key_box.add_widget(self.key_input)
        self.add_widget(key_box)

        # 3. Start/Stop Button
        self.btn_toggle = Button(text="START SERVER", size_hint=(1, 0.15), background_color=(0, 1, 0, 1), font_size='20sp')
        self.btn_toggle.bind(on_press=self.toggle_server)
        self.add_widget(self.btn_toggle)

        # --- LOG CONSOLE ---
        self.log_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.log_layout.bind(minimum_height=self.log_layout.setter('height'))
        
        scroll = ScrollView(size_hint=(1, 0.5))
        scroll.add_widget(self.log_layout)
        self.add_widget(scroll)

        self.server_socket = None
        self.running = False
        self.clients = {}

    @mainthread
    def log(self, message, color=(1, 1, 1, 1)):
        # Safe logging to screen
        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        lbl = Label(text=f"[{time_str}] {message}", size_hint_y=None, height=50, color=color, text_size=(self.width, None), halign='left')
        self.log_layout.add_widget(lbl)

    def toggle_server(self, instance):
        if not self.running:
            self.running = True
            self.btn_toggle.text = "STOP SERVER"
            self.btn_toggle.background_color = (1, 0, 0, 1)
            threading.Thread(target=self.start_server, daemon=True).start()
        else:
            self.running = False
            self.btn_toggle.text = "START SERVER"
            self.btn_toggle.background_color = (0, 1, 0, 1)
            self.stop_server()

    def get_ip(self):
        try:
            # Quick way to find local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def start_server(self):
        try:
            host = "0.0.0.0"
            port = 9000
            my_ip = self.get_ip()
            
            Clock.schedule_once(lambda dt: self.ip_label.setter('text')(f"ONLINE: {my_ip}"))
            self.log(f"Starting on {my_ip}:{port}...", (0, 1, 1, 1))

            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((host, port))
            self.server_socket.listen(5)

            while self.running:
                client_sock, address = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_sock, address), daemon=True).start()
        
        except OSError as e:
            if self.running: # Only log if we didn't intentionally stop it
                self.log(f"NETWORK ERROR: {e}", (1, 0, 0, 1))
                self.log("Check App Permissions!", (1, 1, 0, 1))
                self.running = False
                Clock.schedule_once(lambda dt: self.reset_ui())
        except Exception as e:
            self.log(f"CRITICAL ERROR: {e}", (1, 0, 0, 1))

    def handle_client(self, client_sock, address):
        ip = address[0]
        self.log(f"Connecting: {ip}", (1, 1, 0, 1))
        
        try:
            client_sock.send("AUTH_REQUIRED".encode('utf-8'))
            client_sock.settimeout(10)
            key_received = client_sock.recv(1024).decode('utf-8').strip()
            
            # Check Key
            expected_key = self.key_input.text
            
            if key_received == expected_key:
                client_sock.send("ACCESS_GRANTED".encode('utf-8'))
                client_sock.settimeout(None)
                self.clients[client_sock] = ip
                self.log(f"Verified: {ip}", (0, 1, 0, 1))
                
                # Chat Loop
                while self.running:
                    msg = client_sock.recv(1024).decode('utf-8')
                    if not msg: break
                    self.log(f"Agent {ip}: {msg}")
                    self.broadcast(f"Agent {ip}: {msg}", client_sock)
            else:
                self.log(f"Blocked {ip} (Bad Key)", (1, 0, 0, 1))
                client_sock.send("ACCESS_DENIED".encode('utf-8'))
        except:
            pass
        finally:
            client_sock.close()
            if client_sock in self.clients: del self.clients[client_sock]

    def broadcast(self, msg, sender):
        for c in list(self.clients.keys()):
            if c != sender:
                try: c.send(msg.encode('utf-8'))
                except: pass

    def stop_server(self):
        try: self.server_socket.close()
        except: pass
        self.log("Server Stopped.", (1, 0.5, 0, 1))
        Clock.schedule_once(lambda dt: self.ip_label.setter('text')("Status: OFFLINE"))

    @mainthread
    def reset_ui(self):
        self.btn_toggle.text = "START SERVER"
        self.btn_toggle.background_color = (0, 1, 0, 1)

class DroidShieldHQ(App):
    def build(self):
        return ServerGUI()

if __name__ == '__main__':
    DroidShieldHQ().run()
