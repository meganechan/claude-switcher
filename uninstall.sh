#!/bin/bash
set -e

PLIST_PATH="$HOME/Library/LaunchAgents/com.meganechan.claude-switcher.plist"

echo "Uninstalling Claude Switcher..."

launchctl unload "$PLIST_PATH" 2>/dev/null || true
rm -f "$PLIST_PATH"
rm -rf "$HOME/tools/claude-switcher"
rm -rf "$HOME/.claude-switcher"
rm -f "$HOME/Library/Logs/claude-switcher.log"

echo "Done. Account data removed from ~/.claude-switcher/"
