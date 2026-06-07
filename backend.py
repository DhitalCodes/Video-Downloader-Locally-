#!/usr/bin/env python3
"""
Video Downloader — local backend.

Serves both the API and the web UI (index.html) so the user only opens ONE thing.
Streams downloads straight to the browser with live progress via Server-Sent Events.
"""

from flask import Flask, request, jsonify, send_file, send_from_directory, Response
from flask_cors import CORS
import yt_dlp
import os
import json
import uuid
import tempfile
import shutil
import threading
import time
from pathlib import Path

# ------------------------------------------------------------------
# App setup
# ------------------------------------------------------------------
BASE_DIR = Path(__file__).parent.resolve()
app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")
CORS(app)

# In-memory job registry: job_id -> {status, progress, speed, eta, filepath, error, tmpdir}
JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()


# ------------------------------------------------------------------
# Static / UI
# ------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(str(BASE_DIR), "index.html")


@app.route("/api/status")
def status():
    return jsonify({"status": "running"})


# ------------------------------------------------------------------
# Analyze: list available formats
# ------------------------------------------------------------------
@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        return jsonify({"error": f"Could not read this link: {e}"}), 400

    video_formats, audio_formats = [], []
    seen_v, seen_a = set(), set()

    for f in info.get("formats", []) or []:
        vcodec = f.get("vcodec") or "none"
        acodec = f.get("acodec") or "none"
        ext = (f.get("ext") or "").lower()
        size = f.get("filesize") or f.get("filesize_approx") or 0

        if vcodec != "none" and f.get("height"):
            key = f"{f['height']}p_{ext}"
            if key in seen_v:
                continue
            seen_v.add(key)
            video_formats.append({
                "resolution": f"{f['height']}p",
                "height": f["height"],
                "format": ext.upper(),
                "bitrate": f"{f.get('tbr'):.1f}Mbps" if f.get("tbr") else "—",
                "size": size,
                "has_audio": acodec != "none",
            })
        elif acodec != "none" and vcodec == "none":
            if ext in seen_a:
                continue
            seen_a.add(ext)
            audio_formats.append({
                "format": ext.upper(),
                "bitrate": f"{int(f['abr'])}kbps" if f.get("abr") else "—",
                "size": size,
            })

    video_formats.sort(key=lambda x: x["height"], reverse=True)

    return jsonify({
        "title": info.get("title") or "Untitled",
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "uploader": info.get("uploader"),
        "platform": info.get("extractor_key") or "Video",
        "videoFormats": video_formats,
        "audioFormats": audio_formats,
    })


# ------------------------------------------------------------------
# Start a download job (returns job_id, then client polls progress)
# ------------------------------------------------------------------
def _run_download(job_id: str, url: str, quality: str, kind: str):
    job = JOBS[job_id]
    tmpdir = tempfile.mkdtemp(prefix="vdl_")
    job["tmpdir"] = tmpdir

    def hook(d):
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes") or 0
            job["progress"] = round(done * 100 / total, 1) if total else 0
            job["speed"] = d.get("speed") or 0
            job["eta"] = d.get("eta") or 0
            job["status"] = "downloading"
        elif d.get("status") == "finished":
            job["status"] = "processing"

    if kind == "audio":
        fmt = "bestaudio/best"
        postprocessors = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}] if quality == "mp3" else []
        outtmpl = os.path.join(tmpdir, "%(title).200B.%(ext)s")
    else:
        if quality in ("best", "", None):
            fmt = "bestvideo*+bestaudio/best"
        else:  # like "720p"
            h = quality.rstrip("p")
            fmt = f"bestvideo[height<={h}]+bestaudio/best[height<={h}]/best"
        postprocessors = []
        outtmpl = os.path.join(tmpdir, "%(title).200B.%(ext)s")

    opts = {
        "format": fmt,
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "progress_hooks": [hook],
        "postprocessors": postprocessors,
        "merge_output_format": "mp4" if kind == "video" else None,
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            # If audio was post-processed to mp3, swap extension
            if kind == "audio" and quality == "mp3":
                filename = os.path.splitext(filename)[0] + ".mp3"

        if not os.path.exists(filename):
            # fall back to whatever single file is in tmpdir
            files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir)]
            files = [f for f in files if os.path.isfile(f)]
            if not files:
                raise RuntimeError("Download finished but no file was produced.")
            filename = max(files, key=os.path.getsize)

        job["filepath"] = filename
        job["filename"] = os.path.basename(filename)
        job["progress"] = 100
        job["status"] = "ready"
    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
        shutil.rmtree(tmpdir, ignore_errors=True)


@app.route("/api/start", methods=["POST"])
def start_download():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    quality = data.get("quality") or "best"
    kind = data.get("type") or "video"

    if not url:
        return jsonify({"error": "URL is required"}), 400

    job_id = uuid.uuid4().hex
    with JOBS_LOCK:
        JOBS[job_id] = {
            "status": "queued",
            "progress": 0,
            "speed": 0,
            "eta": 0,
            "filepath": None,
            "filename": None,
            "error": None,
        }

    threading.Thread(target=_run_download, args=(job_id, url, quality, kind), daemon=True).start()
    return jsonify({"job_id": job_id})


@app.route("/api/progress/<job_id>")
def progress_stream(job_id):
    """Server-Sent Events stream so the UI gets live progress without polling."""
    def gen():
        last = None
        while True:
            job = JOBS.get(job_id)
            if not job:
                yield f"data: {json.dumps({'status':'error','error':'unknown job'})}\n\n"
                return
            payload = {
                "status": job["status"],
                "progress": job["progress"],
                "speed": job["speed"],
                "eta": job["eta"],
                "error": job["error"],
                "filename": job["filename"],
            }
            blob = json.dumps(payload)
            if blob != last:
                yield f"data: {blob}\n\n"
                last = blob
            if job["status"] in ("ready", "error"):
                return
            time.sleep(0.4)
    return Response(gen(), mimetype="text/event-stream")


@app.route("/api/file/<job_id>")
def get_file(job_id):
    job = JOBS.get(job_id)
    if not job or job["status"] != "ready" or not job.get("filepath"):
        return jsonify({"error": "File not ready"}), 404

    filepath = job["filepath"]
    tmpdir = job.get("tmpdir")

    response = send_file(filepath, as_attachment=True, download_name=job["filename"])

    @response.call_on_close
    def _cleanup():
        try:
            if tmpdir and os.path.isdir(tmpdir):
                shutil.rmtree(tmpdir, ignore_errors=True)
        finally:
            JOBS.pop(job_id, None)

    return response


# ------------------------------------------------------------------
# Run directly (start.py also imports `app` from this module)
# ------------------------------------------------------------------
if __name__ == "__main__":
    print("✅ Backend running at http://localhost:5000")
    app.run(host="localhost", port=5000, debug=False)
