# NW5 Shared Wiki-Search Analysis

created: 2026-10-01

The analysis NW5 asks for: how to serve the wiki through one wiki-search server
that every Claude Code project can read and update, instead of one server per
session. It checks NW5's claims against the MCP's code and live tests on a
scratch copy of the wiki, compares the options, and recommends one. A second
wiki is covered as a nice-to-have.

revised on: 2026-10-02
Recorded the decisions (all six recommendations in section 10 accepted), added
the implementation plan with `$WIKI_PATH` as the default wiki (section 11), and
recorded its results (section 12).

Status: implemented 2026-10-02 (section 12). In the
[llm-wiki-pm Fork Backlog](llm-wiki-pm-fork-backlog.md), this closes NW5. The
setup is documented in the [Wiki-Search Launchd Guide](wiki-search-launchd-guide.md).

Companion to the [llm-wiki-pm Fork Backlog](llm-wiki-pm-fork-backlog.md) (NW5),
[Wiki-Search MCP Tools Analysis](wiki-search-mcp-tools-analysis.md),
[NW6 Page Name Resolution Analysis](nw6-page-name-resolution-analysis.md) and
the [Wiki Path Launchd Guide](wiki-path-launchd-guide.md).

Scope is NW5 only. NW2 and NW7 were read for how they interact with it.
Section 9 notes the interactions, without designing anything for them.

---

## 1. Summary

- **NW5's proposal works, with two changes.** One wiki-search server running in
  SSE mode served two clients at once on a scratch copy of the wiki. They shared
  one vault, index and embedder, and each had its own workflow state. A write
  from one client was readable from the other. A scratch Claude Code session
  connected to it with a bearer-token header. The tool names stayed
  `mcp__wiki-search__*`, so the `deny` rule still removed `edit`, the `ask` rule
  still gated `vault`, and `pre-write.sh` still fired on a `vault` write.
- **Change 1: the LaunchAgent must set `PATH`.** Under launchd's default `PATH`,
  `wiki-search.sh` exits with "node not found". This machine's `node` is
  Homebrew's `/opt/homebrew/bin/node`, which isn't in the launcher's fallback
  list. A Claude Code session passes its own `PATH`, which hides the gap today.
- **Change 2: set the vault through the working directory, not `WIKI_PATH`.**
  `wiki-search.sh` reads `.wiki-path` in its working directory before it reads
  `WIKI_PATH`. pm-wiki's own `.wiki-path` names pm-wiki, so a pm-wiki working
  directory fixes the vault. It doesn't depend on whether
  `local.wiki-path-env.plist` has run first at login.
- **Claude Code handles outages.** It reconnected without a visible error when
  the server was killed and restarted mid-session. A session that started while
  the server was down reported `failed`, then picked up the tools on its own
  once the server came up.
- **One real cost: backlinks on a long-running server go stale.** The MCP builds
  its page-name map once, at startup, and only `system(action=reindex)` rebuilds
  it (about 2.5 minutes on the scratch copy). Pages created or renamed while it
  runs get no backlinks. Search isn't affected, because the file watcher
  re-embeds changed files. Today each session's server restarts with the
  session. A shared one could run for weeks. Agents use `backlinks.py`, not the
  MCP's lookup (NW6 analysis), so the practical impact is small.
- **Running several copies has a hidden risk that the shared server removes.**
  Every copy rewrites the whole vector index (about 18 MB) every 60 seconds,
  whether or not anything changed, through temp files with fixed names. Two
  copies saving at the same moment could leave an `index.json` and a
  `vectors.bin` from different processes. This comes from reading the code and
  wasn't observed.
- **Transport:** the package (2.3.0, still the latest on npm) only offers stdio
  and SSE. The MCP spec has deprecated SSE in favour of streamable HTTP, but
  Claude Code 2.1.285 supports SSE with headers, and that's what was tested.
- **Second wiki:** a project of a second wiki can carry a local-scope entry,
  also named `wiki-search`, pointing at that wiki's own server. A test showed a
  project-level entry replaces the user-scope one with the same name, so tool
  names, rules and hooks stay unchanged. The primary setup doesn't rule this
  out, and none of it has to be built now.

