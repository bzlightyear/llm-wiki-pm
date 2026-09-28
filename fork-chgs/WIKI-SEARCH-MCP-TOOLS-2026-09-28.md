# wiki-search MCP: tools, usage and risk

Date: 2026-09-28 · Companion to
[SOURCES-AND-REFERENCES-DESIGN-REVIEW-2026-09-28.md](SOURCES-AND-REFERENCES-DESIGN-REVIEW-2026-09-28.md)
(finding F4) and
[SOURCES-AND-REFERENCES-DESIGN-2026-09-25.md](SOURCES-AND-REFERENCES-DESIGN-2026-09-25.md).

The wiki-search MCP is `@wirux/mcp-markdown-vault` **2.3.0**, launched by
`hooks/wiki-search.sh` from the npx cache. That version was installed on
2026-08-03 and hasn't changed, so every session discussed here ran the code
described below (`dist/presentation/mcp-tools.js` unless noted).

The private wiki is described only in counts. No page names, people or source
slugs appear here.

---

## 1. Summary

- **What the MCP is for.** llm-wiki-pm uses it as a search tool. The core skill
  prescribes only `view` actions (`semantic_search`, `read`, `backlinks`,
  `outline`, `global_search`).
- **Edits were used in early August, damaged pages, and were then avoided.** The
  wiki's own log records MCP `edit` use on 2026-08-05 and 2026-08-11. On 2026-08-11
  it re-escaped wikilinks across whole files, which led to upstream issue #47. From
  then on, the log records agents choosing the Write tool or `sed` instead.
- **Search works but is noisy.** About a third of semantic-search results are
  `_archive/` snapshots. Agents mostly search with grep, and a small measurement
  (section 5) found no duplicates or stale claims that grep missed.
- **Usage evidence is incomplete.** Saved transcripts miss about a third of the
  wiki-editing days (section 3), so every count here is a lower bound.
- **Recommendation.** Keep `view`. Block `mcp__wiki-search__edit` with a
  permission rule under both tool-name forms (section 6). The only operations that
  damage pages are `frontmatter_set` and the heading-based edits, and nothing in
  llm-wiki-pm needs them.

---

## 2. Tools and operations

The server exposes **5 tools** (`vault`, `edit`, `view`, `workflow`, `system`).
Each takes an `action` (or, for `edit`, an `operation`) parameter, for **27
operations** in total.

**How to read the Usage column.** "Used" means observed in the saved transcripts
(section 3) or recorded in the wiki's `log.md`. "Likely" means a skill prescribes
it. "Unlikely" means no skill mentions it and no use was observed.

### `view` (read-only)

| Operation | What it does | Usage | Risk |
|---|---|---|---|
| `semantic_search` | Ranks notes by meaning, combining vector and keyword matching, so it finds paraphrases. The skill's preferred search. | Used: 12 calls, 2026-08-06 to 09-02 | **Low.** About a third of its results are `_archive/` snapshots (section 5). |
| `global_search` | Exact-phrase search across the whole vault. Returns matching sections with scores. | Used: 3 calls | **Low** |
| `search` | Finds the most relevant sections within one note, by keyword and proximity. | Used: 1 call | **Low** |
| `read` | Returns a whole note or one section by heading. | Used: 11 calls | **Low** |
| `bulk_read` | Reads several notes or sections in one call. | Used: 1 call | **Low** |
| `outline` | Shows a note's heading structure, or a folder tree. | Likely (prescribed; 0 observed) | **Low** |
| `frontmatter_get` | Returns a note's header fields, parsed with js-yaml. | Unlikely (0 observed) | **Low–medium.** It probably returns plain dates as timestamps (not tested). An agent that copies such a value into an Edit would write the timestamp form itself. |
| `backlinks` | Lists notes that link to a given note. | Likely (prescribed; 0 observed) | **Low** |

### `vault` (whole-file operations)

| Operation | What it does | Usage | Risk |
|---|---|---|---|
| `list` | Lists notes, optionally within one folder. | Unlikely | **Low** |
| `read` | Returns a note's full text. It duplicates `view.read`. | Used: 1 call | **Low** |
| `stat` | Returns file details such as size and dates. | Unlikely | **Low** |
| `create` | Creates a note from the content given. Content is required (`mcp-tools.js:88-92`), and it refuses to overwrite an existing note. | Unlikely | **Medium.** No write-time hook sees it today. |
| `create_from_template` | Creates a note by filling placeholders in a template file. | Unlikely | **Low–medium.** Same unhooked path; `meta/contract.md` suggests an off-schema template. |
| `update` | Replaces a note's whole content with exactly the text given, with no reformatting (`update-file.js:13`). | Unlikely | **Medium–high.** It overwrites a whole page with no snapshot today, and git is the only undo. |
| `delete` | Deletes a note. | Unlikely | **High if used.** No snapshot, no dangling-link check, and git is the only undo. |

### `edit` (changes inside a note; single or batch)

