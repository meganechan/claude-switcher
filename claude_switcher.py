#!/usr/bin/env python3
"""Claude Code Account Switcher — macOS menu bar app."""

import json
import os
import subprocess
import threading
import time

import requests
import rumps

KEYCHAIN_SERVICE = "Claude Code-credentials"
KEYCHAIN_ACCOUNT = os.environ.get("USER", "tony")
BACKUP_DIR = os.path.expanduser("~/.claude-switcher")
BACKUP_FILE = os.path.join(BACKUP_DIR, "accounts.json")
CLAUDE_JSON = os.path.expanduser("~/.claude.json")
USAGE_API = "https://api.anthropic.com/api/oauth/usage"
REFRESH_INTERVAL = 300


def read_keychain_token():
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE,
             "-a", KEYCHAIN_ACCOUNT, "-w"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def write_keychain_token(token):
    subprocess.run(
        ["security", "delete-generic-password", "-s", KEYCHAIN_SERVICE,
         "-a", KEYCHAIN_ACCOUNT],
        capture_output=True
    )
    result = subprocess.run(
        ["security", "add-generic-password", "-s", KEYCHAIN_SERVICE,
         "-a", KEYCHAIN_ACCOUNT, "-w", token],
        capture_output=True
    )
    return result.returncode == 0


def read_oauth_account():
    try:
        with open(CLAUDE_JSON, "r") as f:
            data = json.load(f)
        return data.get("oauthAccount", {})
    except Exception:
        return {}


