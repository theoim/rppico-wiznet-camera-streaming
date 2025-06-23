import socket, threading, queue, time, tkinter as tk
from tkinter import ttk, scrolledtext
from PIL import Image, ImageTk
import cv2, numpy as np

# ======= 유틸 =======
def load_logo(path, max_size=(160, 60)):
    try:
        img = Image.open(path)
        img.thumbnail(max_size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception as e:
        print(f"Logo load failed: {e}")
        return None

def create_rounded_rectangle(canvas, x1, y1, x2, y2, radius=20, **kwargs):
    points = []
    for x, y in [(x1, y1 + radius), (x1, y1), (x1 + radius, y1),
                 (x2 - radius, y1), (x2, y1), (x2, y1 + radius),
                 (x2, y2 - radius), (x2, y2), (x2 - radius, y2),
                 (x1 + radius, y2), (x1, y2), (x1, y2 - radius)]:
        points.extend([x, y])
    return canvas.create_polygon(points, smooth=True, **kwargs)

# ======= 상수 =======
REMOTE_DEF = "192.168.11.2"
FW, FH = 320, 240                # ← 변경
FRAME_SZ = FW * FH * 2
HDR = 4
WIN = "YUY2 Stream"

# ======= 패킷 재조립 =======
class Assembler:
    def __init__(self): self.buf, self.need = {}, {}
    def add(self, pkt: bytes):
        if len(pkt) <= HDR: return None
        fid, pid, tot = pkt[0], pkt[1], pkt[2]
        self.buf.setdefault(fid, {})[pid] = pkt[HDR:]
        self.need[fid] = tot
        if len(self.buf[fid]) == tot:
            data = b''.join(self.buf[fid].get(i, b'') for i in range(tot))
            self.buf.pop(fid); self.need.pop(fid)
            return data if len(data) == FRAME_SZ else None
        return None

# ======= 커스텀 버튼 =======
class AppleButton(tk.Canvas):
    def __init__(self, parent, text, command=None, style='primary', state='normal', **kwargs):
        super().__init__(parent, highlightthickness=0, **kwargs)
        self.text = text
        self.command = command
        self.style = style
        self.state = state
        self.is_hovered = False
        self.colors = {
            'primary': {'bg': '#007AFF', 'fg': 'white', 'hover': '#0056CC'},
            'secondary': {'bg': '#F2F2F7', 'fg': '#1D1D1F', 'hover': '#E5E5EA'},
            'danger': {'bg': '#FF3B30', 'fg': 'white', 'hover': '#D70015'},
            'success': {'bg': '#34C759', 'fg': 'white', 'hover': '#248A3D'}
        }
        self.bind('<Button-1>', self._on_click)
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.draw()
    
    def draw(self):
        self.delete('all')
        if self.state == 'disabled':
            bg_color = '#F2F2F7'
            text_color = '#8E8E93'
        else:
            color_set = self.colors[self.style]
            bg_color = color_set['hover'] if self.is_hovered else color_set['bg']
            text_color = color_set['fg']
        create_rounded_rectangle(self, 2, 2, self.winfo_reqwidth()-2, self.winfo_reqheight()-2,
                               radius=8, fill=bg_color, outline='')
        self.create_text(self.winfo_reqwidth()//2, self.winfo_reqheight()//2,
                        text=self.text, fill=text_color, 
                        font=('Calibri', 11, 'normal'))
    
    def _on_click(self, event):
        if self.command and self.state == 'normal':
            self.command()
    
    def _on_enter(self, event):
        if self.state == 'normal':
            self.is_hovered = True
            self.after_idle(self.draw)
    
    def _on_leave(self, event):
        self.is_hovered = False
        self.after_idle(self.draw)
    
    def config_state(self, state):
        self.state = state
        self.draw()

# ======= 메인 앱 =======
class StreamApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.q = queue.Queue()
        self.sock, self.remote = None, None
        self.recv_th = None
        self.stop_all = threading.Event()
        self.stop_req = threading.Event()
        self.streaming = False
        self.window_up = False
        self.scale = 4
        self._setup_apple_style()
        self._build_ui()
        self._poll_log()

    def _setup_apple_style(self):
        style = ttk.Style()
        style.configure('Apple.TEntry',
                       fieldbackground='#FFFFFF',
                       foreground='#1D1D1F',
                       borderwidth=1,
                       relief='solid',
                       bordercolor='#D1D1D6',
                       insertcolor='#007AFF',
                       font=('Calibri', 11),
                       padding=6)
        style.map('Apple.TEntry', bordercolor=[('focus', '#007AFF')])

    def _create_card(self, parent, **kwargs):
        card = tk.Frame(parent, bg='#FFFFFF', relief='flat', **kwargs)
        shadow = tk.Frame(parent, bg='#E5E5EA', height=kwargs.get('height', 100))
        return card, shadow

    def _build_ui(self):
        self.root.title("WIZnet Stream")
        self.root.geometry("520x600")
        self.root.configure(bg="#F2F2F7")

        main_frame = tk.Frame(self.root, bg="#F2F2F7")
        main_frame.pack(fill='both', expand=True, padx=10, pady=20)

        logo_img = load_logo("wiznet_logo.png")
        if logo_img:
            tk.Label(main_frame, image=logo_img, bg="#F2F2F7").pack(pady=(0, 8))
            self.logo_img = logo_img

        tk.Label(main_frame, text="WIZnet Stream",
                font=('SF Pro Display', 22, 'bold'),
                bg="#F2F2F7", fg="#1D1D1F").pack()
        tk.Label(main_frame, text="Professional Video Streaming",
                font=('Calibri', 11),
                bg="#F2F2F7", fg="#8E8E93").pack(pady=(0, 10))

        self.v_rip = tk.StringVar(value=REMOTE_DEF)
        self.v_rpt = tk.StringVar(value='5000')
        self.v_lpt = tk.StringVar(value='5000')
        self.v_scl = tk.StringVar(value='50')
        self.ents = []

        def add_field(label, var):
            f = tk.Frame(main_frame, bg="#F2F2F7")
            f.pack(fill='x', pady=3)
            tk.Label(f, text=label, font=('Calibri', 11), bg="#F2F2F7", anchor='w').pack(anchor='w')
            e = ttk.Entry(f, textvariable=var, style='Apple.TEntry')
            e.pack(fill='x')
            self.ents.append(e)

        for lbl, v in [("Remote IP Address", self.v_rip), 
                    ("Remote Port", self.v_rpt), 
                    ("Local Port", self.v_lpt), 
                    ("Scale Percentage(10~100%)", self.v_scl)]:
            add_field(lbl, v)

        btns = tk.Frame(main_frame, bg="#F2F2F7")
        btns.pack(pady=8)
        self.b_conn = AppleButton(btns, "Connect", self._connect, style='primary', width=100, height=36)
        self.b_conn.pack(side='left', padx=5)
        self.b_clos = AppleButton(btns, "Disconnect", self._close_conn, style='secondary', state='disabled', width=100, height=36)
        self.b_clos.pack(side='left', padx=5)

        sbtns = tk.Frame(main_frame, bg="#F2F2F7")
        sbtns.pack(pady=5)
        self.b_start = AppleButton(sbtns, "Start Stream", self._start, style='success', state='disabled', width=120, height=36)
        self.b_start.pack(side='left', padx=5)
        self.b_stop = AppleButton(sbtns, "Stop Stream", self._stop, style='danger', state='disabled', width=120, height=36)
        self.b_stop.pack(side='left', padx=5)

        self.status_dot = tk.Canvas(main_frame, width=12, height=12, bg="#F2F2F7", highlightthickness=0)
        self.status_dot.create_oval(2, 2, 10, 10, fill="#8E8E93", outline="")
        self.status_dot.pack()
        self.status_txt = tk.Label(main_frame, text="Disconnected", font=('Calibri', 13), bg="#F2F2F7", fg="#1D1D1F")
        self.status_txt.pack()

        self.log = scrolledtext.ScrolledText(main_frame, height=6, font=('SF Mono', 10), bg="#FFFFFF")
        self.log.pack(fill='both', expand=True, pady=(5, 0))
        self.log.insert(tk.END, "Welcome to WIZnet Stream\nReady to connect and start streaming.\n\n")

    def _set_state(self, txt, color):
        self.status_txt.config(text=txt)
        self.status_dot.delete('all')
        self.status_dot.create_oval(2, 2, 10, 10, fill=color, outline="")

    def _log(self, msg): 
        timestamp = time.strftime('%H:%M:%S')
        self.q.put(f"[{timestamp}] {msg}")
    
    def _poll_log(self):
        while not self.q.empty():
            msg = self.q.get()
            self.log.insert(tk.END, msg + '\n')
            self.log.see(tk.END)
        self.root.after(80, self._poll_log)

    def _safe_destroy(self):
        if self.window_up:
            try:
                if cv2.getWindowProperty(WIN, cv2.WND_PROP_VISIBLE) >= 0:
                    cv2.destroyWindow(WIN); cv2.waitKey(1)
            except cv2.error: pass
            self.window_up = False

    def _connect(self):
        try:
            rip = self.v_rip.get().strip()
            rpt = self.v_rpt.get().strip()
            lpt = self.v_lpt.get().strip()

            try: socket.inet_aton(rip)
            except OSError:
                self._set_state('Invalid IP', '#FF3B30')
                self._log(f'Invalid IP Address: {rip}')
                return

            try:
                rpt = int(rpt); lpt = int(lpt)
                if not (1 <= rpt <= 65535 and 1 <= lpt <= 65535):
                    raise ValueError
            except ValueError:
                self._set_state('Invalid Port', '#FF3B30')
                self._log(f'Port number must be 1~65535 (Given: Remote {self.v_rpt.get()}, Local {self.v_lpt.get()})')
                return

            try: pct = int(self.v_scl.get())
            except ValueError: pct = 50
            pct = max(10, min(100, pct))
            self.v_scl.set(str(pct))
            self.scale = max(1, min(8, round(pct / 12.5)))

            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind(('', lpt))
            self.sock.settimeout(0.1)
            self.remote = (rip, rpt)

            if not self.recv_th or not self.recv_th.is_alive():
                self.stop_all.clear()
                self.recv_th = threading.Thread(target=self._recv_loop, daemon=True)
                self.recv_th.start()

            self._set_state('Connected', '#34C759')
            self._log(f'Connected to {rip}:{rpt} (local port {lpt}, scale x{self.scale})')

            for e in self.ents: e.config(state='disabled')
            self.b_conn.config_state('disabled')
            self.b_clos.config_state('normal')
            self.b_start.config_state('normal')

        except Exception as e:
            self._set_state('Connection Failed', '#FF3B30')
            self._log(f'Connection error: {e}')

    def _close_conn(self):
        self._stop()
        if self.sock:
            try: self.sock.close()
            except OSError: pass
            self.sock = None
        self._set_state('Disconnected', '#8E8E93')
        self._log('Disconnected')
        for e in self.ents: e.config(state='normal')
        self.b_conn.config_state('normal')
        self.b_clos.config_state('disabled')
        self.b_start.config_state('disabled')

    def _start(self):
        if not self.sock or self.streaming: return
        self.sock.sendto(b'START', self.remote)
        self.streaming = True; self.stop_req.clear()
        self._set_state('Streaming', '#007AFF')
        self.b_start.config_state('disabled')
        self.b_stop.config_state('normal')
        self._log('Stream started')

    def _stop(self):
        if not self.sock or not self.streaming: return
        try: self.sock.sendto(b'STOP', self.remote)
        except OSError: pass
        self.streaming = False; self.stop_req.set()
        self._set_state('Connected', '#34C759')
        self.b_start.config_state('normal')
        self.b_stop.config_state('disabled')
        self._log('Stream stopped')

    def _recv_loop(self):
        asm = Assembler()
        while not self.stop_all.is_set():
            if self.stop_req.is_set(): self._safe_destroy(); time.sleep(0.05); continue
            if not (self.sock and self.streaming): time.sleep(0.05); continue
            try:
                data, _ = self.sock.recvfrom(4096)     # ← 2 KiB → 4 KiB
                frame = asm.add(data)
                if frame and self.streaming: self._show_frame(frame)
            except socket.timeout: continue
            except OSError: break
            except Exception as e:
                self.q.put(f'Receive error: {e}')
                self.root.after(0, self._stop)
        self._safe_destroy(); self.q.put('Receiver thread ended')

    def _show_frame(self, yuy2: bytes):
        if self.stop_req.is_set(): return
        if not self.window_up:
            cv2.namedWindow(WIN, cv2.WINDOW_NORMAL); self.window_up = True
        yuy = np.frombuffer(yuy2, np.uint8).reshape(FH, FW, 2)
        bgr = cv2.cvtColor(yuy, cv2.COLOR_YUV2BGR_YUY2)
        bgr = cv2.resize(bgr, (FW * self.scale, FH * self.scale), interpolation=cv2.INTER_NEAREST)
        cv2.imshow(WIN, bgr)
        if cv2.getWindowProperty(WIN, cv2.WND_PROP_VISIBLE) < 1:
            self.window_up = False; self.root.after(0, self._stop)
        cv2.waitKey(1)

    def on_quit(self):
        self.stop_all.set(); self._close_conn(); self.root.destroy()

# ======= 실행 =======
if __name__ == '__main__':
    root = tk.Tk()
    app = StreamApp(root)
    root.protocol('WM_DELETE_WINDOW', app.on_quit)
    root.mainloop()
