# Claude Switcher

Lightweight macOS menu bar app to switch between multiple Claude Code Max accounts.

Swaps **only** Keychain token + `oauthAccount` — does NOT touch MCP servers, settings, memory, or CLAUDE.md.

## Features

- Menu bar icon showing weekly usage %
- One-click account switching
- Usage dashboard (5h session + weekly limit)
- Auto-refresh every 5 minutes
- Auto-start on login

## Screenshot

```
┌─────────────────────────┐
│ CC 86%            ▼     │
├─────────────────────────┤
│ Active: user@email.com  │
│─────────────────────────│
│ Session (5h): 2%        │
│ Weekly: 86%             │
│ Reset: 2026-06-03T03:00 │
│─────────────────────────│
│ Switch Account      ⌘S  │
│─────────────────────────│
│ ▸ Accounts              │
│─────────────────────────│
│ Add Current Account     │
│ Refresh Usage           │
│─────────────────────────│
│ Quit                    │
└─────────────────────────┘
```

## Install

```bash
git clone https://github.com/meganechan/claude-switcher.git
cd claude-switcher
chmod +x install.sh
./install.sh
```

## Usage

### Add accounts

1. Login to Claude Code with account A: `claude login`
2. Click **"Add Current Account"** in menu bar
3. Logout and login with account B: `claude logout && claude login`
4. Click **"Add Current Account"** again
5. Now switch between them via **"Switch Account"**

### What gets swapped

| Swapped | NOT touched |
|---------|-------------|
| Keychain OAuth token | `~/.claude/settings.json` |
| `oauthAccount` in `~/.claude.json` | `~/.claude/memory/` |
| | `~/.claude/projects/` |
| | MCP servers config |
| | CLAUDE.md files |

## Uninstall

```bash
./uninstall.sh
```

## How it works

- Reads/writes Claude Code credentials via macOS `security` CLI (Keychain)
- Reads/writes only the `oauthAccount` block in `~/.claude.json`
- Fetches usage from `api.anthropic.com/api/oauth/usage` (official API)
- No telemetry, no analytics, no external servers
- Account backups stored locally at `~/.claude-switcher/accounts.json`

## Requirements

- macOS 12+
- Python 3.9+
- Claude Code CLI installed

## License

MIT
