"""
main.py — Flask server for iPhone GPS Spoofer.

Run with: python main.py
Opens browser automatically at http://localhost:5000
Requires admin privileges for iOS 17+ tunnel — auto-elevates via UAC if needed.
"""

import os
import sys
import ctypes
import threading
import webbrowser
import logging

# ── Sleep prevention (Windows only) ─────────────────────────────────
_ES_CONTINUOUS      = 0x80000000
_ES_SYSTEM_REQUIRED = 0x00000001

def _prevent_sleep():
    if sys.platform == "win32":
        ctypes.windll.kernel32.SetThreadExecutionState(
            _ES_CONTINUOUS | _ES_SYSTEM_REQUIRED
        )

def _allow_sleep():
    if sys.platform == "win32":
        ctypes.windll.kernel32.SetThreadExecutionState(_ES_CONTINUOUS)

# ---------------------------------------------------------------------------
# UAC auto-elevation (Windows only)
# ---------------------------------------------------------------------------
def _is_admin() -> bool:
    if sys.platform != "win32":
        return os.geteuid() == 0
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def _relaunch_as_admin():
    if sys.platform != "win32":
        print("ERROR: Run with sudo: sudo python3 main.py")
        sys.exit(1)
    script = os.path.abspath(sys.argv[0])
    params = " ".join(f'"{a}"' for a in sys.argv[1:])
    rc = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, f'"{script}" {params}', None, 1
    )
    if rc <= 32:
        ctypes.windll.user32.MessageBoxW(
            0,
            "Administrator privileges are required to create the iOS tunnel.\n"
            "Please re-run as administrator.",
            "iPhone Spoofer — Admin Required",
            0x10,
        )
    sys.exit(0)

if __name__ == "__main__" and not _is_admin():
    _relaunch_as_admin()

from flask import Flask, jsonify, request, render_template

from spoofer import DeviceSpoofer

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
# Suppress Flask's per-request access log ("127.0.0.1 GET /api/status 200")
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PyInstaller resource path helper
# ---------------------------------------------------------------------------
def resource_path(relative):
    """Return absolute path — works for dev and PyInstaller one-file builds."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
template_folder = resource_path("templates")
app = Flask(__name__, template_folder=template_folder)
app.config["JSON_SORT_KEYS"] = False

spoofer = DeviceSpoofer()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/connect", methods=["POST"])
def api_connect():
    try:
        spoofer.connect()
        _prevent_sleep()
        status = spoofer.get_status()
        return jsonify({"ok": True, **status})
    except Exception as e:
        logger.error(f"connect error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/location", methods=["POST"])
def api_location():
    data = request.get_json(force=True) or {}
    try:
        lat = float(data["lat"])
        lon = float(data["lon"])
    except (KeyError, TypeError, ValueError) as e:
        return jsonify({"ok": False, "error": f"Bad payload: {e}"}), 400

    try:
        spoofer.set_location(lat, lon)
        return jsonify({"ok": True, "lat": lat, "lon": lon})
    except Exception as e:
        logger.error(f"set_location error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/stop", methods=["POST"])
def api_stop():
    try:
        spoofer.stop_simulation()
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"stop error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/disconnect", methods=["POST"])
def api_disconnect():
    try:
        spoofer.disconnect()
        _allow_sleep()
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"disconnect error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/status", methods=["GET"])
def api_status():
    return jsonify(spoofer.get_status())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def open_browser():
    webbrowser.open("http://127.0.0.1:5000")


if __name__ == "__main__":
    threading.Timer(1.5, open_browser).start()
    logger.info("Starting iPhone Spoofer at http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
