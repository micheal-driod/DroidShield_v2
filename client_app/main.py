import socket
import threading
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock, mainthread
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem

class ClientGUI(TabbedPanel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_default_tab = False
        self.client_socket = None
        self.connected = False

        # --- TAB 1: CONNECT ---
        self.tab_connect = TabbedPanelItem(text="Connect")
        layout_connect = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Connection Inputs
        self.ip_input = TextInput(text="", hint_text="Server IP (e.g. 192.168.x.x)", size_hint=(1, 0.1), multiline=False)
        self.key_input = TextInput(text="ALPHA-77", hint_text="Secret Key", size_hint=(1, 0.1), multiline=False)
        
        self.btn_connect = Button(text="CONNECT", size_hint=(1, 0.1), background_color=(0, 0.5, 1, 1))
        self.btn_connect.bind(on_press=self.toggle_connection)
        
        # Chat Area
        self.chat_box = BoxLayout(orientation='vertical', size_hint_y=None)
        self.chat_box.bind(minimum_height=self.chat_box.setter('height'))
        scroll = ScrollView(size_hint=(1, 0.5))
        scroll.add_widget(self.chat_box)
        
        # Send Area
        send_row = BoxLayout(size_hint=(1, 0.1))
        self.msg_input = TextInput(hint_text="Message...", multiline=False)
        btn_send = Button(text="SEND", size_hint=(0.25, 1))
        btn_send.bind(on_press=self.send_message)
        send_row.add_widget(self.msg_input)
        send_row.add_widget(btn_send)
        
        layout_connect.add_widget(Label(text="SERVER DETAILS:", size_hint=(1, 0.05)))
        layout_connect.add_widget(self.ip_input)
        layout_connect.add_widget(self.key_input)
        layout_connect.add_widget(self.btn_connect)
        layout_connect.add_widget(scroll)
        layout_connect.add_widget(send_row)
        self.tab_connect.add_widget(layout_connect)

        # --- TAB 2: SCANNER ---
        self.tab_scan = TabbedPanelItem(text="Scanner")
        layout_scan = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        self.scan_ip = TextInput(hint_text="Target IP to Scan", size_hint=(1, 0.1), multiline=False)
        self.btn_scan = Button(text="START VULNERABILITY SCAN", size_hint=(1, 0.1), background_color=(1, 0.5, 0, 1))
        self.btn_scan.bind(on_press=self.start_scan)
        
        self.scan_output = Label(text="Ready.", size_hint=(1, 0.7), valign='top', halign='left')
        self.scan_output.bind(size=self.scan_output.setter('text_size'))
        
        layout_scan.add_widget(Label(text="RECONNAISSANCE TOOL:", size_hint=(1, 0.05)))
        layout_scan.add_widget(self.scan_ip)
        layout_scan.add_widget(self.btn_scan)
        layout_scan.add_widget(self.scan_output)
        self.tab_scan.add_widget(layout_scan)
        
        self.add_widget(self.tab_connect)
        self.add_widget(self.tab_scan)

    @mainthread
    def log(self, msg, color=(1,1,1,1)):
        # Thread-safe UI update
        lbl = Label(text=msg, size_hint_y=None, height=40, color=color)
        self.chat_box.add_widget(lbl)

    def toggle_connection(self, instance):
        if not self.connected:
            threading.Thread(target=self.connect_thread, daemon=True).start()
        else:
            self.disconnect()

    def connect_thread(self):
        ip = self.ip_input.text.strip()
        key = self.key_input.text.strip()
        if not ip: return

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(5) # Connection timeout
            self.client_socket.connect((ip, 9000))
            
            # Auth
            req = self.client_socket.recv(1024).decode('utf-8')
            if req == "AUTH_REQUIRED":
                self.client_socket.send(key.encode('utf-8'))
                resp = self.client_socket.recv(1024).decode('utf-8')
                
                if resp == "ACCESS_GRANTED":
                    self.connected = True
                    self.update_btn_state(True)
                    self.log("✅ Secure Link Established", (0, 1, 0, 1))
                    threading.Thread(target=self.listen_thread, daemon=True).start()
                else:
                    self.log("⛔ Access Denied (Wrong Key)", (1, 0, 0, 1))
                    self.client_socket.close()
        except Exception as e:
            self.log(f"Connection Failed: {e}", (1, 0, 0, 1))

    def listen_thread(self):
        while self.connected:
            try:
                self.client_socket.settimeout(None)
                msg = self.client_socket.recv(1024).decode('utf-8')
                if msg: self.log(msg)
                else: break
            except: break
        self.disconnect()

    @mainthread
    def update_btn_state(self, connected):
        if connected:
            self.btn_connect.text = "DISCONNECT"
            self.btn_connect.background_color = (0, 1, 0, 1)
        else:
            self.btn_connect.text = "CONNECT"
            self.btn_connect.background_color = (0, 0.5, 1, 1)

    def disconnect(self):
        self.connected = False
        try: self.client_socket.close()
        except: pass
        self.update_btn_state(False)
        self.log("Disconnected.", (1, 0.5, 0, 1))

    def send_message(self, instance):
        if self.connected and self.msg_input.text:
            try:
                msg = self.msg_input.text
                self.client_socket.send(msg.encode('utf-8'))
                self.log(f"You: {msg}", (0.5, 0.5, 1, 1))
                self.msg_input.text = ""
            except:
                self.log("Failed to send.", (1, 0, 0, 1))

    # --- SCANNER LOGIC (Fixed to prevent crashes) ---
    def start_scan(self, instance):
        target = self.scan_ip.text.strip()
        if not target: return
        self.scan_output.text = f"Scanning {target}...\nPlease wait..."
        threading.Thread(target=self.scan_thread, args=(target,), daemon=True).start()

    def scan_thread(self, ip):
        ports = {21: "FTP", 22: "SSH", 80: "HTTP", 443: "HTTPS", 8080: "Proxy"}
        results = []
        
        for port, name in ports.items():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5) # Short timeout to prevent hanging
                res = s.connect_ex((ip, port))
                if res == 0:
                    results.append(f"[OPEN] Port {port} ({name})")
                s.close()
            except Exception as e:
                # Catch errors so app doesn't die
                pass 
        
        final_text = "\n".join(results) if results else "No open ports found."
        self.update_scan_ui(f"Report for {ip}:\n{final_text}")

    @mainthread
    def update_scan_ui(self, text):
        self.scan_output.text = text

class DroidShieldClient(App):
    def build(self):
        return ClientGUI()

if __name__ == '__main__':
    DroidShieldClient().run()