## 2. Goal

- **Primary:** one wiki-search server serves pm-wiki to every Claude Code
  project, for reading and updating it. No project or session starts its own.
- **Secondary, nice to have:** llm-wiki-pm can maintain a second wiki, chosen by
  `.wiki-path` or `$WIKI_PATH`, served by its own single server. This must not
  complicate the primary solution.

## 3. How it works today

- **Registration.** `~/.claude.json` registers `wiki-search` at user scope as a
  stdio server: `sh ~/Projects/llm-wiki-pm/hooks/wiki-search.sh`. No project has
  its own entry. The llm-wiki-pm marketplace plugin isn't enabled, so its
  manifest's `plugin_llm-wiki-pm_wiki-search` server doesn't start.
- **Lifecycle.** Claude Code starts one copy per session at session start and
  stops it with the session. `session-start.sh` doesn't start the server. Its
  npx step only warms the package cache when it's missing (`session-start.sh:37-48`).
- **Vault resolution.** `wiki-search.sh:13-14` sets `VAULT_PATH` from
  `.wiki-path` in the working directory, then `CLAUDE_PLUGIN_OPTION_wiki_path`,
  then `WIKI_PATH`, then the working directory itself. The write hooks use the
  same order, except that they skip the last fallback (`pre-write.sh:18-20`). So
  for an MCP write, the hook and the server agree on the wiki whenever one is
  configured.
- **Where the wiki is configured.** There are 14 `.wiki-path` files: 13 projects
  and `~`. All name pm-wiki. launchd's `WIKI_PATH` is also pm-wiki.
- **Cost per copy.** This session's copy used 610 MB of resident memory. The
  scratch server used 566 MB right after startup. Most of that is the
  in-process embedding model and the loaded index (6,417 chunks).
- **Leftover from the working-directory fallback.** The fork repo has a
  `.markdown_vault_mcp/` index from 2026-09-01, made by a session that ran
  before this repo had a `.wiki-path`. It's git-ignored and harmless.

## 4. NW5's claims, checked

| Claim | Result | Evidence |
|---|---|---|
| Every session starts its own copy | Confirmed by design: user-scope stdio entry. 1 copy was running at the time of checking. | `~/.claude.json`; `ps` |
| About 580 MB per copy | Confirmed: 566–610 MB | `ps -o rss` |
| Each copy writes the same index | Confirmed, and worse than stated: a full rewrite every 60 s even when idle | `index.js:194-196`, `persisted-flat-vector-store.js:63-108`; index mtime advancing with no edits |
| `MCP_TRANSPORT_TYPE=sse` gives a multi-client server with shared vault, index and embedder | Confirmed | `transport.js` (`createSseApp`), `index.js:61-73`; two-client test |
| Workflow state is per client | Confirmed | `index.js:65` creates a `WorkflowStateMachine` per connection; test: client A moved to `exploring`, client B stayed `idle` |
| `PORT`, `HOST_BIND_ADDRESS` settable | Confirmed; defaults are 3000 and 127.0.0.1 | `index.js:113-115` |
| `MCP_AUTH_TOKEN` checks a bearer token | Confirmed on every route (`app.use`), compared in constant time. No token: 401 on `GET /sse` and on `POST /messages`. | `auth-middleware.js`; curl |
| `claude mcp add --transport sse … -H "Authorization: Bearer …"` works | Confirmed: `-t sse` and `-H` exist, and a session connected with the header | `claude mcp add --help`; scratch session |
| Server name kept, so rules and matchers unchanged | Confirmed: tools appear as `mcp__wiki-search__*` | scratch session init |
| Exposure to web pages through DNS rebinding | Mostly already blocked: the server rejects any request whose `Origin` isn't localhost, before the token check. A foreign `Origin` got a 500 even with a valid token. Browsers send `Origin` on POST, so a rebound page can't send tool calls. That browsers do so wasn't tested here. | `transport.js:13-35`; curl |
| Upgrades need `launchctl kickstart -k` | Correct | — |
| Sessions may need to reconnect after a restart | Not needed: Claude Code reconnected without a visible error | restart test |

