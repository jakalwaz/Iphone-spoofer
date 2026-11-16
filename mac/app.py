"""
iPhone Spoofer for macOS: menu bar icon + native map window, no browser.

- Starts the server as admin (one password prompt).
- Closing the window only hides it and unloads the map, so nothing runs in it.
- Every 5 s it checks the phone; if it dropped (lock, cable, sleep) it reconnects
  and re-applies the last location.
- Quit stops the server, and the phone goes back to real GPS.
"""

import json
import os
import subprocess
import threading
import time
import urllib.request

import AppKit
import objc
import webview
from Foundation import NSObject
from PyObjCTools.AppHelper import callAfter
from webview.platforms.cocoa import BrowserView
import atexit

URL = "http://127.0.0.1:5055"
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = os.path.join(APP_DIR, ".venv", "bin", "python")


def call(path, body=None, timeout=2):
    req = urllib.request.Request(
        URL + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"{}")


def _q(s):
    return "'" + s.replace("'", "'\\''") + "'"


def start_server():
    # the subshell detaches it; nohup fails under the admin prompt ("can't detach from console")
    cmd = f"cd {_q(APP_DIR)} && (SPOOFER_NO_BROWSER=1 {_q(PY)} main.py > /tmp/iphone-spoofer.log 2>&1 < /dev/null &)"
    script = (
        f'do shell script "{cmd}" with prompt '
        '"iPhone Spoofer needs your password to open the USB tunnel to your iPhone." '
        "with administrator privileges"
    )
    if subprocess.run(["osascript", "-e", script]).returncode != 0:
        return False
    for _ in range(40):
        try:
            call("/api/status")
            return True
        except Exception:
            time.sleep(0.25)
    return False


window = None
# last: location to keep re-applying (None = spoofing off); resume: where "turn on" goes back to
state = {"last": None, "resume": None}

ICONS = {"spoof": "location.fill", "idle": "location", "none": "location.slash"}


def _symbol(name):
    img = AppKit.NSImage.imageWithSystemSymbolName_accessibilityDescription_(name, "iPhone Spoofer")
    img.setTemplate_(True)  # follows light/dark menu bar
    return img


class Menu(NSObject):
    def init(self):
        self = objc.super(Menu, self).init()
        bar = AppKit.NSStatusBar.systemStatusBar()
        self.item = bar.statusItemWithLength_(AppKit.NSVariableStatusItemLength)
        self.item.button().setImage_(_symbol(ICONS["none"]))
        menu = AppKit.NSMenu.alloc().init()
        menu.setAutoenablesItems_(False)
        self.status = menu.addItemWithTitle_action_keyEquivalent_("Starting…", None, "")
        self.status.setEnabled_(False)
        self.where = menu.addItemWithTitle_action_keyEquivalent_("", None, "")
        self.where.setEnabled_(False)
        self.where.setHidden_(True)
        menu.addItem_(AppKit.NSMenuItem.separatorItem())
        self.toggle = menu.addItemWithTitle_action_keyEquivalent_("Fake Location", "toggle:", "t")
        self.toggle.setTarget_(self)
        menu.addItem_(AppKit.NSMenuItem.separatorItem())
        for title, sel, key in (("Open Map…", "openMap:", "o"), ("Reconnect iPhone", "reconnect:", "r")):
            menu.addItemWithTitle_action_keyEquivalent_(title, sel, key).setTarget_(self)
        menu.addItem_(AppKit.NSMenuItem.separatorItem())
        menu.addItemWithTitle_action_keyEquivalent_("Quit iPhone Spoofer", "quit:", "q").setTarget_(self)
        self.item.setMenu_(menu)
        return self

    def openMap_(self, _):
        show_window()

    def toggle_(self, _):
        if state["last"]:  # on -> off: real GPS
            state["last"] = None
            threading.Thread(target=lambda: _try(call, "/api/stop", {}, 5), daemon=True).start()
        elif state["resume"]:  # off -> on: back to the last fake spot
            lat, lon = state["resume"]
            state["last"] = (lat, lon)
            threading.Thread(target=lambda: _try(call, "/api/location", {"lat": lat, "lon": lon}, 10), daemon=True).start()
        else:
            show_window()  # nothing to resume yet: pick a spot on the map

    def reconnect_(self, _):
        def work():
            _try(call, "/api/disconnect", {}, 10)
            _try(call, "/api/connect", {}, 40)
            if state["last"]:
                _try(call, "/api/location", {"lat": state["last"][0], "lon": state["last"][1]}, 10)
        threading.Thread(target=work, daemon=True).start()

    def quit_(self, _):
        _try(call, "/api/quit", {}, 5)
        os._exit(0)

    @objc.python_method
    def set(self, icon, status, where=None, connected=False):
        self.item.button().setImage_(_symbol(ICONS[icon]))
        self.status.setTitle_(status)
        self.where.setHidden_(not where)
        self.where.setTitle_(where or "")
        self.toggle.setState_(1 if state["last"] else 0)
        self.toggle.setEnabled_(connected)


