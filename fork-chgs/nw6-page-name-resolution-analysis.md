# NW6 Page Name Resolution Analysis

created: 2026-09-30

The audit that NW6's first next step asks for: every component that turns a wiki
page name, link or path into a file. Each was tested on the live wiki
(read-only) and on two scratch copies, one as it is and one with the proposed
fix applied. It ends with the options for fixing NW6, the one chosen, and its
implementation plan.

revised on: 2026-10-01
Replaced the proposed design, implementation and open decisions (sections
9–11) with the options considered, the decision (option 4: name a folder page
after its folder and delete the `README.md` rule) and its implementation plan.
The proposals had grown far beyond the problem.

Status: done. Option 4 is implemented, and NW6 steps 1-3 are closed (section 10).

Companion to [Sources and References Design](sources-and-references-design.md)
(NW6 in section 10) and
[Wiki-Search MCP Tools Analysis](wiki-search-mcp-tools-analysis.md).

The four folder pages are named by topic: three research sprints (Kiro, IBM Bob,
OpenAI Codex) and one PRD. Every other page is described by kind and count,
never by name.

---

## 1. Summary

- **The fix works for every reader tested.** 57 links point at the four
  folder pages (32 outside `_archive/`). With each folder's main page named
  `queries/<slug>/<slug>.md`, every reader resolves every one it reads as a link.
  Obsidian doesn't treat 4 of them, inside frontmatter strings, as links. Today
  the wiki-search MCP, Obsidian and an agent's lookup by file name resolve none
  of them. Lint's output is identical before and after, because no slug
  changes.
- **The wiki change is small.** 4 renames, 6 prose lines on 3 pages, 2 lines in
  the wiki's `meta/contract.md`, and a log entry. No link, `sources:` entry or
  citation names a folder page's path.
- **Running MCP servers don't see a renamed or new page until they rebuild.**
  The MCP maps names to files once, at startup. After the rename, a running
  server still reported 0 backlinks. `system(action=reindex)` fixed it after
  about 105 s, and a fresh server was correct at once. With one server per
  open session (NW5), each one needs the reindex or a restart. The same holds
  for any page created after a server starts: a new page and a new link to it
  gave 0 backlinks 30 s later.
- **`slug()`'s `README.md` rule is only needed by wikis not yet renamed.** On
  the fixed copy, lint without the rule gives identical output. On today's
  copy, it reports 23 broken links, 4 orphans and 4 index gaps.
- **`backlinks.py` can't serve as the link search for archive, supersede and
  rename as it is (NW6 step 4).** It doesn't read `briefings/`, `index.md`,
  `overview.md` or the other root files, where 747 links to live pages sit
  today.
- **Five other mismatches, and three minor ones,** turned up (section 7). The biggest: an archived
  copy of a live page kept the page's exact file name, so the MCP credits that
  page's 10 inbound links to the archive file and reports 0 for the live page.
  Also, `overview.md` links twice to an archived page, and nothing checks the
  links in `overview.md` or `index.md`.
- **Nothing in this setup depends on the name `README.md`.** GitHub's folder
  view would, but the wiki isn't browsed there. The fork's own uses are the
  `slug()` rule, a copy of it in `backlinks.py`, the migration's handling of
  old `_archive/README-*.md` snapshots, 19 doc lines and test fixtures.

## 2. Method

Measured 2026-09-30 against the live wiki at commit `9064297`.

- **Copies.** Two rsync copies of the working tree, `.git` and the MCP's index
  included. Each copy had its git remote removed, Obsidian Sync turned off, and
  its own `.wiki-path` pointed at itself. The wiki tracks a `.wiki-path` that
  names the live wiki, so a tool started inside an unchanged copy would have
  fallen back to live.
- **Link census.** A scratch script listed every `[[…]]`, `![[…]]`, markdown
  link and escaped `\[\[` in all 838 `.md` files (dot folders excluded, as
  Obsidian does). It recorded each link's form, whether it sits in
  frontmatter, a code span or body text, and its target. For each link, it
  computed:
  - the target under `slug()` over lint's page set, which is what the design
    means a link to name;
  - what lint, `backlinks.py` and `post-write.sh` do with it;
  - an agent's lookup by file name;
  - the MCP's resolution, using the installed package's own `WikilinkResolver`
    and `BacklinkIndexService` classes.
