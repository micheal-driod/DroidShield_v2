import socket
import threading
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem

class ClientGUI(TabbedPanel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_default_tab = False
        self.client_socket = None
        self.connected = False

        # --- TAB 1: CONNECTION & CHAT ---
        self.tab_connect = TabbedPanelItem(text="Comms Link")
        layout_connect = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Inputs
        self.ip_input = TextInput(text="192.168.1.X", hint_text="Server IP", size_hint=(1, 0.1), multiline=False)
        self.key_input = TextInput(text="ALPHA-TANGO-77", hint_text="Secret Key", size_hint=(1, 0.1), multiline=False, password=True)
        
        # Connect Button
        self.btn_connect = Button(text="ESTABLISH SECURE LINK", size_hint=(1, 0.1), background_color=(0, 0.5, 1, 1))
        self.btn_connect.bind(on_press=self.toggle_connection)
        
        # Chat Display
        self.chat_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.chat_layout.bind(minimum_height=self.chat_layout.setter('height'))
        scroll = ScrollView(size_hint=(1, 0.5))
        scroll.add_widget(self.chat_layout)
        
        # Message Input
        msg_box = BoxLayout(size_hint=(1, 0.1))
        self.msg_input = TextInput(hint_text="Type message...", multiline=False)
        self.btn_send = Button(text="SEND", size_hint=(0.2, 1))
        self.btn_send.bind(on_press=self.send_message)
        msg_box.add_widget(self.msg_input)
        msg_box.add_widget(self.btn_send)
        
        layout_connect.add_widget(Label(text="TARGET IP:", size_hint=(1, 0.05)))
        layout_connect.add_widget(self.ip_input)
        layout_connect.add_widget(Label(text="ENCRYPTION KEY:", size_hint=(1, 0.05)))
        layout_connect.add_widget(self.key_input)
        layout_connect.add_widget(self.btn_connect)
        layout_connect.add_widget(scroll)
        layout_connect.add_widget(msg_box)
        self.tab_connect.add_widget(layout_connect)

        # --- TAB 2: VULNERABILITY SCANNER ---
        self.tab_scan = TabbedPanelItem(text="Scanner")
        layout_scan = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        self.scan_ip_input = TextInput(hint_text="IP to Scan", size_hint=(1, 0.1), multiline=False)
        self.btn_scan = Button(text="RUN PORT VULNERABILITY SCAN", size_hint=(1, 0.1), background_color=(1, 0.5, 0, 1))
        self.btn_scan.bind(on_press=self.run_scan)
        
        self.scan_results = Label(text="Ready to scan...", size_hint=(1, 0.7), valign='top', halign='left')
        self.scan_results.bind(size=self.scan_results.setter('text_size'))
        
        layout_scan.add_widget(Label(text="TARGET RECON:", size_hint=(1, 0.05)))
        layout_scan.add_widget(self.scan_ip_input)
        layout_scan.add_widget(self.btn_scan)
        layout_scan.add_widget(self.scan_results)
        self.tab_scan.add_widget(layout_scan)

        # --- TAB 3: SETTINGS / EXIT ---
        self.tab_settings = TabbedPanelItem(text="System")
        layout_settings = BoxLayout(orientation='vertical', padding=20)
        btn_exit = Button(text="KILL SWITCH (EXIT APP)", background_color=(1, 0, 0, 1))
        btn_exit.bind(on_press=self.exit_app)
        layout_settings.add_widget(btn_exit)
        self.tab_settings.add_widget(layout_settings)

        self.add_widget(self.tab_connect)
        self.add_widget(self.tab_scan)
        self.add_widget(self.tab_settings)

    def log_chat(self, msg, color=(1,1,1,1)):
        Clock.schedule_once(lambda dt: self.chat_layout.add_widget(Label(text=msg, size_hint_y=None, height=40, color=color)))

    def toggle_connection(self, instance):
        if not self.connected:
            threading.Thread(target=self.connect_to_server, daemon=True).start()
        else:
            self.disconnect()

    def connect_to_server(self):
        ip = self.ip_input.text
        key = self.key_input.text
        
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((ip, 9000))
            
            # Auth Handshake
            req = self.client_socket.recv(1024).decode('utf-8')
            if req == "AUTH_REQUIRED":
                self.client_socket.send(key.encode('utf-8'))
                resp = self.client_socket.recv(1024).decode('utf-8')
                
                if resp == "ACCESS_GRANTED":
                    self.connected = True
                    Clock.schedule_once(lambda dt: self.btn_connect.setter('text')("DISCONNECT"))
                    Clock.schedule_once(lambda dt: self.btn_connect.setter('background_color')((0, 1, 0, 1)))
                    self.log_chat("✅ Secure Link Established", (0, 1, 0, 1))
                    
                    # Start listening
                    threading.Thread(target=self.listen_for_messages, daemon=True).start()
                else:
                    self.log_chat("⛔ ACCESS DENIED: Invalid Key", (1, 0, 0, 1))
                    self.client_socket.close()
        except Exception as e:
            self.log_chat(f"Connection Failed: {e}", (1, 0, 0, 1))

    def listen_for_messages(self):
        while self.connected:
            try:
                msg = self.client_socket.recv(1024).decode('utf-8')
                if msg:
                    self.log_chat(msg)
                else:
                    break
            except:
                break
        self.disconnect()

    def send_message(self, instance):
        if self.connected and self.msg_input.text:
            try:
                msg = self.msg_input.text
                self.client_socket.send(msg.encode('utf-8'))
                self.log_chat(f"You: {msg}", (0.5, 0.5, 1, 1))
                self.msg_input.text = ""
            except:
                self.log_chat("Send Error", (1, 0, 0, 1))

    def disconnect(self):
        self.connected = False
        if self.client_socket:
            self.client_socket.close()
        Clock.schedule_once(lambda dt: self.btn_connect.setter('text')("ESTABLISH SECURE LINK"))
        Clock.schedule_once(lambda dt: self.btn_connect.setter('background_color')((0, 0.5, 1, 1)))
        self.log_chat("Disconnected.", (1, 0.5, 0, 1))

    def run_scan(self, instance):
        target_ip = self.scan_ip_input.text
        if not target_ip:
            return
        
        self.scan_results.text = f"Scanning {target_ip}...\nThis may take a moment."
        threading.Thread(target=self.perform_scan, args=(target_ip,), daemon=True).start()

    def perform_scan(self, ip):
        # Basic common ports
        ports = {21: "FTP", 22: "SSH", 80: "HTTP", 443: "HTTPS", 8080: "Web Proxy"}
        result_text = f"REPORT FOR {ip}:\n"
        
        found_open = False
        for port, name in ports.items():
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.0)
            result = s.connect_ex((ip, port))
            if result == 0:
                result_text += f"[OPEN] Port {port} ({name}) - POTENTIAL VULNERABILITY\n"
                found_open = True
            s.close()
            
        if not found_open:
            result_text += "No common open ports detected (Secure-ish)."
            
        Clock.schedule_once(lambda dt: self.scan_results.setter('text')(result_text))

    def exit_app(self, instance):
        if self.client_socket:
            self.client_socket.close()
        App.get_running_app().stop()

class DroidShieldClient(App):
    def build(self):
        return ClientGUI()

if __name__ == '__main__':
    DroidShieldClient().run()
