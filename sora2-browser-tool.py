#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Sora 2 Browser Tool

# --- Dependency bootstrap ---
def _check_dependencies():
    import importlib, subprocess, sys, traceback
    missing = []
    for mod, pkg in [("PyQt6", "PyQt6"), ("PyQt6.QtWebEngineWidgets", "PyQt6-WebEngine")]:
        try:
            importlib.import_module(mod)
        except Exception:
            missing.append(pkg)
    if missing:
        try:
            print("[Deps] Installing:", ", ".join(missing))
            subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
            print("[Deps] Install complete.")
        except Exception as e:
            print("[Deps] Auto-install failed. Run:", sys.executable, "-m pip install", " ".join(missing))
            print("[Deps] Error:", e)
            traceback.print_exc()

try:
    _check_dependencies()
except Exception:
    pass

import os, sys, re, json, tempfile, random, mimetypes, pathlib, webbrowser
import urllib.request
from urllib.parse import urlparse

from PyQt6.QtCore import Qt, QUrl, QSize, QProcess
from PyQt6.QtWidgets import (QTextEdit,
    QApplication, QMainWindow, QSplitter, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QPushButton, QLineEdit, QComboBox, QLabel,
    QMessageBox, QInputDialog, QTabWidget, QCheckBox, QCompleter, QFileDialog
)
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile
from PyQt6.QtWebEngineWidgets import QWebEngineView
# --- Cloudflare/Turnstile compatibility flags (GPU + third-party cookies) ---
# Must be set before QtWebEngine starts
os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "--enable-gpu --ignore-gpu-blocklist --enable-webgl --enable-accelerated-video-decode "
    "--disable-features=BlockThirdPartyCookies,ThirdPartyStoragePartitioning"
)


CONFIG_PATH = os.path.join(os.path.dirname(__file__), "sora2_config.json")
USER_SITES_PATH = os.path.join(os.path.dirname(__file__), "sora2_user_sites.json")
USER_PROMPTS_PATH = os.path.join(os.path.dirname(__file__), "sora2_user_prompts.json")
USER_CHARACTERS_PATH = os.path.join(os.path.dirname(__file__), "sora2_user_characters.json")


DEFAULT_CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)

PRESET_UAS = {
    "Chrome (Windows)": DEFAULT_CHROME_UA,
    "Chrome (macOS)": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "Edge (Windows)": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0",
    "Firefox (Windows)": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Chrome (Android)": "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36",
    "Safari (iPhone)": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
}

# Prompts come exclusively from sora2_config.json
PROMPT_DEFAULTS = []
def load_config():
    if not os.path.exists(CONFIG_PATH):
        QMessageBox.warning(None, "Config", f"Config not found at {CONFIG_PATH}. Using defaults.")
        return {
            "version": "0.0.0",
            "window": {"width": 1920,"height": 1080,"orientation":"horizontal","user_agent":"Chrome (Windows)","mail_url":"https://www.guerrillamail.com/inbox","window_title":"Sora 2 Browser Tool"},
            "sites": [],
            "prompts": []
        }
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    # allow config to override prompt defaults; if missing, keep built-in
    if "prompts" not in cfg:
        cfg["prompts"] = PROMPT_DEFAULTS
    return cfg

def save_config(cfg):
    try:
        # Preserve existing; only update window/ui/version. Never touch characters/sites/prompts here.
        existing = {}
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    existing = json.load(f) or {}
            except Exception:
                existing = {}

        for k in ("version", "window", "ui"):
            if k in cfg:
                existing[k] = cfg[k]

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
    except Exception as e:
        QMessageBox.critical(None, "Config Save Error", str(e))

