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

class ServerGUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=15, spacing=10, **kwargs)
        
        # --- HEADER ---
        self.add_widget(Label(text="[b]DROIDSHIELD HQ (STABLE)[/b]", markup=True, size_hint=(1, 0.1), font_size='22sp'))
        
        # --- CONFIG (Key & IP) ---
        config_box = BoxLayout(orientation='vertical', size_hint=(1, 0.2), spacing=5)
        
        # IP Label
        self.ip_label = Label(text="Initializing Network...", color=(0, 1, 1, 1), font_size='18sp')
        config_box.add_widget(self.ip_label)
        
        # Secret Key Input
        key_row = BoxLayout(spacing=10)
        key_row.add_widget(Label(text="Security Key:", size_hint=(0.3, 1)))
        self.key_input = TextInput(text="ALPHA-77", multiline=False, write_tab=False)
        key_row.add_widget(self.key_input)
        config_box.add_widget(key_row)
        
        self.add_widget(config_box)

        # --- LOG DISPLAY ---
        self.log_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.log_layout.bind(minimum_height=self.log_layout.setter('height'))
        
        scroll = ScrollView(size_hint=(1, 0.6), do_scroll_x=False)
        scroll.add_widget(self.log_layout)
        self.add_widget(scroll)

        # --- CONTROLS ---
        self.btn_stop = Button(text="SHUTDOWN SYSTEM", size_hint=(1, 0.1), background_color=(0.8, 0, 0, 1))
        self.btn_stop.bind(on_press=self.stop_server)
        self.add_widget(self.btn_stop)

        # Internals
        self.server_socket = None
        self.running = False
        self.clients = {}
        
        # Start safely
        threading.Thread(target=self.start_server, daemon=True).start()

    @mainthread
    def log(self, message, color=(1, 1, 1, 1)):
        # This function is now THREAD-SAFE. It will never crash the app.
        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        lbl = Label(
            text=f"[{time_str}] {message}", 
            size_hint_y=None, 
            height=60, 
            color=color, 
            halign='left', 
            text_size=(self.width - 20, None)
        )
        self.log_layout.add_widget(lbl)
        # Auto-scroll could go here if needed

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
        try:
            self.running = True
            host = "0.0.0.0"
            port = 9000
            
            my_ip = self.get_ip()
            Clock.schedule_once(lambda dt: self.ip_label.setter('text')(f"IP: {my_ip} | PORT: {port}"))
            self.log(f"Server Online on {my_ip}", (0, 1, 0, 1))

            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((host, port))
            self.server_socket.listen(5)

            while self.running:
                client_sock, address = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_sock, address), daemon=True).start()
                
        except Exception as e:
            self.log(f"CRITICAL SERVER ERROR: {e}", (1, 0, 0, 1))

    def handle_client(self, client_sock, address):
        ip = address[0]
        self.log(f"Incoming connection: {ip}", (1, 1, 0, 1))
        
        try:
            # 1. Auth Handshake
            client_sock.send("AUTH_REQUIRED".encode('utf-8'))
            client_sock.settimeout(15) # 15s timeout
            
            received_key = client_sock.recv(1024).decode('utf-8').strip()
            
            # Use the key currently in the text box
            required_key = self.key_input.text
            
            if received_key == required_key:
                client_sock.send("ACCESS_GRANTED".encode('utf-8'))
                client_sock.settimeout(None) # Remove timeout for chat
                self.clients[client_sock] = ip
                self.log(f"✅ Verified: {ip}", (0, 1, 0, 1))
                self.broadcast(f"System: Agent {ip} joined.", client_sock)
            else:
                self.log(f"⛔ Blocked {ip} (Wrong Key)", (1, 0, 0, 1))
                client_sock.send("ACCESS_DENIED".encode('utf-8'))
                client_sock.close()
                return

            # 2. Chat Loop
            while self.running:
                data = client_sock.recv(1024)
                if not data: break
                msg = data.decode('utf-8')
                
                log_msg = f"Agent {ip}: {msg}"
                self.log(log_msg)
                self.broadcast(log_msg, client_sock)

        except Exception as e:
            pass # Client disconnected, normal behavior
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
        try:
            if self.server_socket: self.server_socket.close()
        except: pass
        App.get_running_app().stop()

class DroidShieldHQ(App):
    def build(self):
        return ServerGUI()

if __name__ == '__main__':
    DroidShieldHQ().run()
