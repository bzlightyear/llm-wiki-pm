# llm-wiki-pm Fork Backlog

created: 2026-10-01

Candidate work for the llm-wiki-pm fork: issues to fix, capabilities to add or
improve, and performance to tune. Each item records what is known when it's
captured. An item big enough to need one gets its own design, analysis or
proposal doc when the work starts.

revised on: 2026-10-02
Closed NW5: one shared wiki-search server per wiki, under launchd, with
`$WIKI_PATH` as the default wiki. Corrected its title, and added a line on NW5's
effect to NW2 and NW7.

The first seven items, NW1–NW7, were recorded during the sources and references
work and moved here word for word from section 10 of the
[Sources and References Design](sources-and-references-design.md) on
2026-10-01. IDs inside them, such as D9, I6, R12, N15, B3, a "section" number
or a "step" number, refer to that design unless an item says otherwise.
"Review F4" and the like refer to the
[Sources and References Review](sources-and-references-review.md).

**Adding an item:** give it the next ID (NW8 next), a bold one-line title, and
as much of this as is known: what happens, why it matters (with measurements and
dates), the proposal or scope of a fix, related items, and where it was found.
When an item is done or dropped, add a status line at its top and move it to
Closed.

---

## Open

**NW1. Orient content and `overview.md` freshness (separate design).**
`overview.md` only ever grows (70 KB), its action items and decisions are frozen
copies from meeting digests, and later updates never flow back into it, so Orient
loads stale and sometimes wrong information every session. The same design
covers what else Orient should load. The org chart kept in SCHEMA's Domain
section is weeks older than `concepts/relationship-map.md`, which Orient never
reads. The proposal is a pointer from SCHEMA to the map, plus Orient reading only
a compact org-chart section of it. Starting points: ISSUE-1, ISSUE-2, and I8's
revisit mechanism.