- **MCP end to end.** A separate wiki-search server was started on each copy
  with `WIKI_PATH` unset and driven over stdio, with no change to Claude Code's
  config. The calls were `backlinks` and each path-taking action.
- **Live, read-only.** The same `backlinks` and path calls through the
  session's own wiki-search server gave the same results as the unchanged
  copy, so the copy stands in for live.
- **Trial.** The fix was applied to the second copy as a real change would be
  (section 6). Then the census, lint and the MCP checks were repeated.
- **Obsidian.** The user opened both copies as vaults and ran a console
  snippet (Appendix A). It dumps Obsidian's own link resolution for every
  link. The user ran it before clicking anything, then clicked, hovered and
  searched through a short checklist.

The scripts were throwaway and aren't kept. The snippet is.

## 3. Readers

Every component that turns a page name or path into a file. "Folder page"
means a link `[[<slug>]]` to one of the four folder pages.

| Reader | How it resolves | Files it reads | Folder page today | With the fix |
|---|---|---|---|---|
| lint (links, orphans, index, R9), post-validate, session-start counts | `slug()` over the page folders, plus `overview.md` and `index.md` as targets | 247 pages; not `_archive/`, `raw/`, root files, or lint reports | resolves (`README.md` rule) | resolves |
| `sources:` entries (`wikifm.resolve`) | the path must exist | pages | none name a folder page | unchanged |
| citations, snapshots (`lint.snapshot`) | `slug()` | pages | resolve | resolve |
| `backlinks.py` | its own copy of the README rule; matches the link text | `entities/`, `concepts/`, `comparisons/`, `queries/`, `_archive/` | finds them | finds them |
| `lint --auto-fix` supersede rewrite | `slug()` | page folders only | n/a | n/a |
| `post-write.sh` (not registered in `hooks.json`, still shipped and tested) | `find -name "<target>.md"` in four page folders | the written file | misses | resolves |
| `capture.py` ID check | `slug()` | records and pages | n/a | n/a |
| `migrate_sources.py` | renames `_archive/README-*.md` snapshots | `_archive/` | the only code besides `slug()` and `backlinks.py` that knows the name | unchanged |
| worker-wiki-indexer (an agent, no script) | derives index entries from a file scan; no rule for folder pages | four page folders (not `briefings/`) | unspecified | file name = slug |
| worker-link-validator | `lint --json` | as lint | resolves | resolves |
| MCP `view(backlinks)` | lowercase file name over every `.md` file; shortest path wins, then alphabetical; unresolved links filed under the bare target | all 838 files | 0 (all 57 filed under the bare slug) | resolves; running servers need a reindex |
| MCP `read`, `outline`, `frontmatter_get`, `bulk_read`, `search`, `vault stat` | exact path only, no name lookup | — | only `…/README.md` works; `queries/<slug>.md` is "not found" | `queries/<slug>/<slug>.md` works |
| MCP `semantic_search`, `global_search` | return paths | all | shows `README.md` | shows the slug |
| Agent lookup by file name (Glob `**/<slug>.md`, `find -name`) | file name | all | none | unique |
| Obsidian links, hover, graph, backlinks pane | file name, ignoring case; on a tie, the match in the linking file's own folder (seen in M1) | all, except links in code, links whose text spans a line break, and links inside frontmatter strings | unresolved: dimmed, no preview, the backlinks pane shows 0, and a click creates an empty note at the root | resolves: previews, 31 backlinks for the Kiro sprint (as the MCP) |
| Obsidian quick switcher, file explorer, search | file name | all | the page is listed as `…/README`, and `file:<slug>` doesn't find it | listed under its slug; `file:<slug>` finds it |
| Dataview | — | — | installed, no queries anywhere | — |
| Bases | — | — | enabled, no `.base` files | — |
| Bookmarks | path | 2 bookmarks (`overview.md`, `SCHEMA.md`) | unaffected | unaffected |
| Orient files | hold links, aren't resolvers | `index.md` (246 links, 4 to folder pages), `overview.md` (365, none) | lint never checks either file's links | — |
| GitHub web view | renders a folder's `README.md` | — | not used for this wiki | — |

