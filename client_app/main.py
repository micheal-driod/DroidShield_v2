import socket
import threading
import os
import queue
import time
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.clock import Clock, mainthread
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.utils import platform

# --- SAFE IMPORTS (Voice Support) ---
try:
    from plyer import tts
except ImportError:
    tts = None

class ClientGUI(TabbedPanel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_default_tab = False
        self.connected = False
        self.client_socket = None
        self.agent_name = "Unknown"
        
        # --- VOICE THREAD ---
        self.voice_queue = queue.Queue()
        threading.Thread(target=self.voice_worker, daemon=True).start()

        # --- IDENTITY CHECK ---
        Clock.schedule_once(self.check_identity, 1)

        # --- LAYOUT CONSTRUCTION ---
        
        # 1. LOGIN BAR
        self.login_box = BoxLayout(size_hint=(1, 0.12), padding=5, spacing=5)
        self.ip_input = TextInput(hint_text="HQ Address (e.g. tcp://...:12345)", multiline=False, size_hint=(0.4, 1), background_color=(0.2, 0.2, 0.2, 1), foreground_color=(1, 1, 1, 1))
        self.key_input = TextInput(hint_text="Secret Key", multiline=False, password=True, size_hint=(0.3, 1), background_color=(0.2, 0.2, 0.2, 1), foreground_color=(1, 1, 1, 1))
        self.btn_connect = Button(text="CONNECT", size_hint=(0.3, 1), background_color=(0, 0.6, 1, 1), bold=True)
        self.btn_connect.bind(on_press=self.toggle_connection)
        
        self.login_box.add_widget(self.ip_input)
        self.login_box.add_widget(self.key_input)
        self.login_box.add_widget(self.btn_connect)

        # 2. CHAT TAB
        self.tab_chat = TabbedPanelItem(text="Chat")
        chat_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        chat_layout.add_widget(self.login_box)
        
        self.chat_history = BoxLayout(orientation='vertical', size_hint_y=None)
        self.chat_history.bind(minimum_height=self.chat_history.setter('height'))
        
        chat_scroll = ScrollView(size_hint=(1, 0.78), do_scroll_x=False)
        chat_scroll.add_widget(self.chat_history)
        
        send_row = BoxLayout(size_hint=(1, 0.1), spacing=5)
        self.txt_input = TextInput(hint_text="Type Secure Message...", multiline=False, background_color=(0.15, 0.15, 0.15, 1), foreground_color=(1, 1, 1, 1))
        btn_send = Button(text="SEND", size_hint=(0.25, 1), background_color=(0, 0.8, 0, 1))
        btn_send.bind(on_press=self.send_chat)
        
        send_row.add_widget(self.txt_input)
        send_row.add_widget(btn_send)
        chat_layout.add_widget(chat_scroll)
        chat_layout.add_widget(send_row)
        self.tab_chat.add_widget(chat_layout)

        # 3. RADIO TAB
        self.tab_radio = TabbedPanelItem(text="Radio")
        radio_layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        radio_label = Label(text="[b]TACTICAL VOICE LINK[/b]", markup=True, font_size='24sp', size_hint=(1, 0.15), color=(1, 0.8, 0, 1))
        self.radio_status = Label(text="Status: Radio Silence", font_size='18sp', color=(0.5, 0.5, 0.5, 1))
        self.radio_input = TextInput(hint_text="Enter text to Broadcast...", size_hint=(1, 0.25), background_color=(0.1, 0.1, 0.1, 1), foreground_color=(0, 1, 0, 1), font_size='18sp')
        self.btn_ptt = Button(text="TRANSMIT VOICE", size_hint=(1, 0.2), background_color=(0.8, 0, 0, 1), font_size='20sp', bold=True)
        self.btn_ptt.bind(on_press=self.send_radio)
        
        radio_layout.add_widget(radio_label)
        radio_layout.add_widget(self.radio_status)
        radio_layout.add_widget(self.radio_input)
        radio_layout.add_widget(self.btn_ptt)
        radio_layout.add_widget(Label(size_hint=(1, 0.2)))
        self.tab_radio.add_widget(radio_layout)

        # 4. SCANNER TAB
        self.tab_scan = TabbedPanelItem(text="Scanner")
        scan_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        scan_header = Label(text="NETWORK VULNERABILITY SCANNER", size_hint=(1, 0.1), bold=True)
        self.scan_ip = TextInput(hint_text="Target IP", size_hint=(1, 0.1), multiline=False)
        btn_scan = Button(text="INITIATE SCAN", size_hint=(1, 0.15), background_color=(1, 0.5, 0, 1))
        btn_scan.bind(on_press=self.start_scan)
        self.scan_res = Label(text="System Ready.", size_hint=(1, 0.65), valign='top', halign='left')
        self.scan_res.bind(size=self.scan_res.setter('text_size'))
        
        scan_layout.add_widget(scan_header)
        scan_layout.add_widget(self.scan_ip)
        scan_layout.add_widget(btn_scan)
        scan_layout.add_widget(self.scan_res)
        self.tab_scan.add_widget(scan_layout)

        self.add_widget(self.tab_chat)
        self.add_widget(self.tab_radio)
        self.add_widget(self.tab_scan)

    # --- IDENTITY ---
    def check_identity(self, dt):
        if os.path.exists("identity.txt"):
            try:
                with open("identity.txt", "r") as f: self.agent_name = f.read().strip()
                self.log(f"Identity Loaded: [b]{self.agent_name}[/b]", (0, 1, 1, 1))
            except: self.show_name_popup()
        else: self.show_name_popup()

    def show_name_popup(self):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text="INITIAL SETUP\nEnter Agent Callsign:", halign='center'))
        self.name_input = TextInput(multiline=False, size_hint=(1, 0.3), font_size='18sp')
        content.add_widget(self.name_input)
        btn_confirm = Button(text="CONFIRM", size_hint=(1, 0.3), background_color=(0, 1, 0, 1))
        btn_confirm.bind(on_press=self.save_identity)
        content.add_widget(btn_confirm)
        self.popup = Popup(title="CLASSIFIED ACCESS", content=content, size_hint=(0.8, 0.4), auto_dismiss=False)
        self.popup.open()

    def save_identity(self, instance):
        name = self.name_input.text.strip().upper()
        if name and len(name) > 1:
            try:
                with open("identity.txt", "w") as f: f.write(name)
                self.agent_name = name
                self.popup.dismiss()
                self.log(f"Welcome, Agent [b]{name}[/b].", (0, 1, 0, 1))
            except: pass

    # --- HELPERS ---
    @mainthread
    def log(self, msg, color=(1, 1, 1, 1)):
        lbl = Label(text=msg, size_hint_y=None, height=40, color=color, markup=True, halign='left', text_size=(self.width*0.9, None))
        self.chat_history.add_widget(lbl)

    @mainthread
    def update_status(self, connected):
        if connected:
            self.btn_connect.text = "DISCONNECT"
            self.btn_connect.background_color = (1, 0, 0, 1)
            self.radio_status.text = "Status: CHANNEL OPEN"
            self.radio_status.color = (0, 1, 0, 1)
        else:
            self.btn_connect.text = "CONNECT"
            self.btn_connect.background_color = (0, 0.6, 1, 1)
            self.radio_status.text = "Status: DISCONNECTED"
            self.radio_status.color = (0.5, 0.5, 0.5, 1)

    @mainthread
    def set_radio_feedback(self, text):
        self.radio_status.text = text

    @mainthread
    def update_scan_result(self, text):
        self.scan_res.text = text

    # ==================================================
    #        THE PROTOCOL: "PASSIVE LISTENING"
    # ==================================================
    def toggle_connection(self, instance):
        if not self.connected:
            threading.Thread(target=self.connect_thread, daemon=True).start()
        else:
            self.disconnect()

    def connect_thread(self):
        # 1. PARSE ADDRESS
        raw_input = self.ip_input.text.strip()
        key = self.key_input.text.strip()
        
        # REMOVE PREFIXES
        raw_input = raw_input.replace("tcp://", "").replace("http://", "").replace(" ", "")
        
        # EXTRACT PORT
        target_host = raw_input
        target_port = 9000 # Default fallback
        if ":" in raw_input:
            try:
                parts = raw_input.split(":")
                target_port = int(parts[-1]) # Last part is always port
                target_host = ":".join(parts[:-1]) # Rejoin the rest (IP/Domain)
            except: 
                self.log("Invalid Address Format", (1, 0, 0, 1))
                return

        self.log(f"Dialing {target_host} : {target_port}...", (1, 1, 0, 1))

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(15) 
            self.client_socket.connect((target_host, target_port))

            self.log("Secure Line Connected. Waiting for HQ Signal...", (1, 1, 0, 1))

            # STEP 1: WAIT FOR AUTH BEACON (LOOP)
            # We passively listen. The server will keep sending "AUTH".
            # As soon as we catch one "AUTH", we proceed.
            buffer = ""
            found_auth = False
            start_time = time.time()
            
            while time.time() - start_time < 30: # 30s timeout
                try:
                    chunk = self.client_socket.recv(1024).decode('utf-8', errors='ignore')
                    if not chunk: break 
                    buffer += chunk
                    if "AUTH" in buffer:
                        found_auth = True
                        break
                except socket.timeout: pass
                except: break

            if found_auth:
                # STEP 2: SEND KEY
                self.client_socket.send(key.encode('utf-8'))
                self.log("Signal Detected. Sending Key...", (1, 1, 0, 1))
                
                # STEP 3: WAIT FOR FINAL OK
                try:
                    self.client_socket.settimeout(10)
                    resp = self.client_socket.recv(1024).decode('utf-8')
                    if "OK" in resp:
                        self.client_socket.settimeout(None) 
                        self.connected = True
                        self.update_status(True)
                        self.log("[b]ENCRYPTED UPLINK ESTABLISHED[/b]", (0, 1, 0, 1))
                        threading.Thread(target=self.listen_thread, daemon=True).start()
                    else:
                        self.log(f"[b]ACCESS DENIED:[/b] {resp}", (1, 0, 0, 1))
                        self.client_socket.close()
                except:
                    self.log("Server timed out checking key.", (1, 0, 0, 1))
                    self.client_socket.close()
            else:
                self.log("[b]ERROR:[/b] HQ did not send AUTH Beacon.", (1, 0, 0, 1))
                self.client_socket.close()

        except Exception as e:
            self.log(f"Connection Error: {e}", (1, 0, 0, 1))

    # --- LISTENING LOOP ---
    def listen_thread(self):
        while self.connected:
            try:
                msg = self.client_socket.recv(1024).decode('utf-8')
                if not msg: break
                
                if "RADIO:" in msg:
                    parts = msg.split("RADIO:")
                    content = parts[-1].strip()
                    if content:
                        self.log(f"[VOICE] {content}", (1, 1, 0, 1))
                        self.voice_queue.put(content)
                else:
                    self.log(msg)
            except: break
        self.disconnect()

    def disconnect(self):
        self.connected = False
        try: self.client_socket.close()
        except: pass
        self.update_status(False)
        self.log("Link Terminated.", (1, 0.5, 0, 1))

    # --- VOICE LOGIC ---
    def voice_worker(self):
        pc_engine = None
        if platform != 'android':
            try:
                import pyttsx3
                pc_engine = pyttsx3.init()
                pc_engine.setProperty('rate', 150)
            except: pass

        while True:
            text = self.voice_queue.get()
            if text is None: break
            try:
                if platform == 'android':
                    if tts: 
                        tts.speak(text)
                        time.sleep(1.5)
                else:
                    if pc_engine:
                        pc_engine.say(text)
                        pc_engine.runAndWait()
            except: pass
            finally: self.voice_queue.task_done()

    # --- UI ACTIONS ---
    def send_chat(self, instance):
        if self.connected and self.txt_input.text:
            msg = self.txt_input.text
            try:
                self.client_socket.send(f"[{self.agent_name}] {msg}".encode('utf-8'))
                self.log(f"[b]You:[/b] {msg}", (0.5, 0.5, 1, 1))
                self.txt_input.text = ""
            except: pass

    def send_radio(self, instance):
        if self.connected and self.radio_input.text:
            msg = self.radio_input.text
            try:
                self.client_socket.send(f"RADIO: {self.agent_name} says: {msg}".encode('utf-8'))
                self.set_radio_feedback(f"Transmitting: '{msg}'")
                self.radio_input.text = ""
            except: self.set_radio_feedback("Transmission Error")

    def start_scan(self, instance):
        target = self.scan_ip.text.strip()
        if target:
            self.update_scan_result(f"Scanning {target}...")
            threading.Thread(target=self.scan_thread, args=(target,), daemon=True).start()

    def scan_thread(self, ip):
        ports = {21: "FTP", 22: "SSH", 80: "HTTP", 443: "HTTPS", 8080: "PROXY"}
        res = []
        for p, n in ports.items():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)
                if s.connect_ex((ip, p)) == 0: res.append(f"OPEN: Port {p} ({n})")
                s.close()
            except: pass
        self.update_scan_result(f"SCAN REPORT FOR {ip}:\n\n" + ("\n".join(res) if res else "No open ports found."))

class DroidShieldClient(App):
    def build(self):
        return ClientGUI()

if __name__ == '__main__':
    DroidShieldClient().run()