def _try(fn, *a):
    try:
        return fn(*a)
    except Exception:
        return None


def _policy(p):
    # Dock icon + Cmd+Q only while the window is open; menu bar only when closed
    app = AppKit.NSApplication.sharedApplication()
    app.setActivationPolicy_(p)
    if p == AppKit.NSApplicationActivationPolicyRegular:
        app.activateIgnoringOtherApps_(True)


class AppDelegate(objc.Category(BrowserView.AppDelegate)):
    # double-clicking the app while it runs reopens the window (menu bar icon can hide behind the notch)
    def applicationShouldHandleReopen_hasVisibleWindows_(self, app, flag):
        show_window()
        return True


def show_window():
    # pywebview calls block on the main thread, so drive them from a worker
    def work():
        state["declined"] = False  # user asked for the map: allow a restart prompt again
        if not state.get("loaded"):
            window.load_url(URL)
            state["loaded"] = True
        window.show()
        callAfter(_policy, AppKit.NSApplicationActivationPolicyRegular)
    threading.Thread(target=work, daemon=True).start()


def on_closing():
    # hide instead of quitting; unload the page so the map uses no CPU or memory
    def work():
        window.hide()
        window.load_url("about:blank")
        state["loaded"] = False
        callAfter(_policy, AppKit.NSApplicationActivationPolicyAccessory)
    threading.Thread(target=work, daemon=True).start()
    return False


def watchdog(menu):
    while True:
        try:
            s = call("/api/status")
        except Exception:
            # server died or was stopped: start it again (one password prompt); if cancelled, wait for Open Map
            if state.get("declined"):
                callAfter(menu.set, "none", "Stopped — choose Open Map to restart")
                time.sleep(5)
                continue
            callAfter(menu.set, "none", "Starting…")
            if start_server():
                if state.get("loaded"):
                    window.load_url(URL)
            else:
                state["declined"] = True
            continue
        if s.get("lat") is not None:
            state["last"] = state["resume"] = (s["lat"], s["lon"])
        elif s.get("connected"):
            state["last"] = None  # spoofing turned off (map or menu)
        if s.get("connected"):
            name = f"{s.get('device') or 'iPhone'} · iOS {s.get('ios') or ''}".strip()
            if s.get("lat") is not None:
                callAfter(menu.set, "spoof", name, f"At {s['lat']:.5f}, {s['lon']:.5f}", True)
            else:
                callAfter(menu.set, "idle", name, "Using real GPS", True)
        else:
            callAfter(menu.set, "none", "Looking for iPhone — plug in & unlock")
            try:
                call("/api/connect", {}, timeout=40)
                if state["last"]:
                    call("/api/location", {"lat": state["last"][0], "lon": state["last"][1]}, timeout=10)
            except Exception:
                pass
        time.sleep(5)


def setup():
    def main_thread():
        app = AppKit.NSApplication.sharedApplication()
        app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)  # no Dock icon
        icon = AppKit.NSImage.alloc().initWithContentsOfFile_(os.path.join(os.path.dirname(APP_DIR), "AppIcon.icns"))
        if icon:
            app.setApplicationIconImage_(icon)  # Dock shows our icon, not Python's
        menu = Menu.alloc().init()
        globals()["_menu"] = menu  # keep a reference
        threading.Thread(target=watchdog, args=(menu,), daemon=True).start()
        show_window()
    callAfter(main_thread)


if __name__ == "__main__":
    # name the app menu "iPhone Spoofer" instead of "Python"
    AppKit.NSBundle.mainBundle().infoDictionary()["CFBundleName"] = "iPhone Spoofer"
    try:
        call("/api/status")
    except Exception:
        if not start_server():
            raise SystemExit(0)  # password prompt cancelled
    atexit.register(lambda: _try(call, "/api/quit", {}, 3))  # Cmd+Q also stops the server
    window = webview.create_window("iPhone Spoofer", "about:blank", width=1200, height=800, min_size=(720, 480))
    window.events.closing += on_closing
    webview.start(setup)
