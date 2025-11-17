# Sora 2 Browser Tool

A split‑screen desktop browser UI for exploring free Sora 2 AI prompt sites on the left while using a disposable email inbox on the right.  
Everything is driven by simple JSON files so you can customize and back up your own sites, characters, and prompts.

<img src="https://i.imgur.com/tmBb8iQ.png" alt="Sora2 Browser Tool">

---

## Main Features

### 1. Split‑screen Sora 2 browser

- **Left pane – Sora 2 sites**
  - Browse a curated list of 100+ Sora 2 (and related) AI prompt sites.
  - Quickly switch sites using the **Sites** list on the left.
  - Add your own sites at runtime and save them into the user JSON.
  - Remove sites you don’t use, or restore the full default list at any time.

- **Right pane – Disposable mail**
  - Built‑in disposable email window for handling verification codes and sign‑ups.
  - Switch between different mail providers via **Switch Email Site** in the menubar.
  - Mail sites are also configurable via JSON, so you can point to any web‑mail style page you prefer.

- **Open in external browser**
  - One‑click buttons and **File → Open Externally / Open Media…** actions to send the current page or media URL to your system browser / media handler.

---

### 2. Prompt builder, characters, and live preview

- **Prompt list**
  - Right side of the top area shows a list of prompts grouped by scenario/category.
  - You can add, remove, import, export, and restore default prompts from the **Prompts** menu.
  - Prompts are stored in JSON in a structured format so they can be edited by hand if needed.

- **4 customizable characters**
  - Up to four character slots with dropdowns for common presets plus free‑text entry.
  - Character sets are managed via the **Characters** menu:
    - Restore default characters
    - Clear only user‑added characters
    - Import / export full character lists

- **Live prompt preview panel**
  - A dedicated preview pane shows the **final prompt text** with your selected characters applied.
  - The app automatically fills `""` placeholders with your chosen characters (Character 1–4) and any manual text.
  - As you change the selected prompt or tweak characters, the preview updates in real time.

- **Right‑click editing**
  - Prompts in the list support right‑click actions to quickly duplicate, edit, or remove entries without touching the JSON by hand.

---

### 3. Site, prompt, and character management (JSON‑backed)

All core data lives in simple JSON files so you can:
- **Customize**: Add your own Sora 2 sites, email sites, characters, and prompts.
- **Backup / sync**: Copy the JSON file between machines or commit it to git.
- **Recover**: Menubar options let you restore default data separately for:
  - Sites
  - Mail sites
  - Prompts
  - Characters

Import/export menus exist for prompts and characters, so you can share setups without touching the main config.

---

### 4. User‑Agent controls & captcha helpers

- **User‑Agent (UA) presets**
  - UA dropdown in the toolbar plus a **Tools → User Agent** submenu to:
    - Pick from named presets (Chrome, Firefox, Mobile, etc.).
    - Apply the current UA to the active Sora 2 browser.
  - A **Custom UA** field lets you paste any UA string you want.

- **UA actions**
  - **Apply UA (from fields)** – apply whatever is in the UA inputs.
  - **Random UA** – pick a random UA from the presets.
  - **Reset UA** – go back to the default engine UA.
  - **Try Mobile WebM** – switch to a mobile‑style UA that can help with some Sora sites.

- **Captcha helpers**
  - **Clear reCAPTCHA Cookies** – clears cookies and reloads the current page.
  - **Fix Captcha (Cloudflare)** – helper action specifically aimed at stubborn CF captcha flows.
  - **Aggressive Spoof** toggle – optional, extra UA spoofing behavior for trouble sites.

> Note: UA tricks can sometimes help, but they can also **break** captchas or logins. If something stops working, try resetting the UA or turning off aggressive spoofing.

---

### 5. Layout, zoom, and hotkeys