The fork's docs tell agents where folder pages live in 19 lines across 9 files
(section 10), and two docs point incoming-link searches at the MCP: the vault
contract ("Incoming links to a note → `view.backlinks`") and the core skill's
tool list.

## 4. Link forms in the wiki

12,847 links in 838 files, 7,763 of them in `_archive/`. The rows from "in a
code span" down count links by where they sit, so they overlap the first
three rows.

| Form | Count | Where | How readers differ |
|---|---|---|---|
| `[[slug]]`, no alias | 12,601 | everywhere | the folder-page and name-clash cases (sections 5, 7) |
| `[[slug\|text]]` | 241 | 89 in `_archive/` | none: every reader agrees on all 237 that resolve |
| `[[folder/name]]` | 7 real, plus 13 bash `[[ -d "$WIKI/.git" ]]` strings | `_archive/`, one in `log.md`; the bash strings are in old lint reports | lint would report path links as broken; the MCP and Obsidian resolve them. None are in pages. |
| `[[…]]` in a code span or block | 58 | none in pages | lint, `backlinks.py` and the MCP count them; Obsidian ignores them |
| `[[…]]` in frontmatter | 11 | 4 in pages, inside `gaps:` strings | lint and the MCP count them. Obsidian doesn't treat a link inside a longer string as a link, so one link to the PRD from a concept page's `gaps:` exists only for them. |
| `[[slug\|text]]` whose text wraps onto the next line | 5 | 2 in pages, 2 in records, 1 in a snapshot | lint and the MCP count them; Obsidian shows plain text (M6) |
| table-escaped `[[a\|b]]` | 1 | `log.md`, in code | none in pages |
| `![[embed]]`, `#heading`, `#^block`, `.md` suffix | 0 | — | — |
| markdown link `[text](path.md)` | 5 | 2 in a brief, 3 in a record | lint ignores them; the MCP resolves them relative to the file, so the brief's two vault-root paths don't resolve; Obsidian resolves them from the vault root |
| escaped `\[\[` | 7 | 2 `_archive/` files | no reader sees a link |

## 5. Results: links to folder pages

57 links point at the four folder pages: 32 outside `_archive/` (23 on 15
pages, 4 in `index.md`, 3 in `log.md`, 2 in a reconstructed record) and 25 in
snapshots. This confirms NW6's count.

| Reader | Today | With the fix |
|---|---|---|
| lint, post-validate | 23 of 23 in pages resolve; it doesn't read the others | same |
| `backlinks.py` | 21, 10, 8 and 9 links (Kiro, Bob, Codex, PRD) | same, plus the trial's 3 new snapshots |
| MCP `backlinks` on `…/README.md` | 0 for each, live and copy | — |
| MCP `backlinks` on the new path, fresh server | — | 31, 13, 9, 10 (all, archives included) |
| MCP `backlinks`, server running through the rename | — | 0 until `reindex`, then correct (~105 s). A page created mid-session behaves the same. |
| MCP path actions | only `…/README.md` | only `…/<slug>.md` |
| Agent lookup by file name | 0 of 57 | 57 of 57, each unique |
| Obsidian (its own metadata cache) | 0 of 53 links it sees; the other 4 are in frontmatter strings | all 53 |

On today's wiki, the MCP files the folder pages' links under the bare slug, so
`backlinks(path="<slug>")` returns them, but `backlinks` on the page's real path
returns nothing. No doc tells an agent to pass the bare slug.

## 6. Trial of the fix

Applied to the copy as a real change would be, following AGENTS.md:

1. Read the copy's Orient files.
2. Snapshot the three pages that get prose edits with lint's own `snapshot()`,
   since a Bash rename bypasses the pre-write hook.
3. `git mv` each `README.md` to `<slug>.md`.
4. Reword the lines below.
5. Append a log entry.

The prose edits:

- "(this README was over the 200-line threshold)" → "(this page was over the
  200-line threshold)", on the three research sprints.
- The sprints' "This synthesis page: `queries/<slug>/README.md`" lines → the
  new path, also on the three sprints.
- `meta/contract.md`: drop "(the folder name for a `README.md` page)" from the
  `sources` line, and change the example path `queries/research-<topic>-<date>/README.md`
  to `queries/research-<topic>-<date>/research-<topic>-<date>.md`. These two
  lines mirror the fork's `templates/vault-contract.md`, so they change with
  it.

