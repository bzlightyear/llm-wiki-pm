# Fixing WIKI_PATH via launchd

## Problem

The llm-wiki-pm plugin's `session-start.sh` hook resolves the wiki location in
this priority order:

1. `.wiki-path` file in the current working directory
2. `CLAUDE_PLUGIN_OPTION_wiki_path` (set via the plugin's own config)
3. `$WIKI_PATH` environment variable
4. Falls back to `$(pwd)` if none of the above are set

None of the first two were configured, and although `WIKI_PATH` is exported in
`~/.zshenv`, the hook process never saw it — so it fell back to whatever
directory the session happened to start in. This produced stray `queries/` and
`_status.md` scaffolding in `~` and later in this project directory
(`/Users/pgoubert/Projects/llm-wiki-pm`), instead of the real wiki at
`/Users/pgoubert/Projects/pm-wiki`.

## Root cause

`.zshenv` is sourced by every zsh invocation, but only if the process that
launches Claude Code is itself a zsh process (interactive or not). If Claude
Code is instead launched via Dock, Finder, Spotlight, or some other non-shell
launcher, it inherits macOS's per-user `launchd` environment instead — which
never sources any shell rc file. That mismatch is almost certainly why
`$WIKI_PATH` wasn't visible to the hook even though it's visible in an
interactive terminal.

## Fix: set the variable in the launchd environment

Setting `WIKI_PATH` via `launchctl setenv` puts it in the environment that
launchd hands to every process it spawns — GUI apps included — independent of
which shell (if any) actually launches Claude Code.

### Step 1 — set it now (session-only)

```bash
launchctl setenv WIKI_PATH "$HOME/Projects/pm-wiki"
```

This takes effect immediately for anything launched *after* this command, but:
- it does **not** persist across logout/reboot
- it does **not** affect an already-running Claude Code process — quit and
  relaunch it after running this

### Step 2 — make it persist across reboots

Create a LaunchAgent that re-runs `launchctl setenv` at every login:

```bash
cat > ~/Library/LaunchAgents/local.wiki-path-env.plist <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>local.wiki-path-env</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/launchctl</string>
    <string>setenv</string>
    <string>WIKI_PATH</string>
    <string>/Users/pgoubert/Projects/pm-wiki</string>
  </array>
  <key>RunAtLoad</key><true/>
</dict>
</plist>
EOF
launchctl load ~/Library/LaunchAgents/local.wiki-path-env.plist
```

`RunAtLoad` means this fires once per login session, re-applying the
`launchctl setenv` call before any GUI apps (including Claude Code) get
launched.

### Verifying it worked

After running Step 1 (or logging back in after Step 2), relaunch Claude Code
and check the SessionStart hook's reported wiki path — it should now read
`Wiki at /Users/pgoubert/Projects/pm-wiki` instead of falling back to the
session's working directory.

To check the launchd value directly from a shell at any time:

```bash
launchctl getenv WIKI_PATH
```

## Alternative / belt-and-suspenders option (not covered in depth here)

The plugin also supports a `wiki_path` option in its own `userConfig`
(`plugin.json`), injected as `CLAUDE_PLUGIN_OPTION_wiki_path` — this is set by
Claude Code itself, not the OS environment, so it's immune to this whole
launch-environment problem. It wasn't found configured anywhere under
`~/.claude` at the time of writing. Reconfiguring it requires an interactive
Claude Code session (re-running the plugin's enable/config flow) and is a
reasonable next step if `launchctl setenv` proves unreliable.