**NW2. Fork `wirux/mcp-markdown-vault`. Deferred (review F4).** The permission
rule in D9 removes the damaging operations on this install at no cost, so the
fork is only worth doing if MCP edits are wanted back. The original plan
follows. The MCP's full-file round-trip causes
the bracket escaping (#47) and the timestamp dates (#49, N15), and its
maintainer has not responded since June 2026. The fork would be thin, on top of
upstream, with one fix per branch and a regression test in the project's vitest
suite: `CORE_SCHEMA` for #49 first, then text-preserving `frontmatter_set` and
`string_replace` for #47, and possibly #45 (orphaned server processes). Each fix
also goes back upstream as a pull request. `wiki-search.sh` then runs a pinned
build of the fork (a fork-only launcher difference). Costs: owning a
Node/TypeScript build and its dependency updates, and a small recurring merge fix
when upstream changes `wiki-search.sh`. If it lands, D9's deny rule can be
lifted. R12's auto-fix, the escaped-bracket check and the MCP hook matchers stay
as safety nets. `CORE_SCHEMA` alone isn't enough: it writes dates unquoted, so
the fork's #49 fix must keep string dates quoted (review F2).
Since NW5, the MCP runs as one shared server under launchd: a fork build means
repointing that LaunchAgent and restarting it, and streamable HTTP would go in
the fork if Claude Code drops SSE.

**NW3. Lint log entries crowd out `log.md`.** Every lint run outside `--json`
mode appends an entry to `log.md` (`lint.py:772-780`). As of 2026-09-28 those
are 257 of the log's 480 entries, with up to 37 on a single day. That buries the
entries recording actual wiki work, and pushes the log toward `session-stop.sh`'s
500-entry rotation roughly twice as fast. The rotation is what forces migration
step M2 to read rotated `log-*.md` files (review finding F14). Options: append
at most one lint entry per day, updating it in place, or stop appending and rely
on the per-day report in `queries/`. Found in the design review
([Sources and References Review](sources-and-references-review.md), F14).

**NW4. The action-items file is outside the plugin's rules.**
- **What it is:** a root-level markdown file of open action items, ranked by
  urgency (about 400 lines, about 90 items). An agent created it at the user's
  request in a chat session, and it is regenerated or partly updated only when the
  user asks (39 `log.md` entries).
- **Why it drifts:**
  - It sits outside every page folder, so lint, the hooks and `index.md` skip it.
  - It has no frontmatter, sources or links, and no skill defines when or how it
    is updated.
  - Wiki pages mention it in prose, but none link to it.
- **Related work:** it has the same staleness problem as ISSUE-1 (action-item
  status never updated after capture; [llm-wiki-pm Fork Changelog](llm-wiki-pm-fork-changelog.md) notes action
  items have no real page type) and as NW1 (frozen action items in `overview.md`).
- **Options:**
  1. **Make it a first-class page,** for example `queries/open-action-items.md`,
     with standard frontmatter, sources and links. Define in the maintain skill
     when it is updated (for example on every run that ingests meetings), and let
     lint check it.
  2. **Remove it and generate the list on demand** from the action items in
     meeting digests, through a brief-skill command. There is no separate file to
     go stale, but it only works once digests' action items are marked done when
     resolved, which is ISSUE-1's open problem.

  They aren't exclusive: option 1 now, and option 2 once ISSUE-1 is solved.
- **Found in:** the design review (F15).

**NW7. No link search finds every incoming link.**
- **What happens:** archiving, superseding or renaming a page means updating
  every link to it, but none of the ways to find those links is complete:
  - `backlinks.py` reads `entities/`, `concepts/`, `comparisons/`, `queries/`
    and `_archive/`. It skips `briefings/`, `index.md`, `overview.md`, the
    action-items file and the other root files, which held 747 links to live
    pages on 2026-09-30 (analysis M4).
  - The wiki-search MCP's `view(action=backlinks)` reads every file, but a
    running server misses renamed and new pages until it's reindexed or its
    session restarts. On 2026-10-01 the first reindex after a rename didn't
    take, and a second one did.
  - When two files share a page's file name, the MCP can credit the page's
    links to the wrong one (M1, below).
  - The docs don't say which to use. Update ① names `backlinks.py`. The core
    skill's §6 Archive, `update-guide.md`'s Supersede steps and the SCHEMA
    template's Archive line name none, and the vault contract says "Incoming
    links to a note → `view.backlinks`".
- **M1, the one doing harm today:** one `_archive/` file has the exact file
  name of a live concept page. The page's slug ends in a date, so the name
  looks like a snapshot's. It came from a move into `_archive/` by hand on
  2026-08-11, not from `snapshot()`.
  - The MCP resolves the page's links to the archive copy (shortest path wins,
    and `_archive` sorts first), so it reports 0 backlinks for the live page.
    Rechecked 2026-10-01.
  - `backlinks.py` finds 8 links on 6 pages, but not the one in `index.md`.
  - A lookup by file name finds two files, and Obsidian sends the links from
    snapshots to the archive copy.
  - Lint doesn't read `_archive/`, so nothing reports it.
  - **Why it happened:** the core skill's §6 Archive says to move a page to
    `_archive/` "preserving path", so a move by hand keeps the bare name.
    `snapshot()` names its copies `<slug>-<date>`, but archiving doesn't use
    it.
- **Scope of the fix,** to be written up as a complete proposal before any
  change:
  1. `backlinks.py` also reads `briefings/` and the root files except
     `log.md`, which is history. `raw/` stays out, since records are
     immutable.
  2. The archive, supersede and rename docs name `backlinks.py` as the link
     search. The vault contract's "Incoming links" line points at it, or says
     that the MCP lags.
  3. Rename M1's archive copy to a dated name. `citation-spec.md` says
     `_archive/` is immutable, so the proposal has to say whether a rename
     counts as a change.
  4. Decide how archived pages are named from now on, so a bare-name copy
     can't come back: a doc rule (`_archive/<slug>-<date>.md`, as `snapshot()`
     names them) or a script.
- **Not included:** lint checking the links in `index.md` and `overview.md`
  (analysis M2), and the analysis's other optional follow-ups (its section 9).