## 5. Tests

All tests ran on a scratch copy of the wiki (841 markdown files, its index
copied too) with a scratch server on port 3199. The live wiki and its index
were not touched.

1. **Two clients, one server.** Both connected with the token. Client A created
   a page and client B read it back. Workflow state stayed separate.
2. **Claude Code over SSE.** A `claude -p` session using `--strict-mcp-config`
   connected with the header and called `view`. The `deny` rule hid `edit`
   entirely. A `vault` update was blocked by the `ask` rule, even with
   `--allowedTools`. `pre-write.sh` fired first, took its `_archive/` snapshot
   and showed its freshness reminder. `post-validate.sh` uses the same
   tool-name matcher. It didn't run because the write was refused, so it's
   covered by the matcher, not by the test.
3. **Restart mid-session.** The server was killed while the session waited and
   was back about 11 s later. The session's next read worked, with no error.
4. **Server down at session start.** The session reported `failed`
   (`ECONNREFUSED`). The server started after the session did, and within 45 s
   the tools showed up and a read worked.
5. **New page, long-running server.** A page and a link to it, written as plain
   files: backlinks stayed at 0 until `reindex`, and then for another 140 s
   while it ran.
6. **Launcher under launchd's environment.** `env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin`,
   working directory `/`: "wiki-search: node not found on PATH or common
   locations".
7. **A project-level entry with the same name.** A scratch project's `.mcp.json`
   defining `wiki-search` as SSE replaced the user-scope stdio entry. Only one
   `wiki-search` was loaded (`source: project`), and no stdio copy started.

Startup is quick: the restarted server was listening in about a second,
loading the saved index. It re-embeds files that changed since the last save in
the background.

## 6. Options for the primary goal

**A. NW5's proposal, amended.** A LaunchAgent runs `wiki-search.sh` at login in
SSE mode, with `KeepAlive`. The user-scope entry points at its URL with a bearer
token. Amendments: `EnvironmentVariables` includes a `PATH` with
`/opt/homebrew/bin`, and `WorkingDirectory` is pm-wiki.

**B. An on-demand shared server behind a stdio launcher.** The user-scope entry
stays stdio, but runs a small client launcher. The launcher resolves the
session's wiki the way the hooks do, starts that wiki's server if none is
running, and relays stdio to it over SSE (an npm bridge such as `mcp-remote`, or
a small Node script on the SDK).

**C. Keep a server per session, but lighter.** Point each copy at a shared
Ollama embedder (`OLLAMA_URL`), so the model isn't loaded into every copy.

**D. Register the server only in wiki projects.** Project or local scope
instead of user scope.

| | A | B | C | D |
|---|---|---|---|---|
| Server processes | 1 | 1 per wiki, plus a relay per session | 1 per session | 1 per session in wiki projects |
| Memory with N sessions | about 0.6 GB | about 0.6 GB plus N relays (size not measured) | N copies, each smaller (amount not measured) | same as today: all 13 projects use the wiki |
| Index save race | gone | gone | stays | stays |
| Second wiki | by hand (section 7) | automatic | automatic, as today | automatic, as today |
| Server and write hooks agree on the wiki | yes for pm-wiki. A second wiki needs care (section 7). | yes, by construction | yes | yes |
| New code to own | none: a plist and one config entry | launcher, start lock, relay, token handling, tests, all in the always-on hook path | none, but an Ollama install and service | none |
| Fork change | none required | yes | small | none |
| Backlink staleness | yes, for as long as the server runs | yes, for as long as the server runs | no | no |

**Recommendation: A.** It meets the primary goal with no new code, and is easy
to undo by putting the stdio entry back. B is the general answer, but it means
owning a launcher, a relay and lifecycle code in the path every session
depends on, for a second wiki that isn't needed yet. C keeps N processes and
the save race. D doesn't reduce anything, because every project uses the wiki.

### What A doesn't fix

