import tkinter as tk
import json
import os
import ctypes

APP_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_FILE = os.path.join(APP_DIR, "memo_data.json")

# ── color palette ──
BG0    = "#0a0a0a"
BG1    = "#181818"
BG2    = "#252525"
ACC    = "#5bacff"
GREEN  = "#3ddc84"
RED    = "#ff4060"
TEXT   = "#ffffff"
DIM    = "#909090"
LINE   = "#333333"


class TodoRow(tk.Frame):
    def __init__(self, parent, text, on_check, **kw):
        super().__init__(parent, bg=BG0, **kw)
        self._text = text
        self._cb = on_check
        self._done = False

        self.var = tk.BooleanVar(value=False)
        self.cb = tk.Checkbutton(
            self, variable=self.var, bg=BG0, fg=ACC,
            selectcolor=BG0, activebackground=BG0,
            activeforeground=ACC, font=("Microsoft YaHei UI", 10),
            command=self._toggle
        )
        self.cb.pack(side=tk.LEFT, padx=(8, 8), pady=5)

        self.label = tk.Label(
            self, text=text, bg=BG0, fg=TEXT, anchor="w",
            font=("Microsoft YaHei UI", 10), padx=0, pady=5
        )
        self.label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _toggle(self):
        if not self.var.get() or self._done:
            return
        self._done = True
        self.cb.configure(state=tk.DISABLED)
        self._step(0)

    def _step(self, n):
        sequence = [
            lambda: (self.configure(bg="#0a2a18"),
                     self.label.configure(fg=GREEN)),
            lambda: (self.label.configure(fg=DIM,
                     font=("Microsoft YaHei UI", 10, "overstrike")),
                     self.configure(bg=BG0)),
            lambda: None,
            lambda: None,
            lambda: self._cb(self),
        ]
        if n < len(sequence):
            fn = sequence[n]
            if fn:
                fn()
            self.after(90, self._step, n + 1)


