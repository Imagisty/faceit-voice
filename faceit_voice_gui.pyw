"""Lightweight desktop mixer for FACEIT demo voice commands."""
from __future__ import annotations

import ctypes
import json
import pathlib
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, font as tkfont

from faceit_voice import analyze_demo, commands, export_audio
from switch_art import SWITCH_IMAGES

BG = "#14171C"
PANEL = "#1C2027"
FIELD = "#252B34"
BORDER = "#303741"
TEXT = "#F2F4F7"
MUTED = "#A2ACB9"
DIM = "#718092"
ACCENT = "#FF8A4C"
BLUE = "#7DB4FF"
GREEN = "#8AD5AE"


def rounded(canvas, x1, y1, x2, y2, radius, **kwargs):
    r = min(radius, (x2 - x1) / 2, (y2 - y1) / 2)
    return canvas.create_polygon(
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        smooth=True, splinesteps=24, **kwargs,
    )


class Surface(tk.Canvas):
    def __init__(self, parent, color=PANEL, padding=18, **kwargs):
        super().__init__(parent, bg=parent.cget("bg"), highlightthickness=0, bd=0, **kwargs)
        self.color = color
        self.content = tk.Frame(self, bg=color)
        self.content.place(x=padding, y=padding, relwidth=1, width=-2 * padding,
                           relheight=1, height=-2 * padding)
        self.bind("<Configure>", self.paint)

    def paint(self, event=None):
        self.delete("surface")
        rounded(self, 1, 1, self.winfo_width() - 1, self.winfo_height() - 1,
                14, fill=self.color, outline=BORDER, width=1, tags="surface")
        self.tag_lower("surface")


class Button(tk.Canvas):
    def __init__(self, parent, text, command, width=132, height=38, primary=False):
        super().__init__(parent, width=width, height=height, bg=parent.cget("bg"),
                         highlightthickness=0, bd=0, takefocus=True, cursor="hand2")
        self.text = text
        self.command = command
        self.primary = primary
        self.enabled = True
        self.hover = False
        self.bind("<Configure>", self.paint)
        self.bind("<Enter>", lambda e: self.set_hover(True))
        self.bind("<Leave>", lambda e: self.set_hover(False))
        self.bind("<Button-1>", self.invoke)
        self.bind("<space>", self.invoke)
        self.bind("<Return>", self.invoke)
        self.bind("<FocusIn>", self.paint)
        self.bind("<FocusOut>", self.paint)

    def set_hover(self, value):
        self.hover = value
        self.paint()

    def set_enabled(self, value):
        self.enabled = value
        self.configure(cursor="hand2" if value else "arrow", takefocus=value)
        self.paint()

    def set_text(self, text):
        self.text = text
        self.paint()

    def invoke(self, event=None):
        if self.enabled:
            self.focus_set()
            self.command()
        return "break"

    def paint(self, event=None):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        fill = ("#FFA16E" if self.hover else ACCENT) if self.primary else ("#353E4B" if self.hover else FIELD)
        fg = BG if self.primary else TEXT
        if not self.enabled:
            fill, fg = FIELD, DIM
        outline = ACCENT if self.focus_get() is self else fill
        rounded(self, 2, 2, w - 2, h - 2, 9, fill=fill, outline=outline, width=2)
        self.create_text(w / 2, h / 2, text=self.text, fill=fg, font=("Segoe UI Semibold", 10))


class Switch(tk.Canvas):
    def __init__(self, parent, variable, command, color):
        super().__init__(parent, width=82, height=34, bg=parent.cget("bg"),
                         highlightthickness=0, bd=0, takefocus=True, cursor="hand2")
        self.variable, self.command, self.color = variable, command, color
        self.enabled = True
        root = self._root()
        if not hasattr(root, "_switch_images"):
            root._switch_images = {name: tk.PhotoImage(master=root, data=data)
                                   for name, data in SWITCH_IMAGES.items()}
        self.images = root._switch_images
        self.bind("<Button-1>", self.toggle)
        self.bind("<space>", self.toggle)
        self.bind("<Return>", self.toggle)
        self.bind("<FocusIn>", self.paint)
        self.bind("<FocusOut>", self.paint)
        self.variable.trace_add("write", lambda *_: self.paint())
        self.bind("<Configure>", self.paint)

    def toggle(self, event=None):
        if not self.enabled:
            return "break"
        self.focus_set()
        self.variable.set(not self.variable.get())
        self.command()
        return "break"

    def paint(self, event=None):
        self.delete("all")
        enabled = self.variable.get()
        self.create_text(14, 17, text="Да" if enabled else "Нет", fill=self.color if enabled else MUTED,
                         font=("Segoe UI", 9))
        state = ("orange" if self.color == ACCENT else "blue") if enabled else "off"
        if self.focus_get() is self:
            state += "_focus"
        self.create_image(35, 3, anchor="nw", image=self.images[state])


