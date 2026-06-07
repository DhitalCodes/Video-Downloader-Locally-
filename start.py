#!/usr/bin/env python3
"""
🚀 One-Click Launcher for Video Downloader

Just double-click this file. It will:
  1. Check & auto-install Python dependencies if missing
  2. Start the local backend server
  3. Open the app in your default browser

No terminal commands. No setup. Just run.
"""

import sys
import subprocess
import importlib
import webbrowser
import time
import threading
import os

# ---- Required packages (pip name -> import name) ----
REQUIRED = {
    "flask": "flask",
    "flask-cors": "flask_cors",
    "yt-dlp": "yt_dlp",
}

APP_URL = "http://localhost:5000"


def ensure_deps():
    """Auto-install any missing Python dependency. User does nothing."""
    missing = []
    for pip_name, import_name in REQUIRED.items():
        try:
            importlib.import_module(import_name)
        except ImportError:
            missing.append(pip_name)

    if not missing:
        return

    print(f"📦 First-time setup: installing {', '.join(missing)} ...")
    print("   (this only happens once)\n")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check", *missing]
        )
        print("✅ Dependencies installed.\n")
    except subprocess.CalledProcessError:
        print("\n❌ Could not auto-install dependencies.")
        print("   Please run manually:  pip install " + " ".join(missing))
        input("\nPress Enter to exit...")
        sys.exit(1)


def open_browser_when_ready():
    """Wait until the server responds, then open the browser."""
    import urllib.request
    for _ in range(40):  # ~10 seconds max
        try:
            urllib.request.urlopen(APP_URL + "/api/status", timeout=0.25)
            webbrowser.open(APP_URL)
            return
        except Exception:
            time.sleep(0.25)


def main():
    print("=" * 60)
    print("  🎬  Video Downloader  —  starting up")
    print("=" * 60)

    ensure_deps()

    # Launch browser in parallel so it opens as soon as the server is live
    threading.Thread(target=open_browser_when_ready, daemon=True).start()

    # Import after deps are guaranteed
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    from backend import app  # noqa: E402

    print(f"✅ Server ready at {APP_URL}")
    print("   Your browser should open automatically.")
    print("   Keep this window open while using the app.")
    print("   Press Ctrl+C to quit.\n")

    try:
        app.run(host="localhost", port=5000, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")


if __name__ == "__main__":
    main()
