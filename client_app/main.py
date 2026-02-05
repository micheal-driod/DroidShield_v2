import socket
import threading
import struct
import math
from kivy.app import App
from kivy.clock import Clock
from kivy.storage.jsonstore import JsonStore
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from kivy.utils import platform

# --- CONFIG ---
CYBER_GREEN = (0, 1, 0.4, 1)
ALERT_RED = (1, 0, 0, 1)
DARK_BG = (0.05, 0.05, 0.05, 1)
store = JsonStore('secure_data.json')

# --- ENCRYPTION ---
def encrypt_decrypt(text, key):
    try: return ''.join(chr(ord(c) ^ ord(k)) for c, k in zip(text, key * len(text)))
    except: return text

# --- AUDIO ENGINE (CLIENT SIDE) ---
class AudioEngine:
    def __init__(self):
        self.is_android = platform == 'android'
        self.rec = None; self.track = None; self.pa = None; self.stream = None
        self.rate = 16000; self.chunk = 1024
        
        if self.is_android:
            try:
                from jnius import autoclass
                self.AudioRecord = autoclass('android.media.AudioRecord')
                self.AudioTrack = autoclass('android.media.AudioTrack')
                self.AudioFormat = autoclass('android.media.AudioFormat')
                self.MediaRecorder = autoclass('android.media.MediaRecorder$AudioSource')
                self.AudioManager = autoclass('android.media.AudioManager')
                self.src = self.MediaRecorder.MIC
                self.stream_type = self.AudioManager.STREAM_VOICE_CALL
                self.sr = self.rate
                self.chin = self.AudioFormat.CHANNEL_IN_MONO; self.chout = self.AudioFormat.CHANNEL_OUT_MONO
                self.enc = self.AudioFormat.ENCODING_PCM_16BIT
                self.min_buf_rec = self.AudioRecord.getMinBufferSize(self.sr, self.chin, self.enc) * 2
                self.min_buf_play = self.AudioTrack.getMinBufferSize(self.sr, self.chout, self.enc) * 2
            except: pass
        else:
            try: import pyaudio; self.pa = pyaudio.PyAudio()
            except: pass

    def start(self):
        if self.is_android:
            try:
                self.rec = self.AudioRecord(self.src, self.sr, self.chin, self.enc, self.min_buf_rec)
                self.track = self.AudioTrack(self.stream_type, self.sr, self.chout, self.enc, self.min_buf_play, 1)
                self.rec.startRecording(); self.track.play()
                return True
            except: return False
        elif self.pa:
            try:
                self.stream = self.pa.open(format=self.pa.get_format_from_width(2), channels=1, rate=self.rate, input=True, output=True, frames_per_buffer=self.chunk)
                return True
            except: return False
        return False

    def read(self):
        if self.is_android and self.rec:
            try:
                b = bytearray(self.chunk)
                r = self.rec.read(b, 0, self.chunk)
                if r > 0: return bytes(b[:r])
            except: pass
        elif self.stream:
            try: return self.stream.read(self.chunk, exception_on_overflow=False)
            except: pass
        return None

    def write(self, data):
        if self.is_android and self.track: 
            try: self.track.write(data, 0, len(data))
            except: pass
        elif self.stream:
            try: self.stream.write(data)
            except: pass

    def stop(self):
        if self.is_android:
            try: self.rec.stop(); self.track.stop()
            except: pass
        elif self.stream:
            try: self.stream.stop_stream(); self.stream.close()
            except: pass

audio = AudioEngine()