| Operation | What it does | Usage | Risk |
|---|---|---|---|
| `append` / `prepend` | Adds content at the end or start of a note or heading section. It parses the page and re-serializes the **whole page** to do so. | Unknown | **High.** The re-serialization escapes `[`, which breaks wikilinks and `## [date]` headers (#47). |
| `replace` | Replaces a section's body, or the whole section, found by heading. Heading names are fuzzy-matched (threshold 0.6), so a close name can hit a different section. | Unknown | **High.** Whole-page re-serialization (#47), plus the risk of matching the wrong section. |
| `delete` | Removes a heading section, including its subsections. | Unknown | **High.** Re-serialization, and it can remove large amounts of content by accident. |
| `line_replace` | Replaces a line range with new text, as plain text (`freeform-editor.js`). | Unknown | **Medium.** Text-preserving, but unhooked, and line numbers go stale if the page changed after it was read. |
| `string_replace` | Replaces exact text (first match or all), as plain text (`freeform-editor.js`). | Used per `log.md` (2026-08-11) | **Low–medium.** Text-preserving, but unhooked. The 2026-08-11 log blamed it for the escaping; per the code, `frontmatter_set` in the same session is the likely cause. |
| `frontmatter_set` | Merges fields into a note's header (`mcp-tools.js:287-305`). It re-dumps the whole header with js-yaml and re-serializes the body. | Used per `log.md` (2026-08-05, 08-11) | **High.** Unquoted dates become `…T00:00:00.000Z` timestamps (#49), quoted dates become single-quoted, flow lists become block lists, and the body rewrite escapes brackets (#47). |
| batch `operations[]` | Runs up to 50 of the operations above in order, and stops at the first error. | Unknown | **High.** Every risk above, across up to 50 edits in one call, and an early stop can leave a batch half-applied. |
| `dryRun` flag | Returns a diff without saving. | Unknown | **None** |

### `workflow` (agent session state)

| Operation | What it does | Usage | Risk |
|---|---|---|---|
| `status` / `transition` / `history` / `reset` | An optional in-memory state machine for agent steps (search → open note → save → done). It doesn't touch files. | Unlikely | **Low.** Irrelevant to the wiki. |

### `system` (server administration)

| Operation | What it does | Usage | Risk |
|---|---|---|---|
| `status` | Reports index, backlink and workflow health. | Unlikely | **Low** |
| `reindex` | Rebuilds the search index in the background. | Unlikely | **Low** (CPU only) |
| `overview` | Returns a folder tree. | Unlikely | **Low** |
| `overview_status` / `prepare_overview` | Report on, and gather material for, the MCP's own `meta/overview.md`. | `prepare_overview`: 1 call (2026-08-29) | **Low** |
| `save_overview` | Writes `meta/overview.md` and a one-line vault description. | 1 call (2026-08-29) | **Low–medium.** It creates a second "overview" that the MCP tells agents to read, which competes with the wiki's own. On disk the file still carries its 2026-08-03 date, so the write may not have landed (not checked). |

### Behavior outside the tools

- **Startup writes.** At server start (`index.js:123` → `vault-auto-init.js`) the
  MCP creates `meta/contract.md` and `meta/overview.md` if they're missing. On a
  brand-new, empty wiki folder that makes the folder non-empty, and then
  `session-start.sh` skips its scaffold. Whether the MCP or the SessionStart hook
  runs first is unverified.
- **Resources.** It exposes read-only `vault://overview` and `vault://stats`.
- **No folder exclusion.** The only configurable settings are the environment
  variables `VECTOR_STORE_URL` and `VECTOR_STORE_COLLECTION`. Nothing excludes
  `_archive/`, lint reports or `log.md` from the index.

---

## 3. Usage evidence

### Tool names

Claude Code names MCP tools by how the server is registered:

- **Plugin install:** `mcp__plugin_llm-wiki-pm_wiki-search__<tool>`. This is what
  was used until the wiki moved to the fork on 2026-09-25.
- **Direct configuration:** `mcp__wiki-search__<tool>`. This is what is used now.

Every count below covers both forms. No wiki pages have been updated through
llm-wiki-pm since 2026-09-25, so the effective window is 2026-08-06 to 2026-09-25.

### Calls in saved transcripts (`~/.claude/projects`, all projects, subagents included)

| Operation | Calls | Dates |
|---|---|---|
| `view.semantic_search` | 12 | 2026-08-06 – 09-02 |
| `view.read` | 11 | 2026-09-01 – 09-02 |
| `view.global_search` | 3 | 2026-09-01 – 09-02 |
| `view.bulk_read` | 1 | 2026-09-01 |
| `view.search` | 1 | 2026-09-01 |
| `vault.read` | 1 | 2026-09-01 |
| `system.prepare_overview` | 1 | 2026-08-29 |
| `system.save_overview` | 1 | 2026-08-29 |
| Any `edit` operation, or `vault` create/update/delete | **0** | — |
| **Total** | **31** | none after 2026-09-02 |

For comparison, the same transcripts contain:

- 1,138 Write/Edit calls on wiki files;
- 374 Bash `grep` calls against the wiki;
- 23 Bash calls running ad-hoc Python frontmatter scripts over the wiki (1 using
  `yaml.dump`, 1 Node script).

### Search behavior per session

| Measure | Count |
|---|---|
| Sessions that loaded an llm-wiki skill | 54 |
| … with at least one `semantic_search` | 6 |
| … that searched the wiki only with grep | 30 |
| ToolSearch lookups for the wiki-search tools | 4 |

### Transcripts are incomplete

- **Missing days.** Of 30 days since 2026-08-07 with non-lint `log.md` entries, 11
  have no transcript that touches the wiki. One of those days has 15 log entries.
- **Missing sessions on covered days.** The 2026-08-11 daily-maintenance session
  that logged MCP `string_replace` and `frontmatter_set` use is absent, although
  that day has 3 other transcripts.
- **Unknown location.** Where the missing sessions ran is unverified. They aren't
  under `~/.claude/projects`, and no other session store was found.

The zero-edit row above therefore does **not** show that MCP edits never
happened. `log.md` shows they did, in early August.

### Evidence from the wiki's `log.md`

- **2026-08-05:** a fix for escaped wikilinks caused by an MCP edit.
- **2026-08-11:** a daily-maintenance sweep's `string_replace` and `frontmatter_set`
  calls re-escaped wikilinks across whole files. The fix used `sed`, "not the MCP
  edit tool, to avoid re-triggering the same bug". Upstream issue #47 was filed the
  same day.
- **From 2026-08-11 on:** entries note writing with the Write tool "not the
  wiki-search MCP edit tool".

### Timestamp dates

New `…T00:00:00.000Z` values entered wiki commits dated 08-05, 08-11, 08-28, 08-30
and 09-04. The format is js-yaml's, which the MCP uses, and early-August
`frontmatter_set` use is logged, so the MCP is the likely writer. It isn't
confirmed for the later commits: commits batch several days, and those sessions'
transcripts are missing.

---

## 4. Why agents use grep

Observed: 12 semantic searches against 374 grep calls, and no MCP calls at all
after 2026-09-02. The cause is **unverified**. Plausible contributors:

- **Deferred tools.** MCP tools must be loaded through ToolSearch before their
  first use in a session. Grep needs no setup.
- **Slow connection.** The server can still be connecting when a session starts.
- **Skill wording.** "`semantic_search` preferred, grep fallback" lets grep satisfy
  the step.
- **Noisy results.** About a third of results are archive snapshots (section 5).

---

## 5. Measurement: has grep-only search cost anything?

Run 2026-09-28 against the live wiki (read-only `view.semantic_search`).

**Duplicate pages.** For each of the 16 concept pages created since 2026-08-25, a
topic query of the kind an agent would run before creating the page:

- **0 accidental duplicates.**
- Every overlapping page the search found was already linked from the new page,
  usually with a note on how the two differ.
- The one near-miss checked was a deliberate umbrella page, recorded as such in
  `log.md`.
- Likely reason: Orient reads `index.md`, which lists all pages every session.

**Stale claims after corrections.** Three logged corrections, searched for the
old claim:

| Correction type | Old claim left on live pages? | Found by grep? |
|---|---|---|
| Wording (two systems are distinct) | No | n/a |
| Wording (two efforts are one) | No | n/a |
| Date (GA date corrected by one day) | Yes, once, in `overview.md`'s Active Bets, stated as current. About 20 other mentions are legitimately historical (dated digests, history pages). | Yes, instantly |

The one leftover came from the update not sweeping `overview.md` (design
follow-on NW1), not from search.

**Archive clutter.** Across 11 unfiltered semantic searches, **30 of 85 results
(35%)** were `_archive/` snapshots. One search returned 8 of 8 snapshots of a single
page, pushing all live pages out. The `directory` filter takes a single prefix, so a
clean search of live pages needs one call per folder.

**Limits.** This is a small sample, git history commits in multi-day batches, and
entity pages and unlogged corrections weren't tested.

---

## 6. Recommendations

1. **Block the damaging operations.** Add `permissions.deny` (or explicit
   `permissions.ask`) entries for `mcp__wiki-search__edit` **and**
   `mcp__plugin_llm-wiki-pm_wiki-search__edit`. The Edit tool covers every operation
   it offers, and agents have avoided it since 2026-08-11. Permission rules aren't
   hooks, so this doesn't conflict with "hooks never deny". Optionally block
   `vault` writes as well. Permissions match on tool name, not action, so blocking
   `vault` would also block `vault.read`, which duplicates `view.read` anyway.
2. **Match both tool-name forms in any MCP hook matcher**, for example
   `mcp__.*wiki-search__(vault|edit)`, because upstream users install the plugin and
   get the prefixed names.
3. **Drop the design's step 12 (patched MCP) and defer NW2 (fork)** unless MCP edits
   are wanted back.
4. **Align the skill with practice.** Grep plus `index.md` first. `semantic_search`
   only for wording-dependent checks (before creating a concept page, and in
   stale-claim sweeps), run once per live folder to avoid archive noise. Add
   `overview.md` to the stale-claim sweep.
5. **Expect more search noise from new snapshots.** The snapshots the design adds (MCP writes, lint
   auto-fix, briefings, `overview.md`) will all be indexed and add to the archive
   noise.