The PRD needed only the rename. Other wiki mentions of "README" are GitHub
READMEs of the products compared, a record ID, history in `log.md` (18) and
snapshots in `_archive/` (22 files). None of them change.

Results:

- `lint.py --json`: identical to today's.
- `backlinks.py`: same counts, plus the trial's snapshots.
- Census: the MCP and agent lookups now agree with `slug()` on every folder-page
  link. The other disagreements (section 7) are unchanged, since the fix
  doesn't touch them.
- `slug()` without its `README.md` rule, in a scratch copy of the scripts:
  identical lint output on the fixed copy; 23 broken links, 4 orphans and 4
  index gaps on today's.

## 7. Other mismatches

**M1. An archived copy has a live page's exact file name.**
- **What:** one `_archive/` file is named exactly like a live concept page. The
  page's slug ends in a date, so the name looks like a snapshot's. It came
  from an archive move on 2026-08-11, not from `snapshot()`.
- **Effect:**
  - The MCP picks the `_archive/` copy for the page's 10 links (shortest path
    ties, and `_archive` sorts first), so the live page's backlinks are 0.
  - An agent's lookup by file name finds two files.
  - Obsidian prefers a match in the linking file's own folder. It gets the 4
    links from live files right and sends the 6 from snapshots to the
    archive copy.
- **Why nothing reported it:** lint doesn't read `_archive/`, so R9 can't see
  it.

**M2. Links to archived pages in files lint doesn't check.**
- **What:** `overview.md` links twice to a person stub that was superseded and
  moved to `_archive/` under its bare name, and a record links to it once.
- **Effect:** under `slug()` those links are broken. Obsidian and the MCP open
  the archived stub.
- **Why nothing fixed or reported them:** `lint --auto-fix` rewrites superseded
  links only in page folders, never in `overview.md`, `index.md` or the
  action-items file. Lint checks none of their links.

**M3. Two files are named `overview.md`.**
- **What:** the root `overview.md` and the MCP's own `meta/overview.md`.
- **Effect:** the MCP resolves all 14 `[[overview]]` links to the root file,
  as lint does, and so does Obsidian (12 links; the other 2 are in code). An
  agent's lookup finds two files.

**M4. `backlinks.py` reads only part of the wiki.**
- **What:** of the links that resolve to live pages, it misses those in:

  | Source | Links |
  |---|---|
  | `raw/` | 563 |
  | `overview.md` | 360 |
  | `index.md` | 246 |
  | the action-items file | 108 |
  | `log.md` | 100 |
  | `briefings/` | 28 |
  | `MY-INTEGRATIONS.md` | 4 |
  | lint reports | 2 |
  | `SCHEMA.md` | 1 |

  Records are immutable and the log is history, which leaves 747 links in
  files a rename or archive must update.
- **Effect:** 7 live pages have no inbound link that `backlinks.py` can see.
- **Also:** it keeps its own copy of the `README.md` rule instead of calling
  `wikifm.slug()`.

**M5. Old lint reports contain text that looks like links.**
- **What:** 13 of the 45 lint reports in `queries/` (2026-08-11 to 08-29) quote
  `[[ -d "$WIKI/.git" ]]` in body text.
- **Effect:** lint skips its own reports. Obsidian and the MCP read the
  string as an unresolved link. Later reports don't contain it.

**M6. Minor.**
- Five links have display text that wraps onto the next line,
  `[[slug|Some⏎text]]`: 2 on pages, 2 in records and 1 in a snapshot. Obsidian
  shows them as plain text, while lint and the MCP count them as links.
- A brief uses markdown links with vault-root paths, which the MCP resolves
  relative to the brief's own folder. Obsidian resolves them.
- worker-wiki-indexer gives no rule for naming a folder page in `index.md`,
  and its scan omits `briefings/`.
- `post-write.sh` is dead code: not registered in `hooks.json`, but still
  shipped and tested.

## 8. Corrections to NW6

- **"About 5 prose lines":** 6 lines on 3 pages, plus 2 in the wiki's
  `meta/contract.md`.
