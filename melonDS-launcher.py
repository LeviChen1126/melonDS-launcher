#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, json, subprocess, platform, hashlib
from pathlib import Path
from typing import Any, Tuple, Dict, List, Optional
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

if platform.system() == "Windows":
    try:
        import ctypes, ctypes.wintypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

try:
    from PIL import Image, ImageTk
    PIL_OK = True
except Exception:
    PIL_OK = False
    Image = None
    ImageTk = None

APP_TITLE = "melonDS Launcher"
CONFIG_FILE = "config/melonds_launcher_config.json"
COVERS_MAP_FILE = "config/covers_map.json"
TITLES_MAP_FILE = "config/titles_map.json"

SUPPORTED_EXTS = [".nds", ".NDS"]
IMG_EXTS = [".png", ".jpg", ".jpeg"]

DEFAULT_CONFIG = {
    "rom_dir": "",
    "melonds_path": "",
    "covers_dir": "covers",
    "ui_scale": 1.0,
    "dark_mode": True,
    "view_mode": "grid",
    "show_titles": True,
    "pinned_files": [],
    "only_pinned": False,
    "last_dirs": {"rom":"", "melonds":"", "cover":""},
    "lang": "zh",
}

I18N = {
    "zh": {
        "rom_dir": "ROM 目錄：",
        "browse": "瀏覽...",
        "melonds": "melonDS：",
        "search": "搜尋：",
        "view": "檢視：",
        "zoom": "縮放：",
        "refresh": "重新整理",
        "not_selected": "未選取遊戲",
        "start_game": "開始遊戲",
        "choose_cover": "選擇封面",
        "rename_title": "更改顯示標題",
        "pin_this": "釘選此遊戲",
        "unpin": "取消釘選",
        "context_reveal": "在資料夾顯示",
        "tip_select": "請先選取一款遊戲。",
        "rename_prompt_title": "更改顯示標題",
        "rename_prompt": "輸入新的顯示名稱：",
        "pick_rom_title": "選取 ROM 目錄",
        "pick_melonds_title": "選取 melonDS 執行檔",
        "pick_cover_title": "選擇封面",
        "warn_notset": "尚未設定",
        "warn_set_melonds": "請先指定 melonDS 執行檔",
        "not_found": "找不到",
        "launch_failed": "啟動失敗",
        "open_folder_failed": "開啟資料夾失敗",
        "id_label": "ID / GameCode：",
        "language": "語言：",
        "lang_toggle_tip": "切換語言（zh/en）",
        "only_pinned_tip": "只顯示釘選遊戲",
    },
    "en": {
        "rom_dir": "ROM dir:",
        "browse": "Browse...",
        "melonds": "melonDS:",
        "search": "Search:",
        "view": "View:",
        "zoom": "Zoom:",
        "refresh": "Refresh",
        "not_selected": "No game selected",
        "start_game": "Play",
        "choose_cover": "Choose Cover",
        "rename_title": "Rename Display Title",
        "pin_this": "Pin this game",
        "unpin": "Unpin",
        "context_reveal": "Reveal in Folder",
        "tip_select": "Please select a game first.",
        "rename_prompt_title": "Rename Display Title",
        "rename_prompt": "New display name:",
        "pick_rom_title": "Choose ROM Directory",
        "pick_melonds_title": "Choose melonDS Executable",
        "pick_cover_title": "Choose Cover Image",
        "warn_notset": "Not set",
        "warn_set_melonds": "Please choose the melonDS executable first",
        "not_found": "Not found",
        "launch_failed": "Launch failed",
        "open_folder_failed": "Failed to open folder",
        "id_label": "ID / GameCode: ",
        "language": "Language:",
        "lang_toggle_tip": "Toggle language (zh/en)",
        "only_pinned_tip": "Show only pinned",
    },
}

def tr(app, key):
    lang = getattr(app, "lang", "zh")
    return I18N.get(lang, I18N["zh"]).get(key, key)

def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default

def save_json(path: Path, data):
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        messagebox.showerror("儲存失敗", f"{path}\n{e}")

def read_nds_info(path: Path):
    title, code = "", ""
    try:
        with open(path, "rb") as f:
            head = f.read(0x200)
        title = head[0:12].decode("ascii", "ignore").strip("\x00 ").strip()
        code = head[0x0C:0x10].decode("ascii", "ignore").strip("\x00 ").strip()
    except Exception:
        pass
    return title, code

def game_id_for(path: Path):
    _, code = read_nds_info(path)
    if code and len(code) == 4:
        return f"NDS-{code}"
    try:
        h = hashlib.md5()
        with open(path, "rb") as f:
            h.update(f.read(1024*1024))
        return f"HASH-{h.hexdigest()}"
    except Exception:
        return path.stem.lower()

