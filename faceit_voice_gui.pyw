"""GUI for selecting FACEIT demo voice tracks."""
from __future__ import annotations

import queue
import json
import pathlib
import ctypes
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

from faceit_voice import analyze_demo, commands

BG, PANEL, FIELD = "#10141c", "#1b2230", "#131a25"
TEXT, MUTED, ACCENT = "#f2f5fa", "#a8b3c4", "#f39b32"


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("FACEIT Voice")
        width = min(1100, self.root.winfo_screenwidth() - 32)
        height = min(760, self.root.winfo_screenheight() - 90)
        x = (self.root.winfo_screenwidth() - width) // 2
        y = max(8, (self.root.winfo_screenheight() - height - 90) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(min(900, width), min(690, height))
        self.card_wraplength = max(330, (width - 130) // 2)
        self.root.configure(bg=BG)
        self.apply_window_style()
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.events = queue.Queue()
        self.path = tk.StringVar()
        self.status = tk.StringVar(value="Выберите демку FACEIT (.dem.zst или .dem)")
        self.custom_command = tk.StringVar(value="Выберите игроков в таблице")
        self.cards = []
        self.player_rows = []
        self.build()
        self.root.after(100, self.poll_events)
        if len(sys.argv) > 1:
            self.path.set(sys.argv[1])
            self.root.after(200, self.start)

    def apply_window_style(self):
        asset_dir = pathlib.Path(getattr(sys, "_MEIPASS", pathlib.Path(__file__).resolve().parent))
        icon = asset_dir / "faceit_voice.ico"
        if icon.is_file():
            self.root.iconbitmap(default=str(icon))
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

    def button(self, parent, label, action, muted=False):
        return tk.Button(parent, text=label, command=action, bg=FIELD if muted else ACCENT,
                         fg=TEXT if muted else BG, activebackground="#38465b" if muted else "#ffaf50",
                         activeforeground=TEXT if muted else BG, relief="flat", bd=0,
                         padx=12, cursor="hand2", font=("Segoe UI Semibold", 10))

    def build(self):
        main = tk.Frame(self.root, bg=BG, padx=24, pady=12)
        main.grid(sticky="nsew")
        main.columnconfigure(0, weight=1)
        tk.Label(main, text="FACEIT Voice", bg=BG, fg=TEXT,
                 font=("Segoe UI Semibold", 23)).grid(row=0, column=0, sticky="w")
        tk.Label(main, text="Слушай целую команду или выбери конкретных игроков", bg=BG,
                 fg=MUTED, font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", pady=(0, 8))

        path_row = tk.Frame(main, bg=BG)
        path_row.grid(row=2, column=0, sticky="ew")
        path_row.columnconfigure(0, weight=1)
        entry = tk.Entry(path_row, textvariable=self.path, bg=FIELD, fg=TEXT,
                         insertbackground=TEXT, relief="flat", font=("Segoe UI", 11),
                         highlightthickness=1, highlightbackground="#344050", highlightcolor=ACCENT)
        entry.grid(row=0, column=0, sticky="ew", ipady=9, padx=(0, 8))
        entry.bind("<Return>", lambda event: self.start())
        self.button(path_row, "Обзор…", self.browse, muted=True).grid(row=0, column=1, ipady=6)

        action_row = tk.Frame(main, bg=BG)
        action_row.grid(row=3, column=0, sticky="ew", pady=(6, 3))
        self.run_button = self.button(action_row, "Разобрать демку", self.start)
        self.run_button.pack(side="left", ipady=6)
        tk.Label(action_row, textvariable=self.status, bg=BG, fg=MUTED,
                 font=("Segoe UI", 10)).pack(side="left", padx=16)

        teams = tk.Frame(main, bg=BG)
        teams.grid(row=4, column=0, sticky="ew", pady=(2, 8))
        teams.columnconfigure((0, 1), weight=1, uniform="team")
        for number in (1, 2):
            card = tk.Frame(teams, bg=PANEL, padx=12, pady=8)
            card.grid(row=0, column=number - 1, sticky="nsew",
                      padx=(0, 6) if number == 1 else (6, 0))
            card.columnconfigure(0, weight=1)
            tk.Label(card, text=f"Команда {number}", bg=PANEL, fg=TEXT,
                     font=("Segoe UI Semibold", 13)).grid(row=0, column=0, sticky="w")
            names = tk.Label(card, text="—", bg=PANEL, fg=MUTED, font=("Segoe UI", 9),
                             anchor="w", justify="left", wraplength=self.card_wraplength)
            names.grid(row=1, column=0, sticky="ew", pady=(3, 5))
            cmd = tk.StringVar(value="—")
            tk.Entry(card, textvariable=cmd, bg=FIELD, fg=TEXT, readonlybackground=FIELD,
                     relief="flat", font=("Consolas", 9), state="readonly").grid(
                         row=2, column=0, sticky="ew", ipady=6)
            actions = tk.Frame(card, bg=PANEL)
            actions.grid(row=3, column=0, sticky="w", pady=(4, 0))
            copy = self.button(actions, "Копировать", lambda n=number: self.copy_team(n), muted=True)
            copy.pack(side="left", ipady=3)
            select = self.button(actions, "Выбрать этих игроков",
                                 lambda n=number: self.select_team(n), muted=True)
            select.pack(side="left", padx=(8, 0), ipady=3)
            copy.configure(state="disabled")
            select.configure(state="disabled")
            self.cards.append((names, cmd, copy, select))

        panel = tk.Frame(main, bg=PANEL, padx=12, pady=8)
        panel.grid(row=5, column=0, sticky="ew")
        panel.columnconfigure(0, weight=1)
        tk.Label(panel, text="Игроки", bg=PANEL, fg=TEXT,
                 font=("Segoe UI Semibold", 13)).grid(row=0, column=0, sticky="w")
        table = tk.Frame(panel, bg=PANEL)
        table.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        table.columnconfigure(0, weight=1)
        table.columnconfigure(1, minsize=130)
        table.columnconfigure(2, minsize=100)
        for col, name in enumerate(("Ник", "Команда", "Слушать")):
            tk.Label(table, text=name, bg=PANEL, fg=MUTED, font=("Segoe UI Semibold", 9),
                     anchor="w").grid(row=0, column=col, sticky="ew", pady=(0, 2))
        self.table_body = tk.Frame(table, bg=PANEL)
        self.table_body.grid(row=1, column=0, columnspan=3, sticky="ew")
        self.table_body.columnconfigure(0, weight=1)
        self.table_body.columnconfigure(1, minsize=130)
        self.table_body.columnconfigure(2, minsize=100)
        tk.Label(self.table_body, text="После загрузки здесь появятся 10 игроков", bg=PANEL,
                 fg=MUTED, font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", pady=8)

        custom = tk.Frame(main, bg=BG)
        custom.grid(row=6, column=0, sticky="ew", pady=(8, 0))
        custom.columnconfigure(0, weight=1)
        tk.Label(custom, text="Выбранные игроки", bg=BG, fg=TEXT,
                 font=("Segoe UI Semibold", 12)).grid(row=0, column=0, sticky="w", pady=(0, 3))
        line = tk.Frame(custom, bg=BG)
        line.grid(row=1, column=0, sticky="ew")
        line.columnconfigure(0, weight=1)
        tk.Entry(line, textvariable=self.custom_command, bg=FIELD, fg=TEXT,
                 readonlybackground=FIELD, relief="flat", font=("Consolas", 10),
                 state="readonly").grid(row=0, column=0, sticky="ew", ipady=9, padx=(0, 8))
        self.custom_copy = self.button(line, "Копировать", self.copy_custom)
        self.custom_copy.grid(row=0, column=1, ipady=6)
        self.custom_copy.configure(state="disabled")

    def browse(self):
        path = filedialog.askopenfilename(title="Выберите демку FACEIT",
                                          filetypes=[("Демки CS2", "*.dem.zst *.dem"), ("Все файлы", "*.*")])
        if path:
            self.path.set(path)
            self.start()

    def clear_result(self):
        self.player_rows.clear()
        for child in self.table_body.winfo_children():
            child.destroy()
        self.custom_command.set("Выберите игроков в таблице")
        self.custom_copy.configure(state="disabled")
        for names, cmd, copy, select in self.cards:
            names.configure(text="—")
            cmd.set("—")
            copy.configure(state="disabled")
            select.configure(state="disabled")

    def start(self):
        path = self.path.get().strip().strip('"')
        if not path:
            messagebox.showinfo("FACEIT Voice", "Выберите или вставьте путь к демке.")
            return
        self.run_button.configure(state="disabled")
        self.status.set("Обрабатываю демку...")
        self.clear_result()
        threading.Thread(target=self.worker, args=(path,), daemon=True).start()

    def worker(self, path):
        try:
            result = analyze_demo(path, status=lambda text: self.events.put(("status", text)))
            self.events.put(("done", result))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def poll_events(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "status":
                    self.status.set(value)
                elif kind == "done":
                    self.show_result(value)
                elif kind == "error":
                    self.status.set("Ошибка")
                    self.run_button.configure(state="normal")
                    messagebox.showerror("FACEIT Voice", value)
        except queue.Empty:
            pass
        self.root.after(100, self.poll_events)

    def show_result(self, result):
        self.status.set(f"{result['map']} · {result['found']} игроков")
        if result["found"] < result["expected"]:
            self.status.set(self.status.get() + f" (ожидалось {result['expected']})")
        for group in result["groups"]:
            names, cmd, copy, select = self.cards[group["number"] - 1]
            names.configure(text=", ".join(p["name"] for p in group["players"]))
            cmd.set(group["command"])
            copy.configure(state="normal")
            select.configure(state="normal")
            for player in group["players"]:
                row = len(self.player_rows)
                enabled = tk.BooleanVar(value=False)
                label = tk.StringVar(value="Нет")
                tk.Label(self.table_body, text=f"{player['name']}  ·  слот {player['user_id'] + 1}",
                         bg=PANEL, fg=TEXT, font=("Segoe UI", 10), anchor="w").grid(
                             row=row, column=0, sticky="ew")
                tk.Label(self.table_body, text=f"Команда {group['number']}", bg=PANEL, fg=MUTED,
                         font=("Segoe UI", 10), anchor="w").grid(row=row, column=1, sticky="ew")
                tk.Checkbutton(self.table_body, variable=enabled, textvariable=label,
                               command=self.update_custom, indicatoron=False,
                               bg=FIELD, fg=TEXT, activebackground=ACCENT,
                               activeforeground=BG, selectcolor=ACCENT, relief="flat",
                               font=("Segoe UI Semibold", 9), width=7).grid(row=row, column=2, sticky="w")
                self.player_rows.append((player, enabled, label))
        self.run_button.configure(state="normal")

    def update_custom(self):
        selected = []
        for player, enabled, label in self.player_rows:
            label.set("Да" if enabled.get() else "Нет")
            if enabled.get():
                selected.append(player)
        if selected:
            low, high = commands(selected)
            self.custom_command.set(f"tv_listen_voice_indices {low}; tv_listen_voice_indices_h {high}")
            self.custom_copy.configure(state="normal")
        else:
            self.custom_command.set("Выберите игроков в таблице")
            self.custom_copy.configure(state="disabled")

    def select_team(self, number):
        for player, enabled, _ in self.player_rows:
            enabled.set(player["team"] == (2 if number == 1 else 3))
        self.update_custom()

    def copy_text(self, value, label):
        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self.status.set(f"{label}: команда скопирована")

    def copy_team(self, number):
        self.copy_text(self.cards[number - 1][1].get(), f"Команда {number}")

    def copy_custom(self):
        self.copy_text(self.custom_command.get(), "Выбранные игроки")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--self-test":
        try:
            result = analyze_demo(sys.argv[2])
            pathlib.Path(sys.argv[3]).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            pathlib.Path(sys.argv[3]).write_text(json.dumps({"error": str(exc)}, ensure_ascii=False), encoding="utf-8")
            sys.exit(1)
    else:
        App().run()
