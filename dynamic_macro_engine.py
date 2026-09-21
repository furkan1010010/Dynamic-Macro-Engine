import time
import threading
import random
import tkinter as tk
from tkinter import messagebox
import winsound
import json
import os
from pynput.keyboard import Listener, KeyCode, Key
from pynput import mouse as pynput_mouse
import ctypes

# Windows API Entegrasyonları ve Kontrolü
win32api_available = False
try:
    import win32gui
    import win32process
    import win32con
    import win32api
    win32api_available = True
except ImportError:
    pass

user32 = ctypes.windll.user32
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
KEYEVENTF_KEYUP = 0x0002

# --- SendInput scan-code keyboard simulation ---
KEYEVENTF_SCANCODE = 0x0008
INPUT_KEYBOARD = 1
MAPVK_VK_TO_VSC = 0

PUL = ctypes.POINTER(ctypes.c_ulong)

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong),
                ("wParamL", ctypes.c_short),
                ("wParamH", ctypes.c_ushort)]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT),
                ("ki", KEYBDINPUT),
                ("hi", HARDWAREINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong),
                ("union", _INPUT_UNION)]

def send_scancode_key(vk, key_up=False):
    scan = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
    extra = ctypes.c_ulong(0)
    flags = KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if key_up else 0)
    ki = KEYBDINPUT(0, scan, flags, 0, ctypes.pointer(extra))
    inp = INPUT(INPUT_KEYBOARD, _INPUT_UNION(ki=ki))
    n = user32.SendInput(1, ctypes.pointer(inp), ctypes.sizeof(inp))
    return n == 1

VK_CODES = {
    '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34, '5': 0x35,
    '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39, '0': 0x30,
    'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45,
    'f': 0x46, 'g': 0x47, 'h': 0x48, 'i': 0x49, 'j': 0x4A,
    'k': 0x4B, 'l': 0x4C, 'm': 0x4D, 'n': 0x4E, 'o': 0x4F,
    'p': 0x50, 'q': 0x51, 'r': 0x52, 's': 0x53, 't': 0x54,
    'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58, 'y': 0x59, 'z': 0x5A,

    'mouse1': 0x01, 'lmb': 0x01, 'leftclick': 0x01,
    'mouse2': 0x02, 'rmb': 0x02, 'rightclick': 0x02,
    'mouse3': 0x04, 'mmb': 0x04, 'middleclick': 0x04,
    'mouse4': 0x05, 'xbutton1': 0x05,
    'mouse5': 0x06, 'xbutton2': 0x06,

    'space': 0x20, 'spacebar': 0x20,
    'shift': 0x10, 'ctrl': 0x11, 'control': 0x11, 'alt': 0x12,
    'tab': 0x09, 'capslock': 0x14, 'enter': 0x0D, 'esc': 0x1B, 'escape': 0x1B,
    'up': 0x26, 'down': 0x28, 'left': 0x25, 'right': 0x27,

    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73, 'f5': 0x74, 'f6': 0x75,
    'f7': 0x76, 'f8': 0x77, 'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
}

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    pass

CONFIG_FILE = "clicker_config.json"

# App identity (change name/version here)
APP_NAME = "Dynamic Macro Engine"
APP_VERSION = "v1.0.0"

# Polling rate levels: (spin_window_seconds, idle_poll_seconds)
# spin_window None = busy-wait the entire delay (max accuracy, max CPU)
POLLING_LEVELS = {
    1: (0.0,    0.020),
    2: (0.0005, 0.010),
    3: (0.002,  0.005),
    4: (0.005,  0.002),
    5: (None,   0.0005),
}
POLLING_NAMES = {1: "1 · Lowest CPU", 2: "2 · Light", 3: "3 · Balanced", 4: "4 · High", 5: "5 · Max"}

# --- PREMIUM SMOOTH ELEMENT UI KIT (FIXED GEOMETRY) ---
class SmoothButton(tk.Canvas):
    def __init__(self, parent, text, command=None, font=("Segoe UI", 9, "bold"), width=100, height=28, bg="#121212", fg="#ffffff", btn_bg="#252525", active_bg="#353535", radius=8, **kwargs):
        super().__init__(parent, width=width, height=height, bg=bg, highlightthickness=0, bd=0, **kwargs)
        self.command = command
        self.text = text
        self.font = font
        self.fg = fg
        self.btn_bg = btn_bg
        self.active_bg = active_bg
        self.radius = radius
        self.width = width
        self.height = height
        self.current_bg = btn_bg
        self.shape_items = []
        self.text_item = None
        self.draw_button()
        self.bind("<Button-1>", self.on_click)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def draw_button(self):
        w, h = self.width, self.height
        r = self.radius
        if not self.shape_items:
            self.shape_items = [
                self.create_oval(0, 0, r*2, r*2, fill=self.current_bg, outline=self.current_bg),
                self.create_oval(w-r*2, 0, w, r*2, fill=self.current_bg, outline=self.current_bg),
                self.create_oval(0, h-r*2, r*2, h, fill=self.current_bg, outline=self.current_bg),
                self.create_oval(w-r*2, h-r*2, w, h, fill=self.current_bg, outline=self.current_bg),
                self.create_rectangle(r, 0, w-r, h, fill=self.current_bg, outline=self.current_bg),
                self.create_rectangle(0, r, w, h-r, fill=self.current_bg, outline=self.current_bg),
            ]
            self.text_item = self.create_text(w/2, h/2, text=self.text, fill=self.fg, font=self.font, justify="center")
        else:
            for item in self.shape_items:
                self.itemconfig(item, fill=self.current_bg, outline=self.current_bg)
            self.itemconfig(self.text_item, text=self.text, fill=self.fg, font=self.font)

    def on_click(self, event):
        if self.command: self.command()

    def on_enter(self, event):
        self.current_bg = self.active_bg
        self.draw_button()

    def on_leave(self, event):
        self.current_bg = self.btn_bg
        self.draw_button()

    def update_colors(self, bg, fg, btn_bg, active_bg):
        self.config(bg=bg)
        self.fg = fg
        self.btn_bg = btn_bg
        self.active_bg = active_bg
        self.current_bg = btn_bg
        self.draw_button()


class SmoothEntry(tk.Canvas):
    def __init__(self, parent, textvariable, width_chars=8, height_px=24, bg="#121212", fg="#ffffff", entry_bg="#252525", radius=6, justify="center", font=("Segoe UI", 9)):
        self.calculated_width = (width_chars * 8) + 14
        self.height_px = height_px
        super().__init__(parent, width=self.calculated_width, height=height_px, bg=bg, highlightthickness=0, bd=0)
        self.textvariable = textvariable
        self.entry_bg = entry_bg
        self.radius = radius
        self.fg = fg
        self.justify = justify
        self.font = font
        self.shape_items = []
        self.entry = None

        self.draw_entry()

    def draw_entry(self):
        w = self.calculated_width
        h = self.height_px
        r = self.radius

        if not self.shape_items:
            self.shape_items = [
                self.create_oval(0, 0, r*2, r*2, fill=self.entry_bg, outline=self.entry_bg),
                self.create_oval(w-r*2, 0, w, r*2, fill=self.entry_bg, outline=self.entry_bg),
                self.create_oval(0, h-r*2, r*2, h, fill=self.entry_bg, outline=self.entry_bg),
                self.create_oval(w-r*2, h-r*2, w, h, fill=self.entry_bg, outline=self.entry_bg),
                self.create_rectangle(r, 0, w-r, h, fill=self.entry_bg, outline=self.entry_bg),
                self.create_rectangle(0, r, w, h-r, fill=self.entry_bg, outline=self.entry_bg),
            ]
            self.entry = tk.Entry(self, textvariable=self.textvariable, bg=self.entry_bg, fg=self.fg, insertbackground=self.fg, bd=0, highlightthickness=0, justify=self.justify, font=self.font)
            self.create_window(w/2, h/2, window=self.entry, width=w-8, height=h-4)
            self._idle_after_id = None
            self.entry.bind("<FocusIn>", self._start_idle_timer)
            self.entry.bind("<Key>", self._reset_idle_timer)
            self.entry.bind("<FocusOut>", self._cancel_idle_timer)
        else:
            for item in self.shape_items:
                self.itemconfig(item, fill=self.entry_bg, outline=self.entry_bg)
            self.entry.config(bg=self.entry_bg, fg=self.fg, insertbackground=self.fg)

    def _start_idle_timer(self, event=None):
        self._cancel_idle_timer()
        self._idle_after_id = self.after(15000, self._deselect_on_idle)

    def _reset_idle_timer(self, event=None):
        self._cancel_idle_timer()
        self._idle_after_id = self.after(15000, self._deselect_on_idle)

    def _cancel_idle_timer(self, event=None):
        if getattr(self, "_idle_after_id", None):
            try:
                self.after_cancel(self._idle_after_id)
            except:
                pass
            self._idle_after_id = None

    def _deselect_on_idle(self):
        try:
            if self.entry is self.entry.focus_get():
                self.winfo_toplevel().focus_set()
        except:
            pass

    def update_colors(self, bg, fg, entry_bg):
        self.config(bg=bg)
        self.fg = fg
        self.entry_bg = entry_bg
        self.draw_entry()


