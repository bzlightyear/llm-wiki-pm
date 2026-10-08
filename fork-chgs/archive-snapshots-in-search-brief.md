# Archive Snapshots in Search Brief

created: 2026-10-08

Pre-write snapshots in pm-wiki's `_archive/` outrank the live pages they copy
in wiki-search results, and they make up most of what `grep -r` and
`backlinks.py` return. This brief measures the problem, lists every reader of
`_archive/`, weighs four options, and recommends moving the snapshots out of the
wiki folder, with a short query rule for the few archived pages that stay.

Status: proposal, awaiting approval. Nothing is implemented.
Backlog item: NW12 in the [llm-wiki-pm Fork Backlog](llm-wiki-pm-fork-backlog.md).
Related: NW7 (an `_archive/` copy steals a live page's backlinks), NW2 (the
deferred fork of the MCP server), NW10 (script writes get no snapshot).

## Recommendation in brief

1. **Move snapshots out of the wiki folder,** to a sibling folder,
   `~/Projects/pm-wiki-snapshots/`. The change is one function, `snapshot()` in
   `lint.py`, which the pre-write hook, lint's `--auto-fix` and the migration
   already share. Every reader stops seeing them at once: the MCP's search and
   backlinks, `grep -r`, `backlinks.py` and Obsidian.
2. **Keep `_archive/` for archived and superseded pages only** (6 files today),
   and add one sentence to the query and update steps: a hit under `_archive/`
   is a retired page, not current.
3. **Drop `_archive` from `backlinks.py`'s folder list,** as part of NW7's
   step 1.
4. **Leave server-side exclusion to NW2.** It's not needed once snapshots are
   outside the folder. If NW2 goes ahead anyway, compare option 3 with NW2
   plus a `_snapshots/` folder inside the wiki (option 4).

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
| wiki-search server | Indexes it: semantic and global search, backlinks, outline | Sees the 6 archived pages only |
| `grep -r "$WIKI"` in the skills: core §4 and `update-guide.md`, `ingest-guide.md`, `llm-wiki-research`, `llm-wiki-prd`, `privacy-guide.md` | Reads it | Sees the 6 archived pages only |
| `grep` scoped to page folders (`llm-wiki-brief`, `llm-wiki-research` stub scan) | Doesn't read it | Unchanged |
| `backlinks.py` | Scans it (`WIKI_DIRS`) | Scan dropped (NW7 step 1) |
| Obsidian | Ignores it (`userIgnoreFilters`) | Unchanged, filter kept |
| `lint.py` | Never reads it. Writes snapshots through `snapshot()` before `--auto-fix` changes | Writes to the new folder |
| `pre-write.sh` | Writes snapshots through `snapshot()`. Exempts `_archive/` from the freshness gate | Writes to the new folder. Exemption kept |
| `post-validate.sh` | Skips it | Unchanged |
| `session-start.sh` | Creates it when it scaffolds a new wiki | Unchanged (archived pages still go there) |
| `migrate_sources.py` | Writes snapshots through `snapshot()`. Moved `_archive/briefings/` back and flagged `_archive/README-*` | Writes to the new folder. Its one run (2026-09-30) is done |
| `wikifm.resolve()` | Rejects an `_archive/` path in `sources:` | Unchanged. A path to the new folder is outside the wiki, rejected anyway |
| `worker-wiki-indexer`, `worker-people-updater` | Told to exclude it | Unchanged |
| The vault contract (`meta/contract.md`) | Search hints, no word on `_archive/` | Gains the query sentence |
| Agents answering "undo that" | Read a snapshot back by hand | Read it from the new folder |

## Options

### 1. A query rule: drop `_archive/` hits

Add to core `SKILL.md` §3 Query ① and §4 Update ①, `update-guide.md`'s
three-way search, the vault contract's Search Hints, and the sub-skills that
grep the whole wiki: drop `_archive/` hits, or read the live page they name.
Add `--exclude-dir=_archive` to each whole-wiki `grep -r`.

- **For:** docs only, no code or tests. Works for archived pages, which will
  always live somewhere searchable.
- **Against:**
  - It depends on agent behavior. NW10 showed a rule read 600 steps earlier
    being missed at the moment it applied.
  - It doesn't fix ranking. Snapshots still take 6 of 10 slots, and the
    current page in the measured query wasn't in the 10 at all. Dropping hits
    afterwards can't bring back a page that was crowded out. Agents would have
    to ask for more results every time.
  - `backlinks.py` and the MCP's backlinks keep counting snapshots.
- **Cost:** about 10 doc edits.

### 2. Exclude `_archive/` in the server

- **The `directory` filter doesn't do it.** It's one include prefix, not an
  exclusion. `semantic_search` applies it after retrieving
  `max(3 × k, 20)` candidates, so a filtered search loses recall: the measured
  query limited to `concepts/` returned 5 results for 10 asked. Searching each
  page folder separately doesn't work either, because scores are normalized
  within each call and can't be merged across calls.
- **A real exclusion is server code:** an ignore list (for example a
  `VAULT_EXCLUDE` variable) applied in `listNotes()` and in the watcher's
  change handler. That means the fork in NW2, or an upstream pull request to a
  maintainer who hasn't responded since June 2026.