class LauncherApp(tk.Tk):
    def _resolve_asset_path(self, filename: str) -> Path:
        try:
            p = Path(filename)
            if p.exists():
                return p
            base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
            cand = base / filename
            if cand.exists():
                return cand
            for root in [Path.cwd(), base]:
                cand = root / "assets" / filename
                if cand.exists():
                    return cand
        except Exception:
            pass
        return Path(filename)

    def _set_app_icon(self):
        try:
            nds_path = self._resolve_asset_path("nds.png")
            if nds_path and nds_path.exists():
                try:
                    if PIL_OK:
                        ph = ImageTk.PhotoImage(Image.open(nds_path))
                    else:
                        ph = tk.PhotoImage(file=str(nds_path))
                    self.iconphoto(True, ph)
                    try: self.wm_iconphoto(True, ph)
                    except Exception: pass
                except Exception:
                    pass
                try:
                    import ctypes
                    if platform.system() == "Windows" and PIL_OK:
                        base_im = Image.open(nds_path).convert("RGBA")
                        def to_square(im, size):
                            from PIL import Image as _I
                            canvas = _I.new("RGBA", (size, size), (0,0,0,0))
                            ratio = min(size / im.width, size / im.height)
                            new_w = max(1, int(im.width * ratio))
                            new_h = max(1, int(im.height * ratio))
                            im2 = im.resize((new_w, new_h), Image.LANCZOS)
                            x = (size - new_w)//2; y = (size - new_h)//2
                            canvas.paste(im2, (x,y), im2)
                            return canvas
                        ico128 = to_square(base_im, 128)
                        ico256 = to_square(base_im, 256)
                        ico_tmp = Path("./assets/nds.ico")
                        ico_tmp.parent.mkdir(parents=True, exist_ok=True)
                        ico128.save(ico_tmp, format="ICO", sizes=[(128,128),(256,256)], append_images=[ico256])
                        try: ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("melonDS.Launcher")
                        except Exception: pass
                        try:
                            self.iconbitmap(default=str(ico_tmp))
                            try: self.tk.call("wm", "iconbitmap", self._w, str(ico_tmp))
                            except Exception: pass
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

    PADDING_BORDER = 2
    BREAKPOINTS = [
        (520,  2, 140, 205),
        (760,  3, 148, 212),
        (980,  4, 156, 220),
        (1200, 5, 164, 228),
        (1450, 6, 172, 236),
        (1720, 7, 180, 244),
        (99999,8, 188, 252),
    ]

    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1280x820")

        self.config_path = Path(CONFIG_FILE)
        self.config_dir = Path("config"); self.config_dir.mkdir(exist_ok=True)
        self.config = load_json(self.config_path, DEFAULT_CONFIG.copy())
        self.lang = self.config.get("lang", "zh")

        try:
            files = set(self.config.get("pinned_files") or [])
            self.config["pinned_files"] = sorted(files)
            save_json(self.config_path, self.config)
        except Exception:
            pass

        self.covers_path = Path(self.config.get("covers_dir", "covers")); self.covers_path.mkdir(parents=True, exist_ok=True)
        self.map_path = Path(COVERS_MAP_FILE); self.covers_map = load_json(self.map_path, {})
        self.titles_path = Path(TITLES_MAP_FILE); self.titles_map = load_json(self.titles_path, {})
        self.roms: List[Path] = []
        self.images_cache: Dict = {}
        self.pil_cache: Dict = {}
        self.selected_game: Optional[Path] = None
        self.selected_widget: Optional[tk.Widget] = None
        self._scroll_enabled = True
        self._last_grid_bp: Tuple[int,int,int,int] = (-1,-1,-1,-1)
        self._canvas_cfg_id = None
        self._root_cfg_id = None
        self._scale_applied_percent = None
        self._last_right_width = None
        self._is_scaling_drag = False
        self._tile_by_path: Dict[Path, tk.Widget] = {}
        self._icons: Dict[str, Any] = {}

        self._init_style()
        self._build_toolbar()
        try:
            self._set_app_icon()
        except Exception:
            pass
        self._build_main()
        self.after(80, self._apply_dark_titlebar)

        self.bind("<Configure>", self._on_root_resized)
        self._bind_mousewheel()
        self.refresh_rom_list()

    def _init_style(self):
        import tkinter.font as tkfont
        style = ttk.Style()
        try: style.theme_use("clam")
        except Exception: pass

        sysname = platform.system()
        if sysname == "Windows": ff = "Microsoft JhengHei UI"
        elif sysname == "Darwin": ff = "PingFang TC"
        else: ff = "Noto Sans CJK TC"

        tkfont.nametofont("TkDefaultFont").configure(family=ff, size=10)
        tkfont.nametofont("TkTextFont").configure(family=ff, size=10)
        tkfont.nametofont("TkFixedFont").configure(family=ff, size=10)

        dark = self.config.get("dark_mode", True)
        self.bg   = "#0f1419" if dark else "#f0f0f0"
        self.fg   = "#e6edf3" if dark else "#202020"
        self.panel= "#1b2228" if dark else "#ffffff"
        self.accent="#3fb950" if dark else "#0b5ed7"
        self.sel  = "#29323a" if dark else "#e6f0ff"
        self.trough = "#0a0f14" if dark else "#e4e4e4"
        self.thumb  = "#4b5866" if dark else "#b5b5b5"
        self["bg"] = self.bg

        style.configure(".", background=self.bg, foreground=self.fg, font=(ff, 10))
        style.configure("TFrame", background=self.panel)
        style.configure("TLabel", background=self.panel, foreground=self.fg, font=(ff, 10))
        style.configure("TButton", padding=6, font=(ff, 10))
        style.configure("Accent.TButton", background=self.accent, foreground="#fff", font=(ff, 10, "bold"))
        style.configure("Dark.TEntry", fieldbackground=self.bg, background=self.bg, foreground=self.fg, insertcolor=self.fg)
        style.configure("Tile.TFrame", background=self.panel, relief="flat")
        style.configure("TileSelected.TFrame", background=self.sel, relief="flat")

        style.layout("Dark.Vertical.TScrollbar",
            [('Vertical.Scrollbar.trough',
              {'children': [('Vertical.Scrollbar.thumb', {'expand': '1', 'sticky': 'nswe'})],
               'sticky': 'ns'})])
        style.configure("Dark.Vertical.TScrollbar",
                        background=self.thumb, troughcolor=self.trough, arrowcolor=self.fg,
                        darkcolor=self.thumb, lightcolor=self.thumb, bordercolor=self.thumb,
                        width=14, arrowsize=14)
        style.map("Dark.Vertical.TScrollbar",
                  background=[("active", self.thumb), ("!active", self.thumb)])

        self.colors = dict(bg=self.bg, fg=self.fg, panel=self.panel, accent=self.accent, sel=self.sel,
                           trough=self.trough, thumb=self.thumb, font_family=ff)

        def _load_icon(filename: str, size_if_pil: Tuple[int,int] = None):
            p = self._resolve_asset_path(filename)
            if not p.exists():
                return None
            try:
                if PIL_OK:
                    im = Image.open(p).convert("RGBA")
                    if size_if_pil:
                        im = im.resize(size_if_pil, Image.LANCZOS)
                    return ImageTk.PhotoImage(im)
                else:
                    return tk.PhotoImage(file=str(p))
            except Exception:
                return None
        self._icons["grid"]   = _load_icon("assets/grid.png", (28,28))
        self._icons["list"]   = _load_icon("assets/list.png", (28,28))
        self._icons["browse"] = _load_icon("assets/browse.png", (23,23))
        self._icons["pin"]    = _load_icon("assets/pin.png", (28,28))
        self._icons["lang"]   = _load_icon("assets/lang.png", (28,28))

        self._icons_pil = {}
        try:
            if PIL_OK:
                p_pin = self._resolve_asset_path("assets/pin.png")
                if p_pin and p_pin.exists():
                    self._icons_pil["pin"] = Image.open(p_pin).convert("RGBA")
        except Exception:
            pass

    def _apply_dark_titlebar(self):
        if platform.system() != "Windows":
            return
        try:
            import ctypes, ctypes.wintypes
            hwnd = ctypes.wintypes.HWND(self.winfo_id())
            for attr in (20, 19):
                try:
                    val = ctypes.c_int(1)
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd,
                        ctypes.wintypes.DWORD(attr),
                        ctypes.byref(val), ctypes.sizeof(val))
                except Exception:
                    pass
        except Exception:
            pass

    def _build_toolbar(self):
        if hasattr(self, "_toolbar") and self._toolbar and self._toolbar.winfo_exists():
            try: self._toolbar.destroy()
            except Exception: pass

        bar = ttk.Frame(self)
        try:
            if hasattr(self, "_main") and self._main and self._main.winfo_exists():
                bar.pack(side="top", fill="x", before=self._main)
            else:
                bar.pack(side="top", fill="x")
        except Exception:
            bar.pack(side="top", fill="x")
        self._toolbar = bar

        ttk.Label(bar, text=tr(self, "rom_dir")).pack(side="left", padx=(8,4), pady=8)
        rom_row = ttk.Frame(bar); rom_row.pack(side="left")
        self.var_romdir = tk.StringVar(value=self.config.get("rom_dir",""))
        self.entry_rom = ttk.Entry(rom_row, textvariable=self.var_romdir, width=40, style="Dark.TEntry")
        self.entry_rom.pack(side="left", ipady=5)
        ttk.Button(rom_row,
                   text=(" " if self._icons.get("browse") else tr(self, "browse")),
                   image=(self._icons.get("browse") or None),
                   command=self.pick_rom_dir).pack(side="left", padx=4)

        ttk.Label(bar, text=tr(self, "melonds")).pack(side="left", padx=(16,4))
        mel_row = ttk.Frame(bar); mel_row.pack(side="left")
        self.var_melonds = tk.StringVar(value=self.config.get("melonds_path",""))
        self.entry_mel = ttk.Entry(mel_row, textvariable=self.var_melonds, width=30, style="Dark.TEntry")
        self.entry_mel.pack(side="left", ipady=5)
        ttk.Button(mel_row,
                   text=(" " if self._icons.get("browse") else tr(self, "browse")),
                   image=(self._icons.get("browse") or None),
                   command=self.pick_melonds).pack(side="left", padx=4)

        ttk.Label(bar, text=tr(self, "search")).pack(side="left", padx=(16,4))
        self.var_query = tk.StringVar()
        self.entry_query = ttk.Entry(bar, textvariable=self.var_query, width=22, style="Dark.TEntry")
        self.entry_query.pack(side="left", ipady=5)
        self.entry_query.bind("<KeyRelease>", lambda e: self.refresh_rom_list())

        ttk.Label(bar, text=tr(self, "view")).pack(side="left", padx=(16,4))
        self.btn_grid = ttk.Button(bar,
                                   text=(" " if self._icons.get("grid") else "Grid"),
                                   image=(self._icons.get("grid") or None),
                                   width=3, command=lambda:self._set_view_mode("grid"))
        self.btn_list = ttk.Button(bar,
                                   text=(" " if self._icons.get("list") else "List"),
                                   image=(self._icons.get("list") or None),
                                   width=3, command=lambda:self._set_view_mode("list"))
        self.btn_grid.pack(side="left", padx=(0,2)); self.btn_list.pack(side="left", padx=(2,8))

        ttk.Label(bar, text=tr(self, "zoom")).pack(side="left", padx=(0,4))
        self.var_scale = tk.DoubleVar(value=float(self.config.get("ui_scale", 1.0)))
        self.scale = ttk.Scale(bar, from_=0.6, to=2.2, orient="horizontal",
                               variable=self.var_scale, length=200, command=self._on_scale_drag)
        self.scale.pack(side="left", padx=4, pady=8)
        self.scale.bind("<ButtonPress-1>", lambda e: setattr(self, "_is_scaling_drag", True))
        self.scale.bind("<ButtonRelease-1>", self._apply_scale_on_release)
        self.lbl_zoom = ttk.Label(bar, text=f"{int(self.var_scale.get()*100)}%"); self.lbl_zoom.pack(side="left", padx=(6,0))

        def _toggle_lang():
            self.lang = "en" if self.lang == "zh" else "zh"
            self.config["lang"] = self.lang
            save_json(self.config_path, self.config)
            # 重新建構 toolbar 以更新文字，並保持在最上方
            self._build_toolbar()
            # 更新右側資訊區塊文字
            self._refresh_right_panel_texts()
            # 如有選擇中的遊戲，更新程式碼前綴等文字
            if self.selected_game:
                gid = game_id_for(self.selected_game)
                title, code = read_nds_info(self.selected_game)
                self.lbl_title.config(text=self._display_name_for(self.selected_game))
                self.lbl_code.config(text=f"{tr(self,'id_label')}{gid}" + (f"（{code}）" if code else ""))
            else:
                self.lbl_title.config(text=tr(self, "not_selected"))
        self.btn_lang = ttk.Button(bar,
                                   text=(" " if self._icons.get("lang") else tr(self, "language")),
                                   image=(self._icons.get("lang") or None),
                                   command=_toggle_lang)
        self.btn_lang.pack(side="left", padx=(12,4))

        self.btn_only_pin = ttk.Button(bar, image=self._icons.get("pin"), command=self._toggle_only_pinned)
        self.btn_only_pin.pack(side="left", padx=(8,0))

        ttk.Button(bar, text=tr(self, "refresh"), command=self.refresh_rom_list).pack(side="right", padx=6, pady=8)
        self._refresh_view_buttons()
        self._refresh_only_pin_button()
        self._bind_scale_precise()

    def _bind_scale_precise(self):
        def _goto_click(e):
            try:
                w = max(1, self.scale.winfo_width())
                frac = min(1.0, max(0.0, e.x / w))
                vmin = float(self.scale.cget("from")); vmax = float(self.scale.cget("to"))
                val = vmin + (vmax - vmin) * frac
                self.var_scale.set(val)
                self._on_scale_drag(str(val))
                self._apply_scale_on_release()
            except Exception:
                pass
        self.scale.bind("<Button-1>", _goto_click, add="+")

    def _set_view_mode(self, mode: str):
        self.config["view_mode"] = mode
        save_json(self.config_path, self.config)
        self._refresh_view_buttons()
        self.refresh_rom_list()

    def _toggle_only_pinned(self):
        cur = bool(self.config.get("only_pinned", False))
        self.config["only_pinned"] = not cur
        save_json(self.config_path, self.config)
        self._refresh_only_pin_button()
        self.refresh_rom_list()

    def _refresh_only_pin_button(self):
        try:
            if bool(self.config.get("only_pinned", False)):
                self.btn_only_pin.configure(style="Accent.TButton")
            else:
                self.btn_only_pin.configure(style="TButton")
        except Exception:
            pass

    def _refresh_view_buttons(self):
        vm = self.config.get("view_mode", "grid")
        self.btn_grid.state(["!disabled"]); self.btn_list.state(["!disabled"])
        if vm == "grid":
            self.btn_grid.configure(style="Accent.TButton"); self.btn_list.configure(style="TButton")
        else:
            self.btn_list.configure(style="Accent.TButton"); self.btn_grid.configure(style="TButton")

    def _on_scale_drag(self, val):
        try: p = int(float(val)*100 + 0.5)
        except Exception: p = int(self.var_scale.get()*100 + 0.5)
        self.lbl_zoom.config(text=f"{p}%")
        self._scale_applied_percent = p
        self.config["ui_scale"] = max(50, min(250, p))/100.0
        save_json(self.config_path, self.config)

    def _apply_scale_on_release(self, _evt=None):
        self._is_scaling_drag = False
        p = int(self.var_scale.get()*100 + 0.5)
        self.config["ui_scale"] = max(50, min(250, p))/100.0
        save_json(self.config_path, self.config)
        self.refresh_rom_list()

    def _build_main(self):
        main = ttk.Frame(self); main.pack(side="top", fill="both", expand=True, padx=8, pady=8)
        self._main = main

        left = ttk.Frame(main); left.pack(side="left", fill="both", expand=True)
        self.canvas = tk.Canvas(left, highlightthickness=0, bd=0, bg=self.bg)
        self.scroll_y = ttk.Scrollbar(left, orient="vertical", command=self.canvas.yview, style="Dark.Vertical.TScrollbar")
        self.grid_frame = ttk.Frame(self.canvas, style="TFrame")
        self.grid_window = self.canvas.create_window((0,0), window=self.grid_frame, anchor="nw")
        def on_canvas_cfg(_evt=None):
            if getattr(self, "_canvas_cfg_id", None):
                try: self.after_cancel(self._canvas_cfg_id)
                except Exception: pass
            self._canvas_cfg_id = self.after(150, self._handle_canvas_resize)
        self.canvas.bind("<Configure>", on_canvas_cfg)
        self.grid_frame.bind("<Configure>", self._on_gridframe_configure)
        self.canvas.configure(yscrollcommand=self.canvas_yset)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scroll_y.pack(side="right", fill="y")
        self.after(0, self._apply_right_panel_width)

        right = ttk.Frame(main, style="TFrame", width=380)
        right.pack(side="right", fill="y"); right.pack_propagate(False)
        self.right_panel = right
        self.right_cover = tk.Label(right, bg=self.panel); self.right_cover.pack(padx=12, pady=(12,6), anchor="w")
        self.lbl_title = tk.Label(right, text=tr(self, "not_selected"), font=(self._font_family(), 12, "bold"),
                                  bg=self.panel, fg=self.fg, justify="left", anchor="w", wraplength=350)
        self.lbl_title.pack(padx=12, pady=(6,6), anchor="w", fill="x")
        self.lbl_path = tk.Label(right, text="", wraplength=350, justify="left", anchor="w",
                                 bg=self.panel, fg=self.fg)
        self.lbl_path.pack(padx=12, pady=6, anchor="w", fill="x")
        self.lbl_code = tk.Label(right, text="", bg=self.panel, fg=self.fg, anchor="w", justify="left", wraplength=350)
        self.lbl_code.pack(padx=12, pady=6, anchor="w", fill="x")
        ttk.Separator(right).pack(fill="x", padx=12, pady=12)

        # 右側功能按鈕（之後會在語言切換時更新文字）
        self.btn_play = ttk.Button(right, text=tr(self, "start_game"), style="Accent.TButton", command=self.launch_selected)
        self.btn_play.pack(padx=12, pady=6, anchor="w")
        self.btn_choose_cover = ttk.Button(right, text=tr(self, "choose_cover"), command=self.pick_cover_for_selected)
        self.btn_choose_cover.pack(padx=12, pady=6, anchor="w")
        self.btn_rename = ttk.Button(right, text=tr(self, "rename_title"), command=self.rename_selected)
        self.btn_rename.pack(padx=12, pady=6, anchor="w")
        self.btn_pin = ttk.Button(right, text=tr(self, "pin_this"), command=self.pin_toggle_selected)
        self.btn_pin.pack(padx=12, pady=6, anchor="w")

        def update_wrap(_=None):
            try:
                w = max(120, right.winfo_width()-24)
                for lab in (self.lbl_title, self.lbl_path, self.lbl_code):
                    lab.configure(wraplength=w)
            except Exception: pass
        right.bind("<Configure>", update_wrap)
        self.after(200, update_wrap)

    def _refresh_right_panel_texts(self):
        """在語言切換後更新右側面板的按鈕與文字。"""
        try:
            # 標題（若未選取遊戲）
            if not self.selected_game:
                self.lbl_title.config(text=tr(self, "not_selected"))
            # 四個按鈕
            self.btn_play.config(text=tr(self, "start_game"))
            self.btn_choose_cover.config(text=tr(self, "choose_cover"))
            self.btn_rename.config(text=tr(self, "rename_title"))
            # 釘選/取消釘選需依狀態切換
            if self.selected_game and self._is_pinned(self.selected_game):
                self.btn_pin.config(text=tr(self, "unpin"))
            else:
                self.btn_pin.config(text=tr(self, "pin_this"))
        except Exception:
            pass

    def canvas_yset(self, first, last):
        self.scroll_y.set(first, last)

    def _font_family(self): return self.colors["font_family"]

    def _active_breakpoint(self, canvas_w: int):
        s = float(self.config.get("ui_scale", 1.0))
        for limit, cols, tw, th in self.BREAKPOINTS:
            if canvas_w <= limit:
                return cols, int(tw*s), int(th*s), 10
        return 4, int(156*s), int(220*s), 6

    def _pin_key(self, p: Path) -> str:
        return p.name

    def _cover_box_for_tile(self, w, h):
        return w, int(h * 0.78)

    def _list_thumb_box(self):
        s = float(self.config.get("ui_scale", 1.0))
        base_w = 148
        w = max(80, int(base_w * s))
        h = int(w * 0.75)
        return w, h

    def _title_font(self, grid=False):
        s = float(self.config.get("ui_scale", 1.0))
        base = 9 if grid else 12
        size = max(9, min(int(base * s), 22))
        return (self._font_family(), size, "bold")

    def _path_font(self):
        s = float(self.config.get("ui_scale", 1.0))
        size = max(8, min(int(10 * s), 18))
        return (self._font_family(), size)

    def _display_name_for(self, rom_path: Path) -> str:
        gid = game_id_for(rom_path)
        if gid in self.titles_map and self.titles_map[gid]:
            return self.titles_map[gid]
        title, _ = read_nds_info(rom_path)
        return rom_path.stem or title or rom_path.name

    def _cover_path_for(self, rom_path: Path) -> Optional[Path]:
        gid = game_id_for(rom_path)
        p = self.covers_map.get(gid)
        if p and Path(p).exists(): return Path(p)
        for ext in IMG_EXTS:
            guess = self.covers_path / f"{rom_path.stem}{ext}"
            if guess.exists(): return guess
        return None

    def _is_pinned(self, p: Path) -> bool:
        files = set(self.config.get("pinned_files", []))
        return self._pin_key(p) in files

    def _resize_fit_box(self, im: Any, box_w: int, box_h: int, resample: Any):
        iw, ih = im.size
        if iw == 0 or ih == 0: return im
        scale = min(box_w/iw, box_h/ih)
        new_w = max(1, int(iw*scale)); new_h = max(1, int(ih*scale))
        return im.resize((new_w, new_h), resample=resample)

    def _load_image_fit(self, path: Path, box_w: int, box_h: int, quality: str = "hq", overlay_pin: bool = False):
        key = (str(path), box_w, box_h, quality, 1 if overlay_pin else 0)
        if key in self.images_cache: return self.images_cache[key]
        if not path.exists(): return None
        try:
            if PIL_OK:
                im = self.pil_cache.get(str(path))
                if im is None:
                    im = Image.open(path).convert("RGBA")
                    self.pil_cache[str(path)] = im
                resample = Image.LANCZOS if quality == "hq" else Image.BILINEAR
                im_resized = self._resize_fit_box(im, box_w, box_h, resample)
                if overlay_pin and hasattr(self, "_icons_pil") and self._icons_pil.get("pin") is not None:
                    try:
                        pin_im = self._icons_pil["pin"]
                        target_w = max(16, min(64, int(box_w * 0.22)))
                        ratio = target_w / float(pin_im.width)
                        target_h = max(16, int(pin_im.height * ratio))
                        pim = pin_im.resize((target_w, target_h), Image.LANCZOS)
                        margin = max(4, int(min(box_w, box_h) * 0.04))
                        x = im_resized.width - pim.width - margin
                        y = im_resized.height - pim.height - margin
                        im_resized.paste(pim, (x, y), pim)
                    except Exception:
                        pass
                ph = ImageTk.PhotoImage(im_resized) if PIL_OK else None
            else:
                ph = tk.PhotoImage(file=str(path))
            self.images_cache[key] = ph; return ph
        except Exception:
            return None

    def _build_context_menu(self, rom_path: Path):
        m = tk.Menu(self, tearoff=0)
        m.configure(bg=self.panel, fg=self.fg, activebackground=self.sel, activeforeground=self.fg, bd=0, relief="flat")
        m.add_command(label=tr(self, "start_game"), command=lambda rp=rom_path: self._launch(rp))
        m.add_command(label=tr(self, "choose_cover"), command=lambda rp=rom_path: self._pick_cover_for(rp))
        m.add_command(label=tr(self, "rename_title"), command=lambda rp=rom_path: self._rename_title(rp))
        m.add_separator()
        m.add_command(label=tr(self, "context_reveal"), command=lambda rp=rom_path: self._reveal(rp))
        return m

    def _make_tile(self, parent, rom_path: Path, tile_size, cover_box):
        w, h = tile_size
        cover_w, cover_h = cover_box
        wrap = tk.Frame(parent, bg=self.panel)
        f = ttk.Frame(wrap, style="Tile.TFrame")
        f._rom_path = rom_path; wrap._rom_path = rom_path; wrap._inner = f
        menu = self._build_context_menu(rom_path)

        box = tk.Frame(f, width=cover_w, height=cover_h, bg=self.panel, highlightthickness=0, bd=0)
        box.pack_propagate(False); box.pack(fill="x", padx=0, pady=(6,0))
        f._cover_box = box

        ip = self._cover_path_for(rom_path)
        img_label = None; name_label = None
        if ip:
            ph = self._load_image_fit(ip, cover_w, cover_h, "hq", overlay_pin=self._is_pinned(rom_path))
            if ph:
                img_label = tk.Label(box, image=ph, bg=self.panel); img_label.image = ph
                img_label.pack(side="bottom"); f._img_label = img_label
        else:
            name_label = tk.Label(box, text=self._display_name_for(rom_path), bg=self.panel, fg=self.fg,
                                  font=self._title_font(grid=True), justify="center")
            name_label.pack(side="bottom"); f._name_label = name_label

        ttl = None
        if self.config.get("show_titles", True):
            raw = self._display_name_for(rom_path)
            ttl = tk.Label(f, text=raw, bg=self.panel, fg=self.fg,
                           font=self._title_font(grid=True), justify="center", wraplength=w)
            ttl.pack(fill="x", padx=0, pady=(0,4))
            f._title_label = ttl; f._title_raw = raw

        self._bind_game_handlers([wrap, f, box, img_label, name_label, ttl], rom_path, wrap, menu)

        f.pack(fill="both", expand=True, padx=self.PADDING_BORDER, pady=self.PADDING_BORDER)
        try: self._tile_by_path[rom_path] = wrap
        except Exception: pass
        return wrap

    def _render_list(self):
        tw, th = self._list_thumb_box()
        for p in self.roms:
            wrap = tk.Frame(self.grid_frame, bg=self.panel); wrap.pack(fill="x", pady=6)
            row = ttk.Frame(wrap, style="Tile.TFrame"); row.pack(fill="x", padx=self.PADDING_BORDER, pady=self.PADDING_BORDER)
            row._rom_path = p; wrap._rom_path = p; wrap._inner = row
            menu = self._build_context_menu(p)

            box = tk.Frame(row, width=tw, height=th, bg=self.panel, highlightthickness=0, bd=0)
            box.pack_propagate(False); box.pack(side="left", padx=0, pady=6)
            row._thumb_box = box

            ip = self._cover_path_for(p)
            img_lbl = None; name_lbl = None
            if ip:
                ph = self._load_image_fit(ip, tw, th, "hq", overlay_pin=self._is_pinned(p))
                if ph:
                    img_lbl = tk.Label(box, image=ph, bg=self.panel); img_lbl.image = ph
                    img_lbl.place(relx=0.5, rely=0.5, anchor="center"); row._thumb_label = img_lbl
            else:
                name_lbl = tk.Label(box, text=self._display_name_for(p), bg=self.panel, fg=self.fg,
                                    font=self._title_font(grid=False), justify="center")
                name_lbl.place(relx=0.5, rely=0.5, anchor="center"); row._name_label = name_lbl

            tf = ttk.Frame(row, style="Tile.TFrame"); tf.pack(side="left", fill="both", expand=True, padx=(6,12), pady=6)
            inner = tk.Frame(tf, bg=self.panel); inner.place(relx=0.0, rely=0.5, anchor="w", relwidth=1.0)
            title = tk.Label(inner, text=self._display_name_for(p), bg=self.panel, fg=self.fg,
                             font=self._title_font(grid=False), justify="left", anchor="w")
            title.pack(anchor="w", fill="x")
            path_lbl = tk.Label(inner, text=str(p), bg=self.panel, fg="#92a0ad",
                                anchor="w", justify="left", font=self._path_font())
            path_lbl.pack(anchor="w", fill="x")
            row._path_label = path_lbl; row._title_label = title

            self._bind_game_handlers([wrap, row, box, img_lbl, name_lbl, tf, inner, title, path_lbl], p, wrap, menu)
            try: self._tile_by_path[p] = wrap
            except Exception: pass

    def _scan_roms(self):
        rom_dir = Path(self.var_romdir.get().strip() or self.config.get("rom_dir",""))
        query = (self.var_query.get() or "").lower().strip()
        out: List[Path] = []
        if rom_dir and rom_dir.exists():
            for p in sorted(rom_dir.glob("**/*")):
                if p.is_file() and p.suffix in SUPPORTED_EXTS:
                    name = (self._display_name_for(p) + " " + p.name).lower()
                    if query and (query not in name): continue
                    out.append(p)
        if bool(self.config.get("only_pinned", False)):
            out = [p for p in out if self._is_pinned(p)]
        out = sorted(out, key=lambda x: (0 if self._is_pinned(x) else 1, x.name.lower()))
        return out

    def refresh_rom_list(self):
        prev = self.selected_game
        self.images_cache.clear()
        for w in list(self.grid_frame.children.values()): w.destroy()
        self._tile_by_path = {}
        self.roms = self._scan_roms()
        if self.config.get("view_mode","grid") == "list":
            self._render_list(); self._last_grid_bp = (-1,-1,-1,-1)
        else:
            self._render_grid()

        restored = False
        if prev and prev in self.roms:
            w = self._tile_by_path.get(prev)
            if w and w.winfo_exists():
                self._set_selected(prev, w)
                restored = True
        if not restored and not self.selected_game:
            self.lbl_title.config(text=tr(self, "not_selected"), font=(self._font_family(), 12, "bold"))
            self.lbl_path.config(text=""); self.lbl_code.config(text="")
            self.right_cover.configure(image="", text="")

        self._refresh_scrollbar_style()
        self._update_scrollbar_visibility()
        self._update_list_wrap()

    def _render_grid(self):
        import math
        canvas_w = max(1, self.canvas.winfo_width() or 1)
        cols_bp, tw, th, gutter = self._active_breakpoint(canvas_w)
        cols = max(1, int((canvas_w + gutter) // (tw + gutter)))
        cover_w, cover_h = self._cover_box_for_tile(tw, th)
        self._last_grid_bp = (cols, tw, th, gutter)

        total = len(self.roms)
        total_rows = max(1, math.ceil(total / cols)) if total else 1

        for idx, p in enumerate(self.roms):
            r, c = idx // cols, idx % cols
            tile = self._make_tile(self.grid_frame, p, (tw, th), (cover_w, cover_h))
            pad_x = (0, 0 if c == cols - 1 else gutter)
            pad_y = (0, 0 if r == total_rows - 1 else gutter)
            tile.grid(row=r, column=c, padx=pad_x, pady=pad_y, sticky="nw")
        for i in range(cols): self.grid_frame.grid_columnconfigure(i, weight=0, minsize=tw)

    def _update_list_wrap(self):
        if self.config.get("view_mode","grid") == "grid": return
        try:
            canvas_w = self.canvas.winfo_width() or 1
            tw, _ = self._list_thumb_box()
            usable = max(100, canvas_w - tw - 80)
            for wrap in self.grid_frame.winfo_children():
                row = getattr(wrap, "_inner", None)
                if not row: continue
                if hasattr(row, "_path_label"):
                    row._path_label.configure(wraplength=usable, font=self._path_font())
                if hasattr(row, "_title_label"):
                    row._title_label.configure(wraplength=usable, font=self._title_font(grid=False))
        except Exception:
            pass

    def _apply_selection_border(self, wrap, selected: bool):
        try:
            if not wrap or not wrap.winfo_exists(): return
            wrap.configure(bg=("#ffffff" if selected else self.panel))
        except Exception:
            pass

    def _set_selected(self, rom_path: Optional[Path], widget: Optional[tk.Widget]):
        if self.selected_widget and self.selected_widget.winfo_exists():
            try: self.selected_widget.configure(style="Tile.TFrame")
            except Exception: pass
            self._apply_selection_border(self.selected_widget, False)
        self.selected_game = rom_path; self.selected_widget = widget
        if rom_path:
            if widget and widget.winfo_exists():
                try: widget.configure(style="TileSelected.TFrame")
                except Exception: pass
                self._apply_selection_border(widget, True)
            title, code = read_nds_info(rom_path)
            self.lbl_title.config(text=self._display_name_for(rom_path) or title or rom_path.stem, font=self._title_font(grid=False))
            self.lbl_path.config(text=str(rom_path))
            gid = game_id_for(rom_path)
            self.lbl_code.config(text=f"{tr(self,'id_label')}{gid}" + (f"（{code}）" if code else ""))
            self._update_right_cover(rom_path)
            try:
                if self._is_pinned(rom_path):
                    self.btn_pin.configure(text=tr(self, "unpin"))
                else:
                    self.btn_pin.configure(text=tr(self, "pin_this"))
            except Exception:
                pass
        else:
            self.lbl_title.config(text=tr(self, "not_selected"), font=(self._font_family(), 12, "bold"))
            self.lbl_path.config(text=""); self.lbl_code.config(text="")
            self.right_cover.configure(image="", text="")
        # 每次選取時，同步一次右面板語系（避免漏掉）
        self._refresh_right_panel_texts()

    def _bind_game_handlers(self, widgets, rom_path: Path, select_widget, menu=None):
        def on_select(e, rp=rom_path, w=select_widget):
            self._set_selected(rp, w); return "break"
        def on_launch(e, rp=rom_path):
            self._launch(rp); return "break"
        def on_menu(e, m=menu):
            if m:
                try: m.tk_popup(e.x_root, e.y_root)
                finally: m.grab_release()
            return "break"
        for w in widgets:
            if not w: continue
            try:
                w.bind("<Button-1>", on_select)
                w.bind("<Double-Button-1>", on_launch)
                w.bind("<Button-3>", on_menu)
                w.bind("<Button-2>", on_menu)
            except Exception: pass

    def _update_right_cover(self, rom_path: Path):
        try:
            ip = self._cover_path_for(rom_path)
            if not ip:
                self.right_cover.configure(image="", text="")
                return
            canvas_w = max(1, self.canvas.winfo_width() or 1)
            _, tw, th, _ = self._active_breakpoint(canvas_w)
            cw, ch = self._cover_box_for_tile(tw, th)
            target_w = int(cw * 2.0); target_h = int(ch * 2.0)
            ph = self._load_image_fit(ip, target_w, target_h, "hq")
            if ph:
                self.right_cover.configure(image=ph, text=""); self.right_cover.image = ph
                want = max(380, target_w + 24)
                try: self.right_panel.configure(width=want)
                except Exception: pass
        except Exception:
            pass

    def pick_rom_dir(self):
        init = self.config.get("last_dirs", {}).get("rom") or self.var_romdir.get() or os.getcwd()
        d = filedialog.askdirectory(title=tr(self, "pick_rom_title"), initialdir=init)
        if not d: return
        self.config.setdefault("last_dirs", {})["rom"] = d
        self.var_romdir.set(d); self.config["rom_dir"] = d; save_json(self.config_path, self.config)
        self.refresh_rom_list()

    def pick_melonds(self):
        init = self.config.get("last_dirs", {}).get("melonds") or (Path(self.var_melonds.get()).parent.as_posix() if self.config.get("melonds_path") else os.getcwd())
        types = [("執行檔","*.exe;*.AppImage;*.bin;*.sh;*.app")]
        fp = filedialog.askopenfilename(title=tr(self, "pick_melonds_title"), filetypes=types, initialdir=init)
        if not fp: return
        self.config.setdefault("last_dirs", {})["melonds"] = str(Path(fp).parent)
        self.var_melonds.set(fp); self.config["melonds_path"] = fp; save_json(self.config_path, self.config)

    def pick_cover_for_selected(self):
        if not self.selected_game: messagebox.showinfo(APP_TITLE, tr(self, "tip_select")); return
        self._pick_cover_for(self.selected_game)

    def _pick_cover_for(self, rom_path: Path):
        init = self.config.get("last_dirs", {}).get("cover") or str(self.covers_path)
        fp = filedialog.askopenfilename(title=tr(self, "choose_cover"), filetypes=[("圖片","*.png;*.jpg;*.jpeg")], initialdir=init)
        if not fp: return
        self.config.setdefault("last_dirs", {})["cover"] = str(Path(fp).parent)
        src = Path(fp); dst = self.covers_path / (rom_path.stem + src.suffix.lower())
        try:
            dst.write_bytes(src.read_bytes())
            gid = game_id_for(rom_path)
            self.covers_map[gid] = str(dst)
            save_json(self.map_path, self.covers_map); save_json(self.config_path, self.config)
            self.refresh_rom_list()
        except Exception as e: messagebox.showerror("封面設定失敗", str(e))

    def rename_selected(self):
        if not self.selected_game: messagebox.showinfo(APP_TITLE, tr(self, "tip_select")); return
        self._rename_title(self.selected_game)

    def _rename_title(self, rom_path: Path):
        old = self._display_name_for(rom_path)
        top = tk.Toplevel(self)
        top.title(tr(self, "rename_title")); top.transient(self); top.grab_set()
        bg = getattr(self, "bg", "#0f1419"); fg = getattr(self, "fg", "#e6edf3")
        panel = getattr(self, "panel", "#1b2228")
        top.configure(bg=bg)
        frm = ttk.Frame(top); frm.pack(padx=16, pady=16, fill="both", expand=True)
        ttk.Label(frm, text=tr(self, "rename_prompt")).pack(anchor="w", pady=(0,8))
        var = tk.StringVar(value=old)
        ent = ttk.Entry(frm, textvariable=var, style="Dark.TEntry"); ent.pack(fill="x")
        btns = ttk.Frame(frm); btns.pack(fill="x", pady=(12,0))
        res = {"value": None}
        def ok(): res["value"] = var.get().strip(); top.destroy()
        def cancel(): top.destroy()
        ttk.Button(btns, text="確定", command=ok, style="Accent.TButton").pack(side="right")
        ttk.Button(btns, text="取消", command=cancel).pack(side="right", padx=(0,8))
        ent.focus_set()
        top.bind("<Return>", lambda e: ok()); top.bind("<Escape>", lambda e: cancel())
        self.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width()//2 - 180)
        y = self.winfo_rooty() + (self.winfo_height()//2 - 60)
        top.geometry(f"+{x}+{y}")
        self.wait_window(top)
        new = res["value"]
        if new is None: return
        gid = game_id_for(rom_path)
        self.titles_map[gid] = new.strip()
        save_json(self.titles_path, self.titles_map)
        self.refresh_rom_list()

    def pin_toggle_selected(self):
        if not self.selected_game:
            messagebox.showinfo(APP_TITLE, tr(self, "tip_select")); return
        try:
            files = set(self.config.get("pinned_files", []))
            k = self._pin_key(self.selected_game)
            if k in files:
                files.remove(k)
            else:
                files.add(k)
            self.config["pinned_files"] = sorted(files)
            save_json(self.config_path, self.config)
            self.refresh_rom_list()
            # 切換釘選狀態後，更新右側按鈕文字（Unpin/Pin）
            self._refresh_right_panel_texts()
        except Exception as e:
            messagebox.showerror("錯誤", str(e))

    def launch_selected(self):
        if not self.selected_game: messagebox.showinfo(APP_TITLE, tr(self, "tip_select")); return
        self._launch(self.selected_game)

    def _launch(self, rom_path: Path):
        melonds = self.var_melonds.get().strip() or self.config.get("melonds_path","").strip()
        if not melonds: messagebox.showwarning(tr(self,"warn_notset"), tr(self,"warn_set_melonds")); return
        if not Path(melonds).exists(): messagebox.showwarning(tr(self,"not_found"), f"{tr(self,'not_found')}: {melonds}"); return
        try:
            if platform.system()=="Darwin" and melonds.endswith(".app"):
                subprocess.Popen(["open","-a",melonds,str(rom_path)])
            else:
                subprocess.Popen([melonds, str(rom_path)])
        except Exception as e:
            messagebox.showerror(tr(self,"launch_failed"), str(e))

    def _reveal(self, rom_path: Path):
        try:
            if platform.system()=="Windows":
                subprocess.Popen(["explorer","/select,",str(rom_path)])
            elif platform.system()=="Darwin":
                subprocess.Popen(["open","-R",str(rom_path)])
            else:
                subprocess.Popen(["xdg-open", str(rom_path.parent)])
        except Exception as e:
            messagebox.showerror(tr(self,"open_folder_failed"), str(e))

    def _bind_mousewheel(self):
        def _on_mousewheel(event):
            if not self._scroll_enabled: return "break"
            delta = -1 * int(event.delta/120) * 30 if platform.system()=="Windows" else -1 * event.delta
            self.canvas.yview_scroll(int(delta/10), "units"); return "break"
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.canvas.bind_all("<Button-4>", _on_mousewheel)
        self.canvas.bind_all("<Button-5>", _on_mousewheel)

    def _refresh_scrollbar_style(self):
        try: self.scroll_y.configure(style="Dark.Vertical.TScrollbar"); self.scroll_y.update_idletasks()
        except Exception: pass

    def _on_gridframe_configure(self, event):
        try: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except Exception: pass
        self._update_scrollbar_visibility()

    def _update_scrollbar_visibility(self):
        try:
            bbox = self.canvas.bbox("all")
            if not bbox: return
            _, _, _, content_h = bbox
            canvas_h = self.canvas.winfo_height() or 1
            need = content_h > canvas_h + 2
            if need:
                self._scroll_enabled = True
                if not self.scroll_y.winfo_ismapped():
                    self.scroll_y.pack(side="right", fill="y")
            else:
                self._scroll_enabled = False
                if self.scroll_y.winfo_ismapped():
                    self.scroll_y.pack_forget()
                try: self.canvas.yview_moveto(0.0)
                except Exception: pass
            self._refresh_scrollbar_style()
        except Exception: pass

    def _apply_right_panel_width(self):
        try:
            cw = max(1, self.canvas.winfo_width() or 1)
            cols_bp, tw, th, gutter = self._active_breakpoint(cw)
            cover_w, cover_h = self._cover_box_for_tile(tw, th)
            target_w = int(cover_w * 2.0)
            want = max(380, target_w + 24)
            try:
                if getattr(self, "_last_right_width", None) is None or abs(int(self._last_right_width) - int(want)) > 6:
                    self.right_panel.configure(width=want)
                    self._last_right_width = want
            except Exception:
                pass
            try:
                wrap = max(200, want - 30)
                self.lbl_title.configure(wraplength=wrap)
                self.lbl_path.configure(wraplength=wrap)
                self.lbl_code.configure(wraplength=wrap)
            except Exception:
                pass
        except Exception:
            pass

    def _handle_canvas_resize(self):
        try: self.canvas.itemconfigure(self.grid_window, width=self.canvas.winfo_width())
        except Exception: pass
        if self.config.get("view_mode","grid") == "list":
            self._update_list_wrap(); return
        cw = max(1, self.canvas.winfo_width() or 1)
        cols_bp, tw, th, gutter = self._active_breakpoint(cw)
        cols = max(1, int((cw + gutter) // (tw + gutter)))
        if (cols, tw, th, gutter) != self._last_grid_bp:
            if getattr(self, "_relayout_in_progress", False): return
            self._relayout_in_progress = True
            try:
                self.refresh_rom_list()
            finally:
                self._relayout_in_progress = False
            self._apply_right_panel_width()

    def _on_root_resized(self, event):
        if getattr(self, "_root_cfg_id", None):
            try: self.after_cancel(self._root_cfg_id)
            except Exception: pass
        self._root_cfg_id = self.after(80, self._handle_canvas_resize)

if __name__ == "__main__":
    app = LauncherApp()
    app.mainloop()
