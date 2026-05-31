#!/bin/bash
set -e

INSTALL_DIR="$HOME/tools/claude-switcher"
PLIST_NAME="com.meganechan.claude-switcher"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"

echo "Installing Claude Switcher..."

# Stop existing instance
launchctl unload "$PLIST_PATH" 2>/dev/null || true
killall -9 python3 2>/dev/null || true

# Create install directory
mkdir -p "$INSTALL_DIR"
cp claude_switcher.py "$INSTALL_DIR/"

# Create venv and install deps
if [ ! -d "$INSTALL_DIR/.venv" ]; then
    python3 -m venv "$INSTALL_DIR/.venv"
fi
"$INSTALL_DIR/.venv/bin/pip" install -q rumps requests

# Create LaunchAgent
cat > "$PLIST_PATH" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_NAME</string>
    <key>ProgramArguments</key>
    <array>
        <string>$INSTALL_DIR/.venv/bin/python3</string>
        <string>$INSTALL_DIR/claude_switcher.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$INSTALL_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HOME/Library/Logs/claude-switcher.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/Library/Logs/claude-switcher.log</string>
</dict>
</plist>
PLIST

# Load and start
launchctl load "$PLIST_PATH"

echo "Done! Look for 'CC' in your menu bar."