- **Since NW5:** the one shared server can run for weeks, and its backlinks
  stay stale until a reindex, which adds to the case for `backlinks.py`.
- **Found in:** the NW6 analysis (M1, M4). Split out of NW6's next step 4 on
  2026-10-01.

## Closed

**NW5. One wiki-search server per wiki.**
- **Status: done 2026-10-02.** pm-wiki is served by one shared server under
  launchd (`local.wiki-search`, SSE on port 3100 with a bearer token), and every
  project's sessions connect to it. `$WIKI_PATH` is the default wiki: the
  projects' `.wiki-path` files were removed, and a `.wiki-path` now only marks a
  project that uses another wiki. See the
  [NW5 Shared Wiki-Search Analysis](nw5-shared-wiki-search-analysis.md) and the
  [Wiki-Search Launchd Guide](wiki-search-launchd-guide.md), which also covers
  adding a second wiki. The text below describes the problem as found.
- **What happens:** `wiki-search` is registered at user scope in
  `~/.claude.json` as a stdio server (`sh …/hooks/wiki-search.sh`), so every
  Claude Code session in any project starts its own copy at session start,
  whether or not it uses the wiki. The SessionStart hook doesn't start it; its
  npx step only warms the package cache when it's missing. Measured 2026-09-30:
  one copy uses about 580 MB. Every open session adds another, and each one
  writes the same `.markdown_vault_mcp/` vector index.
- **Wanted:** wiki access from every project (all 13 `.wiki-path` files point at
  pm-wiki), served by a single process.
- **Proposal:** the MCP already has a multi-client mode (`MCP_TRANSPORT_TYPE=sse`:
  `GET /sse` per client, shared vault, index and embedder, separate workflow
  state per client). This is a local install change, with no plugin change.
  1. A LaunchAgent, `~/Library/LaunchAgents/local.wiki-search.plist`, like the
     existing `local.wiki-path-env.plist`. It runs `sh hooks/wiki-search.sh` at
     login with `KeepAlive`, `MCP_TRANSPORT_TYPE=sse`, `PORT=3100` (3000 is a
     common dev-server port), `HOST_BIND_ADDRESS=127.0.0.1`, the vault fixed to
     pm-wiki through `WIKI_PATH` and a pm-wiki working directory, and a log in
     `~/Library/Logs/wiki-search.log`.
  2. Replace the user-scope entry with
     `claude mcp add --transport sse -s user wiki-search http://127.0.0.1:3100/sse`.
     The server name stays `wiki-search`, so tool names, D9's deny and `ask`
     rules, and the pre-write and post-validate matchers are unchanged.
  3. Verify from a new session that the tools work and exactly one server
     process runs.
- **Costs and open points:**
  - A port on 127.0.0.1 can be reached by any local process, and in principle by
    a web page through DNS rebinding, while a stdio copy talks only to its own
    session. pm-wiki holds customer and 1:1 content, so set `MCP_AUTH_TOKEN` in
    the plist and a matching `Authorization: Bearer` header in the Claude Code
    entry.
  - A package upgrade, or switching to NW2's fork build, needs
    `launchctl kickstart -k`. Sessions open at the time may have to reconnect.
  - The vault is fixed to pm-wiki for every project. A project whose
    `.wiki-path` pointed at another wiki would still get pm-wiki.
  - The plugin manifest keeps its per-session stdio server for plugin installs.
    Whether the plugin should document the shared setup is left open.
- **Related:** NW2's possible #45 fix (orphaned server processes).
- **Found in:** a check of running servers after step 8, 2026-09-30.

**NW6. Folder pages don't resolve outside the fork's own tools.**
- **Status: fixed 2026-10-01** (next steps 1-3 below), with option 4 of the
  [analysis](nw6-page-name-resolution-analysis.md) (its section 9): the wiki's four
  folder pages were renamed `queries/<slug>/<slug>.md` (pm-wiki `fbfb8d7`,
  `82c63d8`), and the fork's docs and `slug()` changed with them (`84aeeac`).
  The text below describes the gap as found. Next step 4 moved to NW7, and
  next step 5 is done, so NW6 is closed.
