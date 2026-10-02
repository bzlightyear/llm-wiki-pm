# Wiki-Search Launchd Guide

created: 2026-10-02

How this install runs the wiki-search MCP as one shared server under launchd,
instead of one copy per Claude Code session: the setup, how wikis are chosen,
restarts, troubleshooting, rollback, and adding a second wiki. Set up for NW5;
the reasoning and tests are in the
[NW5 Shared Wiki-Search Analysis](nw5-shared-wiki-search-analysis.md).

Companion to the [Wiki Path Launchd Guide](wiki-path-launchd-guide.md), which
sets `WIKI_PATH` for apps launched from the Dock or Finder.

## How it fits together

- **One server per wiki.** A LaunchAgent starts `hooks/wiki-search.sh` at
  login in SSE mode. It serves one wiki on a local port and keeps running.
- **Sessions connect to it.** The user-scope `wiki-search` entry in
  `~/.claude.json` points at the server's URL with a bearer token. Every
  session in every project connects to the same server, and reconnects on its
  own after the server restarts.
- **The server name stays `wiki-search`,** so tool names
  (`mcp__wiki-search__*`), the permission rules in `~/.claude/settings.json`
  and the hook matchers are unchanged.
- **The default wiki is `$WIKI_PATH`.** Skills, hooks and workers use it in any
  project without a `.wiki-path` file. A `.wiki-path` is only for a project
  that uses another wiki (see "Adding a second wiki").
- **The default is set in two places.** `$WIKI_PATH` (from
  `local.wiki-path-env.plist` and `~/.zshenv`) for skills and hooks, and
  `WIKI_PATH` plus `WorkingDirectory` in `local.wiki-search.plist` for the
  server. To change the default wiki, change both.

## Setup

**1. The LaunchAgent,** `~/Library/LaunchAgents/local.wiki-search.plist`,
mode 600 because it holds the token. Paths are absolute, because launchd
doesn't expand `~`. `PATH` must include Homebrew's `/opt/homebrew/bin`:
`wiki-search.sh`'s own fallback list for `node` doesn't, and launchd's default
`PATH` is only `/usr/bin:/bin:/usr/sbin:/sbin`.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>local.wiki-search</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/sh</string>
    <string>/Users/pgoubert/Projects/llm-wiki-pm/hooks/wiki-search.sh</string>
  </array>
  <key>WorkingDirectory</key><string>/Users/pgoubert/Projects/pm-wiki</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>WIKI_PATH</key><string>/Users/pgoubert/Projects/pm-wiki</string>
    <key>MCP_TRANSPORT_TYPE</key><string>sse</string>
    <key>PORT</key><string>3100</string>
    <key>HOST_BIND_ADDRESS</key><string>127.0.0.1</string>
    <key>MCP_AUTH_TOKEN</key><string>TOKEN</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/Users/pgoubert/Library/Logs/wiki-search.log</string>
  <key>StandardErrorPath</key><string>/Users/pgoubert/Library/Logs/wiki-search.log</string>
</dict>
</plist>
```

`TOKEN` stands for a random value, generated straight into the file so it is
never printed: write the plist with the placeholder, then run:

```bash
/usr/libexec/PlistBuddy -c "Set :EnvironmentVariables:MCP_AUTH_TOKEN $(openssl rand -hex 32)" ~/Library/LaunchAgents/local.wiki-search.plist && chmod 600 ~/Library/LaunchAgents/local.wiki-search.plist
```

**2. Start it:**

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/local.wiki-search.plist
```

The log should end with `Bearer auth: enabled` and `SSE transport listening on
http://127.0.0.1:3100/sse`.

**3. Point Claude Code at it.** The token is read from the plist inside the
command, so it isn't printed or kept in shell history:

```bash
claude mcp remove -s user wiki-search && claude mcp add -s user -t sse wiki-search http://127.0.0.1:3100/sse -H "Authorization: Bearer $(/usr/libexec/PlistBuddy -c 'Print :EnvironmentVariables:MCP_AUTH_TOKEN' ~/Library/LaunchAgents/local.wiki-search.plist)"
```

`claude mcp list` should show `wiki-search: http://127.0.0.1:3100/sse (SSE) -
✔ Connected`. Sessions opened before the switch keep their own copy of the
server until they close.

## Checking it