class SmoothCombobox(tk.Canvas):
    def __init__(self, parent, textvariable, values, width_chars=14, height_px=24, bg="#121212", fg="#ffffff", entry_bg="#252525", radius=6, font=("Segoe UI", 9), command=None):
        self.calculated_width = (width_chars * 8) + 22
        self.height_px = height_px
        super().__init__(parent, width=self.calculated_width, height=height_px, bg=bg, highlightthickness=0, bd=0)
        self.textvariable = textvariable
        self.values = values
        self.entry_bg = entry_bg
        self.radius = radius
        self.fg = fg
        self.font = font
        self.command = command
        self.shape_items = []
        self.text_item = None
        self.arrow_item = None
        self.menu = None

        self.draw_combo()
        self.bind("<Button-1>", self.show_menu)

    def draw_combo(self):
        r = self.radius
        w, h = self.calculated_width, self.height_px

        if not self.shape_items:
            self.shape_items = [
                self.create_oval(0, 0, r*2, r*2, fill=self.entry_bg, outline=self.entry_bg),
                self.create_oval(w-r*2, 0, w, r*2, fill=self.entry_bg, outline=self.entry_bg),
                self.create_oval(0, h-r*2, r*2, h, fill=self.entry_bg, outline=self.entry_bg),
                self.create_oval(w-r*2, h-r*2, w, h, fill=self.entry_bg, outline=self.entry_bg),
                self.create_rectangle(r, 0, w-r, h, fill=self.entry_bg, outline=self.entry_bg),
                self.create_rectangle(0, r, w, h-r, fill=self.entry_bg, outline=self.entry_bg),
            ]
            self.text_item = self.create_text(10, h/2, text=self.textvariable.get(), fill=self.fg, font=self.font, anchor="w")
            self.arrow_item = self.create_text(w-12, h/2, text="▾", fill=self.fg, font=self.font, anchor="center")
        else:
            for item in self.shape_items:
                self.itemconfig(item, fill=self.entry_bg, outline=self.entry_bg)
            self.itemconfig(self.text_item, text=self.textvariable.get(), fill=self.fg, font=self.font)
            self.itemconfig(self.arrow_item, fill=self.fg, font=self.font)

    def _build_menu(self):
        self.menu = tk.Menu(self, tearoff=0, bg=self.entry_bg, fg=self.fg, font=self.font, activebackground="#353535", activeforeground="#ffffff", bd=0)
        for val in self.values:
            self.menu.add_command(label=val, command=lambda v=val: self.set_value(v))

    def show_menu(self, event):
        if self.menu is None:
            self._build_menu()
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        self.menu.post(x, y)

    def set_value(self, value):
        self.textvariable.set(value)
        self.draw_combo()
        if self.command:
            self.command(None)

    def update_colors(self, bg, fg, entry_bg):
        self.config(bg=bg)
        self.fg = fg
        self.entry_bg = entry_bg
        self.draw_combo()
        if self.menu is not None:
            self.menu.config(bg=self.entry_bg, fg=self.fg, activebackground="#353535", activeforeground="#ffffff")


class AutoClickerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        
        self.base_width = 510         
        self.fixed_height = None
        
        self.root.geometry(f"{self.base_width}x600")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.clicking = False
        self.program_running = True
        self.listener = None
        self.picking_location = False
        self._pick_listener = None
        self.picking_hotkey = False
        self._hotkey_prev_value = None
        self.settings_visible = True 
        self.accent_color = "#3498db" 
        
        self.timer_remaining_seconds = None
        self.has_timer_finished = False
        self.is_currently_holding = False 

        self.active_run_effective_cps = None
        self.HIGH_SPEED_CPS_THRESHOLD = 100.0
        self._last_values = {}

        self.is_dark_mode = tk.BooleanVar(value=True) 
        self.safety_mode_var = tk.BooleanVar(value=True)
        self.polling_rate_var = tk.IntVar(value=3)

        self.click_mins_var = tk.StringVar(value="0")
        self.click_secs_var = tk.StringVar(value="0")
        self.click_ms_var = tk.StringVar(value="100")
        self.use_cps_var = tk.BooleanVar(value=False)
        self.cps_var = tk.StringVar(value="10")
        self.speed_mode_var = tk.StringVar(value="Normal Click") 
        self.active_time_var = tk.StringVar(value="10")   
        self.wait_time_var = tk.StringVar(value="10")     
        self.action_type_var = tk.StringVar(value="Left Click") 
        self.target_key_var = tk.StringVar(value="1")     
        self.start_key_var = tk.StringVar(value="f8")     
        self.timer_seconds_var = tk.StringVar(value="0")
        self.main_x_var = tk.StringVar(value="0") 
        self.main_y_var = tk.StringVar(value="0") 

        self.main_hold_duration_var = tk.StringVar(value="5.0")
        self.main_hold_wait_var = tk.StringVar(value="2.0")
        self.main_hold_infinite_var = tk.BooleanVar(value=False)

        self.loop_wait_first_var = tk.BooleanVar(value=False)

        self.main_font = ("Segoe UI", 9)
        self._cps_clamp_after_id = None
        self.bold_font = ("Segoe UI", 9, "bold")
        self.title_font = ("Segoe UI", 11, "bold")

        self.letter_jokes = [
            "Oh, are you Einstein or something? That's not a number.",
            "Bro thinks this is an essay. This field wants numbers.",
            "Letters in a number field? Bold strategy, let's see if it pays off.",
            "I've seen calculators cry less than this input just did.",
            "Are you trying to hack the mainframe or just fill in a number?",
            "That's not a number, that's a cry for help.",
            "Nice try, but this box only speaks digits, not poetry.",
            "Did your keyboard have a stroke, or did you mean to type a number?",
            "Congrats, you just invented a new math error.",
            "This isn't Wordle, buddy. Numbers only.",
        ]

        self.minus_jokes = [
            "A negative number here? What are you clicking, backwards in time?",
            "Ah yes, negative speed. Truly a scientific breakthrough.",
            "Are you trying to un-click something that hasn't happened yet?",
            "Negative numbers won't make it click faster, Einstein.",
            "That minus sign is doing more work than your plan ever will.",
            "Sir, this is a clicker, not a time machine.",
            "Bold of you to assume negativity helps anything here.",
            "Even the number knows that's a bad idea.",
            "Minus signs go in math class, not this box.",
            "You can't click less than zero times. Nice try though.",
        ]

        self.zero_jokes = [
            "Zero? So you want it to do... nothing? Bold strategy.",
            "Setting this to zero is basically asking it to retire.",
            "Zero here means it does absolutely nothing, champ.",
            "A zero in this field is just you giving up quietly.",
            "Congrats, you just invented the world's laziest macro.",
            "Zero isn't a speed, it's a cry for help.",
            "At this rate (zero), we'll be here till the heat death of the universe.",
            "Putting a zero here is like ordering food and asking for nothing.",
            "Zero? Are you Einstein, or did you just give up?",
            "That's not a value, that's a shrug in number form.",
        ]

        self.smooth_buttons = []
        self.smooth_entries = []
        self.smooth_combos = []

        self.load_settings() 
        self.polling_level = self.polling_rate_var.get()   # plain int, safe to read from worker threads
        self._polling_confirmed = self.polling_level
        self.create_widgets()
        self.start_keyboard_listener()
        
        self.toggle_speed_mode()
        self.toggle_key_entry()
            
        self.apply_static_layout()

        # --- Lock the mode-dependent Click Speed panel to its tallest state ---
        # interval_frame (Click Speed Configuration) shows/hides its
        # mins/secs/ms row depending on the current mode (e.g. that row
        # disappears entirely in Hold Mode). Left unlocked, that makes the
        # frame shrink or grow as the user changes modes, which shoves
        # everything below it up/down and makes the whole window look like
        # it's resizing. Measure it once in its tallest state, lock it there
        # with pack_propagate(False), then restore whatever mode was
        # actually loaded/selected -- the row disappears into blank space
        # inside its own frame instead of resizing the layout around it.
        # (Click Options doesn't need this: it shares its row with Mode
        # Parameters, which is already a fixed height, so it never moves
        # anything below it.)
        saved_speed_mode = self.speed_mode_var.get()
        saved_use_cps = self.use_cps_var.get()

        self.speed_mode_var.set("Normal Click")
        self.use_cps_var.set(False)
        self.toggle_speed_mode()
        self.root.update_idletasks()

        interval_h = self.interval_frame.winfo_reqheight()
        self.interval_frame.config(height=interval_h)
        self.interval_frame.pack_propagate(False)

        self.speed_mode_var.set(saved_speed_mode)
        self.use_cps_var.set(saved_use_cps)
        self.toggle_speed_mode()
        self.root.update_idletasks()

        # Auto-fit the window to the actual content instead of a hardcoded
        # guess, so removing/adding panels doesn't leave dead space below
        # the last widget (or clip anything if content grows later). A small
        # bottom buffer keeps the last row (the theme/safety checkboxes)
        # from sitting flush against the window edge.
        self.fixed_height = self.left_main_frame.winfo_reqheight() + 10
        self.left_main_frame.config(height=self.fixed_height)
        self.left_main_frame.pack_propagate(False)
        self.root.geometry(f"{self.base_width}x{self.fixed_height}")

        self.apply_theme()

        self.setup_input_guards()

    def create_widgets(self):
        self.main_container_frame = tk.Frame(self.root, bd=0, highlightthickness=0)
        self.main_container_frame.pack(side="top", fill="both", expand=True)

        self.left_main_frame = tk.Frame(self.main_container_frame, bd=0, highlightthickness=0, width=self.base_width)
        self.left_main_frame.pack(side="left", fill="both", expand=False)
        self.left_main_frame.columnconfigure(0, weight=1)

        self.top_frame = tk.Frame(self.left_main_frame, width=self.base_width)
        self.top_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(12, 4))

        self.title_label = tk.Label(self.top_frame, text=f"{APP_NAME.upper()} {APP_VERSION}", font=self.title_font)
        self.title_label.pack(side="left")

        self.settings_btn = SmoothButton(
            self.top_frame, text="⚙️ Settings", font=("Segoe UI", 9, "bold"), 
            width=85, height=24, command=self.toggle_settings_panel_static
        )
        self.settings_btn.pack(side="right")
        self.smooth_buttons.append(self.settings_btn)

        self.interval_frame = tk.LabelFrame(self.left_main_frame, text=" Click Speed Configuration ", font=self.bold_font, padx=10, pady=6)
        self.interval_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=4)

        self.speed_mode_row = tk.Frame(self.interval_frame, bd=0, highlightthickness=0)
        self.speed_mode_row.pack(side="top", fill="x", pady=(0, 6))

        self.speed_combo = SmoothCombobox(self.speed_mode_row, textvariable=self.speed_mode_var, values=["Normal Click", "Loop Macro Mode", "Hold Mode"], width_chars=14, command=self.toggle_speed_mode)
        self.speed_combo.pack(side="left")
        self.smooth_combos.append(self.speed_combo)

        self.computed_delay_var = tk.StringVar(value="")
        self.computed_delay_label = tk.Label(self.speed_mode_row, textvariable=self.computed_delay_var, font=("Segoe UI", 8, "italic"))

        self.speed_time_row = tk.Frame(self.interval_frame, bd=0, highlightthickness=0)
        self.speed_time_row.pack(side="top", fill="x")

        self.click_mins_entry = SmoothEntry(self.speed_time_row, textvariable=self.click_mins_var, width_chars=3)
        self.click_mins_entry.pack(side="left", padx=(0, 3))
        self.smooth_entries.append(self.click_mins_entry)
        self.mins_label = tk.Label(self.speed_time_row, text="mins", font=self.main_font)
        self.mins_label.pack(side="left", padx=(0, 8))

        self.click_secs_entry = SmoothEntry(self.speed_time_row, textvariable=self.click_secs_var, width_chars=3)
        self.click_secs_entry.pack(side="left", padx=(0, 3))
        self.smooth_entries.append(self.click_secs_entry)
        self.secs_label = tk.Label(self.speed_time_row, text="secs", font=self.main_font)
        self.secs_label.pack(side="left", padx=(0, 8))

        self.click_ms_entry = SmoothEntry(self.speed_time_row, textvariable=self.click_ms_var, width_chars=4)
        self.click_ms_entry.pack(side="left", padx=(0, 3))
        self.smooth_entries.append(self.click_ms_entry)
        self.ms_label = tk.Label(self.speed_time_row, text="milliseconds", font=self.main_font)
        self.ms_label.pack(side="left")

        self.cps_row = tk.Frame(self.interval_frame, bd=0, highlightthickness=0)
        self.cps_label = tk.Label(self.cps_row, text="Clicks Per Second:", font=self.main_font)
        self.cps_label.pack(side="left", padx=(0, 6))
        self.cps_entry = SmoothEntry(self.cps_row, textvariable=self.cps_var, width_chars=6)
        self.cps_entry.pack(side="left")
        self.smooth_entries.append(self.cps_entry)

        self.mid_container = tk.Frame(self.left_main_frame)
        self.mid_container.grid(row=2, column=0, sticky="ew", padx=15, pady=4)

        self.options_frame = tk.LabelFrame(self.mid_container, text=" Click Options ", font=self.bold_font, padx=10, pady=6)
        self.options_frame.pack(side="left", fill="both", expand=True, padx=(0,4))

        self.repeat_label = tk.Label(self.options_frame, text="Action:", font=self.main_font)
        self.repeat_label.grid(row=0, column=0, sticky="w", pady=4)

        self.type_combo = SmoothCombobox(self.options_frame, textvariable=self.action_type_var, values=["Left Click", "Right Click", "Keyboard Key"], width_chars=12, command=self.toggle_key_entry)
        self.type_combo.grid(row=0, column=1, sticky="w", padx=4, pady=4)
        self.smooth_combos.append(self.type_combo)

        self.key_entry_label = tk.Label(self.options_frame, text="Key:", font=self.main_font)
        self.key_entry_label.grid(row=1, column=0, sticky="w", pady=4)
        self.key_entry = SmoothEntry(self.options_frame, textvariable=self.target_key_var, width_chars=5)
        self.key_entry.grid(row=1, column=1, sticky="w", padx=4, pady=4)
        self.smooth_entries.append(self.key_entry)

        self.coord_lbl = tk.Label(self.options_frame, text="X/Y:", font=self.main_font)
        self.coord_lbl.grid(row=2, column=0, sticky="w", pady=4)
        self.coord_f = tk.Frame(self.options_frame, bd=0, highlightthickness=0)
        self.coord_f.grid(row=2, column=1, sticky="w", padx=4, pady=4)
        self.mx_e = SmoothEntry(self.coord_f, textvariable=self.main_x_var, width_chars=4)
        self.mx_e.pack(side="left")
        self.my_e = SmoothEntry(self.coord_f, textvariable=self.main_y_var, width_chars=4)
        self.my_e.pack(side="left", padx=(4,0))
        self.smooth_entries.extend([self.mx_e, self.my_e])

        self.coord_btn_row = tk.Frame(self.options_frame, bd=0, highlightthickness=0)
        self.coord_btn_row.grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, 2))

        self.pick_location_btn = SmoothButton(self.coord_btn_row, text="Pick Coordinates", font=self.bold_font, width=118, height=22, command=self.start_pick_location)
        self.pick_location_btn.pack(side="left")
        self.smooth_buttons.append(self.pick_location_btn)

        self.reset_coords_btn = SmoothButton(self.coord_btn_row, text="Reset", font=self.bold_font, width=50, height=22, command=self.reset_coordinates)
        self.reset_coords_btn.pack(side="left", padx=(4, 0))
        self.smooth_buttons.append(self.reset_coords_btn)

        self.loop_frame = tk.LabelFrame(self.mid_container, text=" Mode Parameters ", font=self.bold_font, padx=10, pady=6)
        self.loop_frame.pack(side="right", fill="both", expand=True, padx=(4,0))
        self.loop_frame.grid_propagate(False)
        self.loop_frame.config(width=230, height=155)

        self.active_label = tk.Label(self.loop_frame, text="Active (s):", font=self.main_font)
        self.active_entry = SmoothEntry(self.loop_frame, textvariable=self.active_time_var, width_chars=5)
        self.wait_label = tk.Label(self.loop_frame, text="Wait (s):", font=self.main_font)
        self.wait_entry = SmoothEntry(self.loop_frame, textvariable=self.wait_time_var, width_chars=5)
        self.smooth_entries.extend([self.active_entry, self.wait_entry])

        self.chk_loop_wait_first = tk.Checkbutton(self.loop_frame, text="Wait First", variable=self.loop_wait_first_var, command=self.on_toggle_loop_wait_first, font=self.main_font)

        self.main_hold_lbl1 = tk.Label(self.loop_frame, text="Hold (s):", font=self.main_font)
        self.main_hold_ent1 = SmoothEntry(self.loop_frame, textvariable=self.main_hold_duration_var, width_chars=5)
        self.main_hold_lbl2 = tk.Label(self.loop_frame, text="Wait (s):", font=self.main_font)
        self.main_hold_ent2 = SmoothEntry(self.loop_frame, textvariable=self.main_hold_wait_var, width_chars=5)
        self.smooth_entries.extend([self.main_hold_ent1, self.main_hold_ent2])

        self.chk_hold_infinite = tk.Checkbutton(self.loop_frame, text="∞ Infinite", variable=self.main_hold_infinite_var, command=self.toggle_main_hold_infinite, font=self.main_font)

        self.hold_infinite_label = tk.Label(self.loop_frame, text="Holding infinitely...", font=self.bold_font)

        self.chk_use_cps = tk.Checkbutton(self.loop_frame, text="Use CPS instead", variable=self.use_cps_var, command=self.toggle_speed_mode, font=self.main_font)

        # Control Configuration Frame
        self.control_frame = tk.LabelFrame(self.left_main_frame, text=" Hotkey & Timer Configuration ", font=self.bold_font, padx=10, pady=6)
        self.control_frame.grid(row=3, column=0, sticky="ew", padx=15, pady=4)

        self.hk_label = tk.Label(self.control_frame, text="Hotkey:", font=self.main_font)
        self.hk_label.grid(row=0, column=0, sticky="w", pady=4)
        self.hk_entry = SmoothEntry(self.control_frame, textvariable=self.start_key_var, width_chars=6)
        self.hk_entry.grid(row=0, column=1, sticky="w", padx=4, pady=4)
        self.smooth_entries.append(self.hk_entry)
        self.hk_entry.entry.config(cursor="hand2", state="readonly", readonlybackground=self.hk_entry.entry.cget("bg"))
        self.hk_entry.entry.bind("<Button-1>", lambda e: self.start_pick_hotkey())
        self.hk_entry.bind("<Button-1>", lambda e: self.start_pick_hotkey())

        self.timer_label = tk.Label(self.control_frame, text="Timer (s, 0=∞):", font=self.main_font)
        self.timer_label.grid(row=0, column=2, sticky="w", padx=(10,2), pady=4)
        self.timer_entry = SmoothEntry(self.control_frame, textvariable=self.timer_seconds_var, width_chars=5)
        self.timer_entry.grid(row=0, column=3, sticky="w", padx=4, pady=4)
        self.smooth_entries.append(self.timer_entry)

        self.buttons_frame = tk.Frame(self.left_main_frame)
        self.buttons_frame.grid(row=4, column=0, sticky="ew", padx=15, pady=(6, 10))

        self.start_btn = SmoothButton(self.buttons_frame, text="START (F8)", font=self.bold_font, width=110, height=30, command=self.toggle_clicking)
        self.start_btn.pack(side="left", padx=2)
        self.smooth_buttons.append(self.start_btn)

        self.status_label = tk.Label(self.buttons_frame, text="STATUS: IDLE", font=self.bold_font, fg="#95a5a6")
        self.status_label.pack(side="left", padx=10)

        self.help_btn = SmoothButton(self.buttons_frame, text="?", font=self.bold_font, width=26, height=26, radius=13, command=self.show_help_guide)
        self.help_btn.pack(side="right", padx=2)
        self.smooth_buttons.append(self.help_btn)

        self.settings_lower_panel = tk.Frame(self.left_main_frame, bd=0, highlightthickness=0)

        self.st_sep = tk.Frame(self.settings_lower_panel, height=1, bg="#2a2a2a")
        self.st_sep.pack(fill="x", padx=15, pady=(2, 6))

        self.st_container = tk.Frame(self.settings_lower_panel)
        self.st_container.pack(fill="x", padx=15, pady=(0, 8))
        for c in range(4):
            self.st_container.columnconfigure(c, weight=1, uniform="settings_col")

        self.chk_dark = tk.Checkbutton(self.st_container, text="Dark Theme", variable=self.is_dark_mode, command=self.apply_theme, font=self.main_font)
        self.chk_dark.grid(row=0, column=0, sticky="w", padx=4, pady=2)

        self.chk_safety = tk.Checkbutton(self.st_container, text="Safety Mode", variable=self.safety_mode_var, command=self.toggle_safety_mode, font=self.main_font)
        self.chk_safety.grid(row=0, column=1, sticky="w", padx=4, pady=2)

        # --- Polling Rate slider ---
        self.polling_frame = tk.Frame(self.st_container, bd=0, highlightthickness=0)
        self.polling_frame.grid(row=1, column=0, columnspan=4, sticky="ew", padx=4, pady=(6, 2))

        self.polling_label = tk.Label(self.polling_frame, text="Polling Rate:", font=self.main_font)
        self.polling_label.pack(side="left")

        self.polling_scale = tk.Scale(
            self.polling_frame, from_=1, to=5, orient="horizontal",
            variable=self.polling_rate_var, showvalue=False,
            length=150, sliderlength=16, width=12, bd=0, highlightthickness=0,
            command=self.on_polling_change
        )
        self.polling_scale.pack(side="left", padx=8)
        self.polling_scale.bind("<ButtonRelease-1>", self.on_polling_release)
        self.polling_scale.bind("<KeyRelease>", self.on_polling_release)

        self.polling_value_label = tk.Label(self.polling_frame, text="", font=self.bold_font)
        self.polling_value_label.pack(side="left")

    def toggle_settings_panel_static(self):
        if self.settings_visible:
            self.settings_lower_panel.grid_forget()
            self.settings_visible = False
        else:
            self.apply_static_layout()
            self.settings_visible = True

    def apply_static_layout(self):
        self.settings_lower_panel.grid(row=5, column=0, sticky="ew", padx=0, pady=2)
        self.settings_visible = True

    def is_running_at_high_speed(self):
        return (
            self.clicking
            and self.active_run_effective_cps is not None
            and self.active_run_effective_cps >= self.HIGH_SPEED_CPS_THRESHOLD
        )

    def _guard_var_or_revert(self, var, key):
        last = self._last_values.get(key, var.get())
        if var.get() != last and self.is_running_at_high_speed():
            var.set(last)
            self.warn_change_blocked()
            return True
        self._last_values[key] = var.get()
        return False

    def warn_change_blocked(self):
        messagebox.showwarning(
            "Autoclicker Running",
            "Stop the autoclicker first before changing settings.\n\n"
            "You're running at a high speed (10ms delay / 100+ CPS or faster) "
            "and changing values mid-run can cause glitchy or inconsistent behavior."
        )

    def show_input_joke(self, category="letter"):
        pool = {
            "letter": self.letter_jokes,
            "minus": self.minus_jokes,
            "zero": self.zero_jokes,
        }.get(category, self.letter_jokes)
        joke = random.choice(pool)
        messagebox.showwarning("Really?", joke)

    def attach_numeric_guard(self, var, allow_zero=True, allow_negative=False, zero_callback=None, allow_decimal=True, guard_while_running=False):
        state = {"updating": False, "last": var.get()}

        def on_change(*args):
            if state["updating"]:
                return
            val = var.get()

            if guard_while_running and val != state["last"] and self.is_running_at_high_speed():
                state["updating"] = True
                var.set(state["last"])
                state["updating"] = False
                self.warn_change_blocked()
                return

            if val == "" or val == "-":
                state["last"] = val
                return

            is_negative = val.startswith("-")
            cleaned = val[1:] if is_negative else val
            digits_only = cleaned.replace(".", "", 1) if allow_decimal else cleaned
            has_bad_decimal = (not allow_decimal) and ("." in cleaned)
            is_valid_shape = (not has_bad_decimal) and (digits_only.isdigit() or digits_only == "") and len(digits_only) <= 9

            if is_negative and not allow_negative:
                state["updating"] = True
                var.set(state["last"])
                state["updating"] = False
                self.show_input_joke("minus")
                return

            if not is_valid_shape:
                state["updating"] = True
                var.set(state["last"])
                state["updating"] = False
                self.show_input_joke("letter")
                return

            state["last"] = val

            if not allow_zero:
                try:
                    if float(val) == 0:
                        def _confirm_zero(v=var, expected=val):
                            if v.get() != expected:
                                return
                            if zero_callback:
                                zero_callback()
                            else:
                                state["updating"] = True
                                v.set("1")
                                state["updating"] = False
                                self.show_input_joke("zero")
                        self.root.after(5000, _confirm_zero)
                except:
                    pass

        var.trace_add("write", on_change)

    def play_alarm(self):
        try:
            winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        except:
            pass

    def show_help_guide(self):
        win = tk.Toplevel(self.root)
        win.title("How Everything Works")
        win.geometry("480x580")
        win.transient(self.root)

        is_dark = self.is_dark_mode.get()
        bg = "#121212" if is_dark else "#f4f4f4"
        fg = "#ffffff" if is_dark else "#1a1a1a"
        win.config(bg=bg)

        frame = tk.Frame(win, bg=bg)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")

        text = tk.Text(frame, wrap="word", yscrollcommand=scrollbar.set,
                        bg="#1e1e1e" if is_dark else "#ffffff", fg=fg,
                        insertbackground=fg, bd=0, highlightthickness=0,
                        font=("Segoe UI", 9), padx=10, pady=10)
        text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=text.yview)

        guide = (
"DYNAMIC MACRO ENGINE — HOW IT WORKS\n\n"
"CLICK SPEED CONFIGURATION\n"
"Set the delay between clicks using mins / secs / milliseconds. "
"The mode dropdown controls how that delay is used:\n\n"
"  Normal Click — clicks repeatedly, waiting the configured delay "
"between each click, for as long as you leave it running.\n\n"
"  Loop Macro Mode — clicks repeatedly using the same delay, but only "
"for the 'Active (s)' duration, then pauses for 'Wait (s)', then "
"repeats that cycle for as long as it's running. Check 'Wait First' "
"to flip the order of the very first cycle so it waits 'Wait (s)' "
"before its first burst of clicks, instead of clicking first.\n\n"
"  Hold Mode — presses and holds the button/key down instead of "
"clicking repeatedly. 'Hold (s)' controls how long it stays held, "
"'Wait (s)' controls the pause before it holds again. Check "
"'Infinite' to just hold down with no release until you stop it.\n\n"
"USE CPS INSTEAD\n"
"Shown in Mode Parameters for Normal Click and Loop Macro Mode. When "
"checked, the mins/secs/milliseconds fields are replaced with a "
"single Clicks Per Second value — set how many clicks you want per "
"second instead of the delay between them.\n\n"
"CLICK OPTIONS\n"
"Action picks what gets pressed: Left Click, Right Click, or a "
"Keyboard Key. For Keyboard Key, you can type a single key name "
"(like 'space', 'f5', 'a') or multiple letters to type as a full "
"word/sequence.\n\n"
"X/Y are the screen coordinates clicks are sent to. Leave both at 0 "
"to click wherever your cursor already is instead of a fixed spot. "
"'Pick Coordinates' lets you click anywhere on screen to capture its "
"position automatically. 'Reset' sets X/Y back to 0.\n\n"
"HOTKEY & TIMER CONFIGURATION\n"
"Hotkey is the key that starts/stops clicking from anywhere, even "
"outside this window. Click the Hotkey box, then press the key you "
"want to use — it gets captured automatically. Press Escape while "
"capturing to cancel and keep the old hotkey. Timer (s) automatically "
"stops clicking after that many seconds — 0 means it runs until you "
"stop it manually. When a Timer run finishes on its own, an alarm "
"sound plays.\n\n"
"SETTINGS\n"
"Dark Theme switches the color scheme.\n\n"
"Safety Mode caps clicking at 100 CPS / 10ms delay to protect your "
"system. You'll be asked before it's turned off if you start above "
"that limit.\n\n"
"Polling Rate (1-5) controls how precisely the click timing is "
"kept. Low levels mostly sleep between clicks, which is light on "
"your CPU but slightly less accurate. Higher levels spend more of "
"each delay actively spinning the CPU for tighter timing.\n\n"
"  1 — Lowest CPU use, least accurate.\n"
"  2 — Light.\n"
"  3 — Balanced (default).\n"
"  4 — High accuracy, noticeably more CPU use.\n"
"  5 — Maximum accuracy. Busy-waits the entire delay, so it uses the "
"most CPU and can make your PC, this window, and your games feel "
"laggy.\n\n"
"Levels 4 and 5 are meant for good/high-end PCs only, and you'll "
"get a warning when you switch to them. Hold Mode also checks the "
"key/button state faster at higher levels."
        )

        text.insert("1.0", guide)
        text.config(state="disabled")

        close_btn = SmoothButton(win, text="Close", font=self.bold_font, width=90, height=28, command=win.destroy)
        close_btn.pack(pady=(0, 10))
        close_btn.update_colors(bg, fg, "#252525" if is_dark else "#e0e0e0", "#353535" if is_dark else "#d0d0d0")

    def update_start_button_label(self, *args):
        if self.clicking:
            return
        hk = self.start_key_var.get().strip().upper()
        self.start_btn.text = f"START ({hk})" if hk else "START"
        self.start_btn.draw_button()

    def debounce_cps_safety_clamp(self, *args):
        if not self.safety_mode_var.get():
            return
        if self._cps_clamp_after_id:
            try: self.root.after_cancel(self._cps_clamp_after_id)
            except: pass
        self._cps_clamp_after_id = self.root.after(600, self._apply_cps_safety_clamp)

    def _apply_cps_safety_clamp(self):
        self._cps_clamp_after_id = None
        if not self.safety_mode_var.get():
            return
        try:
            if float(self.cps_var.get()) > 100:
                self.cps_var.set("100")
        except:
            pass

    def check_safety_clamp_before_start(self):
        if not self.safety_mode_var.get():
            return True

        if self.use_cps_var.get():
            try:
                cps = float(self.cps_var.get())
            except:
                cps = 10.0
            if cps > 100:
                proceed = messagebox.askyesno(
                    "Safety Mode Warning",
                    f"You're starting at {cps:g} clicks per second, above Safety Mode's 100 CPS cap.\n\n"
                    "Very high click speeds can also cause system lag, an unresponsive UI, "
                    "or performance issues in some games/programs.\n\n"
                    "Disable Safety Mode and start at the higher speed anyway?"
                )
                if proceed:
                    self.safety_mode_var.set(False)
                else:
                    return False
        else:
            try:
                mins = float(self.click_mins_var.get() or "0")
                secs = float(self.click_secs_var.get() or "0")
                ms = float(self.click_ms_var.get() or "0")
            except:
                mins, secs, ms = 0, 0, 100
            total = mins * 60.0 + secs + ms / 1000.0
            if 0 < total < 0.01:
                ms_display = f"{total * 1000:.3f}".rstrip("0").rstrip(".")
                proceed = messagebox.askyesno(
                    "Safety Mode Warning",
                    f"You're starting at a click delay of {ms_display}ms, under Safety Mode's 10ms minimum.\n\n"
                    "Very high click speeds can also cause system lag, an unresponsive UI, "
                    "or performance issues in some games/programs.\n\n"
                    "Disable Safety Mode and start at the faster speed anyway?"
                )
                if proceed:
                    self.safety_mode_var.set(False)
                else:
                    return False

        self.update_computed_delay_display()
        return True

    def update_polling_label(self):
        lvl = self.polling_rate_var.get()
        self.polling_value_label.config(
            text=POLLING_NAMES.get(lvl, str(lvl)),
            fg="#e67e22" if lvl >= 4 else self.polling_label.cget("fg")
        )

    def on_polling_change(self, value=None):
        self.polling_level = max(1, min(5, self.polling_rate_var.get()))
        self.update_polling_label()

    def on_polling_release(self, event=None):
        lvl = self.polling_rate_var.get()
        if lvl >= 4 and lvl > self._polling_confirmed:
            ok = messagebox.askyesno(
                "High Polling Rate",
                f"Polling Rate {lvl} gives more accurate click timing, but it uses a lot more CPU "
                "and can make your PC, this window, and your games feel much laggier.\n\n"
                "This is meant for good/high-end PCs only.\n\n"
                "Use this polling rate anyway?"
            )
            if not ok:
                self.polling_rate_var.set(self._polling_confirmed)
                self.on_polling_change()
                return
        self._polling_confirmed = lvl
        self.on_polling_change()

    def toggle_safety_mode(self):
        self.update_computed_delay_display()
        if self.safety_mode_var.get():
            try:
                if float(self.cps_var.get()) > 100:
                    self.cps_var.set("100")
            except:
                pass

    def reset_coordinates(self):
        self.main_x_var.set("0")
        self.main_y_var.set("0")

    def start_pick_location(self):
        if self.picking_location:
            return
        if self.is_running_at_high_speed():
            self.warn_change_blocked()
            return
        self.picking_location = True
        self.pick_location_btn.text = "Click anywhere..."
        self.pick_location_btn.draw_button()

        self.root.withdraw()
        self.root.after(300, self._begin_pick_listener)

    def _begin_pick_listener(self):
        def on_click(x, y, button, pressed):
            if button == pynput_mouse.Button.left and pressed:
                self.root.after(0, lambda: self._finish_pick_location(x, y))
                return False

        listener = pynput_mouse.Listener(on_click=on_click)
        listener.daemon = True
        listener.start()
        self._pick_listener = listener

    def _finish_pick_location(self, x, y):
        self.main_x_var.set(str(int(x)))
        self.main_y_var.set(str(int(y)))

        self.picking_location = False
        self._pick_listener = None
        self.pick_location_btn.text = "Pick Coordinates"
        self.pick_location_btn.draw_button()

        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def toggle_speed_mode(self, event=None):
        blocked_mode = self._guard_var_or_revert(self.speed_mode_var, "speed_mode")
        blocked_cps = self._guard_var_or_revert(self.use_cps_var, "use_cps")
        if blocked_mode:
            self.speed_combo.draw_combo()
        if blocked_mode or blocked_cps:
            return
        m = self.speed_mode_var.get()
        self.active_label.grid_forget()
        self.active_entry.grid_forget()
        self.wait_label.grid_forget()
        self.wait_entry.grid_forget()
        self.chk_loop_wait_first.grid_forget()
        self.main_hold_lbl1.grid_forget()
        self.main_hold_ent1.grid_forget()
        self.main_hold_lbl2.grid_forget()
        self.main_hold_ent2.grid_forget()
        self.chk_hold_infinite.grid_forget()
        self.hold_infinite_label.grid_forget()
        self.chk_use_cps.grid_forget()
        self.speed_time_row.pack_forget()
        self.cps_row.pack_forget()
        self.computed_delay_label.pack_forget()

        if m == "Normal Click":
            self.chk_use_cps.grid(row=0, column=0, columnspan=2, sticky="w", pady=4, padx=4)
        elif m == "Loop Macro Mode":
            self.active_label.grid(row=0, column=0, sticky="w", pady=4, padx=4)
            self.active_entry.grid(row=0, column=1, sticky="w", pady=4)
            self.wait_label.grid(row=1, column=0, sticky="w", pady=4, padx=4)
            self.wait_entry.grid(row=1, column=1, sticky="w", pady=4)
            self.chk_loop_wait_first.grid(row=2, column=0, columnspan=2, sticky="w", pady=4, padx=4)
            self.chk_use_cps.grid(row=3, column=0, columnspan=2, sticky="w", pady=4, padx=4)

        if m in ("Normal Click", "Loop Macro Mode"):
            if self.use_cps_var.get():
                self.cps_row.pack(side="top", fill="x", after=self.speed_mode_row)
            else:
                self.speed_time_row.pack(side="top", fill="x", after=self.speed_mode_row)
            self.computed_delay_label.pack(side="left", padx=10)
        else:
            self.chk_hold_infinite.grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))
            self.toggle_main_hold_infinite()

    def get_raw_delay_seconds(self):
        if self.use_cps_var.get():
            try:
                cps = float(self.cps_var.get())
                if cps <= 0:
                    raise ValueError
            except:
                cps = 10.0
            if self.safety_mode_var.get() and cps > 100:
                cps = 100.0
            return 1.0 / cps
        else:
            try:
                mins = float(self.click_mins_var.get() or "0")
                secs = float(self.click_secs_var.get() or "0")
                ms = float(self.click_ms_var.get() or "0")
            except:
                mins, secs, ms = 0, 0, 100
            total = (mins * 60.0) + secs + (ms / 1000.0)
            if self.safety_mode_var.get() and 0 < total < 0.01:
                total = 0.01
            return total

    def get_click_delay_seconds(self):
        total = self.get_raw_delay_seconds()
        if total < 0.00005:
            total = 0.00005
        return total

    def update_computed_delay_display(self, *args):
        total = self.get_raw_delay_seconds()
        m = int(total // 60)
        s = int(total % 60)
        ms = (total - int(total)) * 1000
        parts = []
        if m: parts.append(f"{m}m")
        if s: parts.append(f"{s}s")
        if ms:
            ms_str = f"{ms:.3f}".rstrip("0").rstrip(".")
            parts.append(f"{ms_str}ms")
        if not parts: parts = ["0ms"]
        self.computed_delay_var.set("= " + " ".join(parts) + " per click")

    def toggle_main_hold_infinite(self):
        if self.speed_mode_var.get() != "Hold Mode":
            return
        if self._guard_var_or_revert(self.main_hold_infinite_var, "hold_infinite"):
            return
        self.main_hold_lbl1.grid_forget()
        self.main_hold_ent1.grid_forget()
        self.main_hold_lbl2.grid_forget()
        self.main_hold_ent2.grid_forget()
        self.hold_infinite_label.grid_forget()

        if self.main_hold_infinite_var.get():
            self.hold_infinite_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=4, padx=4)
        else:
            self.main_hold_lbl1.grid(row=0, column=0, sticky="w", pady=4, padx=4)
            self.main_hold_ent1.grid(row=0, column=1, sticky="w", pady=4)
            self.main_hold_lbl2.grid(row=1, column=0, sticky="w", pady=4, padx=4)
            self.main_hold_ent2.grid(row=1, column=1, sticky="w", pady=4)

    def activate_infinite_from_wait_zero(self):
        if not self.main_hold_infinite_var.get():
            self.main_hold_infinite_var.set(True)
            self.main_hold_wait_var.set("2.0")
            self.toggle_main_hold_infinite()

    def on_toggle_loop_wait_first(self):
        self._guard_var_or_revert(self.loop_wait_first_var, "loop_wait_first")

    def toggle_key_entry(self, event=None):
        if self._guard_var_or_revert(self.action_type_var, "action_type"):
            self.type_combo.draw_combo()
            return
        act = self.action_type_var.get()
        if act == "Keyboard Key":
            self.key_entry_label.grid(row=1, column=0, sticky="w", pady=4)
            self.key_entry.grid(row=1, column=1, sticky="w", padx=4, pady=4)
        else:
            self.key_entry_label.grid_forget()
            self.key_entry.grid_forget()

    def _parse_coord(self, s):
        s = (s or "").strip()
        if not s:
            return 0
        try:
            return int(round(float(s)))
        except:
            return 0

    def execute_native_action(self, act_type, target_key, x_str, y_str, is_hold_release=False, is_hold_press=False):
        x, y = self._parse_coord(x_str), self._parse_coord(y_str)

        if x != 0 or y != 0:
            if win32api_available:
                try: win32api.SetCursorPos((x, y))
                except: user32.SetCursorPos(x, y)
            else:
                user32.SetCursorPos(x, y)

        if act_type == "Left Click":
            if is_hold_press:
                try: win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                except: user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            elif is_hold_release:
                try: win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                except: user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            else:
                try:
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                except:
                    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

        elif act_type == "Right Click":
            if is_hold_press:
                try: win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                except: user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            elif is_hold_release:
                try: win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
                except: user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
            else:
                try:
                    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
                except:
                    user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                    user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)

        elif act_type == "Keyboard Key":
            k = target_key.strip()
            k_lower = k.lower()
            vk = VK_CODES.get(k_lower, None)
            if vk is None and len(k_lower) == 1:
                vk = ord(k_lower.upper()) if k_lower.isalpha() else ord(k_lower)

            if vk:
                if is_hold_press:
                    send_scancode_key(vk, key_up=False)
                elif is_hold_release:
                    send_scancode_key(vk, key_up=True)
                else:
                    send_scancode_key(vk, key_up=False)
                    time.sleep(0.01)
                    send_scancode_key(vk, key_up=True)
            elif len(k) > 1 and not is_hold_press and not is_hold_release:
                self.type_string(k)

    def type_string(self, s):
        for ch in s:
            ch_lower = ch.lower()
            vk = VK_CODES.get(ch_lower, None)
            if vk is None:
                if ch == " ":
                    vk = VK_CODES.get("space")
                elif ch_lower.isalpha():
                    vk = ord(ch_lower.upper())
                elif ch.isdigit():
                    vk = ord(ch)
                else:
                    continue
            send_scancode_key(vk, key_up=False)
            time.sleep(0.015)
            send_scancode_key(vk, key_up=True)
            time.sleep(0.015)

    def release_native_action(self, act_type, target_key, x_str="0", y_str="0"):
        if act_type == "Left Click":
            try: win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            except: user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        elif act_type == "Right Click":
            try: win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
            except: user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        elif act_type == "Keyboard Key":
            k = target_key.lower()
            vk = VK_CODES.get(k, None)
            if vk is None and len(k) == 1: vk = ord(k)
            if vk:
                send_scancode_key(vk, key_up=True)

    def toggle_clicking(self):
        if self.clicking:
            self.clicking = False
            self.active_run_effective_cps = None
            self.status_label.config(text="STATUS: IDLE", fg="#95a5a6")
            self.update_start_button_label()
            if self.is_currently_holding:
                self.release_native_action(self.action_type_var.get(), self.target_key_var.get().strip(), self.main_x_var.get().strip(), self.main_y_var.get().strip())
                self.is_currently_holding = False
        else:
            if not self.check_safety_clamp_before_start():
                return

            d = self.get_click_delay_seconds()

            if self.speed_mode_var.get() == "Hold Mode":
                self.active_run_effective_cps = None
            else:
                raw_d = self.get_raw_delay_seconds()
                self.active_run_effective_cps = (1.0 / raw_d) if raw_d > 0 else float("inf")

            self.clicking = True
            self.status_label.config(text="STATUS: ACTIVE", fg=self.accent_color)
            self.start_btn.text = "STOP"
            self.start_btn.draw_button()
            
            self.has_timer_finished = False
            try: t_sec = float(self.timer_seconds_var.get())
            except: t_sec = 0.0
            
            if t_sec > 0:
                self.timer_remaining_seconds = t_sec
                threading.Thread(target=self.main_timer_countdown_thread, daemon=True).start()
            else:
                self.timer_remaining_seconds = None

            m = self.speed_mode_var.get()
            act_type = self.action_type_var.get()
            tgt_key = self.target_key_var.get().strip()
            x_str = self.main_x_var.get().strip()
            y_str = self.main_y_var.get().strip()

            first_click_target = time.perf_counter() + d

            if m == "Normal Click":
                threading.Thread(target=self.normal_click_worker, args=(d, act_type, tgt_key, x_str, y_str, first_click_target), daemon=True).start()
            elif m == "Loop Macro Mode":
                threading.Thread(target=self.loop_macro_worker, args=(d, act_type, tgt_key, x_str, y_str, first_click_target), daemon=True).start()
            elif m == "Hold Mode":
                threading.Thread(target=self.hold_mode_worker, args=(act_type, tgt_key, x_str, y_str), daemon=True).start()

    def main_timer_countdown_thread(self):
        while self.clicking and self.timer_remaining_seconds is not None and self.timer_remaining_seconds > 0:
            time.sleep(0.05)
            self.timer_remaining_seconds -= 0.05
        if self.clicking and self.timer_remaining_seconds is not None and self.timer_remaining_seconds <= 0:
            self.has_timer_finished = True
            self.root.after(0, self.toggle_clicking)
            threading.Thread(target=self.play_alarm, daemon=True).start()

    def precise_sleep(self, seconds):
        if seconds <= 0:
            return
        spin, _ = POLLING_LEVELS.get(self.polling_level, POLLING_LEVELS[3])
        target = time.perf_counter() + seconds
        if spin is None:                      # level 5: pure busy-wait
            while time.perf_counter() < target:
                pass
            return
        coarse = seconds - spin
        if coarse > 0:
            time.sleep(coarse)
        while time.perf_counter() < target:
            pass

    def precise_sleep_until(self, target_time):
        remaining = target_time - time.perf_counter()
        if remaining <= 0:
            return
        spin, _ = POLLING_LEVELS.get(self.polling_level, POLLING_LEVELS[3])
        if spin is not None:
            coarse = remaining - spin
            if coarse > 0:
                time.sleep(coarse)
        while time.perf_counter() < target_time:
            pass

    def normal_click_worker(self, base_delay, act_type, tgt_key, x_str, y_str, first_click_target=None):
        first = True
        while self.clicking:
            if self.has_timer_finished: break
            d = base_delay

            if first and first_click_target is not None:
                self.precise_sleep_until(first_click_target)
                first = False
            else:
                self.precise_sleep(d)
            if not self.clicking or self.has_timer_finished: break

            self.execute_native_action(act_type, tgt_key, x_str, y_str)

    def loop_macro_worker(self, click_interval, act_type, tgt_key, x_str, y_str, first_click_target=None):
        try:
            act_t = float(self.active_time_var.get())
            wt_t = float(self.wait_time_var.get())
        except:
            act_t, wt_t = 5.0, 5.0

        wait_first = self.loop_wait_first_var.get()
        first = True

        def do_active_phase():
            nonlocal first
            start_act = time.perf_counter()
            while self.clicking and (time.perf_counter() - start_act < act_t):
                if self.has_timer_finished: break
                d = click_interval
                if d < 0.00005: d = 0.00005

                if first and first_click_target is not None:
                    self.precise_sleep_until(first_click_target)
                    first = False
                else:
                    self.precise_sleep(d)
                if not self.clicking or self.has_timer_finished: break

                self.execute_native_action(act_type, tgt_key, x_str, y_str)

        def do_wait_phase():
            start_wait = time.perf_counter()
            while self.clicking and (time.perf_counter() - start_wait < wt_t):
                if self.has_timer_finished: break
                time.sleep(0.02)

        while self.clicking:
            if wait_first:
                do_wait_phase()
                if not self.clicking or self.has_timer_finished: break
                do_active_phase()
            else:
                do_active_phase()
                if not self.clicking or self.has_timer_finished: break
                do_wait_phase()

            if not self.clicking or self.has_timer_finished: break

    def hold_mode_worker(self, act_type, tgt_key, x_str, y_str):
        is_kb = act_type == "Keyboard Key"
        repeat_interval = 0.03

        press_x, press_y = x_str, y_str

        if self.main_hold_infinite_var.get():
            self.is_currently_holding = True
            self.execute_native_action(act_type, tgt_key, press_x, press_y, is_hold_press=True)
            last_repeat = time.perf_counter()
            while self.clicking:
                if self.has_timer_finished: break
                if is_kb and (time.perf_counter() - last_repeat >= repeat_interval):
                    self.execute_native_action(act_type, tgt_key, press_x, press_y, is_hold_press=True)
                    last_repeat = time.perf_counter()
                time.sleep(POLLING_LEVELS.get(self.polling_level, POLLING_LEVELS[3])[1])
            self.release_native_action(act_type, tgt_key, press_x, press_y)
            self.is_currently_holding = False
            return

        try:
            h_dur = float(self.main_hold_duration_var.get())
            w_dur = float(self.main_hold_wait_var.get())
        except:
            h_dur, w_dur = 5.0, 2.0

        while self.clicking:
            if self.has_timer_finished: break

            self.is_currently_holding = True
            self.execute_native_action(act_type, tgt_key, press_x, press_y, is_hold_press=True)
            
            hold_start = time.perf_counter()
            last_repeat = hold_start
            while self.clicking and (time.perf_counter() - hold_start < h_dur):
                if self.has_timer_finished: break
                if is_kb and (time.perf_counter() - last_repeat >= repeat_interval):
                    self.execute_native_action(act_type, tgt_key, press_x, press_y, is_hold_press=True)
                    last_repeat = time.perf_counter()
                time.sleep(POLLING_LEVELS.get(self.polling_level, POLLING_LEVELS[3])[1])
            
            self.release_native_action(act_type, tgt_key, press_x, press_y)
            self.is_currently_holding = False
            
            if not self.clicking or self.has_timer_finished: break
            
            wait_start = time.perf_counter()
            while self.clicking and (time.perf_counter() - wait_start < w_dur):
                if self.has_timer_finished: break
                time.sleep(0.01)

    def start_keyboard_listener(self):
        self.listener = Listener(on_press=self.on_key_press)
        self.listener.daemon = True
        self.listener.start()

    def on_key_press(self, key):
        try:
            pressed_str = ""
            if isinstance(key, KeyCode):
                if key.char: pressed_str = key.char.lower()
            else:
                pressed_str = key.name.lower()

            if self.picking_hotkey:
                if pressed_str == "esc":
                    self.root.after(0, self._cancel_pick_hotkey)
                elif pressed_str:
                    self.root.after(0, lambda k=pressed_str: self._finish_pick_hotkey(k))
                return

            hk = self.start_key_var.get().strip().lower()
            if not hk: return

            if pressed_str == hk:
                self.root.after(0, self.toggle_clicking)
        except:
            pass

    def start_pick_hotkey(self):
        if self.picking_hotkey:
            return
        if self.is_running_at_high_speed():
            self.warn_change_blocked()
            return
        self.picking_hotkey = True
        self._hotkey_prev_value = self.start_key_var.get()
        self.start_key_var.set("...")

    def _finish_pick_hotkey(self, key_str):
        self.picking_hotkey = False
        self._hotkey_prev_value = None
        self.start_key_var.set(key_str)

    def _cancel_pick_hotkey(self):
        self.picking_hotkey = False
        if self._hotkey_prev_value is not None:
            self.start_key_var.set(self._hotkey_prev_value)
        self._hotkey_prev_value = None

    def apply_theme(self):
        is_dark = self.is_dark_mode.get()
        bg = "#121212" if is_dark else "#f5f6fa"
        fg = "#ffffff" if is_dark else "#2c3e50"
        card_bg = "#1e1e1e" if is_dark else "#ffffff"
        entry_bg = "#2d2d2d" if is_dark else "#e2e8f0"
        btn_bg = "#2a2a2a" if is_dark else "#dcdde1"
        active_bg = "#3a3a3a" if is_dark else "#b2bec3"
        border_color = "#2c3e50" if is_dark else "#dcdde1"
        self.accent_color = "#ffffff" if is_dark else "#1565c0"

        self.root.config(bg=bg)
        self.main_container_frame.config(bg=bg)
        self.left_main_frame.config(bg=bg)
        self.top_frame.config(bg=bg)
        self.mid_container.config(bg=bg)
        self.coord_f.config(bg=card_bg)
        self.speed_time_row.config(bg=card_bg)
        self.cps_row.config(bg=card_bg)
        self.coord_btn_row.config(bg=card_bg)
        self.speed_mode_row.config(bg=card_bg)
        self.st_container.config(bg=bg)
        self.settings_lower_panel.config(bg=bg)
        self.buttons_frame.config(bg=bg)
        self.polling_frame.config(bg=bg)

        self.title_label.config(bg=bg, fg=self.accent_color)
        self.status_label.config(bg=bg)

        for f in [self.interval_frame, self.options_frame, self.loop_frame, self.control_frame]:
            f.config(bg=card_bg, fg=self.accent_color, bd=1, highlightbackground=border_color)

        self.apply_recursive_theme(self.root, bg, fg, card_bg)

        card_frames = {self.coord_f, self.speed_time_row, self.speed_mode_row, self.cps_row}

        for btn in self.smooth_buttons:
            btn.update_colors(card_bg if btn.master != self.top_frame and btn.master != self.buttons_frame and btn.master != self.st_container else bg, fg, btn_bg, active_bg)
        for ent in self.smooth_entries:
            p = ent.master
            use_card = isinstance(p, tk.LabelFrame) or p in card_frames
            ent.update_colors(card_bg if use_card else bg, fg, entry_bg)
        try:
            self.hk_entry.entry.config(readonlybackground=entry_bg)
        except:
            pass
        for cmb in self.smooth_combos:
            p = cmb.master
            use_card = isinstance(p, tk.LabelFrame) or p in card_frames
            cmb.update_colors(card_bg if use_card else bg, fg, entry_bg)

        self.polling_scale.config(bg=bg, fg=fg, troughcolor=entry_bg, activebackground=btn_bg)
        self.update_polling_label()

    def apply_recursive_theme(self, parent, bg, fg, card_bg):
        card_frames = (self.coord_f, self.speed_time_row, self.speed_mode_row)
        for w in parent.winfo_children():
            if isinstance(w, tk.Label) and w != self.title_label and w != self.status_label:
                p = w.master
                w.config(bg=card_bg if (isinstance(p, tk.LabelFrame) or p in card_frames) else bg, fg=fg)
            elif isinstance(w, tk.Checkbutton):
                p = w.master
                use_card = isinstance(p, tk.LabelFrame) or p in card_frames
                w.config(bg=card_bg if use_card else bg, fg=fg, selectcolor="#1e1e1e" if self.is_dark_mode.get() else "#ffffff", activebackground=card_bg if use_card else bg, activeforeground=fg)
            elif isinstance(w, tk.Frame) or isinstance(w, tk.LabelFrame):
                self.apply_recursive_theme(w, bg, fg, card_bg)

    def save_settings(self):
        s = {
            "click_mins_var": self.click_mins_var.get(),
            "click_secs_var": self.click_secs_var.get(),
            "click_ms_var": self.click_ms_var.get(),
            "use_cps_var": self.use_cps_var.get(),
            "cps_var": self.cps_var.get(),
            "speed_mode_var": self.speed_mode_var.get(),
            "active_time_var": self.active_time_var.get(),
            "wait_time_var": self.wait_time_var.get(),
            "loop_wait_first": self.loop_wait_first_var.get(),
            "action_type_var": self.action_type_var.get(),
            "target_key_var": self.target_key_var.get(),
            "start_key_var": self.start_key_var.get(),
            "timer_seconds_var": self.timer_seconds_var.get(),
            "main_x": self.main_x_var.get(),
            "main_y": self.main_y_var.get(),
            "main_hold_duration": self.main_hold_duration_var.get(),
            "main_hold_wait": self.main_hold_wait_var.get(),
            "polling_rate": self.polling_rate_var.get(),
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(s, f, indent=4)
        except: pass

    def load_settings(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    s = json.load(f)
                    self.click_mins_var.set(s.get("click_mins_var", "0"))
                    self.click_secs_var.set(s.get("click_secs_var", "0"))
                    self.click_ms_var.set(s.get("click_ms_var", "100"))
                    self.use_cps_var.set(s.get("use_cps_var", False))
                    self.cps_var.set(s.get("cps_var", "10"))
                    self.speed_mode_var.set(s.get("speed_mode_var", "Normal Click"))
                    self.active_time_var.set(s.get("active_time_var", "10"))
                    self.wait_time_var.set(s.get("wait_time_var", "10"))
                    self.loop_wait_first_var.set(s.get("loop_wait_first", False))
                    self.action_type_var.set(s.get("action_type_var", "Left Click"))
                    self.target_key_var.set(s.get("target_key_var", "1"))
                    self.start_key_var.set(s.get("start_key_var", "f8"))
                    self.timer_seconds_var.set(s.get("timer_seconds_var", "0"))
                    self.main_x_var.set(s.get("main_x", "0"))
                    self.main_y_var.set(s.get("main_y", "0"))
                    self.main_hold_duration_var.set(s.get("main_hold_duration", "5.0"))
                    self.main_hold_wait_var.set(s.get("main_hold_wait", "2.0"))
                    self.polling_rate_var.set(max(1, min(5, int(s.get("polling_rate", 3)))))
            except: pass

    def setup_input_guards(self):
        self.click_mins_var.trace_add("write", self.update_computed_delay_display)
        self.click_secs_var.trace_add("write", self.update_computed_delay_display)
        self.click_ms_var.trace_add("write", self.update_computed_delay_display)
        self.cps_var.trace_add("write", self.update_computed_delay_display)
        self.update_computed_delay_display()

        self.start_key_var.trace_add("write", self.update_start_button_label)
        self.update_start_button_label()

        self.attach_numeric_guard(self.cps_var, allow_zero=False)

        self.cps_var.trace_add("write", self.debounce_cps_safety_clamp)

        self.attach_numeric_guard(self.main_x_var, allow_zero=True, allow_negative=True, allow_decimal=False, guard_while_running=True)
        self.attach_numeric_guard(self.main_y_var, allow_zero=True, allow_negative=True, allow_decimal=False, guard_while_running=True)

        self.attach_numeric_guard(self.wait_time_var, allow_zero=True, guard_while_running=True)
        self.attach_numeric_guard(self.timer_seconds_var, allow_zero=True, guard_while_running=True)
        self.attach_numeric_guard(self.click_mins_var, allow_zero=True, guard_while_running=True)
        self.attach_numeric_guard(self.click_secs_var, allow_zero=True, guard_while_running=True)
        self.attach_numeric_guard(self.click_ms_var, allow_zero=True, guard_while_running=True)

        self.attach_numeric_guard(self.active_time_var, allow_zero=False, guard_while_running=True)
        self.attach_numeric_guard(self.main_hold_duration_var, allow_zero=False, guard_while_running=True)

        self.attach_numeric_guard(self.main_hold_wait_var, allow_zero=False, zero_callback=self.activate_infinite_from_wait_zero, guard_while_running=True)

        self._cps_running_guard_last = self.cps_var.get()
        def _guard_cps_running(*args):
            if getattr(self, "_cps_running_guard_updating", False):
                return
            val = self.cps_var.get()
            if val != self._cps_running_guard_last and self.is_running_at_high_speed():
                self._cps_running_guard_updating = True
                self.cps_var.set(self._cps_running_guard_last)
                self._cps_running_guard_updating = False
                self.warn_change_blocked()
                return
            self._cps_running_guard_last = val
        self.cps_var.trace_add("write", _guard_cps_running)

        self._target_key_running_last = self.target_key_var.get()
        def _guard_target_key_running(*args):
            if getattr(self, "_target_key_running_updating", False):
                return
            val = self.target_key_var.get()
            if val != self._target_key_running_last and self.is_running_at_high_speed():
                self._target_key_running_updating = True
                self.target_key_var.set(self._target_key_running_last)
                self._target_key_running_updating = False
                self.warn_change_blocked()
                return
            self._target_key_running_last = val
        self.target_key_var.trace_add("write", _guard_target_key_running)

        self._start_key_running_last = self.start_key_var.get()
        def _guard_start_key_running(*args):
            if getattr(self, "_start_key_running_updating", False):
                return
            val = self.start_key_var.get()
            if val != self._start_key_running_last and self.is_running_at_high_speed():
                self._start_key_running_updating = True
                self.start_key_var.set(self._start_key_running_last)
                self._start_key_running_updating = False
                self.warn_change_blocked()
                return
            self._start_key_running_last = val
        self.start_key_var.trace_add("write", _guard_start_key_running)

    def on_closing(self):
        if getattr(self, "_closing", False):
            return
        self._closing = True

        self.clicking = False
        self.program_running = False

        try:
            if self._pick_listener:
                self._pick_listener.stop()
        except:
            pass

        try:
            if self.is_currently_holding:
                self.release_native_action(self.action_type_var.get(), self.target_key_var.get().strip(), self.main_x_var.get().strip(), self.main_y_var.get().strip())
        except:
            pass
        self.is_currently_holding = False

        try:
            if self.listener:
                self.listener.stop()
        except:
            pass

        try:
            self.save_settings()
        except:
            pass

        try:
            self.root.destroy()
        except:
            pass

if __name__ == "__main__":
    try:
        ctypes.windll.winmm.timeBeginPeriod(1)
    except:
        pass

    root = tk.Tk()

    # Load icon from the same folder as the script
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")
    try:
        root.iconbitmap(default=icon_path)   # default= also applies to the Help popup
    except Exception:
        pass

    app = AutoClickerApp(root)
    root.mainloop()
