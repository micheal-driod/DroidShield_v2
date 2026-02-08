import socket
import threading
import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.clock import Clock, mainthread
from kivy.utils import platform

# --- CONFIGURATION ---
PORT = 9000

class ServerGUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=15, spacing=10, **kwargs)
        
        # 1. HEADER
        self.add_widget(Label(text="[b]DROIDSHIELD COMMAND CENTER[/b]", markup=True, size_hint=(1, 0.08), font_size='22sp', color=(0, 1, 0, 1)))
        
        # 2. SERVER CONTROLS (Key & Power)
        control_box = BoxLayout(size_hint=(1, 0.1), spacing=10)
        self.key_input = TextInput(text="ALPHA-77", multiline=False, password=True, size_hint=(0.4, 1), hint_text="Secret Key")
        self.btn_power = Button(text="INITIALIZE SYSTEM", background_color=(0, 1, 0, 1), bold=True)
        self.btn_power.bind(on_press=self.toggle_server)
        
        control_box.add_widget(Label(text="KEY:", size_hint=(0.1, 1)))
        control_box.add_widget(self.key_input)
        control_box.add_widget(self.btn_power)
        self.add_widget(control_box)

        # 3. MONITORING DASHBOARD (Split View)
        dashboard = BoxLayout(size_hint=(1, 0.4), spacing=10)
        
        # Left: Active Agents
        agent_box = BoxLayout(orientation='vertical')
        agent_box.add_widget(Label(text="[b]ACTIVE AGENTS[/b]", markup=True, size_hint=(1, 0.15), color=(0, 1, 1, 1)))
        self.agent_list_lbl = Label(text="No Agents Connected", valign='top', halign='left')
        self.agent_list_lbl.bind(size=self.agent_list_lbl.setter('text_size'))
        agent_box.add_widget(self.agent_list_lbl)
        
        # Right: Security & Block List
        security_box = BoxLayout(orientation='vertical')
        security_box.add_widget(Label(text="[b]BLOCKED INTRUDERS[/b]", markup=True, size_hint=(1, 0.15), color=(1, 0, 0, 1)))
        
        # Spinner to select IP to unblock
        self.block_spinner = Spinner(text='Select IP to Unblock', values=(), size_hint=(1, 0.2))
        self.btn_unblock = Button(text="UNBLOCK SELECTED", size_hint=(1, 0.2), background_color=(1, 0.5, 0, 1))
        self.btn_unblock.bind(on_press=self.unblock_ip)
        
        self.blocked_lbl = Label(text="System Secure.", valign='top', halign='left', color=(1, 0.3, 0.3, 1))
        self.blocked_lbl.bind(size=self.blocked_lbl.setter('text_size'))
        
        security_box.add_widget(self.blocked_lbl)
        security_box.add_widget(self.block_spinner)
        security_box.add_widget(self.btn_unblock)
        
        dashboard.add_widget(agent_box)
        dashboard.add_widget(security_box)
        self.add_widget(dashboard)

        # 4. LIVE LOGS
        self.add_widget(Label(text="SYSTEM LOGS:", size_hint=(1, 0.05)))
        self.log_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.log_layout.bind(minimum_height=self.log_layout.setter('height'))
        
        scroll = ScrollView(size_hint=(1, 0.35))
        scroll.add_widget(self.log_layout)
        self.add_widget(scroll)

        # INTERNALS
        self.server_socket = None
        self.running = False
        self.clients = {}         # socket -> ip
        self.failed_attempts = {} # ip -> count
        self.blocked_ips = []     # list of strings

    # --- UI UPDATES ---
    @mainthread
    def log(self, msg, color=(1, 1, 1, 1)):
        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        lbl = Label(text=f"[{time_str}] {msg}", size_hint_y=None, height=40, color=color, markup=True, halign='left', text_size=(self.width, None))
        self.log_layout.add_widget(lbl)

    @mainthread
    def update_lists(self):
        # Update Active Agents
        if self.clients:
            agents = "\n".join([f"• {ip}" for ip in self.clients.values()])
            self.agent_list_lbl.text = agents
        else:
            self.agent_list_lbl.text = "No Agents Connected"

        # Update Blocked List
        if self.blocked_ips:
            blocked = "\n".join([f"• {ip}" for ip in self.blocked_ips])
            self.blocked_lbl.text = blocked
            self.block_spinner.values = self.blocked_ips
        else:
            self.blocked_lbl.text = "System Secure."
            self.block_spinner.values = ()
            self.block_spinner.text = "No Blocked IPs"

    # --- SERVER LOGIC ---
    def toggle_server(self, instance):
        if not self.running:
            self.running = True
            self.btn_power.text = "SHUTDOWN SYSTEM"
            self.btn_power.background_color = (1, 0, 0, 1)
            self.key_input.disabled = True
            threading.Thread(target=self.start_server, daemon=True).start()
        else:
            self.stop_server()

    def unblock_ip(self, instance):
        target = self.block_spinner.text
        if target in self.blocked_ips:
            self.blocked_ips.remove(target)
            if target in self.failed_attempts:
                del self.failed_attempts[target]
            self.log(f"Manual Override: Unblocked {target}", (0, 1, 0, 1))
            self.update_lists()

    def start_server(self):
        try:
            host = "0.0.0.0"
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            
            self.log(f"Server Initialized on {ip}", (0, 1, 1, 1))

            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((host, PORT))
            self.server_socket.listen(5)

            while self.running:
                client_sock, address = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_sock, address), daemon=True).start()

        except Exception as e:
            self.log(f"Server Error: {e}", (1, 0, 0, 1))
            self.stop_server()

    def handle_client(self, client_sock, address):
        ip = address[0]
        
        # 1. BLOCK CHECK
        if ip in self.blocked_ips:
            client_sock.close()
            return

        self.log(f"Verifying: {ip}...", (1, 1, 0, 1))

        try:
            client_sock.send("AUTH".encode('utf-8'))
            client_sock.settimeout(10)
            key = client_sock.recv(1024).decode('utf-8').strip()
            
            if key == self.key_input.text:
                # SUCCESS
                client_sock.send("OK".encode('utf-8'))
                client_sock.settimeout(None)
                
                self.clients[client_sock] = ip
                if ip in self.failed_attempts: del self.failed_attempts[ip]
                
                self.log(f"✅ Access Granted: {ip}", (0, 1, 0, 1))
                self.update_lists()
                
                # CHAT/RADIO LOOP
                while self.running:
                    msg = client_sock.recv(1024).decode('utf-8')
                    if not msg: break
                    
                    full_msg = f"Agent {ip}: {msg}"
                    self.log(full_msg)
                    self.broadcast(full_msg, client_sock)
            else:
                # FAIL
                client_sock.send("FAIL".encode('utf-8'))
                self.handle_fail(ip)
                client_sock.close()

        except: pass
        finally:
            if client_sock in self.clients:
                del self.clients[client_sock]
                self.update_lists()
            try: client_sock.close()
            except: pass

    def handle_fail(self, ip):
        count = self.failed_attempts.get(ip, 0) + 1
        self.failed_attempts[ip] = count
        self.log(f"⚠️ Auth Fail {count}/3 for {ip}", (1, 0.5, 0, 1))
        
        if count >= 3:
            if ip not in self.blocked_ips:
                self.blocked_ips.append(ip)
                self.log(f"🚨 BLOCKED INTRUDER: {ip}", (1, 0, 0, 1))
                self.update_lists()

    def broadcast(self, msg, sender_sock):
        for sock in list(self.clients.keys()):
            if sock != sender_sock:
                try: sock.send(msg.encode('utf-8'))
                except: pass

    def stop_server(self):
        self.running = False
        try: self.server_socket.close()
        except: pass
        self.btn_power.text = "INITIALIZE SYSTEM"
        self.btn_power.background_color = (0, 1, 0, 1)
        self.key_input.disabled = False
        self.log("System Shutdown.", (1, 0.5, 0, 1))

class DroidShieldHQ(App):
    def build(self):
        return ServerGUI()

if __name__ == '__main__':
    DroidShieldHQ().run()