- **What happens:** a multi-file page is a folder whose main page is
  `README.md` (`queries/<slug>/README.md`, section 5.2). `slug()` names that file
  after its folder, so lint, `backlinks.py`, the post-write check, `sources:`
  entries and citations all resolve `[[<slug>]]` to it. Obsidian and the
  wiki-search MCP resolve a link by file name instead. No file is named
  `<slug>.md`, so for them the link points at nothing.
- **Measured 2026-09-30:** 32 links point at the wiki's 4 folder pages (3
  research sprints and a PRD): 23 on 15 pages, 4 in `index.md`, 3 in `log.md`
  and 2 in a reconstructed record that quotes the log. Lint reports no broken
  links. For the Kiro sprint's `README.md`, the MCP's `view(action=backlinks)`
  returns 0 links, while `backlinks.py` finds 21 on 15 pages, archives included.
  No agent has used the MCP's lookup: across the 128 Claude Code sessions saved
  since 2026-08-07, agents made 47 MCP read calls (31 of them semantic searches)
  and no backlinks call, while `backlinks.py` ran in 64 sessions. The only two
  backlinks calls were the tests that found this gap.
- **Impact until fixed.** No page's content or frontmatter is changed by the
  mismatch itself. Two things can still go wrong:
  - **Obsidian:** the links show as unresolved (dimmed, no hover preview), and
    the `README.md`'s backlinks pane misses them. The graph draws none of them,
    because this vault hides unresolved links. Clicking one creates an
    empty note named after the folder at the wiki root, Obsidian's default
    location for new notes. That happened once on 2026-09-30, and the note was
    deleted. While such a note exists, Obsidian resolves the link to it, so the
    link opens a blank page instead of looking broken. Lint and session start
    don't scan root files, so nothing reports it, and a `git add -A` in the
    wiki would commit it. If Obsidian's new-note location were set to the
    current file's folder, the note would instead share the folder page's
    slug, and lint would report both (R9, R12).
  - **Agents:** possible but not seen. The core skill lists the MCP's
    backlinks action among its tools, and the vault contract (`meta/contract.md`)
    says "Incoming links to a note → `view.backlinks`". An agent that used it
    on a folder page would conclude nothing links there. Update ① uses
    `backlinks.py`, but nothing says which tool archive, supersede and rename
    use. One that archived, superseded or renamed a folder page that way would
    leave its inbound links broken. Lint reports those as 🔴 at its next run,
    and session start shows its counts, so the break would show within a
    session and could be undone from `_archive/` and git.
  - **Scope and growth:** only the 4 folder pages and their 32 links. Each new
    research sprint or PRD adds another folder page.
- **Until fixed:** don't click those links in Obsidian, and delete any empty
  note a click creates at the wiki root.
- **Why the design missed it:** section 5.2 makes `slug()` "the one ID function
  for every reference site", and I6 requires each link to resolve to a slug.
  The design and both reviews checked resolution only against the fork's own
  code. Obsidian appears only as a writer (B3), and the wiki-search MCP
  analysis covered its writes, not how it resolves links. No invariant says a
  page's name must resolve to the same file for every reader. `slug()` and the
  file name agree for every page except a folder's `README.md`.