def load_or_init_user_sites(default_sites):
    """Load user sites from USER_SITES_PATH; if missing, seed with defaults and write file."""
    try:
        if os.path.exists(USER_SITES_PATH):
            with open(USER_SITES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            sites = data.get("sites", data if isinstance(data, list) else [])
        else:
            sites = list(default_sites)
            with open(USER_SITES_PATH, "w", encoding="utf-8") as f:
                json.dump({"sites": sites}, f, indent=2, ensure_ascii=False)
        return sites
    except Exception:
        return list(default_sites)

def save_user_sites(sites):
    try:
        with open(USER_SITES_PATH, "w", encoding="utf-8") as f:
            json.dump({"sites": sites}, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def load_or_init_user_prompts(default_prompts):
    """Load user prompts; if file missing or empty, seed with defaults and persist. Return the list."""
    try:
        if os.path.exists(USER_PROMPTS_PATH):
            with open(USER_PROMPTS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                prompts = data.get("prompts", [])
            elif isinstance(data, list):
                prompts = data
            else:
                prompts = []
        else:
            prompts = list(default_prompts)
        if not isinstance(prompts, list) or len(prompts) == 0:
            prompts = list(default_prompts)
        with open(USER_PROMPTS_PATH, "w", encoding="utf-8") as f:
            json.dump({"prompts": prompts}, f, indent=2, ensure_ascii=False)
        return prompts
    except Exception:
        return list(default_prompts)

def save_user_prompts(prompts):
    try:
        with open(USER_PROMPTS_PATH, "w", encoding="utf-8") as f:
            json.dump({"prompts": prompts}, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


# --- Prompt helpers ---
def _p_to_obj(p, idx=0):
    if isinstance(p, dict):
        text = str(p.get("text") or p.get("prompt") or "").strip()
        title = p.get("title") or (text.splitlines()[0][:60] if text else "Untitled")
        cat = p.get("category") or "Base"
        tags = p.get("tags") or []
        pid = p.get("id") or f"p{idx:04d}"
        return {"id": pid, "title": title, "category": cat, "tags": tags, "text": text}
    else:
        text = str(p or "").strip()
        title = (text.splitlines()[0][:60] if text else "Untitled")
        return {"id": f"p{idx:04d}", "title": title, "category": "Base", "tags": [], "text": text}

def _normalize_prompts_list(prompts):
    return [_p_to_obj(p, i) for i, p in enumerate(prompts or [])]

def _extract_categories(objs):
    seen = set(); cats = []
    for o in objs:
        c = o.get("category") or "Base"
        if c not in seen:
            seen.add(c); cats.append(c)
    return cats



def sanitize_character_name(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9 '\-]", "", str(name))
    s = re.sub(r"\s+", " ", s).strip()
    return s


def save_user_characters(characters):
    try:
        with open(USER_CHARACTERS_PATH, "w", encoding="utf-8") as f:
            json.dump({"characters": characters}, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False
class Browser(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        s = self.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)

def load_or_init_user_characters(default_characters):
    """Load user characters from USER_CHARACTERS_PATH; if missing/empty, seed with defaults and persist."""
    try:
        if os.path.exists(USER_CHARACTERS_PATH):
            with open(USER_CHARACTERS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                characters = data.get("characters", [])
            elif isinstance(data, list):
                characters = data
            else:
                characters = []
        else:
            characters = list(default_characters)
            with open(USER_CHARACTERS_PATH, "w", encoding="utf-8") as f:
                json.dump({"characters": characters}, f, indent=2, ensure_ascii=False)
        if not isinstance(characters, list):
            characters = []
        characters = [(" ".join(str(x).split())).strip() for x in characters if isinstance(x, str) and x.strip()]
        characters = sorted(set(characters), key=lambda s: s.lower())
        return characters
    except Exception as e:
        try:
            QMessageBox.critical(None, "Characters", str(e))
        except Exception:
            pass
        return list(default_characters)

class Main(QMainWindow):

    def _get_prompt_pid(self, obj, text):
        """Return a stable id for the selected prompt, using explicit id
        or hashing "title|text" when no explicit id is present."""
        import hashlib
        if isinstance(obj, dict):
            pid = obj.get("id")
            title = obj.get("title", "")
            base_text = obj.get("text", text or "")
        else:
            pid = None
            title = ""
            base_text = text or ""
        if not pid:
            pid = hashlib.sha1((title + "|" + (base_text or "")).encode("utf-8")).hexdigest()
        return pid



    def __init__(self):
        super().__init__()

        try:
            self._apply_pending_tmp_updates()
        except Exception:
            pass
        self.cfg = load_config()
        self.setWindowTitle(self.cfg.get("window",{}).get("window_title", "Sora 2 Browser Tool"))

        # Shared profile
        self.profile = QWebEngineProfile.defaultProfile()
        data_dir = os.path.join(tempfile.gettempdir(), "sora2_split_profile")
        os.makedirs(data_dir, exist_ok=True)
        self.profile.setPersistentStoragePath(data_dir)
        self.profile.setCachePath(os.path.join(data_dir, "cache"))
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
        self.profile.setHttpAcceptLanguage("en-US,en;q=0.9")
        # Allow third-party cookies if supported (helps CF Turnstile)
        try:
            self.profile.setThirdPartyCookiePolicy(QWebEngineProfile.ThirdPartyCookiePolicy.AllowAll)
        except Exception:
            pass


        ua_label = self.cfg["window"].get("user_agent","Default (Engine)")
        if ua_label.startswith('Default'):
            self.current_ua = 'Default (Engine)'
        else:
            self.current_ua = PRESET_UAS.get(ua_label, ua_label)
            try:
                self.profile.setHttpUserAgent(self.current_ua)
            except Exception:
                pass
        self.profile.downloadRequested.connect(self.on_download)

        if self.cfg['window'].get('fullscreen', False):
            self.showFullScreen()
        else:
            self.resize(self.cfg['window'].get('width',1440), self.cfg['window'].get('height',900))

        # Root: ACTIONS / CONTENT
        self.rootSplit = QSplitter(Qt.Orientation.Vertical)
        self.setCentralWidget(self.rootSplit)

        # === MENUBAR ===
        menubar = self.menuBar()

        m_file = menubar.addMenu("File")
        act_open_ext = m_file.addAction("Open Externally")
        act_open_ext.triggered.connect(self.open_external)
        act_open_media = m_file.addAction("Open Media…")
        act_open_media.triggered.connect(self.open_media_externally)

        m_view = menubar.addMenu("View")
        act_switch_tb = m_view.addAction("Switch Top/Bottom")
        act_switch_tb.triggered.connect(self.switch_orientation)
        act_swap_lr = m_view.addAction("Swap Left/Right")
        act_swap_lr.triggered.connect(self.swap_left_right)

        m_tools = menubar.addMenu("Tools")
        m_tools_ua = m_tools.addMenu("User Agent")
        # mirror the preset list in a submenu
        m_tools_ua.addAction('Default (Engine)').triggered.connect(lambda _, lab='Default (Engine)': self.set_user_agent(None, preset_label=lab))
        for label in PRESET_UAS.keys():
            a = m_tools_ua.addAction(label)
            a.triggered.connect(lambda _, lab=label: self.set_user_agent(PRESET_UAS[lab], preset_label=lab))
        m_tools_ua.addSeparator()
        a_apply = m_tools_ua.addAction("Apply UA (from fields)"); a_apply.triggered.connect(self.apply_ua_clicked)
        a_random = m_tools_ua.addAction("Random UA"); a_random.triggered.connect(self.random_ua_clicked)
        a_reset = m_tools_ua.addAction("Reset UA"); a_reset.triggered.connect(self.reset_ua_clicked)
        a_mobile = m_tools_ua.addAction("Try Mobile WebM"); a_mobile.triggered.connect(self.use_mobile_ua)

        m_tools_cap = m_tools.addMenu("Captcha")
        a_clear_recaptcha = m_tools_cap.addAction("Clear reCAPTCHA Cookies"); a_clear_recaptcha.triggered.connect(self.clear_recaptcha_cookies)
        a_fix_cf = m_tools_cap.addAction("Fix Captcha (Cloudflare)"); a_fix_cf.triggered.connect(self.fix_captcha_cloudflare)
        self.act_aggr_spoof = m_tools_cap.addAction("Aggressive Spoof"); self.act_aggr_spoof.setCheckable(True)
        self.act_aggr_spoof.toggled.connect(self.toggle_aggressive_spoof)
        
        m_sites = menubar.addMenu("Sites")
        a_sites_restore = m_sites.addAction("Restore Default 100…"); a_sites_restore.triggered.connect(self.restore_default_sites)
        a_sites_clear = m_sites.addAction("Clear User Sites…"); a_sites_clear.triggered.connect(self.clear_user_sites)
        m_sites.addSeparator()
        a_sites_add = m_sites.addAction("Add Current Page"); a_sites_add.triggered.connect(self.add_site_from_current)
        a_sites_remove = m_sites.addAction("Remove Selected"); a_sites_remove.triggered.connect(self.remove_selected_site)

        m_prompts = menubar.addMenu("Prompts")
        a_p_copy = m_prompts.addAction("Copy Selected"); a_p_copy.triggered.connect(self.copy_selected_prompt)
        a_p_add = m_prompts.addAction("Add…"); a_p_add.triggered.connect(self.add_prompt_dialog)
        a_p_remove = m_prompts.addAction("Remove"); a_p_remove.triggered.connect(self.remove_selected_prompt)
        m_prompts.addSeparator()
        a_p_restore = m_prompts.addAction("Restore Default Prompts…"); a_p_restore.triggered.connect(self.restore_default_prompts)
        a_p_clear = m_prompts.addAction("Clear User Prompts…"); a_p_clear.triggered.connect(self.clear_user_prompts)
        a_p_export = m_prompts.addAction("Export…"); a_p_export.triggered.connect(self.export_prompts_dialog)
        a_p_import = m_prompts.addAction("Import…"); a_p_import.triggered.connect(self.import_prompts_dialog)
        
        m_characters = menubar.addMenu("Characters")
        a_rp = m_characters.addAction("Restore Default Characters…"); a_rp.triggered.connect(self.restore_default_characters)
        a_cp = m_characters.addAction("Clear User Characters…"); a_cp.triggered.connect(self.clear_user_characters)
        m_characters.addSeparator()
        a_ep = m_characters.addAction("Export…"); a_ep.triggered.connect(self.export_characters_dialog)
        a_ip = m_characters.addAction("Import…"); a_ip.triggered.connect(self.import_characters_dialog)
        a_clear_data = menubar.addAction("Clear Site Data"); a_clear_data.triggered.connect(self.clear_site_data)
        a_update = menubar.addAction("Check For Updates"); a_update.triggered.connect(self.check_for_updates)



        # === ACTIONS (split left actions | right prompts) ===
        actions = QWidget(); act_v = QVBoxLayout(actions)
        act_v.setContentsMargins(6,6,6,6); act_v.setSpacing(8)

        self.actionsSplit = QSplitter(Qt.Orientation.Horizontal)
        act_v.addWidget(self.actionsSplit, 1)

        # ----- LEFT ACTIONS (existing UI) -----
        leftActions = QWidget(); la_v = QVBoxLayout(leftActions)
        la_v.setContentsMargins(0,0,0,0); la_v.setSpacing(8)

        bar = QWidget(); row = QHBoxLayout(bar); row.setContentsMargins(0,0,0,0); row.setSpacing(8)
        self.addr = QLineEdit(); self.addr.setPlaceholderText("Paste any Sora 2 URL and press Enter")
        self.addr.returnPressed.connect(self.load_left_addr)
        row.addWidget(QLabel("URL:")); row.addWidget(self.addr,1)

        row.addWidget(QLabel("UA:"))
        self.uaPreset = QComboBox(); self.uaPreset.addItem('Default (Engine)'); self.uaPreset.addItems(list(PRESET_UAS.keys()))
        preset_label = 'Default (Engine)' if self.current_ua == 'Default (Engine)' else next((k for k,v in PRESET_UAS.items() if v==self.current_ua), "Chrome (Windows)")
        self.uaPreset.setCurrentText(preset_label)
        self.uaCustom = QLineEdit(); self.uaCustom.setPlaceholderText("Custom UA…")

        self.btnApplyUA = QPushButton("Apply UA"); self.btnApplyUA.clicked.connect(self.apply_ua_clicked)
        self.btnRandomUA = QPushButton("Random UA"); self.btnRandomUA.clicked.connect(self.random_ua_clicked)
        self.btnResetUA = QPushButton("Reset"); self.btnResetUA.clicked.connect(self.reset_ua_clicked)
        self.btnMobileUA = QPushButton("Try Mobile WebM"); self.btnMobileUA.clicked.connect(self.use_mobile_ua)
        self.btnClear = QPushButton("Clear reCAPTCHA Cookies"); self.btnClear.clicked.connect(self.clear_recaptcha_cookies)
        self.btnToggle = QPushButton("Top/Bottom"); self.btnToggle.clicked.connect(self.switch_orientation)
        self.btnExternal = QPushButton("Open Externally"); self.btnExternal.clicked.connect(self.open_external)
        self.btnOpenMedia = QPushButton("Open Media"); self.btnOpenMedia.clicked.connect(self.open_media_externally)
        row.addWidget(self.uaPreset); row.addWidget(self.uaCustom,1)
        for b in (self.btnApplyUA,self.btnRandomUA,self.btnResetUA,self.btnToggle,self.btnExternal,self.btnOpenMedia):
            row.addWidget(b)
        la_v.addWidget(bar)

        # Quick open
        quick = QWidget(); qrow = QHBoxLayout(quick); qrow.setContentsMargins(0,0,0,0); qrow.setSpacing(8)
        self.quick = QLineEdit(); self.quick.setPlaceholderText("https://… (Sora 2 link)")
        btn_open = QPushButton("Open"); btn_open.clicked.connect(self.load_quick)
        qrow.addWidget(self.quick,1); qrow.addWidget(btn_open,0)
        la_v.addWidget(quick)

        # Sites list (from user-sites JSON)
        self.user_sites = load_or_init_user_sites(self.cfg.get("sites", []))
        self.listw = QListWidget()
        self.refresh_sites_list()
        self.listw.itemClicked.connect(self.load_from_list)
        la_v.addWidget(self.listw,1)

        info = QLabel("Source: User list (editable) • Defaults preserved")
        row_sites = QWidget(); row_sites_h = QHBoxLayout(row_sites); row_sites_h.setContentsMargins(0,0,0,0); row_sites_h.setSpacing(8)
        btnRestore = QPushButton("Restore Default 100"); btnRestore.clicked.connect(self.restore_default_sites)
        btnClearSites = QPushButton("Clear User Sites"); btnClearSites.clicked.connect(self.clear_user_sites)
        btnAddSite = QPushButton("Add Current Page"); btnAddSite.clicked.connect(self.add_site_from_current)
        btnRemoveSite = QPushButton("Remove Selected"); btnRemoveSite.clicked.connect(self.remove_selected_site)
        row_sites_h.addWidget(info,1)
        for b in (btnAddSite, btnRemoveSite):
            row_sites_h.addWidget(b,0)
        # keep Restore/Clear accessible via the Sites menu

        la_v.addWidget(row_sites)

        # ----- RIGHT PROMPTS PANEL -----
        rightPrompts = QWidget(); rp_v = QVBoxLayout(rightPrompts)
        rp_v.setContentsMargins(8,0,0,0); rp_v.setSpacing(6)

        rp_header = QWidget(); rp_row = QHBoxLayout(rp_header); rp_row.setContentsMargins(0,0,0,0); rp_row.setSpacing(8)
        rp_row.addWidget(QLabel("Prompts"), 0)
        self.btnPromptCopy = QPushButton("Copy"); self.btnPromptCopy.clicked.connect(self.copy_selected_prompt)
        self.btnPromptAdd = QPushButton("Add"); self.btnPromptAdd.clicked.connect(self.add_prompt_dialog)
        self.btnPromptRemove = QPushButton("Remove"); self.btnPromptRemove.clicked.connect(self.remove_selected_prompt)
        self.btnPromptRestore = QPushButton("Restore Default Prompts"); self.btnPromptRestore.clicked.connect(self.restore_default_prompts)
        self.btnPromptClear = QPushButton("Clear User Prompts"); self.btnPromptClear.clicked.connect(self.clear_user_prompts)
        self.btnPromptExport = QPushButton("Export"); self.btnPromptExport.clicked.connect(self.export_prompts_dialog)
        self.btnPromptImport = QPushButton("Import"); self.btnPromptImport.clicked.connect(self.import_prompts_dialog)
        for b in (self.btnPromptCopy,self.btnPromptAdd,self.btnPromptRemove,self.btnPromptRestore,self.btnPromptClear,self.btnPromptExport,self.btnPromptImport):
            rp_row.addWidget(b, 0)
        rp_v.addWidget(rp_header, 0)

        self.user_prompts = load_or_init_user_prompts(self.cfg.get("prompts", []))
        self._manual_placeholder_cache = {}  # remembers manual "" values per prompt


        self._prompt_objs = _normalize_prompts_list(self.user_prompts)
        self.user_characters = load_or_init_user_characters(self.cfg.get("characters", []))

        # --- Category + Character selectors ---
        characterRow = QHBoxLayout()
        characterRow.addWidget(QLabel("Category:"))
        self.categoryBox = QComboBox(); self.categoryBox.addItem("Show All")
        self.categoryBox.currentIndexChanged.connect(self.refresh_prompts_list)
        characterRow.addWidget(self.categoryBox)
        characterRow.addSpacing(12)
        lblP1 = QLabel("Character 1:"); lblP1.setStyleSheet("font-size: 11px;")
        characterRow.addWidget(lblP1)
        self.character1Box = QComboBox()
        self.character1Box.addItem("— None —")
        self.character1Box.addItems(self.user_characters)
        characterRow.addWidget(self.character1Box)
        characterRow.addSpacing(8)
        lblP2 = QLabel("Character 2:"); lblP2.setStyleSheet("font-size: 11px;")
        characterRow.addWidget(lblP2)
        self.character2Box = QComboBox()
        self.character2Box.addItem("— None —")
        self.character2Box.addItems(self.user_characters)
        characterRow.addWidget(self.character2Box)
        characterRow.addSpacing(8); self.keepNamesCheck = QCheckBox("Keep names"); self.keepNamesCheck.setChecked(True); characterRow.addWidget(self.keepNamesCheck)
        rp_v.addLayout(characterRow)
        try:
            self.character1Box.setEditable(True); self.character2Box.setEditable(True)
            _c1 = QCompleter(self.user_characters, self.character1Box); _c1.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            _c2 = QCompleter(self.user_characters, self.character2Box); _c2.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.character1Box.setCompleter(_c1); self.character2Box.setCompleter(_c2)
        except Exception:
            pass
    

        # Prompts list (single; filtered by Category)
        self.promptList = QListWidget()
        self.promptList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.promptList.customContextMenuRequested.connect(self._edit_prompt_on_right_click)

        self.promptList.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.promptList.setWordWrap(True)
        self.promptList.itemClicked.connect(self.copy_selected_prompt)
        # Preview on the right
        self.previewEdit = QTextEdit()
        self.previewEdit.setReadOnly(True)
        self.previewEdit.setPlaceholderText("Prompt preview…")
        self.previewEdit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        # Splitter to hold list + preview
        self.promptsSplitter = QSplitter(Qt.Orientation.Horizontal)
        self.promptsSplitter.addWidget(self.promptList)
        self.promptsSplitter.addWidget(self.previewEdit)
        _sizes = (self.cfg.get('ui', {}) or {}).get('prompts_splitter_sizes', [680, 520])
        try:
            self.promptsSplitter.setSizes([int(_sizes[0]), int(_sizes[1])])
        except Exception:
            pass
        rp_v.addWidget(self.promptsSplitter, 1)
        # Live preview updates
        try:
            self.promptList.currentItemChanged.connect(self.update_prompt_preview)
            self.character1Box.currentIndexChanged.connect(lambda _: self.update_prompt_preview())
            self.character2Box.currentIndexChanged.connect(lambda _: self.update_prompt_preview())
        except Exception:
            pass
        self.refresh_prompts_list()
        try:
            self.update_prompt_preview()
        except Exception:
            pass

        # add left/right panes to the actions splitter
        self.actionsSplit.addWidget(leftActions)
        self.actionsSplit.addWidget(rightPrompts)
        # align actions split with content split via pane_ratio
        self.actionsSplit.setSizes([int(1000*self.cfg['window'].get('pane_ratio',0.5)), int(1000*(1.0-self.cfg['window'].get('pane_ratio',0.5)))])

        #self.actionsSplit.setSizes([1100, 700])  # initial ratio; user can drag

        # === CONTENT splitter LEFT/RIGHT ===
        self.contentSplit = QSplitter(Qt.Orientation.Horizontal)
        # Left tabs
        self.leftTabs = QTabWidget(); self.leftTabs.setTabsClosable(True); self.leftTabs.setMovable(True)
        self.leftTabs.tabBar().setUsesScrollButtons(True)
        self.leftTabs.tabCloseRequested.connect(self.close_left_tab)
        self.leftTabs.currentChanged.connect(self.on_left_tab_changed)
        # initial tab
        _b0 = Browser()
        self._connect_left_browser(_b0)
        self.leftTabs.addTab(_b0, "New Tab")
        self.right = Browser()
        self.right.settings().setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
        self.right.setUrl(QUrl(self.cfg["window"].get("mail_url","https://www.guerrillamail.com/inbox")))

        self.contentSplit.addWidget(self.leftTabs); self.contentSplit.addWidget(self.right)
        self.contentSplit.setStretchFactor(0,1); self.contentSplit.setStretchFactor(1,1)
        self.contentSplit.setSizes([int(1000*self.cfg['window'].get('pane_ratio',0.5)),int(1000*(1.0-self.cfg['window'].get('pane_ratio',0.5)))])

        # add to root
        self.rootSplit.addWidget(actions); self.rootSplit.addWidget(self.contentSplit)
        # Keep ACTIONS and CONTENT splitters aligned
        self._syncing_splitters = False
        self.actionsSplit.splitterMoved.connect(self._on_actions_split_moved)
        self.contentSplit.splitterMoved.connect(self._on_content_split_moved)

        self.rootSplit.setStretchFactor(0,0); self.rootSplit.setStretchFactor(1,1)

        # Apply orientation
        if self.cfg["window"].get("orientation","horizontal") == "vertical":
            self.contentSplit.setOrientation(Qt.Orientation.Vertical)
        self.update_toggle_label()

        self.statusBar().showMessage("Ready")

    # --- UA logic ---
    def set_user_agent(self, ua: str, preset_label=None):
        self.current_ua = ua
        self.profile.setHttpUserAgent(ua)
        if preset_label:
            self.uaPreset.setCurrentText(preset_label)
        # reload all left tabs
        try:
            for i in range(self.leftTabs.count()):
                b = self.leftTabs.widget(i)
                if b.url().isValid():
                    b.reload()
        except Exception:
            pass
        if self.right.url().isValid():
            self.right.reload()
    
    def swap_left_right(self):
        try:
            if self.contentSplit.count() >= 2:
                w0 = self.contentSplit.widget(0)
                w1 = self.contentSplit.widget(1)
                self.contentSplit.insertWidget(0, w1)
                self.contentSplit.insertWidget(1, w0)
        except Exception:
            pass

    def fix_captcha_cloudflare(self):
        # Minimal, non-destructive helper: reload all tabs and right pane; relies on current UA/cookies
        try:
            for i in range(self.leftTabs.count()):
                b = self.leftTabs.widget(i)
                if hasattr(b, "reload"):
                    b.reload()
            if hasattr(self.right, "reload"):
                self.right.reload()
            QMessageBox.information(self, "Fix Captcha", "Reloaded tabs. Consider toggling Aggressive Spoof and trying a different UA.")
        except Exception:
            QMessageBox.information(self, "Fix Captcha", "Attempted reload.")

    def toggle_aggressive_spoof(self, checked):
        # Store a flag; advanced spoofing would adjust deeper settings. Keep minimal to avoid breaking base.
        self.aggressive_spoof = bool(checked)
        QMessageBox.information(self, "Aggressive Spoof", "Enabled" if checked else "Disabled")

    def apply_ua_clicked(self):
        text = self.uaCustom.text().strip() or PRESET_UAS.get(self.uaPreset.currentText(), DEFAULT_CHROME_UA)
        self.set_user_agent(text)

    def random_ua_clicked(self):
        label, ua = random.choice(list(PRESET_UAS.items()))
        self.uaCustom.setText(ua); self.set_user_agent(ua, label)

    def reset_ua_clicked(self):
        self.uaCustom.clear()
        self.set_user_agent(DEFAULT_CHROME_UA, "Chrome (Windows)")

    def use_mobile_ua(self):
        self.set_user_agent(PRESET_UAS["Chrome (Android)"], "Chrome (Android)")

    # --- Cookies ---
    def clear_recaptcha_cookies(self):
        self.profile.cookieStore().deleteAllCookies()
        br = self.current_browser()
        if br and br.url().isValid():
            br.reload()
        self.statusBar().showMessage("Cleared cookies; reloaded active tab.", 4000)
        
    def on_download(self, item):
        downloads = pathlib.Path.home() / "Downloads"
        downloads.mkdir(parents=True, exist_ok=True)
        fname = item.suggestedFileName() or "download"
        root, ext = os.path.splitext(fname)
        mt = getattr(item, "mimeType", lambda:"")()
        path_ext = os.path.splitext(urlparse(item.url().toString()).path)[1]
        guess = path_ext or (mimetypes.guess_extension(mt) or "")
        if not ext and not guess and ("video/" in mt or "mp4" in mt): guess = ".mp4"
        if guess: fname = (root or "download") + guess
        try:
            item.setDownloadDirectory(str(downloads)); item.setDownloadFileName(fname)
        except Exception:
            try: item.setPath(str(downloads / fname))
            except Exception: pass
        item.accept()
        self.statusBar().showMessage(f"Downloading to {downloads/fname}", 4000)

    
    # --- Splitter sync ---
    def _apply_split_sizes(self, sizes):
        try:
            self._syncing_splitters = True
            self.actionsSplit.setSizes(sizes)
            self.contentSplit.setSizes(sizes)
        finally:
            self._syncing_splitters = False

    def _on_actions_split_moved(self, pos, index):
        if getattr(self, "_syncing_splitters", False):
            return
        self._apply_split_sizes(self.actionsSplit.sizes())

    def _on_content_split_moved(self, pos, index):
        if getattr(self, "_syncing_splitters", False):
            return
        self._apply_split_sizes(self.contentSplit.sizes())
        
    # --- Layout toggle ---
    def update_toggle_label(self):
        self.btnToggle.setText("Top/Bottom" if self.contentSplit.orientation()==Qt.Orientation.Horizontal else "Left/Right")

    def switch_orientation(self):
        ori = self.contentSplit.orientation()
        self.contentSplit.setOrientation(Qt.Orientation.Vertical if ori==Qt.Orientation.Horizontal else Qt.Orientation.Horizontal)
        self.contentSplit.setStretchFactor(0,1); self.contentSplit.setStretchFactor(1,1)
        self.contentSplit.setSizes([int(1000*self.cfg['window'].get('pane_ratio',0.5)),int(1000*(1.0-self.cfg['window'].get('pane_ratio',0.5)))])
        self.update_toggle_label()

    # --- Left tabs helpers ---
    def current_browser(self) -> QWebEngineView:
        try:
            return self.leftTabs.currentWidget()
        except Exception:
            return None

    def _connect_left_browser(self, br: QWebEngineView):
        br.titleChanged.connect(lambda t, b=br: self.on_tab_title_changed(b, t))
        br.urlChanged.connect(lambda u, b=br: self.on_tab_url_changed(b, u))

    def on_tab_title_changed(self, br: QWebEngineView, title: str):
        idx = self.leftTabs.indexOf(br)
        if idx != -1:
            ttl = (title or "").strip() or "Loading…"
            self.leftTabs.setTabText(idx, ttl[:30])
            self.leftTabs.setTabToolTip(idx, ttl)

    def on_tab_url_changed(self, br: QWebEngineView, url: QUrl):
        if br is self.current_browser():
            self.addr.setText(url.toString())

    def on_left_tab_changed(self, index: int):
        br = self.current_browser()
        if br and br.url().isValid():
            self.addr.setText(br.url().toString())
        else:
            self.addr.clear()

    def close_left_tab(self, index: int):
        if self.leftTabs.count() <= 1:
            # keep at least one tab
            w = self.leftTabs.widget(index)
            if w:
                w.setUrl(QUrl("about:blank"))
            self.leftTabs.setTabText(index, "New Tab")
            self.leftTabs.setTabToolTip(index, "New Tab")
            return
        w = self.leftTabs.widget(index)
        self.leftTabs.removeTab(index)
        if w:
            w.deleteLater()

    def open_url_in_new_tab(self, url: str):
        if not url:
            return
        br = Browser()
        self._connect_left_browser(br)
        idx = self.leftTabs.addTab(br, "…")
        self.leftTabs.setCurrentIndex(idx)
        br.setUrl(QUrl(url))
        self.addr.setText(url)

    # --- Navigation helpers ---
    def open_external(self):
        br = self.current_browser()
        url = br.url().toString() if (br and br.url().isValid()) else self.addr.text().strip()
        if url:
            webbrowser.open(url)
            
    def open_media_externally(self):
        js = r"(()=>{const v=document.querySelector('video');return v?(v.currentSrc||v.src||''):'';})()"
        def cb(u):
            br = self.current_browser()
            u = u or (br.url().toString() if (br and br.url().isValid()) else '')
            if u:
                webbrowser.open(u)
        br = self.current_browser()
        if br:
            br.page().runJavaScript(js, cb)
            
    def load_quick(self):
        u = self.quick.text().strip()
        if u:
            self.open_url_in_new_tab(u)
    def load_from_list(self, item: QListWidgetItem):
        site = item.data(Qt.ItemDataRole.UserRole); u = site.get("url","")
        if u:
            self.open_url_in_new_tab(u)
            
    def load_left_addr(self):
        u = self.addr.text().strip()
        br = self.current_browser()
        if u and br:
            br.setUrl(QUrl(u))
            
    def refresh_sites_list(self):
        self.listw.clear()
        for site in self.user_sites:
            txt = f'{site.get("id",0):02d}. {site.get("url","")}'
            it = QListWidgetItem(txt)
            it.setData(Qt.ItemDataRole.UserRole, site)
            it.setToolTip(site.get("url",""))
            it.setSizeHint(QSize(100,28))
            self.listw.addItem(it)

    def _base_of(self, url: str) -> str:
        try:
            host = urlparse(url).netloc.lower()
            if host.startswith("www."):
                host = host[4:]
            return host.split(":")[0]
        except Exception:
            return ""

    def _next_site_id(self) -> int:
        ids = [s.get("id", 0) for s in self.user_sites]
        return (max(ids) + 1) if ids else 1

    def add_site_from_current(self):
        url = ""
        br = self.current_browser()
        if br and br.url().isValid():
            url = br.url().toString()
        if not url:
            url = self.addr.text().strip()
        if not url:
            QMessageBox.warning(self, "Add Site", "No URL to add. Load a site on the left or paste one above.")
            return
        base = self._base_of(url)
        if not base:
            QMessageBox.warning(self, "Add Site", "Could not parse base domain for this URL.")
            return
        for s in self.user_sites:
            if self._base_of(s.get("url","")) == base:
                QMessageBox.information(self, "Add Site", f"Site for base '{base}' already exists in your list.")
                return
        name = base.split(".")[0].title()
        site = {
            "id": self._next_site_id(),
            "name": name,
            "url": url,
            "base": base,
            "category": "generator",
            "free_tier": True,
            "notes": ""
        }
        self.user_sites.append(site)
        save_user_sites(self.user_sites)
        self.refresh_sites_list()
        self.statusBar().showMessage(f"Added site: {base}", 4000)

    def remove_selected_site(self):
        item = self.listw.currentItem()
        if not item:
            QMessageBox.information(self, "Remove Site", "Select a site in the list first.")
            return
        site = item.data(Qt.ItemDataRole.UserRole)
        base = self._base_of(site.get("url",""))
        self.user_sites = [s for s in self.user_sites if self._base_of(s.get("url","")) != base]
        save_user_sites(self.user_sites)
        self.refresh_sites_list()
        self.statusBar().showMessage(f"Removed site: {base}", 4000)

    def restore_default_sites(self):
        if QMessageBox.question(self, "Restore Default 100", "Replace your user sites with the original 100 from the base config?") != QMessageBox.StandardButton.Yes:
            return
        defaults = self.cfg.get("sites", [])
        self.user_sites = list(defaults)
        if save_user_sites(self.user_sites):
            self.refresh_sites_list()
            self.statusBar().showMessage("Restored default 100 sites.", 4000)

    def clear_user_sites(self):
        if QMessageBox.question(self, "Clear User Sites", "Remove ALL user sites? This does not touch the base config. Continue?") != QMessageBox.StandardButton.Yes:
            return
        self.user_sites = []
        if save_user_sites(self.user_sites):
            self.refresh_sites_list()
            self.statusBar().showMessage("Cleared user sites.", 4000)

    # --- Prompts helpers ---
    def refresh_prompts_list(self):
        self.promptList.clear()
        # normalize merged prompts list (supports string or object items)
        self._prompt_objs = _normalize_prompts_list(self.user_prompts)
        # rebuild categories (keep selection)
        if hasattr(self, 'categoryBox'):
            cur = self.categoryBox.currentText() if self.categoryBox.currentIndex() >= 0 else 'Show All'
            cats = _extract_categories(self._prompt_objs)
            self.categoryBox.blockSignals(True)
            self.categoryBox.clear(); self.categoryBox.addItem('Show All')
            for c in cats:
                self.categoryBox.addItem(c)
            idx = self.categoryBox.findText(cur)
            self.categoryBox.setCurrentIndex(idx if idx >= 0 else 0)
            self.categoryBox.blockSignals(False)
            selected = self.categoryBox.currentText()
        else:
            selected = 'Show All'
        for obj in self._prompt_objs:
            cat = obj.get('category') or 'Base'
            if selected != 'Show All' and cat != selected:
                continue
            title = obj.get('title') or 'Untitled'
            it = QListWidgetItem(f"{cat} · {title}")
            it.setData(Qt.ItemDataRole.UserRole, obj)
            it.setToolTip(obj.get('text',''))
            self.promptList.addItem(it)

    def copy_selected_prompt(self):
        item = self.promptList.currentItem()
        if not item:
            item = self.promptList.item(0)
        if not item:
            QMessageBox.information(self, "Copy Prompt", "No prompt selected.")
            return

        obj = item.data(Qt.ItemDataRole.UserRole)
        base_text = (obj.get("text") if isinstance(obj, dict) else item.text()) or ""

        pid = self._get_prompt_pid(obj, base_text)
        if not hasattr(self, "_manual_placeholder_cache"):
            self._manual_placeholder_cache = {}
        cached_vals = list(self._manual_placeholder_cache.get(pid, []))

        def replace_once(s, val):
            return re.sub(r'""', f'"{val}"', s, count=1) if val else s

        p1 = self.character1Box.currentText() if hasattr(self, "character1Box") and self.character1Box.currentIndex() > 0 else ""
        p2 = self.character2Box.currentText() if hasattr(self, "character2Box") and self.character2Box.currentIndex() > 0 else ""
        if hasattr(self, "keepNamesCheck") and not self.keepNamesCheck.isChecked():
            p1 = ""; p2 = ""
        txt = replace_once(base_text, p1)
        txt = replace_once(txt, p2)

        for v in cached_vals:
            if v:
                txt = re.sub(r'""', f'"{v}"', txt, count=1)

        remaining = len(re.findall(r'""', txt))
        if remaining > 0:
            resp = QMessageBox.question(
                self,
                'Fill Empty Fields?',
                f'There are {remaining} empty "" fields.\nDo you want to fill them now?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if resp == QMessageBox.StandardButton.Yes:
                applied = []
                for i in range(remaining):
                    val, ok = QInputDialog.getText(self, "Fill Placeholder", f'Value for placeholder #{i+1}:')
                    if ok and val:
                        txt = re.sub(r'""', f'"{val}"', txt, count=1)
                        applied.append(val)
                if applied:
                    self._manual_placeholder_cache[pid] = cached_vals + applied

        QApplication.clipboard().setText(txt)
        self.statusBar().showMessage("Prompt copied to clipboard.", 3000)
        try:
            self.update_prompt_preview()
        except Exception:
            pass

    def update_prompt_preview(self, *_):
        # Get selected item safely
        try:
            item = self.promptList.currentItem()
        except Exception:
            item = None

        if not item:
            try:
                self.previewEdit.clear()
            except Exception:
                pass
            return

        # Resolve base_text from item/obj
        try:
            obj = item.data(Qt.ItemDataRole.UserRole)
        except Exception:
            obj = None
        if isinstance(obj, dict):
            base_text = obj.get('text') or obj.get('prompt') or ''
        else:
            try:
                base_text = item.text() or ''
            except Exception:
                base_text = ''

        text = base_text  # ensure defined

        # Helper: replace the first "" with val
        def replace_once(s, val):
            return re.sub(r'""', f'"{val}"', s, count=1) if (s and val) else s

        # Apply Character 1 / Character 2 to first two slots
        try:
            p1 = self.character1Box.currentText() if hasattr(self, 'character1Box') and self.character1Box.currentIndex() > 0 else ''
        except Exception:
            p1 = ''
        try:
            p2 = self.character2Box.currentText() if hasattr(self, 'character2Box') and self.character2Box.currentIndex() > 0 else ''
        except Exception:
            p2 = ''
        text = replace_once(text, p1)
        text = replace_once(text, p2)

        # Apply cached manual entries (left-to-right)
        try:
            pid = self._get_prompt_pid(obj, base_text)
            cached_vals = getattr(self, '_manual_placeholder_cache', {}).get(pid, [])
        except Exception:
            cached_vals = []
        for v in cached_vals:
            if v:
                text = re.sub(r'""', f'"{v}"', text, count=1)

        # Push to preview
        try:
            self.previewEdit.setPlainText(text or '')
        except Exception:
            pass
    
    def _edit_prompt_on_right_click(self, pos):
        item = self.promptList.itemAt(pos)
        if not item:
            return
        self._edit_prompt_item(item)

    def _edit_prompt_item(self, item):
        obj = item.data(Qt.ItemDataRole.UserRole)
        base_text = (obj.get("text") if isinstance(obj, dict) else "") or ""
        new_text, ok = QInputDialog.getMultiLineText(self, "Edit Prompt", "Prompt text:", base_text)
        if not ok or new_text is None:
            return
        new_text = new_text.strip()
        if not new_text:
            return

        # Default title from first line
        new_title = (new_text.splitlines()[0][:60] if new_text else "Untitled")
        old_id = (obj.get("id") if isinstance(obj, dict) else None)

        # If this prompt has title/tags metadata, offer edits for them too
        new_tags = None
        new_category = None
        if isinstance(obj, dict):
            cur_title = (obj.get("title") or new_title)
            t_title, ok_title = QInputDialog.getText(self, "Edit Title", "Title:", text=cur_title)
            if ok_title and (t_title or "").strip():
                new_title = t_title.strip()
            cur_category = (obj.get("category") or "User")
            t_cat, ok_cat = QInputDialog.getText(self, "Edit Category", "Category:", text=cur_category)
            if ok_cat and (t_cat or "").strip():
                new_category = t_cat.strip()
            else:
                new_category = cur_category


            cur_tags = obj.get("tags")
            if isinstance(cur_tags, (list, tuple)):
                cur_tags_str = ", ".join(str(t) for t in cur_tags if str(t).strip())
            elif isinstance(cur_tags, str):
                cur_tags_str = cur_tags
            else:
                cur_tags_str = ""
            t_tags, ok_tags = QInputDialog.getText(self, "Edit Tags", "Tags (comma-separated):", text=cur_tags_str)
            if ok_tags and t_tags is not None:
                new_tags = [t.strip() for t in t_tags.split(",") if t.strip()]

        # clear any cached placeholders for this prompt
        try:
            pid_old = self._get_prompt_pid(obj, base_text)
            if hasattr(self, "_manual_placeholder_cache"):
                self._manual_placeholder_cache.pop(pid_old, None)
        except Exception:
            pass

        # write-through to backing list (string or dict)
        updated = False
        for i, p in enumerate(self.user_prompts):
            if isinstance(p, dict):
                match = (old_id and p.get("id") == old_id) or (p.get("text") == base_text)
                if match:
                    p["text"] = new_text
                    p["title"] = new_title
                    if new_category is not None:
                        p["category"] = new_category
                    if new_tags is not None:
                        p["tags"] = new_tags
                    updated = True
                    break
            else:
                if p == base_text:
                    # Keep string-type prompts as strings
                    self.user_prompts[i] = new_text
                    updated = True
                    break

        if not updated:
            QMessageBox.information(self, "Edit Prompt", "Could not locate the prompt to update.")
            return

        save_user_prompts(self.user_prompts)
        self.refresh_prompts_list()
        self._reselect_prompt(old_id, new_text)
        try:
            self.update_prompt_preview()
        except Exception:
            pass
        self.statusBar().showMessage("Prompt updated.", 3000)

    def _reselect_prompt(self, pid, text):
        # reselect edited prompt in the list
        for i in range(self.promptList.count()):
            it = self.promptList.item(i)
            o = it.data(Qt.ItemDataRole.UserRole)
            if isinstance(o, dict):
                if pid and o.get("id") == pid:
                    self.promptList.setCurrentItem(it)
                    return
                if text and o.get("text") == text:
                    self.promptList.setCurrentItem(it)
                    return
                    
    def add_prompt_dialog(self):
        text, ok = QInputDialog.getMultiLineText(self, "Add Prompt", "Prompt text:")
        if not ok or not text.strip():
            return
        txt = text.strip()
        # Title default: first line up to 60 chars
        default_title = (txt.splitlines()[0][:60] if txt else "Untitled")
        title, ok = QInputDialog.getText(self, "Add Prompt", "Title:", text=default_title)
        if not ok: return
        cat, ok = QInputDialog.getText(self, "Add Prompt", "Category:", text="User")
        if not ok: return
        tag_str, ok = QInputDialog.getText(self, "Add Prompt", "Tags (comma-separated):", text="")
        if not ok: return
        tags = [t.strip() for t in tag_str.split(",") if t.strip()]

        new_obj = {"id": f"u{len(self.user_prompts):04d}", "title": title or default_title, "category": cat or "User", "tags": tags, "text": txt}
        self.user_prompts.append(new_obj)
        save_user_prompts(self.user_prompts)
        self.refresh_prompts_list()
        self.statusBar().showMessage("Prompt added.", 3000)
        
    def save_splitter_sizes(self):
        try:
            sizes = self.promptsSplitter.sizes()
        except Exception:
            sizes = None
        if not sizes:
            return
        if not isinstance(self.cfg.get("ui"), dict):
            self.cfg["ui"] = {}
        self.cfg["ui"]["prompts_splitter_sizes"] = [int(s) for s in sizes]
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
        if not isinstance(data.get("ui"), dict):
            data["ui"] = {}
        data["ui"]["prompts_splitter_sizes"] = [int(s) for s in sizes]
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


    def restore_default_prompts(self):
        if QMessageBox.question(self, "Restore Default Prompts", "Replace your user prompts with the base defaults?") != QMessageBox.StandardButton.Yes:
            return
        defaults = self.cfg.get("prompts", [])
        self.user_prompts = list(defaults)
        if save_user_prompts(self.user_prompts):
            self.refresh_prompts_list()
            self.statusBar().showMessage("Restored default prompts.", 4000)

    def clear_user_prompts(self):
        if QMessageBox.question(self, "Clear User Prompts", "Remove ALL user prompts? This does not touch the base defaults. Continue?") != QMessageBox.StandardButton.Yes:
            return
        self.user_prompts = []
        if save_user_prompts(self.user_prompts):
            self.refresh_prompts_list()
            self.statusBar().showMessage("Cleared user prompts.", 4000)

    def export_prompts_dialog(self):
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Export Prompts", "sora2_user_prompts_export.json", "JSON Files (*.json)")
            if not path:
                return
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"prompts": self.user_prompts}, f, indent=2)
            self.statusBar().showMessage(f"Exported prompts to {path}", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    def import_prompts_dialog(self):
        try:
            path, _ = QFileDialog.getOpenFileName(self, "Import Prompts", "", "JSON Files (*.json)")
            if not path:
                return
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "prompts" not in data:
                QMessageBox.warning(self, "Import Prompts", "Invalid format. Expecting an object with a 'prompts' array.")
                return
            self.user_prompts = data.get("prompts", [])
            save_user_prompts(self.user_prompts)
            self.refresh_prompts_list()
            self.statusBar().showMessage(f"Imported prompts from {path}", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Import Error", str(e))

    def restore_default_characters(self):
        if QMessageBox.question(self, "Restore Default Characters", "Replace your character list with the defaults from base?", QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        defaults = self.cfg.get("characters", [])
        characters = [sanitize_character_name(x) for x in defaults if sanitize_character_name(x)]
        characters = list(dict.fromkeys(characters))
        self.user_characters = characters
        save_user_characters(self.user_characters)
        self._reload_character_boxes()
        self.statusBar().showMessage("Restored default characters.", 4000)

    def clear_user_characters(self):
        if QMessageBox.question(self, "Clear User Characters", "Remove ALL user characters? This does not touch the base defaults. Continue?", QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        self.user_characters = []
        if save_user_characters(self.user_characters):
            self._reload_character_boxes()
            self.statusBar().showMessage("Cleared user characters.", 4000)

    def export_characters_dialog(self):
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Export Characters", "sora2_user_characters_export.json", "JSON Files (*.json)")
            if not path:
                return
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"characters": self.user_characters}, f, indent=2, ensure_ascii=False)
            self.statusBar().showMessage(f"Exported characters to {path}", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    def import_characters_dialog(self):
        try:
            path, _ = QFileDialog.getOpenFileName(self, "Import Characters", "", "JSON Files (*.json)")
            if not path:
                return
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            characters = data.get("characters", data if isinstance(data, list) else [])
            if not isinstance(characters, list):
                QMessageBox.warning(self, "Import Characters", "Invalid format. Expecting an object with a 'characters' array or a flat array.")
                return
            characters = [sanitize_character_name(x) for x in characters]
            characters = [x for x in characters if x]
            characters = list(dict.fromkeys(characters))
            self.user_characters = characters
            save_user_characters(self.user_characters)
            self._reload_character_boxes()
            self.statusBar().showMessage(f"Imported {len(characters)} characters.", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Import Error", str(e))

    def _reload_character_boxes(self):
        p1 = self.character1Box.currentText() if self.character1Box.currentIndex() > 0 else None
        p2 = self.character2Box.currentText() if self.character2Box.currentIndex() > 0 else None
        for box in (self.character1Box, self.character2Box):
            box.blockSignals(True)
            box.clear()
            box.addItem("— None —")
            for name in self.user_characters:
                box.addItem(name)
            box.blockSignals(False)
        if p1 and p1 in self.user_characters:
            self.character1Box.setCurrentText(p1)
        else:
            self.character1Box.setCurrentIndex(0)
        if p2 and p2 in self.user_characters:
            self.character2Box.setCurrentText(p2)
        else:
            self.character2Box.setCurrentIndex(0)



    # --- Persist window + orientation + UA on close ---
    def closeEvent(self, e):
        try:
            self.cfg["window"]["width"] = self.width()
            self.cfg["window"]["height"] = self.height()
            self.cfg["window"]["orientation"] = "vertical" if self.contentSplit.orientation()==Qt.Orientation.Vertical else "horizontal"
            label = next((k for k,v in PRESET_UAS.items() if v==self.current_ua), "Custom")
            self.cfg["window"]["user_agent"] = label if label!="Custom" else self.current_ua
            save_config(self.cfg)
            try:
                self.save_splitter_sizes()
            except Exception:
                pass
        except Exception:
            pass
        super().closeEvent(e)

    def remove_selected_prompt(self):
        item = self.promptList.currentItem()
        if not item:
            QMessageBox.information(self, "Remove Prompt", "Select a prompt first.")
            return
        obj = item.data(Qt.ItemDataRole.UserRole)
        def _same(p):
            if isinstance(p, dict) and isinstance(obj, dict):
                return p.get('id') == obj.get('id') or p.get('text') == obj.get('text')
            elif isinstance(p, str) and isinstance(obj, dict):
                return p == obj.get('text')
            elif isinstance(p, dict) and isinstance(obj, str):
                return p.get('text') == obj
            else:
                return p == obj
        self.user_prompts = [p for p in self.user_prompts if not _same(p)]
        save_user_prompts(self.user_prompts)
        self.refresh_prompts_list()
        self.statusBar().showMessage("Prompt removed.", 3000)
    def _apply_pending_tmp_updates(self):
        """At startup, apply updates only if BOTH .tmp files exist; otherwise discard and warn."""

        base_dir = os.path.dirname(os.path.abspath(__file__))
        py_name  = "sora2-browser-tool.py"
        py_dst   = os.path.join(base_dir, py_name)
        json_dst = os.path.join(base_dir, "sora2_config.json")
        py_tmp   = os.path.join(base_dir, py_name + ".tmp")
        json_tmp = os.path.join(base_dir, "sora2_config.json.tmp")

        has_py_tmp   = os.path.exists(py_tmp)
        has_json_tmp = os.path.exists(json_tmp)

        # Nothing to do
        if not has_py_tmp and not has_json_tmp:
            return

        # Incomplete update -> discard and warn
        if not (has_py_tmp and has_json_tmp):
            try:
                if has_py_tmp: os.remove(py_tmp)
            except Exception:
                pass
            try:
                if has_json_tmp: os.remove(json_tmp)
            except Exception:
                pass
            try:
                        QMessageBox.warning(self, "Update Error",
                                    "An incomplete update was detected and has been discarded.\nPlease run 'Check For Updates' again.")
            except Exception:
                pass
            return

        # Both .tmp exist -> attempt atomic replace now
        def try_swap():
            ok = True
            try:
                os.replace(json_tmp, json_dst)  # JSON first
            except Exception:
                ok = False
            try:
                os.replace(py_tmp, py_dst)      # then PY
            except Exception:
                ok = False
            return ok

        if try_swap():
            return

        # If replacing PY fails (likely on Windows), write a helper that will finish after app exits
        helper_code = (
            "# -*- coding: utf-8 -*-\n"
            "import os, sys, time\n"
            "base_dir = " + repr(base_dir) + "\n"
            "py_name  = " + repr(py_name) + "\n"
            "py_dst   = os.path.join(base_dir, py_name)\n"
            "json_dst = os.path.join(base_dir, 'sora2_config.json')\n"
            "py_tmp   = os.path.join(base_dir, py_name + '.tmp')\n"
            "json_tmp = os.path.join(base_dir, 'sora2_config.json.tmp')\n"
            "for _ in range(600):\n"
            "    done = True\n"
            "    try:\n"
            "        if os.path.exists(json_tmp): os.replace(json_tmp, json_dst)\n"
            "    except Exception:\n"
            "        done = False\n"
            "    try:\n"
            "        if os.path.exists(py_tmp): os.replace(py_tmp, py_dst)\n"
            "    except Exception:\n"
            "        done = False\n"
            "    if done: break\n"
            "    time.sleep(0.1)\n"
        )

        try:
            tmp_dir = tempfile.gettempdir()
            helper_path = os.path.join(tmp_dir, "sora2_apply_update.py")
            with open(helper_path, "w", encoding="utf-8") as f:
                f.write(helper_code)
            # Launch helper detached; it will finish the swap when the app is closed
            try:
                QProcess.startDetached(sys.executable, [helper_path])
            except Exception:
                import subprocess
                try:
                    subprocess.Popen([sys.executable, helper_path],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
                except Exception:
                    pass
            try:
                self.statusBar().showMessage("Update staged. It will finish when you close the app.", 5000)
            except Exception:
                pass
        except Exception:
            # Ignore if helper creation fails; user can retry update.
            return
    def clear_site_data(self):
        """Clear all site data (cookies, cache, local/session storage, indexedDB) and reload views."""
        import shutil

        confirm = QMessageBox.question(
            self, "Clear Site Data",
            "This will clear cookies, cache, local/session storage, and IndexedDB for all sites. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            store = self.profile.cookieStore()
            if store is not None:
                store.deleteAllCookies()
        except Exception:
            pass

        try:
            self.profile.clearHttpCache()
        except Exception:
            pass

        try:
            storage_dir = self.profile.persistentStoragePath()
        except Exception:
            storage_dir = None
        try:
            if storage_dir and os.path.isdir(storage_dir):
                for root, dirs, files in os.walk(storage_dir, topdown=False):
                    for f in files:
                        try: os.remove(os.path.join(root, f))
                        except Exception: pass
                    for d in dirs:
                        try: shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                        except Exception: pass
        except Exception:
            pass

        js = "(async function(){try{localStorage.clear();sessionStorage.clear();if(window.indexedDB&&indexedDB.databases){let dbs=await indexedDB.databases();for(const db of dbs){if(db&&db.name){try{indexedDB.deleteDatabase(db.name);}catch(e){}}}}catch(e){}})();"
        try:
            for view in self.findChildren(QWebEngineView):
                try:
                    view.page().runJavaScript(js)
                except Exception:
                    pass
        except Exception:
            pass

        try:
            QMessageBox.information(self, "Site Data Cleared", "Site data cleared. Reloading open pages.")
        except Exception:
            pass
        try:
            for view in self.findChildren(QWebEngineView):
                try:
                    view.reload()
                except Exception:
                    pass
        except Exception:
            pass
                
    def check_for_updates(self):
        """Check GitHub JSON for a newer version; if present, download .tmp files into script dir."""
        REMOTE_JSON = "https://raw.githubusercontent.com/esc0rtd3w/sora2-browser-tool/refs/heads/main/sora2_config.json"
        REMOTE_PY   = "https://raw.githubusercontent.com/esc0rtd3w/sora2-browser-tool/refs/heads/main/sora2-browser-tool.py"

        def _ver_tuple(v):
            # extract all ints; fallback [0] if nothing
            return tuple(int(x) for x in re.findall(r"\d+", str(v)) or [0])

        try:
            # Fetch remote config + version
            with urllib.request.urlopen(REMOTE_JSON, timeout=15) as r:
                remote_cfg = json.loads(r.read().decode("utf-8", "ignore"))
            remote_ver = remote_cfg.get("version", "0.0.0")
            local_ver  = (self.cfg or {}).get("version", "0.0.0")

            # Already up to date
            if _ver_tuple(remote_ver) <= _ver_tuple(local_ver):
                QMessageBox.information(
                    self,
                    "Check For Updates",
                    f"You're up to date.\n\nLocal: {local_ver}\nRemote: {remote_ver}",
                )
                return

            # Ask to download
            resp = QMessageBox.question(
                self,
                "Update Available",
                (
                    f"A new version is available.\n\n"
                    f"Current: {local_ver}\n"
                    f"Available: {remote_ver}\n\n"
                    f"Download now?"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if resp != QMessageBox.StandardButton.Yes:
                return

            # Ask whether to auto-close after download
            auto_close = QMessageBox.question(
                self,
                "Close After Download?",
                "Automatically close the app after the update files finish downloading? (Recommended)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            ) == QMessageBox.StandardButton.Yes

            base_dir = os.path.dirname(os.path.abspath(__file__))
            py_tmp   = os.path.join(base_dir, "sora2-browser-tool.py.tmp")
            json_tmp = os.path.join(base_dir, "sora2_config.json.tmp")

            # Download new files as .tmp
            urllib.request.urlretrieve(REMOTE_PY, py_tmp)
            with open(json_tmp, "w", encoding="utf-8") as f:
                json.dump(remote_cfg, f, indent=2, ensure_ascii=False)

            if auto_close:
                QMessageBox.information(
                    self,
                    "Update Downloaded",
                    "Update files downloaded.\n\n"
                    "The app will close now. Relaunch to finish applying the update.",
                )
                QApplication.instance().quit()
            else:
                QMessageBox.information(
                    self,
                    "Update Downloaded",
                    "Update files downloaded.\n\n"
                    "On next launch, the update will apply automatically.",
                )
        except Exception as e:
            QMessageBox.critical(self, "Update Error", f"Failed to update:\n{e}")
def main():
    app = QApplication(sys.argv)
    w = Main(); w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
