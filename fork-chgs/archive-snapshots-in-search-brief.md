# Archive Snapshots in Search Brief

created: 2026-10-08

Pre-write snapshots in pm-wiki's `_archive/` outrank the live pages they copy
in wiki-search results, and they make up most of what `grep -r` and
`backlinks.py` return. This brief measures the problem, lists every reader of
`_archive/`, and weighs four options. It recommends keeping snapshots inside
pm-wiki in their own `_snapshots/` folder, which the wiki-search server ignores
through an ignore list added under NW2, with a query rule for grep. Moving
snapshots outside the wiki is the fallback if NW2 stays deferred, because it
puts them outside the wiki's Claude project.

Status: proposal, awaiting approval. Nothing is implemented.
Backlog item: NW12 in the [llm-wiki-pm Fork Backlog](llm-wiki-pm-fork-backlog.md).
Related: NW7 (an `_archive/` copy steals a live page's backlinks), NW2 (the
deferred fork of the MCP server), NW10 (script writes get no snapshot).

## Recommendation in brief

1. **Now, without waiting for NW2:** `backlinks.py` drops `_archive` from its
   folder list (NW7's step 1), and the query and update steps gain a rule:
   skip snapshot hits, and treat a hit under `_archive/` as a retired page.
   This doesn't undo the crowding in search results, but it keeps agents from
   quoting snapshots as current.
2. **Do NW2, with an ignore list as its first fix.** The fork of
   `mcp-markdown-vault` reads a list of folders to ignore from an environment
   variable, set by your fork's `wiki-search.sh`.
3. **Move snapshots into `_snapshots/` inside pm-wiki.** `snapshot()` in
   `lint.py` writes there, the server ignores it, and Obsidian's filter hides
   it. Snapshots stay in the wiki's Claude project and in its git.
4. **`_archive/` keeps the 6 retired pages,** still searchable, labelled by the
   rule in step 1.
5. **If NW2 stays deferred:** move snapshots outside the wiki instead (option
   3), and add that folder to pm-wiki's Claude settings so wiki sessions can
   still reach it.

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
  holds 435 of the wiki's 1,002 `.md` files.
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

**What's in `_archive/`** (435 files, 4.3 MB, all tracked by pm-wiki's git and
pushed to GitHub):

- **429 snapshots,** named `<slug>-<YYYY-MM-DD>.md`: of live pages, of
  `overview.md`, `SCHEMA.md`, `index.md` and `meta/contract.md`, and of four
  plugin pages since moved out of the wiki. 123 date from the citation
  migration on 2026-09-30. Ingest days add 10 to 34.
- **5 superseded entity pages** with `superseded_by:` (`bill.md` and four
  first-name pages merged into full-name pages in August).