- **Backlink staleness** (section 5, test 5). Options: accept it, because
  `backlinks.py` is the documented link search and NW7 is pointing the docs at
  it; or add a nightly restart (a second LaunchAgent running
  `launchctl kickstart -k`). Renames already follow the NW6 procedure, which
  reindexes.
- **The SSE deprecation.** If Claude Code drops SSE, the server needs
  streamable HTTP, which the package doesn't offer. The SDK it bundles (1.30)
  does, so that would be a small change in NW2's fork.
- **A fixed vault.** Every session reaches pm-wiki, whatever its `.wiki-path`
  says. That's the goal today, and section 7 covers a second wiki.
- **The plugin manifest.** It keeps its per-session stdio server for plugin
  installs. This install doesn't use it.

### Costs of A

- **Security.** A localhost port can be reached by other local processes, and
  by other accounts on the machine. A stdio copy can't be. The Origin check
  already blocks web pages. Any process running as this user can read the vault
  files directly anyway, so the token mainly guards against other accounts and
  against processes that have network access but no file access. Recommended
  anyway, because it costs one setting on each side. The token would live in
  the plist (made `chmod 600`) and in `~/.claude.json` (already 600).
- **Restarts.** An npm package upgrade, a switch to NW2's fork build, or a
  change to `wiki-search.sh` needs `launchctl kickstart -k`. Open sessions
  recover on their own (test 3).
- **Crash loops.** If startup fails (for example a corrupted index),
  `KeepAlive` restarts the server every 10 s and fills the log. The log path
  and the fix (delete `.markdown_vault_mcp/` and restart) go in the guide.
- **One more piece of local setup** to remember on a new machine. It's
  documented the same way as `local.wiki-path-env.plist`.

## 7. A second wiki

The difficulty: `.wiki-path` is per project, but a user-scope entry has one
fixed URL. The write hooks join an MCP write's vault-relative path onto the
session's wiki (`pre-write.sh:45-55`). If the session's wiki and the server's
vault ever differ, a snapshot is taken in the wrong wiki.

| Option | How | Cost on top of A | Verdict |
|---|---|---|---|
| **7a. Same name, local scope** | A second LaunchAgent on its own port (for example 3101), with the second wiki as its working directory. Each project of that wiki gets `claude mcp add -s local -t sse wiki-search http://127.0.0.1:3101/sse -H …`, which overrides the user-scope entry (test 7). | A copied plist, and one command per project. A project's `.wiki-path` and its entry must name the same wiki, so that's two settings to keep together. The set-wiki-path skill could write both later. | **Recommended if it's ever needed.** Tool names, rules and hooks unchanged. |
| 7b. A second server name | A user-scope entry such as `wiki2-wiki-search`. | Every session sees both servers' tools, and an agent can write to the wrong wiki. The hooks would join paths onto the session's wiki, not the server's. The D9 rules need new exact names. | Rejected. |
| 7c. Option B's launcher | Starts the right server automatically. | Option B's costs. | Worth it only if several wikis become normal. |

Choosing A doesn't block 7a or 7c. Nothing for the second wiki needs building
now.

## 8. Effects on the fork

- **No fork change is needed for A.** The plist and the `~/.claude.json` entry
  are local setup.
- **Optional:** add `/opt/homebrew/bin/node` to `wiki-search.sh`'s fallback list
  (`wiki-search.sh:22-28`). The plist's `PATH` makes it unnecessary here, but
  Homebrew on Apple Silicon is a common setup the list misses. It's one line,
  covered by a launcher test, and would be fine to offer upstream.
- **Docs:** a short guide in `fork-chgs/`, like the launchd guide, recording the
  plist, the entry, the restart command and the rollback.

## 9. Interactions with other backlog items

- **NW2 (fork the MCP):** a fork build means repointing the plist and
  restarting. The #45 fix (orphaned server processes) matters less, because
  sessions no longer start servers. If SSE support is ever dropped, the fork is
  where streamable HTTP would go.