def write_oauth_account(oauth_account):
    try:
        with open(CLAUDE_JSON, "r") as f:
            data = json.load(f)
        data["oauthAccount"] = oauth_account
        with open(CLAUDE_JSON, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def extract_access_token(token_json_str):
    try:
        data = json.loads(token_json_str)
        return data.get("claudeAiOauth", {}).get("accessToken")
    except Exception:
        return None


def get_email_from_oauth(oauth):
    return oauth.get("emailAddress", "unknown")


def fetch_usage(access_token):
    try:
        resp = requests.get(
            USAGE_API,
            headers={
                "Authorization": f"Bearer {access_token}",
                "anthropic-beta": "oauth-2025-04-20",
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 401:
            return "expired"
    except Exception:
        pass
    return None


def delegated_refresh():
    """Let Claude CLI refresh the token via `claude auth status`."""
    try:
        result = subprocess.run(
            ["claude", "auth", "status"],
            capture_output=True, text=True, timeout=15
        )
        return result.returncode == 0
    except Exception:
        return False


def validate_token(access_token):
    """Check if token is still valid by calling usage API."""
    try:
        resp = requests.get(
            USAGE_API,
            headers={
                "Authorization": f"Bearer {access_token}",
                "anthropic-beta": "oauth-2025-04-20",
            },
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False


def load_accounts():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    if os.path.exists(BACKUP_FILE):
        with open(BACKUP_FILE, "r") as f:
            return json.load(f)
    return {}


def save_accounts(accounts):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    with open(BACKUP_FILE, "w") as f:
        json.dump(accounts, f, indent=2)


class ClaudeSwitcherApp(rumps.App):
    def __init__(self):
        self.accounts = load_accounts()
        self.current_email = None
        self.usage_data = None

        self._detect_current()

        self.active_item = rumps.MenuItem(f"Active: {self.current_email or 'none'}")
        self.active_item.set_callback(None)
        self.session_item = rumps.MenuItem("Session (5h): ...")
        self.session_item.set_callback(None)
        self.weekly_item = rumps.MenuItem("Weekly: ...")
        self.weekly_item.set_callback(None)
        self.reset_item = rumps.MenuItem("Reset: ...")
        self.reset_item.set_callback(None)

        super().__init__("CC", menu=[
            self.active_item,
            None,
            self.session_item,
            self.weekly_item,
            self.reset_item,
            None,
            rumps.MenuItem("Switch Account"),
            None,
            rumps.MenuItem("Add Current Account"),
            rumps.MenuItem("Refresh Usage"),
            None,
            rumps.MenuItem("Quit"),
        ], quit_button=None)

        self._start_refresh()

    def _detect_current(self):
        oauth = read_oauth_account()
        self.current_email = get_email_from_oauth(oauth)
        token_str = read_keychain_token()
        if token_str and self.current_email != "unknown":
            self.accounts[self.current_email] = {
                "token": token_str,
                "oauth": oauth,
            }
            save_accounts(self.accounts)

    def _update_display(self):
        self.active_item.title = f"Active: {self.current_email or 'none'}"
        if self.usage_data and self.usage_data != "expired":
            five_h = self.usage_data.get("five_hour", {}) or {}
            seven_d = self.usage_data.get("seven_day", {}) or {}
            s_pct = five_h.get("utilization", "?")
            w_pct = seven_d.get("utilization", "?")
            self.session_item.title = f"Session (5h): {s_pct}%"
            self.weekly_item.title = f"Weekly: {w_pct}%"
            w_reset = seven_d.get("resets_at", "")
            self.reset_item.title = f"Reset: {w_reset[:16]}" if w_reset else "Reset: ..."
            self.title = f"CC {w_pct}%"
        elif self.usage_data == "expired":
            self.title = "CC expired"
            self.session_item.title = "Session (5h): expired"
            self.weekly_item.title = "Weekly: expired"
        else:
            self.title = "CC"

    def _start_refresh(self):
        def loop():
            while True:
                self._refresh_usage()
                time.sleep(REFRESH_INTERVAL)
        t = threading.Thread(target=loop, daemon=True)
        t.start()

    def _refresh_usage(self):
        token_str = read_keychain_token()
        if not token_str:
            return
        access_token = extract_access_token(token_str)
        if not access_token:
            return
        result = fetch_usage(access_token)
        if result == "expired":
            if delegated_refresh():
                token_str = read_keychain_token()
                if token_str:
                    access_token = extract_access_token(token_str)
                    if access_token:
                        result = fetch_usage(access_token)
                        # Update saved token after refresh
                        if result and result != "expired":
                            self._detect_current()
        self.usage_data = result
        self._update_display()

    @rumps.clicked("Switch Account")
    def switch_account(self, _):
        others = [e for e in self.accounts if e != self.current_email]
        if not others:
            rumps.alert(
                "No other account",
                "Login with another account in Claude Code first,\nthen click 'Add Current Account'.",
            )
            return

        if len(others) == 1:
            self._do_switch(others[0])
            return

        resp = rumps.Window(
            title="Switch Account",
            message="\n".join(f"{i+1}. {e}" for i, e in enumerate(others)),
            default_text="1",
            ok="Switch",
            cancel="Cancel",
        ).run()
        if resp.clicked:
            try:
                idx = int(resp.text.strip()) - 1
                if 0 <= idx < len(others):
                    self._do_switch(others[idx])
            except ValueError:
                pass

    def _do_switch(self, target_email):
        # Save current account's live token before switching
        prev_email = self.current_email
        current_token = read_keychain_token()
        current_oauth = read_oauth_account()
        if current_token and prev_email and prev_email != "unknown":
            self.accounts[prev_email] = {
                "token": current_token,
                "oauth": current_oauth,
            }

        target = self.accounts.get(target_email)
        if not target:
            rumps.alert("Error", f"No backup for {target_email}")
            return

        # Write target credentials
        ok_token = write_keychain_token(target["token"])
        ok_oauth = write_oauth_account(target["oauth"])

        if not (ok_token and ok_oauth):
            rumps.alert("Error", "Failed to write credentials")
            return

        self.current_email = target_email

        # Check if token is already valid
        access = extract_access_token(target["token"])
        if access and validate_token(access):
            save_accounts(self.accounts)
            self._refresh_usage()
            self._update_display()
            rumps.notification(
                "Claude Switcher",
                f"Switched to {target_email}",
                "Ready to use.",
            )
            return

        # Token expired — try delegated refresh via CLI
        if delegated_refresh():
            new_token = read_keychain_token()
            new_access = extract_access_token(new_token) if new_token else None
            if new_access and validate_token(new_access):
                self.accounts[target_email]["token"] = new_token
                save_accounts(self.accounts)
                self._refresh_usage()
                self._update_display()
                rumps.notification(
                    "Claude Switcher",
                    f"Switched to {target_email}",
                    "Token refreshed. Ready to use.",
                )
                return

        # Refresh failed — switch back to previous account
        prev = self.accounts.get(prev_email)
        if prev:
            write_keychain_token(prev["token"])
            write_oauth_account(prev["oauth"])
            self.current_email = prev_email
        save_accounts(self.accounts)
        self._refresh_usage()
        self._update_display()
        rumps.alert(
            "Token Expired",
            f"Token for {target_email} is expired.\n"
            f"Switched back to {prev_email}.\n\n"
            "To fix: run 'claude login' with that account,\n"
            "then click 'Add Current Account'.",
        )

    @rumps.clicked("Add Current Account")
    def add_current(self, _):
        self._detect_current()
        save_accounts(self.accounts)
        self._update_display()
        rumps.notification(
            "Claude Switcher",
            f"Saved: {self.current_email}",
            f"Total accounts: {len(self.accounts)}",
        )

    @rumps.clicked("Refresh Usage")
    def refresh(self, _):
        threading.Thread(target=self._refresh_usage, daemon=True).start()

    @rumps.clicked("Quit")
    def quit_app(self, _):
        rumps.quit_application()


if __name__ == "__main__":
    ClaudeSwitcherApp().run()
