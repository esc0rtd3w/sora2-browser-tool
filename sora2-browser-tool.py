#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Sora 2 Browser Tool

# Dependency bootstrap
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
    QMessageBox, QInputDialog, QTabWidget, QCheckBox, QCompleter, QFileDialog,
    QSizePolicy, QWidgetAction
)
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtGui import QDesktopServices

# Cloudflare/Turnstile compatibility flags (GPU + third-party cookies)
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
USER_MAIL_SITES_PATH = os.path.join(os.path.dirname(__file__), "sora2_user_mail_sites.json")


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

DEFAULT_HELP_HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>About -> Help</title>
  <style>
    :root {
      color-scheme: dark light;
    }
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 1.5rem;
      line-height: 1.5;
      max-width: 960px;
    }
    h1 {
      font-size: 1.6rem;
      margin-bottom: 0.4rem;
    }
    h2 {
      font-size: 1.1rem;
      margin: 1.2rem 0 0.4rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      font-weight: 600;
      opacity: 0.85;
    }
    p {
      margin: 0.3rem 0 0.5rem;
    }
    ol {
      padding-left: 1.4rem;
      margin: 0.4rem 0 0.6rem;
    }
    li {
      margin: 0.2rem 0 0.4rem;
    }
    .step-title {
      font-weight: 600;
    }
    .tagline {
      opacity: 0.8;
      margin-bottom: 0.9rem;
    }
    code {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      font-size: 0.9em;
      padding: 0.05rem 0.3rem;
      border-radius: 0.25rem;
      background: rgba(0,0,0,0.06);
    }
    ul {
      margin: 0.3rem 0 0.3rem;
      padding-left: 1.2rem;
    }
    .hint {
      font-size: 0.9rem;
      opacity: 0.85;
    }
    .pill {
      display: inline-block;
      padding: 0.1rem 0.5rem;
      border-radius: 999px;
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      opacity: 0.85;
      border: 1px solid rgba(0,0,0,0.1);
    }
  </style>
</head>
<body>
  <h1>Sora 2 Browser Tool Help</h1>
  <p class="tagline">
    <span class="pill">Quick Start</span>
    &nbsp;Use the bottom left side for AI site, the bottom right for email, top left to change site, and the top right for prompts.
  </p>

  <h2>Basic workflow</h2>
  <ol>
    <li>
      <span class="step-title">Load a site from above</span><br>
      Use the URL box or the <code>Sites</code> list above to open your Sora/AI site in a new tab, on the left side.
    </li>
    <li>
      <span class="step-title">Sign up or log in</span><br>
      Start the sign-up or login on the left, using an email provider from the <code>Mail Sites</code> list.
    </li>
    <li>
      <span class="step-title">Check email on the right</span><br>
      Use default or pick a mail site from the <code>Mail Sites</code> list to load it in the right browser, then copy email address and use on left browser, then wait for confirmation links or one-time codes.
    </li>
    <li>
      <span class="step-title">Confirm your account</span><br>
      On the right side, click the confirmation link or copy the code, then switch back to the left side to finish sign-up.
    </li>
    <li>
      <span class="step-title">Build a prompt</span><br>
      Use:
      <ul>
        <li><code>Prompts</code> list to pick a base prompt, or use the <code>Add</code> button to create a new prompt.</li>
        <li><code>Characters</code> drop down boxes and manual entry to inject style/character details.</li>
      </ul>
    </li>
    <li>
      <span class="step-title">Copy the prompt into the site</span><br>
      Copy the prompt using <code>Copy</code> button, and paste into the text box on the left page (your AI/video tool).
    </li>
    <li>
      <span class="step-title">Generate your video</span><br>
      Use the site’s own <code>Generate</code> / <code>Submit</code> button on the left to start the render.
    </li>
    <li>
      <span class="step-title">Download and open results</span><br>
      When the site finishes, download the video in the left browser. Files are saved to your configured download folder (see toolbar <code>Downloads…</code> option) — open that folder in your file manager to play the video.
    </li>
  </ol>

  <p class="hint">
    You can customize this help page by editing <code>help_html</code> in <code>sora2_config.json</code>.
  </p>