- **NW7 (link search):** the backlink staleness above adds to NW7's case for
  naming `backlinks.py` as the link search. NW7's note that a running server
  misses renamed pages applies to the one shared server for longer, but only to
  one server instead of one per session.
- **NW6:** its procedure's step "reindex every running wiki-search server"
  becomes one server.

## 10. Decisions

All six recommendations were accepted on 2026-10-02.

1. **Option A, amended as above.** Recommended.
2. **Bearer token.** Recommended: yes, a random token in a `chmod 600` plist
   and in the user-scope entry's header.
3. **Backlink staleness.** Recommended: accept it for now, since agents use
   `backlinks.py`. Revisit with NW7. The alternative is a nightly restart
   agent.
4. **Port.** Recommended: 3100, as NW5 proposed (3000 is a common dev-server
   port, and 3100 is free).
5. **The launcher's Homebrew fallback (section 8).** Recommended: set `PATH` in
   the plist now. Adding the fork line is optional, and isn't needed for NW5.
6. **Second wiki.** Recommended: build nothing now. Record 7a in the guide as
   the way to add one.

## 11. Implementation plan

Option A, with a token, port 3100, `PATH` and `WIKI_PATH` set in the plist, no
fork line, and no second-wiki build. Two changes were added after the
decisions, on 2026-10-02:

- **`$WIKI_PATH` is the default wiki.** The projects' `.wiki-path` files are
  removed, so any project without one, including a new one, uses pm-wiki. A
  `.wiki-path` now only marks a project that uses another wiki.
- **A second wiki follows 7a.** Its own background server, plus a local
  `wiki-search` entry in each of its projects. Such a project needs both its
  `.wiki-path` and that entry, because `.wiki-path` only steers the skills and
  hooks, not which server a session connects to (section 7). Having
  set-wiki-path write both, with a session-start warning when they disagree, is
  a follow-on for when a second wiki is started.

**Who runs each step.** Steps 1, 2, 4 and 8 write user-level config or files
in other projects. I show each change first. If this session isn't allowed to
make it, I give you the exact command and wait.

**The token never appears in chat, docs or git.** Step 1 generates it straight
into the plist, and step 4 reads it from there.

**Transition window.** From step 2 until the old sessions are closed in step 5,
the shared server and each open session's stdio copy all save the same index
(section 4). Steps 2–5 should run back to back.

| Step | Change | Verify | Roll back | Who |
|---|---|---|---|---|
| 1. Write the plist | Create `~/Library/LaunchAgents/local.wiki-search.plist` (below), `chmod 600` | `plutil -lint` passes; mode `-rw-------`; port 3100 still free | `rm` the plist | me, or you |
| 2. Start the server | `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/local.wiki-search.plist` | step 3 | `launchctl bootout gui/$(id -u)/local.wiki-search` | me, or you |
| 3. Check the server | none | `launchctl print` shows it running; the log shows `SSE transport listening on http://127.0.0.1:3100/sse` and `Bearer auth: enabled`; its parent is launchd and it runs the cached `index.js`, not npx; its `VAULT_PATH` is pm-wiki; curl gets 401 without the token and an `endpoint` event with it | — | me |
| 4. Switch the user-scope entry | Replace the stdio entry with the SSE one (below) | `~/.claude.json`'s user-scope `wiki-search` is `type: sse`, URL `http://127.0.0.1:3100/sse`, with an `Authorization` header (checked without printing the value); `claude mcp list` shows it connected | re-add the stdio entry (below) | you, or me after showing it |
| 5. Smoke test | none | below | full rollback | you open sessions, I check |
| 6. Restart test | `launchctl kickstart -k gui/$(id -u)/local.wiki-search` | the smoke-test session's next wiki-search read works, with no reconnect by hand | — | me |
| 7. Quiet session-start's "global wiki path" message | Fork change (below), with a test | full test suite passes; a session in a project without `.wiki-path` shows `Wiki at …/pm-wiki` and no message | `git revert` | me |
| 8. Remove the `.wiki-path` files | Delete the 14 files (below) | below | recreate them: each held the pm-wiki path | me, after you approve the list |
| 9. Docs and close-out | see below | doc review; you approve the diff | `git restore` | me |

