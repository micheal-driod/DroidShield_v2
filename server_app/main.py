import socket
import threading
import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.utils import platform

# --- SECURITY CONFIGURATION ---
# ONLY clients with this key can connect. Change this to whatever you want.
SECRET_KEY = "ALPHA-TANGO-77" 

class ServerGUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        
        # Header
        self.add_widget(Label(text="[b]DROIDSHIELD HQ[/b]", markup=True, size_hint=(1, 0.1), font_size='24sp'))
        
        # IP Display
        self.ip_label = Label(text="Initializing...", size_hint=(1, 0.1), color=(0, 1, 0, 1))
        self.add_widget(self.ip_label)

        # Log Console
        self.log_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.log_layout.bind(minimum_height=self.log_layout.setter('height'))
        
        scroll = ScrollView(size_hint=(1, 0.7))
        scroll.add_widget(self.log_layout)
        self.add_widget(scroll)

        # Controls
        btn_layout = BoxLayout(size_hint=(1, 0.1))
        self.btn_stop = Button(text="SHUTDOWN SERVER", background_color=(1, 0, 0, 1))
        self.btn_stop.bind(on_press=self.stop_server)
        btn_layout.add_widget(self.btn_stop)
        self.add_widget(btn_layout)

        self.server_socket = None
        self.running = False
        self.clients = {} # Format: {socket: ip_address}
        
        # Start Server automatically
        threading.Thread(target=self.start_server, daemon=True).start()

    def log(self, message, color=(1, 1, 1, 1)):
        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{time_str}] {message}"
        print(full_msg)
        Clock.schedule_once(lambda dt: self._add_log_label(full_msg, color))

    def _add_log_label(self, text, color):
        lbl = Label(text=text, size_hint_y=None, height=40, color=color, halign='left', text_size=(self.width, None))
        self.log_layout.add_widget(lbl)

    def get_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def start_server(self):
        self.running = True
        host = "0.0.0.0"
        port = 9000
        
        my_ip = self.get_ip()
        Clock.schedule_once(lambda dt: self.ip_label.setter('text')(f"HQ IP: {my_ip} | Port: {port}"))
        self.log(f"Server started on {my_ip}:{port}")

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.server_socket.listen(5)

        while self.running:
            try:
                client_sock, address = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_sock, address), daemon=True).start()
            except Exception as e:
                if self.running:
                    self.log(f"Accept Error: {e}", (1, 0, 0, 1))

    def handle_client(self, client_sock, address):
        ip = address[0]
        self.log(f"Connection attempt from {ip}...", (1, 1, 0, 1))
        
        try:
            # 1. SECURITY CHECK (Authentication)
            client_sock.send("AUTH_REQUIRED".encode('utf-8'))
            
            # Wait for key (Timeout 10s)
            client_sock.settimeout(10)
            received_key = client_sock.recv(1024).decode('utf-8').strip()
            
            if received_key == SECRET_KEY:
                # SUCCESS
                self.log(f"✅ Verified Agent: {ip}", (0, 1, 0, 1))
                client_sock.send("ACCESS_GRANTED".encode('utf-8'))
                client_sock.settimeout(None) # Remove timeout for chat
                self.clients[client_sock] = ip
                self.broadcast(f"Agent {ip} joined the network.", client_sock)
            else:
                # FAILURE - INTRUDER
                self.log(f"🚨 INTRUDER DETECTED from {ip}! Invalid Key: {received_key}", (1, 0, 0, 1))
                client_sock.send("ACCESS_DENIED".encode('utf-8'))
                client_sock.close()
                return

            # 2. CHAT LOOP
            while self.running:
                msg = client_sock.recv(1024).decode('utf-8')
                if not msg:
                    break
                
                # Broadcast message to all other trusted agents
                broadcast_msg = f"Agent {ip}: {msg}"
                self.log(broadcast_msg)
                self.broadcast(broadcast_msg, client_sock)

        except Exception as e:
            self.log(f"Agent {ip} disconnected: {e}", (1, 0.5, 0, 1))
        finally:
            if client_sock in self.clients:
                del self.clients[client_sock]
            client_sock.close()

    def broadcast(self, message, sender_sock):
        for sock in list(self.clients.keys()):
            if sock != sender_sock:
                try:
                    sock.send(message.encode('utf-8'))
                except:
                    sock.close()
                    if sock in self.clients:
                        del self.clients[sock]

    def stop_server(self, instance):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        self.log("Server shutdown initiated.", (1, 0, 0, 1))
        App.get_running_app().stop()

class DroidShieldHQ(App):
    def build(self):
        return ServerGUI()

if __name__ == '__main__':
    DroidShieldHQ().run()
