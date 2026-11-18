# -*- coding: utf-8 -*-
"""Графический интерфейс ESP_TEST (Tkinter, тёмная тема)."""

from __future__ import annotations

import os
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import serial.tools.list_ports

import chipdb
from probe import Cancelled, EspProbe, ProbeError, list_serial_ports, usb_esp_devices
from version import APP_NAME, __version__
from i18n import (confirm_hint, confirm_word, get_lang, load_settings, save_settings,
                  set_lang, tr, tr_lines, tr_tree)

# ---------------------------------------------------------------------------
# палитра и шрифты
# ---------------------------------------------------------------------------
C = {
    "bg": "#0a0e13",
    "panel": "#111a23",
    "panel2": "#18242f",
    "border": "#22303c",
    "text": "#e9f0f7",
    "muted": "#7d8fa1",
    "accent": "#2dd4bf",
    "accent_dark": "#0f766e",
    "blue": "#38bdf8",
    "ok": "#4ade80",
    "warn": "#fbbf24",
    "err": "#f87171",
}

F_TITLE = ("Segoe UI", 15, "bold")
F_H2 = ("Segoe UI", 10, "bold")
F_BODY = ("Segoe UI", 9)
F_BOLD = ("Segoe UI", 9, "bold")
F_TINY = ("Segoe UI", 8, "bold")
F_MONO = ("Consolas", 9)
F_BIG = ("Segoe UI", 26, "bold")
F_MID = ("Segoe UI", 15, "bold")


def _tf(value):
    """True/False/None -> OK / ОШИБКА / —"""
    return {True: "OK", False: "ОШИБКА", None: "—"}.get(value, "—")


def round_rect(canvas, x1, y1, x2, y2, r, **kw):
    """Скруглённый прямоугольник на Canvas."""
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    pts = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(pts, smooth=True, **kw)


# ---------------------------------------------------------------------------
# виджеты
# ---------------------------------------------------------------------------
class RButton(tk.Canvas):
    """Кнопка со скруглёнными углами."""

    STYLES = {
        "primary": (C["accent"], "#0a2b28", "#5eead4"),
        "blue": (C["blue"], "#062434", "#7dd3fc"),
        "ghost": (C["panel2"], C["text"], "#22323f"),
        "danger": ("#2a1a1d", "#f87171", "#3a2226"),
    }

    def __init__(self, master, text, command=None, kind="ghost", height=36,
                 width=140, font=None, parent_bg=None):
        self.bgc = parent_bg or master["bg"]
        super().__init__(master, height=height, width=width, bg=self.bgc,
                         highlightthickness=0, bd=0, cursor="hand2")
        self._text = text
        self._command = command
        self._kind = kind
        self._font = font or F_BOLD
        self._enabled = True
        self._hover = False
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<Button-1>", self._click)
        self._draw()

    # --
    def _set_hover(self, value):
        if self._hover != value:
            self._hover = value
            self._draw()

    def _click(self, _event):
        if self._enabled and self._command:
            self._command()

    def set_enabled(self, value: bool):
        self._enabled = bool(value)
        self.configure(cursor="hand2" if value else "arrow")
        self._draw()

    def set_text(self, text):
        self._text = text
        self._draw()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width() or int(self["width"])
        h = self.winfo_height() or int(self["height"])
        if w <= 2 or h <= 2:
            return
        if not self._enabled:
            fill, fg = C["panel2"], "#5a6b7b"
        else:
            fill, fg, hover = self.STYLES.get(self._kind, self.STYLES["ghost"])
            if self._hover:
                fill = hover
        outline = C["border"] if self._kind == "ghost" and self._enabled else fill
        round_rect(self, 1, 1, w - 1, h - 1, 9, fill=fill, outline=outline)
        self.create_text(w / 2, h / 2 + 1, text=self._text, fill=fg, font=self._font)


class Bar(tk.Canvas):
    """Индикатор-полоска."""

    def __init__(self, master, height=10, parent_bg=None, color=None):
        super().__init__(master, height=height, bg=parent_bg or C["panel"],
                         highlightthickness=0, bd=0)
        self._value = 0.0
        self._color = color or C["accent"]
        self.bind("<Configure>", lambda e: self._draw())

    def set(self, frac, color=None):
        self._value = max(0.0, min(1.0, float(frac)))
        if color:
            self._color = color
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 2:
            return
        r = h / 2
        round_rect(self, 0, 0, w, h, r, fill=C["panel2"], outline="")
        if self._value > 0:
            fw = max(w * self._value, h)
            round_rect(self, 0, 0, fw, h, r, fill=self._color, outline="")


class Badge(tk.Canvas):
    """Цветная «пилюля» с текстом."""

    def __init__(self, master, text="", level="muted", parent_bg=None):
        super().__init__(master, height=24, bg=parent_bg or C["panel"],
                         highlightthickness=0, bd=0)
        self._text = text
        self._level = level
        self._font = F_TINY
        self.bind("<Configure>", lambda e: self._draw())
        self._draw()

    def set(self, text, level="muted"):
        self._text = text
        self._level = level
        self._draw()

    def _draw(self):
        self.delete("all")
        colors = {
            "ok": (C["ok"], "#0d2b1c"),
            "warn": (C["warn"], "#2d2410"),
            "err": (C["err"], "#2d1518"),
            "muted": (C["muted"], C["panel2"]),
        }
        fg, bg = colors.get(self._level, colors["muted"])
        h = int(self["height"])
        self.delete("all")
        if not self._text:
            return
        tmp = self.create_text(0, -100, text=self._text, font=self._font, anchor="nw")
        x1, y1, x2, y2 = self.bbox(tmp)
        tw = x2 - x1
        self.delete(tmp)
        w = tw + 26
        self.configure(width=w)
        round_rect(self, 0, 1, w, h - 1, (h - 2) / 2, fill=bg, outline=bg)
        self.create_text(w / 2, h / 2, text=self._text, fill=fg, font=self._font)