class PlayerRow(tk.Frame):
    def __init__(self, parent, player, color, update):
        super().__init__(parent, bg=PANEL, height=58)
        self.pack_propagate(False)
        self.player = player
        self.color = color
        self.enabled = tk.BooleanVar(value=False)
        self.avatar = tk.Canvas(self, width=34, height=34, bg=PANEL, highlightthickness=0)
        self.avatar.pack(side="left", padx=(4, 10))
        self.avatar.create_oval(1, 1, 33, 33, fill=FIELD, outline="")
        initials = ''.join(c for c in player['name'] if c.isalnum())[:2].upper() or '?'
        self.avatar.create_text(17, 17, text=initials, fill=color, font=("Segoe UI Semibold", 9))
        self.switch = Switch(self, self.enabled, update, color)
        self.switch.pack(side="right", padx=(4, 2))
        self.name = tk.Label(self, text=player["name"], bg=PANEL, fg=TEXT,
                             anchor="w", font=("Segoe UI Semibold", 10))
        self.name.pack(side="left", fill="x", expand=True)
        self.name.bind("<Configure>", self.fit_name)
        self.enabled.trace_add("write", self.refresh)
        for widget in (self, self.avatar, self.name):
            widget.bind("<Button-1>", self.switch.toggle)
            widget.configure(cursor="hand2")

    def fit_name(self, event=None):
        value = self.player["name"]
        font = tkfont.Font(font=self.name.cget("font"))
        width = max(25, self.name.winfo_width() - 4)
        while len(value) > 1 and font.measure(value) > width:
            value = value[:-2] + "…" if value.endswith("…") else value[:-1] + "…"
        self.name.configure(text=value)

    def refresh(self, *_):
        bg = "#292A2B" if self.enabled.get() and self.color == ACCENT else "#222C38" if self.enabled.get() else PANEL
        for widget in (self, self.avatar, self.name, self.switch):
            widget.configure(bg=bg)
        self.switch.paint()


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("FACEIT Voice")
        width = min(1200, self.root.winfo_screenwidth() - 40)
        height = min(800, self.root.winfo_screenheight() - 90)
        self.root.geometry(f"{width}x{height}+{max(0, (self.root.winfo_screenwidth()-width)//2)}+{max(10, (self.root.winfo_screenheight()-height)//2-25)}")
        self.root.minsize(min(1060, width), min(700, height))
        self.root.configure(bg=BG)
        self.root.option_add("*Font", ("Segoe UI", 10))
        self.apply_window_style()
        self.events = queue.Queue()
        self.path = tk.StringVar()
        self.status = tk.StringVar(value="")
        self.match = tk.StringVar(value="Демка не выбрана")
        self.audio_directory = tk.StringVar()
        self.loaded_demo = None
        self.pending_demo = None
        self.exporting = False
        self.custom_command = tk.StringVar(value="")
        self.player_rows = []
        self.teams = []
        self.busy = False
        self.build()
        self.root.after(100, self.poll_events)
        self.root.bind("<Control-o>", lambda e: self.browse())
        if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
            self.path.set(sys.argv[1])
            self.root.after(200, self.start)

    def apply_window_style(self):
        base = pathlib.Path(getattr(sys, "_MEIPASS", pathlib.Path(__file__).resolve().parent))
        if (base / "faceit_voice.ico").is_file():
            self.root.iconbitmap(default=str(base / "faceit_voice.ico"))
        if sys.platform == "win32":
            self.root.update_idletasks()
            user32 = ctypes.windll.user32
            user32.GetParent.argtypes = [ctypes.c_void_p]
            user32.GetParent.restype = ctypes.c_void_p
            hwnd = user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
            dark = ctypes.c_int(1)
            dwm = ctypes.windll.dwmapi.DwmSetWindowAttribute
            dwm.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint]
            dwm(hwnd, 20, ctypes.byref(dark), ctypes.sizeof(dark))

    def label(self, parent, text=None, size=10, color=TEXT, bold=False, **kwargs):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color,
                        font=("Segoe UI Semibold" if bold else "Segoe UI", size), bd=0, **kwargs)

    def build(self):
        main = tk.Frame(self.root, bg=BG, padx=24, pady=20)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(3, weight=1)
        header = tk.Frame(main, bg=BG, height=54)
        header.grid(row=0, column=0, sticky="ew")
        header.pack_propagate(False)
        logo = tk.Canvas(header, width=42, height=44, bg=BG, highlightthickness=0)
        logo.pack(side="left", padx=(0, 12), anchor="n", pady=4)
        for x, h in ((7, 14), (16, 30), (25, 40), (34, 22)):
            logo.create_line(x, 22-h/2, x, 22+h/2, width=5, fill=ACCENT, capstyle="round")
        title = tk.Frame(header, bg=BG)
        title.pack(side="left", anchor="n")
        tk.Label(title, text="FACEIT Voice", bg=BG, fg=TEXT, font=("Bahnschrift", 25), bd=0).pack(anchor="w")

        file_panel = Surface(main, height=98, padding=16)
        file_panel.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        file_body = file_panel.content
        file_body.columnconfigure(0, weight=1)
        self.label(file_body, "Демка матча", bold=True).grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.label(file_body, ".dem  /  .dem.zst", color=MUTED, size=9).grid(row=0, column=1, columnspan=2, sticky="e", pady=(0, 8))
        entry = tk.Entry(file_body, textvariable=self.path, bg=FIELD, fg=TEXT,
                         insertbackground=ACCENT, relief="flat", bd=0, font=("Segoe UI", 10),
                         highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT)
        entry.grid(row=1, column=0, sticky="ew", ipady=9, padx=(0, 10))
        entry.bind("<Return>", lambda e: self.start())
        self.browse_button = Button(file_body, "Выбрать файл", self.browse, width=134)
        self.browse_button.grid(row=1, column=1, padx=(0, 8))
        self.run_button = Button(file_body, "Разобрать демку", self.start, width=162, primary=True)
        self.run_button.grid(row=1, column=2)

        section = tk.Frame(main, bg=BG, height=54)
        section.grid(row=2, column=0, sticky="ew")
        section.pack_propagate(False)
        self.label(section, "Кого слушаем?", size=16, bold=True).pack(side="left")
        self.label(section, textvariable=self.match, color=MUTED, size=10).pack(side="left", padx=16)
        self.none_button = Button(section, "Сбросить", lambda: self.select_all(False), width=100, height=32)
        self.none_button.pack(side="right")
        self.all_button = Button(section, "Выбрать всех", lambda: self.select_all(True), width=130, height=32)
        self.all_button.pack(side="right", padx=(0, 8))
        self.all_button.set_enabled(False)
        self.none_button.set_enabled(False)

        body = tk.Frame(main, bg=BG)
        body.grid(row=3, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.columnconfigure(2, minsize=316)
        body.rowconfigure(0, weight=1)
        for number, color in ((1, ACCENT), (2, BLUE)):
            surface = Surface(body, padding=14, width=320)
            surface.grid(row=0, column=number-1, sticky="nsew", padx=(0, 12))
            card = surface.content
            card.columnconfigure(0, weight=1)
            card.rowconfigure(1, weight=1)
            team_header = tk.Frame(card, bg=PANEL, height=48)
            team_header.grid(row=0, column=0, sticky="ew")
            team_header.pack_propagate(False)
            self.label(team_header, f"Команда {number}", size=14, color=color, bold=True).pack(side="left", anchor="n", pady=4)
            select = Button(team_header, "Выбрать", lambda n=number: self.select_team(n), width=96, height=32)
            select.pack(side="right", anchor="n")
            select.set_enabled(False)
            viewport = tk.Canvas(card, bg=PANEL, highlightthickness=0, bd=0, width=1, height=1)
            viewport.grid(row=1, column=0, sticky="nsew")
            roster = tk.Frame(viewport, bg=PANEL)
            window = viewport.create_window(0, 0, anchor="nw", window=roster)
            viewport.bind("<Configure>", lambda e, n=number: self.resize_roster(self.teams[n-1]))
            roster.bind("<Configure>", lambda e, v=viewport: v.configure(scrollregion=v.bbox("all")))
            def scroll(event, v=viewport):
                if v.bbox("all") and v.bbox("all")[3] > v.winfo_height():
                    v.yview_scroll(-int(event.delta / 120), "units")
            viewport.bind("<MouseWheel>", scroll)
            copy = Button(card, "Копировать команду", lambda n=number: self.copy_team(n), width=240, height=40)
            copy.grid(row=2, column=0, sticky="ew", pady=(14, 0))
            copy.set_enabled(False)
            self.teams.append(dict(roster=roster, copy=copy, select=select, command="", viewport=viewport, window=window, scroll=scroll))

        output = Surface(body, padding=20, color="#20252D", width=316)
        output.grid(row=0, column=2, sticky="nsew")
        right = output.content
        count_row = tk.Frame(right, bg=right.cget("bg"))
        count_row.pack(fill="x", pady=(4, 0))
        self.count = tk.Label(count_row, text="0", bg=right.cget("bg"), fg=TEXT, font=("Bahnschrift", 34), bd=0)
        self.count.pack(side="left", anchor="s")
        self.total = self.label(count_row, "игроков выбрано", color=MUTED, size=10)
        self.total.pack(side="left", anchor="s", padx=(10, 0), pady=(0, 10))
        self.meter = tk.Canvas(right, height=18, bg=right.cget("bg"), highlightthickness=0)
        self.meter.pack(fill="x", pady=(4, 12))
        self.meter.bind("<Configure>", lambda e: self.paint_meter())
        self.label(right, "Команда для консоли CS2", size=9, color=MUTED).pack(anchor="w", pady=(0, 10))
        code_box = tk.Frame(right, bg=BG, padx=12, pady=10)
        code_box.pack(fill="x")
        self.code = tk.Label(code_box, text="Выбери игроков\nпереключателями слева", bg=BG, fg=MUTED,
                             font=("Consolas", 9), anchor="w", justify="left", height=2, bd=0)
        self.code.pack(fill="x")
        self.custom_copy = Button(right, "Копировать команду", self.copy_custom, primary=True, height=44)
        self.custom_copy.pack(fill="x", pady=(12, 0))
        self.custom_copy.set_enabled(False)
        self.feedback = self.label(right, "", size=9, color=GREEN)
        self.feedback.pack(anchor="w", pady=(8, 0))
        audio_panel = Surface(main, height=100, padding=16)
        audio_panel.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        audio_body = audio_panel.content
        audio_body.columnconfigure(0, weight=1)
        self.label(audio_body, "Аудиодорожки", bold=True).grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.label(audio_body, "Отдельный .opus для каждого выбранного игрока", size=9, color=MUTED).grid(
            row=0, column=1, columnspan=2, sticky="e", pady=(0, 8))
        self.folder_entry = tk.Entry(audio_body, textvariable=self.audio_directory, bg=FIELD, fg=TEXT,
                                    insertbackground=ACCENT, relief="flat", bd=0,
                                    highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT)
        self.folder_entry.grid(row=1, column=0, sticky="ew", ipady=9, padx=(0, 10))
        self.folder_button = Button(audio_body, "Выбрать папку", self.choose_audio_folder, width=134)
        self.folder_button.grid(row=1, column=1, padx=(0, 8))
        self.export_button = Button(audio_body, "Сохранить аудио", self.start_export, width=162, primary=True)
        self.export_button.grid(row=1, column=2)
        self.export_button.set_enabled(False)

        footer = tk.Frame(main, bg=BG, height=30)
        footer.grid(row=5, column=0, sticky="ew")
        footer.pack_propagate(False)
        self.status_label = self.label(footer, textvariable=self.status, color=MUTED, size=9, anchor="w")
        self.status_label.pack(side="left", fill="x", expand=True)
        self.label(footer, "FACEIT Voice 1.3.1", color=DIM, size=9).pack(side="right", padx=(12, 0))
        self.clear_result()

    def resize_roster(self, team):
        viewport = team["viewport"]
        viewport.itemconfigure(team["window"], width=viewport.winfo_width())
        rows = [child for child in team["roster"].winfo_children() if isinstance(child, PlayerRow)]
        available = viewport.winfo_height() // max(5, len(rows))
        gap = 2 if available >= 42 else 0
        height = max(34, min(58, available - gap))
        for row in rows:
            row.configure(height=height)
            row.pack_configure(pady=(0, gap))

    def show_empty(self, text="Выбери демку матча", detail="Здесь появятся игроки команды"):
        for team in self.teams:
            for child in team["roster"].winfo_children():
                child.destroy()
            self.label(team["roster"], text, size=11, bold=True).pack(pady=(68, 8))
            self.label(team["roster"], detail, size=9, color=MUTED).pack()

    def clear_result(self):
        self.loaded_demo = None
        self.player_rows.clear()
        for team in self.teams:
            team["command"] = ""
            team["copy"].set_enabled(False)
            team["select"].set_enabled(False)
        self.all_button.set_enabled(False)
        self.none_button.set_enabled(False)
        self.feedback.configure(text="")
        self.show_empty()
        self.update_custom()

    def browse(self):
        if self.busy:
            return
        path = filedialog.askopenfilename(title="Выберите демку FACEIT",
                                          filetypes=[("Демки CS2", "*.dem.zst *.dem"), ("Все файлы", "*.*")])
        if path:
            self.path.set(path)
            self.start()

    def start(self):
        if self.busy:
            return
        path = self.path.get().strip().strip('"')
        if not path:
            self.status.set("Выбери файл или вставь путь к демке в поле выше.")
            return
        self.busy = True
        self.pending_demo = path
        self.run_button.set_enabled(False)
        self.browse_button.set_enabled(False)
        self.run_button.set_text("Читаю демку…")
        self.status.set("Распаковываю демку и читаю состав команд…")
        self.status_label.configure(fg=MUTED)
        self.match.set("Загрузка…")
        self.clear_result()
        self.show_empty("Читаю демку…", "Состав команды появится здесь")
        threading.Thread(target=self.worker, args=(path,), daemon=True).start()

    def worker(self, path):
        try:
            result = analyze_demo(path, status=lambda text: self.events.put(("status", text)))
            self.events.put(("done", result))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def finish_loading(self):
        self.busy = False
        self.run_button.set_enabled(True)
        self.browse_button.set_enabled(True)
        self.run_button.set_text("Разобрать демку")

    def poll_events(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "status":
                    self.status.set(value)
                elif kind == "done":
                    self.show_result(value)
                elif kind == "error":
                    self.finish_loading()
                    self.match.set("Не удалось открыть демку")
                    self.status.set(value.replace("\n", " ")[:150])
                    self.status_label.configure(fg=ACCENT)
                    self.show_empty("Не удалось прочитать файл", "Попробуй выбрать другую демку")
                elif kind == "export_done":
                    self.finish_export()
                    suffix = f"; без записанного голоса: {len(value['missing'])}" if value["missing"] else ""
                    self.status.set(f"Сохранено дорожек: {len(value['tracks'])}{suffix}. {value['directory']}")
                    self.feedback.configure(text=f"✓  Сохранено дорожек: {len(value['tracks'])}")
                elif kind == "export_error":
                    self.finish_export()
                    self.status.set(value.replace("\n", " ")[:160])
                    self.status_label.configure(fg=ACCENT)
        except queue.Empty:
            pass
        self.root.after(100, self.poll_events)

    def show_result(self, result):
        self.loaded_demo = self.pending_demo
        self.player_rows.clear()
        for team in self.teams:
            for child in team["roster"].winfo_children():
                child.destroy()
        for group in result["groups"]:
            team = self.teams[group["number"] - 1]
            team["command"] = group["command"]
            team["copy"].set_enabled(True)
            team["select"].set_enabled(True)
            color = ACCENT if group["number"] == 1 else BLUE
            for player in group["players"]:
                row = PlayerRow(team["roster"], player, color, self.update_custom)
                row.pack(fill="x", pady=(0, 2))
                for widget in (row, row.name, row.avatar, row.switch):
                    widget.bind("<MouseWheel>", team["scroll"])
                self.player_rows.append(row)
        self.match.set(f"{result['map']}  /  {result['found']} игроков")
        self.status.set("")
        if result["found"] < result["expected"]:
            self.status.set(f"Найдено {result['found']} из {result['expected']} игроков. Часть игроков могла подключиться позже.")
        self.all_button.set_enabled(True)
        self.none_button.set_enabled(True)
        self.finish_loading()
        self.update_custom()
        self.root.after_idle(lambda: [self.resize_roster(team) for team in self.teams])

    def paint_meter(self):
        self.meter.delete("all")
        rows = self.player_rows
        count = max(10, len(rows))
        width = max(10, self.meter.winfo_width())
        step = width / count
        for index in range(count):
            color = rows[index].color if index < len(rows) and rows[index].enabled.get() else "#3C4653"
            rounded(self.meter, index * step, 3, (index+1) * step - 4, 12, 3, fill=color, outline="")

    def update_custom(self):
        selected = [row.player for row in self.player_rows if row.enabled.get()]
        self.count.configure(text=str(len(selected)))
        self.total.configure(text=f"из {len(self.player_rows)} игроков" if self.player_rows else "игроков выбрано")
        self.feedback.configure(text="")
        if selected:
            low, high = commands(selected)
            self.custom_command.set(f"tv_listen_voice_indices {low}; tv_listen_voice_indices_h {high}")
            self.code.configure(text=f"tv_listen_voice_indices {low};\ntv_listen_voice_indices_h {high}", fg=TEXT)
        else:
            self.custom_command.set("")
            self.code.configure(text="Выбери игроков\nпереключателями слева", fg=MUTED)
        self.custom_copy.set_enabled(bool(selected))
        self.export_button.set_enabled(bool(selected) and not self.busy and bool(self.loaded_demo))
        self.paint_meter()

    def choose_audio_folder(self):
        if self.exporting:
            return
        directory = filedialog.askdirectory(title="Куда сохранить аудиодорожки", mustexist=True)
        if directory:
            self.audio_directory.set(directory)

    def start_export(self):
        if self.busy or not self.loaded_demo:
            return
        selected = [row.player.copy() for row in self.player_rows if row.enabled.get()]
        if not selected:
            return
        if not self.audio_directory.get().strip():
            self.choose_audio_folder()
        directory = self.audio_directory.get().strip()
        if not directory:
            return
        self.busy = self.exporting = True
        self.export_button.set_enabled(False)
        self.export_button.set_text("Сохраняю…")
        self.run_button.set_enabled(False)
        self.browse_button.set_enabled(False)
        self.folder_button.set_enabled(False)
        self.folder_entry.configure(state="disabled")
        self.all_button.set_enabled(False)
        self.none_button.set_enabled(False)
        for team in self.teams:
            team["select"].set_enabled(False)
        for row in self.player_rows:
            row.switch.enabled = False
        self.status_label.configure(fg=MUTED)
        self.status.set("Извлекаю голосовые записи из демки…")
        threading.Thread(target=self.export_worker, args=(self.loaded_demo, directory, selected), daemon=True).start()

    def export_worker(self, demo, directory, players):
        try:
            self.events.put(("export_done", export_audio(demo, directory, players)))
        except Exception as exc:
            self.events.put(("export_error", str(exc)))

    def finish_export(self):
        self.busy = self.exporting = False
        self.run_button.set_enabled(True)
        self.browse_button.set_enabled(True)
        self.folder_button.set_enabled(True)
        self.folder_entry.configure(state="normal")
        self.all_button.set_enabled(True)
        self.none_button.set_enabled(True)
        for team in self.teams:
            team["select"].set_enabled(bool(team["command"]))
        for row in self.player_rows:
            row.switch.enabled = True
        self.export_button.set_text("Сохранить аудио")
        self.update_custom()

    def select_team(self, number):
        for row in self.player_rows:
            row.enabled.set(row.player["team"] == (2 if number == 1 else 3))
        self.update_custom()

    def select_all(self, value):
        for row in self.player_rows:
            row.enabled.set(value)
        self.update_custom()

    def copy_text(self, value, label):
        if value:
            self.root.clipboard_clear()
            self.root.clipboard_append(value)
            self.feedback.configure(text=f"✓  {label} скопирован")
            self.status.set("Команда скопирована. Вставь её в консоль CS2 при просмотре демки.")

    def copy_team(self, number):
        self.copy_text(self.teams[number-1]["command"], f"Состав {number}")

    def copy_custom(self):
        self.copy_text(self.custom_command.get(), "Выбор")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "--self-test-audio":
        try:
            roster = analyze_demo(sys.argv[2])
            players = [p for group in roster["groups"] for p in group["players"]]
            result = export_audio(sys.argv[2], sys.argv[3], players)
            pathlib.Path(sys.argv[4]).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            pathlib.Path(sys.argv[4]).write_text(json.dumps({"error": str(exc)}, ensure_ascii=False), encoding="utf-8")
            sys.exit(1)
    elif len(sys.argv) == 4 and sys.argv[1] == "--self-test":
        try:
            result = analyze_demo(sys.argv[2])
            pathlib.Path(sys.argv[3]).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            pathlib.Path(sys.argv[3]).write_text(json.dumps({"error": str(exc)}, ensure_ascii=False), encoding="utf-8")
            sys.exit(1)
    else:
        App().run()
