# Archive Snapshots in Search Brief

created: 2026-10-08

Pre-write snapshots in pm-wiki's `_archive/` outrank the live pages they copy
in wiki-search results, and they make up most of what `grep -r` and
`backlinks.py` return. This brief measures the problem, lists every reader and
writer of snapshots, and weighs five options. It recommends dropping snapshots
and relying on git, with a checkpoint commit before a session's first write to
the wiki (option 5, which takes in backlog item NW10). Keeping snapshots in a
`_snapshots/` folder that the wiki-search server ignores, through NW2's fork, is
the alternative if automatic commits are unwanted.

revised on: 2026-10-13
Added option 5, dropping snapshots for checkpoint commits, and made it the
recommendation in place of the `_snapshots/` folder with NW2's ignore list,
which becomes the alternative. Added measurements: how many snapshots git
already holds, the `.wiki-lock` behavior that rules out NW10's lock check, the
only recorded snapshot "backstop", and pm-wiki's commit cadence.

Status: proposal, awaiting approval. Nothing is implemented.
Backlog item: NW12 in the [llm-wiki-pm Fork Backlog](llm-wiki-pm-fork-backlog.md),
which NW10 was merged into on 2026-10-13.
Related: NW7 (an `_archive/` copy steals a live page's backlinks), NW2 (the
deferred fork of the MCP server), NW11 (`AGENTS.md`, where the snapshot rule
lives).

## Recommendation in brief

1. **Now:** `backlinks.py` drops `_archive` from its folder list (NW7's step
   1), and the query and update steps gain a rule: a hit under `_archive/` is a
   retired page, not current.
2. **Replace snapshots with checkpoint commits.** One function in your fork,
   `checkpoint()` in `lint.py`, commits the wiki when it has uncommitted
   changes. The pre-write hook calls it before a session's first write to the
   wiki, the session-start hook when a session starts in the wiki folder, and
   lint's `--auto-fix` before its first fix. It replaces `snapshot()` at every
   call site. "Undo that" becomes a git restore that the agent runs.
3. **Delete the 441 snapshots** from `_archive/` in one pm-wiki commit, with
   your OK. Git keeps every one in its history. `_archive/` keeps the 6 retired
   pages.

This removes the search problem without NW2, closes NW10's gap for script
writes, and drops a rule agents have missed. The cost is automatic commits in
pm-wiki's history, and undo through git.

## What happens

The wiki-search MCP server (your fork's `hooks/wiki-search.sh` runs upstream
`@wirux/mcp-markdown-vault` 2.3.0) indexes every `.md` file under the wiki.
`listNotes()` in `infrastructure/local-fs-adapter.js` reads the folder
recursively and skips nothing, not even dot folders. Only the overview builder
(`use-cases/vault-overview.js`) skips `node_modules`. The search index, the
backlink index and `global_search` all start from `listNotes()`, and the file
watcher indexes any `.md` change.

**Measured on 2026-10-08:**

- **Semantic search.** `semantic_search` for "alerts for cost owners merged
  into the permissions screen with a frequency picker" (10 results):
  - 6 of the 10 hits were `_archive/` snapshots, including the top hit
    (`_archive/cfp-alerts-cost-owners-2026-10-06.md`, score 1.0).
  - The live history page `concepts/cfp-alerts-cost-owners-history-2026-09-18.md`
    ranked third, with the same text plus its `[source: ...]` markers. The
    snapshots above it carry no markers, so an agent quoting them gets
    uncited text.
  - The current page, `concepts/cfp-alerts-cost-owners.md`, wasn't in the 10.
    Only the same query limited to `concepts/` found it, fifth of five.
- **`grep -r "$WIKI"`** reads `_archive/` like any other folder. `_archive/`
  held 435 of the wiki's 1,002 `.md` files.
- **`backlinks.py`** lists `_archive` among its folders on purpose. For three
  busy pages, most of the "pages linking here" were snapshots:

  | Page | Linking files | In `_archive/` |
  |---|---|---|
  | `cfp-alerts-cost-owners` | 57 | 35 |
  | `keenan-dolan` | 133 | 88 |
  | `cfp-unified-plan-experience` | 102 | 63 |

  Across the wiki, `_archive/` holds 10,984 `[[wikilinks]]`, the live files
  4,594.
- **Obsidian** already hides `_archive/` (`userIgnoreFilters` in
  `.obsidian/app.json`).

**What's in `_archive/`** (2026-10-13: 447 files, all tracked by pm-wiki's git
and pushed to GitHub):

