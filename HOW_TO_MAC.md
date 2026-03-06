# iPhone Spoofer — Mac Setup Guide

This app runs on Python directly on Mac. There is no .exe — ignore the `dist/` folder entirely.

---

## Requirements

- macOS 12 or later
- Python 3.11+ (check with `python3 --version`)
- iPhone plugged in via USB
- iTunes or Apple Devices app installed (for usbmuxd)

---

## Step 1 — Install Python 3.11+

If you don't have it:

```bash
brew install python@3.11
```

No Homebrew? Get it at https://brew.sh — paste the one-liner in Terminal, done.

---

## Step 2 — Clone or copy the project

If you're getting the files from someone else, just drop the whole `iphone-spoofer` folder somewhere on your Mac (Desktop is fine).

Open Terminal and navigate to it:

```bash
cd ~/Desktop/iphone-spoofer
```

---

## Step 3 — Install dependencies

```bash
pip3 install -r requirements.txt
```

This installs Flask and pymobiledevice3.

---

## Step 4 — Prepare your iPhone

1. Plug iPhone into Mac via USB.
2. Unlock it and tap **Trust** if prompted.
3. Enable **Developer Mode**:
   - Settings > Privacy & Security > Developer Mode > toggle ON
   - iPhone will restart — unlock it after.

---

## Step 5 — Run the app

**iOS 16 and older:**

```bash
python3 main.py
```

**iOS 17+ and iOS 26:**

pymobiledevice3 needs elevated access to create the tunnel:

```bash
sudo python3 main.py
```

Enter your Mac password when asked. This is normal — it's just for the USB tunnel, same as the Windows app auto-elevating via UAC.

The browser will open automatically at `http://127.0.0.1:5000`. If it doesn't, open it manually.

---

## Step 6 — Spoof your location

1. Click **Connect** in the browser UI and wait for it to show your device name.
2. Click anywhere on the map to drop a pin, or type coordinates manually.
3. Click **Set Location** — your iPhone GPS is now spoofed.
4. Click **Stop** to clear the fake location, or **Disconnect** when done.

---

## Troubleshooting

**"pymobiledevice3 is not installed"**
Run `pip3 install pymobiledevice3` and try again.

**Tunnel times out / connection fails on iOS 17+**
- Make sure Developer Mode is ON (see Step 4).
- Make sure you ran with `sudo`.
- Try unplugging and replugging the cable.
- Try a different USB cable (Lightning/USB-C data cables only, not charge-only).

**Device not found at all**
- Open Finder — does your iPhone show up in the sidebar? If not, trust the connection on your phone.
- Make sure no other app is holding the connection (Xcode, 3uTools, etc.).

**Port 5000 already in use**
macOS Monterey+ uses port 5000 for AirPlay Receiver. Disable it:
System Settings > General > AirDrop & Handoff > AirPlay Receiver > OFF

Then re-run the app.

---

## Stopping the app

Press `Ctrl+C` in Terminal. This kills the Flask server and releases the tunnel.