# --- APP UI ---
class DroidClient(App):
    def build(self):
        Window.clearcolor = DARK_BG
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.INTERNET, Permission.RECORD_AUDIO, Permission.MODIFY_AUDIO_SETTINGS])
        
        self.sm = ScreenManager()
        self.sm.add_widget(self.login_screen())
        self.sm.add_widget(self.comms_screen())
        return self.sm

    def login_screen(self):
        s = Screen(name='login')
        l = BoxLayout(orientation='vertical', padding=30, spacing=20)
        l.add_widget(Label(text="[ AGENT LOGIN ]", font_size='24sp', color=CYBER_GREEN))
        
        self.ip_in = TextInput(hint_text="HQ Server IP", multiline=False, foreground_color=CYBER_GREEN, background_color=(0.1,0.1,0.1,1))
        self.key_in = TextInput(hint_text="Secret Key", password=True, multiline=False, foreground_color=CYBER_GREEN, background_color=(0.1,0.1,0.1,1))
        
        btn = Button(text="CONNECT TO HQ", background_color=CYBER_GREEN, bold=True)
        btn.bind(on_press=self.connect_to_hq)
        
        l.add_widget(self.ip_in); l.add_widget(self.key_in); l.add_widget(btn)
        s.add_widget(l)
        return s

    def comms_screen(self):
        s = Screen(name='comms')
        l = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        self.status = Label(text="CONNECTING...", size_hint=(1, 0.1), color=CYBER_GREEN)
        self.history = TextInput(readonly=True, background_color=(0,0,0,1), foreground_color=CYBER_GREEN, size_hint=(1, 0.6))
        
        controls = BoxLayout(size_hint=(1, 0.15), spacing=5)
        self.msg = TextInput(hint_text="Message", multiline=False)
        btn_send = Button(text="SEND", size_hint=(0.3, 1), background_color=CYBER_GREEN, on_press=self.send_msg)
        controls.add_widget(self.msg); controls.add_widget(btn_send)
        
        self.mic_btn = Button(text="RADIO: OFF", background_color=ALERT_RED, size_hint=(1, 0.15), on_press=self.toggle_mic)
        
        l.add_widget(self.status); l.add_widget(self.history); l.add_widget(controls); l.add_widget(self.mic_btn)
        s.add_widget(l)
        return s

    def connect_to_hq(self, instance):
        self.target_ip = self.ip_in.text
        self.key = self.key_in.text
        if not self.target_ip: return
        self.sm.current = 'comms'
        self.running = True
        threading.Thread(target=self.network_loop, daemon=True).start()
        audio.start()

    def network_loop(self):
        try:
            # TCP (Chat)
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((self.target_ip, 8000))
            Clock.schedule_once(lambda dt: setattr(self.status, 'text', f"SECURE LINK: {self.target_ip}"))
            
            # UDP (Audio) - Send Ping to register
            self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp.sendto(b'PING', (self.target_ip, 8001))
            
            threading.Thread(target=self.listen_tcp, daemon=True).start()
            threading.Thread(target=self.listen_udp, daemon=True).start()
        except Exception as e:
            Clock.schedule_once(lambda dt: setattr(self.status, 'text', "CONNECTION FAILED"))

    def listen_tcp(self):
        while self.running:
            try:
                data = self.sock.recv(1024)
                if data:
                    msg = encrypt_decrypt(data.decode(), self.key)
                    Clock.schedule_once(lambda dt, m=msg: setattr(self.history, 'text', self.history.text + "HQ/PEER: " + m + "\n"))
            except: break

    def listen_udp(self):
        while self.running:
            try:
                data, _ = self.udp.recvfrom(4096)
                audio.write(data)
            except: pass

    def send_msg(self, instance):
        if self.msg.text:
            cipher = encrypt_decrypt(self.msg.text, self.key)
            try: self.sock.send(cipher.encode())
            except: pass
            self.history.text += f"ME: {self.msg.text}\n"
            self.msg.text = ""

    def toggle_mic(self, instance):
        self.mic_live = not getattr(self, 'mic_live', False)
        if self.mic_live:
            self.mic_btn.text = "RADIO: LIVE"; self.mic_btn.background_color = CYBER_GREEN
            threading.Thread(target=self.mic_loop, daemon=True).start()
        else:
            self.mic_btn.text = "RADIO: OFF"; self.mic_btn.background_color = ALERT_RED

    def mic_loop(self):
        while self.running and self.mic_live:
            data = audio.read()
            if data:
                try: self.udp.sendto(data, (self.target_ip, 8001))
                except: pass

if __name__ == '__main__': DroidClient().run()