**The plist (step 1).** Absolute paths, because launchd doesn't expand `~`.
`WIKI_PATH` and the working directory both name pm-wiki, so the vault doesn't
depend on any `.wiki-path` file or on login order.

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
    <key>MCP_AUTH_TOKEN</key><string><!-- generated: openssl rand -hex 32 --></string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/Users/pgoubert/Library/Logs/wiki-search.log</string>
  <key>StandardErrorPath</key><string>/Users/pgoubert/Library/Logs/wiki-search.log</string>
</dict>
</plist>
```

**The entry (step 4).** The token is read from the plist inside the command,
so it isn't printed or kept in shell history:

```bash
claude mcp remove -s user wiki-search && claude mcp add -s user -t sse wiki-search http://127.0.0.1:3100/sse -H "Authorization: Bearer $(/usr/libexec/PlistBuddy -c 'Print :EnvironmentVariables:MCP_AUTH_TOKEN' ~/Library/LaunchAgents/local.wiki-search.plist)"
```

**The smoke test (step 5).**
1. Close every other Claude Code session, in the desktop app and in
   terminals, so they drop their stdio copies. This session keeps its own copy
   until it ends.
2. Open a new session in a project unrelated to the wiki. One without a
   `.wiki-path` also exercises the hooks' `WIKI_PATH` fallback. In it:
   - `/mcp` shows `wiki-search` connected over SSE.
   - Have it read a page with `view`.
   - Have it create `queries/nw5-smoke-test.md` with `vault` (approve the
     `ask` prompt), read it back with `view`, then delete it with `vault`.
3. Open a second new session in another project and have it read a page.
4. I check:
   - Exactly one `mcp-markdown-vault` process has launchd as its parent. The
     only other one is this session's own copy.
   - The test page is gone. I remove the `_archive/` snapshot the delete left.
     pm-wiki's `git status` then shows only `_status.md`.
5. At your next login, the first session's `/mcp` shows `wiki-search`
   connected. This can't be checked in this session.

**The session-start change (step 7).** `session-start.sh:33-34` adds "using
global wiki path … Run /llm-wiki-pm:set-wiki-path … to set a project-specific
path" to every session in a project without `.wiki-path`. Under the new model
that's the normal case, so the branch is removed. The warning for no wiki path
configured at all (`session-start.sh:30-32`) stays. The new test, in a new
test file, runs the hook with `WIKI_PATH` set and no `.wiki-path`, and checks
that the output names the wiki and doesn't mention set-wiki-path. The existing
unconfigured-path test (`test_hooks.py:429-460`) keeps covering the other
warning. This changes upstream behavior, so it's recorded in the
[llm-wiki-pm Fork Changelog](llm-wiki-pm-fork-changelog.md) as PATCH-17 and
isn't offered upstream: upstream treats `.wiki-path` as the main setting.

**Removing the `.wiki-path` files (step 8).** Done after the smoke test.
- **Before:** every session that should reach pm-wiki must see `$WIKI_PATH`.
  Desktop sessions get it from `local.wiki-path-env.plist`, and terminal
  sessions from `~/.zshenv`. I check each scheduled task's last run for the
  session-start line `Wiki at …/pm-wiki`. A task that doesn't show it keeps
  its project's file until that's fixed.
- **The files,** all naming pm-wiki:
  - 10 outside any git repo, in `~` and 9 project folders: delete them.
  - 3 git-ignored, in llm-wiki-pm and two docs projects: delete them.
  - 1 tracked, pm-wiki's own: `git rm` it and commit in pm-wiki, excluding
    `_status.md`. This also ends the hazard of wiki copies inheriting a path
    back to the live wiki.
- **Verify:** none of the 14 remain. A new session in llm-wiki-pm and one in
  pm-wiki each show `Wiki at …/pm-wiki` and no warning. The shared server is
  unaffected, because its plist sets `WIKI_PATH`.

**Full rollback.**

```bash
launchctl bootout gui/$(id -u)/local.wiki-search; rm ~/Library/LaunchAgents/local.wiki-search.plist; claude mcp remove -s user wiki-search && claude mcp add -s user wiki-search -- sh /Users/pgoubert/Projects/llm-wiki-pm/hooks/wiki-search.sh
```

Then restart open sessions. Steps 7 and 8 don't depend on the shared server,
so they can stay in place after a rollback.

**Step 9, docs and close-out:**
- New `fork-chgs/wiki-search-launchd-guide.md`, a companion to the
  [Wiki Path Launchd Guide](wiki-path-launchd-guide.md). It covers:
  - the plist (token shown as a placeholder) and the entry command;
  - `$WIKI_PATH` as the default wiki, and `.wiki-path` only for projects using
    another wiki;
  - restarting after an upgrade or a launcher change;
  - the log, and the crash-loop fix (delete `.markdown_vault_mcp/` and
    restart);
  - the rollback;
  - adding a wiki (7a): a copied plist with its own port, token, `WIKI_PATH`
    and working directory, then `.wiki-path` plus a local `wiki-search` entry
    in each of its projects. It also notes that the default wiki is set in two
    places (`$WIKI_PATH` and the plist), and the set-wiki-path follow-on.
- This doc: status changed to implemented.
- Backlog: NW5 moved to Closed with a status line. One line each on NW2 (a
  fork build means repointing the plist and restarting; streamable HTTP would
  go there if SSE support is dropped) and NW7 (the shared server's backlinks
  stay stale until a reindex).
- Fork changelog: PATCH-17 (step 7).
- Project memory: wiki-search is now one shared server under launchd, and
  `$WIKI_PATH` is the default wiki. Update the existing note about `WIKI_PATH`
  and pm-wiki's tracked `.wiki-path`.
- After you approve the diffs: a `fix(hooks)` commit for step 7 and a
  `docs(fork-chgs)` commit for the docs, plus the pm-wiki commit from step 8.
  No push.

**Effect on the fork:** one hook change with a new test file (step 7), and
docs in `fork-chgs/`. No script, launcher or plugin manifest changes. Nothing
is offered upstream.

## 12. Results

Implemented 2026-10-02, following section 11.

- **Steps 1–4.** The plist was written (lint OK, mode 600, 64-character
  token), and the server started under launchd. It was listening within 2 s,
  with launchd as its parent, the cached `index.js` as its program, `VAULT_PATH`
  pm-wiki and bearer auth enabled. Requests without the token got 401. The
  user-scope entry was switched to SSE, and `claude mcp list` showed it
  connected.
- **Step 5.** A desktop session in a project without `.wiki-path` read
  `index.md` and created a test page through `vault`. A CLI session in another
  project read `index.md`, and its `vault` create of the same page failed with
  `NOTE_ALREADY_EXISTS`, showing that both sessions saw the same vault through
  the same server. Exactly one server process had launchd as its parent. The
  only other copy was the session running the implementation, started before
  the switch. Both test sessions were connected to port 3100. The test page was
  removed by hand, and pm-wiki's `git status` showed only `_status.md`.
- **Step 6.** `launchctl kickstart -k` restarted the server in 2 s. The CLI
  session's next read worked, with no reconnect by hand.
- **Step 7.** The session-start change was committed as `2e7247c`, with
  `tests/test_session_start_wiki_path.py`. The new test fails without the
  change. The full suite passed: 449 passed, 2 skipped. Recorded as PATCH-17 in
  the [llm-wiki-pm Fork Changelog](llm-wiki-pm-fork-changelog.md).
- **Step 8.** Nothing scheduled depends on `.wiki-path`: no scheduled tasks,
  no crontab, and no other LaunchAgents. All 14 `.wiki-path` files were
  removed. pm-wiki's tracked one was removed in pm-wiki commit `ac39373`.
  Sessions started in llm-wiki-pm, pm-wiki and `~` all resolve pm-wiki through
  `$WIKI_PATH`, with no warning. The server was unaffected.
- **Still to check:** at the next login, the server starts by itself and the
  first session connects (section 11, step 5 item 5).
