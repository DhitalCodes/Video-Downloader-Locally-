# Implementation Notes — Video Downloader v4

A fully local video downloader designed around one goal: **the user does as little as possible**.

---

## What changed from v3

| Concern | v3 | v4 |
|---|---|---|
| Setup steps for user | Install deps → run `backend.py` → open `index.html` | **Just double-click `start.py`** |
| Dependency install | Manual `pip install …` | **Auto-installed on first run** by `start.py` |
| Browser launch | User opens HTML file from disk | **Browser opens automatically** when server is live |
| Frontend hosting | Loose file on disk (file://) | **Served by Flask** at `http://localhost:5000/` — no CORS quirks, no “file not found” confusion |
| URL paste | Manual paste required | **Clipboard auto-paste** on window focus + drag-and-drop |
| Workflow | Analyze → click Download in a row | One-click **“Download Best Quality”** + per-format buttons |
| Progress feedback | Spinner only | **Live progress bar** with %, speed, ETA via Server-Sent Events |
| Backend status polling | Every 5s, even when idle | **Removed** (UI is served from the backend, so it’s always reachable) |
| URL validation | Hard-coded regex of 6 domains | **Generic `http(s)://…` check**; yt-dlp decides what’s actually supported (1000+ sites) |
| File transfer | Whole file buffered in memory as `Blob`, then re-saved | **`<a href download>` to `/api/file/{job_id}`** — streamed by the browser; no double-buffering |
| Error UX | Inline red box that stays around | Transient **toast** notifications |

---

## File layout

```
video_downloader/
├── start.py                 ← user runs this
├── backend.py               ← Flask app (API + serves index.html)
├── index.html               ← single-page UI
├── SETUP_GUIDE.md
└── IMPLEMENTATION_NOTES.md  ← this file
```

---

## Runtime architecture

```
┌─────────────────────────────────────────────────────────────┐
│  start.py                                                   │
│  ├─ ensure_deps()          install flask/flask-cors/yt-dlp  │
│  ├─ thread: open_browser_when_ready()                       │
│  └─ from backend import app; app.run(...)                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Flask app  (http://localhost:5000)                         │
│                                                             │
│   GET   /                  → index.html                     │
│   GET   /api/status        → liveness                       │
│   POST  /api/analyze       → list formats (yt-dlp dry-run)  │
│   POST  /api/start         → spawn worker thread, returns   │
│                              { job_id }                     │
│   GET   /api/progress/:id  → text/event-stream  (SSE)       │
│   GET   /api/file/:id      → send_file + cleanup tmpdir     │
└─────────────────────────────────────────────────────────────┘
```

Job state lives in an in-process `dict` guarded by a lock. Each download runs in its own daemon thread and writes a `tempfile.mkdtemp()` directory; the tmpdir is removed when the file is streamed out (`response.call_on_close`) or when the job errors out.

---

## API contract

### `POST /api/analyze`
Request:
```json
{ "url": "https://..." }
```
Response:
```json
{
  "title": "…",
  "thumbnail": "https://…",
  "duration": 215,
  "uploader": "…",
  "platform": "Youtube",
  "videoFormats": [
    { "resolution": "1080p", "height": 1080, "format": "MP4",
      "bitrate": "5.2Mbps", "size": 86234112, "has_audio": false }
  ],
  "audioFormats": [
    { "format": "M4A", "bitrate": "128kbps", "size": 3450000 }
  ]
}
```

### `POST /api/start`
Request:
```json
{ "url": "...", "quality": "1080p", "type": "video" }
```
- `type`: `"video"` or `"audio"`
- `quality` for video: `"best"` or e.g. `"1080p"`, `"720p"` (matched as `bestvideo[height<=N]+bestaudio[height<=N]/best`)
- `quality` for audio: `"mp3"` triggers the FFmpeg extractor; anything else keeps the original audio container.

Response: `{ "job_id": "…hex…" }`

### `GET /api/progress/{job_id}`  *(SSE)*
Each event payload:
```json
{ "status": "downloading|processing|ready|error",
  "progress": 47.2, "speed": 1843200, "eta": 12,
  "filename": "Title.mp4", "error": null }
```
Stream closes on `ready` or `error`.

### `GET /api/file/{job_id}`
Streams the file with `Content-Disposition: attachment`. After the response closes, the worker’s tmpdir is removed and the job entry is dropped from memory.

---

## Notable design choices

- **Single origin (Flask serves the UI):** removes every CORS/file-protocol footgun and lets the front-end use relative URLs (`/api/...`). One server = one origin = one less thing for the user.
- **SSE over WebSockets:** progress is strictly server→client; SSE is one line of `Response(..., mimetype="text/event-stream")` and works fine through any localhost setup, no extra dependency.
- **Browser triggers the file save:** the worker writes to a tempdir on the server, then the page sets `a.href = /api/file/{id}; a.click()`. The browser handles the “Save As” / Downloads-folder behaviour; nothing is buffered in JS memory.
- **No registry of past jobs:** when a job is delivered or errors out, it’s wiped. There’s no history feature on purpose — keeps state simple and avoids leaking large files on disk.
- **No hard-coded site whitelist:** the UI just checks for an `http(s)://…` shape and hands the URL to yt-dlp. If yt-dlp can handle it, the user can download it.
- **Clipboard auto-paste:** uses `navigator.clipboard.readText()` on window focus. Browsers only grant it after a user gesture/visible tab, so failures are silently ignored — never breaks the UX.

---

## Configuration knobs

In `backend.py`:
```python
app.run(host="localhost", port=5000)   # change port if 5000 is taken
```
In the worker:
```python
fmt = f"bestvideo[height<={h}]+bestaudio[height<={h}]/best"
postprocessors = [{"key":"FFmpegExtractAudio","preferredcodec":"mp3", ...}]
```
Edit those two blocks to customise default quality or output codec.

---

## Maintenance

- Update yt-dlp periodically (`pip install -U yt-dlp`) — it gets broken by site-side changes often enough.
- If you want to expose the app to your LAN, change `host="localhost"` to `host="0.0.0.0"` *and* add some form of authentication. The default `localhost` bind is intentional.

---

## Privacy & legal

Everything is local. No telemetry, no API keys, no third-party calls (other than the actual download from the source site). The user is responsible for respecting each platform’s terms of service and the underlying content licences.

---

**Version:** 4.0 — “zero-setup local”
**Status:** ready to ship
