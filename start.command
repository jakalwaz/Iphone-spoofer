#!/bin/bash
# Double-click on Mac to run. First run installs everything.
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "First run: installing (one time)..."
  python3 -m venv .venv && .venv/bin/pip install -q -U pip && .venv/bin/pip install -q -r requirements.txt || { echo "Install failed. Need Python 3: brew install python"; read; exit 1; }
fi
echo "Plug in iPhone by USB, unlock it, Developer Mode ON."
echo "Enter your Mac password (needed for the iOS tunnel):"
sudo .venv/bin/python main.py