- **1 page moved by hand,** `cfp-ai-tokenization-history-2026-08-10.md`
  (NW7's M1).
- An empty `briefings/` folder, left by the brief rotation that step 2 of the
  sources design removed.

**Two new facts for NW7:**

- **A second same-name copy.** Two `_archive/` files share a live page's file
  name, not one. The second, `cfp-mcp-ai-insights-history-2026-09-30.md`, is
  a snapshot. The migration snapshotted the then-live page
  `cfp-mcp-ai-insights-history` on 2026-09-30, giving it the name
  `<slug>-2026-09-30`. On 2026-10-06 a history split named a new live page
  `cfp-mcp-ai-insights-history-2026-09-30`, by its end date. A snapshot's name
  can equal a split page's name whenever a page's slug ends in `-history`.
- **One live pointer into `_archive/`.** `overview.md` line 16 says the "full
  prior text is in `_archive/overview-2026-10-06.md`", a snapshot taken when
  the overview was condensed. No `[[wikilink]]` in a live file points at a
  name that exists only in `_archive/`.

**What hasn't happened:** no `_archive/` file was ever changed after it was
created (pm-wiki's git history, 2026-10-08). So the harm is to reading, not
writing: stale text in answers, and live pages crowded out of the top results.

## Every reader of `_archive/`

| Reader | What it does with `_archive/` today | After the recommendation |
|---|---|---|
| wiki-search server | Indexes it: semantic and global search, backlinks, outline | Ignores `_snapshots/`. Sees the 6 retired pages in `_archive/` |
| `grep -r "$WIKI"` in the skills: core §4 and `update-guide.md`, `ingest-guide.md`, `llm-wiki-research`, `llm-wiki-prd`, `privacy-guide.md` | Reads it | Skips `_snapshots/` where the command says so (`--exclude-dir`). Agents' own greps depend on the rule |
| `grep` scoped to page folders (`llm-wiki-brief`, `llm-wiki-research` stub scan) | Doesn't read it | Unchanged |
| `backlinks.py` | Scans it (`WIKI_DIRS`) | Scans neither folder (NW7 step 1) |
| Obsidian | Ignores it (`userIgnoreFilters`) | Ignores both folders |
| `lint.py` | Never reads it. Writes snapshots through `snapshot()` before `--auto-fix` changes | Writes to `_snapshots/` |
| `pre-write.sh` | Writes snapshots through `snapshot()`. Exempts `_archive/` from the freshness gate | Writes to `_snapshots/`. Exempts both folders |
| `post-validate.sh` | Skips it (not a page folder) | Skips both, unchanged |
| `session-start.sh` | Creates it when it scaffolds a new wiki | Unchanged. `snapshot()` creates `_snapshots/` when needed |
| `migrate_sources.py` | Writes snapshots through `snapshot()`. Moved `_archive/briefings/` back and flagged `_archive/README-*` | Writes to `_snapshots/`. Its one run (2026-09-30) is done |
| `wikifm.resolve()` | Rejects an `_archive/` path in `sources:` | Also rejects a `_snapshots/` path |
| `worker-wiki-indexer`, `worker-people-updater` | Told to exclude it | Told to exclude both |
| The vault contract (`meta/contract.md`) | Search hints, no word on `_archive/` | Gains the query rule |
| Agents answering "undo that" | Read a snapshot back by hand | Read it from `_snapshots/`, inside the project |

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

`snapshot()` writes to a folder outside the wiki instead of `_archive/`.
Archived and superseded pages stay in `_archive/`.

- **Where:** it has to be outside the wiki folder. A hidden folder inside it
  (`.snapshots/`) doesn't help, since the server lists dot folders, and so does
  `grep -r`. Two candidates:
  - **A sibling folder,** `<wiki>-snapshots/`, here
    `~/Projects/pm-wiki-snapshots/`. Visible in Finder next to the wiki, found
    from the wiki path with no setting, and the tests' temporary wikis
    (`tmp_path / "wiki"`) get a temporary sibling for free. `~/Projects` isn't
    a git repo or a vault.
  - **A state folder,** `~/.local/state/llm-wiki-pm/snapshots/pm-wiki/`.
    Hidden from the user, and tests would need a variable to keep out of the
    home folder.

  The sibling is simpler. No setting is proposed, since the fork has one wiki.
- **For:** fixes every reader at once with no agent behavior and no server
  code, including readers not listed here. Removes the snapshot side of NW7's
  same-name class. The code change is one function.
- **Against:**
  - **It leaves the wiki's Claude project.** pm-wiki is the folder wiki
    sessions run in. The hooks would still write snapshots there, since they
    are scripts. But Claude reading one back to undo a change needs a
    permission approval, or the folder added to pm-wiki's Claude settings
    (`permissions.additionalDirectories` in `.claude/settings.json`). The
    desktop app opens only files inside a session's folders, so a snapshot
    path in a wiki session isn't clickable. Whether the settings entry changes
    that isn't verified.
  - **Snapshots leave pm-wiki's git,** so they're no longer pushed to GitHub.
    That loses little: a snapshot is the page's state before its first change
    of the day, which matches the last commit unless the page changed since.
  - The snapshot path differs from upstream's `_archive/<slug>-<date>.md`.
- **Variant 3b, rely on git and drop snapshots:** ruled out for now. It depends
  on NW10's checkpoint commits, which are undecided, and the user commits
  rarely. A file copy is also an easier undo for a user learning git.

### 4. Combinations

- **2 with 1, snapshots split into `_snapshots/` inside the wiki
  (recommended):** the server ignores only `_snapshots/`, so the 6 retired
  pages in `_archive/` stay searchable. Snapshots stay in the project and in
  git. The split is a move, but inside the repo, so git keeps each file's
  history as a rename. Grep depends on the rule, which is acceptable because
  grep can't crowd pages out.
- **3 with a light 1 (the fallback if NW2 stays deferred):** the only option
  that fixes the server without NW2. It needs the settings entry to bring the
  snapshots back into the project's reach.
- **2 with 1, snapshots left in `_archive/`:** the server ignores all of
  `_archive/`. Nothing moves, but the 6 retired pages disappear from the
  server's search along with the snapshots. Not recommended.
- **2 on top of 3:** redundant. With snapshots outside the wiki, an ignore list
  adds nothing.

In every option, `backlinks.py` dropping `_archive` is a code change, not a
rule.

## The recommended change

### Step 1, now (your fork)

- `backlinks.py`: drop `_archive` from `WIKI_DIRS`. This belongs to NW7's
  step 1, which already rewrites that list, so it lands with NW7 or first,
  whichever comes sooner.
- **The query rule,** in core §3 ① and §4 ①, `update-guide.md`'s three-way
  search, and the vault contract's Search Hints (template and pm-wiki's
  `meta/contract.md`): "Skip snapshot hits; if one matters, read the live page
  it copies. A hit under `_archive/` is a retired page: say so if you use it,
  and prefer the live page it names." Whole-wiki `grep -r` commands in the
  skills gain `--exclude-dir` for the snapshot folder (`_archive` until the
  move, `_snapshots` after).

### Step 2, the server (NW2)

- The fork of `mcp-markdown-vault` reads a list of folders to ignore from an
  environment variable (for example `VAULT_IGNORE`) and applies it in
  `listNotes()` and the watcher's change handler, with a vitest regression
  test. That covers search, `global_search`, the backlink index and outline.
  It goes upstream as a pull request, like NW2's other fixes.
- Your fork's `wiki-search.sh` sets the variable to `_snapshots/` unless it's
  already set, and runs the pinned fork build. The LaunchAgent needs no change
  beyond NW2's repointing. `test_wiki_search.py` checks the variable.

### Step 3, the snapshot folder (your fork)

- `lint.py`: `snapshot()` writes to `wiki / "_snapshots"` instead of
  `wiki / "_archive"`. Callers don't change: `pre-write.sh`, `--auto-fix` and
  `migrate_sources.py` all go through it.
- `pre-write.sh`: the header comment's path, and `EXEMPT_DIRS` gains
  `_snapshots/`.
- `wikifm.resolve()`: a `_snapshots/` path in `sources:` gets "a snapshot isn't
  a source", as `_archive/` does.
- `migrate_sources.py`: the two "snapshotted to `_archive/` first" messages.

**Snapshot names.** Inside the wiki, snapshot names still share the file-name
space with live pages, so NW7's same-name class remains for any reader that
finds pages by name without the ignore list (Obsidian's link resolution is not
verified). A name no page can have would close it: slugs allow letters,
digits, `.`, `_` and `-` (`wikifm.ID_RE`), so `<slug>@<date>.md` can never
equal a page name. To decide.

### Tests

Snapshot-path assertions move to `_snapshots/`: `test_write_hooks.py` (the
`snaps` helper, the path check, `test_creates_archive_dir`), `test_hooks.py`
(four globs), `test_lint.py` (two), `test_migrate_sources.py` (four paths and a
message). Add a `wikifm` case for a `_snapshots/` path and a pre-write case for
the exemption. The `_archive/briefings` and `_archive/README-*` tests and
`wikifm`'s `_archive/` case stay. The ignore list's own test lives in the
server fork.

### Docs

- **Snapshot path:** `AGENTS.md` ("Snapshot before destructive ops"), core
  `SKILL.md` §4 and the Architecture line (`_archive/` becomes "retired
  pages", plus `_snapshots/`), `lint-guide.md`, `citation-spec.md` (naming and
  the Archive bullet, which gains `_snapshots/`), `llm-wiki-research` (two
  lines), `hooks/README.md`, and GETTING_STARTED's folder tree.
- **Worker agents:** `worker-wiki-indexer` and `worker-people-updater` exclude
  `_snapshots/` as well.
- **Fork changelog:** extend PATCH-5 (it introduced `snapshot()`), with the
  reason and the upstream difference. NW2's server fork gets its own entry.
- **NW10's text** names `_archive/<slug>-<today>.md`. Its snapshot fill goes
  through `snapshot()`, so it follows the new path with no extra work.
- **The launchd guide** names the ignore variable, if NW2 sets it there rather
  than in `wiki-search.sh`.

### Migration of the 435 files

Run once, when no other wiki session holds `.wiki-lock`, after the ignore list
is live (moving first does no harm, it just doesn't help yet):

1. `git mv` the 429 snapshots into `_snapshots/`, renamed if the naming
   changes. Keep in `_archive/` the files with `superseded_by:` and NW7's M1
   file. Remove the empty `_archive/briefings/`.
2. Commit the move on its own, before any page edits, so git records renames
   (the rename lesson from earlier work).
3. Point `overview.md` line 16 at the moved file, shown as a diff first.
4. Add `_snapshots/` to `userIgnoreFilters` in `.obsidian/app.json`.
5. Check the server: rerun the measured query and expect no `_snapshots/` or
   snapshot hits. A `system` reindex settles the backlinks (NW7).

### Upstream

Upstream's own pre-write hook also snapshots into `_archive/`, and upstream
bundles the same server, so upstream wikis have the same problem. Upstream's
CONTRIBUTING counts a changed directory layout as a breaking, major-version
change, so `_snapshots/` goes up as an issue with these measurements, not a
pull request. The ignore list goes to `wirux/mcp-markdown-vault` as a pull
request with NW2's other fixes. Merging an upstream llm-wiki-pm release is
unaffected: `snapshot()` is already fork code (PATCH-5).

### Cost

- **Step 1:** 1 code line and about 10 doc edits.
- **Step 2:** NW2's cost (owning a Node/TypeScript build, a pinned build,
  repointing the LaunchAgent), plus the ignore-list patch and its test, and a
  line in `wiki-search.sh`.
- **Step 3:** about 8 code lines, about 15 test lines, about 14 doc edits, a
  one-time `git mv` of 429 files in pm-wiki, and one Obsidian setting.

The fallback, option 3, costs about 6 code lines, the same tests and docs, the
move out of the repo, and a settings entry in pm-wiki, with no Node build.

## To approve

- Whether NW2 goes ahead, with the ignore list as its first fix. This is the
  real decision: yes means the recommendation, no means the fallback.
- Step 1 now, independent of that decision.
- Snapshot names: keep `<slug>-<date>.md`, or a name no page can have, such as
  `<slug>@<date>.md`.
- `overview.md`'s pointer: to the moved file, or to git.