- **Next steps:**
  1. **Audit every reader first, with a trial of the fix.** Done 2026-09-30, in
     [NW6 Page Name Resolution Analysis](nw6-page-name-resolution-analysis.md).
     The fix resolved every link for every reader tested, and the audit
     found five other mismatches. Its section 9 compares four fixes and records
     the one chosen, and leaves the other mismatches as optional follow-ups.
     List each component
     that turns a page name or path into a file:
     - the fork's scripts, hooks and docs, including anything that treats the
       name `README.md` specially;
     - each MCP action that takes a name or path (`backlinks`, `read`, `outline`,
       `frontmatter_get`, `bulk_read`);
     - Obsidian: links, embeds, `[[page#heading]]` and aliased links, the graph,
       the backlinks pane, the file explorer, search, and Dataview queries;
     - the Orient files (`index.md`, `overview.md`).

     Test each one on the live wiki, read-only, and on a scratch copy with the
     fix in step 3 applied. Point a separate wiki-search MCP at the copy, and
     have the user open the copy as an Obsidian vault and click a few folder
     links. The result is a table of reader and link form, today and with the
     fix. It decides whether the fix is enough, shows whether anything depends
     on the name `README.md`, and may find other mismatches to fix in the same
     change.
  2. **Extend I6** so a page's name resolves to the same file for every reader,
     not only to a slug, and add a lint check that keeps it true, such as a
     page's slug equalling its file stem. Otherwise each new folder page brings
     the gap back. Done without a new rule: `slug()` is now the file stem, so
     lint names a page the way every other reader does, and links to a page
     saved as `README.md` are reported as broken.
  3. **Fix, done 2026-10-01: name a folder's main page after the folder,**
     `queries/<slug>/<slug>.md`, instead of `README.md`.
     - The slug doesn't change, so no link changes, and the fork's tools keep
       working, while Obsidian and the MCP find the file by name. That removes
       both risks above, and every Obsidian link form resolves.
     - The wiki needs 4 renames, 6 prose lines on the 3 sprint pages that call
       themselves "this README" or give their own path, and 2 lines in its
       `meta/contract.md`, which mirror the template. No `sources:` entry names
       a folder page's path, and no link names `README`. Delete any stray root
       note first, or two files would share the name. After the rename,
       reindex every running wiki-search server or restart its session. A
       running server doesn't see renamed or new pages until it rebuilds.
     - The fork needs 19 doc lines changed in 9 files, among them the core
       SKILL's Query step, `output-formats.md`, `citation-spec.md`, and the
       research and PRD sub-skills (the analysis's section 10 lists them all).
     - Opening a page by clicking its folder in Obsidian's file explorer still
       needs the Folder notes plugin. Its default naming, `{{folder_name}}`,
       matches this one, so it would work without setup.
     - `slug()` dropped its `README.md` rule, and `backlinks.py` its copy.
       Without it, an un-renamed wiki loses 23 links, but the fork has one
       wiki, renamed in the same step.
     - `<folder>/<folder>.md` is also the default naming of the Obsidian Folder
       notes plugin.
     - Upstream's docs prescribe `README.md`, but its lint already names a
       page by its file stem, so the convention breaks upstream's own links.
       No upstream issue is filed for now.
  4. **Moved to NW7, 2026-10-01.** **Make archive, supersede and rename name
     their link search:**
     `backlinks.py`, not the MCP's lookup. Point the vault contract's
     "Incoming links" line at it too. First `backlinks.py` has to read
     `briefings/`, `index.md`, `overview.md` and the other root files. It skips
     them today, missing 747 links to live pages.
  5. **Done 2026-10-01: the user set it to `raw/assets` in Obsidian.**
     **Point Obsidian's attachments at a routed folder.** The wiki's
     `.obsidian/app.json` sets `attachmentFolderPath` to `raw/attachments`, so
     a file pasted or dropped into a note in Obsidian recreates the unrouted
     folder the migration emptied (review F15). Set it to `raw/assets` (Settings
     → Files and links). The file still needs a markdown record before a page
     can cite it.
- **Alternatives set aside:**
  - **Links with a path,** `[[<slug>/README|<slug>]]`: lint, `backlinks.py`
    and the post-write check would all need changing, and agents would have to
    remember the special form.
  - **An Obsidian folder-notes plugin:** it opens a folder's note when the
    folder is clicked, but doesn't change how links resolve, in Obsidian or
    the MCP.
  - **Frontmatter `aliases:`:** Obsidian doesn't use aliases to resolve a
    `[[name]]` link.
- **Found in:** the user, viewing a research sprint page in Obsidian after step
  10b, 2026-09-30.