- **Flexible layout**
  - Three splitter levels:
    - **Root**: top (actions/prompts) vs bottom (browser/mail).
    - **Actions splitter**: left (URL & UA controls + sites) vs right (prompts + preview).
    - **Content splitter**: left (Sora site browser) vs right (mail panel).
  - All splitter positions are **remembered** when you exit and stored in `sora2_config.json` under `ui`.

- **View controls (View menu)**
  - **Switch Top/Bottom** – swap the actions area with the browser/mail area.
  - **Swap Left/Right** – swap Sora site pane and mail pane.
  - **Toggle Sites Pane Fullscreen** – focus only on the Sora site pane.
  - **Toggle Mail Pane Fullscreen** – focus only on the mail pane.

- **Per‑pane zoom**
  - Independent zoom controls for left (sites) and right (mail) panes.
  - View menu provides:
    - Zoom In / Zoom Out / Reset for each pane.

- **Hotkeys (configurable)**  
  Default keybindings (stored in `ui.hotkeys`):
  - `F1` – Toggle sites pane fullscreen  
  - `F2` – Toggle mail pane fullscreen  
  - `F3` – Zoom in (sites pane)  
  - `F4` – Zoom out (sites pane)  
  - `F5` – Reset zoom (sites pane)  
  - `F6` – Zoom in (mail pane)  
  - `F7` – Zoom out (mail pane)  
  - `F8` – Reset zoom (mail pane)

You can change these in `sora2_config.json` if you want different keys.

---

### 6. Downloads and download directory

- **Automatic download handling**
  - When a file is downloaded via the built‑in browser, it is saved into a configurable download folder.
  - The suggested filename is normalized based on URL and MIME type (e.g. `.mp4` for video, etc.).

- **Download directory control**
  - **Open Downloads** toolbar button: opens the current download folder in your OS file manager.
  - **Set Download Dir** toolbar button: choose a new download folder using a standard directory picker.
  - The selected path is stored as `ui.download_path` in `sora2_config.json` and reused next launch.
  - If `ui.download_path` is empty or invalid, the app falls back to your `~/Downloads` folder.

---

### 7. Clear Site Data & update checker

- **Clear Site Data**
  - Global action in the menubar that:
    - Clears cookies, cache, local/session storage, and IndexedDB for all sites.
    - Asks for confirmation before doing anything, then reloads views.
  - Useful when a site gets into a bad state or you want a clean slate for testing.

- **Check For Updates**
  - Menu action that checks the GitHub repo for a newer version.
  - Compares the local version against the remote JSON.
  - If a newer version is found, downloads `.tmp` copies of the updated files into the script directory so you can review/replace them.

---

### 8. Config files and persistence

The tool keeps almost everything in a single config JSON:

- **`sora2_config.json`**
  - `version` – current version string.
  - `window` – size and position of the main window.
  - `ui`:
    - Splitter sizes for prompts/actions/content panes.
    - `link_splitters` flag to keep or decouple related splitters.
    - Hotkey mappings for fullscreen and zoom.
    - Pane zoom levels and fullscreen state.
    - `download_path` for the download folder.
  - Default and user‑custom data for:
    - Site list(s)
    - Mail sites
    - Prompts
    - Characters

The Python script auto‑creates user‑data files and keeps them separate from core defaults so you can restore only what you want (sites, prompts, characters, etc.) without blowing away everything.

---

## Requirements & running

- **Python 3.x** (3.10+ recommended).
- **PyQt6** and **PyQt6‑WebEngine**.  
  The script includes a small bootstrap that will attempt to install these with `pip` on first run if they are missing.

Run it from a terminal or double‑click, for example:

```bash
python sora2-browser-tool.py
```

On first launch it will create/refresh `sora2_config.json` and any needed user data files in the same directory as the script.

---

## Notes

- This tool is designed specifically around **Sora 2** prompt workflows but is generic enough to use with other web‑based prompt builders or AI tools.
- All data is stored locally in JSON; there is no cloud sync or telemetry in the script itself.
