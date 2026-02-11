import socket
import threading
import os
import queue
import time
import base64
import hashlib
import traceback

# --- KIVY IMPORTS ---
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

# --- CRYPTO ---
from cryptography.fernet import Fernet

# --- VOICE ---
try:
    from plyer import tts
except ImportError:
    tts = None

class SafeLoader:
    @staticmethod
    def load_identity(obj):
        try:
            if os.path.exists("identity.txt"):
                with open("identity.txt", "r") as f: 
                    obj.agent_name = f.read().strip()
                obj.log(f"Identity: [b]{obj.agent_name}[/b]", (0, 1, 1, 1))
            else:
                obj.show_name_popup()
        except:
            obj.agent_name = "Agent_X"

class ClientGUI(TabbedPanel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_default_tab = False
        self.connected = False
        self.client_socket = None
        self.agent_name = "Unknown"
        self.voice_queue = queue.Queue()
        self.cipher = None 
        
        self._build_ui()
        Clock.schedule_once(self.post_init, 2) 

    def _build_ui(self):
        # LOGIN
        self.login_box = BoxLayout(size_hint=(1, 0.12), padding=5, spacing=5)
        self.ip_input = TextInput(hint_text="HQ Address", multiline=False, size_hint=(0.5, 1))
        self.key_input = TextInput(hint_text="Password", multiline=False, password=True, size_hint=(0.2, 1))
        self.btn_connect = Button(text="LINK", size_hint=(0.3, 1), background_color=(0, 0.6, 1, 1), bold=True)
        self.btn_connect.bind(on_press=self.toggle_connection)
        
        self.login_box.add_widget(self.ip_input)
        self.login_box.add_widget(self.key_input)
        self.login_box.add_widget(self.btn_connect)

        # CHAT
        self.tab_chat = TabbedPanelItem(text="Chat")
        chat_layout = BoxLayout(orientation='vertical', padding=5, spacing=5)
        chat_layout.add_widget(self.login_box)
        
        self.chat_history = BoxLayout(orientation='vertical', size_hint_y=None)
        self.chat_history.bind(minimum_height=self.chat_history.setter('height'))
        
        chat_scroll = ScrollView(size_hint=(1, 0.78))
        chat_scroll.add_widget(self.chat_history)
        
        send_row = BoxLayout(size_hint=(1, 0.1), spacing=5)
        self.txt_input = TextInput(hint_text="Message...", multiline=False)
        btn_send = Button(text="SEND", size_hint=(0.2, 1), background_color=(0, 0.8, 0, 1))
        btn_send.bind(on_press=self.send_chat)
        
        send_row.add_widget(self.txt_input)
        send_row.add_widget(btn_send)
        chat_layout.add_widget(chat_scroll)
        chat_layout.add_widget(send_row)
        self.tab_chat.add_widget(chat_layout)

        # RADIO
        self.tab_radio = TabbedPanelItem(text="Radio")
        radio_layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        radio_label = Label(text="[b]ENCRYPTED VOICE[/b]", markup=True, font_size='24sp', size_hint=(1, 0.15), color=(0, 1, 0, 1))
        self.radio_status = Label(text="Status: Silence", font_size='18sp')
        self.radio_input = TextInput(hint_text="Broadcast...", size_hint=(1, 0.25))
        self.btn_ptt = Button(text="TRANSMIT", size_hint=(1, 0.2), background_color=(0.8, 0, 0, 1))
        self.btn_ptt.bind(on_press=self.send_radio)
        
        radio_layout.add_widget(radio_label)
        radio_layout.add_widget(self.radio_status)
        radio_layout.add_widget(self.radio_input)
        radio_layout.add_widget(self.btn_ptt)
        radio_layout.add_widget(Label(size_hint=(1, 0.2)))
        self.tab_radio.add_widget(radio_layout)

        # SCANNER
        self.tab_scan = TabbedPanelItem(text="Scan")
        scan_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        scan_header = Label(text="NET SCANNER", size_hint=(1, 0.1), bold=True)
        self.scan_ip = TextInput(hint_text="Target IP", size_hint=(1, 0.1), multiline=False)
        btn_scan = Button(text="START", size_hint=(1, 0.15))
        btn_scan.bind(on_press=self.start_scan)
        self.scan_res = Label(text="Ready.", size_hint=(1, 0.65), valign='top', halign='left')
        self.scan_res.bind(size=self.scan_res.setter('text_size'))
        
        scan_layout.add_widget(scan_header)
        scan_layout.add_widget(self.scan_ip)
        scan_layout.add_widget(btn_scan)
        scan_layout.add_widget(self.scan_res)
        self.tab_scan.add_widget(scan_layout)

        self.add_widget(self.tab_chat)
        self.add_widget(self.tab_radio)
        self.add_widget(self.tab_scan)

    def post_init(self, dt):
        threading.Thread(target=self.voice_worker, daemon=True).start()
        SafeLoader.load_identity(self)

    def show_name_popup(self):
        content = BoxLayout(orientation='vertical', padding=10)
        self.name_input = TextInput(multiline=False, hint_text="Agent Name")
        btn = Button(text="CONFIRM")
        btn.bind(on_press=self.save_identity)
        content.add_widget(self.name_input)
        content.add_widget(btn)
        self.popup = Popup(title="IDENTITY", content=content, size_hint=(0.8, 0.3))
        self.popup.open()

    def save_identity(self, instance):
        if self.name_input.text:
            with open("identity.txt", "w") as f: f.write(self.name_input.text)
            self.agent_name = self.name_input.text
            self.popup.dismiss()

    @mainthread
    def log(self, msg, color=(1, 1, 1, 1)):
        self.chat_history.add_widget(Label(text=msg, size_hint_y=None, height=40, color=color, markup=True, halign='left', text_size=(self.width*0.9, None)))

    @mainthread
    def update_status(self, connected):
        self.btn_connect.text = "CUT" if connected else "LINK"
        self.btn_connect.background_color = (1, 0, 0, 1) if connected else (0, 0.6, 1, 1)

    def toggle_connection(self, instance):
        if not self.connected:
            threading.Thread(target=self.connect_thread, daemon=True).start()
        else:
            self.disconnect()

    def connect_thread(self):
        raw = self.ip_input.text.strip()
        pwd = self.key_input.text.strip()
        
        if not pwd:
            self.log("Error: Password Required", (1,0,0,1))
            return

        # GENERATE KEY
        try:
            key = base64.urlsafe_b64encode(hashlib.sha256(pwd.encode()).digest())
            self.cipher = Fernet(key)
        except Exception as e:
            self.log(f"Key Gen Error: {e}")
            return

        # PARSE ADDRESS
        raw = raw.replace("tcp://", "").replace("http://", "")
        host, port = raw.split(":")[0], 9000
        if ":" in raw:
            try: port = int(raw.split(":")[-1])
            except: pass

        self.log(f"Dialing {host}:{port}...")

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(15) 
            self.client_socket.connect((host, port))

            self.log("Connected. Waiting for Encryption Handshake...", (1, 1, 0, 1))

            # WAIT FOR ENCRYPTED BEACON
            # If we have the wrong key, we won't be able to decrypt the "AUTH_REQUEST"
            start_time = time.time()
            found_auth = False
            
            while time.time() - start_time < 30: 
                try:
                    data = self.client_socket.recv(4096)
                    if not data: break
                    
                    try:
                        decrypted = self.cipher.decrypt(data).decode()
                        if "AUTH_REQUEST" in decrypted:
                            found_auth = True
                            break
                    except:
                        pass # Wrong key or garbage data, keep listening
                except socket.timeout: pass
                except: break

            if found_auth:
                # Send Encrypted Reply
                self.client_socket.send(self.cipher.encrypt(b"AUTH_ACK"))
                
                # Wait for Final Access Grant
                try:
                    data = self.client_socket.recv(4096)
                    msg = self.cipher.decrypt(data).decode()
                    if "ACCESS_GRANTED" in msg:
                        self.client_socket.settimeout(None)
                        self.connected = True
                        self.update_status(True)
                        self.log("[b]SECURE TUNNEL ESTABLISHED[/b]", (0, 1, 0, 1))
                        threading.Thread(target=self.listen_thread, daemon=True).start()
                    else:
                        self.log("Access Denied", (1,0,0,1))
                        self.client_socket.close()
                except:
                    self.log("Handshake Failed (Wrong Key?)", (1,0,0,1))
                    self.client_socket.close()
            else:
                self.log("Handshake Timeout (Check Password)", (1,0,0,1))
                self.client_socket.close()

        except Exception as e:
            self.log(f"Connection Error: {e}", (1, 0, 0, 1))

    def listen_thread(self):
        while self.connected:
            try:
                data = self.client_socket.recv(4096)
                if not data: break
                
                # DECRYPT INCOMING
                try:
                    msg = self.cipher.decrypt(data).decode()
                    if "RADIO:" in msg:
                        content = msg.split("RADIO:")[-1].strip()
                        self.log(f"[VOICE] {content}", (1, 1, 0, 1))
                        self.voice_queue.put(content)
                    else:
                        self.log(msg)
                except:
                    pass # Ignore unreadable packets
            except: break
        self.disconnect()

    def disconnect(self):
        self.connected = False
        try: self.client_socket.close()
        except: pass
        self.update_status(False)
        self.log("Disconnected.", (1, 0.5, 0, 1))

    def send_chat(self, instance):
        if self.connected and self.txt_input.text:
            msg = f"[{self.agent_name}] {self.txt_input.text}"
            try:
                # ENCRYPT OUTGOING
                self.client_socket.send(self.cipher.encrypt(msg.encode()))
                self.log(f"[b]You:[/b] {self.txt_input.text}", (0.5, 0.5, 1, 1))
                self.txt_input.text = ""
            except: pass

    def send_radio(self, instance):
        if self.connected and self.radio_input.text:
            msg = f"RADIO: {self.agent_name} says: {self.radio_input.text}"
            try:
                self.client_socket.send(self.cipher.encrypt(msg.encode()))
                self.radio_input.text = ""
            except: pass

    # --- VOICE WORKER ---
    def voice_worker(self):
        pc_engine = None
        if platform != 'android':
            try:
                import pyttsx3
                pc_engine = pyttsx3.init()
            except: pass

        while True:
            text = self.voice_queue.get()
            try:
                if platform == 'android' and tts: 
                    tts.speak(text)
                    time.sleep(1.5)
                elif pc_engine:
                    pc_engine.say(text)
                    pc_engine.runAndWait()
            except: pass
            finally: self.voice_queue.task_done()

    # --- SCANNER ---
    def start_scan(self, instance):
        if self.scan_ip.text:
            threading.Thread(target=self.scan_thread, args=(self.scan_ip.text,), daemon=True).start()

    def scan_thread(self, ip):
        ports = {21: "FTP", 22: "SSH", 80: "HTTP", 443: "HTTPS"}
        res = []
        for p, n in ports.items():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)
                if s.connect_ex((ip, p)) == 0: res.append(f"{p} OPEN")
                s.close()
            except: pass
        self.update_scan_result(f"REPORT: {ip}\n" + ("\n".join(res) if res else "No ports found."))
    
    @mainthread
    def update_scan_result(self, text): self.scan_res.text = text

class DroidShieldClient(App):
    def build(self):
        try: return ClientGUI()
        except: return Label(text=f"CRITICAL ERROR:\n{traceback.format_exc()}")

if __name__ == '__main__':
    DroidShieldClient().run()
