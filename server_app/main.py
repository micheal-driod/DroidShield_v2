import socket
import threading
import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.clock import Clock

class ServerGUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=10, spacing=10, **kwargs)
        
        # --- HEADER ---
        self.add_widget(Label(text="[b]DROIDSHIELD HQ SERVER[/b]", markup=True, size_hint=(1, 0.1), font_size='24sp'))
        
        # --- CONFIGURATION SECTION ---
        config_layout = BoxLayout(orientation='vertical', size_hint=(1, 0.15), spacing=5)
        
        # IP Display
        self.ip_label = Label(text="Detecting IP...", color=(0, 1, 0, 1))
        
        # Secret Key Input (The User sets this now!)
        key_layout = BoxLayout(spacing=10)
        key_layout.add_widget(Label(text="Set Network Key:", size_hint=(0.3, 1)))
        self.key_input = TextInput(text="DEFAULT-KEY", multiline=False, write_tab=False)
        key_layout.add_widget(self.key_input)
        
        config_layout.add_widget(self.ip_label)
        config_layout.add_widget(key_layout)
        self.add_widget(config_layout)

        # --- LOG CONSOLE ---
        self.log_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.log_layout.bind(minimum_height=self.log_layout.setter('height'))
        
        scroll = ScrollView(size_hint=(1, 0.6))
        scroll.add_widget(self.log_layout)
        self.add_widget(scroll)

        # --- CONTROLS ---
        self.btn_stop = Button(text="SHUTDOWN SERVER", size_hint=(1, 0.1), background_color=(1, 0, 0, 1))
        self.btn_stop.bind(on_press=self.stop_server)
        self.add_widget(self.btn_stop)

        # Server Variables
        self.server_socket = None
        self.running = False
        self.clients = {} 
        
        # Start Server automatically in background
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
        self.log(f"Server Online. Waiting for agents...")

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.server_socket.listen(5)

        while self.running:
            try:
                client_sock, address = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_sock, address), daemon=True).start()
            except Exception as e:
                if self.running:
                    self.log(f"Error: {e}", (1, 0, 0, 1))

    def handle_client(self, client_sock, address):
        ip = address[0]
        self.log(f"Connection attempt from {ip}...", (1, 1, 0, 1))
        
        try:
            # 1. SECURITY CHECK
            client_sock.send("AUTH_REQUIRED".encode('utf-8'))
            client_sock.settimeout(10)
            received_key = client_sock.recv(1024).decode('utf-8').strip()
            
            # 2. COMPARE WITH THE TEXT BOX ON SCREEN
            # We use the key that is CURRENTLY typed in the box
            current_server_key = self.key_input.text
            
            if received_key == current_server_key:
                # SUCCESS
                self.log(f"✅ Agent {ip} Verified.", (0, 1, 0, 1))
                client_sock.send("ACCESS_GRANTED".encode('utf-8'))
                client_sock.settimeout(None)
                self.clients[client_sock] = ip
                self.broadcast(f"Agent {ip} connected.", client_sock)
            else:
                # FAILURE
                self.log(f"🚨 INTRUDER {ip} KICKED! (Wrong Key)", (1, 0, 0, 1))
                client_sock.send("ACCESS_DENIED".encode('utf-8'))
                client_sock.close()
                return

            # 3. CHAT LOOP
            while self.running:
                msg = client_sock.recv(1024).decode('utf-8')
                if not msg: break
                
                log_msg = f"Agent {ip}: {msg}"
                self.log(log_msg)
                self.broadcast(log_msg, client_sock)

        except:
            pass # Silent disconnect
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
                    pass

    def stop_server(self, instance):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        App.get_running_app().stop()

class DroidShieldHQ(App):
    def build(self):
        return ServerGUI()

if __name__ == '__main__':
    DroidShieldHQ().run()
