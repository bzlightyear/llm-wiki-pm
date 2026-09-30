# Wiki Hooks

Shell scripts that keep the wiki healthy across sessions. When installed as a Claude Code plugin, they activate automatically via `hooks/hooks.json` at the plugin root. No manual configuration needed.

---

## What these hooks do

**session-start.sh**
Runs at session start. Scaffolds the wiki on first run if it does not exist
(reads `.wiki-path` file in cwd (project-specific), then `CLAUDE_PLUGIN_OPTION_wiki_path` (global plugin config), then `WIKI_PATH` env, then cwd). Then scans
for broken links, orphan pages, stale entries (>30 days), and competitive pages
past their confidence decay threshold (>60 days). Writes `_status.md` and
outputs an `additionalContext` summary directly into Claude's context.
The link and orphan counts come from `lint.py --json`, which writes nothing to
the wiki. So do the counts of pages whose frontmatter, `sources:` or
`[source: ...]` citations break the rules in `references/citation-spec.md`,
and the list of pages resting only on conversation records, which `_status.md`
shows under "Secondhand, unverified". If lint fails, the summary says "health
unknown" rather than reporting zeros.

**pre-write.sh**
Runs before every write to the wiki, from the built-in tools (`Write`, `Edit`, `MultiEdit`) and the wiki-search MCP (`vault` create, create_from_template, update and delete, and `edit` unless `dryRun` is set; reads are ignored). Before an existing page in `entities/`, `concepts/`, `comparisons/`, `queries/` or `briefings/` changes, it copies it to `_archive/<slug>-<YYYY-MM-DD>.md`, at most once per page per day, where the slug is lint's page name (a `README.md` page is named after its folder). `overview.md` is copied only when it is replaced wholesale (`Write`, `vault` update or delete), and `index.md` never, since lint can rebuild it. Files under a directory page's `assets/` subfolder are skipped. A change to an existing `raw/` record gets a warning that records are write-once. The freshness gate reminds the agent to sweep live tools when the page, as it will be after the write, has no primary source and no inline `[source: ...]` marker; `Edit` and `MultiEdit` are applied to the disk text first, MCP `edit` operations aren't simulated, and pages marked `lifecycle: dated-digest` are exempt. The hook always exits 0 and never blocks a write.

**post-validate.sh**
Runs after every write to the wiki, from the same tools as `pre-write.sh` (`vault` delete and reads are ignored), and synchronously, so its report reaches the agent in the same turn. It re-reads each written page and checks it with lint's own functions: the frontmatter, `sources:` entries that aren't the path of an existing file, citations whose ID isn't declared in `sources:`, citations outside the grammar in `references/citation-spec.md`, escaped `\[`, and `[[wikilinks]]` that match no page in lint's page set (`entities/`, `concepts/`, `comparisons/`, `queries/`, `briefings/`, plus `overview` and `index`). `log.md`, `overview.md`, `index.md` and `MY-INTEGRATIONS.md` are checked for escaped `\[` only; `raw/` records, `_archive/` and lint reports aren't checked. It also runs the freshness gate for the two MCP writes `pre-write.sh` can't judge beforehand (`create_from_template` and `edit`), and reminds the agent of the split procedure when a write takes a page over 200 lines, or leaves a rewritten page over 200 lines when its earlier length isn't known. It reports at most 6 lines as `additionalContext` and appends the problems (not the reminders) to `_status.md`. The hook always exits 0 and never blocks a write.

**post-write.sh**
The broken-link check that `post-validate.sh` replaced. It stays in the repo, unregistered, with its tests.

**session-stop.sh**
Guards log rotation at the end of each session. When `log.md` exceeds 500 entries (lines starting with `## [`) it renames the file to `log-YYYY.md` (or `log-YYYY-part-N.md` if that already exists) and creates a fresh `log.md` with a rotation header.

---

## Installation

### Claude Code plugin (automatic)

Hooks are defined in `hooks/hooks.json` at the plugin root and activate automatically when the plugin is enabled. No manual `settings.json` editing required.

Make the scripts executable after cloning:

```bash
chmod +x hooks/*.sh
```

Script paths in `hooks/hooks.json` use `${CLAUDE_PLUGIN_ROOT}` so they resolve correctly regardless of where the plugin is installed.