</body>
</html>
"""

MAIL_SITE_DEFAULTS = []
PROMPT_DEFAULTS = []
def load_config():
    if not os.path.exists(CONFIG_PATH):
        QMessageBox.warning(None, "Config", f"Config not found at {CONFIG_PATH}. Using defaults.")
        return {
            "version": "1.2.9",
            "window": {"width": 1920,"height": 1080,"orientation":"horizontal","user_agent":"Default (Engine)","mail_url":"https://www.guerrillamail.com/inbox","window_title":"Sora 2 Browser Tool"},
            "sites": [],
            "prompts": [],
            "mail_sites": [],
        }
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    if "prompts" not in cfg:
        cfg["prompts"] = PROMPT_DEFAULTS
    if "mail_sites" not in cfg:
        cfg["mail_sites"] = MAIL_SITE_DEFAULTS
    return cfg

def save_config(cfg):
    try:
        # Preserve existing and only update window/ui/version
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
    # Load user sites from USER_SITES_PATH; if missing, seed with defaults and write file.
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

def load_or_init_user_mail_sites(default_mail_sites):
    # Load user mail sites from USER_MAIL_SITES_PATH; if missing, seed with defaults and write file.
    try:
        if os.path.exists(USER_MAIL_SITES_PATH):
            with open(USER_MAIL_SITES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                sites = data.get("mail_sites", [])
            elif isinstance(data, list):
                sites = data
            else:
                sites = []
        else:
            sites = list(default_mail_sites)
            with open(USER_MAIL_SITES_PATH, "w", encoding="utf-8") as f:
                json.dump({"mail_sites": sites}, f, indent=2, ensure_ascii=False)
        if not isinstance(sites, list):
            sites = list(default_mail_sites)
        return sites
    except Exception:
        return list(default_mail_sites)

def save_user_mail_sites(sites):
    try:
        with open(USER_MAIL_SITES_PATH, "w", encoding="utf-8") as f:
            json.dump({"mail_sites": sites}, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False

def load_or_init_user_prompts(default_prompts):
    # Load user prompts; if file missing or empty, seed with defaults and persist. Return the list.
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


# Prompt helpers
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

def _normalize_characters_cfg_list(chars):
    objs = []
    for c in chars or []:
        if isinstance(c, dict):
            name = (" ".join(str(c.get("name", "")).split())).strip()
            cat = (" ".join(str(c.get("category", "Base")).split())).strip() or "Base"
        else:
            name = (" ".join(str(c).split())).strip()
            cat = "Base"
        if not name:
            continue
        objs.append({"name": name, "category": cat})
    # dedupe by lowercased name, keep first
    seen = set()
    result = []
    for o in objs:
        key = o["name"].lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(o)
    return result

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
    # Load user characters from USER_CHARACTERS_PATH; if missing/empty, seed with defaults and persist.
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
        # Return a stable id for the selected prompt, using explicit id
        # or hashing "title|text" when no explicit id is present.
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
        window_cfg = self.cfg.get("window")
        if not isinstance(window_cfg, dict):
            window_cfg = {
                "width": 1920,
                "height": 1080,
                "orientation": "horizontal",
                "user_agent": "Default (Engine)",
                "mail_url": "https://www.guerrillamail.com/inbox",
                "window_title": "Sora 2 Browser Tool",
            }
        self.cfg["window"] = window_cfg

        raw_help = self.cfg.get("help_html", "")
        if not isinstance(raw_help, str):
            raw_help = ""
        self.startup_html = (raw_help.strip() or DEFAULT_HELP_HTML)
        self.user_mail_sites = load_or_init_user_mail_sites(self.cfg.get("mail_sites", MAIL_SITE_DEFAULTS))
        self.setWindowTitle(window_cfg.get("window_title", "Sora 2 Browser Tool"))

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
            
        window_cfg = self.cfg.get("window") or {}
        ua_label = window_cfg.get("user_agent", "Default (Engine)")
        if not isinstance(ua_label, str):
            ua_label = "Default (Engine)"
        if ua_label.startswith("Default"):
            self.current_ua = "Default (Engine)"
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
            self.resize(self.cfg['window'].get('width',1920), self.cfg['window'].get('height',1080))

        # Root: Actions / Content
        self.rootSplit = QSplitter(Qt.Orientation.Vertical)
        self.setCentralWidget(self.rootSplit)

        # Menubar
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

        m_view.addSeparator()
        self.act_toggle_left_fs = m_view.addAction("Toggle Sites Pane Fullscreen")
        self.act_toggle_left_fs.triggered.connect(self.toggle_left_pane_fullscreen)
        self.act_toggle_right_fs = m_view.addAction("Toggle Mail Pane Fullscreen")
        self.act_toggle_right_fs.triggered.connect(self.toggle_right_pane_fullscreen)

        m_view.addSeparator()
        self.act_zoom_left_in = m_view.addAction("Zoom In (Sites Pane)")
        self.act_zoom_left_in.triggered.connect(lambda: self.change_left_zoom(0.1))
        self.act_zoom_left_out = m_view.addAction("Zoom Out (Sites Pane)")
        self.act_zoom_left_out.triggered.connect(lambda: self.change_left_zoom(-0.1))
        self.act_zoom_left_reset = m_view.addAction("Reset Zoom (Sites Pane)")
        self.act_zoom_left_reset.triggered.connect(lambda: self.set_left_zoom(1.0))

        m_view.addSeparator()
        self.act_zoom_right_in = m_view.addAction("Zoom In (Mail Pane)")
        self.act_zoom_right_in.triggered.connect(lambda: self.change_right_zoom(0.1))
        self.act_zoom_right_out = m_view.addAction("Zoom Out (Mail Pane)")
        self.act_zoom_right_out.triggered.connect(lambda: self.change_right_zoom(-0.1))
        self.act_zoom_right_reset = m_view.addAction("Reset Zoom (Mail Pane)")
        self.act_zoom_right_reset.triggered.connect(lambda: self.set_right_zoom(1.0))

        m_view.addSeparator()
        a_view_export = m_view.addAction("Export…")
        a_view_export.triggered.connect(self.export_view_toolbar_dialog)
        a_view_import = m_view.addAction("Import…")
        a_view_import.triggered.connect(self.import_view_toolbar_dialog)

        m_tools = menubar.addMenu("Tools")
        m_tools_ua = m_tools.addMenu("User Agent")
        
        # mirror the preset list in a submenu
        m_tools_ua.addAction('Default (Engine)').triggered.connect(lambda _, lab='Default (Engine)': self.set_user_agent(None, preset_label=lab))
        for label in PRESET_UAS.keys():
            a = m_tools_ua.addAction(label)
            a.triggered.connect(lambda _, lab=label: self.set_user_agent(PRESET_UAS[lab], preset_label=lab))
            
        #m_tools_ua.addSeparator()
        #a_apply = m_tools_ua.addAction("Apply UA (from fields)"); a_apply.triggered.connect(self.apply_ua_clicked)
        #a_random = m_tools_ua.addAction("Random UA"); a_random.triggered.connect(self.random_ua_clicked)
        #a_reset = m_tools_ua.addAction("Reset UA"); a_reset.triggered.connect(self.reset_ua_clicked)
        #a_mobile = m_tools_ua.addAction("Try Mobile WebM"); a_mobile.triggered.connect(self.use_mobile_ua)

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
        self.m_mail_sites = menubar.addMenu("Switch Email Site")
        self._build_mail_sites_menu(self.m_mail_sites)
        a_update = menubar.addAction("Check For Updates"); a_update.triggered.connect(self.check_for_updates)

        # Actions (split left actions | right prompts)
        actions = QWidget(); act_v = QVBoxLayout(actions)
        act_v.setContentsMargins(6,6,6,6); act_v.setSpacing(8)

        self.actionsSplit = QSplitter(Qt.Orientation.Horizontal)
        act_v.addWidget(self.actionsSplit, 1)

        # LEFT ACTIONS (existing UI)
        leftActions = QWidget(); la_v = QVBoxLayout(leftActions)
        la_v.setContentsMargins(0,0,0,0); la_v.setSpacing(8)

        bar = QWidget(); row = QHBoxLayout(bar); row.setContentsMargins(0,0,0,0); row.setSpacing(8)
        self.addr = QLineEdit(); self.addr.setPlaceholderText("Paste any Sora 2 URL and press Enter")
        self.addr.returnPressed.connect(self.load_left_addr)
        row.addWidget(QLabel("URL:")); row.addWidget(self.addr,1)

        #row.addWidget(QLabel("UA:"))
        self.uaPreset = QComboBox(); self.uaPreset.addItem('Default (Engine)'); self.uaPreset.addItems(list(PRESET_UAS.keys()))
        preset_label = 'Default (Engine)' if self.current_ua == 'Default (Engine)' else next((k for k,v in PRESET_UAS.items() if v==self.current_ua), "Chrome (Windows)")
        self.uaPreset.setCurrentText(preset_label)
        #self.uaCustom = QLineEdit(); self.uaCustom.setPlaceholderText("Custom UA…")

        #self.btnApplyUA = QPushButton("Apply UA"); self.btnApplyUA.clicked.connect(self.apply_ua_clicked)
        # self.btnRandomUA = QPushButton("Random UA"); self.btnRandomUA.clicked.connect(self.random_ua_clicked)
        # self.btnResetUA = QPushButton("Reset"); self.btnResetUA.clicked.connect(self.reset_ua_clicked)
        #self.btnMobileUA = QPushButton("Try Mobile WebM"); self.btnMobileUA.clicked.connect(self.use_mobile_ua)
        self.btnClear = QPushButton("Clear reCAPTCHA Cookies"); self.btnClear.clicked.connect(self.clear_recaptcha_cookies)
        self.btnToggle = QPushButton("Top/Bottom"); self.btnToggle.clicked.connect(self.switch_orientation)
        #self.btnExternal = QPushButton("Open Externally"); self.btnExternal.clicked.connect(self.open_external)
        self.btnOpenPrivate = QPushButton("Open Private"); self.btnOpenPrivate.clicked.connect(self.open_private)
        self.btnOpenMedia = QPushButton("Open Media"); self.btnOpenMedia.clicked.connect(self.open_media_externally)
        self.btnOpenDownloads = QPushButton("Open Downloads"); self.btnOpenDownloads.clicked.connect(self.open_download_dir)
        self.btnSetDownloadDir = QPushButton("Set Download Directory"); self.btnSetDownloadDir.clicked.connect(self.change_download_dir)
        #row.addWidget(self.uaPreset); row.addWidget(self.uaCustom,1)
        for b in (self.btnToggle, self.btnOpenPrivate, self.btnOpenMedia, self.btnOpenDownloads, self.btnSetDownloadDir):
            row.addWidget(b)
        la_v.addWidget(bar)

        # Quick open
        quick = QWidget(); qrow = QHBoxLayout(quick); qrow.setContentsMargins(0,0,0,0); qrow.setSpacing(8)
        self.quick = QLineEdit(); self.quick.setPlaceholderText("https://… (Sora 2 link)")
        self.quick.returnPressed.connect(self.load_quick)
        btn_open = QPushButton("Open"); btn_open.clicked.connect(self.load_quick)
        qrow.addWidget(self.quick,1); qrow.addWidget(btn_open,0)
        la_v.addWidget(quick)

        # Sites list (from user-sites JSON)
        self.user_sites = load_or_init_user_sites(self.cfg.get("sites", []))
        self.listw = QListWidget()
        self.refresh_sites_list()
        self.listw.itemClicked.connect(self.load_from_list)
        la_v.addWidget(self.listw,1)

        #info = QLabel("Source: User list")
        row_sites = QWidget(); row_sites_h = QHBoxLayout(row_sites); row_sites_h.setContentsMargins(0,0,0,0); row_sites_h.setSpacing(8)
        btnRestore = QPushButton("Restore Default Sites"); btnRestore.clicked.connect(self.restore_default_sites)
        #btnClearSites = QPushButton("Clear User Sites"); btnClearSites.clicked.connect(self.clear_user_sites)
        btnAddSite = QPushButton("Add Current Page"); btnAddSite.clicked.connect(self.add_site_from_current)
        btnRemoveSite = QPushButton("Remove Selected"); btnRemoveSite.clicked.connect(self.remove_selected_site)
        #row_sites_h.addWidget(info,1)
        for b in (btnRestore, btnAddSite, btnRemoveSite):
            row_sites_h.addWidget(b,0)
            
        # Keep Restore/Clear accessible via the Sites menu
        la_v.addWidget(row_sites)

        # Right Prompts Panel
        rightPrompts = QWidget(); rp_v = QVBoxLayout(rightPrompts)
        rp_v.setContentsMargins(8,0,0,0); rp_v.setSpacing(6)

        rp_header = QWidget()
        rp_row = QHBoxLayout(rp_header)
        rp_row.setContentsMargins(0, 0, 0, 0)
        rp_row.setSpacing(4)

        self.categoriesLabel = QLabel("Prompts:")
        self.categoriesLabel.setSizePolicy(QSizePolicy.Policy.Fixed,
                                           QSizePolicy.Policy.Preferred)
        rp_row.addWidget(self.categoriesLabel)

        self.categoryBox = QComboBox(); self.categoryBox.addItem("Show All")
        self.categoryBox.currentIndexChanged.connect(self.refresh_prompts_list)
        rp_row.addWidget(self.categoryBox)
        
        # Prompt sort toggle
        self.prompt_sort_mode = "original"
        self.btnPromptSort = QPushButton("Sort By Name")
        self.btnPromptSort.clicked.connect(self.toggle_prompt_sort)
        rp_row.addWidget(self.btnPromptSort)

        self.btnPromptCopy = QPushButton("Copy"); self.btnPromptCopy.clicked.connect(self.copy_selected_prompt)
        self.btnPromptAdd = QPushButton("Add"); self.btnPromptAdd.clicked.connect(self.add_prompt_dialog)
        self.btnPromptRemove = QPushButton("Remove"); self.btnPromptRemove.clicked.connect(self.remove_selected_prompt)
        self.btnPromptRestore = QPushButton("Restore Default Prompts"); self.btnPromptRestore.clicked.connect(self.restore_default_prompts)
        self.btnPromptExport = QPushButton("Export"); self.btnPromptExport.clicked.connect(self.export_prompts_dialog)
        self.btnPromptImport = QPushButton("Import"); self.btnPromptImport.clicked.connect(self.import_prompts_dialog)
        for b in (self.btnPromptCopy,self.btnPromptAdd,self.btnPromptRemove,self.btnPromptRestore,self.btnPromptExport,self.btnPromptImport):
            rp_row.addWidget(b, 0)
        rp_v.addWidget(rp_header, 0)

        self.user_prompts = load_or_init_user_prompts(self.cfg.get("prompts", []))
        self._manual_placeholder_cache = {}  # remembers manual "" values per prompt
        self._prompt_objs = _normalize_prompts_list(self.user_prompts)
        
        # Characters (with categories from config)
        cfg_chars_raw = self.cfg.get("characters", [])
        self.character_defs = _normalize_characters_cfg_list(cfg_chars_raw)
        default_char_names = [c.get("name", "") for c in self.character_defs]
        self.user_characters = load_or_init_user_characters(default_char_names)
        
        # Build merged character objects
        self._rebuild_character_objects()

        # Category + Character selectors
        characterRow = QHBoxLayout()
        characterRow.addWidget(QLabel("Characters:"))
        self.characterCategoryBox = QComboBox(); self.characterCategoryBox.addItem("Show All")
        self.characterCategoryBox.currentIndexChanged.connect(self._reload_character_boxes)
        characterRow.addWidget(self.characterCategoryBox)
        characterRow.addSpacing(12)

        #lblP1 = QLabel("Character 1:"); lblP1.setStyleSheet("font-size: 11px;")
        #characterRow.addWidget(lblP1)
        self.character1Box = QComboBox()
        self.character1Box.addItem("— None —")
        self.character1Box.addItems(self.user_characters)
        characterRow.addWidget(self.character1Box)
        characterRow.addSpacing(8)

        #lblP2 = QLabel("Character 2:"); lblP2.setStyleSheet("font-size: 11px;")
        #characterRow.addWidget(lblP2)
        self.character2Box = QComboBox()
        self.character2Box.addItem("— None —")
        self.character2Box.addItems(self.user_characters)
        characterRow.addWidget(self.character2Box)
        characterRow.addSpacing(8)

        #lblP3 = QLabel("Character 3:"); lblP3.setStyleSheet("font-size: 11px;")
        #characterRow.addWidget(lblP3)
        self.character3Box = QComboBox()
        self.character3Box.addItem("— None —")
        self.character3Box.addItems(self.user_characters)
        characterRow.addWidget(self.character3Box)
        characterRow.addSpacing(8)

        #lblP4 = QLabel("Character 4:"); lblP4.setStyleSheet("font-size: 11px;")
        #characterRow.addWidget(lblP4)
        self.character4Box = QComboBox()
        self.character4Box.addItem("— None —")
        self.character4Box.addItems(self.user_characters)
        characterRow.addWidget(self.character4Box)
        characterRow.addSpacing(8)
        self.keepNamesCheck = QCheckBox("Keep"); self.keepNamesCheck.setChecked(True)
        characterRow.addWidget(self.keepNamesCheck)
        rp_v.addLayout(characterRow)

        # Populate character category dropdown and boxes initially
        try:
            self._reload_character_boxes()
        except Exception:
            pass
        try:
            self.character1Box.setEditable(True); self.character2Box.setEditable(True)
            self.character3Box.setEditable(True); self.character4Box.setEditable(True)
            _c1 = QCompleter(self.user_characters, self.character1Box); _c1.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            _c2 = QCompleter(self.user_characters, self.character2Box); _c2.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            _c3 = QCompleter(self.user_characters, self.character3Box); _c3.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            _c4 = QCompleter(self.user_characters, self.character4Box); _c4.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.character1Box.setCompleter(_c1); self.character2Box.setCompleter(_c2)
            self.character3Box.setCompleter(_c3); self.character4Box.setCompleter(_c4)
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
            self.character3Box.currentIndexChanged.connect(lambda _: self.update_prompt_preview())
            self.character4Box.currentIndexChanged.connect(lambda _: self.update_prompt_preview())

        except Exception:
            pass
        self.refresh_prompts_list()
        try:
            self.update_prompt_preview()
        except Exception:
            pass

        # Add left/right panes to the actions splitter
        leftActions.setMinimumWidth(150)
        rightPrompts.setMinimumWidth(150)
        self.actionsSplit.addWidget(leftActions)
        self.actionsSplit.addWidget(rightPrompts)

        # Determine shared split sizes from config
        ui_cfg = (self.cfg.get("ui") or {})
        if not isinstance(ui_cfg, dict):
            ui_cfg = {}
        self.cfg["ui"] = ui_cfg

        # Hotkeys: fullscreen + zoom
        hotkeys = ui_cfg.get("hotkeys")
        if not isinstance(hotkeys, dict):
            hotkeys = {}
        if "fullscreen_left" not in hotkeys:
            hotkeys["fullscreen_left"] = "F1"
        if "fullscreen_right" not in hotkeys:
            hotkeys["fullscreen_right"] = "F2"
        if "zoom_left_in" not in hotkeys:
            hotkeys["zoom_left_in"] = "F3"
        if "zoom_left_out" not in hotkeys:
            hotkeys["zoom_left_out"] = "F4"
        if "zoom_left_reset" not in hotkeys:
            hotkeys["zoom_left_reset"] = "F5"
        if "zoom_right_in" not in hotkeys:
            hotkeys["zoom_right_in"] = "F6"
        if "zoom_right_out" not in hotkeys:
            hotkeys["zoom_right_out"] = "F7"
        if "zoom_right_reset" not in hotkeys:
            hotkeys["zoom_right_reset"] = "F8"
        ui_cfg["hotkeys"] = hotkeys

        # Pane zoom defaults (per pane)
        pane_zoom = ui_cfg.get("pane_zoom")
        if not isinstance(pane_zoom, dict):
            pane_zoom = {}
        try:
            self.left_zoom = float(pane_zoom.get("left", 1.0))
        except Exception:
            self.left_zoom = 1.0
        try:
            self.right_zoom = float(pane_zoom.get("right", 1.0))
        except Exception:
            self.right_zoom = 1.0
        pane_zoom["left"] = float(self.left_zoom)
        pane_zoom["right"] = float(self.right_zoom)
        ui_cfg["pane_zoom"] = pane_zoom

        # Pane fullscreen defaults (per pane)
        pane_fs = ui_cfg.get("pane_fullscreen")
        if not isinstance(pane_fs, dict):
            pane_fs = {}
        self.left_pane_fullscreen = bool(pane_fs.get("left", False))
        self.right_pane_fullscreen = bool(pane_fs.get("right", False))
        pane_fs["left"] = bool(self.left_pane_fullscreen)
        pane_fs["right"] = bool(self.right_pane_fullscreen)
        ui_cfg["pane_fullscreen"] = pane_fs

        # Download path (ui.download_path; default to ~/Downloads)
        download_path = ui_cfg.get("download_path")
        if not isinstance(download_path, str) or not download_path.strip():
            try:
                default_dl = pathlib.Path.home() / "Downloads"
            except Exception:
                default_dl = pathlib.Path.cwd()
            download_path = str(default_dl)
        self.download_path = download_path
        ui_cfg["download_path"] = self.download_path

        # link_splitters: True = keep actions/content splitters in sync (default); False = decouple
        self.link_splitters = bool(ui_cfg.get("link_splitters", True))

        # Apply configured hotkeys to fullscreen and zoom actions
        try:
            self.act_toggle_left_fs.setShortcut(hotkeys.get("fullscreen_left", "F1"))
            self.act_toggle_right_fs.setShortcut(hotkeys.get("fullscreen_right", "F2"))
            self.act_zoom_left_in.setShortcut(hotkeys.get("zoom_left_in", "F3"))
            self.act_zoom_left_out.setShortcut(hotkeys.get("zoom_left_out", "F4"))
            self.act_zoom_left_reset.setShortcut(hotkeys.get("zoom_left_reset", "F5"))
            self.act_zoom_right_in.setShortcut(hotkeys.get("zoom_right_in", "F6"))
            self.act_zoom_right_out.setShortcut(hotkeys.get("zoom_right_out", "F7"))
            self.act_zoom_right_reset.setShortcut(hotkeys.get("zoom_right_reset", "F8"))
        except Exception:
            pass

        # Initialize independent splitter sizes
        ui_cfg = (self.cfg.get("ui") or {})
        def _coerce_sizes(v, ratio_fallback=0.5):
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                try:
                    return [int(v[0]), int(v[1])]
                except Exception:
                    pass
            r = float(self.cfg.get("window", {}).get("pane_ratio", ratio_fallback))
            return [int(1000*r), int(1000*(1.0-r))]

        actions_sizes = _coerce_sizes(ui_cfg.get("actions_splitter_sizes"), 0.5)
        content_sizes = _coerce_sizes(ui_cfg.get("content_splitter_sizes"),
                                      actions_sizes[0]/1000.0)

        try:
            self.actionsSplit.setSizes(actions_sizes)
        except Exception:
            pass
        except Exception:
            pass

        # CONTENT splitter LEFT/RIGHT
        self.contentSplit = QSplitter(Qt.Orientation.Horizontal)
        
        # Left tabs
        self.leftTabs = QTabWidget(); self.leftTabs.setTabsClosable(True); self.leftTabs.setMovable(True)
        self.leftTabs.tabBar().setUsesScrollButtons(True)
        self.leftTabs.tabCloseRequested.connect(self.close_left_tab)
        self.leftTabs.currentChanged.connect(self.on_left_tab_changed)
        
        # Initial tab
        _b0 = Browser()
        self._connect_left_browser(_b0)
        try:
            _b0.setHtml(self.startup_html)
        except Exception:
            pass
        self.leftTabs.addTab(_b0, "New Tab")
        self.right = Browser()
        self.right.settings().setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
        self.right.setUrl(QUrl(self.cfg["window"].get("mail_url","https://www.guerrillamail.com/inbox")))

        self.contentSplit.addWidget(self.leftTabs); self.contentSplit.addWidget(self.right)
        self.contentSplit.setStretchFactor(0,1); self.contentSplit.setStretchFactor(1,1)
        try:
            self.contentSplit.setSizes(content_sizes)
        except Exception:
            pass

        # Add to root
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

        # Apply initial zoom + pane fullscreen state
        try:
            self.set_left_zoom(getattr(self, "left_zoom", 1.0))
        except Exception:
            pass
        try:
            self.set_right_zoom(getattr(self, "right_zoom", 1.0))
        except Exception:
            pass
        try:
            self._apply_pane_fullscreen_state()
        except Exception:
            pass

        self.statusBar().showMessage("Ready")

    # UA logic
    def set_user_agent(self, ua, preset_label=None):
        if ua is None or (isinstance(ua, str) and ua.startswith("Default")):
            self.current_ua = "Default (Engine)"
            try:
                # Empty string tells QtWebEngine to use its built-in default UA
                self.profile.setHttpUserAgent("")
            except Exception:
                pass
        else:
            self.current_ua = ua
            try:
                self.profile.setHttpUserAgent(ua)
            except Exception:
                pass

        if preset_label:
            try:
                self.uaPreset.setCurrentText(preset_label)
            except Exception:
                pass

        # Reload all left tabs and the right pane
        try:
            for i in range(self.leftTabs.count()):
                b = self.leftTabs.widget(i)
                if b.url().isValid():
                    b.reload()
        except Exception:
            pass
        try:
            if self.right.url().isValid():
                self.right.reload()
        except Exception:
            pass
    
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
        # Reload all tabs and right pane; relies on current UA/cookies
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
        # Store a flag
        self.aggressive_spoof = bool(checked)
        QMessageBox.information(self, "Aggressive Spoof", "Enabled" if checked else "Disabled")
    
    '''
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
    '''
    
    # Cookies
    def clear_recaptcha_cookies(self):
        self.profile.cookieStore().deleteAllCookies()
        br = self.current_browser()
        if br and br.url().isValid():
            br.reload()
        self.statusBar().showMessage("Cleared cookies; reloaded active tab.", 4000)
        

    def open_download_dir(self):
        path = pathlib.Path(getattr(self, "download_path", "") or (pathlib.Path.home() / "Downloads"))
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        except Exception:
            try:
                webbrowser.open(path.as_uri())
            except Exception:
                QMessageBox.warning(self, "Open Downloads", f"Download folder:\n{path}")

    def change_download_dir(self):
        start_dir = getattr(self, "download_path", "") or str(pathlib.Path.home() / "Downloads")
        dir_ = QFileDialog.getExistingDirectory(self, "Select Download Directory", start_dir)
        if not dir_:
            return
        self.download_path = dir_
        ui_cfg = self.cfg.get("ui") or {}
        if not isinstance(ui_cfg, dict):
            ui_cfg = {}
        self.cfg["ui"] = ui_cfg
        ui_cfg["download_path"] = self.download_path
        try:
            save_config(self.cfg)
            self.statusBar().showMessage(f"Download directory set to: {self.download_path}", 4000)
        except Exception:
            pass

    def on_download(self, item):
        base = getattr(self, "download_path", "") or str(pathlib.Path.home() / "Downloads")
        downloads = pathlib.Path(base)
        try:
            downloads.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
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

    # Splitter sync
    def _apply_split_sizes(self, sizes):
        # If link_splitters is False, do not propagate sizes between top/bottom splitters
        if not getattr(self, "link_splitters", True):
            return
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
        
    # Layout toggle
    def update_toggle_label(self):
        self.btnToggle.setText("Top/Bottom" if self.contentSplit.orientation()==Qt.Orientation.Horizontal else "Left/Right")

    def switch_orientation(self):
        ori = self.contentSplit.orientation()
        self.contentSplit.setOrientation(Qt.Orientation.Vertical if ori==Qt.Orientation.Horizontal else Qt.Orientation.Horizontal)
        self.contentSplit.setStretchFactor(0,1); self.contentSplit.setStretchFactor(1,1)
        self.contentSplit.setSizes([int(1000*self.cfg['window'].get('pane_ratio',0.5)),int(1000*(1.0-self.cfg['window'].get('pane_ratio',0.5)))])
        self.update_toggle_label()

    # Pane zoom helpers
    def set_left_zoom(self, value: float):
        try:
            z = float(value)
        except Exception:
            z = 1.0
        z = max(0.25, min(5.0, z))
        self.left_zoom = z
        try:
            for i in range(self.leftTabs.count()):
                w = self.leftTabs.widget(i)
                if isinstance(w, QWebEngineView):
                    w.setZoomFactor(z)
        except Exception:
            pass
        try:
            ui = self.cfg.setdefault("ui", {})
            pane_zoom = ui.get("pane_zoom")
            if not isinstance(pane_zoom, dict):
                pane_zoom = {}
            pane_zoom["left"] = float(z)
            ui["pane_zoom"] = pane_zoom
        except Exception:
            pass

    def change_left_zoom(self, delta: float):
        self.set_left_zoom(getattr(self, "left_zoom", 1.0) + float(delta))

    def set_right_zoom(self, value: float):
        try:
            z = float(value)
        except Exception:
            z = 1.0
        z = max(0.25, min(5.0, z))
        self.right_zoom = z
        try:
            if hasattr(self, "right") and isinstance(self.right, QWebEngineView):
                self.right.setZoomFactor(z)
        except Exception:
            pass
        try:
            ui = self.cfg.setdefault("ui", {})
            pane_zoom = ui.get("pane_zoom")
            if not isinstance(pane_zoom, dict):
                pane_zoom = {}
            pane_zoom["right"] = float(z)
            ui["pane_zoom"] = pane_zoom
        except Exception:
            pass

    def change_right_zoom(self, delta: float):
        self.set_right_zoom(getattr(self, "right_zoom", 1.0) + float(delta))

    # Pane fullscreen helpers
    def _apply_pane_fullscreen_state(self):
        try:
            left_fs = bool(getattr(self, "left_pane_fullscreen", False))
            right_fs = bool(getattr(self, "right_pane_fullscreen", False))
        except Exception:
            left_fs = right_fs = False

        # If both are True, normalize to both off
        if left_fs and right_fs:
            left_fs = right_fs = False
            try:
                ui = self.cfg.setdefault("ui", {})
                pane_fs = ui.get("pane_fullscreen")
                if not isinstance(pane_fs, dict):
                    pane_fs = {}
                pane_fs["left"] = False
                pane_fs["right"] = False
                ui["pane_fullscreen"] = pane_fs
            except Exception:
                pass
            self.left_pane_fullscreen = False
            self.right_pane_fullscreen = False

        try:
            if left_fs and not right_fs:
                if hasattr(self, "leftTabs"):
                    self.leftTabs.show()
                if hasattr(self, "right"):
                    self.right.hide()
            elif right_fs and not left_fs:
                if hasattr(self, "leftTabs"):
                    self.leftTabs.hide()
                if hasattr(self, "right"):
                    self.right.show()
            else:
                if hasattr(self, "leftTabs"):
                    self.leftTabs.show()
                if hasattr(self, "right"):
                    self.right.show()
        except Exception:
            pass

    def _update_pane_fullscreen_cfg(self):
        try:
            ui = self.cfg.setdefault("ui", {})
            pane_fs = ui.get("pane_fullscreen")
            if not isinstance(pane_fs, dict):
                pane_fs = {}
            pane_fs["left"] = bool(getattr(self, "left_pane_fullscreen", False))
            pane_fs["right"] = bool(getattr(self, "right_pane_fullscreen", False))
            ui["pane_fullscreen"] = pane_fs
        except Exception:
            pass

    def toggle_left_pane_fullscreen(self):
        left_fs = bool(getattr(self, "left_pane_fullscreen", False))
        right_fs = bool(getattr(self, "right_pane_fullscreen", False))
        if left_fs:
            # turn off -> normal
            self.left_pane_fullscreen = False
        else:
            # enable left, disable right
            self.left_pane_fullscreen = True
            self.right_pane_fullscreen = False
        self._update_pane_fullscreen_cfg()
        self._apply_pane_fullscreen_state()

    def toggle_right_pane_fullscreen(self):
        left_fs = bool(getattr(self, "left_pane_fullscreen", False))
        right_fs = bool(getattr(self, "right_pane_fullscreen", False))
        if right_fs:
            self.right_pane_fullscreen = False
        else:
            self.right_pane_fullscreen = True
            self.left_pane_fullscreen = False
        self._update_pane_fullscreen_cfg()
        self._apply_pane_fullscreen_state()

    # Left tabs helpers
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
            # Keep at least one tab
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


    def _normalize_url_text(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            return ""
        try:
            qurl = QUrl.fromUserInput(text)
        except Exception:
            return ""
        if not qurl.isValid() or qurl.isEmpty():
            return ""
        return qurl.toString()

    def open_url_in_new_tab(self, url: str):
        url = self._normalize_url_text(url)
        if not url:
            return
        br = Browser()
        self._connect_left_browser(br)
        try:
            br.setZoomFactor(getattr(self, "left_zoom", 1.0))
        except Exception:
            pass
        idx = self.leftTabs.addTab(br, "…")
        self.leftTabs.setCurrentIndex(idx)
        br.setUrl(QUrl(url))
        self.addr.setText(url)

    # Navigation helpers
    def open_external(self):
        br = self.current_browser()
        url = br.url().toString() if (br and br.url().isValid()) else self.addr.text().strip()
        if url:
            webbrowser.open(url)

    def open_private(self):
        br = self.current_browser()
        url = br.url().toString() if (br and br.url().isValid()) else self.addr.text().strip()
        url = self._normalize_url_text(url)
        if not url:
            return

        if sys.platform.startswith("win"):
            # Try common Windows browsers with private/incognito flags
            url_arg = url  # keep raw URL for browser
            # Potential Edge install locations
            edge_paths = []
            for env_name in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
                base = os.environ.get(env_name)
                if base:
                    edge_paths.append(os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"))

            # Try specific Edge paths first
            candidates = [(p, ["-inprivate", url_arg]) for p in edge_paths]
            # Then fall back to generic exe names for Edge/Chrome/Firefox
            candidates.extend([
                ("msedge.exe", ["-inprivate", url_arg]),
                ("chrome.exe", ["--incognito", url_arg]),
                ("firefox.exe", ["-private-window", url_arg]),
            ])

            for exe, args in candidates:
                try:
                    result = QProcess.startDetached(exe, args)
                    ok = bool(result[0]) if isinstance(result, tuple) else bool(result)
                except Exception:
                    ok = False
                if ok:
                    return

        # Fallback: normal external open if private/incognito couldn't be launched
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
        u = self._normalize_url_text(self.addr.text())
        br = self.current_browser()
        if u and br:
            br.setUrl(QUrl(u))
            self.addr.setText(u)
            
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
        
        # Reindex IDs
        for i, s in enumerate(self.user_sites, start=1): s["id"] = i
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

    # Mail sites helpers
    def _build_mail_sites_menu(self, menu):
        try:
            menu.clear()
        except Exception:
            return
        a_restore = menu.addAction("Restore Default Mail Sites")
        a_restore.triggered.connect(self.restore_default_mail_sites)
        a_clear = menu.addAction("Clear User Mail Sites")
        a_clear.triggered.connect(self.clear_user_mail_sites)
        wa = QWidgetAction(menu)
        edit = QLineEdit(menu)
        edit.setPlaceholderText("https://… (custom mail site)")
        edit.returnPressed.connect(lambda e=edit: self._custom_mail_site_entered(e))
        wa.setDefaultWidget(edit)
        menu.addAction(wa)
        default_url = self.cfg.get("window", {}).get("mail_url", "https://www.guerrillamail.com/inbox")
        a_default = menu.addAction("Default (current)")
        a_default.triggered.connect(lambda _, u=default_url: self.open_mail_site(u))
        for url in self.user_mail_sites:
            if not url:
                continue
            act = menu.addAction(str(url))
            act.triggered.connect(lambda _, u=url: self.open_mail_site(u))
        menu.addSeparator()
        a_export = menu.addAction("Export...")
        a_export.triggered.connect(self.export_mail_sites_dialog)
        a_import = menu.addAction("Import...")
        a_import.triggered.connect(self.import_mail_sites_dialog)

    def open_mail_site(self, url):
        url = (url or "").strip()
        if not url:
            return
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', url):
            url = "https://" + url
        try:
            self.right.setUrl(QUrl(url))
        except Exception:
            return
        try:
            self.cfg.setdefault("window", {})["mail_url"] = url
        except Exception:
            pass

    def _custom_mail_site_entered(self, edit):
        try:
            url = (edit.text() or "").strip()
        except Exception:
            url = ""
        if not url:
            return
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', url):
            url = "https://" + url
        if url not in self.user_mail_sites:
            self.user_mail_sites.append(url)
            save_user_mail_sites(self.user_mail_sites)
        try:
            edit.clear()
        except Exception:
            pass
        try:
            if hasattr(self, "m_mail_sites") and self.m_mail_sites is not None:
                self._build_mail_sites_menu(self.m_mail_sites)
        except Exception:
            pass
        self.open_mail_site(url)

    def restore_default_mail_sites(self):
        if QMessageBox.question(
            self,
            "Restore Default Mail Sites",
            "Replace your mail sites with the built-in defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        defaults = self.cfg.get("mail_sites", MAIL_SITE_DEFAULTS)
        self.user_mail_sites = list(defaults)
        if save_user_mail_sites(self.user_mail_sites):
            try:
                if hasattr(self, "m_mail_sites") and self.m_mail_sites is not None:
                    self._build_mail_sites_menu(self.m_mail_sites)
            except Exception:
                pass
            self.statusBar().showMessage("Restored default mail sites.", 4000)

    def clear_user_mail_sites(self):
        if QMessageBox.question(
            self,
            "Clear User Mail Sites",
            "Remove ALL user mail sites? This does not touch the built-in default entry. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        self.user_mail_sites = []
        if save_user_mail_sites(self.user_mail_sites):
            try:
                if hasattr(self, "m_mail_sites") and self.m_mail_sites is not None:
                    self._build_mail_sites_menu(self.m_mail_sites)
            except Exception:
                pass
            self.statusBar().showMessage("Cleared user mail sites.", 4000)

    def export_mail_sites_dialog(self):
        try:
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Mail Sites",
                "sora2_user_mail_sites_export.json",
                "JSON Files (*.json)",
            )
            if not path:
                return
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"mail_sites": self.user_mail_sites}, f, indent=2)
            self.statusBar().showMessage(f"Exported mail sites to {path}", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    def import_mail_sites_dialog(self):
        try:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Import Mail Sites",
                "",
                "JSON Files (*.json)",
            )
            if not path:
                return
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                sites = data.get("mail_sites", [])
            elif isinstance(data, list):
                sites = data
            else:
                sites = []
            if not isinstance(sites, list):
                QMessageBox.warning(self, "Import Mail Sites", "Invalid format. Expecting an object with a 'mail_sites' array.")
                return
            cleaned = []
            for u in sites:
                if not isinstance(u, str):
                    continue
                u = u.strip()
                if not u:
                    continue
                if not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', u):
                    u = "https://" + u
                if u not in cleaned:
                    cleaned.append(u)
            self.user_mail_sites = cleaned
            save_user_mail_sites(self.user_mail_sites)
            try:
                if hasattr(self, "m_mail_sites") and self.m_mail_sites is not None:
                    self._build_mail_sites_menu(self.m_mail_sites)
            except Exception:
                pass
            self.statusBar().showMessage(f"Imported mail sites from {path}", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Import Error", str(e))

    # Prompts helpers
    def toggle_prompt_sort(self):
        # Cycle prompt sort mode: original -> name -> category -> original
        mode = getattr(self, "prompt_sort_mode", "original")

        if mode == "original":
            # Next: sort by name
            self.prompt_sort_mode = "name"
            try:
                self.btnPromptSort.setText("Sort By Category")
            except Exception:
                pass
        elif mode == "name":
            # Next: sort by category
            self.prompt_sort_mode = "category"
            try:
                self.btnPromptSort.setText("Sort By Original")
            except Exception:
                pass
        else:
            # Currently category -> next: back to original JSON order
            self.prompt_sort_mode = "original"
            try:
                self.btnPromptSort.setText("Sort By Name")
            except Exception:
                pass

        # Rebuild list with new sort
        self.refresh_prompts_list()

    def refresh_prompts_list(self):
        self.promptList.clear()
        
        # Normalize merged prompts list (supports string or object items)
        self._prompt_objs = _normalize_prompts_list(self.user_prompts)

        # Apply current sort mode
        mode = getattr(self, "prompt_sort_mode", "original")
        objs = list(self._prompt_objs)

        if mode == "category":
            # Group by category, then by title
            objs.sort(
                key=lambda o: (
                    (o.get("category") or "Base").casefold(),
                    (o.get("title") or "").casefold(),
                )
            )
        elif mode == "name":
            # Sort primarily by title, then category
            objs.sort(
                key=lambda o: (
                    (o.get("title") or "").casefold(),
                    (o.get("category") or "Base").casefold(),
                )
            )
        # else: "original" -> keep JSON order as loaded (no sort)

        self._prompt_objs = objs

        # Rebuild categories (keep selection)
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
            # When sorting by name, hide category in the list label
            if mode == "name":
                display_text = title
            else:
                display_text = f"{cat} · {title}"
            it = QListWidgetItem(display_text)
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
        p3 = self.character3Box.currentText() if hasattr(self, "character3Box") and self.character3Box.currentIndex() > 0 else ""
        p4 = self.character4Box.currentText() if hasattr(self, "character4Box") and self.character4Box.currentIndex() > 0 else ""
        if hasattr(self, "keepNamesCheck") and not self.keepNamesCheck.isChecked():
            p1 = ""; p2 = ""; p3 = ""; p4 = ""
        txt = replace_once(base_text, p1)
        txt = replace_once(txt, p2)
        txt = replace_once(txt, p3)
        txt = replace_once(txt, p4)

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

        # Apply Character 1–4 to the first slots
        try:
            p1 = self.character1Box.currentText() if hasattr(self, "character1Box") and self.character1Box.currentIndex() > 0 else ''
        except Exception:
            p1 = ''
        try:
            p2 = self.character2Box.currentText() if hasattr(self, "character2Box") and self.character2Box.currentIndex() > 0 else ''
        except Exception:
            p2 = ''
        try:
            p3 = self.character3Box.currentText() if hasattr(self, "character3Box") and self.character3Box.currentIndex() > 0 else ''
        except Exception:
            p3 = ''
        try:
            p4 = self.character4Box.currentText() if hasattr(self, "character4Box") and self.character4Box.currentIndex() > 0 else ''
        except Exception:
            p4 = ''
        for _val in (p1, p2, p3, p4):
            text = replace_once(text, _val)

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

        # Clear any cached placeholders for this prompt
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
        # Reselect edited prompt in the list
        for i in range(self.promptList.count()):
            it = self.promptList.item(i)
            o = it.data(Qt.ItemDataRole.UserRole)
            if isinstance(o, dict):
                if pid and o.get('id') == pid:
                    self.promptList.setCurrentItem(it)
                    return
                if text and o.get('text') == text:
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
        # Prompts splitter
        try:
            p_sizes = self.promptsSplitter.sizes()
        except Exception:
            p_sizes = None

        # Horizontal actions/content splitters
        try:
            a_sizes = self.actionsSplit.sizes()
        except Exception:
            a_sizes = None
        try:
            c_sizes = self.contentSplit.sizes()
        except Exception:
            c_sizes = None

        # Update in-memory cfg.ui
        ui = self.cfg.get("ui")
        if not isinstance(ui, dict):
            ui = {}
            self.cfg["ui"] = ui
        # persist link_splitters flag into in-memory ui config
        ui["link_splitters"] = bool(getattr(self, "link_splitters", True))
        if p_sizes:
            ui["prompts_splitter_sizes"] = [int(s) for s in p_sizes]
        if a_sizes:
            ui["actions_splitter_sizes"] = [int(s) for s in a_sizes]
        if c_sizes:
            ui["content_splitter_sizes"] = [int(s) for s in c_sizes]

        # Update pane_ratio
        try:
            if a_sizes and len(a_sizes) >= 2:
                total = float(a_sizes[0] + a_sizes[1])
                if total > 0:
                    self.cfg.setdefault("window", {})
                    self.cfg["window"]["pane_ratio"] = float(a_sizes[0]) / total
        except Exception:
            pass

        # Merge back into JSON on disk
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
        except Exception:
            data = {}
        if not isinstance(data.get("ui"), dict):
            data["ui"] = {}
        # persist link_splitters flag into JSON ui section
        data["ui"]["link_splitters"] = bool(getattr(self, "link_splitters", True))
        if p_sizes:
            data["ui"]["prompts_splitter_sizes"] = [int(s) for s in p_sizes]
        if a_sizes:
            data["ui"]["actions_splitter_sizes"] = [int(s) for s in a_sizes]
        if c_sizes:
            data["ui"]["content_splitter_sizes"] = [int(s) for s in c_sizes]

        # Keep window.pane_ratio in sync if present
        try:
            if "window" not in data or not isinstance(data["window"], dict):
                data["window"] = self.cfg.get("window", {})
            else:
                if "pane_ratio" in self.cfg.get("window", {}):
                    data["window"]["pane_ratio"] = self.cfg["window"]["pane_ratio"]
        except Exception:
            pass

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def export_view_toolbar_dialog(self):
        try:
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Export View Toolbar Settings",
                "sora2_view_toolbar_export.json",
                "JSON Files (*.json)",
            )
            if not path:
                return
            ui_cfg = self.cfg.get("ui") or {}
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"ui": ui_cfg}, f, indent=2, ensure_ascii=False)
            self.statusBar().showMessage(f"Exported view toolbar settings to {path}", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    def import_view_toolbar_dialog(self):
        try:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Import View Toolbar Settings",
                "",
                "JSON Files (*.json)",
            )
            if not path:
                return
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            ui_cfg = data.get("ui")
            if not isinstance(ui_cfg, dict):
                QMessageBox.warning(self, "Import Error", "Invalid format. Expecting an object with a 'ui' object.")
                return
            self.cfg["ui"] = ui_cfg

            # Re-apply pane zoom
            pane_zoom = ui_cfg.get("pane_zoom") or {}
            if isinstance(pane_zoom, dict):
                try:
                    self.set_left_zoom(float(pane_zoom.get("left", getattr(self, "left_zoom", 1.0))))
                except Exception:
                    pass
                try:
                    self.set_right_zoom(float(pane_zoom.get("right", getattr(self, "right_zoom", 1.0))))
                except Exception:
                    pass

            # Re-apply pane fullscreen
            pane_fs = ui_cfg.get("pane_fullscreen") or {}
            if isinstance(pane_fs, dict):
                self.left_pane_fullscreen = bool(pane_fs.get("left", False))
                self.right_pane_fullscreen = bool(pane_fs.get("right", False))
                try:
                    self._apply_pane_fullscreen_state()
                except Exception:
                    pass

            # Re-apply hotkeys
            hotkeys = ui_cfg.get("hotkeys") or {}
            if isinstance(hotkeys, dict):
                try:
                    self.act_toggle_left_fs.setShortcut(hotkeys.get("fullscreen_left", "F1"))
                    self.act_toggle_right_fs.setShortcut(hotkeys.get("fullscreen_right", "F2"))
                    self.act_zoom_left_in.setShortcut(hotkeys.get("zoom_left_in", "F3"))
                    self.act_zoom_left_out.setShortcut(hotkeys.get("zoom_left_out", "F4"))
                    self.act_zoom_left_reset.setShortcut(hotkeys.get("zoom_left_reset", "F5"))
                    self.act_zoom_right_in.setShortcut(hotkeys.get("zoom_right_in", "F6"))
                    self.act_zoom_right_out.setShortcut(hotkeys.get("zoom_right_out", "F7"))
                    self.act_zoom_right_reset.setShortcut(hotkeys.get("zoom_right_reset", "F8"))
                except Exception:
                    pass

            self.statusBar().showMessage(f"Imported view toolbar settings from {path}", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Import Error", str(e))

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

    def _rebuild_character_objects(self):
        """Rebuild internal character objects (name + category) from config + user list."""
        defs = getattr(self, "character_defs", []) or []
        # Map config names (casefolded) to category
        lut = {}
        for o in defs:
            name = (o.get("name") or "").strip()
            if not name:
                continue
            key = name.casefold()
            if key not in lut:
                lut[key] = {"name": name, "category": (o.get("category") or "Base")}
        objs = []
        seen = set()
        for raw in getattr(self, "user_characters", []) or []:
            name = (" ".join(str(raw).split())).strip()
            if not name:
                continue
            key = name.casefold()
            if key in seen:
                continue
            seen.add(key)
            base = lut.get(key)
            if base:
                objs.append({"name": base["name"], "category": base.get("category") or "Base"})
            else:
                objs.append({"name": name, "category": "Base"})
        self._character_objs = objs

    def _reload_character_boxes(self):
        p1 = self.character1Box.currentText() if self.character1Box.currentIndex() > 0 else None
        p2 = self.character2Box.currentText() if self.character2Box.currentIndex() > 0 else None
        p3 = self.character3Box.currentText() if self.character3Box.currentIndex() > 0 else None
        p4 = self.character4Box.currentText() if self.character4Box.currentIndex() > 0 else None

        # Ensure character objects are up to date
        try:
            self._rebuild_character_objects()
        except Exception:
            self._character_objs = []

        objs = getattr(self, "_character_objs", []) or []

        # Update character category combo
        selected_cat = "Show All"
        if hasattr(self, "characterCategoryBox"):
            cur = self.characterCategoryBox.currentText() if self.characterCategoryBox.currentIndex() >= 0 else "Show All"
            cats = _extract_categories(objs)
            self.characterCategoryBox.blockSignals(True)
            self.characterCategoryBox.clear()
            self.characterCategoryBox.addItem("Show All")
            for c in cats:
                self.characterCategoryBox.addItem(c)
            idx = self.characterCategoryBox.findText(cur)
            self.characterCategoryBox.setCurrentIndex(idx if idx >= 0 else 0)
            self.characterCategoryBox.blockSignals(False)
            selected_cat = self.characterCategoryBox.currentText() or "Show All"

        # Build visible names based on selected category
        if selected_cat != "Show All":
            names = [o.get("name", "") for o in objs if (o.get("category") or "Base") == selected_cat]
        else:
            names = [o.get("name", "") for o in objs]
        names = [n for n in names if n]

        # Repopulate combo boxes
        for box in (self.character1Box, self.character2Box, self.character3Box, self.character4Box):
            box.blockSignals(True)
            box.clear()
            box.addItem("— None —")
            for name in names:
                box.addItem(name)
            box.blockSignals(False)

        if p1 and p1 in names:
            self.character1Box.setCurrentText(p1)
        else:
            self.character1Box.setCurrentIndex(0)
        if p2 and p2 in names:
            self.character2Box.setCurrentText(p2)
        else:
            self.character2Box.setCurrentIndex(0)
        if p3 and p3 in names:
            self.character3Box.setCurrentText(p3)
        else:
            self.character3Box.setCurrentIndex(0)
        if p4 and p4 in names:
            self.character4Box.setCurrentText(p4)
        else:
            self.character4Box.setCurrentIndex(0)

    # Persist window + orientation + UA on close
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
        # At startup, apply updates only if BOTH .tmp files exist; otherwise discard and warn.

        base_dir = os.path.dirname(os.path.abspath(__file__))
        py_name  = "sora2-browser-tool.py"
        py_dst   = os.path.join(base_dir, py_name)
        json_dst = os.path.join(base_dir, "sora2_config.json")
        py_tmp   = os.path.join(base_dir, py_name + '.tmp')
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
            
        # Force helper to finish update on exit
        try:
            tmp_dir = tempfile.gettempdir()
            helper_path = os.path.join(tmp_dir, "sora2_apply_update.py")
            with open(helper_path, "w", encoding="utf-8") as f:
                f.write(helper_code)
            try:
                QProcess.startDetached(sys.executable, [helper_path])
            except Exception:
                import subprocess
                try:
                    subprocess.Popen([sys.executable, helper_path],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
                except Exception:
                    pass
        except Exception:
            pass
            
        # Exit so helper can apply update
        try:
            sys.exit(0)
        except Exception:
            pass


        # If replacing PY fails, write a helper that will finish after app exits
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
        # Clear all site data (cookies, cache, local/session storage, indexedDB) and reload views.
        import shutil

        confirm = QMessageBox.question(
            self, "Clear Site Data",
            "This will clear cookies, cache, local/session storage, IndexedDB, service workers, and auth cache for all sites. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        # Cookies
        try:
            store = self.profile.cookieStore()
            if store is not None:
                store.deleteAllCookies()
        except Exception:
            pass

        # HTTP Cache
        try:
            self.profile.clearHttpCache()
        except Exception:
            pass

        # HTTP AUTH Cache/Login Sessions
        try:
            self.profile.clearHttpAuthenticationCache()
        except Exception:
            pass

        # Service Workers
        try:
            self.profile.clearAllServiceWorkers()
        except Exception:
            pass

        # Persistent Storage (LocalStorage, IndexedDB files, etc)
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

        # JS Clear (session/local storage + IndexedDB deleteDatabase())
        js = """
        (async function(){
            try {
                localStorage.clear();
                sessionStorage.clear();
                if (window.indexedDB && indexedDB.databases) {
                    let dbs = await indexedDB.databases();
                    for (const db of dbs) {
                        if (db && db.name) {
                            try { indexedDB.deleteDatabase(db.name); } catch(e){}
                        }
                    }
                }
            } catch(e){}
        })();
        """

        try:
            for view in self.findChildren(QWebEngineView):
                try:
                    view.page().runJavaScript(js)
                except Exception:
                    pass
        except Exception:
            pass

        # Done
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
        # Check GitHub JSON for a newer version; if present, download .tmp files into script dir.
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
