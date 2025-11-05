#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Sora 2 Browser Tool

import os, sys, re, json, tempfile, random, mimetypes, pathlib, webbrowser
from urllib.parse import urlparse

from PyQt6.QtCore import Qt, QUrl, QSize
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QPushButton, QLineEdit, QComboBox, QLabel,
    QMessageBox, QInputDialog, QTabWidget
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
            "version": "1.1.7",
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
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
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
                json.dump({"sites": sites}, f, indent=2)
        return sites
    except Exception:
        return list(default_sites)

def save_user_sites(sites):
    try:
        with open(USER_SITES_PATH, "w", encoding="utf-8") as f:
            json.dump({"sites": sites}, f, indent=2)
        return True
    except Exception:
        return False

def load_or_init_user_prompts(default_prompts):
    """Load user prompts from USER_PROMPTS_PATH; if missing, seed with defaults and write file."""
    try:
        if os.path.exists(USER_PROMPTS_PATH):
            with open(USER_PROMPTS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            prompts = data.get("prompts", data if isinstance(data, list) else [])
        else:
            prompts = list(default_prompts)
            with open(USER_PROMPTS_PATH, "w", encoding="utf-8") as f:
                json.dump({"prompts": prompts}, f, indent=2)
        return prompts
    except Exception:
        return list(default_prompts)

def save_user_prompts(prompts):
    try:
        with open(USER_PROMPTS_PATH, "w", encoding="utf-8") as f:
            json.dump({"prompts": prompts}, f, indent=2)
        return True
    except Exception:
        return False



def sanitize_person_name(name: str) -> str:
    import re as _re
    s = _re.sub(r"[^A-Za-z0-9 '\-]", "", str(name))
    s = _re.sub(r"\s+", " ", s).strip()
    return s

def load_or_init_user_persons(default_persons):
    try:
        if os.path.exists(USER_PERSONS_PATH):
            with open(USER_PERSONS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            persons = data.get("persons", data if isinstance(data, list) else [])
        else:
            persons = list(default_persons)
            with open(USER_PERSONS_PATH, "w", encoding="utf-8") as f:
                json.dump({"persons": persons}, f, indent=2, ensure_ascii=False)
        persons = [sanitize_person_name(x) for x in persons]
        persons = [x for x in persons if x]
        persons = list(dict.fromkeys(persons))
        return persons
    except Exception:
        return [sanitize_person_name(x) for x in (default_persons or []) if sanitize_person_name(x)]

def save_user_persons(persons):
    try:
        with open(USER_PERSONS_PATH, "w", encoding="utf-8") as f:
            json.dump({"persons": persons}, f, indent=2, ensure_ascii=False)
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

class Main(QMainWindow):
    def __init__(self):
        super().__init__()
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
            self.current_ua = 'DEFAULT'
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

        m_persons = menubar.addMenu("Persons")
        a_rp = m_persons.addAction("Restore Default Persons…"); a_rp.triggered.connect(self.restore_default_persons)
        a_cp = m_persons.addAction("Clear User Persons…"); a_cp.triggered.connect(self.clear_user_persons)
        m_persons.addSeparator()
        a_ep = m_persons.addAction("Export…"); a_ep.triggered.connect(self.export_persons_dialog)
        a_ip = m_persons.addAction("Import…"); a_ip.triggered.connect(self.import_persons_dialog)



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
        self.uaPreset = QComboBox(); self.uaPreset.addItems(list(PRESET_UAS.keys()))
        preset_label = next((k for k,v in PRESET_UAS.items() if v==self.current_ua), "Chrome (Windows)")
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
        for site in self.user_sites:
            txt = f'{site.get("id",0):02d}. {site.get("url","")}'
            it = QListWidgetItem(txt)
            it.setData(Qt.ItemDataRole.UserRole, site)
            it.setToolTip(site.get("url",""))
            it.setSizeHint(QSize(100,28))
            self.listw.addItem(it)
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

        self.user_persons = load_or_init_user_persons(self.cfg.get("persons", []))

        # --- Person selectors (Person 1 & Person 2) ---
        personRow = QHBoxLayout()
        personRow.addWidget(QLabel("Person 1:"))
        self.person1Box = QComboBox()
        self.person1Box.addItem("— None —")
        self.person1Box.addItems(self.user_persons)
        personRow.addWidget(self.person1Box)
        personRow.addSpacing(8)
        personRow.addWidget(QLabel("Person 2:"))
        self.person2Box = QComboBox()
        self.person2Box.addItem("— None —")
        self.person2Box.addItems(self.user_persons)
        personRow.addWidget(self.person2Box)
        rp_v.addLayout(personRow)

        self.promptList = QListWidget()
        for p in self.user_prompts:
            it = QListWidgetItem(p)
            it.setToolTip(p)
            self.promptList.addItem(it)
        self.promptList.itemClicked.connect(self.copy_selected_prompt)
        rp_v.addWidget(self.promptList, 1)

        # add left/right panes to the actions splitter
        self.actionsSplit.addWidget(leftActions)
        self.actionsSplit.addWidget(rightPrompts)
        # align actions split with content split via pane_ratio
        self.actionsSplit.setSizes([int(1000*self.cfg['window'].get('pane_ratio',0.5)), int(1000*(1.0-self.cfg['window'].get('pane_ratio',0.5)))])

        self.actionsSplit.setSizes([1100, 700])  # initial ratio; user can drag

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
        for p in self.user_prompts:
            it = QListWidgetItem(p); it.setToolTip(p)
            self.promptList.addItem(it)

    
    def copy_selected_prompt(self):
        item = self.promptList.currentItem()
        if not item:
            item = self.promptList.item(0)
        if not item:
            QMessageBox.information(self, "Copy Prompt", "No prompt selected.")
            return
        text = item.text()

        # Fill "" placeholders with selected persons and optional user inputs
        def replace_first_empty(s, repl):
            return re.sub(r'""', f'"{repl}"', s, count=1)

        p1 = self.person1Box.currentText() if hasattr(self, 'person1Box') else "— None —"
        p2 = self.person2Box.currentText() if hasattr(self, 'person2Box') else "— None —"
        if p1 == "— None —":
            p1 = None
        if p2 == "— None —":
            p2 = None

        # Apply Person 1 then Person 2
        if p1:
            text = replace_first_empty(text, p1)
        if p2:
            text = replace_first_empty(text, p2)

        # Check for remaining empty ""
        remaining = len(re.findall(r'""', text))
        if remaining > 0:
            resp = QMessageBox.question(
                self, "Fill Empty Fields?",
                f"There are {remaining} empty \"\" fields.\nDo you want to fill them now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
            )
            if resp == QMessageBox.StandardButton.Yes:
                # Ask user for each remaining value, in order
                values = []
                for i in range(remaining):
                    val, ok = QInputDialog.getText(self, "Fill Placeholder",
                                                   f'Enter text for placeholder #{i+1} (leave blank to keep empty):')
                    if not ok:
                        val = ""
                    values.append(val)
                # Replace sequentially
                for val in values:
                    if val:
                        text = re.sub(r'""', f'"{val}"', text, count=1)

        QApplication.clipboard().setText(text)
        self.statusBar().showMessage("Prompt copied to clipboard.", 3000)

    def add_prompt_dialog(self):
        text, ok = QInputDialog.getMultiLineText(self, "Add Prompt", "Prompt text:")
        if not ok or not text.strip():
            return
        self.user_prompts.append(text.strip())
        save_user_prompts(self.user_prompts)
        self.refresh_prompts_list()
        self.statusBar().showMessage("Prompt added.", 3000)

    def remove_selected_prompt(self):
        item = self.promptList.currentItem()
        if not item:
            QMessageBox.information(self, "Remove Prompt", "Select a prompt first.")
            return
        txt = item.text()
        self.user_prompts = [p for p in self.user_prompts if p != txt]
        save_user_prompts(self.user_prompts)
        self.refresh_prompts_list()
        self.statusBar().showMessage("Prompt removed.", 3000)

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
            from PyQt6.QtWidgets import QFileDialog
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
            from PyQt6.QtWidgets import QFileDialog
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

    def restore_default_persons(self):
        if QMessageBox.question(self, "Restore Default Persons", "Replace your person list with the defaults from base?", QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        defaults = self.cfg.get("persons", [])
        persons = [sanitize_person_name(x) for x in defaults if sanitize_person_name(x)]
        persons = list(dict.fromkeys(persons))
        self.user_persons = persons
        save_user_persons(self.user_persons)
        self._reload_person_boxes()
        self.statusBar().showMessage("Restored default persons.", 4000)

    def clear_user_persons(self):
        if QMessageBox.question(self, "Clear User Persons", "Remove ALL user persons? This does not touch the base defaults. Continue?", QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        self.user_persons = []
        if save_user_persons(self.user_persons):
            self._reload_person_boxes()
            self.statusBar().showMessage("Cleared user persons.", 4000)

    def export_persons_dialog(self):
        try:
            from PyQt6.QtWidgets import QFileDialog
            path, _ = QFileDialog.getSaveFileName(self, "Export Persons", "sora2_user_persons_export.json", "JSON Files (*.json)")
            if not path:
                return
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"persons": self.user_persons}, f, indent=2, ensure_ascii=False)
            self.statusBar().showMessage(f"Exported persons to {path}", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    def import_persons_dialog(self):
        try:
            from PyQt6.QtWidgets import QFileDialog
            path, _ = QFileDialog.getOpenFileName(self, "Import Persons", "", "JSON Files (*.json)")
            if not path:
                return
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            persons = data.get("persons", data if isinstance(data, list) else [])
            if not isinstance(persons, list):
                QMessageBox.warning(self, "Import Persons", "Invalid format. Expecting an object with a 'persons' array or a flat array.")
                return
            persons = [sanitize_person_name(x) for x in persons]
            persons = [x for x in persons if x]
            persons = list(dict.fromkeys(persons))
            self.user_persons = persons
            save_user_persons(self.user_persons)
            self._reload_person_boxes()
            self.statusBar().showMessage(f"Imported {len(persons)} persons.", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Import Error", str(e))

    def _reload_person_boxes(self):
        p1 = self.person1Box.currentText() if self.person1Box.currentIndex() > 0 else None
        p2 = self.person2Box.currentText() if self.person2Box.currentIndex() > 0 else None
        for box in (self.person1Box, self.person2Box):
            box.blockSignals(True)
            box.clear()
            box.addItem("— None —")
            for name in self.user_persons:
                box.addItem(name)
            box.blockSignals(False)
        if p1 and p1 in self.user_persons:
            self.person1Box.setCurrentText(p1)
        else:
            self.person1Box.setCurrentIndex(0)
        if p2 and p2 in self.user_persons:
            self.person2Box.setCurrentText(p2)
        else:
            self.person2Box.setCurrentIndex(0)



    # --- Persist window + orientation + UA on close ---
    def closeEvent(self, e):
        try:
            self.cfg["window"]["width"] = self.width()
            self.cfg["window"]["height"] = self.height()
            self.cfg["window"]["orientation"] = "vertical" if self.contentSplit.orientation()==Qt.Orientation.Vertical else "horizontal"
            label = next((k for k,v in PRESET_UAS.items() if v==self.current_ua), "Custom")
            self.cfg["window"]["user_agent"] = label if label!="Custom" else self.current_ua
            save_config(self.cfg)
        except Exception:
            pass
        super().closeEvent(e)

def main():
    app = QApplication(sys.argv)
    w = Main(); w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()