- **"About 10 doc lines":** 19 lines in 9 docs. On top of those, `backlinks.py`
  has its own copy of the `README.md` rule, which must change with `slug()`.
- **"Check the MCP's backlinks for each page, and reindex if it misses
  them":** every server already running will miss them. Each one needs
  `reindex` or a restart; fresh servers are correct.
- **Step 4 (archive, supersede and rename use `backlinks.py`):** as it is,
  this would leave the links in `index.md`, `overview.md`, briefs and the
  action-items file broken (M4). `backlinks.py` has to read them first.
- **Graph "phantom node":** not with this vault's settings. Its `graph.json`
  sets `hideUnresolved: true`, so an unresolved target has no node. Once a click
  has created the root note, that empty note is a real node holding every link,
  and clicking it opens a blank page.
- **Clicking a folder link creates a root note:** confirmed. Hovering says the
  file isn't created yet, and a click creates an empty
  `<slug>.md` at the vault root. From then on the quick switcher and
  `file:` search find that note instead of the page.
- **Confirmed as stated:** the 32 links and how they split, the MCP's 0
  backlinks (live too), `backlinks.py`'s 21 links on 15 pages for the Kiro
  sprint, no `sources:` entry or citation naming a folder page, and
  `attachmentFolderPath` still `raw/attachments` (step 5).

## 9. Options and decision

Decided 2026-10-01. The first version of this analysis (`1ca53ef`) ended with
a design for NW6 and for every other mismatch: two new lint rules (R14, R15),
an archive command, a `backlinks.py` rewrite and lint checks on the Orient
files' links. Each proposal exposed further gaps, and the whole grew far
heavier than the problem. Two later commits expanded it further and were
reverted. This section and section 10 replace it.

**Core requirement:** a link to a folder page opens the same file in lint,
Obsidian, the wiki-search MCP and an agent's lookup by file name, for today's
four folder pages and for any made later.

Two facts checked after the audit:

- **The `README.md` rule exists only in the fork.** Upstream's docs say to
  save a folder page as `README.md`, but upstream's lint names a page by its
  file name only (`slug = path.stem`, `queries/` included). So upstream's own
  lint can't resolve these links either. The fork added the rule to lint and
  `backlinks.py` on 2026-08-11 (PATCH-3b and PATCH-2 in the
  [fork changelog](llm-wiki-pm-fork-changelog.md)) and moved it into
  `wikifm.slug()` on 2026-09-30.
- **The fork has one user and one wiki, the PM wiki.** No other wiki needs the
  rule kept.

**Options**, simplest first:

1. **Roll back and do nothing.** Revert this analysis's commits. Nothing is
   fixed: Obsidian and the MCP keep missing the 57 links, and an archive that
   finds incoming links through the MCP misses the 23 on pages (lint reports
   them as broken only afterwards). NW6 would also keep the errors section 8
   corrects.
2. **Rename the four pages in the wiki only.** Fixes today's links for every
   reader, with lint's output unchanged. The skills still say `README.md`, so
   the next research sprint or PRD brings the gap back, and lint, which knows
   the rule, reports nothing.
3. **Option 2 plus the fork's docs, keeping the rule.** 19 lines in 9 files.
   New folder pages are fixed when agents follow the docs. A `README.md` page
   made any other way still passes lint and fails in Obsidian and the MCP,
   which is how NW6 went unnoticed for about seven weeks.
4. **Option 3 plus deleting the rule** from `slug()` and `backlinks.py`. Lint
   then names pages the way every other reader does, so a page saved as
   `README.md` shows up as broken links at the next session start. No new lint
   rule is needed.

| | 1 Roll back | 2 Wiki rename | 3 + fork docs | 4 + drop rule |
|---|---|---|---|---|
| Fork changes | 2 docs restored | none | 9 docs (19 lines) | + 2 scripts, 4 test files |
| Wiki changes | none | 4 renames, 8 lines, log | same as 2 | same as 2 |
| Today's 57 links in Obsidian, MCP and file lookup | broken | fixed (after reindex) | fixed | fixed |
| New folder pages | broken | broken | fixed if agents follow the docs | fixed |
| Lint notices a new `README.md` folder page | no | no | no | yes |
| Upstream | none | none | docs differ | docs differ; code matches upstream |