- **441 snapshots,** named `<slug>-<YYYY-MM-DD>.md`: of live pages, of
  `overview.md`, `SCHEMA.md`, `index.md` and `meta/contract.md`, and of four
  plugin pages since moved out of the wiki. 123 date from the citation
  migration on 2026-09-30. Ingest days add 10 to 34.
- **5 superseded entity pages** with `superseded_by:` (`bill.md` and four
  first-name pages merged into full-name pages in August).
- **1 page moved by hand,** `cfp-ai-tokenization-history-2026-08-10.md`
  (NW7's M1).
- An empty `briefings/` folder, left by the brief rotation that step 2 of the
  sources design removed.

**How much of that git already has** (2026-10-13): 310 of the 441 snapshots
are byte-identical to a version of a live file in some commit. The other 131
captured states that were never committed under the page's own path, but they
are committed as `_archive/` files, so git holds all 441.

**Two new facts for NW7:**

- **A second same-name copy.** Two `_archive/` files share a live page's file
  name, not one. The second, `cfp-mcp-ai-insights-history-2026-09-30.md`, is
  a snapshot. The migration snapshotted the then-live page
  `cfp-mcp-ai-insights-history` on 2026-09-30, giving it the name
  `<slug>-2026-09-30`. On 2026-10-06 a history split named a new live page
  `cfp-mcp-ai-insights-history-2026-09-30`, by its end date. A snapshot's name
  can equal a split page's name whenever a page's slug ends in `-history`.
- **One live pointer into `_archive/`.** `overview.md` says its
  "Pre-2026-10-06 text" is in `_archive/overview-2026-10-06.md`, a snapshot
  taken when the overview was condensed. That file is identical to
  `overview.md` in commit `7db03cd`. No `[[wikilink]]` in a live file points
  at a name that exists only in `_archive/`.

**What hasn't happened:** no `_archive/` file was ever changed after it was
created (pm-wiki's git history, 2026-10-08). So the harm is to reading, not
writing: stale text in answers, and live pages crowded out of the top results.

**Snapshots in use** (2026-10-13):

- NW10 records that the user has never restored from one.
- The only log entry that mentions them as a backstop (`log-2026.md`,
  2026-09-22) is about a range replacement that deleted a subsection written
  an hour earlier. No snapshot of that page exists for 2026-09-22, and a
  snapshot holds only the state before the day's first write, so it couldn't
  have held that subsection. The text was restored from the agent's own
  context.
- **What a snapshot covers:** the page as it was before its first Write, Edit
  or MCP write of the day. Bash, script and Obsidian writes get none, and
  neither does a second session's first write to the same page on the same
  day (design invariant I7).

**pm-wiki's commit cadence:** 82 commits since 2026-08-05. Gaps of up to 17
days in August and September. Since 2026-09-30 there's been a commit every 1 to
5 days, usually at the end of an ingest sweep.

**`.wiki-lock` doesn't mean a wiki session is running.** The hooks are
installed at user level, so `session-start.sh` writes the lock at the start of
every Claude Code session in any project, and `session-stop.sh` deletes it at
the end of any session. A session in this repo shows "Another wiki session may
be active" whenever another session of any kind is open, and any session's
end clears another's lock. NW10's proposal skipped its checkpoint when the
lock was held, which would skip it most of the time.

## Every reader and writer of snapshots

| Component | What it does with snapshots today | Under option 5 (recommended) |
|---|---|---|
| wiki-search server | Indexes `_archive/`: semantic and global search, backlinks, outline | Sees the 6 retired pages only |
| `grep -r "$WIKI"` in the skills: core §4 and `update-guide.md`, `ingest-guide.md`, `llm-wiki-research`, `llm-wiki-prd`, `privacy-guide.md` | Reads `_archive/` | Sees the 6 retired pages only |
| `grep` scoped to page folders (`llm-wiki-brief`, `llm-wiki-research` stub scan) | Doesn't read it | Unchanged |
| `backlinks.py` | Scans `_archive/` (`WIKI_DIRS`) | Scan dropped (NW7 step 1) |
| Obsidian | Ignores `_archive/` (`userIgnoreFilters`) | Unchanged |
| `pre-write.sh` | Writes a snapshot before the first tool write per page per day (`overview.md` only on a whole-file replacement, `index.md` never) | Calls `checkpoint()` before the session's first write to the wiki |
| `session-start.sh` | Creates `_archive/` when it scaffolds a wiki. Writes `.wiki-lock` | Also calls `checkpoint()` when the session starts in the wiki folder |
| `lint.py` | Defines `snapshot()`. `--auto-fix` snapshots each page before fixing it (three call sites) | Defines `checkpoint()`. `--auto-fix` calls it once before its first fix |
| `migrate_sources.py` | `--apply` snapshots each changed file first. Its one run (2026-09-30) is done | `--apply` calls `checkpoint()` first |
| `post-validate.sh` | Skips `_archive/` | Unchanged |
| `wikifm.resolve()` | Rejects an `_archive/` path in `sources:` | Unchanged |
| `worker-wiki-indexer`, `worker-people-updater` | Told to exclude `_archive/` | Unchanged |
| The vault contract (`meta/contract.md`) | Search hints, no word on `_archive/` | Gains the retired-page rule |
| Agents answering "undo that" | Copy a snapshot back by hand | Restore from git, after showing the diff |
| Agents making a script edit | Told to snapshot by hand first (core §4, `citation-spec.md` split step, `AGENTS.md`) | Rule removed: the checkpoint already happened |

## Options

### 1. A query rule: drop snapshot hits

Add to core `SKILL.md` §3 Query ① and §4 Update ①, `update-guide.md`'s
three-way search, the vault contract's Search Hints, and the sub-skills that
grep the whole wiki: drop snapshot hits, or read the live page they name. Add
`--exclude-dir` for the snapshot folder to each whole-wiki `grep -r`.

- **For:** docs only, no code or tests. Works for archived pages, which will
  always live somewhere searchable.
- **Against:**
  - It depends on agent behavior. NW10 showed a rule read 600 steps earlier
    being missed at the moment it applied.
  - It doesn't fix ranking. Snapshots still take 6 of 10 slots, and the
    current page in the measured query wasn't in the 10 at all. Dropping hits
    afterwards can't bring back a page that was crowded out. Agents would have
    to ask for more results every time.
  - The MCP's backlinks keep counting snapshots.
- **Where it's enough: grep.** Grep doesn't rank, so it can't crowd a page
  out: it returns every match, and each hit shows its folder. Without the
  rule, grep costs noise and a chance of quoting a snapshot. Claude Code's own
  search tool is built on ripgrep, which may honor an `.ignore` file in the
  wiki. That would cover its searches automatically, but not `grep -r` in
  Bash. Not verified.
- **Cost:** about 10 doc edits.

### 2. Exclude snapshots in the server

- **The `directory` filter doesn't do it.** It's one include prefix, not an
  exclusion. `semantic_search` applies it after retrieving
  `max(3 × k, 20)` candidates, so a filtered search loses recall: the measured
  query limited to `concepts/` returned 5 results for 10 asked. Searching each
  page folder separately doesn't work either, because scores are normalized
  within each call and can't be merged across calls.
- **A real exclusion is server code:** an ignore list (for example a
  `VAULT_IGNORE` variable) applied in `listNotes()` and in the watcher's
  change handler. That means the fork in NW2, or an upstream pull request to a
  maintainer who hasn't responded since June 2026.
- **For:** fixes the MCP's search and backlinks at the source, and keeps
  snapshots inside the wiki.
- **Against:** owns a Node/TypeScript build (NW2's cost). Grep still needs
  option 1's rule.
- **Cost:** NW2's, plus the patch and a test.

### 3. Move snapshots out of the wiki folder

`snapshot()` writes to a folder outside the wiki instead of `_archive/`, for
example a sibling `~/Projects/pm-wiki-snapshots/`. A hidden folder inside the
wiki (`.snapshots/`) doesn't help, since the server lists dot folders, and so
does `grep -r`.

- **For:** fixes every reader at once with no agent behavior and no server
  code.
- **Against:**
  - **It leaves the wiki's Claude project.** pm-wiki is the folder wiki
    sessions run in. The hooks would still write snapshots there, since they
    are scripts. But Claude reading one back to undo a change needs a
    permission approval, or the folder added to pm-wiki's Claude settings
    (`permissions.additionalDirectories` in `.claude/settings.json`). The
    desktop app opens only files inside a session's folders, so a snapshot
    path in a wiki session isn't clickable. Whether the settings entry changes
    that isn't verified.
  - Snapshots leave pm-wiki's git and GitHub.
  - The snapshot path differs from upstream's `_archive/<slug>-<date>.md`.

### 4. Combinations that keep snapshots

- **2 with 1, snapshots split into `_snapshots/` inside the wiki:** the server
  ignores only `_snapshots/`, so the 6 retired pages in `_archive/` stay
  searchable. Snapshots stay in the project and in git, moved with `git mv`.
  Grep depends on the rule, which is acceptable because grep can't crowd pages
  out. A snapshot name no page can have, such as `<slug>@<date>.md` (slugs
  allow only letters, digits, `.`, `_` and `-`, per `wikifm.ID_RE`), would end
  NW7's same-name class for readers without the ignore list. This was the
  recommendation before option 5, and is now the alternative.
- **3 with a light 1:** the only way to keep snapshots and fix the server
  without NW2, at the cost of the project boundary.
- **2 with 1, snapshots left in `_archive/`:** the server ignores all of
  `_archive/`. Nothing moves, but the 6 retired pages disappear from the
  server's search along with the snapshots.
- **2 on top of 3:** redundant.

None of these closes NW10's gap: script, Bash and Obsidian writes still get no
snapshot, and a second session the same day gets none either. NW10's proposal
would still be needed alongside them.

### 5. Drop snapshots and rely on git, with checkpoint commits

Stop creating snapshots. Before a session first changes the wiki, commit any
uncommitted changes, so the state the session started from is always in git.
This takes in NW10's checkpoint and makes its snapshot fill unnecessary.

**Where it lives (your fork):** one function, `checkpoint(wiki, reason)` in
`lint.py`, replacing `snapshot()`. It:

- does nothing unless the wiki is a git work tree with uncommitted changes
  other than `_status.md`;
- skips when a merge, rebase or cherry-pick is in progress;
- runs `git add -A -- . ':(exclude)_status.md'` and commits with a message
  starting `checkpoint:` and naming the reason;
- is best-effort: if git fails (for example another session holds
  `index.lock`), it skips without raising, and the caller says so in its
  report.

**Who runs it:**

| Caller | When | Covers |
|---|---|---|
| `pre-write.sh` | The first wiki write of a session, from any project. A marker file per session ID in the temporary folder stops later calls | Write, Edit, MultiEdit and MCP writes, and anything the session does after its first such write, Bash included |
| `session-start.sh` | When the session's working folder (the hook input's `cwd`) is the wiki | Sessions in pm-wiki that write only through Bash or scripts |
| `lint.py --auto-fix` | Once, before its first fix | Lint run by hand or by a skill, from any project |
| `migrate_sources.py --apply` | Before it writes | A rerun of the migration |

No caller checks `.wiki-lock`: it doesn't show whether a wiki session is
running (see above). When sessions overlap, a checkpoint can include the other
session's half-done edits. For a backup that's harmless: it records what was on
disk, and the other session's own commit holds the rest.

**What it covers, compared with snapshots.** "Yes" means the page as it was
before the write can be restored. A checkpoint restores the state at the
session's first write, as a snapshot restores the state at the day's first
write.

| Write | Snapshot | Checkpoint |
|---|---|---|
| A session's first tool write to a page | Yes, once per page per day | Yes |
| A second session's write to the same page the same day | No | Yes |
| Bash or script writes in a session started in pm-wiki | No | Yes (session start) |
| Bash or script writes from another project, after a tool write | No | Yes (first write) |
| Bash or script writes only, from another project | No | No |
| Obsidian edits by the user | No | Committed at the next checkpoint |
| Text written earlier in the same session, then damaged | No | No |
| `overview.md` replaced wholesale | Yes | Yes |

The one gap both share, script-only writes from another project, could be
closed by a pre-write check on Bash commands that name the wiki path. That's
optional and not proposed.

**Undo.** The agent finds the commit with `git log -- <path>`, shows the diff,
and restores with `git restore --source=<commit> -- <path>`. Core §4 says so.
The user doesn't need to know the commands. Restoring the same day's earlier
work in the same session isn't covered, as it isn't now. On 2026-09-22 it came
from the agent's context.

**Every reader of snapshots** is covered by deleting them: the table above.
Search, grep and `backlinks.py` see only the 6 retired pages, and NW7's
same-name class loses its snapshot half.

**Tests:** the snapshot tests become checkpoint tests (24 references to
`snapshot` across `test_write_hooks.py`, `test_hooks.py`, `test_lint.py`,
`test_migrate_sources.py` and `test_wikifm.py`). The temporary wikis need
`git init`. Cases:

- a clean tree makes no commit, a dirty one makes one, without `_status.md`;
- no commit during a merge or rebase, or when the folder isn't a git repo, and
  no error;
- a held `index.lock` makes it skip without raising;
- `pre-write.sh` commits once per session, however many writes follow;
- `session-start.sh` commits only when `cwd` is the wiki;
- `--auto-fix` commits before its first fix;
- nothing is written to `_archive/`.

`tests/conftest.py`'s `WIKI_PATH` guard matters more here, since a test that
reached pm-wiki would commit in it.

**Docs:**

- **The rule:** `AGENTS.md` "Snapshot before destructive ops" becomes a
  checkpoint rule with no by-hand step. The by-hand parenthetical goes from
  core `SKILL.md` §4 and `citation-spec.md`'s split step.
- **Undo:** core `SKILL.md` §4.
- **The Architecture line:** `_archive/` becomes "retired pages".
- **Other mentions:** `lint-guide.md`, `citation-spec.md` (page naming and the
  Archive bullet), `llm-wiki-research` (two lines), `hooks/README.md`
  (pre-write and session-start).
- **The retired-page rule** in core §3 ① and §4 ①, `update-guide.md`, and the
  vault contract.
- **Fork records:** design invariant I7's guarantee text, the fork changelog
  (PATCH-5 introduced `snapshot()`), and NW1's line that the pre-write
  snapshot mitigates the indexer's overview regeneration.

**Migration:**

1. With pm-wiki committed, `git rm` the 441 snapshots and the empty
   `_archive/briefings/` in one commit, with the user's OK. Git keeps every one
   in its history.
2. Point `overview.md`'s "Pre-2026-10-06 text" at `7db03cd:overview.md`, shown
   as a diff first.
3. Check the server: the watcher drops deleted files, and a `system` reindex
   settles the backlinks (NW7). Rerun the measured query and expect no
   snapshot hits.

**Upstream:** upstream's pre-write hook snapshots into `_archive/` too (its
PLUGIN-REVIEW item A4), so this diverges further, in `pre-write.sh` (already
fork code since PATCH-5), `lint.py`, `AGENTS.md`, the core skill and the
tests. The search problem goes up as an issue with these measurements and this
approach. A wiki that isn't a git repo would have no undo at all under this
option, which upstream would need to handle. Your fork has one wiki, in git.

**Cost:**

- About 40 lines of code (`checkpoint()`, the per-session marker, the
  session-start call), with about 20 lines of snapshot code removed.
- About 60 lines of tests rewritten, about 14 doc edits, and one `git rm`
  commit in pm-wiki.
- No Node build, and NW2 isn't needed.
- **Commits:** at most one per session that writes to the wiki while it has
  uncommitted changes, plus `--auto-fix` runs. Ingest sweeps usually end with a
  commit, so the next session often starts clean and makes none. The
  `checkpoint:` prefix lets `git log --invert-grep --grep='^checkpoint:'` hide
  them. Count them for a week after it lands.

**Against:**

- Automatic, unreviewed commits in pm-wiki, including other sessions'
  half-done edits.
- Undo goes through git. The agent runs it, but a restore picks a commit
  instead of copying a dated file.
- A wiki-writing session that isn't in pm-wiki and writes only through Bash
  gets no checkpoint, as it gets no snapshot today.
- More divergence from upstream.

## Comparison

| | Option 5: checkpoints, no snapshots | 2 + 1 with `_snapshots/` (NW2) |
|---|---|---|
| Search results | Fixed: no snapshots to find | Fixed: the server ignores them |
| grep | Nothing to skip but 6 retired pages | Depends on the rule |
| Needs NW2's Node build | No | Yes |
| NW10's script-write gap | Closed, except script-only writes from other projects | Still open, needs NW10 too |
| A second session the same day | Covered | Not covered |
| Undo | Agent restores from git | Agent copies a file back |
| Files or commits added | A few checkpoint commits | 10 to 34 snapshot files per ingest day |
| Rules agents must remember | None for backups | "Snapshot by hand before a script edit", plus grep |
| Divergence from upstream | Larger | Smaller |

## Recommendation

**Option 5, with the retired-page rule and `backlinks.py` dropping `_archive`.**
It fixes the search problem without NW2, covers more writes than snapshots do,
and removes the one backup rule agents depend on. Snapshots were never used for
an undo. The case against it is automatic commits, which are cheap to filter
out and are what NW10 already proposed. If they're unwanted, the alternative is
`_snapshots/` with NW2's ignore list, which also needs NW10 to close the script
gap.

## To approve

- Automatic `checkpoint:` commits in pm-wiki, including another session's
  half-done edits when sessions overlap.
- Deleting the 441 snapshots from `_archive/` (all kept in git history).
- Step 1 now (`backlinks.py` and the retired-page rule), independent of the
  rest.
- `overview.md`'s pointer to `7db03cd:overview.md`.
