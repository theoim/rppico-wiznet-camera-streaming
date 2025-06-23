import socket
import threading
import tkinter as tk
from tkinter import scrolledtext

MCU_IP = '192.168.11.2'
MCU_PORT = 5000
LOCAL_PORT = 5000

class UDPControllerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("WIZnet UDP Controller")
        self.root.geometry("500x400")

        self.text_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=20)
        self.text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)

        self.start_btn = tk.Button(btn_frame, text="START", command=self.send_start)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = tk.Button(btn_frame, text="STOP", command=self.send_stop)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', LOCAL_PORT))
        self.running = True

        self.recv_thread = threading.Thread(target=self.receive_loop, daemon=True)
        self.recv_thread.start()

    def log(self, message):
        self.text_area.insert(tk.END, message + '\n')
        self.text_area.see(tk.END)

    def send_start(self):
        self.sock.sendto(b'START', (MCU_IP, MCU_PORT))
        self.log("[*] Sent 'START'")

    def send_stop(self):
        self.sock.sendto(b'STOP', (MCU_IP, MCU_PORT))
        self.log("[*] Sent 'STOP'")

    def receive_loop(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                msg = data.decode(errors='ignore').strip()
                self.log(f"[{addr}] {msg}")
            except Exception as e:
                self.log(f"[!] Receive error: {e}")
                break

    def close(self):
        self.running = False
        try:
            self.sock.sendto(b'STOP', (MCU_IP, MCU_PORT))
        except:
            pass
        self.sock.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = UDPControllerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()