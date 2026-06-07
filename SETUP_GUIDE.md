# 🎬 Video Downloader — Setup Guide

## ⚡ The whole setup, in one step

> **Double-click `start.py`.**
> That's it. Really.

The first time you run it, it will:
1. Auto-install the few Python packages it needs (`flask`, `flask-cors`, `yt-dlp`)
2. Start the local server
3. Open the app in your default browser

After that, paste a link and click **Download**. You're done.

---

## ✅ Prerequisites (one-time, ~2 minutes)

You only need two things installed on your machine:

### 1. Python 3.8 or newer
- **Windows:** install from [python.org/downloads](https://www.python.org/downloads/) — **tick "Add Python to PATH"** during install.
- **macOS:** `brew install python` (or download from python.org).
- **Linux:** Python is usually preinstalled. Otherwise `sudo apt install python3 python3-pip`.

Verify:
```bash
python --version     # or: python3 --version
```

### 2. FFmpeg (only needed for high-resolution videos and MP3 audio)
FFmpeg is used to merge video+audio streams (anything above 720p on YouTube ships them separately) and to convert audio to MP3.

- **Windows:** `winget install ffmpeg` *(or download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH)*
- **macOS:** `brew install ffmpeg`
- **Linux:** `sudo apt install ffmpeg`

> Skipping FFmpeg? The app still works for single-stream videos (e.g. 720p and below) and original-format audio, but high-res downloads will fail.

---

## 🚀 Running the app

### Option A — Double-click (easiest)
- **Windows:** double-click `start.py`. If Windows asks "How do you want to open this file?", pick **Python**.
- **macOS / Linux:** right-click `start.py` → *Open With* → Python launcher. *(Or run from terminal: `python3 start.py`.)*

### Option B — From a terminal
```bash
cd path/to/this/folder
python start.py
```

A browser tab opens automatically at `http://localhost:5000`.

To stop the app: close the terminal window, or press `Ctrl + C`.

---

## 🎯 Using the app

1. **Copy a video link** (YouTube, Vimeo, TikTok, Instagram, Twitter/X, Facebook, and 1000+ other sites supported by yt-dlp).
2. **Switch to the app tab** — the link auto-pastes from your clipboard.
3. Click **Download** to inspect formats, or just hit **Download Best Quality** for the one-click route.
4. Watch the progress bar. When it's done, the file lands in your browser's Downloads folder.

---

## 🛠 Troubleshooting

| Problem | Fix |
|---|---|
| `python` isn't recognized | Reinstall Python with the **"Add to PATH"** option ticked. |
| "Could not auto-install dependencies" | Run manually: `pip install flask flask-cors yt-dlp` |
| 1080p / 4K downloads fail | Install **FFmpeg** (see prerequisites). |
| Browser didn't open | Open it yourself: <http://localhost:5000> |
| "Port already in use" | Another app is on port 5000. Close it, or edit `port=5000` in `backend.py`. |
| YouTube says "Sign in to confirm…" | yt-dlp may need updating — re-run `start.py` after deleting it, or run `pip install -U yt-dlp`. |
| Mac says "cannot verify developer" | This is a plain Python script — right-click → **Open** to bypass once. |

---

## 🔒 Privacy

Everything runs **on your computer**. Nothing is sent to any third-party server, there are no API keys, no analytics, no accounts. The server only listens on `localhost`, so other devices on your network can't reach it.

---

## 📁 What's in this folder

| File | What it does |
|---|---|
| `start.py` | One-click launcher. **This is what you run.** |
| `backend.py` | The local server (API + serves the web UI). |
| `index.html` | The web UI. You don't need to open it yourself — `start.py` does it. |
| `SETUP_GUIDE.md` | This file. |
| `IMPLEMENTATION_NOTES.md` | Technical notes / architecture. |

Enjoy! 🎉