class ReminderApp:
    def __init__(self, root):
        self.root = root
        self.root.configure(bg=BG0)
        self.root.overrideredirect(True)
        self.root.attributes("-alpha", 0.45)

        self.data = {"active": [], "completed": []}
        self._tab = "active"
        self._drag_x = self._drag_y = 0
        self._rsz_x = self._rsz_y = self._rsz_w = self._rsz_h = 0
        self._rsz_edge = ""

        self._build_ui()
        self.load()
        self._snap_right()

        self.root.bind_all("<Control-r>", lambda e: self._snap_right())
        self.root.protocol("WM_DELETE_WINDOW", self._hide)

        # 启动全局热键检测 Ctrl+Shift+M
        self._hk_fired = False
        self.root.after(100, self._poll_hotkey)

    def _make_draggable(self, w):
        w.bind("<Button-1>", self._drag_start)
        w.bind("<B1-Motion>", self._drag)

    def _build_ui(self):
        # ── 标题栏（拖拽区域）──
        tb = tk.Frame(self.root, bg=BG1, height=36, cursor="fleur")
        tb.pack(fill=tk.X, side=tk.TOP)
        self._make_draggable(tb)

        d1 = tk.Label(tb, text="  ● ● ●", bg=BG1, fg=DIM, font=("Consolas", 7))
        d1.pack(side=tk.LEFT, pady=5)
        self._make_draggable(d1)

        d2 = tk.Label(tb, text="备忘录", bg=BG1, fg=ACC, font=("Microsoft YaHei UI", 9, "bold"))
        d2.pack(side=tk.LEFT, pady=5, padx=(4, 0))
        self._make_draggable(d2)

        spacer = tk.Label(tb, text="", bg=BG1)
        spacer.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=5)
        self._make_draggable(spacer)

        cls = tk.Button(tb, text="✕", bg=BG1, fg=DIM, font=("Consolas", 10), bd=0, padx=10,
                        activebackground=RED, activeforeground="white", command=self._hide)
        cls.pack(side=tk.RIGHT, pady=2)
        cls.bind("<Enter>", lambda e: cls.configure(bg=RED, fg="white"))
        cls.bind("<Leave>", lambda e: cls.configure(bg=BG1, fg=DIM))

        # 标题栏右键菜单：真正退出
        self._ctx = tk.Menu(self.root, tearoff=0, bg=BG1, fg=TEXT, font=("Microsoft YaHei UI", 9),
                            activebackground=RED, activeforeground="white")
        self._ctx.add_command(label="彻底退出", command=self._on_close)
        tb.bind("<Button-3>", lambda e: self._ctx.post(e.x_root, e.y_root))
        d1.bind("<Button-3>", lambda e: self._ctx.post(e.x_root, e.y_root))
        d2.bind("<Button-3>", lambda e: self._ctx.post(e.x_root, e.y_root))

        # ── 标签栏 ──
        tab_bar = tk.Frame(self.root, bg=BG0)
        tab_bar.pack(fill=tk.X, side=tk.TOP)

        self.tab_a = tk.Label(tab_bar, text="[ 待办事项 ]", bg=BG1, fg=ACC,
                              font=("Microsoft YaHei UI", 10, "bold"), padx=18, pady=7, cursor="hand2")
        self.tab_a.pack(side=tk.LEFT, padx=(0, 2))
        self.tab_a.bind("<Button-1>", lambda e: self._switch_tab("active"))

        self.tab_b = tk.Label(tab_bar, text="[ 已完成 0 ]", bg=BG0, fg=DIM,
                              font=("Microsoft YaHei UI", 10), padx=18, pady=7, cursor="hand2")
        self.tab_b.pack(side=tk.LEFT)
        self.tab_b.bind("<Button-1>", lambda e: self._switch_tab("completed"))

        tk.Frame(self.root, bg=ACC, height=1).pack(fill=tk.X)

        # ── 输入行 ──
        self.input_frame = tk.Frame(self.root, bg=BG0)
        self.input_frame.pack(fill=tk.X, side=tk.TOP, padx=12, pady=(10, 6))

        tk.Label(self.input_frame, text=">", bg=BG0, fg=ACC,
                 font=("Consolas", 11, "bold")).pack(side=tk.LEFT, padx=(0, 8))

        self.entry = tk.Entry(self.input_frame, bg=BG1, fg=TEXT, insertbackground=ACC,
                              font=("Microsoft YaHei UI", 10), bd=0, relief=tk.FLAT)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=7, padx=(0, 6))
        self.entry.bind("<Return>", lambda e: self.add_todo())
        self.entry.focus_set()

        add = tk.Button(self.input_frame, text="＋", bg=ACC, fg=BG0,
                        font=("Consolas", 13, "bold"), bd=0, padx=12, pady=1,
                        activebackground="#80ccff", activeforeground=BG0,
                        command=self.add_todo)
        add.pack(side=tk.RIGHT)

        # ── 可滚动列表 ──
        self.list_area = tk.Frame(self.root, bg=BG0)
        self.list_area.pack(fill=tk.BOTH, expand=True, side=tk.TOP)

        self.canvas = tk.Canvas(self.list_area, bg=BG0, bd=0, highlightthickness=0)
        sb = tk.Scrollbar(self.list_area, orient=tk.VERTICAL, command=self.canvas.yview,
                          bg=BG1, troughcolor=BG0, activebackground=ACC, bd=0)
        self.canvas.configure(yscrollcommand=sb.set)

        self.inner = tk.Frame(self.canvas, bg=BG0)
        self._cw = self.canvas.create_window((0, 0), window=self.inner, anchor="nw", tags="cw")

        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self._mw = False
        self.canvas.bind("<Enter>", self._bind_mw)
        self.canvas.bind("<Leave>", self._unbind_mw)

        # ── 底部栏 ──
        bbar = tk.Frame(self.root, bg=BG1, height=34)
        bbar.pack(fill=tk.X, side=tk.BOTTOM)

        tk.Button(bbar, text="清空", bg=BG1, fg=DIM, bd=0, padx=12, pady=3,
                  font=("Microsoft YaHei UI", 9), activebackground=ACC,
                  activeforeground=BG0, command=self.clear).pack(
                  side=tk.LEFT, padx=(12, 0), pady=3)

        self.status = tk.Label(bbar, text="", bg=BG1, fg=DIM,
                               font=("Microsoft YaHei UI", 9), anchor="w", padx=0)
        self.status.pack(side=tk.LEFT, pady=6, padx=(8, 0))

        # ── 底部缩放条 ──
        rz = tk.Frame(self.root, bg=BG2, height=14, cursor="sb_v_double_arrow")
        rz.pack(fill=tk.X, side=tk.BOTTOM)
        rz.bind("<Button-1>", lambda e: self._resize_start(e, "s"))
        rz.bind("<B1-Motion>", self._resize)
        rz.bind("<Enter>", lambda e: rz.configure(bg=ACC))
        rz.bind("<Leave>", lambda e: rz.configure(bg=BG2))

        # 右下角缩放手柄 — place 钉在窗口右下，永不消失
        self._grip = tk.Label(self.root, text="◢", bg=BG0, fg="#888",
                              font=("Consolas", 16, "bold"),
                              cursor="bottom_right_corner")
        self._grip.place(relx=1.0, rely=1.0, x=-2, y=-2, anchor="se")
        self._grip.bind("<Button-1>", lambda e: self._resize_start(e, "se"))
        self._grip.bind("<B1-Motion>", self._resize)
        self._grip.bind("<Enter>", lambda e: self._grip.configure(fg=ACC))
        self._grip.bind("<Leave>", lambda e: self._grip.configure(fg="#888"))
        self._grip.lift()  # 确保在最上层

    # ── 滚动 ──
    def _on_canvas_resize(self, event):
        self.canvas.itemconfigure(self._cw, width=event.width)

    def _bind_mw(self, e):
        if not self._mw:
            self.canvas.bind_all("<MouseWheel>", self._on_mw)
            self._mw = True

    def _unbind_mw(self, e):
        if self._mw:
            self.canvas.unbind_all("<MouseWheel>")
            self._mw = False

    def _on_mw(self, event):
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

    # ── 拖拽 ──
    def _drag_start(self, event):
        self._drag_x = event.x_root - self.root.winfo_x()
        self._drag_y = event.y_root - self.root.winfo_y()

    def _drag(self, event):
        self.root.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

    # ── 缩放 ──
    def _resize_start(self, event, edge):
        self._rsz_x = event.x_root
        self._rsz_y = event.y_root
        self._rsz_w = self.root.winfo_width()
        self._rsz_h = self.root.winfo_height()
        self._rsz_edge = edge

    def _resize(self, event):
        if not self._rsz_edge:
            return
        dx = event.x_root - self._rsz_x
        dy = event.y_root - self._rsz_y
        edge = self._rsz_edge

        # width
        if "e" in edge:
            w = max(300, self._rsz_w + dx)
            x = self.root.winfo_x()
        elif "w" in edge:
            w = max(300, self._rsz_w - dx)
            x = self.root.winfo_x() + self._rsz_w - w
        else:
            w = self._rsz_w
            x = self.root.winfo_x()

        # height
        if "s" in edge:
            h = max(420, self._rsz_h + dy)
            y = self.root.winfo_y()
        elif "n" in edge:
            h = max(420, self._rsz_h - dy)
            y = self.root.winfo_y() + self._rsz_h - h
        else:
            h = self._rsz_h
            y = self.root.winfo_y()

        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # ── 标签切换 ──
    def _switch_tab(self, tab):
        self._tab = tab
        if tab == "active":
            self.tab_a.configure(bg=BG1, fg=ACC, font=("Microsoft YaHei UI", 10, "bold"))
            self.tab_b.configure(bg=BG0, fg=DIM, font=("Microsoft YaHei UI", 10))
            self.input_frame.pack(fill=tk.X, side=tk.TOP, padx=12, pady=(10, 6),
                                  before=self.list_area)
        else:
            self.tab_b.configure(bg=BG1, fg=ACC, font=("Microsoft YaHei UI", 10, "bold"))
            self.tab_a.configure(bg=BG0, fg=DIM, font=("Microsoft YaHei UI", 10))
            self.input_frame.pack_forget()
        self._redraw()

    # ── 逻辑 ──
    def add_todo(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, tk.END)
        self.data["active"].append(text)
        if self._tab == "active":
            self._redraw()
        self.status.configure(text="已添加")

    def _on_check(self, row):
        try:
            self.data["active"].remove(row._text)
        except ValueError:
            return
        self.data["completed"].append(row._text)
        self._redraw()
        count = len(self.data["completed"])
        self.tab_b.configure(text=f"[ 已完成 {count} ]")
        self.status.configure(text="已完成")

    def clear(self):
        if self._tab == "active":
            self.data["active"].clear()
        else:
            self.data["completed"].clear()
        self._redraw()
        self.status.configure(text="已清空")

    # ── 重绘列表 ──
    def _redraw(self):
        for w in self.inner.winfo_children():
            w.destroy()

        if self._tab == "active":
            if not self.data["active"]:
                tk.Label(self.inner, text="暂无待办，在上方输入添加", bg=BG0, fg=DIM,
                         font=("Microsoft YaHei UI", 10), pady=30).pack()
            for text in self.data["active"]:
                TodoRow(self.inner, text, self._on_check).pack(fill=tk.X, padx=6, pady=1)
        else:
            if not self.data["completed"]:
                tk.Label(self.inner, text="暂无已完成事项", bg=BG0, fg=DIM,
                         font=("Microsoft YaHei UI", 10), pady=30).pack()
            for text in self.data["completed"]:
                tk.Label(self.inner, text=f"✓  {text}", bg=BG0, fg=DIM, anchor="w",
                         font=("Microsoft YaHei UI", 10, "overstrike"), padx=14, pady=5
                         ).pack(fill=tk.X, padx=6)

        count = len(self.data["completed"])
        self.tab_b.configure(text=f"[ 已完成 {count} ]")

    # ── 持久化 ──
    def save(self):
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        self.status.configure(text="已保存")

    def load(self):
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                try:
                    self.data = json.load(f)
                except Exception:
                    self.data = {"active": [], "completed": []}
        self._redraw()
        count = len(self.data["completed"])
        self.tab_b.configure(text=f"[ 已完成 {count} ]")

    def _snap_right(self):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = 380, 500
        x = sw - w - 40
        y = (sh - h) // 2
        # clamp to visible area
        x = max(-w + 60, min(sw - 60, x))
        y = max(-h + 60, min(sh - 60, y))
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # ── 热键 & 隐藏 ──

    def _poll_hotkey(self):
        try:
            ctrl = ctypes.windll.user32.GetAsyncKeyState(0x11) & 0x8000
            shift = ctypes.windll.user32.GetAsyncKeyState(0x10) & 0x8000
            m = ctypes.windll.user32.GetAsyncKeyState(0x4D) & 0x8000
            if ctrl and shift and m:
                if not self._hk_fired:
                    self._hk_fired = True
                    self._show()
            else:
                self._hk_fired = False
        except Exception:
            pass
        self.root.after(100, self._poll_hotkey)

    def _hide(self):
        self.save()
        self.root.withdraw()
        self.status.configure(text="Ctrl+Shift+M 呼出")

    def _show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.status.configure(text="")

    def _on_close(self):
        self.save()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ReminderApp(root)
    root.mainloop()
