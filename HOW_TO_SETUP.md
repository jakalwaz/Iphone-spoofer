# iPhone Spoofer — Full Setup Guide (Someone Else's Computer)

---

## Option A — No installs needed (Windows only)

If you have the `iPhoneSpoofer.exe` file:

1. Copy `iPhoneSpoofer.exe` onto their computer (USB, Google Drive, Discord, whatever)
2. Double-click it
3. Click **Yes** on the UAC admin prompt
4. Browser opens automatically at `http://127.0.0.1:5000`
5. Done

---

## Option B — Running from source (Windows or Mac)

Use this if you don't have the .exe or they're on a Mac.

---

### Step 1 — Get the files

Download the project as a ZIP from GitHub:

- Go to the repo page
- Click the green **Code** button
- Click **Download ZIP**
- Extract it — you'll get a folder called `iphone-spoofer-main`

---

### Step 2 — Install Python

Check if Python is already installed — open a terminal and run:

```
python --version
```

If it says `Python 3.11` or higher, skip to Step 3.

If not, download and install Python 3.11+ from **https://www.python.org/downloads/**

> **Windows:** During install, tick the box that says **"Add Python to PATH"** — this is important.

> **Mac:** You can also install via Homebrew: `brew install python@3.11`

After installing, close and reopen the terminal, then check again:

```
python --version
```

---

### Step 3 — Open a terminal in the project folder

**Windows:**
- Open the extracted folder `iphone-spoofer-main`
- Click the address bar at the top, type `cmd`, press Enter
- A command prompt opens already inside the folder

**Mac:**
- Open Terminal (search Spotlight for "Terminal")
- Type `cd ` (with a space), then drag the `iphone-spoofer-main` folder into the Terminal window and press Enter

---

### Step 4 — Install dependencies

Run this command:

```
python -m pip install -r requirements.txt
```

> Use `python -m pip` — this works even if `pip` alone isn't recognised.

Wait for it to finish. You only need to do this once.

---

### Step 5 — Run the app

**Windows:**
```
python main.py
```
Click **Yes** on the UAC admin prompt that pops up.

**Mac (iOS 16 and older):**
```
python3 main.py
```

**Mac (iOS 17+ / iOS 26):**
```
sudo python3 main.py
```
Enter the Mac password when asked.

The browser will open automatically at `http://127.0.0.1:5000`

If it doesn't open, go there manually in any browser.

---

### Step 6 — Prepare the iPhone

1. Plug iPhone into the computer via USB
2. Unlock the phone and tap **Trust** if a prompt appears
3. Enable Developer Mode:
   - Settings > Privacy & Security > Developer Mode > toggle ON
   - Phone will restart — unlock it after

---

### Step 7 — Use the app

1. Click **Connect Device** in the browser and wait for your device name to appear
2. **Teleport tab** — click anywhere on the map to instantly set your GPS location
3. **Path Walk tab** — click multiple points on the map to set a route, then hit Start Walk
4. **Joystick tab** — use W/A/S/D or arrow keys to move in real time
5. Click **Stop Simulation** when done to restore real GPS
6. Click **Disconnect** before closing

---

## Troubleshooting

**`pip` not recognised**
Use `python -m pip install -r requirements.txt` instead

**`python` not recognised**
Try `python3` instead. If still nothing, Python isn't installed or wasn't added to PATH — reinstall and tick "Add Python to PATH"

**Port 5000 already in use (Mac)**
Go to System Settings > General > AirDrop & Handoff > AirPlay Receiver > turn OFF, then re-run

**Device not found / connection fails**
- Make sure Developer Mode is ON
- Unplug and replug the cable
- Try a different cable (must be a data cable, not charge-only)
- Make sure no other app is using the phone (Xcode, iTunes sync, etc.)

**Tunnel times out on iOS 17+ (Mac)**
Make sure you ran with `sudo python3 main.py`

**UAC prompt doesn't appear (Windows)**
Right-click `main.py` or the terminal and choose **Run as administrator**

---

## Stopping the app

- Click **Disconnect** in the browser first
- Then close the browser tab
- In the terminal, press `Ctrl+C` to shut down the server
