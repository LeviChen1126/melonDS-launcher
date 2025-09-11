#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, json, subprocess, platform, hashlib, shutil, struct, ctypes
from pathlib import Path
from typing import Any, Optional, Dict, List, Tuple

from PySide6.QtCore import (Qt, QSize, QRect, QPoint, QSortFilterProxyModel,
                            QAbstractListModel, QModelIndex, Signal, QObject, QEvent, QRegularExpression)
from PySide6.QtGui import (QGuiApplication, QIcon, QPixmap, QPainter, 
                           QFont, QAction, QActionGroup, QCursor, QFontMetrics, QColor, QPalette, QImage)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QListView, QFileDialog, QMessageBox,
    QLabel, QPushButton, QLineEdit, QToolBar, QStyle, QStatusBar, QHBoxLayout,
    QVBoxLayout, QSplitter, QSlider, QFrame, QMenu, QStyledItemDelegate, QSizePolicy, QStyleOptionSlider,
    QInputDialog
)

APP_TITLE = "melonDS Launcher v2.0.0"
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
    "lang": "en",
    "thumb_dir": "covers/.thumb",
    "thumb_size": 256,
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
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        QMessageBox.critical(None, "儲存失敗", f"{path}\n{e}")

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

# ----------- Model 層（以顯示 Title 排序/搜尋） ----------- #
class Roles:
    Title = Qt.UserRole + 1
    Path = Qt.UserRole + 2
    Cover = Qt.UserRole + 3
    Pinned = Qt.UserRole + 4
    GameCode = Qt.UserRole + 5

class GameItem:
    def __init__(self, path: Path, title: str, cover: Optional[Path], pinned: bool):
        self.path = path
        self.title = title
        self.cover = cover
        self.pinned = pinned

class GameListModel(QAbstractListModel):
    def __init__(self, items: List[GameItem]):
        super().__init__()
        self._items = items

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._items)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        g = self._items[index.row()]
        if role in (Qt.DisplayRole, Roles.Title):
            return g.title
        if role == Roles.Path:
            return str(g.path).replace("\\", "/")
        if role == Roles.Cover:
            return str(g.cover) if g.cover else ""
        if role == Roles.Pinned:
            return g.pinned
        if role == Roles.GameCode:
            return game_id_for(g.path)
        return None

    def item(self, row: int) -> GameItem:
        return self._items[row]

    def setPinned(self, row: int, val: bool):
        g = self._items[row]
        g.pinned = val
        idx = self.index(row, 0)
        self.dataChanged.emit(idx, idx, [Roles.Pinned])

    def setTitle(self, row: int, title: str):
        g = self._items[row]
        g.title = title
        idx = self.index(row, 0)
        self.dataChanged.emit(idx, idx, [Qt.DisplayRole, Roles.Title])