**Decision: option 4.** The rule is the only reason lint disagreed with the
other readers, and the reason it reported 0 broken links while they resolved
none of these. Deleting it makes "0 broken links" true for every reader and
guards new folder pages without new machinery. Its one cost, broken links on
any fork wiki not yet renamed, doesn't arise with one wiki renamed in the same
step. It also brings the fork's code back in line with upstream. No upstream
issue is filed.

**Left out, optional separate follow-ups:** M1, the archived copy that takes a
live page's MCP backlinks (the only one doing damage today); dated archive
names or an archive command; `backlinks.py` reading the root files (M4, NW6
step 4); lint checking the links in `index.md` and `overview.md` (M2); the
wrapped links (M6); the unused `post-write.sh`; and the MCP not seeing new
pages until a reindex (NW5). NW6 step 5, Obsidian's attachment folder, stays
open too.

## 10. Implementation

Status: done 2026-10-01. Results are at the end of this section.

**Order.** The fork's hooks, skills and workers run straight from its working
tree, so a code change takes effect when the file is saved. The wiki is renamed
first, while the old `slug()` accepts both names, and the rule is deleted
after. Lint never sees broken links in between.

1. **Baseline.** Run the fork's test suite. Save lint's `--json` output for the
   live wiki, and a full lint report from a scratch copy of it.
2. **Commit A (fork):** revert `c06c6a9` and `beaf265`, which only expanded the
   dropped proposals, and replace sections 9–11 with these two.
3. **Wiki commit:**
   - Read the Orient files, as AGENTS.md requires before any write.
   - `git mv` each `queries/<slug>/README.md` to `queries/<slug>/<slug>.md`.
     No link, `sources:` entry or citation changes.
   - Change 8 lines with the Edit tool, so the pre-write hook snapshots each
     page first:

     | File | Line now | Becomes |
     |---|---|---|
     | 3 research sprint pages | "(this README was over the 200-line threshold)" | "(this page was over …)" |
     | the same 3 pages | "This synthesis page: `queries/<slug>/README.md`" | the new path |
     | `meta/contract.md`:23 | "… (the folder name for a `README.md` page)" | the parenthetical removed |
     | `meta/contract.md`:47 | example `queries/research-<topic>-<date>/README.md` | `…/research-<topic>-<date>.md` |

   - Add a `log.md` entry.
   - **Check:** lint's output matches the baseline, apart from the four pages'
     paths.
   - Commit, leaving out `_status.md`.
4. **Reindex** the session's wiki-search server. **Check:** the four pages'
   backlinks are no longer 0 (the audit measured 31, 13, 9 and 10).
5. **Commit B (fork), the fix:**
   - **Code:** delete the rule from `wikifm.slug()` and update its docstring;
     `backlinks.py`:25 goes back to upstream's `p.stem`.
   - **Docs:** the 19 lines in 9 files that name `README.md`:
     - core `SKILL.md`:255;
     - `output-formats.md`:17, 27, 31, 185, 264, 268. Line 185, "Keep a
       `README.md` next to the CSV", becomes "explain the CSV's columns and
       sources on the folder's main page";
     - `citation-spec.md`:49, 58, 70;
     - `templates/vault-contract.md`:23, 47;
     - research `SKILL.md`:83, 255;
     - PRD `SKILL.md`:64, 108;
     - `prd-templates.md`:13;
     - `.claude/roles/researcher.md`:27;
     - `hooks/README.md`:28.
   - **Tests:** the `README.md` fixtures in `test_wikifm.py`, `test_lint.py`,
     `test_write_hooks.py` and `test_capture.py` become `<slug>/<slug>.md`.
     A new test checks that links to a page saved as `README.md` are reported
     as broken. `test_migrate_sources.py`'s two uses, about old archive
     snapshots, stay.
   - **Checks:** the full suite passes, and lint on the live wiki with the new
     code matches step 3's output.
6. **Commit C (fork), the record:** the design doc (section 5.2 becomes "slug =
   file stem", the matching Bottom line text, PATCH-2 and PATCH-3b's
   dispositions, NW6 steps 1–3 done, a revision note), the fork changelog
   (PATCH-2 and PATCH-3b retired), and this section's results.

**Decided along with the plan:**