- **For:** fixes the MCP's search and backlinks at the source.
- **Against:** owns a Node/TypeScript build (NW2's cost), and still leaves
  `grep -r` and `backlinks.py` exposed.
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
- **What's lost:** snapshots leave pm-wiki's git, so they're no longer pushed
  to GitHub. Little is lost: a snapshot is the page's state before its first
  change of the day, which matches the last commit unless the page changed
  since. NW10's checkpoint, if adopted, would make that true every time.
- **For:** fixes every reader at once with no agent behavior, including
  readers not listed here. Removes the snapshot side of NW7's same-name class.
  The code change is one function.
- **Against:** the snapshot path differs from upstream's `_archive/<slug>-<date>.md`.
  Agents need to learn the new path for "undo that last change."
- **Variant 3b, rely on git and drop snapshots:** ruled out for now. It depends
  on NW10's checkpoint commits, which are undecided, and the user commits
  rarely. A file copy is also an easier undo for a user learning git.

### 4. Combinations

- **3 with a light 1 (recommended).** 3 removes 429 of 435 files from every
  reader. The 6 archived pages that stay are retired on purpose, carry
  `superseded_by:` (5 of them), and may be wanted, so a rule that labels them
  fits better than a filter that hides them.
- **2 with 1, snapshots left in `_archive/`:** the server excludes all of
  `_archive/`, which fixes the MCP's search and backlinks. Grep still needs
  `--exclude-dir=_archive` in the skills' commands and a rule for agents' own
  greps, so it depends on agent behavior where option 3 doesn't. The 6
  archived pages become unsearchable through the MCP, which is probably
  acceptable, since they can still be read by path. Snapshots stay in
  pm-wiki's git. It costs NW2's build.
- **2 with 1, snapshots split into `_snapshots/` inside the wiki:** the same,
  except the server excludes only `_snapshots/`, so the archived pages stay
  searchable. The split is still a move, but inside the wiki, and snapshots
  stay in git. This is the strongest combination if NW2 goes ahead for its
  own reasons (#47, #49), since the exclusion then costs only a patch and a
  test.
- **2 on top of 3:** redundant. With snapshots outside the wiki, an ignore list
  adds nothing.

In every option, `backlinks.py` dropping `_archive` is a code change, not a
rule.

## The recommended change

### Code (your fork)

- `lint.py`: `snapshot()` writes to `wiki.parent / f"{wiki.name}-snapshots"`
  instead of `wiki / "_archive"`. Its docstring says so. Callers don't change:
  `pre-write.sh` passes the resolved wiki path, and `--auto-fix` and
  `migrate_sources.py` pass theirs.
- `pre-write.sh`: the header comment's path. `EXEMPT_DIRS` keeps `_archive/`.
- `migrate_sources.py`: the two "snapshotted to `_archive/` first" messages.
- `backlinks.py`: drop `_archive` from `WIKI_DIRS`. This belongs to NW7's
  step 1, which already rewrites that list, so it lands with NW7 or first,
  whichever comes sooner.

### Tests

Snapshot-path assertions move to the sibling folder: `test_write_hooks.py`
(the `snaps` helper, the path check, `test_creates_archive_dir`),
`test_hooks.py` (four globs), `test_lint.py` (two), `test_migrate_sources.py`
(four paths and a message). Add one test that a snapshot never lands under the
wiki folder. The `_archive/briefings` and `_archive/README-*` tests and
`wikifm`'s "isn't a source" case stay.

### Docs

- **Snapshot path:** `AGENTS.md` ("Snapshot before destructive ops"), core
  `SKILL.md` §4 and the Architecture line (`_archive/` becomes "archived and
  superseded pages"), `lint-guide.md`, `citation-spec.md` (naming and the
  Archive bullet), `llm-wiki-research` (two lines), `hooks/README.md`.
- **Query sentence,** in core §3 ① and §4 ①, `update-guide.md`'s three-way
  search, and the vault contract's Search Hints (template and pm-wiki's
  `meta/contract.md`): "A hit under `_archive/` is a retired page: say so if
  you use it, and prefer the live page it names."
- **Fork changelog:** extend PATCH-5 (it introduced `snapshot()`), with the
  reason and the upstream difference.
- **NW10's text** names `_archive/<slug>-<today>.md`. Its snapshot fill goes
  through `snapshot()`, so it follows the new path with no extra work.

### Migration of the 435 files

Run once, by hand or a short script, when no other wiki session holds
`.wiki-lock`:

1. Move the 429 snapshots to `~/Projects/pm-wiki-snapshots/`. Keep in
   `_archive/` the files with `superseded_by:` and NW7's M1 file. Remove the
   empty `_archive/briefings/`.
2. Point `overview.md` line 16 at the new path, or at git, shown as a diff
   first.
3. Commit in pm-wiki: git records the 429 files as deleted, and they stay in
   its history. The move goes in its own commit, before any page edits (the
   rename lesson from earlier work).
4. Check the server dropped them: the watcher removes deleted files from the
   index, and a `system` reindex settles the backlinks (NW7). Rerun the
   measured query and expect no `_archive/` hits.

### Upstream

Upstream's own pre-write hook also snapshots into `_archive/`, and upstream
bundles the same server, so upstream wikis have the same problem. Upstream's
CONTRIBUTING counts a changed directory layout as a breaking, major-version
change, so it goes up as an issue with these measurements, not a pull
request. Merging an upstream
release is unaffected: `snapshot()` is already fork code (PATCH-5).

### Cost

About 6 code lines, about 12 test lines, about 12 doc edits, and a one-time
move of 429 files in pm-wiki. No new settings, no Node build, no change to
how agents search.

## To approve

- The recommendation: option 3 with the light rule, and `backlinks.py`
  dropping `_archive`.
- The snapshot folder: the sibling `~/Projects/pm-wiki-snapshots/`, or the
  hidden state folder.
- `overview.md`'s pointer: to the moved file, or to git.