# ----------- 主視窗 ----------- #
class LauncherApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1280, 820)

        self.config_path = Path(CONFIG_FILE)
        self.config_dir = Path("config"); self.config_dir.mkdir(exist_ok=True)
        self.config = load_json(self.config_path, DEFAULT_CONFIG.copy())
        self.lang = self.config.get("lang", "zh")

        # sanitize pinned list
        try:
            files = set(self.config.get("pinned_files") or [])
            self.config["pinned_files"] = sorted(files)
            save_json(self.config_path, self.config)
        except Exception:
            pass

        self.covers_path = Path(self.config.get("covers_dir", "covers")); self.covers_path.mkdir(parents=True, exist_ok=True)
        self.map_path = Path(COVERS_MAP_FILE); self.covers_map = load_json(self.map_path, {})
        self.titles_path = Path(TITLES_MAP_FILE); self.titles_map = load_json(self.titles_path, {})
        # 縮圖輸出資料夾（可在設定檔調整）
        self.thumb_path = Path(self.config.get("thumb_dir", "covers/.thumb"))
        self.thumb_path.mkdir(parents=True, exist_ok=True)


        self._icons: Dict[str, QIcon] = {}
        self._thumb_cache: Dict[Tuple[str,int,int], QPixmap] = {}
        self._nds_icon_cache: Dict[Tuple[str,int], QPixmap] = {}
        self._view_mode = self.config.get("view_mode", "grid")
        # 右欄寬度基準：只在啟動時掃描一次（不隨後續 refresh 改變）
        self._panel_base_s: float = float(self.config.get("ui_scale", 1.0))
        self._panel_base_cover_w: int | None = None
        self._only_pinned = bool(self.config.get("only_pinned", False))

        # 拖曳捲動狀態（反向拖曳）
        self._drag_scroll_active = False
        self._drag_last_pos = None
        self._drag_ctx = None

        self._build_ui()
        self._set_app_icon()
        self._compute_panel_base_width_once()
        self.refresh_rom_list()

    # ---------- Assets 與 Icon ---------- #
    def _resolve_asset_path(self, filename: str) -> Path:
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
        return Path(filename)

    def _set_app_icon(self):
        ico = self._resolve_asset_path("assets/nds.png")
        if ico.exists():
            self.setWindowIcon(QIcon(str(ico)))
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("melonDS.Launcher")

    def _load_icon(self, name: str):
        p = self._resolve_asset_path(f"assets/{name}.png")
        if not p.exists():
            return None
        icon = QIcon(QPixmap(str(p)))
        return icon

    # ---------- 介面 ---------- #
    def _build_ui(self):
        # Toolbar
        tb = QToolBar()
        self.addToolBar(tb)
        self.toolbar = tb
        self.toolbar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.toolbar.setLayoutDirection(Qt.LeftToRight)
        self.toolbar.setMovable(False)


        # ROM dir
        self.lbl_rom = QLabel(tr(self, "rom_dir"))
        tb.addWidget(self.lbl_rom)
        self.ed_rom = QLineEdit(self.config.get("rom_dir",""))
        self.ed_rom.setFixedWidth(420)
        tb.addWidget(self.ed_rom)

        icon_browse = self._load_icon("browse")
        self.act_pick_rom = QAction(icon_browse or QIcon(), tr(self, "browse"), self)
        self.act_pick_rom.triggered.connect(self.pick_rom_dir)
        tb.addAction(self.act_pick_rom)

        # melonDS path
        tb.addSeparator()
        self.lbl_mel = QLabel(tr(self, "melonds"))
        tb.addWidget(self.lbl_mel)
        self.ed_mel = QLineEdit(self.config.get("melonds_path",""))
        self.ed_mel.setFixedWidth(320)
        tb.addWidget(self.ed_mel)

        self.act_pick_mel = QAction(icon_browse or QIcon(), tr(self, "browse"), self)
        self.act_pick_mel.triggered.connect(self.pick_melonds)
        tb.addAction(self.act_pick_mel)

        # search
        tb.addSeparator()
        self.lbl_search = QLabel(tr(self, "search"))
        tb.addWidget(self.lbl_search)
        self.ed_search = QLineEdit()
        self.ed_search.setFixedWidth(240)
        self.ed_search.textChanged.connect(self._on_search_changed)
        tb.addWidget(self.ed_search)

        # view buttons
        tb.addSeparator()
        self.lbl_view = QLabel(tr(self, "view"))
        tb.addWidget(self.lbl_view)
        icon_grid = self._load_icon("grid")
        icon_list = self._load_icon("list")

        view_group = QActionGroup(self)
        view_group.setExclusive(True)

        self.act_grid = QAction(icon_grid or QIcon(), "Grid", self)
        self.act_list = QAction(icon_list or QIcon(), "List", self)
        self.act_grid.setCheckable(True)
        self.act_list.setCheckable(True)

        view_group.addAction(self.act_grid)
        view_group.addAction(self.act_list)

        self.act_grid.triggered.connect(lambda: self._set_view_mode("grid"))
        self.act_list.triggered.connect(lambda: self._set_view_mode("list"))
        tb.addAction(self.act_grid)
        tb.addAction(self.act_list)

        # 初始選中
        if self._view_mode == "grid":
            self.act_grid.setChecked(True)
        else:
            self.act_list.setChecked(True)

        # 樣式：選中的按鈕綠色
        tb.setStyleSheet("""
        QToolButton:checked {
            background-color: #28a745;
            color: white;
            border-radius: 4px;
        }
        QToolButton:checked:hover {
            background-color: #186029;
        }
        """)

        # zoom
        tb.addSeparator()
        self.lbl_zoom = QLabel(tr(self, "zoom"))
        tb.addWidget(self.lbl_zoom)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(60, 220)
        self.slider.setValue(int(float(self.config.get("ui_scale", 1.0)) * 100))
        self.slider.valueChanged.connect(self._on_zoom_changed)
        self.slider.setFixedWidth(220)
        tb.addWidget(self.slider)
        self.lbl_zoom_pct = QLabel(f"{self.slider.value()}%")
        tb.addWidget(self.lbl_zoom_pct)
        
        # 建立 Label 後，設定字體大小（例如固定 12pt）
        font = self.font()
        font.setPointSize(12)

        for lbl in [self.lbl_rom, self.lbl_mel, self.lbl_search, self.lbl_view, self.lbl_zoom]:
            lbl.setFont(font)

        # refresh
        icon_refresh = self._load_icon("refresh")
        self.act_refresh = QAction(icon_refresh or QIcon(), tr(self, "refresh"), self)
        self.act_refresh.triggered.connect(self.refresh_rom_list)
        tb.addAction(self.act_refresh)

        # only pinned toggle
        icon_pin = self._load_icon("pin")
        self.act_only_pin = QAction(icon_pin or QIcon(), tr(self, "only_pinned_tip"), self)
        self.act_only_pin.setCheckable(True)
        self.act_only_pin.setChecked(self._only_pinned)
        self.act_only_pin.triggered.connect(self._toggle_only_pinned)
        tb.addAction(self.act_only_pin)

        # spacer: push following items (like refresh) to the far right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        spacer.setMinimumWidth(0)
        tb.addWidget(spacer)

        # language toggle
        tb.addSeparator()
        icon_lang = self._load_icon("lang")
        self.act_lang = QAction(icon_lang or QIcon(), tr(self, "language"), self)
        self.act_lang.triggered.connect(self._toggle_lang)
        tb.addAction(self.act_lang)

        # Central layout: left view + right panel
        central = QWidget()
        lay = QHBoxLayout(central)
        lay.setContentsMargins(8,8,8,8)
        self.setCentralWidget(central)

        self.view = QListView()
        self.view.setSelectionMode(QListView.SingleSelection)
        self.view.setSelectionBehavior(QListView.SelectItems)
        self.view.clicked.connect(lambda idx: self._refresh_details_panel())
        self.view.setUniformItemSizes(True)
        self.view.setResizeMode(QListView.Adjust)
        self.view.setSpacing(12)
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self._on_context_menu)
        self.view.doubleClicked.connect(self._double_clicked)

        # 反向拖曳捲動：在 viewport 上裝 event filter
        self.view.viewport().installEventFilter(self)

        # Right panel
        # === Right panel（Top-aligned container；封面→標題→路徑→ID→分隔線→按鈕） ===
        self.right_panel = QFrame()
        self.right_panel.setFrameShape(QFrame.NoFrame)
        rlay = QVBoxLayout(self.right_panel)
        rlay.setContentsMargins(12, 12, 12, 12)
        rlay.setSpacing(0)  # 外層不留縫，縫隙交給內層控制

        # 內層：所有元件塞進同一個 VBox，並置頂
        info_box = QFrame()
        info_lay = QVBoxLayout(info_box)
        s = float(self.config.get("ui_scale", 1.0))
        info_lay.setContentsMargins(0, 0, 0, 0)
        info_lay.setSpacing(int(8 * s))

        # 封面
        self.right_cover = QLabel("")
        self.right_cover.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.right_cover.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.right_cover.setScaledContents(False)
        info_lay.addWidget(self.right_cover, 0, Qt.AlignLeft)

        # 標題
        self.lbl_title = QLabel(tr(self, "not_selected"))
        self.lbl_title.setWordWrap(True)
        f = self.font()
        f.setPointSize(max(8, int((f.pointSize()+4) * s)))
        f.setBold(True)
        self.lbl_title.setFont(f)
        self.lbl_title.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        info_lay.addWidget(self.lbl_title)
        # NDS 檔案內建 32x32 圖示（banner icon），顯示於標題下方
        self.right_nds_icon = QLabel("")
        self.right_nds_icon.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.right_nds_icon.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        info_lay.addWidget(self.right_nds_icon, 0, Qt.AlignLeft)


        # 路徑
        self.lbl_path = QLabel("")
        self.lbl_path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_path.setWordWrap(True)
        self.lbl_path.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        info_lay.addWidget(self.lbl_path)

        # ID
        self.lbl_code = QLabel("")
        self.lbl_code.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_code.setWordWrap(True)
        self.lbl_code.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        info_lay.addWidget(self.lbl_code)
        self._apply_right_label_fonts()

        # 分隔線（固定高度）
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        sep.setFixedHeight(1)
        info_lay.addWidget(sep)

        # 按鈕群
        btn_box = QFrame()
        btn_lay = QVBoxLayout(btn_box)
        btn_lay.setContentsMargins(0, 8, 0, 0)
        btn_lay.setSpacing(int(6 * s))

        self.btn_play = QPushButton(tr(self, "start_game"))
        self.btn_play.clicked.connect(self.launch_selected)
        btn_lay.addWidget(self.btn_play, 0, Qt.AlignLeft)

        self.btn_choose_cover = QPushButton(tr(self, "choose_cover"))
        self.btn_choose_cover.clicked.connect(self.pick_cover_for_selected)
        btn_lay.addWidget(self.btn_choose_cover, 0, Qt.AlignLeft)

        self.btn_pin = QPushButton(tr(self, "pin_this"))
        self.btn_pin.clicked.connect(self.pin_toggle_selected)
        btn_lay.addWidget(self.btn_pin, 0, Qt.AlignLeft)

        self.btn_rename = QPushButton(tr(self, "rename_title"))
        self.btn_rename.clicked.connect(self.rename_selected)
        btn_lay.addWidget(self.btn_rename, 0, Qt.AlignLeft)

        info_lay.addWidget(btn_box)
        self._apply_right_button_scale()

        # 把 info_box 放到右欄，並在底下放一個 stretch 把剩餘空間吃掉（確保元件群靠上）
        rlay.addWidget(info_box, 0, Qt.AlignTop)
        rlay.addStretch(1)

        # 佈局：左清單、右資訊
        lay.addWidget(self.view, 1)
        lay.addWidget(self.right_panel, 0)
        # Status
        self.setStatusBar(QStatusBar())

        # Model / Proxy
        self._items: List[GameItem] = []
        self.model = GameListModel(self._items)
        self.proxy = TitleSearchSortProxy(self)
        self.proxy.setSourceModel(self.model)
        self.view.setModel(self.proxy)

        # 點選即可更新右側資訊
        self.view.selectionModel().currentChanged.connect(lambda _c,_p: self._refresh_details_panel())

        # Delegate
        self.delegate = CardDelegate(self)
        self.view.setItemDelegate(self.delegate)
        self._apply_view_mode()  # set icon/list

        # Dark palette近似現有風格
        if self.config.get("dark_mode", True):
            self._apply_dark_palette()


    def _compute_panel_base_width_once(self):
        """在啟動 GUI 時掃描一次所有 ROM 的封面，記錄『放大圖』中最寬的寬度作為右欄寬度基準。
        之後只會用這個基準搭配 ui_scale 做等比例縮放，不再重新掃描。"""
        if self._panel_base_cover_w is not None:
            return
        s0 = self._panel_base_s  # 啟動時的 scale
        max_w = 0
        try:
            # 用掃描器直接抓 ROM 路徑（不依賴 model 是否已就緒）
            paths = self._scan_roms()
            for p in paths:
                cover = self._cover_path_for(p)
                pm = self._get_thumb(cover, grid=True, double=True, overlay_pin=False)
                if pm:
                    max_w = max(max_w, pm.width())
        except Exception:
            pass
        # fallback：若沒有任何封面，給一個和最小寬相近的基準（不含 padding）
        if max_w <= 0:
            max_w = int(260 * s0)
        self._panel_base_cover_w = max_w


    def _apply_dark_palette(self):
        pal = self.palette()
        pal.setColor(QPalette.Window, QColor(0,0,0))
        pal.setColor(QPalette.WindowText, QColor(255,255,255))
        pal.setColor(QPalette.Base, QColor(0,0,0))
        pal.setColor(QPalette.AlternateBase, QColor(16,16,16))
        pal.setColor(QPalette.ToolTipBase, QColor(32,32,32))
        pal.setColor(QPalette.ToolTipText, QColor(255,255,255))
        pal.setColor(QPalette.Text, QColor(230,230,230))
        pal.setColor(QPalette.Button, QColor(0,0,0))
        pal.setColor(QPalette.ButtonText, QColor(255,255,255))
        pal.setColor(QPalette.BrightText, QColor(255,0,0))
        self.setPalette(pal)

    # ---------- 行為 ---------- #


    def _apply_right_label_fonts(self, base_title=16, base_path=12, base_code=12):

        """讓右欄字體跟著 ui_scale 連動"""

        s = float(self.config.get("ui_scale", 0.8))

        # 標題
        f_title = QFont(self.font())
        f_title.setBold(True)
        f_title.setPointSize(int(base_title * s))
        self.lbl_title.setFont(f_title)
        self.lbl_title.setStyleSheet("color: #FFFFFF;")

        # 路徑
        f_path = QFont(self.font())
        f_path.setPointSize(int(base_path * s))
        self.lbl_path.setFont(f_path)
        self.lbl_path.setStyleSheet("color: #AAAAAA;")

        # ID
        f_code = QFont(self.font())
        f_code.setPointSize(int(base_code * s))
        self.lbl_code.setFont(f_code)
        self.lbl_code.setStyleSheet("color: #AAAAAA;")


    def _apply_right_button_scale(self, base_font=12, base_height=32, base_hpadding=12):

        """讓右欄四個按鈕（含字體）隨 ui_scale 調整"""
        s = float(self.config.get("ui_scale", 1.0))
        f_btn = QFont(self.font())
        f_btn.setPointSize(int(base_font * s))
        pad_v = int(6 * s)
        pad_h = int(base_hpadding * s)
        h = int(max(base_height * s, 24))

        for btn in [self.btn_play, self.btn_choose_cover, self.btn_rename, self.btn_pin]:

            btn.setFont(f_btn)
            btn.setMinimumHeight(h)

            # 用樣式控制左右 padding；避免覆蓋其他樣式，只設定 padding
            btn.setStyleSheet(f"padding: {pad_v}px {pad_h}px;")

        # 開始遊戲：背景綠色，文字白色，含 hover/pressed 狀態
        self.btn_play.setStyleSheet(
            f"""
                QPushButton {{
                    padding: {pad_v}px {pad_h}px;
                    background-color: #28a745;
                    color: white;
                    border: none;
                    border-radius: {int(6 * s)}px;
                }}
                QPushButton:hover {{
                    background-color: #186029;
                }}
                QPushButton:pressed {{
                    background-color: #0d3416;
                }}
            """
        )

    def _on_zoom_changed(self, val: int):
        self.lbl_zoom_pct.setText(f"{val}%")
        s = max(60, min(220, int(val))) / 100.0
        self.config["ui_scale"] = s
        save_json(self.config_path, self.config)
        # 調整清單呈現
        self._apply_view_mode()
        self.view.viewport().update()
        # 右側標題字體也跟著縮放
        f = self.lbl_title.font(); f.setPointSize(max(8, int((self.font().pointSize()+4) * s)))
        f.setBold(True); self.lbl_title.setFont(f)
        self._apply_right_label_fonts()
        self._apply_right_button_scale()
        self._update_right_cover_size()
        self._update_right_nds_icon()

    def _on_search_changed(self, txt: str):
        self.proxy.setFilterString(txt)

    def _set_view_mode(self, mode: str):
        self._view_mode = mode
        self.config["view_mode"] = mode
        save_json(self.config_path, self.config)
        self._apply_view_mode()
        self.view.viewport().update()

    def _apply_view_mode(self):
        s = float(self.config.get("ui_scale", 1.0))
        if self._view_mode == "grid":
            self.view.setViewMode(QListView.IconMode)
            self.view.setSpacing(int(12*s))
            self.view.setIconSize(QSize(int(160*s), int(140*s)))
        else:
            self.view.setViewMode(QListView.ListMode)
            self.view.setSpacing(int(6*s))
            self.view.setIconSize(QSize(int(148*s), int(112*s)))

    def _toggle_lang(self):
        self.lang = "en" if self.lang == "zh" else "zh"
        self.config["lang"] = self.lang
        save_json(self.config_path, self.config)
        # 更新 toolbar/右側文字
        self.lbl_rom.setText(tr(self, "rom_dir"))
        self.lbl_mel.setText(tr(self, "melonds"))
        self.lbl_search.setText(tr(self, "search"))
        self.lbl_view.setText(tr(self, "view"))
        self.lbl_zoom.setText(tr(self, "zoom"))
        self.act_lang.setText(tr(self, "language"))
        self.act_only_pin.setText(tr(self, "only_pinned_tip"))
        self.act_refresh.setText(tr(self, "refresh"))
        self.btn_play.setText(tr(self, "start_game"))
        self.btn_choose_cover.setText(tr(self, "choose_cover"))
        self.btn_rename.setText(tr(self, "rename_title"))
        # pin button會在選取時同步更新

        if not self._selected_index():
            self.lbl_title.setText(tr(self, "not_selected"))

        # code label refresh
        self._refresh_details_panel()

    def _toggle_only_pinned(self):
        self._only_pinned = not self._only_pinned
        self.config["only_pinned"] = self._only_pinned
        save_json(self.config_path, self.config)
        self.refresh_rom_list()

    def _selected_index(self) -> Optional[QModelIndex]:
        idx = self.view.currentIndex()
        return idx if idx.isValid() else None

    def _select_path(self, path_str: str):
        """在重新整理列表後，根據 Roles.Path 重新選取指定路徑的遊戲。"""
        target = (path_str or "").replace("\\", "/")
        try:
            rows = self.proxy.rowCount()
        except Exception:
            rows = 0
        for r in range(rows):
            idx = self.proxy.index(r, 0)
            p = self.proxy.data(idx, Roles.Path) or ""
            if p == target:
                self.view.setCurrentIndex(idx)
                self.view.scrollTo(idx, QListView.PositionAtCenter)
                break
        self._refresh_details_panel()

    def _current_item(self) -> Optional[GameItem]:
        idx = self._selected_index()
        if not idx: return None
        src = self.proxy.mapToSource(idx)
        return self.model.item(src.row())
    
    def _fmt_title_grid(self, title: str) -> str:
        """ Grid 模式：用 '_' 當作換行，且不顯示 '_' """
        parts = [p for p in (title or "").split("_") if p]
        return "\n".join(parts) if parts else (title or "")

    def _fmt_title_list(self, title: str) -> str:
        """ List 模式：單行顯示，移除 '_'（不加空白） """
        return (title or "").replace("_", "")

    def _compute_scrollbar_span(self, sb) -> int:
            """ 回傳垂直 ScrollBar 可用拖曳範圍(span、像素) """
            try:
                opt = QStyleOptionSlider()
                opt.initFrom(sb)
                opt.orientation = Qt.Vertical
                opt.minimum = sb.minimum()
                opt.maximum = sb.maximum()
                opt.sliderPosition = sb.sliderPosition()
                opt.sliderValue = sb.value()
                opt.pageStep = sb.pageStep()
                opt.upsideDown = False
                opt.rect = sb.rect()
                style = sb.style()
                groove = style.subControlRect(QStyle.CC_ScrollBar, opt, QStyle.SC_ScrollBarGroove, sb)
                handle = style.subControlRect(QStyle.CC_ScrollBar, opt, QStyle.SC_ScrollBarSlider, sb)
                span = max(0, groove.height() - handle.height())
                if span <= 0:
                    # 退而求其次：視口高度（避免偶發 style 回傳 0）
                    span = max(1, self.view.viewport().height() - 20)
                return span
            except Exception:
                return max(1, self.view.viewport().height() - 20)

    def eventFilter(self, obj, event):
            """在清單內按住左鍵拖曳：向上拖 -> 向下捲；向下拖 -> 向上捲（Grid/List 皆適用）。
            速度/位移對應採用 QStyle 的 slider 對映，與拖拉 scrollbar 一致。"""
            try:
                if obj is self.view.viewport():
                    et = event.type()
                    # Press：啟動
                    if et == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                        self._drag_scroll_active = True
                        self._drag_last_pos = event.position().toPoint() if hasattr(event,"position") else event.pos()
                        sb = self.view.verticalScrollBar()
                        if sb is not None:
                            # 只有 List 模式才需要預先計算 slider 對映參數
                            if self._view_mode == "list":
                                span = self._compute_scrollbar_span(sb)
                                pos0 = QStyle.sliderPositionFromValue(sb.minimum(), sb.maximum(), sb.sliderPosition(), span, False)
                                press_y0 = self._drag_last_pos.y()
                                self._drag_ctx = {"pos0": pos0, "span": span, "press_y0": press_y0}
                            else:
                                self._drag_ctx = None
                        return False  # 不中斷選取

                    # Move：依檢視模式分開處理
                    if et == QEvent.MouseMove and self._drag_scroll_active:
                        pos_now = event.position().toPoint() if hasattr(event,"position") else event.pos()

                        sb = self.view.verticalScrollBar()
                        if sb is not None:
                            if self._view_mode == "grid":
                                # --- Grid 模式：滑鼠像素 = 捲動像素 ---
                                dy = pos_now.y() - (self._drag_last_pos.y() if self._drag_last_pos else pos_now.y())
                                self._drag_last_pos = pos_now
                                speed = 1.5  # 可微調靈敏度，例如 0.8 或 1.2
                                sb.setValue(sb.value() - int(dy * speed))  # 往上拖(dy<0) => 捲下去
                            else:
                                # --- List 模式：維持與 scrollbar 對映一致 ---
                                self._drag_last_pos = pos_now
                                if self._drag_ctx:
                                    span = self._drag_ctx.get("span") or self._compute_scrollbar_span(sb)
                                    pos0 = self._drag_ctx.get("pos0", 0)
                                    dy = pos_now.y() - self._drag_ctx.get("press_y0", pos_now.y())
                                    speed = 0.15   # >1.0 表示更靈敏（移動少就捲動多），<1.0 表示更鈍
                                    dy = int(dy * speed)
                                    pos = max(0, min(span, pos0 - dy))  # 往上拖(dy<0) => pos 增加
                                    new_val = QStyle.sliderValueFromPosition(sb.minimum(), sb.maximum(), pos, span, False)
                                    sb.setSliderPosition(new_val)

                        return True  # 吃掉 move，避免框選

                    # Release / Leave：關閉（原樣保留）
                    if et in (QEvent.MouseButtonRelease, QEvent.Leave):
                        self._drag_scroll_active = False
                        self._drag_last_pos = None
                        self._drag_ctx = None
                        return False
            except Exception:
                self._drag_scroll_active = False
                self._drag_last_pos = None
                self._drag_ctx = None
            return super().eventFilter(obj, event)

    def _on_context_menu(self, pos: QPoint):
        idx = self.view.indexAt(pos)
        if not idx.isValid():
            return
        self.view.setCurrentIndex(idx)
        g = self._current_item()
        if not g: return
        m = QMenu(self)
        a_play = m.addAction(tr(self, "start_game"))
        a_cover = m.addAction(tr(self, "choose_cover"))
        a_pin = m.addAction(tr(self, "unpin") if g.pinned else tr(self, "pin_this"))
        a_rename = m.addAction(tr(self, "rename_title"))
        m.addSeparator()
        a_reveal = m.addAction(tr(self, "context_reveal"))
        act = m.exec(QCursor.pos())
        if act == a_play:
            self._launch(g.path)
        elif act == a_cover:
            self._pick_cover_for(g.path)
        elif act == a_pin:
            self.pin_toggle_selected()
        elif act == a_rename:
            self._rename_title(g.path)
        elif act == a_reveal:
            self._reveal(g.path)

    def _double_clicked(self, idx: QModelIndex):
        g = self._current_item()
        if not g: return
        self._launch(g.path)

    # ---- 檔案/資料邏輯（沿用原始 JSON 結構） ---- #
    def _ensure_title_for(self, rom_path: Path):
        gid = game_id_for(rom_path)
        if not self.titles_map.get(gid):
            self.titles_map[gid] = rom_path.stem
            save_json(self.titles_path, self.titles_map)

    def _display_name_for(self, rom_path: Path) -> str:
        self._ensure_title_for(rom_path)
        gid = game_id_for(rom_path)
        name = self.titles_map.get(gid) or rom_path.stem
        return name

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
        return p.name in files

    def _scan_roms(self) -> List[Path]:
        rom_dir = Path(self.ed_rom.text().strip() or self.config.get("rom_dir",""))
        query = (self.ed_search.text() or "").lower().strip()
        out: List[Path] = []
        if rom_dir and rom_dir.exists():
            for p in sorted(rom_dir.glob("**/*")):
                if p.is_file() and p.suffix in SUPPORTED_EXTS:
                    self._ensure_title_for(p)
                    disp = self._display_name_for(p)
                    name_for_search = (disp + " " + p.name).lower()
                    if query and (query not in name_for_search):
                        continue
                    out.append(p)
        if self._only_pinned:
            out = [p for p in out if self._is_pinned(p)]
        out = sorted(out, key=lambda x: (0 if self._is_pinned(x) else 1, self._display_name_for(x).lower()))
        return out

    def refresh_rom_list(self):
        paths = self._scan_roms()
        items: List[GameItem] = []
        for p in paths:
            items.append(GameItem(
                path=p,
                title=self._display_name_for(p),
                cover=self._cover_path_for(p),
                pinned=self._is_pinned(p)
            ))
        # reset model
        self.model.beginResetModel()
        self.model._items = items
        self.model.endResetModel()
        self.proxy.invalidate()
        self.statusBar().showMessage(f"掃描完成：{len(items)} 個 ROM", 3000)
        self._refresh_details_panel()
        self._update_right_cover_size()
        self._update_right_nds_icon()

    def _refresh_details_panel(self):
        g = self._current_item()
        if not g:
            self.lbl_title.setText(tr(self, "not_selected"))
            self.lbl_path.setText("")
            self.lbl_code.setText("")
            self.right_cover.setPixmap(QPixmap())
            self.right_nds_icon.setPixmap(QPixmap())
            self.btn_pin.setText(tr(self, "pin_this"))
            return
        self.lbl_title.setText((g.title or g.path.stem).replace("_", ""))
        self.lbl_path.setText(str(g.path).replace("\\", "/"))
        gid = game_id_for(g.path)
        t, code = read_nds_info(g.path)
        extra = f"（{code}）" if code else ""
        self.lbl_code.setText(f"{tr(self,'id_label')}{gid}{extra}")
        self.btn_pin.setText(tr(self, "unpin") if g.pinned else tr(self, "pin_this"))
        # nds icon + cover
        self._update_right_nds_icon()
        self._update_right_cover_size()
        self._update_right_nds_icon()

    
    # ---- NDS Banner Icon 解碼與右欄更新 ---- #
    def _get_nds_icon_pixmap(self, rom_path: Path, scale: int) -> Optional[QPixmap]:
        """
        從 .nds 檔讀取 32x32 的 banner icon：4bpp/16色、RGB555 調色盤。
        讀取成功回傳放大後的 QPixmap，並快取；失敗回傳 None。
        """
        try:
            key = (str(rom_path), int(scale))
            if key in self._nds_icon_cache:
                return self._nds_icon_cache[key]
            with open(rom_path, "rb") as f:
                head = f.read(0x200)
                if len(head) < 0x200:
                    return None
                # 0x68: icon/banner 在檔案中的位移（uint32 little-endian）
                (banner_off,) = struct.unpack("<I", head[0x68:0x6C])
                if banner_off == 0:
                    return None
                # 0x20: 32x32, 4bpp, 共 512 bytes 的像素資料（分 16 個 8x8 tiles）
                f.seek(banner_off + 0x20)
                tile_bytes = f.read(512)
                if len(tile_bytes) != 512:
                    return None
                # 0x220: 16 色調色盤（RGB555, 32 bytes）
                f.seek(banner_off + 0x220)
                pal_bytes = f.read(32)
                if len(pal_bytes) != 32:
                    return None

            # 轉調色盤為 RGBA
            palette = []
            for i in range(16):
                v = pal_bytes[2*i] | (pal_bytes[2*i+1] << 8)
                r = (v & 0x1F) * 255 // 31
                g = ((v >> 5) & 0x1F) * 255 // 31
                b = ((v >> 10) & 0x1F) * 255 // 31
                a = 0 if i == 0 else 255  # index 0 視為透明
                palette.append((r, g, b, a))

            # 解 4bpp tiled: 4x4 tiles，每 tile 8x8；每 tile 32 bytes
            img = QImage(32, 32, QImage.Format_ARGB32)
            for ty in range(4):
                for tx in range(4):
                    base = (ty * 4 + tx) * 32
                    for py in range(8):
                        for px in range(8):
                            p_index = py * 8 + px
                            byte = tile_bytes[base + (p_index // 2)]
                            idx = (byte & 0x0F) if (p_index % 2) == 0 else ((byte >> 4) & 0x0F)
                            r, g, b, a = palette[idx]
                            x = tx * 8 + px
                            y = ty * 8 + py
                            img.setPixel(x, y, (a << 24) | (r << 16) | (g << 8) | b)

            pm = QPixmap.fromImage(img)
            if scale and scale != 32:
                pm = pm.scaled(scale, scale, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._nds_icon_cache[key] = pm
            return pm
        except Exception:
            return None

    def _update_right_nds_icon(self):
        """依目前選取的 ROM 刷新右欄的 .nds 內建圖示。"""
        if not hasattr(self, "right_nds_icon"):
            return
        g = self._current_item()
        if not g:
            self.right_nds_icon.setPixmap(QPixmap())
            return
        s = float(self.config.get("ui_scale", 1.0))
        # 讓 100% 時約 64px，隨 ui_scale 伸縮
        size = max(24, int(48 * s))
        pm = self._get_nds_icon_pixmap(g.path, size)
        if pm:
            self.right_nds_icon.setPixmap(pm)
        else:
            self.right_nds_icon.setPixmap(QPixmap())

    
    def _update_right_cover_size(self):
        """右欄寬度只依啟動時掃描的『最寬封面』做等比例縮放；不再隨選取/列表變動。
        畫面上仍會顯示目前選取遊戲的封面，但寬度基準固定來自啟動時的最大封面寬。"""
        s = float(self.config.get("ui_scale", 1.0))
        min_width = int(300 * s)    # 右欄最小寬度，避免文字/按鈕擠壓
        padding = int(40 * s)       # 右欄內邊距

        # 基準寬（不含 padding）：來自啟動時掃描的最大封面「放大圖」寬度
        if self._panel_base_cover_w is None:
            # 萬一還沒掃描到，做一次；理論上在 __init__ 會先算過
            self._compute_panel_base_width_once()

        base_w = self._panel_base_cover_w or int(260 * self._panel_base_s)

        # 依目前 s 對基準寬做等比例縮放（啟動時 s0 -> 現在 s）
        ratio = s / max(0.0001, self._panel_base_s)
        scaled_w = int(base_w * ratio)

        # 右欄最終寬度
        panel_w = max(scaled_w + padding, min_width)
        self.right_panel.setFixedWidth(panel_w)

        # 顯示目前選取的封面（不影響寬度）
        g_sel = self._current_item()
        if g_sel:
            pm = self._get_thumb(g_sel.cover, grid=True, double=True, overlay_pin=g_sel.pinned)
            self.right_cover.setPixmap(pm or QPixmap())
        else:
            self.right_cover.setPixmap(QPixmap())
        return



# ---- 縮圖檔案（持久化在 thumb_dir） ---- #
    def _thumb_path_for(self, cover_path: Path) -> Path:
        """回傳對應的縮圖輸出路徑（固定 .jpg）。"""
        return self.thumb_path / f"{cover_path.stem}.jpg"

    def _ensure_thumb_for(self, cover_path):
        """若縮圖不存在則建立；成功回傳縮圖路徑。"""
        if not cover_path:
            return None
        p = Path(cover_path)
        if not p.exists():
            return None
        outp = self._thumb_path_for(p)
        try:
            if outp.exists():
                return outp
            size = int(self.config.get("thumb_size", 256))
            img = QImage(str(p))
            if img.isNull():
                return None
            w, h = img.width(), img.height()
            if w <= 0 or h <= 0:
                return None
            if w >= h:
                new_w = min(size, w)
                new_h = int(h * (new_w / w))
            else:
                new_h = min(size, h)
                new_w = int(w * (new_h / h))
            img2 = img.scaled(new_w, new_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            outp.parent.mkdir(parents=True, exist_ok=True)
            img2.save(str(outp), "JPG", quality=85)
            return outp
        except Exception:
            return None


    # ---- 縮圖/快取（無殘影、平滑） ---- #
    
    def _get_thumb(self, cover_path: Optional[Path], grid: bool, double: bool=False, overlay_pin: bool=False) -> Optional[QPixmap]:
        if not cover_path or not Path(cover_path).exists():
            return None
        s = float(self.config.get("ui_scale", 1.0))
        if grid:
            w,h = int(160*s), int(140*s)
        else:
            w,h = int(148*s), int(112*s)
        if double:
            w*=2; h*=2

        # 非 double（左側清單縮圖）優先使用縮圖；右欄放大圖使用原圖
        src_path = Path(cover_path)
        if not double:
            thumbp = self._ensure_thumb_for(src_path)
            if thumbp and Path(thumbp).exists():
                src_path = Path(thumbp)

        key = (str(src_path), w, h, bool(overlay_pin))
        if key in self._thumb_cache:
            return self._thumb_cache[key]
        pm = QPixmap(str(src_path))
        if pm.isNull(): 
            return None
        pm = pm.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        if overlay_pin:
            pin_path = self._resolve_asset_path("assets/pin.png")
            pin_pm = QPixmap(str(pin_path)) if pin_path.exists() else QPixmap()
            if not pin_pm.isNull():
                pin_size = max(12, int(min(pm.width(), pm.height()) * 0.26))
                pin_pm = pin_pm.scaled(pin_size, pin_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                composed = QPixmap(pm.size())
                composed.fill(Qt.transparent)
                painter = QPainter(composed)
                painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
                painter.drawPixmap(0, 0, pm)
                margin = max(2, int(pin_size * 0.08))
                x = pm.width() - pin_pm.width() - margin
                y = pm.height() - pin_pm.height() - margin
                painter.drawPixmap(x, y, pin_pm)
                painter.end()
                pm = composed
        self._thumb_cache[key] = pm
        return pm

    # ---- 右鍵動作 ---- #
    def pick_rom_dir(self):
        init = self.config.get("last_dirs", {}).get("rom") or self.ed_rom.text() or os.getcwd()
        d = QFileDialog.getExistingDirectory(self, tr(self, "pick_rom_title"), init)
        if not d: return
        self.config.setdefault("last_dirs", {})["rom"] = d
        self.ed_rom.setText(d); self.config["rom_dir"] = d; save_json(self.config_path, self.config)
        self.refresh_rom_list()

    def pick_melonds(self):
        init = self.config.get("last_dirs", {}).get("melonds") or (str(Path(self.ed_mel.text()).parent) if self.config.get("melonds_path") else os.getcwd())
        fp, _ = QFileDialog.getOpenFileName(self, tr(self, "pick_melonds_title"), init,
                                            "Executable (*.exe *.AppImage *.bin *.sh *.app);;All (*)")
        if not fp: return
        self.config.setdefault("last_dirs", {})["melonds"] = str(Path(fp).parent)
        self.ed_mel.setText(fp); self.config["melonds_path"] = fp; save_json(self.config_path, self.config)

    def pick_cover_for_selected(self):
        g = self._current_item()
        if not g:
            QMessageBox.information(self, APP_TITLE, tr(self, "tip_select")); return
        self._pick_cover_for(g.path)

    def _pick_cover_for(self, rom_path: Path):
        init = self.config.get("last_dirs", {}).get("cover") or str(self.covers_path)
        fp, _ = QFileDialog.getOpenFileName(self, tr(self, "choose_cover"), init,
                                            "Images (*.png *.jpg *.jpeg);;All (*)")
        if not fp: return
        self.config.setdefault("last_dirs", {})["cover"] = str(Path(fp).parent)
        src = Path(fp); dst = self.covers_path / (rom_path.stem + src.suffix.lower())
        try:
            shutil.copyfile(src, dst)
            # 立刻產生對應縮圖
            try:
                self._ensure_thumb_for(dst)
            except Exception:
                pass
            gid = game_id_for(rom_path)
            self.covers_map[gid] = str(dst)
            save_json(self.map_path, self.covers_map); save_json(self.config_path, self.config)
            self.refresh_rom_list()
        except Exception as e:
            QMessageBox.critical(self, "封面設定失敗", str(e))

    def rename_selected(self):
        g = self._current_item()
        if not g:
            QMessageBox.information(self, APP_TITLE, tr(self, "tip_select")); return
        self._rename_title(g.path)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F2:
            g = self._current_item()
            if g:
                self._rename_title(g.path)
        else:
            super().keyPressEvent(event)
    
    def _rename_title(self, rom_path: Path):
        s = float(self.config.get("ui_scale", 1.0))

        old = self._display_name_for(rom_path)

        # 建立可調大小的對話框
        dlg = QInputDialog(self)
        dlg.setModal(True)
        dlg.setInputMode(QInputDialog.TextInput)
        dlg.setWindowTitle(tr(self, "rename_prompt_title"))
        dlg.setLabelText(tr(self, "rename_prompt"))
        dlg.setTextValue(old)
        dlg.setTextEchoMode(QLineEdit.Normal)

        # 視窗大小（可改成固定像素 200x220）
        dlg.resize(int(200 * s), int(220 * s))

        # 送出
        if dlg.exec():
            new = dlg.textValue().strip()
            if not new:
                return
            gid = game_id_for(rom_path)
            self.titles_map[gid] = new
            save_json(self.titles_path, self.titles_map)
            self.refresh_rom_list()

    def pin_toggle_selected(self):
        g = self._current_item()
        if not g:
            QMessageBox.information(self, APP_TITLE, tr(self, "tip_select")); return
        keep_path = str(g.path).replace("\\", "/")
        files = set(self.config.get("pinned_files", []))
        k = g.path.name
        if k in files:
            files.remove(k)
        else:
            files.add(k)
        self.config["pinned_files"] = sorted(files)
        save_json(self.config_path, self.config)
        self.refresh_rom_list()
        self._select_path(keep_path)

    def launch_selected(self):
        g = self._current_item()
        if not g:
            QMessageBox.information(self, APP_TITLE, tr(self, "tip_select")); return
        self._launch(g.path)

    def _launch(self, rom_path: Path):
        melonds = self.ed_mel.text().strip() or self.config.get("melonds_path","").strip()
        if not melonds:
            QMessageBox.warning(self, tr(self,"warn_notset"), tr(self,"warn_set_melonds")); return
        if not Path(melonds).exists():
            QMessageBox.warning(self, tr(self,"not_found"), f"{tr(self,'not_found')}: {melonds}"); return
        try:
            if platform.system()=="Darwin" and melonds.endswith(".app"):
                subprocess.Popen(["open","-a",melonds,str(rom_path)])
            else:
                subprocess.Popen([melonds, str(rom_path)])
        except Exception as e:
            QMessageBox.critical(self, tr(self,"launch_failed"), str(e))

    def _reveal(self, rom_path: Path):
        try:
            if platform.system()=="Windows":
                subprocess.Popen(["explorer","/select,",str(rom_path)])
            elif platform.system()=="Darwin":
                subprocess.Popen(["open","-R",str(rom_path)])
            else:
                subprocess.Popen(["xdg-open", str(rom_path.parent)])
        except Exception as e:
            QMessageBox.critical(self, tr(self,"open_folder_failed"), str(e))

# ---- 以顯示 Title 為主的搜尋/排序 Proxy ---- #
class TitleSearchSortProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDynamicSortFilter(True)
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setSortCaseSensitivity(Qt.CaseInsensitive)

    def setFilterString(self, s: str):
        self.setFilterRegularExpression(QRegularExpression(s))

    def filterAcceptsRow(self, src_row, src_parent):
        idx = self.sourceModel().index(src_row, 0, src_parent)
        title = self.sourceModel().data(idx, Roles.Title) or ""
        # 同時容許以檔名輔助
        path = self.sourceModel().data(idx, Roles.Path) or ""
        re = self.filterRegularExpression()
        if not re.pattern():
            return True
        return re.match(str(title)).hasMatch() or re.match(str(path)).hasMatch()

    def lessThan(self, left, right):
        lpin = bool(self.sourceModel().data(left, Roles.Pinned))
        rpin = bool(self.sourceModel().data(right, Roles.Pinned))
        if lpin != rpin:
            return lpin  # pinned 優先
        lt = str(self.sourceModel().data(left, Roles.Title) or "")
        rt = str(self.sourceModel().data(right, Roles.Title) or "")
        return lt.lower() < rt.lower()

# ---- Delegate：統一繪製 Grid/List 卡片 ---- #

class CardDelegate(QStyledItemDelegate):
    def __init__(self, app: LauncherApp):
        super().__init__(app)
        self.app = app

    def paint(self, painter: QPainter, option, index):
        painter.save()
        r = option.rect.adjusted(4, 4, -4, -4)
        gtitle = index.data(Roles.Title) or ""
        disp_title_grid = self.app._fmt_title_grid(gtitle)
        disp_title_list = self.app._fmt_title_list(gtitle)
        pinned = bool(index.data(Roles.Pinned))
        cover = index.data(Roles.Cover) or ""
        path = Path(index.data(Roles.Path))

        is_grid = self.app._view_mode == "grid"
        pm = self.app._get_thumb(Path(cover) if cover else None, grid=is_grid, double=False, overlay_pin=pinned)

        # 背景與選中高亮
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(r, option.palette.base())
        painter.setPen(option.palette.mid().color())
        painter.drawRoundedRect(r, 8, 8)

        # 縮圖
        s = float(self.app.config.get("ui_scale", 1.0))
        if is_grid:
            thumb_rect = QRect(r.left()+10, r.top()+10, r.width()-20, int(140*s))
        else:
            th = int(112*s)
            tw = int(148*s)
            thumb_rect = QRect(r.left()+10, r.top() + (r.height()-th)//2, tw, th)

        if pm:
            x = thumb_rect.center().x() - pm.width()//2
            y = thumb_rect.center().y() - pm.height()//2
            painter.drawPixmap(x, y, pm)
        else:
            painter.setPen(option.palette.mid().color())
            painter.drawRect(thumb_rect)
            painter.drawText(thumb_rect, Qt.AlignCenter, "No Cover")

        # Title/path
        f = painter.font()
        f.setBold(True)
        f.setPointSize(int(f.pointSize() * s * 1.2))
        painter.setFont(f)
        painter.setPen(option.palette.text().color())

        if is_grid:
            title_rect = QRect(r.left()+10, thumb_rect.bottom()+8, r.width()-20, int(40*s))
            painter.drawText(title_rect, Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, disp_title_grid)
        else:

            # ---- List 模式：將「標題＋路徑」垂直置中 ----
            text_x = thumb_rect.right() + 12
            text_w = r.width() - thumb_rect.width() - 22

            # 1) 標題字型：沿用前面設定（粗體、倍率）
            f_title = QFont(painter.font())
            f_title.setBold(True)
            f_title.setPointSize(f_title.pointSize() + 10)
            painter.setFont(f_title)
            fm_title = QFontMetrics(f_title)
            title_h = fm_title.height()

            # 2) 路徑字型：非粗體（若要更小，可自行 setPointSize(f_title.pointSize()-6)）
            f_path = QFont(painter.font())
            f_path.setBold(False)
            f_path.setPointSize(f_title.pointSize() - 6)  # 需要更小字時可開啟
            fm_path = QFontMetrics(f_path)
            path_h = fm_path.height()

            gap = int(6 * s)  # 行距
            total_h = title_h + gap + path_h
            y0 = r.y() + (r.height() - total_h) // 2

            title_rect = QRect(text_x, y0,               text_w, title_h)
            path_rect  = QRect(text_x, y0 + title_h+gap, text_w, path_h)

            # 畫標題
            painter.setFont(f_title)
            painter.setPen(option.palette.text().color())
            painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, disp_title_list)   # List

            # 畫路徑
            painter.setFont(f_path)
            painter.setPen(QColor(100, 100, 100))
            painter.drawText(path_rect, Qt.AlignLeft | Qt.AlignVCenter, str(path).replace("\\", "/"))

        # pin 標記由覆蓋的 pin.png 顯示於縮圖右下角（見 _get_thumb）

        painter.restore()

    def sizeHint(self, option, index):
        s = float(self.app.config.get("ui_scale", 1.0))
        if self.app._view_mode == "grid":
            return QSize(int(180*s), int(200*s))
        else:
            return QSize(int(420*s), int(140*s))
        
# ---- 進入點 ---- #
    def _grid_base_wh(self) -> Tuple[int, int]:
        """取得目前檢視模式對應的縮圖基準寬高（尚未 *2）。"""
        s = float(self.config.get("ui_scale", 1.0))
        if self._view_mode == "grid":
            return int(160*s), int(140*s)
        else:
            return int(148*s), int(112*s)

def main():
    # 正確設定 Windows 的 High DPI 策略（Enum 不能被呼叫，直接取成員）
    if platform.system() == "Windows" and hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
        try:
            QApplication.setHighDpiScaleFactorRoundingPolicy(
                Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
            )
        except Exception:
            pass
    app = QApplication(sys.argv)
    win = LauncherApp()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()