- Running, with launchd as its parent: `launchctl print gui/$(id -u)/local.wiki-search`
  shows `state = running`.
- One server: `pgrep -fl mcp-markdown-vault` lists one process, plus one per
  session still open from before the switch.
- Auth: `curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3100/sse`
  prints `401`.

## Restarting

Restart after upgrading `@wirux/mcp-markdown-vault`, changing
`wiki-search.sh`, editing the plist's environment, or switching to a fork
build of the MCP (NW2):

```bash
launchctl kickstart -k gui/$(id -u)/local.wiki-search
```

Open sessions reconnect on their own. A changed plist needs `launchctl bootout
gui/$(id -u)/local.wiki-search` and then the `bootstrap` command again, because
`kickstart` reuses the loaded copy.

## Known limits

- **Backlinks go stale while the server runs.** The MCP maps page names to
  files once, at startup. Pages created or renamed after that get no backlinks
  from `view(action=backlinks)` until `system(action=reindex)` (about 2.5
  minutes) or a restart. Search isn't affected. Use `backlinks.py` for link
  searches (NW7).
- **SSE only.** The MCP offers stdio and SSE, and SSE is deprecated in the MCP
  spec. If Claude Code drops SSE, the server needs streamable HTTP, which would
  go in NW2's fork.

## Troubleshooting

- **Sessions show wiki-search as failed.** Check `launchctl print` and the
  log, `~/Library/Logs/wiki-search.log`. A session that started while the
  server was down picks the tools up once it's back.
- **"node not found" in the log.** The plist's `PATH` doesn't include the
  directory `node` is in (`command -v node` in a terminal).
- **The log repeats a startup error every 10 seconds.** `KeepAlive` restarts a
  server that fails at startup. For "Corrupted vector index" or "incompatible"
  index errors, delete the wiki's `.markdown_vault_mcp/` folder and restart.
  The index rebuilds in the background.
- **The log grows.** It holds startup lines and errors only. Truncate it if
  needed.

## Rollback

Back to one server per session:

```bash
launchctl bootout gui/$(id -u)/local.wiki-search; rm ~/Library/LaunchAgents/local.wiki-search.plist; claude mcp remove -s user wiki-search && claude mcp add -s user wiki-search -- sh /Users/pgoubert/Projects/llm-wiki-pm/hooks/wiki-search.sh
```

Then restart open sessions. Per-session copies resolve their wiki from the
session's `.wiki-path` or `WIKI_PATH`, as before.

## Adding a second wiki

Each wiki gets its own shared server, and each project is bound to one wiki.

1. **A second LaunchAgent.** Copy the plist to a new label (for example
   `local.wiki-search-<name>.plist`) and change `Label`, `WorkingDirectory`,
   `WIKI_PATH` and the log path to the new wiki. Give it its own `PORT` (for
   example 3101) and its own token. Start it with `launchctl bootstrap`. It
   runs all the time, at about 600 MB.
2. **In each project that uses it,** two settings:
   - a `.wiki-path` naming the wiki, which steers the skills, hooks and workers;
   - a local `wiki-search` entry pointing at its server, which steers the MCP:

     ```bash
     claude mcp add -s local -t sse wiki-search http://127.0.0.1:3101/sse -H "Authorization: Bearer $(/usr/libexec/PlistBuddy -c 'Print :EnvironmentVariables:MCP_AUTH_TOKEN' ~/Library/LaunchAgents/local.wiki-search-<name>.plist)"
     ```

   A local entry is stored in `~/.claude.json` under the project's folder path,
   not in the project, and overrides the user-scope entry there. Keeping the
   name `wiki-search` keeps the tool names, permission rules and hooks
   unchanged. Moving or renaming the project folder leaves the entry behind.
   A project-scope `.mcp.json` in the project's root works the same way and
   travels with the folder.
3. **Keep both settings together.** A `.wiki-path` without the entry sends
   skills and hooks to the second wiki while the MCP still serves the default
   one, and an MCP write lands in the wrong wiki. That a local entry overrides
   the user-scope one is Claude Code's documented order. It was tested with a
   project-scope entry, not a local one, so check `claude mcp list` in the
   project.

**Possible follow-on in the fork:** set-wiki-path writes both settings, and
session start warns when a project's `.wiki-path` names a wiki other than
`$WIKI_PATH` and the project has no local `wiki-search` entry.
