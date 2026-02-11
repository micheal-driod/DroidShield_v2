import socket
import threading
import time
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox

# --- CONFIGURATION ---
# Listens on ALL interfaces (IPv4/IPv6) to catch the Tunnel connection
HOST = ''import socket
import threading
import time
import base64
import hashlib
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
from cryptography.fernet import Fernet

# --- CONFIGURATION ---
HOST = ''  
PORT = 9000       
BLOCKED_IPS = set()
clients = {}      
client_ips = {}
CIPHER = None # Will be set by password

class TacticalServer:
    def __init__(self, master):
        self.master = master
        master.title("DROID SHIELD: ENCRYPTED HQ")
        master.geometry("900x650")
        master.configure(bg='#050505')

        self.lbl_title = tk.Label(master, text="DROID SHIELD: CLASSIFIED", 
                                font=("Courier", 22, "bold"), fg="#00ff00", bg="#050505")
        self.lbl_title.pack(pady=10)

        self.log_area = scrolledtext.ScrolledText(master, width=100, height=22, 
                                                font=("Courier", 10), bg="black", fg="#00ff00",
                                                insertbackground="white", state='disabled')
        self.log_area.pack(pady=5, padx=10)

        self.lbl_status = tk.Label(master, text="STATUS: STANDBY - NO ENCRYPTION KEY", 
                                 font=("Courier", 12, "bold"), fg="red", bg="#050505")
        self.lbl_status.pack(pady=5)

        control_frame = tk.LabelFrame(master, text=" OPS CENTER ", 
                                    font=("Courier", 10, "bold"), bg="#050505", fg="white", bd=2)
        control_frame.pack(pady=10, padx=10, fill="x")

        tk.Button(control_frame, text="[ BAN IP ]", command=self.cmd_ban, bg="#550000", fg="white", width=14).grid(row=0, column=0, padx=15, pady=10)
        tk.Button(control_frame, text="[ UNBLOCK ]", command=self.cmd_unblock, bg="#003366", fg="white", width=14).grid(row=0, column=1, padx=15, pady=10)
        tk.Button(control_frame, text="[ KICK ]", command=self.cmd_kick, bg="#555500", fg="white", width=14).grid(row=0, column=2, padx=15, pady=10)
        tk.Button(control_frame, text="[ ROSTER ]", command=self.cmd_list, bg="#004400", fg="white", width=14).grid(row=0, column=3, padx=15, pady=10)

        self.btn_start = tk.Button(master, text="INITIALIZE ENCRYPTION & SERVER", command=self.start_sequence,
                                 font=("Courier", 14, "bold"), bg="#005500", fg="white", width=35)
        self.btn_start.pack(pady=15)

    def log(self, message):
        self.master.after(0, self._log_internal, message)

    def _log_internal(self, message):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, f"> {message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

    # --- CRYPTO HELPERS ---
    def encrypt(self, msg):
        try: return CIPHER.encrypt(msg.encode())
        except: return b""

    def decrypt(self, data):
        try: return CIPHER.decrypt(data).decode()
        except: return None

    # --- COMMANDS ---
    def cmd_ban(self):
        target = simpledialog.askstring("BAN IP", "Enter IP to Blacklist:")
        if target:
            BLOCKED_IPS.add(target)
            self.log(f"SECURITY: IP {target} added to BLACKLIST.")
            self.kick_by_ip(target)

    def cmd_unblock(self):
        target = simpledialog.askstring("UNBLOCK", "Enter IP to Unblock:")
        if target in BLOCKED_IPS:
            BLOCKED_IPS.remove(target)
            self.log(f"SECURITY: IP {target} Removed from Blacklist.")

    def cmd_kick(self):
        name = simpledialog.askstring("KICK", "Enter Agent Name:")
        if name: self.kick_user(name)

    def cmd_list(self):
        self.log("-" * 30)
        self.log(f"AGENTS: {list(clients.values())}")
        self.log(f"BANNED: {list(BLOCKED_IPS)}")
        self.log("-" * 30)

    def kick_user(self, name):
        target_sock = None
        for sock, n in clients.items():
            if n == name: target_sock = sock
        if target_sock: self.remove_client(target_sock)

    def kick_by_ip(self, ip):
        to_remove = [s for s, i in client_ips.items() if i == ip]
        for s in to_remove: self.remove_client(s)

    def broadcast(self, raw_bytes, sender=None):
        # We broadcast the ALREADY ENCRYPTED bytes to everyone else
        # This saves CPU. We only decrypt to read it on the server log.
        for sock in list(clients.keys()):
            if sock != sender:
                try: sock.send(raw_bytes)
                except: self.remove_client(sock)

    def remove_client(self, sock):
        if sock in clients:
            name = clients[sock]
            del clients[sock]
            if sock in client_ips: del client_ips[sock]
            try: sock.close()
            except: pass
            
            msg = f"[SYSTEM] {name} Connection Lost."
            self.log(msg)
            # Encrypt and send system message
            enc_msg = self.encrypt(msg)
            self.broadcast(enc_msg)

    def handle_client(self, client_socket, addr):
        ip = addr[0]
        if ip in BLOCKED_IPS:
            client_socket.close()
            return

        self.log(f"UPLINK DETECTED: {ip}")
        client_ips[client_socket] = ip

        try:
            client_socket.settimeout(3.0) 
            authenticated = False
            
            # --- ACTIVE HANDSHAKE (ENCRYPTED) ---
            # We send an encrypted "AUTH" beacon.
            # If client has wrong key, they see garbage and can't reply "OK".
            
            auth_token = self.encrypt("AUTH_REQUEST")
            
            for i in range(15):
                try:
                    client_socket.send(auth_token)
                    try:
                        data = client_socket.recv(4096)
                        decoded = self.decrypt(data)
                        if decoded == "AUTH_ACK":
                            authenticated = True
                            break
                    except socket.timeout: continue
                except: break
                time.sleep(1)

            if authenticated:
                name = f"AGENT_{ip.split('.')[-1]}"
                clients[client_socket] = name
                
                # Send Welcome
                client_socket.send(self.encrypt("ACCESS_GRANTED"))
                client_socket.settimeout(None)
                self.log(f"VERIFIED: {name}")
                
                # Notify others
                join_msg = self.encrypt(f"[SYSTEM] {name} Secured.")
                self.broadcast(join_msg, client_socket)
                
                while True:
                    data = client_socket.recv(4096) # Larger buffer for crypto overhead
                    if not data: break
                    
                    # 1. Decrypt locally to Log
                    text = self.decrypt(data)
                    if text:
                        if "RADIO:" in text:
                            self.log(f"[VOICE] {text}")
                        else:
                            self.log(f"[CHAT] {text}")
                        
                        # 2. Forward the ENCRYPTED data to others
                        # (Clients have the key, so they can decrypt it)
                        self.broadcast(data, client_socket)
            else:
                client_socket.close()

        except Exception as e:
            # self.log(f"Err: {e}") # Debug only
            client_socket.close()
            
        if client_socket in clients: self.remove_client(client_socket)

    def start_server_thread(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind((HOST, PORT))
            server.listen(5)
            self.master.after(0, lambda: self.lbl_status.config(text="STATUS: ONLINE (ENCRYPTED)", fg="#00ff00"))
            self.log(f"SECURE SERVER STARTED ON PORT {PORT}")
            
            while True:
                client, addr = server.accept()
                threading.Thread(target=self.handle_client, args=(client, addr), daemon=True).start()
        except Exception as e:
            self.log(f"CRITICAL ERROR: {e}")

    def start_sequence(self):
        global CIPHER
        key_input = simpledialog.askstring("SECURITY", "Set Session Password (Must match Client):", show='*')
        if not key_input: return
        
        # GENERATE 32-BYTE FERNET KEY FROM PASSWORD
        # This ensures the key is valid for cryptography library
        key = base64.urlsafe_b64encode(hashlib.sha256(key_input.encode()).digest())
        CIPHER = Fernet(key)
        
        self.btn_start.config(state='disabled')
        threading.Thread(target=self.start_server_thread, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = TacticalServer(root)
    root.mainloop()
  
PORT = 9000       

# --- GLOBAL STORAGE ---
SESSION_KEY = "123456" 
BLOCKED_IPS = set()
clients = {}      # {socket: name}
client_ips = {}   # {socket: ip}

class TacticalServer:
    def __init__(self, master):
        self.master = master
        master.title("FIELD HEADQUARTERS - COMMANDER")
        master.geometry("900x650")
        master.configure(bg='black')

        # --- HEADER ---
        self.lbl_title = tk.Label(master, text="DROID SHIELD: COMMANDER", 
                                font=("Courier", 22, "bold"), fg="#00ff00", bg="black")
        self.lbl_title.pack(pady=10)

        # --- LOG WINDOW ---
        self.log_area = scrolledtext.ScrolledText(master, width=100, height=22, 
                                                font=("Courier", 10), bg="#111", fg="#00ff00",
                                                insertbackground="white", state='disabled')
        self.log_area.pack(pady=5, padx=10)

        # --- STATUS INDICATORS ---
        self.lbl_status = tk.Label(master, text="STATUS: STANDBY", 
                                 font=("Courier", 12, "bold"), fg="yellow", bg="black")
        self.lbl_status.pack(pady=5)

        # --- CONTROLS ---
        control_frame = tk.LabelFrame(master, text=" TACTICAL OPERATIONS ", 
                                    font=("Courier", 10, "bold"), bg="black", fg="white", bd=2)
        control_frame.pack(pady=10, padx=10, fill="x")

        # Buttons
        btn_ban = tk.Button(control_frame, text="[ BAN IP ]", command=self.cmd_ban,
                          font=("Courier", 10, "bold"), bg="#550000", fg="white", width=14)
        btn_ban.grid(row=0, column=0, padx=15, pady=10)

        btn_unblock = tk.Button(control_frame, text="[ UNBLOCK ]", command=self.cmd_unblock,
                              font=("Courier", 10, "bold"), bg="#003366", fg="white", width=14)
        btn_unblock.grid(row=0, column=1, padx=15, pady=10)

        btn_kick = tk.Button(control_frame, text="[ KICK USER ]", command=self.cmd_kick,
                           font=("Courier", 10, "bold"), bg="#555500", fg="white", width=14)
        btn_kick.grid(row=0, column=2, padx=15, pady=10)

        btn_list = tk.Button(control_frame, text="[ ROSTER ]", command=self.cmd_list,
                           font=("Courier", 10, "bold"), bg="#004400", fg="white", width=14)
        btn_list.grid(row=0, column=3, padx=15, pady=10)

        # --- START BUTTON ---
        self.btn_start = tk.Button(master, text="INITIATE SERVER SEQUENCE", command=self.start_sequence,
                                 font=("Courier", 14, "bold"), bg="#005500", fg="white", width=35)
        self.btn_start.pack(pady=15)

    # --- THREAD-SAFE LOGGING ---
    def log(self, message):
        self.master.after(0, self._log_internal, message)

    def _log_internal(self, message):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, f"> {message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

    # --- COMMANDS ---
    def cmd_ban(self):
        target = simpledialog.askstring("BAN IP", "Enter IP to Blacklist:")
        if target:
            BLOCKED_IPS.add(target)
            self.log(f"SECURITY: IP {target} added to BLACKLIST.")
            self.kick_by_ip(target)

    def cmd_unblock(self):
        target = simpledialog.askstring("UNBLOCK", "Enter IP to Unblock:")
        if target in BLOCKED_IPS:
            BLOCKED_IPS.remove(target)
            self.log(f"SECURITY: IP {target} Removed from Blacklist.")

    def cmd_kick(self):
        name = simpledialog.askstring("KICK", "Enter Agent Name:")
        if name: self.kick_user(name)

    def cmd_list(self):
        self.log("-" * 30)
        self.log(f"ACTIVE AGENTS: {list(clients.values())}")
        self.log(f"BLOCKED IPS:   {list(BLOCKED_IPS)}")
        self.log("-" * 30)

    # --- NETWORK ACTIONS ---
    def kick_user(self, name):
        target_sock = None
        for sock, n in clients.items():
            if n == name:
                target_sock = sock
                break
        if target_sock:
            self.remove_client(target_sock)
            self.log(f"KICK: {name} removed from session.")

    def kick_by_ip(self, ip):
        to_remove = [s for s, i in client_ips.items() if i == ip]
        for s in to_remove:
            self.remove_client(s)

    def broadcast(self, msg, sender=None):
        if isinstance(msg, str): msg = msg.encode('utf-8')
        for sock in list(clients.keys()):
            if sock != sender:
                try: sock.send(msg)
                except: self.remove_client(sock)

    def remove_client(self, sock):
        if sock in clients:
            name = clients[sock]
            del clients[sock]
            if sock in client_ips: del client_ips[sock]
            try: sock.close()
            except: pass
            self.broadcast(f"[SYSTEM] {name} Offline.".encode('utf-8'))
            self.log(f"DISCONNECT: {name}")

    # ==================================================
    #        THE PROTOCOL: "ACTIVE HANDSHAKE"
    # ==================================================
    def handle_client(self, client_socket, addr):
        ip = addr[0]
        if ip in BLOCKED_IPS:
            client_socket.close()
            return

        self.log(f"CONNECTION DETECTED: {ip}")
        client_ips[client_socket] = ip

        try:
            # We set a short timeout for the handshake phase
            client_socket.settimeout(2.0) 
            authenticated = False
            
            # THE BEACON LOOP:
            # We aggressively send "AUTH" every second for 15 seconds.
            # This forces the message through the tunnel to the client.
            for i in range(15):
                try:
                    # 1. Send Beacon
                    client_socket.send(b"AUTH\n")
                    
                    # 2. Check for Reply (Non-blocking-ish)
                    try:
                        data = client_socket.recv(1024).decode('utf-8').strip()
                        if data:
                            # 3. Verify Key
                            if data == SESSION_KEY:
                                authenticated = True
                                break # Success! Exit the loop.
                            else:
                                self.log(f"SECURITY ALERT: Bad Key from {ip}")
                                client_socket.send(b"WRONG_KEY\n")
                                client_socket.close()
                                return
                    except socket.timeout:
                        # No reply yet? Just loop back and send AUTH again.
                        continue 
                        
                except Exception as e:
                    self.log(f"Handshake Comms Error: {e}")
                    break
                
                time.sleep(1) # Wait 1s between beacons

            if authenticated:
                name = f"AGENT_{ip.split('.')[-1]}"
                clients[client_socket] = name
                client_socket.send(b"OK\n") # Send Final OK
                client_socket.settimeout(None) # Remove timeout for chat
                
                self.log(f"ACCESS GRANTED: {name}")
                self.broadcast(f"[SYSTEM] {name} Joined.".encode('utf-8'))
                
                # CHAT LOOP
                while True:
                    data = client_socket.recv(1024)
                    if not data: break
                    
                    try:
                        text = data.decode('utf-8')
                        if "RADIO:" in text:
                            self.log(f"[VOICE] {text}")
                            self.broadcast(data, client_socket) # Forward Voice
                        else:
                            self.log(f"[CHAT] {text}")
                            self.broadcast(data, client_socket) # Forward Chat
                    except: pass
            else:
                self.log(f"TIMEOUT: {ip} failed to authenticate (No Key Sent).")
                client_socket.close()

        except Exception as e:
            self.log(f"CRITICAL ERROR: {e}")
            client_socket.close()
        
        if client_socket in clients:
            self.remove_client(client_socket)

    def start_server_thread(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            # BIND TO ALL INTERFACES
            server.bind((HOST, PORT))
            server.listen(5)
            self.master.after(0, lambda: self.lbl_status.config(text="STATUS: ONLINE (LISTENING ON 9000)", fg="#00ff00"))
            self.log(f"SERVER STARTED ON LOCAL PORT {PORT}")
            self.log(f"WAITING FOR TUNNEL CONNECTIONS...")
            
            while True:
                client, addr = server.accept()
                threading.Thread(target=self.handle_client, args=(client, addr), daemon=True).start()
        except Exception as e:
            self.log(f"CRITICAL ERROR: {e}")
            self.master.after(0, lambda: self.lbl_status.config(text="STATUS: ERROR", fg="red"))

    def start_sequence(self):
        global SESSION_KEY
        
        # Set Password
        key = simpledialog.askstring("SECURITY", "Set Session Password:", show='*')
        if not key: return
        
        SESSION_KEY = key
        self.btn_start.config(state='disabled')
        threading.Thread(target=self.start_server_thread, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = TacticalServer(root)
    root.mainloop()