**Notes on events:**
- `SessionStart` fires once when the session opens (new, resumed, or cleared). Not on every message.
- `PostToolUse` fires after a tool call succeeds. `post-validate.sh` reads the written path from stdin JSON (`tool_input.file_path`, or `path` and `operations[].path` for the MCP tools). It runs without `async`, since an async hook's output doesn't reach the agent.
- `SessionEnd` fires when the session terminates. Not after every Claude response (`Stop` does that).

**Notes on `PreToolUse` matcher:**
`Write|Edit|MultiEdit|mcp__.*wiki-search__(vault|edit)` also covers the wiki-search MCP's write tools under both of their names: `mcp__wiki-search__*` when the server is configured directly, and `mcp__plugin_llm-wiki-pm_wiki-search__*` when it comes with the plugin.

**Notes on `PostToolUse` matcher:**
The same matcher as `PreToolUse`. The `"matcher"` field is matched against the tool name. `Write|Edit|MultiEdit` covers all file-writing tools; `MultiEdit` is confirmed in the official Anthropic `security-guidance` plugin example.

---

### Standalone use (without plugin)

If using the scripts without the Claude Code plugin system, wire them manually.

**Shell alias approach:**

Add to `~/.bashrc` or `~/.zshrc`:

```bash
# Run wiki health check before starting any AI session
alias wiki-start='bash /path/to/hooks/session-start.sh'
alias wiki-stop='bash /path/to/hooks/session-stop.sh'
```

Call `wiki-start` before opening your AI tool, `wiki-stop` when you close it.

**Wrapper script approach:**

```bash
#!/usr/bin/env bash
# ai-session.sh -- wrapper that runs hooks around your AI tool

bash /path/to/hooks/session-start.sh
your-ai-tool "$@"
bash /path/to/hooks/session-stop.sh
```

For `pre-write.sh` and `post-validate.sh`, pass the hook JSON payload on stdin (same format Claude Code uses):

```bash
echo '{"tool_name":"Write","tool_input":{"file_path":"/path/to/wiki/entities/example.md"}}' \
  | WIKI_PATH=/path/to/wiki bash /path/to/hooks/post-validate.sh
```

---

## How the agent uses hook output

`session-start.sh` writes `$WIKI/_status.md` before the agent gets your first message. The skill instructs the agent to read `_status.md` during the orient step (before planning any work). This means:

- Broken links are surfaced automatically, not discovered mid-task.
- Confidence decay warnings appear at session start, prompting a review.
- Stale pages are listed so the agent can factor them into recommendations.

`post-validate.sh` reports problems with a page to the agent right after the write, so it can fix them in the same turn. It also appends them to `_status.md`, where they accumulate until the next session start rewrites the file. The agent can re-read `_status.md` later in the session, for example for a brief.

---

## Skipping auto-commit

Auto-commit is not included in these hooks. Automatic commits can obscure work-in-progress and create noisy git history.

If you want auto-commit on session end, add this to `session-stop.sh` before the final `exit 0`:

```bash
# Optional auto-commit -- add manually if desired
cd "$WIKI" && git add -A && git commit -m "wiki update $(date +%Y-%m-%d)" 2>/dev/null || true
```

The `|| true` prevents the hook from failing if there is nothing to commit or git is not initialized.

---

## Configuration

### Project config (preferred)
Create a `.wiki-path` file in your project directory:

```bash
# via the skill command (recommended)
/llm-wiki-pm:set-wiki-path ~/pm-wiki

# or manually
echo ~/pm-wiki > .wiki-path
```

The SessionStart hook reads this file on every session start. Commit it to share a
team wiki location; add it to `.gitignore` for personal paths.

`wiki_domain` is set at scaffold time via the plugin's `userConfig` prompt or
`CLAUDE_PLUGIN_OPTION_wiki_domain`. It defaults to `PM` if not set.

### Fallback: environment variable

If plugin config is not set, `WIKI_PATH` is used instead. Add to `~/.bashrc`
or `~/.zshrc`:

```bash
export WIKI_PATH=~/pm-wiki
export WIKI_DOMAIN="PM, Katalon"  # optional, defaults to "PM"
```

`WIKI_DOMAIN` is only read at scaffold time. Changing it after the wiki is
created has no effect on existing files.
| Variable | Default | Purpose |
|----------|---------|---------|
| `WIKI_PATH` | (none) | Wiki directory location fallback |
| `WIKI_DOMAIN` | `PM` | Domain label used during scaffold |