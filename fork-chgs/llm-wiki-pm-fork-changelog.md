# llm-wiki-pm Fork Changelog

created: 2026-08-11

How this fork differs from its baseline, upstream llm-wiki-pm 2.21.0: each
change (PATCH-1 to PATCH-18) with its reason, files, commits and status, how
the fork is installed, and what to check when merging an upstream release.

revised on: 2026-10-02
Rewrote the changelog from git against the 2.21.0 baseline, for a fork that
runs from this clone rather than as an installed plugin. Patches are renumbered
PATCH-1 to PATCH-18 and grouped by area, with an old-to-new mapping. The
sources and references work and NW6 are now entries. The removed patches are
reduced to background lines. The open issues moved to the
[llm-wiki-pm Fork Backlog](llm-wiki-pm-fork-backlog.md), and the plugin-cache
re-application steps gave way to a section on merging an upstream release.

revised on: 2026-10-01
Marked PATCH-2 and PATCH-3b removed. A folder page is now named after its
folder, so neither `backlinks.py` nor `slug()` needs a `README.md` rule (NW6 in
the llm-wiki-pm fork backlog).

revised on: 2026-09-30
Marked ISSUE-3 closed. After the PM wiki's migration (step 10b of the sources
and references design), no citation there fails to resolve, and body legends
are no longer something citations must match.

revised on: 2026-09-29
Marked ISSUE-2 mitigated, now that the pre-write hook snapshots `overview.md`
before any whole-file replacement (step 3 of the sources and references design).
Marked PATCH-3a replaced by the `wikifm.py` frontmatter parser (step 4), and
added a correction to `91878dc`'s commit message.

revised on: 2026-08-30
Moved into the fork from the PM wiki, where it had been kept as a wiki page.
Reorganized with PATCH-N/ISSUE-N IDs, merged five overlapping open issues into
ISSUE-1, fixed a stale patch count and a dangling cross-reference, and added a
status line to each open issue.

revised on: 2026-08-29
Added PATCH-4 (relationship-map wiring), captured from the diff before it was
committed.

## About this document

- **Baseline:** upstream `github.com/anh-chu/llm-wiki-pm` (the `upstream`
  remote) at `0667f75 chore(release): 2.21.0`. Upstream has had no commits
  since (checked 2026-10-02).
- **Fork:** `github.com/bzlightyear/llm-wiki-pm` (`origin`), branch `main`.
- **Inventory:** `git log 0667f75..main` and `git diff 0667f75 main`. Git holds
  the diffs, so entries cite commits instead of pasting them.