# ---------------------------------------------------------------------------
# главное окно
# ---------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self, demo: bool = False):
        super().__init__()
        self.demo = demo

        cfg = load_settings()
        set_lang(cfg.get("lang") or "ru")

        self._apply_title()
        self.geometry("1200x820")
        self.minsize(1060, 720)
        self.configure(bg=C["bg"])

        self.queue: "queue.Queue" = queue.Queue()
        self.probe: EspProbe | None = None
        self.worker: threading.Thread | None = None
        self.cancel_flag = threading.Event()
        self.state = {"chip": None, "flash": None, "ram": None, "deep": None,
                      "erase": None, "bin": None}
        self.kv: dict[str, tk.Label] = {}
        self._busy = False
        self._bin_path = None
        self._ports: dict[str, str] = {}
        self._port_info: dict[str, dict] = {}
        self._port_items: list[str] = []
        self._pinned_device = None
        self._reconnect_tried = None
        self._manual_disconnect = False
        self._connected_port_info = None
        self._io_lock = threading.Lock()
        self._liveness_running = False
        self._tick = 0
        self._usb_hint = ""
        self._tab = "chip"
        self._log_lines: list[tuple] = []
        self._status = ("не подключено", C["muted"])
        self._connected = False
        self._closing = False

        self._init_style()
        self._build()
        self._refresh_ports()
        self._set_tab("chip")
        self._set_busy(False)
        self.after(80, self._poll)
        self.after(2000, self._auto_ports)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        if demo:
            self.after(120, self._load_demo)
        else:
            self._log("Готов к работе. Плата ищется автоматически: подключите её по USB.", "info")

    # ------------------------------------------------------------------
    # язык интерфейса
    # ------------------------------------------------------------------
    def _apply_title(self):
        self.title(f"{APP_NAME} {__version__} — "
                   + tr("реальный объём Flash и RAM у ESP32"))

    def _mark_lang(self):
        """Подсветить активный язык в переключателе."""
        for code, lbl in getattr(self, "lang_lbls", {}).items():
            active = code == get_lang()
            lbl.configure(fg=C["accent"] if active else "#4a5a68",
                          font=("Segoe UI", 8, "bold" if active else "normal"))

    def _switch_lang(self, code):
        if code == get_lang() or self._busy:
            return
        set_lang(code)
        cfg = load_settings()
        cfg["lang"] = code
        save_settings(cfg)
        self._rebuild()

    def _rebuild(self):
        """Пересобрать окно на другом языке, сохранив всё состояние."""
        snap = self._snapshot()
        for child in self.winfo_children():
            child.destroy()
        self.kv.clear()
        self._build()
        self._apply_title()
        self._restore(snap)

    def _snapshot(self) -> dict:
        return {
            "tab": self._tab,
            "log": list(self._log_lines),
            "baud": self.baud_var.get(),
            "auto": bool(self.auto_port_var.get()),
            "autoconn": bool(self.auto_connect_var.get()),
            "verify": bool(self.verify_var.get()),
            "reset": bool(self.reset_after_var.get()),
            "backup": bool(self.backup_var.get()),
            "offset": self.offset_var.get(),
            "port_label": self.port_var.get(),
            "pinned": self._pinned_device,
            "items": list(self._port_items),
            "bin_path": self._bin_path,
            "status": self._status,
            "usb_hint": self._usb_hint,
        }

    def _restore(self, s: dict):
        self.baud_var.set(s["baud"])
        self.auto_connect_var.set(s["autoconn"])
        self.verify_var.set(s["verify"])
        self.reset_after_var.set(s["reset"])
        self.backup_var.set(s["backup"])
        self.offset_var.set(s["offset"])

        self._usb_hint = s["usb_hint"]
        self._set_port_mode(s["auto"])
        self._pinned_device = s["pinned"]
        # подписи портов зависят от языка — пересобираем их заново
        items = [self._port_text(p) for p in self._port_info.values()]
        self._port_items = items
        self._ports = {self._port_text(p): p["device"] for p in self._port_info.values()}
        self.port_box["values"] = items
        self._fill_port_list(items)
        self.port_var.set(tr(s["port_label"]))
        self._sync_port_list()
        self._update_port_detail()

        # данные на вкладках
        if self.state.get("chip"):
            self._render_chip(self.state["chip"])
        if self.state.get("erase"):
            self._render_erase(self.state["erase"])
        elif self.state.get("flash"):
            self._render_flash(self.state["flash"])
        if self.state.get("ram"):
            self._render_ram(self.state["ram"])
        if self.state.get("deep"):
            self._render_deep(self.state["deep"])

        # журнал
        self._log_lines = []
        for msg, level in s["log"]:
            self._log_append(msg, level)

        # отчёт
        if any(v for v in self.state.values()):
            self._report_set(self._build_report())
        else:
            self._report_set("Отчёт появится после проверки.")

        # состояние подключения
        connected = self._connected
        self.status_dot.itemconfigure(self._dot, fill=C["ok"] if connected else "#3b4a58")
        self._set_status(s["status"][0], s["status"][1])
        self.btn_connect.set_text(tr("Отключиться") if connected else tr("Подключиться"))

        if self._bin_path:
            try:
                size = os.path.getsize(self._bin_path)
            except OSError:
                size = 0
            self.bin_lbl.configure(
                text=tr(f"{os.path.basename(self._bin_path)}\n{chipdb.human_size(size)}"),
                fg=C["text"])

        self._set_busy(self._busy)
        self._set_tab(s["tab"])

    # ------------------------------------------------------------------
    # стили
    # ------------------------------------------------------------------
    def _init_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "Dark.TCombobox",
            fieldbackground=C["panel2"], background=C["panel2"],
            foreground=C["text"], arrowcolor=C["muted"],
            bordercolor=C["border"], lightcolor=C["panel2"], darkcolor=C["panel2"],
            selectbackground=C["panel2"], selectforeground=C["text"], padding=4,
        )
        style.map(
            "Dark.TCombobox",
            fieldbackground=[("readonly", C["panel2"])],
            foreground=[("readonly", C["text"])],
            bordercolor=[("focus", C["accent_dark"])],
        )
        style.configure(
            "Dark.Vertical.TScrollbar",
            background="#2c3b49", troughcolor=C["bg"],
            bordercolor=C["bg"], arrowcolor=C["muted"], gripcount=0, arrowsize=10,
        )
        self.option_add("*TCombobox*Listbox.background", C["panel2"])
        self.option_add("*TCombobox*Listbox.foreground", C["text"])
        self.option_add("*TCombobox*Listbox.selectBackground", C["accent_dark"])
        self.option_add("*TCombobox*Listbox.font", "Segoe UI 9")

    # ------------------------------------------------------------------
    # построение интерфейса
    # ------------------------------------------------------------------
    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()

        body = tk.Frame(self, bg=C["bg"])
        body.grid(row=1, column=0, sticky="nsew", padx=14, pady=(4, 0))
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        self._build_sidebar(body)
        self._build_main(body)

        self._build_footer()
        tr_tree(self)
        self._mark_lang()

    # -- шапка ---------------------------------------------------------
    def _build_header(self):
        head = tk.Frame(self, bg=C["bg"])
        head.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 6))
        head.grid_columnconfigure(2, weight=1)

        logo = tk.Canvas(head, width=26, height=26, bg=C["bg"], highlightthickness=0)
        logo.grid(row=0, column=0, sticky="w")
        round_rect(logo, 1, 1, 25, 25, 7, fill=C["accent_dark"], outline="")
        for i in range(3):
            for j in range(3):
                logo.create_rectangle(7 + i * 5, 7 + j * 5, 10 + i * 5, 10 + j * 5,
                                      fill=C["accent"], outline="")

        brand = tk.Frame(head, bg=C["bg"])
        brand.grid(row=0, column=1, sticky="w", padx=(9, 0))
        tk.Label(brand, text=APP_NAME, bg=C["bg"], fg=C["text"],
                 font=("Segoe UI", 12, "bold")).pack(side="left")
        tk.Label(brand, text=f"v{__version__}", bg=C["bg"], fg="#4a5a68",
                 font=F_TINY).pack(side="left", padx=(6, 0), pady=(3, 0))

        # переключатель языка: RU | EN
        self.lang_lbls = {}
        lang_box = tk.Frame(brand, bg=C["bg"])
        lang_box.pack(side="left", padx=(12, 0), pady=(3, 0))
        for i, (code, name) in enumerate((("ru", "RU"), ("en", "EN"))):
            if i:
                tk.Label(lang_box, text="|", bg=C["bg"], fg="#2b3945",
                         font=("Segoe UI", 8)).pack(side="left", padx=3)
            lbl = tk.Label(lang_box, text=name, bg=C["bg"], fg="#4a5a68",
                           font=("Segoe UI", 8), cursor="hand2")
            lbl.pack(side="left")
            lbl.bind("<Button-1>", lambda e, c=code: self._switch_lang(c))
            self.lang_lbls[code] = lbl

        right = tk.Frame(head, bg=C["bg"])
        right.grid(row=0, column=3, sticky="e")

        self.port_mode_lbl = tk.Label(right, text="ПОРТ · АВТО", bg=C["bg"], fg=C["muted"],
                                      font=F_TINY)
        self.port_mode_lbl.grid(row=0, column=0, padx=(0, 6))
        self.port_var = tk.StringVar()
        self.port_box = ttk.Combobox(right, textvariable=self.port_var, width=30,
                                     style="Dark.TCombobox", state="readonly")
        self.port_box.grid(row=0, column=1, padx=(0, 6))
        self.port_box.bind("<<ComboboxSelected>>", self._on_port_selected)

        self.btn_refresh = RButton(right, "⟳", command=self._refresh_ports,
                                   kind="ghost", width=40, height=30, parent_bg=C["bg"])
        self.btn_refresh.grid(row=0, column=2, padx=(0, 8))

        self.btn_connect = RButton(right, "Подключиться", command=self._toggle_connect,
                                   kind="primary", width=150, height=30, parent_bg=C["bg"])
        self.btn_connect.grid(row=0, column=3, padx=(0, 12))

        self.status_dot = tk.Canvas(right, width=12, height=12, bg=C["bg"], highlightthickness=0)
        self.status_dot.grid(row=0, column=4)
        self._dot = self.status_dot.create_oval(2, 2, 10, 10, fill="#3b4a58", outline="")
        self.status_lbl = tk.Label(right, text="не подключено", bg=C["bg"], fg=C["muted"],
                                   font=F_TINY)
        self.status_lbl.grid(row=0, column=5, padx=(6, 0))

    # -- боковая панель ------------------------------------------------
    def _build_sidebar(self, parent):
        outer = tk.Frame(parent, bg=C["bg"], width=302)
        outer.grid(row=0, column=0, sticky="nsw", padx=(0, 14))
        outer.grid_propagate(False)
        outer.grid_rowconfigure(0, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        canvas = tk.Canvas(outer, bg=C["bg"], highlightthickness=0, bd=0, width=286)
        sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview,
                           style="Dark.Vertical.TScrollbar")
        canvas.configure(yscrollcommand=sb.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")

        side = tk.Frame(canvas, bg=C["bg"])
        win = canvas.create_window((0, 0), window=side, anchor="nw")
        side.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win, width=e.width))

        def on_wheel(event):
            try:
                canvas.yview_scroll(int(-event.delta / 120), "units")
            except Exception:
                pass

        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", on_wheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        # --- действия ---
        card = self._card(side, "Проверка")
        self.btn_full = RButton(card, "▶  Полная проверка", command=lambda: self._start("full"),
                                kind="primary", height=40)
        self.btn_full.pack(fill="x", pady=(0, 8))
        row = tk.Frame(card, bg=C["panel"])
        row.pack(fill="x", pady=(0, 8))
        self.btn_flash = RButton(row, "Только Flash", command=lambda: self._start("flash"),
                                 kind="ghost", height=34)
        self.btn_flash.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.btn_ram = RButton(row, "Только ОЗУ", command=lambda: self._start("ram"),
                               kind="ghost", height=34)
        self.btn_ram.pack(side="left", fill="x", expand=True, padx=(4, 0))
        self.btn_stop = RButton(card, "■  Прервать", command=self._cancel, kind="danger", height=32)
        self.btn_stop.pack(fill="x")

        # --- скорость ---
        card = self._card(side, "Соединение")
        line = tk.Frame(card, bg=C["panel"])
        line.pack(fill="x")
        tk.Label(line, text="Скорость", bg=C["panel"], fg=C["muted"], font=F_BODY).pack(side="left")
        self.baud_var = tk.StringVar(value="921600")
        baud = ttk.Combobox(line, textvariable=self.baud_var, width=10, style="Dark.TCombobox",
                            state="readonly", values=["115200", "230400", "460800", "921600", "1500000"])
        baud.pack(side="right")
        self.auto_port_var = tk.BooleanVar(value=True)
        self._check(card, "Искать плату на всех портах", self.auto_port_var,
                    command=self._on_auto_toggle).pack(fill="x", pady=(8, 0))
        self.auto_connect_var = tk.BooleanVar(value=True)
        self._check(card, "Подключаться автоматически", self.auto_connect_var).pack(fill="x", pady=(2, 0))

        tk.Label(card, text="Порты — нажмите, чтобы выбрать:",
                 bg=C["panel"], fg=C["muted"], font=F_TINY, anchor="w").pack(fill="x", pady=(9, 3))
        holder = tk.Frame(card, bg=C["panel"])
        holder.pack(fill="x")
        self.port_list = tk.Listbox(
            holder, height=3, bg=C["panel2"], fg=C["text"], font=F_BODY,
            selectbackground=C["accent_dark"], selectforeground="#ffffff",
            highlightthickness=0, bd=0, activestyle="none", exportselection=False,
            relief="flat", selectborderwidth=0)
        self.port_list.pack(side="left", fill="both", expand=True)
        lsb = ttk.Scrollbar(holder, orient="vertical", command=self.port_list.yview,
                            style="Dark.Vertical.TScrollbar")
        self.port_list.configure(yscrollcommand=lsb.set)
        lsb.pack(side="right", fill="y")
        self.port_list.bind("<<ListboxSelect>>", self._on_list_select)

        self.port_detail = tk.Label(card, text="", bg=C["panel"], fg=C["muted"], font=F_TINY,
                                    wraplength=246, justify="left", anchor="w")
        self.port_detail.pack(fill="x", pady=(6, 0))
        self.btn_reset = RButton(card, "Сбросить плату (RST)", command=self._reset_board,
                                 kind="ghost", height=30)
        self.btn_reset.pack(fill="x", pady=(8, 0))

        # --- прошивка .bin ---
        card = self._card(side, "Прошить .bin")
        self.bin_lbl = tk.Label(card, text="файл не выбран", bg=C["panel"], fg=C["muted"],
                                font=F_TINY, wraplength=246, justify="left", anchor="w")
        self.bin_lbl.pack(fill="x")
        self.btn_pick = RButton(card, "Выбрать файл…", command=self._pick_bin,
                                kind="ghost", height=30)
        self.btn_pick.pack(fill="x", pady=(6, 0))
        row = tk.Frame(card, bg=C["panel"])
        row.pack(fill="x", pady=(7, 0))
        tk.Label(row, text="Адрес", bg=C["panel"], fg=C["muted"], font=F_BODY).pack(side="left")
        self.offset_var = tk.StringVar(value="0x0")
        self.offset_entry = tk.Entry(row, textvariable=self.offset_var, width=9, bg=C["panel2"],
                                     fg=C["text"], insertbackground=C["text"], font=F_MONO,
                                     bd=0, highlightthickness=1, highlightbackground=C["border"],
                                     highlightcolor=C["accent"], justify="right")
        self.offset_entry.pack(side="right", ipady=3)
        self.verify_var = tk.BooleanVar(value=True)
        self.reset_after_var = tk.BooleanVar(value=True)
        flags = tk.Frame(card, bg=C["panel"])
        flags.pack(fill="x", pady=(7, 0))
        self._check(flags, "Проверять", self.verify_var).pack(side="left")
        self._check(flags, "Перезагрузить", self.reset_after_var).pack(side="left", padx=(10, 0))
        self.btn_write = RButton(card, "Прошить файл", command=self._start_write_bin,
                                 kind="blue", height=34)
        self.btn_write.pack(fill="x", pady=(7, 0))

        # --- стирание flash ---
        card = self._card(side, "Стереть прошивку")
        tk.Label(card, text=("Полностью очищает микросхему: загрузчик, таблицу разделов, NVS и "
                             "файловую систему. Плата перестанет запускать прошивку — "
                             "восстановить данные будет нельзя."),
                 bg=C["panel"], fg=C["muted"], font=F_TINY, wraplength=246,
                 justify="left").pack(anchor="w")
        self.btn_erase = RButton(card, "Стереть flash полностью", command=self._start_erase,
                                 kind="danger", height=34)
        self.btn_erase.pack(fill="x", pady=(8, 0))

        # --- глубокий тест ---
        card = self._card(side, "Глубокий тест Flash")
        tk.Label(card, text=("Стирает flash, пишет шаблон, сверяет чтением и восстанавливает "
                             "прошивку из копии."),
                 bg=C["panel"], fg=C["muted"], font=F_TINY, wraplength=246, justify="left").pack(anchor="w")
        self.backup_var = tk.BooleanVar(value=True)
        self._check(card, "Сохранять резервную копию", self.backup_var).pack(fill="x", pady=(8, 6))
        self.btn_deep = RButton(card, "Запустить глубокий тест", command=self._start_deep,
                                kind="ghost", height=34)
        self.btn_deep.pack(fill="x")

        tk.Label(side, text="esptool внутри · ничего доустанавливать не нужно",
                 bg=C["bg"], fg="#4a5a68", font=F_TINY).pack(anchor="w", pady=(4, 12))

    # -- правая часть ---------------------------------------------------
    def _build_main(self, parent):
        main = tk.Frame(parent, bg=C["bg"])
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)

        tabs = tk.Frame(main, bg=C["bg"])
        tabs.grid(row=0, column=0, sticky="ew")
        self.tab_btns = {}
        self.tab_marks = {}
        for key, title in (("chip", "Чип"), ("flash", "Flash"), ("ram", "ОЗУ"),
                           ("report", "Отчёт"), ("log", "Журнал")):
            holder = tk.Frame(tabs, bg=C["bg"])
            holder.pack(side="left", padx=(0, 4))
            lbl = tk.Label(holder, text=title, bg=C["bg"], fg=C["muted"], font=F_H2,
                           padx=14, pady=6, cursor="hand2")
            lbl.pack()
            mark = tk.Frame(holder, bg=C["bg"], height=2)
            mark.pack(fill="x")
            lbl.bind("<Button-1>", lambda e, k=key: self._set_tab(k))
            self.tab_btns[key] = lbl
            self.tab_marks[key] = mark

        self.pages = tk.Frame(main, bg=C["bg"])
        self.pages.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        self.pages.grid_rowconfigure(0, weight=1)
        self.pages.grid_columnconfigure(0, weight=1)

        self.page_chip = self._page_chip()
        self.page_flash = self._page_flash()
        self.page_ram = self._page_ram()
        self.page_report = self._page_report()
        self.page_log = self._page_log()

    def _new_page(self):
        frame = tk.Frame(self.pages, bg=C["bg"])
        frame.grid(row=0, column=0, sticky="nsew")
        return frame

    # -- вкладка «Чип» --------------------------------------------------
    def _page_chip(self):
        page = self._new_page()
        holder, inner = self._scrollable(page)

        card = self._card(inner, "Определённое устройство")
        card.grid_columnconfigure(3, weight=1)
        self._kv(card, "chip.name", "Модель", 0)
        self._kv(card, "chip.desc", "Маркировка", 1)
        self._kv(card, "chip.rev", "Ревизия", 2)
        self._kv(card, "chip.core", "Ядро", 0, col=1)
        self._kv(card, "chip.crystal", "Кварц", 1, col=1)
        self._kv(card, "chip.mac", "MAC", 2, col=1)
        self._kv(card, "chip.stub", "Загрузчик", 3, col=0)
        self._kv(card, "chip.port", "Порт", 4, col=0)
        self._kv(card, "chip.baud", "Скорость", 5, col=0)
        self._kv(card, "chip.features", "Особенности", 6, col=0)

        card = self._card(inner, "Возможности чипа")
        card.grid_columnconfigure(3, weight=1)
        self._kv(card, "cap.wifi", "Wi-Fi", 0)
        self._kv(card, "cap.bt", "Bluetooth", 1)
        self._kv(card, "cap.154", "IEEE 802.15.4", 2)
        self._kv(card, "cap.flash", "Встроенная flash", 0, col=1)
        self._kv(card, "cap.psram", "Встроенная PSRAM", 1, col=1)
        self._kv(card, "cap.cpu", "Процессор", 2, col=1)
        self.cap_note = tk.Label(
            card, text="", bg=C["panel"], fg=C["muted"], font=F_TINY,
            wraplength=760, justify="left", anchor="w")
        self.cap_note.grid(row=3, column=0, columnspan=4, sticky="w", pady=(8, 0))

        card = self._card(inner, "Безопасность и подлинность")
        card.grid_columnconfigure(3, weight=1)
        self._kv(card, "sec.oui", "MAC / производитель", 0)
        self._kv(card, "sec.boot", "Secure Boot", 1)
        self._kv(card, "sec.enc", "Шифрование flash", 2)
        self._kv(card, "sec.jtag", "JTAG", 0, col=1)
        self._kv(card, "sec.chipid", "Chip ID (eFuse)", 1, col=1)
        self._kv(card, "sec.usb", "USB в загрузчике", 2, col=1)

        card = self._card(inner, "Прошивка на плате")
        card.grid_columnconfigure(3, weight=1)
        self._kv(card, "app.project", "Проект", 0)
        self._kv(card, "app.version", "Версия", 1)
        self._kv(card, "app.idf", "ESP-IDF", 2)
        self._kv(card, "app.built", "Собрана", 0, col=1)
        self._kv(card, "app.chipid", "Chip ID образа", 1, col=1)

        card = self._card(inner, "Справка по памяти")
        card.grid_columnconfigure(1, weight=1)
        self._kv(card, "chip.sram", "Встроенная SRAM", 0)
        self._kv(card, "chip.psram", "Внешняя PSRAM", 1)
        self.note_lbl = tk.Label(card, text="—", bg=C["panel"], fg=C["muted"], font=F_TINY,
                                 wraplength=720, justify="left", anchor="w")
        self.note_lbl.grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))
        return page

    # -- вкладка «Flash» ------------------------------------------------
    def _page_flash(self):
        page = self._new_page()
        holder, inner = self._scrollable(page)

        # карточка с главной цифрой
        card = self._card(inner, "Реальный объём Flash")
        top = tk.Frame(card, bg=C["panel"])
        top.pack(fill="x")
        self.flash_big = tk.Label(top, text="—", bg=C["panel"], fg=C["text"], font=F_BIG)
        self.flash_big.pack(side="left")
        self.flash_badge = Badge(top, "", "muted")
        self.flash_badge.pack(side="right", pady=(10, 0))
        self.flash_sub = tk.Label(card, text="нет данных", bg=C["panel"], fg=C["muted"], font=F_BODY)
        self.flash_sub.pack(anchor="w", pady=(2, 10))
        self.flash_bar = Bar(card, height=12)
        self.flash_bar.pack(fill="x")
        self.flash_cmp = tk.Label(card, text="", bg=C["panel"], fg=C["muted"], font=F_TINY)
        self.flash_cmp.pack(anchor="w", pady=(6, 0))
        self.flash_verdict = tk.Label(card, text="", bg=C["panel"], fg=C["muted"], font=F_BODY,
                                      wraplength=760, justify="left", anchor="w")
        self.flash_verdict.pack(anchor="w", pady=(8, 0))

        # идентификация
        card = self._card(inner, "Идентификация чипа Flash")
        card.grid_columnconfigure(3, weight=1)
        self._kv(card, "fl.jedec", "JEDEC ID", 0)
        self._kv(card, "fl.mfg", "Производитель", 1)
        self._kv(card, "fl.cap", "Код ёмкости", 2)
        self._kv(card, "fl.size_id", "Объём по ID", 0, col=1)
        self._kv(card, "fl.size_det", "Автоопределение", 1, col=1)
        self._kv(card, "fl.speed", "Скорость чтения", 2, col=1)

        # заявлено прошивкой
        card = self._card(inner, "Что заявлено в прошивке")
        card.grid_columnconfigure(3, weight=1)
        self._kv(card, "fl.hdr", "Заголовок образа", 0)
        self._kv(card, "fl.declared", "Заявленный объём", 1)
        self._kv(card, "fl.chipid", "Chip ID в образе", 2)
        self._kv(card, "fl.part_total", "Суммарно разделов", 0, col=1)
        self._kv(card, "fl.part_end", "Конец последнего", 1, col=1)
        self._kv(card, "fl.pt_addr", "Таблица разделов", 2, col=1)

        # разделы
        card = self._card(inner, "Таблица разделов")
        self.part_frame = tk.Frame(card, bg=C["panel"])
        self.part_frame.pack(fill="x")
        tk.Label(self.part_frame, text="—", bg=C["panel"], fg=C["muted"], font=F_BODY).pack(anchor="w")

        # глубокий тест
        card = self._card(inner, "Результат глубокого теста")
        self.deep_lbl = tk.Label(card, text="не выполнялся", bg=C["panel"], fg=C["muted"],
                                 font=F_BODY, wraplength=760, justify="left", anchor="w")
        self.deep_lbl.pack(anchor="w")
        return page

    # -- вкладка «ОЗУ» --------------------------------------------------
    def _page_ram(self):
        page = self._new_page()
        holder, inner = self._scrollable(page)

        card = self._card(inner, "Встроенная SRAM")
        top = tk.Frame(card, bg=C["panel"])
        top.pack(fill="x")
        self.ram_big = tk.Label(top, text="—", bg=C["panel"], fg=C["text"], font=F_BIG)
        self.ram_big.pack(side="left")
        self.ram_badge = Badge(top, "", "muted")
        self.ram_badge.pack(side="right", pady=(10, 0))
        self.ram_sub = tk.Label(card, text="объём определяется моделью чипа",
                                bg=C["panel"], fg=C["muted"], font=F_BODY)
        self.ram_sub.pack(anchor="w", pady=(2, 0))

        card = self._card(inner, "Тест записи/чтения SRAM")
        card.grid_columnconfigure(3, weight=1)
        self._kv(card, "ram.base", "Область теста", 0)
        self._kv(card, "ram.cells", "Проверено ячеек", 1)
        self._kv(card, "ram.data", "Шина данных", 0, col=1)
        self._kv(card, "ram.addr", "Шина адреса", 1, col=1)
        self.ram_err = tk.Label(card, text="", bg=C["panel"], fg=C["err"], font=F_TINY,
                                wraplength=760, justify="left", anchor="w")
        self.ram_err.grid(row=2, column=0, columnspan=4, sticky="w", pady=(6, 0))

        card = self._card(inner, "Внешняя PSRAM")
        self.ram_psram = tk.Label(card, text="—", bg=C["panel"], fg=C["text"], font=F_BOLD,
                                  wraplength=760, justify="left", anchor="w")
        self.ram_psram.pack(anchor="w")
        self.ram_psram_note = tk.Label(
            card, text=(
                "PSRAM нельзя измерить через ROM-загрузчик: она не инициализирована до запуска "
                "прошивки. Точный объём PSRAM показывает сама прошивка (esp_psram_get_size) или "
                "команда esptool flash_id по встроенному в модуль чипу."),
            bg=C["panel"], fg=C["muted"], font=F_TINY, wraplength=760, justify="left", anchor="w")
        self.ram_psram_note.pack(anchor="w", pady=(8, 0))
        return page

    # -- вкладка «Отчёт» ------------------------------------------------
    def _page_report(self):
        page = self._new_page()
        bar = tk.Frame(page, bg=C["bg"])
        bar.pack(fill="x", pady=(0, 6))
        self.btn_save = RButton(bar, "Сохранить отчёт в файл", command=self._save_report,
                                kind="ghost", height=30, width=200, parent_bg=C["bg"])
        self.btn_save.pack(side="right")
        tk.Label(bar, text="Отчёт обновляется после каждой проверки", bg=C["bg"], fg=C["muted"],
                 font=F_TINY).pack(side="left", pady=(6, 0))
        card = tk.Frame(page, bg=C["panel"], highlightbackground=C["border"], highlightthickness=1)
        card.pack(fill="both", expand=True)
        self.report_text = tk.Text(card, bg=C["panel"], fg=C["text"], bd=0, highlightthickness=0,
                                   font=F_MONO, wrap="none", insertbackground=C["text"],
                                   padx=14, pady=12, tabs=(250, 360, 470, 580))
        self.report_text.pack(fill="both", expand=True, side="left")
        sb = ttk.Scrollbar(card, orient="vertical", command=self.report_text.yview,
                           style="Dark.Vertical.TScrollbar")
        sb.pack(side="right", fill="y")
        self.report_text.configure(yscrollcommand=sb.set)
        self._report_set("Отчёт появится после проверки.")
        return page

    # -- вкладка «Журнал» -----------------------------------------------
    def _page_log(self):
        page = self._new_page()
        card = tk.Frame(page, bg=C["panel"], highlightbackground=C["border"], highlightthickness=1)
        card.pack(fill="both", expand=True)
        self.log_text = tk.Text(card, bg=C["panel"], fg=C["text"], bd=0, highlightthickness=0,
                                font=F_MONO, wrap="word", insertbackground=C["text"],
                                padx=14, pady=12, state="disabled")
        self.log_text.pack(fill="both", expand=True, side="left")
        sb = ttk.Scrollbar(card, orient="vertical", command=self.log_text.yview,
                           style="Dark.Vertical.TScrollbar")
        sb.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=sb.set)
        self.log_text.tag_config("ok", foreground=C["ok"])
        self.log_text.tag_config("warn", foreground=C["warn"])
        self.log_text.tag_config("err", foreground=C["err"])
        self.log_text.tag_config("time", foreground="#4a5a68")
        return page

    # -- подвал ---------------------------------------------------------
    def _build_footer(self):
        foot = tk.Frame(self, bg=C["bg"])
        foot.grid(row=2, column=0, sticky="ew", padx=14, pady=(8, 12))
        foot.grid_columnconfigure(0, weight=1)
        self.progress = Bar(foot, height=8, parent_bg=C["bg"])
        self.progress.grid(row=0, column=0, sticky="ew")
        self.progress_lbl = tk.Label(foot, text="", bg=C["bg"], fg=C["muted"], font=F_TINY)
        self.progress_lbl.grid(row=1, column=0, sticky="w", pady=(5, 0))

    # ------------------------------------------------------------------
    # вспомогательные конструкторы
    # ------------------------------------------------------------------
    def _card(self, parent, title=None):
        outer = tk.Frame(parent, bg=C["panel"], highlightbackground=C["border"],
                         highlightthickness=1)
        outer.pack(fill="x", pady=(0, 8))
        if title:
            tk.Label(outer, text=title.upper(), bg=C["panel"], fg=C["muted"],
                     font=F_TINY).pack(anchor="w", padx=14, pady=(9, 0))
        body = tk.Frame(outer, bg=C["panel"])
        body.pack(fill="x", padx=14, pady=(6, 11))
        return body

    def _kv(self, parent, key, label, row, col=0, value="—"):
        tk.Label(parent, text=label, bg=C["panel"], fg=C["muted"], font=F_BODY).grid(
            row=row, column=col * 2, sticky="w", pady=3, padx=(0, 12))
        val = tk.Label(parent, text=value, bg=C["panel"], fg=C["text"], font=F_BOLD,
                       anchor="w", justify="left")
        val.grid(row=row, column=col * 2 + 1, sticky="w", pady=3, padx=(0, 34))
        if key:
            self.kv[key] = val
        return val

    def _check(self, parent, text, var, command=None):
        cb = tk.Checkbutton(parent, text=text, variable=var, bg=C["panel"], fg=C["text"],
                            activebackground=C["panel"], activeforeground=C["text"],
                            selectcolor=C["panel2"], font=F_BODY, bd=0,
                            highlightthickness=0, anchor="w", cursor="hand2",
                            command=command)
        return cb

    def _center_dialog(self, dlg):
        """Задать диалогу размер по содержимому, запретить растягивание и отцентровать."""
        dlg.update_idletasks()
        w, h = dlg.winfo_reqwidth(), dlg.winfo_reqheight()
        x = self.winfo_rootx() + max(0, (self.winfo_width() - w) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - h) // 3)
        dlg.geometry(f"{w}x{h}+{x}+{y}")
        dlg.resizable(False, False)
        dlg.update_idletasks()

    def _scrollable(self, parent):
        canvas = tk.Canvas(parent, bg=C["bg"], highlightthickness=0, bd=0)
        sb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview,
                           style="Dark.Vertical.TScrollbar")
        inner = tk.Frame(canvas, bg=C["bg"])
        win = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win, width=e.width))

        def on_wheel(event):
            try:
                canvas.yview_scroll(int(-event.delta / 120), "units")
            except Exception:
                pass

        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", on_wheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        tk.Frame(inner, bg=C["bg"], height=8).pack()
        return canvas, inner

    # ------------------------------------------------------------------
    # вкладки
    # ------------------------------------------------------------------
    def _set_tab(self, key):
        self._tab = key
        pages = {
            "chip": self.page_chip, "flash": self.page_flash, "ram": self.page_ram,
            "report": self.page_report, "log": self.page_log,
        }
        for k, page in pages.items():
            if k == key:
                page.tkraise()
            lbl = self.tab_btns[k]
            lbl.configure(fg=C["text"] if k == key else C["muted"])
            self.tab_marks[k].configure(bg=C["accent"] if k == key else C["bg"])

    # ------------------------------------------------------------------
    # порты
    # ------------------------------------------------------------------
    def _refresh_ports(self, quiet=False, ports=None):
        if ports is None:
            try:
                ports = list_serial_ports()
            except Exception as exc:  # noqa: BLE001
                self._log(f"Не удалось получить список портов: {exc}", "err")
                return

        items = [self._port_text(p) for p in ports]
        self._ports = {self._port_text(p): p["device"] for p in ports}
        self._port_info = {self._port_text(p): p for p in ports}
        prev = getattr(self, "_port_items", [])
        changed = items != prev
        self._port_items = items

        if changed:
            self.port_box["values"] = items
            self._fill_port_list(items)
            if not self.auto_port_var.get() and self._pinned_device:
                # ручной режим: подпись выбранного порта могла измениться — обновляем,
                # а если порт пропал, оставляем выбор как есть и ждём его возвращения
                match = next((p for p in ports if p["device"] == self._pinned_device), None)
                if match:
                    self.port_var.set(match["label"])
            else:
                current = self.port_var.get()
                if current not in items:
                    best = next((p for p in ports if p["priority"] <= 1), None)
                    self.port_var.set(best["label"] if best else (items[0] if items else ""))
            added = [i for i in items if i not in prev]
            removed = [i for i in prev if i not in items]
            for label in added:
                self._log(f"Найден порт: {label}", "ok")
            if added:
                # новая плата — снимаем «ручное отключение» и пробуем снова
                self._manual_disconnect = False
                self._reconnect_tried = None
            for label in removed:
                self._log(f"Порт пропал: {label}", "warn")
            if not items:
                self._usb_hint = self._usb_diagnosis()
                self._log(self._usb_hint, "warn")
            else:
                self._usb_hint = ""
        elif not quiet:
            self._log(f"Портов: {len(items)}" + (f" ({', '.join(items)})" if items else ""))
        self._sync_port_list()
        self._update_port_detail()

    @staticmethod
    def _port_text(p) -> str:
        """Подпись порта для показа (описание Windows переводим)."""
        return tr(p.get("label") or p.get("device") or "")

    # -- список портов в боковой панели ---------------------------------
    def _fill_port_list(self, items):
        if not hasattr(self, "port_list"):
            return
        self.port_list.delete(0, "end")
        for label in items:
            self.port_list.insert("end", label)

    def _sync_port_list(self):
        """Подсветить в списке тот порт, который выбран (в авто-режиме — ничего)."""
        if not hasattr(self, "port_list"):
            return
        self.port_list.selection_clear(0, "end")
        if self.auto_port_var.get():
            return
        label = self.port_var.get()
        if not label:
            return
        try:
            idx = list(self.port_list.get(0, "end")).index(label)
        except ValueError:
            return
        self.port_list.selection_set(idx)
        self.port_list.see(idx)

    def _on_list_select(self, _event=None):
        if not hasattr(self, "port_list"):
            return
        sel = self.port_list.curselection()
        if not sel:
            return
        label = self.port_list.get(sel[0])
        if not self.auto_port_var.get() and label == self.port_var.get():
            return
        self.port_var.set(label)
        self._on_port_selected()

    # -- автопоиск: слежение за портами и автоподключение -----------------
    def _auto_ports(self):
        """Каждые 1.5 с: проверяем, не отключилась ли плата, и ищем новую."""
        if self._closing:
            return
        try:
            self._tick += 1
            ports = list_serial_ports()
            self._detect_unplug(ports)
            if not self._busy:
                self._refresh_ports(quiet=True, ports=ports)
                self._auto_connect(ports)
                if self._tick % 5 == 0:
                    self._liveness_check()
        except Exception:  # noqa: BLE001
            pass
        self.after(1500, self._auto_ports)

    def _liveness_check(self):
        """Раз в ~7 с проверяем, отвечает ли чип (ловит замену платы на том же COM)."""
        if self._busy or self._liveness_running:
            return
        probe = self.probe
        if not (probe and probe.connected):
            return
        addr = getattr(probe.esp, "CHIP_DETECT_MAGIC_REG_ADDR", 0x40001000)
        self._liveness_running = True

        def work():
            ok = False
            try:
                with self._io_lock:
                    probe.esp.read_reg(addr)
                ok = True
            except Exception:  # noqa: BLE001
                ok = False
            finally:
                self._liveness_running = False
            self.queue.put(("liveness", ok))

        threading.Thread(target=work, daemon=True).start()

    def _detect_unplug(self, ports):
        """Плату выдернули (или заменили на другую) — закрываем сессию и ждём новую."""
        if self._busy or not (self.probe and self.probe.connected):
            return
        device = self.probe.port
        if not device:
            return
        current = next((p for p in ports if p["device"] == device), None)
        replaced = False
        if current is None:
            reason = f"Плата на {device} отключена. Жду подключения…"
        else:
            snap = self._connected_port_info or {}
            if (snap.get("vid"), snap.get("pid")) not in ((None, None), (current["vid"], current["pid"])):
                replaced = True
                reason = f"На {device} подключена другая плата — переподключаюсь…"
            else:
                return
        self._log(reason, "warn")
        try:
            self.probe.close()
        except Exception:  # noqa: BLE001
            pass
        self.probe = None
        self._connected_port_info = None
        self._reconnect_tried = None
        self._on_connected(False)
        self._set_status("плата отключена", C["warn"])
        if replaced:
            self._refresh_ports(quiet=True, ports=ports)

    def _auto_connect(self, ports):
        """Появилась плата и мы не подключены — подключаемся сами."""
        if self._busy or (self.probe and self.probe.connected):
            return
        if self._manual_disconnect or not self.auto_connect_var.get():
            return
        if self.auto_port_var.get():
            candidates = [p for p in ports if p["priority"] <= 1]
            if not candidates:
                return
            device = candidates[0]["device"]
        else:
            device = self._pinned_device
            if not device:
                return
            # ждём именно выбранный порт: чужие платы не трогаем
            if not any(p["device"] == device for p in ports):
                return
        if device == getattr(self, "_reconnect_tried", None):
            return
        self._reconnect_tried = device
        self._log(f"Плата на {device} — подключаюсь автоматически…", "ok")
        self._start("connect")

    def _usb_diagnosis(self) -> str:
        """Почему нет COM-портов: платы нет на USB или нет драйвера."""
        try:
            usb = usb_esp_devices()
        except Exception:  # noqa: BLE001
            usb = []
        if usb:
            dev = usb[0]
            service = dev.get("service") or "не назначена"
            return (f"USB-устройство {dev['vid']:04X}:{dev['pid']:04X} воткнуто, но COM-порт "
                    f"не создан — похоже, нет драйвера USB-UART (служба: {service}). "
                    f"Поставьте драйвер CP210x / CH340 и нажмите ⟳.")
        return ("USB-устройств Espressif / USB-UART в системе нет: проверьте кабель "
                "(нужен data-кабель, не «только зарядка»), другой USB-порт и питание платы.")

    def _update_port_detail(self):
        if not hasattr(self, "port_detail"):
            return
        items = getattr(self, "_port_items", [])
        if not items:
            text = getattr(self, "_usb_hint", "") or "COM-портов нет — проверьте кабель и драйвер"
            color = C["err"]
        elif self.auto_port_var.get():
            text = f"авто: перебор {len(items)} порт(ов), плата ищется сама"
            color = C["accent"]
        else:
            info = self._find_port_info(self._pinned_device)
            if info:
                text = f"выбран {info['device']} · {info['desc']}"
                color = C["accent"]
            elif self._pinned_device:
                text = f"{self._pinned_device} — сейчас не подключён, жду его"
                color = C["warn"]
            else:
                text = "порт не выбран — нажмите строку в списке"
                color = C["warn"]
        self.port_detail.configure(text=tr(text), fg=color)

    def _set_port_mode(self, auto: bool):
        self.auto_port_var.set(bool(auto))
        if auto:
            self._pinned_device = None
            self.port_mode_lbl.configure(text=tr("ПОРТ · АВТО"), fg=C["muted"])
        else:
            self.port_mode_lbl.configure(text=tr("ПОРТ · ВРУЧНУЮ"), fg=C["accent"])

    def _on_auto_toggle(self):
        if self.auto_port_var.get():
            self._set_port_mode(True)
            self._reconnect_tried = None
            self._manual_disconnect = False
            best = next((p for p in self._port_info.values() if p["priority"] <= 1), None)
            if best:
                self.port_var.set(best["label"])
            self._log("Автопоиск включён: плата ищется на всех портах.", "info")
        else:
            # включили ручной режим — фиксируем текущий порт из списка
            if not self._ports.get(self.port_var.get()):
                self._set_port_mode(False)
                self._log("Ручной режим: выберите порт в списке ниже.", "warn")
                self._update_port_detail()
                return
            self._on_port_selected()
            return
        self._sync_port_list()
        self._update_port_detail()

    def _on_port_selected(self, _event=None):
        label = self.port_var.get()
        device = self._ports.get(label)
        if not device:
            self._update_port_detail()
            return
        first_time = self.auto_port_var.get() or device != self._pinned_device
        self._set_port_mode(False)
        self._pinned_device = device
        self._reconnect_tried = None
        self._manual_disconnect = False
        self._sync_port_list()
        self._update_port_detail()
        if first_time:
            self._log(f"Выбран порт {device}: автопоиск выключен, работаю только с ним.", "ok")
        if self._busy:
            return
        # если уже сидим на другом порте — переключаемся на выбранный
        if self.probe and self.probe.connected and self.probe.port != device:
            self._log(f"Переключаюсь с {self.probe.port} на {device}…", "warn")
            try:
                self.probe.close()
            except Exception:  # noqa: BLE001
                pass
            self.probe = None
            self._connected_port_info = None
            self._on_connected(False)
            self._start("connect")

    def _on_liveness(self, ok: bool):
        if ok or self._busy or not (self.probe and self.probe.connected):
            return
        self._log("Связь с платой потеряна (плата заменена или перезагружена).", "warn")
        try:
            self.probe.close()
        except Exception:  # noqa: BLE001
            pass
        self.probe = None
        self._connected_port_info = None
        self._reconnect_tried = None
        self._on_connected(False)
        self._set_status("связь потеряна", C["warn"])

    def _find_port_info(self, device):
        if not device:
            return None
        for p in self._port_info.values():
            if p["device"] == device:
                return dict(p)
        return None

    def _selected_port(self):
        if self.auto_port_var.get():
            return None
        return self._pinned_device or self._ports.get(self.port_var.get())

    def _selected_baud(self):
        try:
            return int(self.baud_var.get())
        except Exception:
            return 921600

    # ------------------------------------------------------------------
    # журнал / прогресс
    # ------------------------------------------------------------------
    def _log(self, msg, level="info"):
        if threading.current_thread() is not threading.main_thread():
            self.queue.put(("log", msg, level))
            return
        self._log_append(msg, level)

    def _log_append(self, msg, level="info"):
        if not hasattr(self, "log_text"):
            return
        msg = str(msg)
        self._log_lines.append((msg, level))
        if len(self._log_lines) > 1200:
            del self._log_lines[:200]
        self.log_text.configure(state="normal")
        self.log_text.insert("end", time.strftime("%H:%M:%S  "), "time")
        self.log_text.insert("end", tr_lines(msg) + "\n", level)
        lines = int(self.log_text.index("end-1c").split(".")[0])
        if lines > 1200:
            self.log_text.delete("1.0", f"{lines - 1000}.0")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _set_status(self, text, fg=None):
        """Текст состояния в шапке (храним по-русски, показываем переведённым)."""
        self._status = (text, fg if fg is not None else self._status[1])
        self.status_lbl.configure(text=tr(text), fg=self._status[1])

    def _qlog(self, msg, level="info"):
        self.queue.put(("log", msg, level))

    def _qprog(self, frac, text=""):
        self.queue.put(("progress", frac, text))

    def _poll(self):
        if self._closing:
            return
        try:
            while True:
                msg = self.queue.get_nowait()
                kind = msg[0]
                if kind == "log":
                    self._log_append(msg[1], msg[2])
                elif kind == "progress":
                    self.progress.set(msg[1])
                    self.progress_lbl.configure(text=f"{int(msg[1] * 100)}%   {tr(msg[2])}")
                elif kind == "chip":
                    self.state["chip"] = msg[1]
                    self._render_chip(msg[1])
                elif kind == "flash":
                    self.state["flash"] = msg[1]
                    self._render_flash(msg[1])
                elif kind == "ram":
                    self.state["ram"] = msg[1]
                    self._render_ram(msg[1])
                elif kind == "deep":
                    self.state["deep"] = msg[1]
                    self._render_deep(msg[1])
                elif kind == "erase":
                    self.state["erase"] = msg[1]
                    self._render_erase(msg[1])
                elif kind == "bin":
                    self.state["bin"] = msg[1]
                elif kind == "connected":
                    self._on_connected(msg[1])
                elif kind == "liveness":
                    self._on_liveness(msg[1])
                elif kind == "busy":
                    self._set_busy(msg[1])
                elif kind == "error":
                    self._set_busy(False)
                    self._log_append(msg[1], "err")
                    self._set_tab("log")
                    messagebox.showerror(tr("Ошибка"), tr_lines(msg[1]), parent=self)
                elif kind == "report":
                    self._report_set(msg[1])
        except queue.Empty:
            pass
        self.after(80, self._poll)

    # ------------------------------------------------------------------
    # запуск задач
    # ------------------------------------------------------------------
    def _toggle_connect(self):
        if self.probe and self.probe.connected:
            self._disconnect()
        else:
            self._manual_disconnect = False
            self._reconnect_tried = None
            self._start("connect")

    def _disconnect(self):
        if self.probe:
            self.probe.close()
        self.probe = None
        self._manual_disconnect = True
        self._on_connected(False)
        self._set_status("не подключено", C["muted"])
        self._log("Отключено. Автоподключение возобновится при появлении новой платы.", "info")

    def _start(self, kind):
        if self._busy:
            return
        # все Tk-переменные читаем в главном потоке и передаём в поток работы
        opts = {
            "port": self._selected_port(),
            "baud": self._selected_baud(),
            "backup": bool(self.backup_var.get()),
        }
        self.cancel_flag.clear()
        self._set_busy(True)
        self.progress.set(0)
        self.progress_lbl.configure(text="…")
        self.worker = threading.Thread(target=self._work, args=(kind, opts), daemon=True)
        self.worker.start()

    def _start_deep(self):
        if self._busy:
            return
        if not (self.probe and self.probe.connected):
            messagebox.showinfo("Нужно подключение",
                                "Сначала подключитесь к плате.", parent=self)
            return
        flash = self.state.get("flash")
        if not flash or not flash.get("size_real"):
            messagebox.showinfo("Нет данных",
                                "Сначала выполните проверку Flash — нужен объём чипа.", parent=self)
            return
        if not self._confirm_deep(flash):
            return
        opts = {"port": self._selected_port(), "baud": self._selected_baud(),
                "backup": bool(self.backup_var.get())}
        self.cancel_flag.clear()
        self._set_busy(True)
        self.worker = threading.Thread(target=self._work, args=("deep", opts), daemon=True)
        self.worker.start()

    def _confirm_deep(self, flash) -> bool:
        size = chipdb.human_size(flash["size_real"])
        minutes = max(1, int((flash["size_real"] / (1 << 20)) * 0.7))
        dlg = tk.Toplevel(self)
        dlg.title(tr("Подтверждение"))
        dlg.configure(bg=C["panel"])
        dlg.transient(self)
        dlg.grab_set()
        pad = 20
        tk.Label(dlg, text=tr("⚠  ВНИМАНИЕ: ОПЕРАЦИЯ РАЗРУШАЮЩАЯ"), bg=C["panel"], fg=C["warn"],
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=pad, pady=(pad, 6))
        txt = (f"Будет перезаписана вся flash ({size}): прошивка, NVS, файловая система.\n\n"
               "Перед началом программа снимет полную резервную копию и восстановит её "
               "после теста. Не отключайте плату во время работы!\n\n"
               f"Ожидаемое время: около {minutes} мин.\n\n"
               "Если восстановление прервётся, плату придётся прошивать заново.")
        tk.Label(dlg, text=tr(txt), bg=C["panel"], fg=C["text"], font=F_BODY, wraplength=470,
                 justify="left").pack(anchor="w", padx=pad, pady=(0, 14))
        btns = tk.Frame(dlg, bg=C["panel"])
        btns.pack(fill="x", padx=pad, pady=(0, pad))
        result = {"ok": False}

        def ok():
            result["ok"] = True
            dlg.destroy()

        RButton(btns, tr("Отмена"), command=dlg.destroy, kind="ghost", height=34,
                width=130, parent_bg=C["panel"]).pack(side="right", padx=(8, 0))
        RButton(btns, tr("Стирать и тестировать"), command=ok, kind="danger", height=34,
                width=210, parent_bg=C["panel"]).pack(side="right")
        self._center_dialog(dlg)
        self.wait_window(dlg)
        return result["ok"]

    # ------------------------------------------------------------------
    # прошивка произвольного .bin
    # ------------------------------------------------------------------
    def _pick_bin(self):
        path = filedialog.askopenfilename(
            parent=self, title=tr("Выберите файл прошивки"),
            filetypes=[(tr("Образ прошивки"), "*.bin"), (tr("Все файлы"), "*.*")])
        if not path:
            return
        self._bin_path = path
        try:
            size = os.path.getsize(path)
        except OSError:
            size = 0
        self.bin_lbl.configure(text=tr(f"{os.path.basename(path)}\n{chipdb.human_size(size)}"),
                               fg=C["text"])
        self._log(f"Выбран файл: {path} ({chipdb.human_size(size)})", "info")

    def _start_write_bin(self):
        if self._busy:
            return
        if not (self.probe and self.probe.connected):
            messagebox.showinfo(tr("Нужно подключение"), tr("Сначала подключитесь к плате."),
                                parent=self)
            return
        path = self._bin_path
        if not path or not os.path.isfile(path):
            messagebox.showinfo(tr("Файл не выбран"),
                                tr("Нажмите «Выбрать файл…» и укажите .bin для прошивки."),
                                parent=self)
            return
        try:
            offset = int(str(self.offset_var.get()).strip(), 0)
        except ValueError:
            messagebox.showerror(tr("Неверный адрес"),
                                 tr("Адрес задаётся как 0x0, 0x10000 или 0."), parent=self)
            return
        if offset < 0 or offset % 4:
            messagebox.showerror(tr("Неверный адрес"),
                                 tr("Адрес должен быть неотрицательным и кратным 4."), parent=self)
            return
        opts = {"port": self._selected_port(), "baud": self._selected_baud(),
                "bin": path, "offset": offset, "verify": bool(self.verify_var.get()),
                "reset": bool(self.reset_after_var.get())}
        self.cancel_flag.clear()
        self._set_busy(True)
        self.progress.set(0)
        self.progress_lbl.configure(text="…")
        self.worker = threading.Thread(target=self._work, args=("bin", opts), daemon=True)
        self.worker.start()

    # ------------------------------------------------------------------
    # стирание flash
    # ------------------------------------------------------------------
    def _start_erase(self):
        if self._busy:
            return
        if not (self.probe and self.probe.connected):
            messagebox.showinfo(tr("Нужно подключение"), tr("Сначала подключитесь к плате."),
                                parent=self)
            return
        chip = self.state.get("chip") or {}
        flash = self.state.get("flash") or {}
        if not self._confirm_erase(chip, flash):
            return
        opts = {"port": self._selected_port(), "baud": self._selected_baud(),
                "backup": bool(self.backup_var.get())}
        self.cancel_flag.clear()
        self._set_busy(True)
        self.progress.set(0)
        self.progress_lbl.configure(text="…")
        self.worker = threading.Thread(target=self._work, args=("erase", opts), daemon=True)
        self.worker.start()

    def _confirm_erase(self, chip, flash) -> bool:
        size = chipdb.human_size(flash.get("size_real")) if flash.get("size_real") else "вся"
        model = chip.get("name") or "ESP"
        word = confirm_word()
        dlg = tk.Toplevel(self)
        dlg.title(tr("Подтверждение стирания"))
        dlg.configure(bg=C["panel"])
        dlg.transient(self)
        dlg.grab_set()
        pad = 20

        tk.Label(dlg, text=tr("⚠  ПОЛНОЕ СТИРАНИЕ FLASH"), bg=C["panel"], fg=C["err"],
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=pad, pady=(pad, 6))
        txt = (f"Будет очищена вся flash ({size}) чипа {model}:\n"
               "  • загрузчик (bootloader) и таблица разделов\n"
               "  • приложение и все его данные (NVS, SPIFFS/LittleFS, coredump)\n\n"
               "Резервная копия НЕ создаётся. После стирания плата не запустит прошивку — "
               "её нужно будет прошить заново (esptool, Arduino IDE или ESP-IDF).\n\n"
               "Не отключайте плату во время операции.")
        tk.Label(dlg, text=tr(txt), bg=C["panel"], fg=C["text"], font=F_BODY, wraplength=470,
                 justify="left").pack(anchor="w", padx=pad, pady=(0, 12))

        tk.Label(dlg, text=confirm_hint(),
                 bg=C["panel"], fg=C["muted"], font=F_BODY).pack(anchor="w", padx=pad)
        var = tk.StringVar()
        entry = tk.Entry(dlg, textvariable=var, bg=C["panel2"], fg=C["text"],
                         insertbackground=C["text"], font=F_BOLD, bd=0,
                         highlightthickness=1, highlightbackground=C["border"],
                         highlightcolor=C["accent"], width=24)
        entry.pack(anchor="w", padx=pad, pady=(6, 14), ipady=5)

        btns = tk.Frame(dlg, bg=C["panel"])
        btns.pack(fill="x", padx=pad, pady=(0, pad))
        result = {"ok": False}

        def ok():
            if var.get().strip().upper() != word:
                return
            result["ok"] = True
            dlg.destroy()

        btn_ok = RButton(btns, tr("Стереть навсегда"), command=ok, kind="danger", height=34,
                         width=190, parent_bg=C["panel"])
        btn_ok.pack(side="right", padx=(8, 0))
        btn_ok.set_enabled(False)
        RButton(btns, tr("Отмена"), command=dlg.destroy, kind="ghost", height=34,
                width=120, parent_bg=C["panel"]).pack(side="right")

        def on_change(*_):
            btn_ok.set_enabled(var.get().strip().upper() == word)

        var.trace_add("write", on_change)
        entry.bind("<Return>", lambda e: ok())
        entry.focus_set()
        self._center_dialog(dlg)
        self.wait_window(dlg)
        return result["ok"]

    def _cancel(self):
        if self._busy:
            self.cancel_flag.set()
            self._log("Запрошено прерывание…", "warn")
    def _reset_board(self):
        if self._busy:
            return
        if not (self.probe and self.probe.connected):
            messagebox.showinfo(tr("Нужно подключение"), tr("Сначала подключитесь к плате."),
                                parent=self)
            return

        def work():
            try:
                self.probe.reset()
                self.queue.put(("log", "Плата перезагружена.", "ok"))
            except Exception as exc:  # noqa: BLE001
                self.queue.put(("log", f"Сброс не удался: {exc}", "warn"))

        threading.Thread(target=work, daemon=True).start()

    # ------------------------------------------------------------------
    # рабочая нить
    # ------------------------------------------------------------------
    def _work(self, kind, opts=None):
        opts = opts or {}
        try:
            with self._io_lock:
                self._run_task(kind, opts)
        except Cancelled:
            self.queue.put(("log", "Операция прервана.", "warn"))
            self._qprog(0, "прервано")
        except ProbeError as exc:
            self.queue.put(("error", str(exc)))
        except Exception as exc:  # noqa: BLE001
            self.queue.put(("error", f"{type(exc).__name__}: {exc}"))
        finally:
            self.queue.put(("busy", False))

    def _run_task(self, kind, opts):
        if self.probe is None:
            self.probe = EspProbe(log=self._qlog, progress=self._qprog,
                                  cancel=self.cancel_flag.is_set)
        if not self.probe.connected:
            self.queue.put(("log", "Подключение к плате…", "info"))
            self.probe.connect(opts.get("port"), opts.get("baud") or 921600)
            self.queue.put(("chip", self.probe.read_chip()))
            self.queue.put(("connected", True))

        if kind in ("full", "connect"):
            self.queue.put(("log", "Читаю паспорт flash…", "info"))
            try:
                self.queue.put(("flash", self.probe.read_flash_info()))
            except Cancelled:
                raise
            except Exception as exc:  # noqa: BLE001
                self.queue.put(("log", f"Flash: {exc}", "err"))
            self.queue.put(("log", "Тестирую SRAM…", "info"))
            try:
                self.queue.put(("ram", self.probe.ram_test()))
            except Cancelled:
                raise
            except Exception as exc:  # noqa: BLE001
                self.queue.put(("log", f"SRAM: {exc}", "err"))
            self._qprog(1.0, "Проверка завершена")
        elif kind == "flash":
            self.queue.put(("flash", self.probe.read_flash_info()))
            self._qprog(1.0, "Готово")
        elif kind == "ram":
            self.queue.put(("ram", self.probe.ram_test()))
            self._qprog(1.0, "Готово")
        elif kind == "deep":
            flash = self.state.get("flash") or {}
            size = flash.get("size_real") or 0
            if not size:
                raise ProbeError("Неизвестен объём flash — сначала выполните проверку Flash.")
            backup_dir = os.path.join(os.path.expanduser("~"), "Documents")
            if not os.path.isdir(backup_dir):
                backup_dir = os.path.expanduser("~")
            res = self.probe.deep_test(size, backup_dir if opts.get("backup") else None)
            self.queue.put(("deep", res))
            if res.get("error"):
                self.queue.put(("log", f"Тест прерван сбоем: {res['error']}", "err"))
            if res.get("cancelled"):
                self.queue.put(("log", "Тест прерван, прошивка восстановлена.", "warn"))
            # перезапускаем плату в обычный режим и закрываем сессию
            try:
                self.probe.reset()
            except Exception:  # noqa: BLE001
                pass
            self.probe.close()
            self.queue.put(("connected", False))
            self.queue.put(("log", "Плата перезагружена, сессия закрыта.", "ok"))
            self._qprog(1.0, "Готово")
        elif kind == "erase":
            self.queue.put(("log", "Полное стирание flash — не отключайте плату…", "warn"))
            res = self.probe.erase_flash()
            self.queue.put(("erase", res))
            self.state["flash"] = None
            self.state["deep"] = None
            if res.get("blank"):
                self.queue.put(("log", "Проверка чтением: начало flash чистое (0xFF).", "ok"))
            elif res.get("blank") is False:
                self.queue.put(("log", "Внимание: после стирания в начале flash остались данные.", "warn"))
            self.queue.put(("log",
                            f"Flash стёрта за {res.get('seconds', 0):.1f} с "
                            f"({chipdb.human_size(res.get('capacity'))}).", "ok"))
            try:
                self.probe.reset()
            except Exception:  # noqa: BLE001
                pass
            self.probe.close()
            self.queue.put(("connected", False))
            self.queue.put(("log",
                            "Плата перезагружена. Прошивки на ней больше нет — "
                            "прошейте её заново.", "warn"))
            self._qprog(1.0, "Flash стёрта")
        elif kind == "bin":
            res = self.probe.write_bin(opts["bin"], opts.get("offset", 0),
                                       verify=opts.get("verify", True))
            self.queue.put(("bin", res))
            if res.get("cancelled"):
                self.queue.put(("log", "Прошивка прервана — файл записан частично.", "err"))
            else:
                self.queue.put(("log",
                                f"Записано {chipdb.human_size(res['size'])} по адресу "
                                f"0x{res['offset']:06X} за {res['seconds']:.1f} с "
                                f"({(res.get('speed') or 0) / 1024:.0f} КБ/с).", "ok"))
                if res.get("verified") is True:
                    self.queue.put(("log", "Проверка чтением: данные совпадают.", "ok"))
                elif res.get("verified") is False:
                    self.queue.put(("log", "Проверка чтением: есть расхождения!", "err"))
                if res["offset"] == 0:
                    # прошит полный образ — перечитываем паспорт до перезапуска
                    try:
                        self.queue.put(("flash", self.probe.read_flash_info()))
                    except Exception as exc:  # noqa: BLE001
                        self.queue.put(("log", f"Не удалось перечитать flash: {exc}", "warn"))
                if opts.get("reset", True):
                    try:
                        self.probe.reset()
                    except Exception:  # noqa: BLE001
                        pass
                    self.probe.close()
                    self.queue.put(("connected", False))
                    self.queue.put(("log", "Плата перезагружена — запущена новая прошивка.", "ok"))
                else:
                    self.queue.put(("log", "Запись завершена, плата не перезагружалась — "
                                           "нажмите «Сбросить плату (RST)» для запуска.", "info"))
            self._qprog(1.0, "Готово")

        self.queue.put(("report", self._build_report()))

    def _on_connected(self, value: bool):
        self._connected = bool(value)
        self.status_dot.itemconfigure(self._dot, fill=C["ok"] if value else "#3b4a58")
        self._set_status("подключено" if value else "не подключено",
                         C["ok"] if value else C["muted"])
        self.btn_connect.set_text(tr("Отключиться" if value else "Подключиться"))
        if value:
            self._reconnect_tried = None
            self._manual_disconnect = False
            port = getattr(self.probe, "port", None)
            self._connected_port_info = self._find_port_info(port)
            if port:
                # показываем в шапке реальный порт, к которому подключились
                info = self._find_port_info(port)
                self.port_var.set(info["label"] if info else port)
                self._sync_port_list()
        if not value:
            for key in ("chip.name", "chip.desc", "chip.rev", "chip.core", "chip.crystal",
                        "chip.mac", "chip.stub", "chip.port", "chip.baud", "chip.features"):
                if key in self.kv:
                    self.kv[key].configure(text="—")

    def _set_busy(self, value: bool):
        self._busy = value
        for btn in (self.btn_full, self.btn_flash, self.btn_ram, self.btn_deep,
                    self.btn_erase, self.btn_write, self.btn_pick, self.btn_connect):
            btn.set_enabled(not value)
        self.btn_stop.set_enabled(value)
        if not value:
            self.progress.set(0)

    # ------------------------------------------------------------------
    # отрисовка данных
    # ------------------------------------------------------------------
    def _render_chip(self, info: dict):
        self.state["chip"] = info
        table = info.get("table") or {}
        self.kv["chip.name"].configure(text=info.get("name") or "—", fg=C["accent"])
        self.kv["chip.desc"].configure(text=info.get("desc") or "—")
        self.kv["chip.rev"].configure(text=f"v{info['revision']}" if info.get("revision") else "—")
        self.kv["chip.core"].configure(text=tr(table.get("core", "—")))
        crystal = info.get("crystal")
        self.kv["chip.crystal"].configure(text=tr(f"{crystal} МГц") if crystal else "—")
        self.kv["chip.mac"].configure(text=info.get("mac", "—"))
        self.kv["chip.stub"].configure(
            text=tr("ROM + stub (полный доступ)" if info.get("stub")
                    else "ROM (ограниченный доступ)"))
        self.kv["chip.port"].configure(text=info.get("port", "—"))
        self.kv["chip.baud"].configure(text=tr(f"{info.get('baud', 0)} бод"))
        feats = info.get("features") or "—"
        self.kv["chip.features"].configure(text=feats, wraplength=760, justify="left")

        sram = table.get("sram_kb")
        self.kv["chip.sram"].configure(
            text=tr(f"{sram} КБ") if sram else tr("неизвестно"),
            fg=C["accent"] if sram else C["muted"])
        self.kv["chip.psram"].configure(text=tr(table.get("psram", "—")))
        self.note_lbl.configure(text=tr(table.get("note", "")))

        # --- возможности чипа ---
        caps = info.get("caps") or {}
        self._cap_row("cap.wifi", caps.get("wifi"), "есть", "нет в этой модели")
        self._cap_row("cap.bt", caps.get("bt"), "есть", "нет")
        self._cap_row("cap.154", caps.get("ieee154"), "есть", "нет")
        self._cap_row("cap.flash", caps.get("flash"), "", "нет в корпусе (внешняя микросхема)")
        self._cap_row("cap.psram", caps.get("psram"), "", "нет в корпусе")
        cpu = " · ".join(x for x in (caps.get("cores"), caps.get("freq")) if x) or "—"
        self.kv["cap.cpu"].configure(text=cpu)

        note = ("Wi-Fi / Bluetooth / 802.15.4 — наличие радио в кристалле (по данным eFuse и ROM). "
                "Живую проверку (скан сетей, сопряжение) даёт только прошивка платы: "
                "загрузчик радио не включает.")
        self.cap_note.configure(text=tr(note))

        # --- безопасность ---
        sec = info.get("security")
        mac_check = info.get("mac_check") or {}
        if info.get("usb_vid") == 0x303A:
            oui_text, oui_level = tr("Espressif · нативный USB (VID 303A)"), "ok"
        else:
            oui_text = tr(mac_check.get("text", "—"))
            oui_level = mac_check.get("level", "muted")
        self.kv["sec.oui"].configure(
            text=oui_text,
            fg={"ok": C["ok"], "warn": C["warn"]}.get(oui_level, C["muted"]))
        if not sec:
            for key in ("sec.boot", "sec.enc", "sec.jtag", "sec.chipid", "sec.usb"):
                self.kv[key].configure(text="—", fg=C["muted"])
        else:
            self.kv["sec.boot"].configure(
                text=tr("ВКЛЮЧЁН") if sec.get("secure_boot") else tr("выключен"),
                fg=C["warn"] if sec.get("secure_boot") else C["muted"])
            enc = sec.get("flash_enc")
            self.kv["sec.enc"].configure(
                text=tr({True: "ВКЛЮЧЕНО", False: "выключено", None: "—"}[enc]),
                fg=C["warn"] if enc else C["muted"])
            self.kv["sec.jtag"].configure(text=tr(sec.get("jtag", "—")))
            cid = sec.get("chip_id")
            self.kv["sec.chipid"].configure(text=f"0x{cid:04X}" if cid is not None else "—")
            self.kv["sec.usb"].configure(
                text=tr("отключён") if sec.get("usb_disabled") else tr("доступен"),
                fg=C["warn"] if sec.get("usb_disabled") else C["muted"])

        if self.state.get("flash"):
            self._render_app((self.state["flash"] or {}).get("app"), info)
        if self.state.get("ram"):
            self._render_ram(self.state["ram"])

    def _cap_row(self, key, value, prefix, absent):
        lbl = self.kv.get(key)
        if not lbl:
            return
        if value:
            text = f"{prefix} · {value}".strip(" ·") if prefix else str(value)
            lbl.configure(text=tr(text), fg=C["ok"])
        else:
            lbl.configure(text=tr(absent), fg=C["muted"])

    def _render_app(self, app, chip):
        chip = chip or {}
        if not app:
            for key in ("app.project", "app.version", "app.idf", "app.built", "app.chipid"):
                self.kv[key].configure(text="—", fg=C["muted"])
            return
        if not app.get("valid"):
            self.kv["app.project"].configure(text=tr("заголовок приложения не найден"),
                                             fg=C["warn"])
            for key in ("app.version", "app.idf", "app.built"):
                self.kv[key].configure(text="—", fg=C["muted"])
            acid = app.get("chip_id")
            self.kv["app.chipid"].configure(text=f"0x{acid:04X}" if acid is not None else "—")
            return
        self.kv["app.project"].configure(text=app.get("project", "—"), fg=C["accent"])
        self.kv["app.version"].configure(text=app.get("version", "—"))
        self.kv["app.idf"].configure(text=app.get("idf", "—"))
        self.kv["app.built"].configure(text=app.get("built", "—"))
        acid = app.get("chip_id")
        rid = chip.get("image_chip_id")
        if acid is not None and rid is not None and acid != rid:
            self.kv["app.chipid"].configure(
                text=tr(f"0x{acid:04X} ≠ 0x{rid:04X} — образ от другого чипа!"), fg=C["err"])
        elif acid is not None:
            self.kv["app.chipid"].configure(text=tr(f"0x{acid:04X} — совпадает"), fg=C["ok"])
        else:
            self.kv["app.chipid"].configure(text="—", fg=C["muted"])

    def _render_flash(self, info: dict):
        self.state["flash"] = info
        real = info.get("size_real")
        declared = info.get("size_declared")
        self.flash_big.configure(text=tr(chipdb.human_size_short(real)) if real else "—",
                                 fg=C["text"])
        self.flash_sub.configure(
            text=f"JEDEC {info.get('jedec_id') or '—'} · {info.get('mfg', '—')}")

        verdict = info.get("verdict") or {}
        level = verdict.get("level", "muted")
        self.flash_badge.set(tr(verdict.get("title", "")), level)
        self.flash_verdict.configure(
            text=tr(verdict.get("text", "")),
            fg={"ok": C["ok"], "warn": C["warn"], "err": C["err"]}.get(level, C["muted"]))

        top = max(filter(None, [real, declared]), default=0)
        if top:
            self.flash_bar.set((real or 0) / top, C["accent"] if level == "ok" else C["warn"])
        else:
            self.flash_bar.set(0)
        self.flash_cmp.configure(
            text=tr(f"реально: {chipdb.human_size(real) if real else '—'}   ·   "
                    f"заявлено прошивкой: {chipdb.human_size(declared) if declared else '—'}"))

        self.kv["fl.jedec"].configure(text=("0x" + info["jedec_id"]) if info.get("jedec_id") else "—")
        self.kv["fl.mfg"].configure(text=tr(info.get("mfg", "—")))
        code = info.get("cap_code")
        self.kv["fl.cap"].configure(text=f"0x{code:02X}" if code is not None else "—")
        self.kv["fl.size_id"].configure(text=tr(chipdb.human_size_short(info.get("size_jedec"))))
        self.kv["fl.size_det"].configure(text=tr(chipdb.human_size_short(info.get("size_detected"))))
        sp = info.get("read_speed")
        self.kv["fl.speed"].configure(text=tr(f"{sp / 1024:.0f} КБ/с") if sp else "—")

        hdr = info.get("hdr_addr")
        self.kv["fl.hdr"].configure(text=tr(f"0x{hdr:04X} (валидный)") if hdr is not None
                                        else tr("не найден"))
        self.kv["fl.declared"].configure(text=tr(chipdb.human_size_short(declared)))
        cid = info.get("hdr_chip_id")
        self.kv["fl.chipid"].configure(text=f"0x{cid:04X}" if cid is not None else "—")
        self.kv["fl.part_total"].configure(text=tr(chipdb.human_size_short(info.get("part_total"))))
        self.kv["fl.part_end"].configure(
            text=(f"0x{info['part_end']:06X}" if info.get("part_end") else "—"))
        pt = info.get("pt_addr")
        self.kv["fl.pt_addr"].configure(text=f"0x{pt:04X}" if pt else tr("не найдена"))
        self._render_app(info.get("app"), self.state.get("chip"))

        for child in self.part_frame.winfo_children():
            child.destroy()
        parts = info.get("partitions") or []
        if not parts:
            tk.Label(self.part_frame, text=tr("таблица разделов не найдена (плата не прошита?)"),
                     bg=C["panel"], fg=C["muted"], font=F_BODY).pack(anchor="w")
        else:
            head = tk.Frame(self.part_frame, bg=C["panel"])
            head.pack(fill="x", pady=(0, 4))
            for text, width in (("Раздел", 22), ("Тип", 8), ("Смещение", 12), ("Размер", 12)):
                tk.Label(head, text=tr(text), bg=C["panel"], fg=C["muted"], font=F_TINY,
                         width=width, anchor="w").pack(side="left")
            for p in parts[:20]:
                row = tk.Frame(self.part_frame, bg=C["panel"])
                row.pack(fill="x")
                tk.Label(row, text=p["label"], bg=C["panel"], fg=C["text"], font=F_MONO,
                         width=22, anchor="w").pack(side="left")
                tk.Label(row, text=tr(p["type"]), bg=C["panel"], fg=C["muted"], font=F_MONO,
                         width=8, anchor="w").pack(side="left")
                tk.Label(row, text=f"0x{p['offset']:06X}", bg=C["panel"], fg=C["text"],
                         font=F_MONO, width=12, anchor="w").pack(side="left")
                tk.Label(row, text=tr(chipdb.human_size_short(p["size"])), bg=C["panel"],
                         fg=C["text"], font=F_MONO, width=12, anchor="w").pack(side="left")

    def _render_ram(self, info: dict):
        self.state["ram"] = info
        table = (self.state.get("chip") or {}).get("table") or {}
        sram = table.get("sram_kb")
        self.ram_big.configure(text=tr(f"{sram} КБ") if sram else "—")

        if not info.get("available"):
            self.ram_badge.set(tr("не проверено"), "warn")
            self.ram_sub.configure(text=tr(info.get("note") or "тест недоступен"))
        else:
            data_ok = info.get("data_ok")
            addr_ok = info.get("addr_ok")
            good = bool(data_ok) and bool(addr_ok)
            self.ram_badge.set(tr("SRAM работает" if good else "ошибки чтения/записи"),
                               "ok" if good else "err")
            self.ram_sub.configure(text=tr(
                "объём задан моделью чипа; ниже — проверка целостности ячеек"))

        base = info.get("base")
        self.kv["ram.base"].configure(text=f"0x{base:08X}" if base else "—")
        self.kv["ram.cells"].configure(text=str(info.get("cells") or "—"))
        self.kv["ram.data"].configure(
            text=tr({True: "OK", False: "ОШИБКА", None: "—"}[info.get("data_ok")]),
            fg={True: C["ok"], False: C["err"], None: C["muted"]}[info.get("data_ok")])
        self.kv["ram.addr"].configure(
            text=tr({True: "OK", False: "ОШИБКА", None: "—"}[info.get("addr_ok")]),
            fg={True: C["ok"], False: C["err"], None: C["muted"]}[info.get("addr_ok")])
        errors = info.get("errors") or []
        self.ram_err.configure(text="\n".join(errors[:6]) if errors else "")

        self.ram_psram.configure(text=tr(table.get("psram", "—")))
        no_psram = "нет интерфейса" in (table.get("psram") or "")
        self.ram_psram_note.configure(
            text=tr("В этом чипе внешняя PSRAM не поддерживается аппаратно — проверять нечего."
                  if no_psram else
                  "PSRAM нельзя измерить через ROM-загрузчик: она не инициализирована до запуска "
                  "прошивки. Точный объём PSRAM показывает сама прошивка (esp_psram_get_size) или "
                  "команда esptool flash_id по встроенному в модуль чипу."))

    def _render_deep(self, res: dict):
        self.state["deep"] = res
        if res.get("ok"):
            text = (f"Запись и чтение всей flash ({chipdb.human_size(res['capacity'])}) "
                    f"без ошибок. Это подтверждает реальный объём.")
            color = C["ok"]
        else:
            bad = res.get("bad") or []
            first = f"0x{min(bad):06X}" if bad else "—"
            text = (f"Найдено ошибок в {len(bad)} блоках. Первый сбой: {first}. "
                    f"Похоже, реальный объём ≈ {chipdb.human_size_short(res.get('guess'))} "
                    f"(заявлено {chipdb.human_size_short(res['capacity'])}).")
            color = C["err"]
        if res.get("restore_ok") is True:
            text += "\nПрошивка восстановлена и проверена."
        elif res.get("restore_ok") is False:
            text += "\n⚠ Восстановление не подтверждено — прошейте плату заново."
        if res.get("backup"):
            text += f"\nРезервная копия: {res['backup']}"
        if res.get("write_speed"):
            text += (f"\nСкорость: запись {res['write_speed'] / 1024:.0f} КБ/с, "
                     f"чтение {(res.get('read_speed') or 0) / 1024:.0f} КБ/с")
        self.deep_lbl.configure(text=tr_lines(text), fg=color)
        self._set_tab("flash")

    def _render_erase(self, res: dict):
        """Показать, что плата осталась без прошивки."""
        self.state["flash"] = None
        self.state["deep"] = None
        self.flash_big.configure(text=tr("стёрта"), fg=C["warn"])
        self.flash_sub.configure(text=tr("микросхема очищена полностью — прошивки на плате нет"))
        self.flash_badge.set(tr("flash пуста"), "warn")
        self.flash_verdict.configure(
            text=tr("Все данные удалены (загрузчик, разделы, NVS). Чтобы плата снова работала, "
                    "прошейте её: esptool write_flash, Arduino IDE или ESP-IDF."),
            fg=C["warn"])
        self.flash_bar.set(0)
        self.flash_cmp.configure(text="")
        self.deep_lbl.configure(text="")
        for key in ("fl.jedec", "fl.mfg", "fl.cap", "fl.size_id", "fl.size_det", "fl.speed",
                    "fl.hdr", "fl.declared", "fl.chipid", "fl.part_total", "fl.part_end",
                    "fl.pt_addr"):
            if key in self.kv:
                self.kv[key].configure(text="—")
        for child in self.part_frame.winfo_children():
            child.destroy()
        tk.Label(self.part_frame, text=tr("flash стёрта — таблицы разделов больше нет"),
                 bg=C["panel"], fg=C["muted"], font=F_BODY).pack(anchor="w")
        self._set_tab("flash")

    # ------------------------------------------------------------------
    # отчёт
    # ------------------------------------------------------------------
    def _report_set(self, text):
        self.report_text.configure(state="normal")
        self.report_text.delete("1.0", "end")
        self.report_text.insert("1.0", tr_lines(text))
        self.report_text.configure(state="disabled")

    def _build_report(self) -> str:
        chip = self.state.get("chip") or {}
        flash = self.state.get("flash") or {}
        ram = self.state.get("ram") or {}
        deep = self.state.get("deep") or {}
        table = chip.get("table") or {}
        L = []
        L.append("=" * 66)
        L.append("  ESP_TEST — ОТЧЁТ О ПРОВЕРКЕ ПАМЯТИ")
        L.append("=" * 66)
        L.append(f"Дата: {time.strftime('%d.%m.%Y %H:%M:%S')}")
        L.append("")
        L.append("ЧИП")
        L.append(f"  Модель\t{chip.get('name', '—')}")
        L.append(f"  Маркировка\t{chip.get('desc') or '—'}")
        L.append(f"  Ревизия\t{chip.get('revision') or '—'}")
        L.append(f"  Ядро\t{table.get('core', '—')}")
        L.append(f"  Кварц\t{str(chip.get('crystal') or '—') + ' МГц'}")
        L.append(f"  MAC\t{chip.get('mac', '—')}")
        L.append(f"  Порт / скорость\t{chip.get('port', '—')} / {chip.get('baud', '—')} бод")
        caps = chip.get("caps") or {}
        L.append("")
        L.append("ВОЗМОЖНОСТИ ЧИПА")
        L.append(f"  Wi-Fi\t{caps.get('wifi') or 'нет'}")
        L.append(f"  Bluetooth\t{caps.get('bt') or 'нет'}")
        L.append(f"  IEEE 802.15.4\t{caps.get('ieee154') or 'нет'}")
        L.append(f"  Встроенная flash\t{caps.get('flash') or 'нет'}")
        L.append(f"  Встроенная PSRAM\t{caps.get('psram') or 'нет'}")
        L.append(f"  Процессор\t{' · '.join(x for x in (caps.get('cores'), caps.get('freq')) if x) or '—'}")
        sec = chip.get("security") or {}
        if sec:
            L.append("")
            L.append("БЕЗОПАСНОСТЬ И ПОДЛИННОСТЬ")
            L.append(f"  MAC / OUI\t{(chip.get('mac_check') or {}).get('text', '—')}")
            L.append(f"  Secure Boot\t{'включён' if sec.get('secure_boot') else 'выключен'}")
            L.append(f"  Шифрование flash\t{'включено' if sec.get('flash_enc') else 'выключено'}")
            L.append(f"  JTAG\t{sec.get('jtag', '—')}")
            cid = sec.get("chip_id")
            L.append(f"  Chip ID (eFuse)\t{'0x%04X' % cid if cid is not None else '—'}")
        L.append("")
        L.append("FLASH")
        L.append(f"  JEDEC ID\t{'0x' + flash['jedec_id'] if flash.get('jedec_id') else '—'}")
        L.append(f"  Производитель\t{flash.get('mfg', '—')}")
        L.append(f"  Объём по ID\t{chipdb.human_size(flash.get('size_jedec'))}")
        L.append(f"  Автоопределение\t{chipdb.human_size(flash.get('size_detected'))}")
        L.append(f"  РЕАЛЬНЫЙ ОБЪЁМ\t{chipdb.human_size(flash.get('size_real'))}")
        L.append(f"  Заявлено в образе\t{chipdb.human_size(flash.get('size_declared'))}")
        L.append(f"  Таблица разделов\t{('0x%04X' % flash['pt_addr']) if flash.get('pt_addr') else 'не найдена'}")
        L.append(f"  Занято разделами\t{chipdb.human_size(flash.get('part_total'))}")
        if flash.get("read_speed"):
            L.append(f"  Скорость чтения\t{flash['read_speed'] / 1024:.0f} КБ/с")
        verdict = flash.get("verdict") or {}
        L.append(f"  Вердикт\t{verdict.get('title', '—')}")
        if verdict.get("text"):
            L.append(f"    {verdict['text']}")
        app = flash.get("app") or {}
        if app.get("valid"):
            L.append("")
            L.append("ПРОШИВКА НА ПЛАТЕ")
            L.append(f"  Проект\t{app.get('project', '—')}")
            L.append(f"  Версия\t{app.get('version', '—')}")
            L.append(f"  ESP-IDF\t{app.get('idf', '—')}")
            L.append(f"  Собрана\t{app.get('built', '—')}")
            acid = app.get("chip_id")
            if acid is not None:
                L.append(f"  Chip ID образа\t0x{acid:04X}")
        parts = flash.get("partitions") or []
        if parts:
            L.append("")
            L.append("  Разделы:")
            L.append("    Имя\tТип\tСмещение\tРазмер")
            for p in parts:
                L.append(f"    {p['label']}\t{p['type']}\t0x{p['offset']:06X}\t"
                         f"{chipdb.human_size_short(p['size'])}")
        if deep:
            L.append("")
            L.append("ГЛУБОКИЙ ТЕСТ FLASH")
            L.append(f"  Объём теста\t{chipdb.human_size(deep.get('capacity'))}")
            L.append(f"  Ошибок\t{len(deep.get('bad') or [])}")
            L.append(f"  Без ошибок\t{chipdb.human_size(deep.get('verified'))}")
            L.append(f"  Восстановлено\t{deep.get('restore_ok')}")
            if deep.get("backup"):
                L.append(f"  Резервная копия\t{deep['backup']}")
        erase = self.state.get("erase") or {}
        if erase:
            L.append("")
            L.append("СТИРАНИЕ FLASH (ПОЛНОЕ)")
            L.append(f"  Выполнено\t{'да' if erase.get('ok') else 'нет'}")
            L.append(f"  Объём микросхемы\t{chipdb.human_size(erase.get('capacity'))}")
            L.append(f"  Время\t{erase.get('seconds', 0):.1f} с")
            L.append(f"  Проверка 0xFF\t{_tf(erase.get('blank'))}")
            L.append("  Прошивка удалена — плату нужно прошить заново")
        binres = self.state.get("bin") or {}
        if binres:
            L.append("")
            L.append("ПРОШИВКА ФАЙЛА")
            L.append(f"  Файл\t{binres.get('name', '—')}")
            L.append(f"  Адрес\t0x{binres.get('offset', 0):06X}")
            L.append(f"  Размер\t{chipdb.human_size(binres.get('size'))}")
            L.append(f"  Проверка чтением\t{_tf(binres.get('verified'))}")
        L.append("")
        L.append("ОЗУ")
        L.append(f"  Встроенная SRAM\t{str(table.get('sram_kb') or '?') + ' КБ (по документации)'}")
        L.append(f"  Тест данных\t{_tf(ram.get('data_ok'))}")
        L.append(f"  Тест адресов\t{_tf(ram.get('addr_ok'))}")
        L.append(f"  Ячеек проверено\t{ram.get('cells')}")
        L.append(f"  Внешняя PSRAM\t{table.get('psram', '—')}")
        if ram.get("errors"):
            L.append("  Ошибки:")
            for e in ram["errors"][:10]:
                L.append(f"    {e}")
        L.append("")
        L.append("=" * 66)
        return "\n".join(tr(line) for line in L)

    def _save_report(self):
        text = self._build_report()
        path = filedialog.asksaveasfilename(
            parent=self, title=tr("Сохранить отчёт"),
            defaultextension=".txt",
            initialfile=f"esp32_memory_report_{time.strftime('%Y%m%d_%H%M')}.txt",
            filetypes=[(tr("Текстовый файл"), "*.txt"), (tr("Все файлы"), "*.*")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            self._log(f"Отчёт сохранён: {path}", "ok")
        except Exception as exc:
            messagebox.showerror(tr("Ошибка"), tr(f"Не удалось сохранить: {exc}"), parent=self)

    # ------------------------------------------------------------------
    # демо-режим
    # ------------------------------------------------------------------
    def _load_demo(self):
        self._on_connected(True)
        self._set_status("демо-режим", C["warn"])
        features = ["Wi-Fi", "BT 5 (LE)", "Dual Core + LP Core", "240MHz", "Embedded PSRAM 8MB"]
        self._render_chip({
            "name": "ESP32-S3",
            "desc": "ESP32-S3 (QFN56) (revision v0.2)",
            "revision": "0.2",
            "features": ", ".join(features),
            "features_list": features,
            "caps": chipdb.describe_features(features),
            "crystal": 40,
            "mac": "7C:DF:A1:1A:2B:3C",
            "mac_check": chipdb.check_mac("7C:DF:A1:1A:2B:3C"),
            "security": {"secure_boot": False, "flash_enc": False, "jtag": "доступен",
                         "usb_disabled": False, "chip_id": 9, "flags": 0},
            "image_chip_id": 9,
            "stub": True,
            "baud": 921600,
            "port": "COM5",
            "table": chipdb.chip_entry("ESP32-S3"),
        })
        self._render_flash({
            "jedec_id": "C84017", "mfg": "GigaDevice", "cap_code": 0x17,
            "size_jedec": 8 << 20, "size_detected": 8 << 20, "size_real": 8 << 20,
            "size_declared": 8 << 20, "hdr_addr": 0x0, "hdr_chip_id": 0x0009,
            "pt_addr": 0x8000, "part_total": 4 << 20, "part_end": 0x410000,
            "read_speed": 148 << 10,
            "app": {"offset": 0x10000, "valid": True, "chip_id": 9,
                    "project": "esp_hub", "version": "1.0.1",
                    "built": "Nov 16 2026 13:24:30", "idf": "v5.2.2"},
            "partitions": [
                {"label": "nvs", "type": "data", "subtype": "0x02", "offset": 0x9000, "size": 0x5000},
                {"label": "otadata", "type": "data", "subtype": "0x00", "offset": 0xE000, "size": 0x2000},
                {"label": "app0", "type": "app", "subtype": "0x00", "offset": 0x10000, "size": 0x140000},
                {"label": "spiffs", "type": "data", "subtype": "0x82", "offset": 0x150000, "size": 0x2C0000},
            ],
            "verdict": {"level": "ok", "title": "Объём подтверждён",
                        "text": "Идентификатор чипа и заголовок прошивки совпадают: 8 МБ."},
        })
        self._render_ram({
            "available": True, "base": 0x3FCAE000, "bss": 0x3FCB0000,
            "data_ok": True, "addr_ok": True, "cells": 9, "errors": [],
            "note": "",
        })
        self._report_set(self._build_report())
        self._log("Демо-режим: показаны данные виртуальной платы ESP32-S3.", "warn")

    # ------------------------------------------------------------------
    def _on_close(self):
        self._closing = True
        self.cancel_flag.set()
        if self.probe:
            try:
                self.probe.close()
            except Exception:
                pass
        self.destroy()


def run(demo: bool = False):
    app = App(demo=demo)
    app.mainloop()