- Historical text stays as it is: the wiki's `log.md`, old lint reports,
  `_archive/`, the design doc's findings tables, and `migrate_sources.py`'s
  handling of old `_archive/README-*.md` snapshots.
- No version bump and no `CHANGELOG.md` entry. No fork step has bumped the
  version since 2.21.0, and fork changes are recorded in `fork-chgs/`.

**Needs the user:**

- Restart any other Claude session open on the wiki after step 4. A running
  wiki-search server only sees the renamed files after a reindex or restart.
- Optionally, in Obsidian after step 3, hover a link to the Kiro sprint and
  check its backlinks pane. Until the rename, clicking one of these links
  creates an empty note at the wiki root.
- Push both repos, or ask for them to be pushed. Nothing is pushed by this
  plan.
- Making the fork private is separate and not needed for this.

**Results, 2026-10-01:**

- **Commits.** Fork: `275dfd8` (step 2), `84aeeac` (step 5) and the commit
  that adds these results (step 6). Wiki: `fbfb8d7` (the four renames alone,
  so `git log --follow` traces each page back through its `README.md`
  history) and `82c63d8` (the 8 lines, the log entry and the hook's three
  snapshots).
- **Tests.** 446 passed and 2 skipped before; 447 passed and 2 skipped after,
  the extra one being the new `README.md` test. Removing the rule failed 11
  tests, all of them `README.md` fixtures.
- **Lint.** After the rename, `--json` was byte-identical to the baseline
  (0 errors, 33 warnings, 20 info on 247 pages), and the full report differed
  only in the four pages' paths. With the rule deleted, both were identical
  to the post-rename output.
- **Wiki-search MCP.** After the reindex, backlinks on the new paths returned
  31, 13, 9 and 10, the counts the trial predicted. The first reindex hadn't
  taken effect after about five minutes; a second one did. Restarting a
  session is the surer way to refresh a running server.
- **Departures from the plan.** None in substance. The wiki change went in as
  two commits instead of one, because git paired each `README.md` with its
  identical snapshot rather than with the renamed page. `updated:` was left
  alone on the edited pages, as only file names and self-references changed.
  `output-formats.md` gained one sentence saying not to name a folder page
  `README.md`, and why.

## Provenance

- **Checked:** every reader in section 3.
  - The MCP was checked live (read-only) and on both copies, using version
    2.3.0's own code and a running server.
  - Obsidian was checked through its metadata cache and the user's checklist.
- **Not checked:**
  - Obsidian's mobile app;
  - the Folder notes plugin, which isn't installed;
  - a GitHub web view;
  - how often agents actually pass the bare slug to the MCP's backlinks.
- **The live wiki wasn't changed.** Its commit and `git status` were the same
  before and after. The only live files written during the audit were the
  wiki-search index files in `.markdown_vault_mcp/` (gitignored). The
  session's own server saves those every minute.

## Appendix A. Obsidian console snippet

Run in the vault's developer console (Cmd+Opt+I). It writes
`nw6-obsidian-links.json` at the vault root, with Obsidian's resolved and
unresolved links and, for every link, embed and frontmatter link, the file
Obsidian resolves it to.

```js
(async () => {
  const mc = app.metadataCache;
  const files = app.vault.getMarkdownFiles();
  const out = { resolved: mc.resolvedLinks, unresolved: mc.unresolvedLinks, files: {} };
  for (const f of files) {
    const c = mc.getFileCache(f) || {};
    const dest = (l) => { const t = l.link.split("#")[0]; const d = t ? mc.getFirstLinkpathDest(t, f.path) : f; return d ? d.path : null; };
    const pick = (arr) => (arr || []).map((l) => ({ line: l.position ? l.position.start.line + 1 : null, link: l.link, original: l.original, dest: dest(l) }));
    out.files[f.path] = { links: pick(c.links), embeds: pick(c.embeds),
      frontmatterLinks: (c.frontmatterLinks || []).map((l) => ({ key: l.key, link: l.link, original: l.original, dest: dest(l) })) };
  }
  await app.vault.adapter.write("nw6-obsidian-links.json", JSON.stringify(out));
  return `${files.length} markdown files, ${Object.keys(mc.resolvedLinks).length} in resolvedLinks: written to nw6-obsidian-links.json`;
})()
```