- **Numbering:** patches are grouped by area, and within the sources and
  references group by dependency, so a reader carrying them to a newer baseline
  can take them in order. Older docs and commit messages use the numbers in
  [Old Patch and Issue Numbers](#old-patch-and-issue-numbers).
- **Work not done yet** lives in the
  [llm-wiki-pm Fork Backlog](llm-wiki-pm-fork-backlog.md), not here.

## How the Fork Runs

The fork isn't installed as the Claude Code plugin. The plugin isn't enabled,
and `hooks/hooks.json` is kept in step with the fork for plugin installs but
isn't read on this machine. Every wiki, pm-wiki included,
runs this clone's code:

- **Skills:** `~/.claude/skills/llm-wiki-*` and `set-wiki-path` are symlinks to
  `skills/` in this clone.
- **Worker agents:** `~/.claude/agents/worker-*.md` are symlinks to
  `.claude/agents/` (step 9 of the sources and references design).
- **Hooks:** registered in `~/.claude/settings.json` by absolute path:
  SessionStart `session-start.sh`, PreToolUse `pre-write.sh`, PostToolUse
  `post-validate.sh` and SessionEnd `session-stop.sh`, the write hooks with the
  matcher `Write|Edit|MultiEdit|mcp__.*wiki-search__(vault|edit)`.
- **Permission rules:** `~/.claude/settings.json` denies the wiki-search MCP's
  `edit` tool and asks before its `vault` tool, under both tool-name forms
  (PATCH-5).
- **wiki-search MCP:** one shared server under launchd (`local.wiki-search`,
  SSE on 127.0.0.1:3100 with a bearer token) running `hooks/wiki-search.sh`.
  `$WIKI_PATH` is the default wiki, and a project's `.wiki-path` only marks one
  that uses another wiki. See the
  [Wiki-Search Launchd Guide](wiki-search-launchd-guide.md) and NW5 in the
  backlog.

So a commit on `main` takes effect at the next session, or for `wiki-search.sh`
at the next server restart. Upstream releases arrive by merging the `upstream`
remote (see [Merging an Upstream Release](#merging-an-upstream-release)).

The fork was made because there is no write access to upstream: it is the
remote this work is pushed to, and the place pull requests would come from.

## Patches

Each entry: what changes relative to 2.21.0, why, where, and its status on
2026-10-02. "Upstream candidate" means worth offering upstream and not offered
yet; no fork change has an upstream pull request.

### Lint fixes from before the design

#### PATCH-1 — `overview` and `index` are valid link targets

- **What:** lint registers `overview.md` and `index.md` in its slug map, so
  `[[overview]]` and `[[index]]` resolve, without putting the two files through
  the page checks (frontmatter, tags, orphans, index). PATCH-8 extended lint's
  page set to `briefings/`, and post-validate resolves links the same way.
- **Why:** upstream lint reported every link to them as broken, because they sit
  outside the page folders.
- **Where:** `skills/llm-wiki-pm/scripts/lint.py`, `main()`. Commit `dfdd98c`
  (first made in the plugin cache as `4b74c51`).
- **Status:** active. Upstream candidate, not filed.

#### PATCH-2 — Escaped-bracket check and repair

- **What:** lint reports a stray backslash before `[` as 🔴 in every page and in
  `log.md`, `overview.md`, `index.md` and `MY-INTEGRATIONS.md`, and
  `--auto-fix` removes it. Matches inside fenced code blocks and inline code
  spans are skipped, since quoted source may hold a literal `\[`.
  `post-validate.sh` (PATCH-9) runs the same check at write time.
- **Why:** the wiki-search MCP's `string_replace` and `frontmatter_set`
  re-serialize the whole file and escape `[[` as `\[[`
  (`wirux/mcp-markdown-vault#47`), breaking wikilinks and `## [date]` log
  headers. It happened three times by 2026-08-11. The deny rule on the MCP's
  `edit` tool (PATCH-5) removes the cause on this install, so the check is now a
  safety net for other installs and for writes the rule doesn't cover.
- **Where:** `lint.py`: `find_escaped_brackets()`, `_fenced_ranges()`,
  `_inline_code_ranges()`. Commit `dfdd98c` (first made as `4b74c51`, with the
  code-span guard added in `79c9f3b`).
- **Status:** active until `#47` is fixed. `#47` is open with one comment and no
  maintainer reply, and the MCP repo was last pushed 2026-06-02 (checked
  2026-10-02). Not an upstream llm-wiki-pm change by itself: the bug is in the
  MCP.

### Sources and references design (steps 1–10a)

The [Sources and References Design](sources-and-references-design.md) gives a
source one identity: a `raw/` record's file stem, declared by path in
`sources:` and cited by ID in `[source: <id>, <location>]`, with exact
resolution. Its section 8 orders the steps by dependency and marks each one
"Up" or "Fork". Each step below is one patch. The design holds the detail, and
the entries summarize. Step 11, which promotes R3, R6 and R12 to 🔴 and is when
the set would go upstream with the migration script, isn't done.

#### PATCH-3 — `wiki-search.sh` reads `.wiki-path` without a false error

- **What:** the launcher reads `.wiki-path` with `cat`, not a `<` redirection,
  and `tests/test_wiki_search.py` smoke-tests it with a stub `node`.
- **Why:** the shell reports a failed `<` before `2>/dev/null` applies, so every
  MCP start without `.wiki-path` logged "No such file or directory".
- **Where:** `hooks/wiki-search.sh`. Commit `5ee7f59` (step 1, design 5.13).
- **Status:** active. Upstream candidate.

#### PATCH-4 — Doc drift fixes

- **What:** README, CONTRIBUTING and GETTING_STARTED describe the
  private-by-default model (`shareable: true`) instead of the retired
  `private:` flag. CONTRIBUTING's required fields match lint.
  `worker-source-fetcher` stops writing `private:` and routes records as the
  ingest guide does. `llm-wiki-prd` calls the orient gate a checklist, not
  "enforced". `llm-wiki-maintain` drops the 7-day brief rotation into
  `_archive/briefings/`, which broke links to briefs, and says what plain
  `--auto-fix` does.
- **Where:** commit `7c41339` (step 2).
- **Status:** active. Upstream candidate.

#### PATCH-5 — Write hooks cover MCP writes and name snapshots by slug

- **What:** `pre-write.sh` also runs on the wiki-search MCP's `vault` and `edit`
  writes (both tool-name forms, with `action` and `dryRun` filters). Snapshots
  go to `_archive/<slug>-<date>.md` through one `snapshot()` in `lint.py`, which
  lint's auto-fix and the migration reuse. `overview.md` is snapshotted on
  whole-file replacement, `index.md` never. `briefings/` is covered, a directory
  page's `assets/` is skipped, and a change to a `raw/` record gets a
  write-once warning. The README documents the permission rules that deny the
  MCP's `edit` tool and ask before `vault`.
- **Why:** MCP writes bypassed the snapshot and freshness gate, and the MCP's
  `edit` tool damages pages (`#47`, `#49`).
- **Where:** `hooks/pre-write.sh`, `hooks/hooks.json`, `hooks/README.md`,
  `README.md`, `lint.py`, `tests/test_write_hooks.py`. Commit `eda0293` (step
  3, design 5.11). The permission rules are in `~/.claude/settings.json`.
- **Status:** active. Upstream candidate; the permission rules are per user.

#### PATCH-6 — `wikifm.py`, the one frontmatter parser

- **What:** `skills/llm-wiki-pm/scripts/wikifm.py` parses frontmatter to a
  declared profile (block lists as lists, wrapped items, quoted dates) and has
  text-preserving writers (`set_field`, `set_list`) that write dates as
  `'YYYY-MM-DD'`. Lint, `pre-write.sh` and session-start's stale scan read
  frontmatter through it, and upstream's `parse_frontmatter()` and
  `extract_sources()` are gone. `slug()` lives here.
- **Why:** four hand-rolled parsers disagreed on block lists, quoting and
  dates, and silently dropped values.
- **Where:** `wikifm.py`, `lint.py`, `hooks/pre-write.sh`,
  `hooks/session-start.sh`, `tests/test_wikifm.py` (PyYAML oracle tests, skipped
  without PyYAML). Commit `31a9a70` (step 4, design 5.10).
- **Background:** it replaced two earlier lint fixes: block-style list parsing
  in `parse_frontmatter()` (old PATCH-3a, `dfdd98c`), which joined a block list
  into a `[a, b]` string, and quote-aware splitting of `sources:` flow lists
  (`543766c`).
- **Status:** active. Upstream candidate. Upstream issue `anh-chu#9` (block-style
  tags dropped by lint) is open; this is the fork's fix for it.

#### PATCH-7 — Citation spec and conversation capture

- **What:** `references/citation-spec.md` is the single spec for records,
  `sources:` and citations. A fact stated in conversation becomes a write-once
  record `raw/internal/conversation-<date>-<topic>.md` made by `capture.py`, and
  is cited like any other source. `lint.py --cited-sources <page>` lists what a
  page cites, for setting `sources:`. AGENTS.md, the core SKILL.md, the ingest,
  update, crystallize and output-format guides, the SCHEMA and persona
  templates, the CRM, research and PRD skills point to the spec, and enrichment
  captures and cites each page it uses.
- **Why:** a source had no defined identity, so free text was accepted as one
  (design section 3).
- **Where:** commits `783e37d` (step 5) and `d3941bb` (person enrichment and
  supersede).
- **Background:** `ae33f9d` had told Update to cite
  `[source: user, conversation, <date>]` when nothing was captured. This patch
  kept its rule against coining a `raw/`-shaped ID for an uncaptured artifact
  and replaced the conversational form with a captured record.
- **Status:** active. Upstream: an issue first, since it changes the
  micro-capture contract (design section 8).

#### PATCH-8 — Lint checks sources and citations exactly (R1–R12)

- **What:** lint's R-rules, catalogued in design 5.15: frontmatter structure and
  profile (R1, R2, R5, R12), exact citation resolution (R3), citation coverage
  (R4), `sources:` entries that are existing paths (R6), citation grammar (R7),
  unique IDs and slugs (R9), pages resting only on conversation records (R10),
  the MCP's default contract (R11). Content fixes run only under
  `--auto-fix=content`. `--json` writes nothing. `briefings/` joins the page
  set, with dated digests exempt from the index check. Session start reports
  I1–I3 counts and R10's list, and says "health unknown" if lint fails.
  `worker-link-validator` uses `lint.py --json`. `lint-guide.md` documents it
  all.
- **Where:** `lint.py`, `wikifm.py`, `hooks/session-start.sh`,
  `hooks/README.md`, `references/lint-guide.md`,
  `.claude/agents/worker-link-validator.md`, `tests/test_lint.py`. Commits
  `91878dc` (R1–R5) and `db6dd04` (step 6).
- **Background:** `91878dc` added R1–R5 before the design. R3 was a loose
  substring match, rewritten as exact resolution.
- **Status:** active, with R3, R6 and R12 at 🟡 until step 11. Upstream
  candidate.

#### PATCH-9 — `post-validate.sh` checks each written page

- **What:** a synchronous PostToolUse hook re-reads each written page and
  checks it with lint's own functions: frontmatter, `sources:`, citations,
  escaped `\[`, and wikilinks against lint's page set. It also runs the
  freshness gate for MCP writes `pre-write.sh` can't judge, and reminds the
  agent of the split procedure past 200 lines. It replaces `post-write.sh` in
  `hooks.json`; `post-write.sh` stays in the repo, unregistered, with its tests.
- **Where:** `hooks/post-validate.sh`, `hooks/hooks.json`, `hooks/README.md`,
  `tests/test_write_hooks.py`. Commit `dc8d87f` (step 7).
- **Status:** active. Upstream candidate.

#### PATCH-10 — Vault contract template and scaffold

- **What:** `templates/vault-contract.md` is copied to `meta/contract.md` on
  scaffold (noclobber), and a directory holding only the MCP's `meta/` and
  `.markdown_vault_mcp/` and session-start's own `_status.md` and `.wiki-lock`
  counts as empty. GETTING_STARTED and CONTRIBUTING copy the contract too.
- **Why:** the MCP may start first and write its own files and a generic
  contract, which made a new wiki look non-empty and skip the scaffold.
- **Where:** `hooks/session-start.sh`, the template, `tests/test_scaffold.py`.
  Commit `09dfb6f` (step 8).
- **Status:** active. Upstream candidate.

#### PATCH-11 — Lint workers find `lint.py` without `CLAUDE_SKILL_DIR`

- **What:** `worker-lint` and `worker-link-validator` resolve the core skill
  from `$CLAUDE_PLUGIN_ROOT`, else `~/.claude/skills/llm-wiki-pm`.
- **Why:** Claude Code fills in `${CLAUDE_SKILL_DIR}` only in skill files. In a
  subagent it was empty, so the workers ran `/scripts/lint.py`.
- **Where:** `.claude/agents/`. Commit `3ce221e` (step 9, which also moved the
  workers to user-level symlinks, an install change).
- **Status:** active. Upstream candidate. Related upstream issue `anh-chu#10`
  (the plugin ships workers in a folder Claude Code doesn't read) is open; the
  fork sidesteps it with the symlinks.

#### PATCH-12 — `migrate_sources.py`

- **What:** moves a wiki onto the citation spec (design section 7, M1–M8),
  `overview.md` included. Dry run by default.
- **Where:** `skills/llm-wiki-pm/scripts/migrate_sources.py`,
  `tests/test_migrate_sources.py`. Commits `c2e086b`, `0e5b578` (step 10a).
  pm-wiki was migrated with it on 2026-09-30 (step 10b).
- **Status:** active. Fork-only until step 11, then upstream with it.

### Page names

#### PATCH-13 — A folder page is named after its folder

- **What:** a multi-file page is `queries/<slug>/<slug>.md`, not
  `queries/<slug>/README.md`, and `slug()` is the file stem for every page. The
  core SKILL's Query step, `output-formats.md`, `citation-spec.md`, the
  research and PRD skills, the researcher role and the vault contract template
  say so.
- **Why:** Obsidian and the wiki-search MCP resolve a link by file name, so
  links to a `README.md` page resolved for the fork's tools only. See NW6 in the
  backlog and the
  [NW6 Page Name Resolution Analysis](nw6-page-name-resolution-analysis.md).
- **Where:** commit `84aeeac`. pm-wiki's four folder pages were renamed in its
  own repo.
- **Background:** earlier, `slug()` in lint (old PATCH-3b) and `backlinks.py`
  (old PATCH-2) named a `README.md` page after its folder. Both rules were
  removed on 2026-10-01, and `backlinks.py` now matches upstream.
- **Status:** active. Upstream's docs still prescribe `README.md`, though its
  lint already names a page by its file stem. Upstream issue `anh-chu#11`, filed
  2026-08-08 from this fork, proposed the opposite fix. A comment on 2026-10-02
  withdrew it, described this patch, and offered a pull request with only the
  upstream doc changes (see Open Questions).

### Skill docs

#### PATCH-14 — Entity promotion updates the relationship map

- **What:** the core skill's entity-promotion scan (§2 ⑫) updates
  `concepts/relationship-map.md` when it promotes a person: it creates the map
  if needed, or adds the person's row and their manager's `direct_reports`
  entry. `llm-wiki-persona` says the scan triggers it.
- **Why:** in the source wiki, two people promoted on 2026-08-28 were missing
  from the map until it was fixed by hand the next day.
- **Where:** `skills/llm-wiki-pm/SKILL.md`, `skills/llm-wiki-persona/SKILL.md`.
  Commit `8680b22` (first made in the plugin cache as `f7faab5`).
- **Status:** active, not verified end to end (see Open Questions). Upstream
  candidate, not filed.

#### PATCH-15 — Template paths resolve outside the plugin

- **What:** three template references use `${CLAUDE_SKILL_DIR}`, and the
  persona skill reaches the core skill's template through
  `${CLAUDE_SKILL_DIR}/../llm-wiki-pm/`.
- **Why:** `${CLAUDE_PLUGIN_ROOT}` exists only in a plugin install, and the bare
  relative paths depended on the reader guessing the base directory.
- **Where:** the core, CRM and persona `SKILL.md` files. Commit `11fa847`.
- **Status:** active. Upstream candidate.

#### PATCH-16 — Ingest routes HTML reports and slides like PDFs

- **What:** any document file gets a markdown record in `raw/papers/`, with the
  original in `raw/assets/` named in the record's `asset:` field.
- **Why:** only PDFs had a route, and an HTML report landed in an unrouted
  `raw/attachments/` folder.
- **Where:** `references/ingest-guide.md`. Commit `74a1ad7`.
- **Status:** active. Upstream candidate.

### Install

#### PATCH-17 — No session-start warning when `WIKI_PATH` supplies the wiki

- **What:** `session-start.sh` no longer warns "using global wiki path … Run
  /llm-wiki-pm:set-wiki-path …" when no `.wiki-path` is present. The warning
  for no wiki path at all stays. `tests/test_session_start_wiki_path.py` covers
  both.
- **Why:** here `WIKI_PATH` is the default wiki for every project, and
  `.wiki-path` only marks a project that uses another one (NW5), so the warning
  fired in every session.
- **Where:** `hooks/session-start.sh`. Commit `2e7247c`.
- **Status:** active. Fork-only: it reverses upstream's intent, where
  `.wiki-path` is the main setting.

### Tests

#### PATCH-18 — Test isolation and Python 3.9

- **What:** `tests/conftest.py` runs every test from its own temp directory with
  `WIKI_PATH` unset. `tests/test_hooks.py` gets `from __future__ import
  annotations`.
- **Why:** hooks started without `cwd=` read the checkout's `.wiki-path` or the
  developer's `WIKI_PATH` and could act on a real wiki. `test_hooks.py` didn't
  import on Python 3.9.
- **Where:** commits `c98f84c`, `5edd090`.
- **Status:** active. Upstream candidate. The suite passed on 2026-10-02: 449
  passed, 2 skipped.

### Repository-only files

Not patches to upstream's code, and not offered upstream:

- `fork-chgs/`: this changelog, the backlog, and the fork's designs, analyses,
  reviews, guides and prompts.
- `wiki-search-architecture.md`, relocated from pm-wiki on 2026-08-30.
- `.claude/commands/implement-step.md`, the `/implement-step` command for the
  sources and references plan.
- `.gitignore`: `.wiki-path`, `.obsidian/` and `.DS_Store`.

## Merging an Upstream Release

1. `git fetch upstream`, then read `git log main..upstream/main` and upstream's
   `CHANGELOG.md` before merging.
2. `git merge upstream/main` on a branch, so `main` keeps working while
   conflicts are resolved.

**Most likely to conflict:**

- `skills/llm-wiki-pm/scripts/lint.py`. The fork rewrote much of it (PATCH-6,
  PATCH-8): upstream's `parse_frontmatter()`, `extract_sources()` and
  `extract_tags()` are gone. Any upstream lint change needs porting onto
  `wikifm`, not a textual merge.
- `hooks/session-start.sh` (lint parsing, stale scan, scaffold, the removed
  warning), `hooks/pre-write.sh` (PATCH-5, PATCH-6) and `hooks/hooks.json`
  (matchers, `post-validate.sh` in place of `post-write.sh`).
- `skills/llm-wiki-pm/SKILL.md` §2, §4 and the References and Scripts lists;
  `ingest-guide.md`, `update-guide.md`, `output-formats.md`; the `SCHEMA.md`
  template (PATCH-7, PATCH-14).
- The research and PRD skills, wherever upstream names folder pages
  `README.md` (PATCH-13).
- `README.md`, `hooks/README.md`, `CONTRIBUTING.md`, `GETTING_STARTED.md`.

**After a merge:**

- Run the suite: `python3 -m pytest tests/ -q`.
- Run `lint.py <wiki> --json` before and after on pm-wiki and compare the
  counts.
- Search for new frontmatter reading outside `wikifm` (`grep -n "^---"` style
  regexes, `yaml.safe_load`) and new `README.md` folder-page wording.
- New docs or templates: check them against `citation-spec.md` (citations,
  `sources:` as paths, quoted dates) and the private-by-default model.
- If upstream changed `hooks/hooks.json`, mirror it in
  `~/.claude/settings.json` by hand. Nothing reads `hooks.json` here, so a new
  or changed upstream hook doesn't run until then.
- Symlink any new skill into `~/.claude/skills/` and any new worker into
  `~/.claude/agents/`.
- If `hooks/wiki-search.sh` or the MCP package version changed, restart the
  server: `launchctl kickstart -k gui/$(id -u)/local.wiki-search`.
- If upstream fixed any patch here, drop the fork's version and update its
  entry. Check `wirux/mcp-markdown-vault#47` too: if it's fixed, PATCH-2 is
  optional.

## Open Questions

- **What to offer upstream, and when.** Section 8 of the design marks steps 1–8
  and step 9's worker fix as upstream candidates (step 5 as an issue first), and
  the migration script to go with step 11. PATCH-1, PATCH-14, PATCH-15 and
  PATCH-16 aren't covered by it, and none is filed. Two issues filed from this
  fork are open: `anh-chu#9` (block-style tags), which PATCH-6 fixes another
  way, and `anh-chu#11`. On 2026-10-02 a comment on `#11` withdrew its
  suggested `README.md` slug rule in favor of PATCH-13 and offered a docs-only
  pull request. It's waiting on a reply.
- **PATCH-14 is unverified end to end.** It was written after the gap it fixes
  was corrected by hand. pm-wiki's log shows person promotions on 2026-09-14 and
  2026-09-22 whose entries don't mention the relationship map. Check whether
  those were people the map should hold, and whether the scan updated it.

## Corrections to Commit Messages

Recorded here rather than by rewriting git history, which would change the IDs
of every later commit.

- `91878dc` (lint checks R1–R5) says it adds `tests/test_lint.py` as "the first
  test module for lint.py". `TestLint` in `tests/test_hooks.py`, added upstream
  in v2.20.0, already tested `lint.py`.
- `dfdd98c` lists "session-stop.sh: disable auto-commit block" among patches to
  the plugin. Upstream 2.21.0 has no auto-commit: the fork's own `dc6bc6c`
  added it from the README's optional snippet, and `eb154e1` moved it.

## Background

### How the fork got here

- **Plugin-cache patches, 2026-08-06 to 2026-08-29.** The first fixes were made
  in the installed plugin's cache, `~/.claude/plugins/cache/anh-chu-plugins/
  llm-wiki-pm/2.21.0`, as commits `4b74c51`, `79c9f3b` and `f7faab5`. That copy
  wouldn't survive a plugin update, so they were ported to this clone (`dfdd98c`,
  2026-08-11, all bundled in one commit, and `8680b22`, 2026-08-30). Tag
  `plugin-cache-2.21.0` keeps the cache commits reachable.
- **Auto-commit.** `dc6bc6c` added an auto-commit at session end from the
  README's optional snippet, `eb154e1` made it run every session, and
  `dfdd98c` commented it out (old PATCH-1): SessionEnd fired per short-lived
  backend session, producing dozens of near-duplicate wiki commits.
  `38c3757` removed the commented-out block on 2026-10-02, so
  `session-stop.sh` matches 2.21.0 again.
- **This document** started as a page in pm-wiki and moved here on 2026-08-30.
- **The install** moved from the plugin to symlinks and `settings.json` hooks
  in September 2026, so the fork's code runs directly (see How the Fork Runs).
- **History rewrite, 2026-09-29.** `git filter-repo` replaced real names in 27
  commits from `4e61e6c` on (step 0 of the design). Every commit ID in this
  document was checked to exist on 2026-10-02.

### Old Patch and Issue Numbers

Older docs, commit messages and this changelog's older revision entries use
these numbers.

| Old | New | Note |
|---|---|---|
| PATCH-1 | none | Auto-commit disabled. `session-stop.sh` matches 2.21.0 since `38c3757` (Background). |
| PATCH-2 | none | `backlinks.py` README self-slug. Removed 2026-10-01 (PATCH-13). |
| PATCH-3a | none | Block-style list parsing. Replaced by `wikifm.py` (PATCH-6). |
| PATCH-3b | none | `slug()` README rule. Removed 2026-10-01 (PATCH-13). |
| PATCH-3c | PATCH-1 | |
| PATCH-3d, PATCH-3e | PATCH-2 | One entry. |
| PATCH-4 | PATCH-14 | |
| PATCH-5 | PATCH-17 | |
| ISSUE-1 | NW1 | Merged into NW1 in the backlog, 2026-10-02. |
| ISSUE-2 | NW1 | Merged into NW1 in the backlog, 2026-10-02. |
| ISSUE-3 | none | Closed 2026-09-30, by steps 5–7 and 10b of the design. |
