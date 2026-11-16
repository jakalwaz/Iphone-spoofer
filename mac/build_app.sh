#!/bin/bash
# Builds the menu bar app "iPhone Spoofer.app" into ~/Applications (or the folder given as $1).
set -e
cd "$(dirname "$0")/.."
DEST="${1:-$HOME/Applications}/iPhone Spoofer.app"
rm -rf "$DEST"
mkdir -p "$DEST/Contents/MacOS" "$DEST/Contents/Resources/app"
APP="$DEST/Contents/Resources/app"
cp -R main.py spoofer.py requirements.txt templates mac "$APP/"
python3 -m venv "$APP/.venv"
"$APP/.venv/bin/pip" install -q -U pip
"$APP/.venv/bin/pip" install -q -r requirements.txt

"$APP/.venv/bin/python" mac/make_icon.py "$DEST/Contents/Resources/AppIcon.icns"

cat > "$DEST/Contents/MacOS/iPhone Spoofer" <<'SH'
#!/bin/bash
APP="$(cd "$(dirname "$0")/../Resources/app" && pwd)"
exec "$APP/.venv/bin/python" "$APP/mac/app.py"
SH
chmod +x "$DEST/Contents/MacOS/iPhone Spoofer"

cat > "$DEST/Contents/Info.plist" <<'PL'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>iPhone Spoofer</string>
  <key>CFBundleExecutable</key><string>iPhone Spoofer</string>
  <key>CFBundleIdentifier</key><string>local.iphone-spoofer</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>LSUIElement</key><true/>
</dict></plist>
PL
echo "Built: $DEST"
