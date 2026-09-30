# Sources and References Design

created: 2026-09-25

Invariant-based redesign of how the wiki writes and checks `raw/` source records,
frontmatter `sources:`, inline `[source: …]` citations and wikilinks, with the
lint rules, hooks, migration and implementation plan that enforce it.

revised on: 2026-09-30
Completed step 5. The one-pager joins the Marp deck in a directory page's
`assets/` folder, and `--cited-sources` reads citations with lint's existing
marker parser until step 6 switches it to `citations()`. Section 8 records the
measured sizes: SKILL.md grew 423 bytes, the gap from the estimate being the
Scripts list, and `citation-spec.md` is 11.4 KB.
Completed step 6. `resolve()` takes one `sources:` entry, `slug()` moved into
`wikifm.py`, and R3 resolves what a malformed citation names, so a citation is
both R3 and R7 only when it resolves to nothing. Dated digests skip the
staleness warnings, session-start keeps the new counts out of its health total,
and section 8 records the lint counts before and after.
Completed step 7. Post-validate checks what lint checks, with lint's exact link
match. It runs the freshness gate for the two MCP writes pre-write can't judge,
and reminds about splitting whenever a rewrite leaves a page over 200 lines. It
measured about 0.09 s on a copy of the wiki.

revised on: 2026-09-29
Narrowed step 0's scrub to people and customer company names, after a scan of
the full git history. Product and page-topic names stay, so only the test file
and the lint-checks design are scrubbed, and N12 and D8 were updated to match.
Completed step 0, decided to implement in the fork before offering anything
upstream (D10), and set the status to in progress. Completed step 1 with the
other hooks' `.wiki-path` read in place of the `-f` test in section 5.13, which
would have stopped the launcher when the file exists but can't be read. Took in
the plan review's issues (P1–P29): each step now names the files, decisions and
dependencies it needs, step 10 is split into writing and running the migration,
and missing frontmatter and missing required keys stay 🔴. Completed step 2,
adding `GETTING_STARTED.md`, whose export audit still filtered on `private: true`.
Completed step 3 with the PostToolUse matcher moved to step 7 and dated digests
exempt from the freshness gate, and recorded the live check's result.
Completed step 4, which found that the 15 pages with wrapped `gaps:` items use
`>-` markers rather than plain wrapped lines. The profile now accepts both and
allows comments and one-line lists as persona values, `citations()` and
`resolve()` move to step 6, and section 8 records the date fix's effect.

revised on: 2026-09-28
Took in the design review's findings (F1–F16). It dropped the legend checks, R13,
`split_from` and the patched-MCP step, made R10 date-free, set `'YYYY-MM-DD'` as
the date form, and added a deny rule for the MCP edit tool and a text-preserving
frontmatter writer for scripts. It also moved the appendices to their own file,
relabeled follow-on work NW1–NW4 (adding NW3 and NW4), and changed step 0 to
rewrite git history.

revised on: 2026-09-26
Added the lint rule catalog (5.15), impact lines for each new finding, and the
MCP round-trip findings (N15) with follow-on work. Also disambiguated write-path
IDs and narrowed root-file snapshots.

Status: **in progress**: steps 0–7 done (see section 8)

Scope: every rule that governs how wiki pages, `raw/` records, frontmatter `sources:`, inline
`[source: ...]` citations, body `## Sources` legends and `[[wikilinks]]` are
written, parsed and checked.

Follows [Lint Frontmatter Checks Design](lint-frontmatter-checks-design.md). That document added checks. This
one steps back and asks which small set of properties would make a broken
reference impossible to create, or at least impossible to keep, and where each
property has to live.

Changes that came from the
[Sources and References Review](sources-and-references-review.md) (F1–F16) are
marked with the finding that caused them, for example "(review F7)". Counts from the review's 2026-09-28 scratch copy are used where
they differ from this document's 2026-09-25 measurements.

Changes that came from the
[Sources and References Plan Review](sources-and-references-plan-review.md)
(P1–P29), an audit of the implementation plan against this document, the review
and the code, are marked the same way, for example "(plan review P9)".

Line references are against the fork at `11fa847` (upstream `2.21.0` plus local
commits). Wiki measurements come from a scratch copy of the private production
wiki taken 2026-09-25 (245 live pages, 242 archive snapshots, 156 `raw/` files).
Every wiki example below is a placeholder. Defect classes are described with
counts, never quoted.

Reference convention: `§N` always means an operation number in the core
`SKILL.md` (for example §2 Ingest, §4 Update). "Section N" means a section of
this document; other files' sections are named with the file. A-numbers (A3,
A11, …) always mean PLUGIN-REVIEW-2026-07-15 items; this document's own IDs
use other prefixes (I, RC, N, W, S, H, K, V, B, R, M, D, NW).

---

## Bottom line

1. **The root cause is that a source has no identity.** Nothing defines what a
   source *is*. Three sites (frontmatter, inline markers, body legend) each hold
   free text that happens to describe one, and no single function maps any of
   them to a file. Every defect in the brief follows from free text being
   accepted as a source: 12 shapes, comma-shredding, the phantom slug, typo'd
   paths, fuzzy R3 matching, legend drift.
2. **The fix is one identifier with one resolution rule.** A *source ID* is the
   file stem of a `raw/` record (or the slug of a wiki page). Frontmatter declares
   the path, inline markers cite the ID, and
   resolution is exact: `id == slug(path)` and `path` exists (`slug()` is the
   file stem, or the folder name for a `README.md` page, section 5.2). IDs are
   `[a-z0-9][a-z0-9._-]*`, so they cannot contain a comma, space or bracket.
   That makes YAML quoting and flow-vs-block style irrelevant, which matters
   because the wiki-search MCP rewrites both.
3. **Conversations become ordinary records.** A fact from chat is captured as a
   small write-once file `raw/internal/conversation-YYYY-MM-DD-<topic>.md` and
   cited like any other source. This is the path-only candidate, with two
   changes: one file per capture instead of a daily append file (so `raw/`
   stays immutable), and a helper script so the capture stays one call. It costs
   micro-capture exactly one extra file write, and I state that trade openly
   (sections 4 and 5.6).
4. **Enforcement is honest about its limits.** Hooks never deny. What is
   *prevented*: malformed IDs (by grammar); MCP page re-serialization (a
   permission rule denies the MCP `edit` tool, which agents have avoided since
   2026-08-11 and the Edit tool fully covers); and date damage (the canonical form
   `'YYYY-MM-DD'` survives every serializer in use). What is *detected*: (a) the
   snapshot hook and a new synchronous post-write validator run on Write/Edit and
   on MCP `vault` writes, so agent tool writes get a pre-image and a same-turn
   violation report; (b) all hand-rolled frontmatter parsers, including
   session-start's, are replaced by one module, which also gives scripts a
   text-preserving field writer; (c) lint remains the only check that sees Bash,
   script, Obsidian and git writes. Session-start already runs it and will report
   a lint failure instead of reading it as "clean", so every write path is
   detected by the next session at the latest. (Review F2, F4, F8.)
5. **Legacy migration is mechanical except for conversational provenance, which
   cannot be recovered.** 81 non-path `sources:` entries and 217 conversational
   markers reference 18 distinct conversation dates with no captured content.
   The migration writes one *reconstructed* record per date from `log.md`,
   marked `reconstructed: true`. That makes the citations resolve without
   claiming provenance that was never captured.

---

## 0. Corrections to the brief (verified against files and git)

| Brief item | What the files show |
|---|---|
| 17: capture-to-raw rule "arrived around v2.5" | It arrived in upstream commit `dfa3b93` (2026-04-20, the v2.0.0 era, CHANGELOG line 712). The same bullet introduced the `user, <date>` attribution. |
| 14: inline grammar "documented since about v2.8" | `[source: raw-slug, location]` arrived in v2.5.0 (`56413ab`, SKILL/SCHEMA). `AGENTS.md` itself was created in v2.6.0 (`67c4adb`). |
| LINT doc: "18 live pages" with flow/block hybrids | At `c4de70c^` (the commit before the repair) I count **17** live pages, 21 orphan items, all under `sources:`. The 18th may have been an archive page or fixed earlier. Not resolved. |
| 2: comma-shredding on 11 pages | 5 were quoted in `5cc416c`. **5 remain**: 4 are still unquoted flow lists, and 1 was converted to block style by the `c4de70c` repair with the shred frozen in as two block items (a bare `conversation` item and a bare date item). |
| 4: typo'd raw paths | All 695 declared `raw/` paths resolve today (repaired in `5cc416c`). The *class* is still undetected by lint. |
| 7: `pre-write.sh` "on Edit reads pre-edit content from disk" | Confirmed (`pre-write.sh:65-71`). Worse than stated: the freshness gate therefore judges the page *before* the edit, so an Edit that removes the last source passes silently and an Edit that adds the first one still triggers the warning. |
| 11: "543766c removed the comma ambiguity from extract_sources" | True only for quoted flow entries. `extract_tags()` still splits PATCH-3a's comma-joined string (`lint.py:133-139`), so a block-style tag with a comma would still shred. No tag contains one today. |
| 19: TestLint | Confirmed: `tests/test_hooks.py:864` has 5 tests and `tests/test_lint.py` has 13. PyYAML 6.0.3 **is** installed (system Python 3.9.6). pytest is not. |
| SKILL.md "~4.3k tokens" (v2.20.0) | The file is 24,625 bytes today (23,938 at `2.21.0`). At a typical ~4 chars/token that is ~6k, so the 4.3k figure used a different estimator. This doc reports deltas in bytes. |

Item 10, evaluated: **the 17-page flow/block hybrid was not produced by the MCP
round-trip.** Every hybrid entered in one commit (`c910309`, a six-day batch).
In each diff the `sources: [...]` line is untouched and new `  - raw/...` lines
are inserted below it. Every other flow list on the page (`tags`, `gaps`) and
every quoted date keep their original serialization. An AST round-trip
re-serializes the whole block and can only emit valid YAML (compare `5cc416c`,
where it converted every flow list to block style). The producer was a
text-level line insertion: an Edit tool call, an ad-hoc script, or an MCP
`line_replace`/`append`. Git cannot tell these apart, because the commit spans
six days of sessions.

The round-trip does have real effects. It was reproduced on 2026-09-26 with the
installed MCP's own js-yaml (v2.3.0 loads and dumps frontmatter with js-yaml's
default schema). (1) It converts flow lists to block style. (2) It rewrites every
*unquoted* date as a timestamp (`2026-09-03` → `2026-09-03T00:00:00.000Z`),
which is N15, reported upstream as wirux/mcp-markdown-vault#49. (3) It keeps
quoted dates quoted, but writes them single-quoted (`'2026-09-03'`), as PyYAML's
dumper also does. Lint's 90-day check (`lint.py:583`) and session-start's stale
scan (`session-start.sh:177`) don't strip single quotes, so they silently skip
those pages: 115 pages for lint and 92 of 143 knowledge pages for session-start
as of 2026-09-28 (review F2).

That means the unquoted `last_verified` in `5cc416c` was **not** produced by
this MCP version, even though the same commit's block-list conversion was. The
writer of that one value is unconfirmed; an Edit or Obsidian's properties editor
are the likely candidates. Either way, a quoted date can end up unquoted, and
PyYAML (YAML 1.1) then loads it as a `datetime.date`, not a string. Any parser
this design adopts must load every scalar as a string.

---

## 1. Invariants

Eight properties, one of them dropped. If I1–I3, I5 and I6 hold, every reference
on a live page can be followed to a file. I7 makes violations recoverable, and I8
makes them revisitable.

| # | Invariant | Single spec location | Write paths that can violate it | Enforcement | Resulting guarantee |
|---|---|---|---|---|---|
| I1 | **Parseable frontmatter.** Every wiki page starts with one frontmatter block that parses under the *frontmatter profile* (section 5.10): unique keys, values are strings, lists of strings, or one level of string mappings, and the required keys are present. | `references/citation-spec.md`, "Frontmatter profile" section (new). `SCHEMA.md` template keeps the field list and points there. | W1–W3, W5, W7–W12, W14–W16, V1–V4, B1–B6 (all page writers) | Write-time advisory (post-validate hook) for tool writes; lint for all (R12 🟡 until migration, then 🔴, with R1/R2/R5 as specific messages; missing frontmatter and missing required keys stay 🔴 throughout, plan review P15) | Detected in the same turn for Write/Edit/MultiEdit and MCP `vault` writes; detected at next session start (or next lint) for Bash, script, Obsidian and git writes. Not prevented. |
| I2 | **Declared ⇒ exists.** Every `sources:` entry is a canonical path (`raw/<dir>/<id>.md` or `<wiki-dir>/<slug>.md`) to a file that exists. | `citation-spec.md`, "Declarations" section | Same as I1, plus any rename or deletion under `raw/` or of a page (B1, B3, V3) | Post-validate hook (stat each path); lint 🔴 (R6) | Same as I1. Because IDs have a closed grammar, a malformed entry *cannot be written by a correct writer*, and no serializer can split one. That is the only prevention-by-construction in the design. |
| I3 | **Cited ⇒ declared.** Every inline citation ID on a page equals the `slug()` of exactly one entry in that page's own `sources:` (section 5.2). | `citation-spec.md`, "Inline grammar" section | Any body edit, including split children and MCP `string_replace` | Post-validate hook; lint 🔴 (R3 rewritten as exact match) | Same as I1. With I2, this closes the chain claim → ID → declared path → file. |
| I4 | **Dropped (review F7).** Was: a `## Sources` legend's IDs equal the declared IDs. No skill or template prescribes legends, agents have almost stopped writing them, and 1 drift instance was found, against a migration of up to 136 prose bullets. Legends are optional free prose, not a declaration site (section 5.5). | — | — | — | — |
| I5 | **Records are unique and write-once.** Every `raw/` record's ID (stem of a `.md` file outside `raw/assets/`) is unique across `raw/` and disjoint from all page slugs, and a record is never modified after creation. | `citation-spec.md`, "Records" section; `AGENTS.md` "No raw/ mutations" points there | W1, W4, V1–V2 (create or overwrite raw), fetcher worker (K1), Bash | Pre-write hook warns on any Write/Edit/MCP edit to an *existing* `raw/` file; lint 🔴 on ID collisions (R9) | Uniqueness is fully detected. Immutability is detected at write time for tool writes only. A Bash or Obsidian edit to a record is invisible except in git. |
| I6 | **Links resolve.** Every `[[target]]` on a live page resolves to exactly one page slug. Slugs are unique across the page directories. | `SCHEMA.md` Conventions (unchanged format; CONTRIBUTING protects it) | Rename, split, archive, supersede (W7–W10), MCP writes that escape `[` | post-write link check (existing); lint 🔴 (existing), supersession auto-fix; lint 🔴 on duplicate page slugs (R9, review F11) | Unchanged from today, plus `briefings/` coverage, a checked slug-uniqueness rule, and the escape check at write time. |
| I7 | **Recoverable.** Before an agent tool overwrites, deletes or archives a page, a pre-image exists in `_archive/<slug>-<date>.md`, or in git. | `AGENTS.md` "Snapshot before destructive ops" (kept as the behavioral rule), with the mechanism in `hooks/README.md` | Every page writer | PreToolUse hook extended to MCP `vault` writes (and `edit`, for installs that don't deny it); lint `--auto-fix` snapshots before writing; Bash/script writers keep the behavioral rule | Guaranteed (best-effort I/O) for the first tool write per page per day, **including MCP `vault` writes after this change**. Not guaranteed for Bash, script, Obsidian or git writes, or for the second write of the day to the same page. For those, git is the undo, and the wiki is a git repo. |
| I8 | **Revisitable.** A page whose only primary sources are conversation records (or reconstructed records) is listed until a non-conversation primary record is declared on it. No date clears it (review F1). | `citation-spec.md`, "Revisit" section | Any write that leaves a page resting only on conversation or reconstructed records | Lint 🔵 (R10), listed in `_status.md` | Surfaced, never forced. It clears only when someone saves and declares a real primary record, which an ordinary edit can't fake. This is the revisit obligation ISSUE-1 and ISSUE-3 lack (brief item 13). |

Not an invariant, by decision: *declared ⇒ cited*. `ingest-guide.md ⑤` says
frontmatter lists all sources while markers anchor specific claims. On this wiki,
211 of 694 declared raw sources are never cited inline, spread over 84 pages.
Most are legitimate. It stays a ratio heuristic (R4) on every page. The split
procedure (section 5.8) prevents the copy-paste signature at the source, and R4
still flags split pages that skip it (review F9).

### Which invariants inherit the MCP hole

Today the wiki-search MCP write tools trigger no hook, so for MCP writes **I1,
I2, I3, I5, I6 (write-time part) and I7 all degrade to lint-only**, and I7 is
simply absent: no snapshot, no undo except git. The revised design closes most of
this by prevention rather than coverage (review F4):

- **Only some MCP operations damage pages.** `frontmatter_set` and the AST
  operations (`append`, `prepend`, `replace`, `delete`) re-serialize the whole
  page. That causes the `\[` escaping (#47) and the timestamp dates (#49).
  `string_replace` and `line_replace` edit the raw text, and `vault.update` writes
  its content verbatim.
- **The damaging operations are all in the `edit` tool, and it is denied.** A
  `permissions.deny` rule covers `mcp__wiki-search__edit` and
  `mcp__plugin_llm-wiki-pm_wiki-search__edit` (section 5.11, item 1). Agents have
  avoided it since 2026-08-11, when an MCP edit re-escaped wikilinks across whole
  files, and the Edit tool covers every operation it offers. A permission rule is
  not a hook, so "hooks never deny" still holds.
- **`vault` writes stay hooked.** After step 3 of the plan (section 8), the hook
  matchers include both name forms of `vault` and `edit`. The hooks act only on
  `vault` create/update/delete and skip `dryRun` edits (review F13), so they also
  cover installs that haven't added the deny rule.
- **For those installs, `edit` is not simulated.** The pre-hook snapshots but
  cannot compute the post-image, so validation happens after the write, and the
  `\[` bug is detected and repaired rather than prevented.
- **`meta/contract.md` still competes.** The MCP tells agents to read it, and its
  default describes a different schema. `vault.create` requires content and never
  applies the contract's Note Template automatically (review F10), but an agent
  may copy it. Fixed by reconciling the contract (section 5.10), not by a hook.

`AGENTS.md`'s "Snapshot before destructive ops" stays as written, relabeled as
the obligation *for the paths the hook cannot see* (Bash `mv`, scripts, lint
before its own fix lands). This follows the author's "mechanize or relabel"
rule: the mechanized part is stated as automatic and the rest as a checklist.

---

## 2. Write-path inventory

Every operation that creates or modifies a page or a raw file, from reading every
SKILL.md, reference, template, hook, worker and `lint.py`. **Hook** = which of
today's hooks fire. **Refs** = what it writes into reference sites.

### Core skill (`skills/llm-wiki-pm`)

| ID | Operation | Writes | Tool | Hook today | Refs written |
|---|---|---|---|---|---|
| W1 | §2 ① raw capture (`ingest-guide ①`: articles, papers, transcripts, chat, email, warehouse, conversation) | new `raw/**` | Write, fetcher worker | pre-write exits (raw/ exempt) | the record itself; `source_*` fields |
| W2 | §2 micro-capture (append or stub) | page | Write/Edit **or MCP** | pre-write only if Write/Edit | `source: conversation \| <date>` (a shape no other doc uses) |
| W3 | §2 ⑤ create/update pages | pages | Write/Edit/MCP | same | sources, markers, legend, links |
| W4 | §2 ④ enrichment capture (`raw/internal/<topic>-<source>-<date>.md`) | new raw | Write | exempt | record |
| W5 | §2 ⑥ backlink audit, ⑦ overview, ⑧ index + log, ⑨ MY-INTEGRATIONS | other pages, root files | Edit/MCP | overview/index/log exempt from snapshot **and** gate | links |
| W6 | §2 ⑪ crystallize digest (`queries/crystallize-*`) | new page | Write | gate | sources (template: paths) |
| W7 | §2 ⑫ entity promotion: new entity page + rewrite of the concept page. **This is a split.** | 2+ pages | Write/Edit | gate + snapshot | sources copied or not; links |
| W8 | §4 Update + stale-claim sweep (N pages) | pages | Edit/MCP | snapshot (first edit/day) | markers, sources |
| W9 | §6 Archive (move to `_archive/`, rewrite inbound links to plain text) | page move, inbound pages | Bash `mv` or Write + delete | none for the move | removes links |
| W10 | Supersede (`update-guide.md` section 6) | 2 pages + archive + link rewrite | Edit + lint auto-fix | partial | `supersedes`/`superseded_by` |
| W11 | Page split for >200 lines (`SCHEMA.md` Page Thresholds) | parent + children | anything | partial | **no procedure exists** (finding 8) |
| W12 | §3 ⑥ file an answer (`queries/<slug>/README.md`) | new page | Write | gate; snapshot **named `README-<date>.md`** (collision, new finding N14) | sources (often wiki pages) |
| W13 | §7/§9–§13 logging | `log.md` | Edit/Bash | exempt | none |
| W14 | §5 lint | `queries/lint-<date>.md`, `log.md` append | Python | none | report |
| W15 | §5 lint `--auto-fix` | index, link rewrites, de-escape, on any page | Python `write_text` | **none, and no snapshot** | links |
| W16 | §1 scaffold | SCHEMA, index, overview, log | session-start (Bash) | none | templates |

### Sub-skills

| ID | Operation | Refs it prescribes |
|---|---|---|
| S1 | brief: file `queries/weekly-brief-*`, tag digests | `sources:` of structural files (`log.md` etc.) in practice (2 pages) |
| S2 | maintain: `briefings/YYYY-MM-DD.md`; rotation `mv` to `_archive/briefings/` (dropped, review F12); autonomous `lint --auto-fix` | **`briefings/` is outside every hook gate and lint scan** (new finding N2) |
| S3 | crm: company/person enrichment; `queries/account-health-*`, `feature-asks-*`; SCHEMA merge | inline `[source: <url>, <date>]` (URL IDs, contradicts AGENTS.md) |
| S4 | persona: `entities/<name>-persona.md`, `concepts/relationship-map.md` | `sources: [entities/<name>.md, raw/...]` (wiki-page source) |
| S5 | prd: `queries/prd-*/README.md`, user stories, release notes | template prescribes `[source: [[wiki-page]]]` (origin of the bracket-truncation class, N3); `sources:` = wiki pages |
| S6 | research: raw via fetcher; `queries/research-*/README.md`; entity updates | `sources: [<raw slugs>]` (slugs, not paths); inline `[source: url, date]` |
| S7 | set-wiki-path | `.wiki-path` (config only) |

### Hooks, workers, MCP, other

| ID | Operation | Notes |
|---|---|---|
| H1 | session-start: scaffold, `_status.md`, `.wiki-lock`, **runs `lint.py --json`, which writes `queries/lint-<date>.md` every session** (N1) | Hidden writer. It is why that report shows as modified in the wiki's git status after any session. |
| H2 | pre-write: `_archive/<stem>-<date>.md` snapshots | stem, not slug, so all `README.md` pages collide (1 collision exists) |
| H3 | post-write: `_status.md` appends | async |
| H4 | session-stop: rotates `log.md` with `mv`, removes lock | |
| K1 | worker-source-fetcher: new `raw/**` | writes `private:` into raw frontmatter (14 records carry it) and tells callers to flag `private: true` (v2.20.0 missed it, N5); its slug table disagrees with `ingest-guide ①` routing |
| K2 | worker-wiki-indexer: rewrites `index.md`, `overview.md` | `overview` is exempt from snapshot, so an ISSUE-2 regeneration has no pre-image |
| K3 | worker-lint | runs W14 |
| V1 | MCP `vault.create` / `create_from_template` | new file; `create` requires content, and the contract's Note Template is advisory text an agent may copy (review F10) |
| V2 | MCP `vault.update` | whole-file overwrite, no snapshot today |
| V3 | MCP `vault.delete` | **deletion with no snapshot today** |
| V4 | MCP `edit` (append, prepend, replace, delete-section, line_replace, string_replace, frontmatter_set; batch ≤50 paths) | `frontmatter_set` and the AST operations re-serialize the page (#47 `\[` bug, #49 dates); `line_replace`/`string_replace` are text-level. Denied by permission rule after step 3 (review F4) |
| V5 | MCP `system.save_overview` | `meta/overview.md` (not a wiki page) |
| B1 | Bash `mv`/`sed`/heredoc | No hooks ever; lint only |
| B2 | Ad-hoc scripts (for example the page-splitting script) | No hooks ever; lint only |
| B3 | Obsidian edits (including renames) | No hooks ever; lint only |
| B4 | `git` checkout/merge | No hooks ever; lint only |
| B5 | User hand-edits outside Claude Code | No hooks ever; lint only |
| B6 | lint `--auto-fix` (same writer as W15) | No hooks ever; lint only |

---

## 3. Root causes

Plain-language explanations of each root cause are in Appendix A
([Sources and References Appendices](sources-and-references-appendices.md)).

| RC | Root cause | Findings it explains |
|---|---|---|
| **RC1** | **No source identity.** There is no definition of a source ID or a resolution function. Each of three declaration sites accepts free text, and "is this a source?" is answered by a prefix test (`not startswith(entities/…)`). **This is the biggest root cause.** | 1, 2, 3, 4, 6, 12, 14, 16; R3's permissive matcher; N3, N4, N7 |
| RC2 | **The honest path for conversational facts is more expensive than the dishonest one.** Capture-to-raw (v2.0.0) is a full ingest; the v2.20.0 fast path skips it by design (A13) and prescribes a citation shape that resolves to nothing. `ae33f9d` then made a *third* shape official for Update. | 1, 3, 17, ISSUE-3 A |
| RC3 | **No frontmatter profile, at least four parsers.** No document says what subset of YAML a page may use, so each parser guesses: `parse_frontmatter`, `extract_sources`, the copy in `pre-write.sh`, and session-start's stale scan (`session-start.sh:151-189`, review F2). PATCH-3a added another behavior by joining lists into strings. | 5, 10, 11 |
| RC4 | **Enforcement is attached to tool names, not to files.** The hooks match Write/Edit/MultiEdit, so MCP, Bash, scripts, lint `--auto-fix` and session-start are unseen writers, and `briefings/` sits outside the gate entirely. | 7, 10, 18; N1, N2, N14 |
| RC5 | **Derived-page operations have no reference procedure.** Split, entity promotion, supersede and crystallize say nothing about which sources and links the new page may carry. | 3 (propagation into 10 files), 8 |
| RC6 | **Nothing revisits a citation.** Write-time rules only. There is no horizon, verification date, or status that brings a citation back. | 13, ISSUE-1, ISSUE-3 |
| RC7 | **Duplicated surfaces drift.** Two worker copies, templates showing one shape, a default MCP contract, stale README/CONTRIBUTING, sub-skills that predate AGENTS.md's grammar. | 9, 15, 18, 20; N5, N8, N9 |

New findings (N) not in the brief. Appendix B
([Sources and References Appendices](sources-and-references-appendices.md)) explains each one in plain terms:

- **N1** `session-start.sh:136` runs lint in `--json` mode, and `lint.py:753` writes
  the report before the `--json` early return. Every session start writes a page
  into `queries/`.
  **Impact:** Starting any session quietly writes a lint report into the wiki, which clutters `queries/` and your git changes and can overwrite a report from a lint run you did yourself earlier that day, but it never damages page content.
- **N2** `llm-wiki-maintain` writes `briefings/YYYY-MM-DD.md`. `briefings/` is in
  neither `WIKI_DIRS` (lint) nor the pre-write gate, so briefs are unlinted,
  unsnapshotted, and invisible as link targets.
  **Impact:** Daily briefs get no backup before they change and no checks after, and lint can't tell a correct link to a brief from a broken one.
- **N3** Three documented citation forms that lint cannot resolve:
  `[source: [[wiki-page]]]` (`prd-templates.md:91`, truncated by the marker
  regex), `(per [[raw/articles/…]])` (`update-guide.md:77`, `output-formats.md:89-90`,
  which lint would report as a broken wikilink), and `[source: <url>, <date>]`
  (crm:104, research:197).
  **Impact:** Templates and guides teach agents three ways of citing that lint can't match to anything, so following the instructions faithfully produces citations reported as broken or unresolvable.
- **N4** Four definitions of required frontmatter disagree: `lint.py:15` (6 keys
  incl. `created`), CONTRIBUTING (incl. `coverage`, no `created`),
  worker-link-validator (4 keys), `meta/contract.md` (`status`, no `sources`).
  **Impact:** Whether a page counts as complete depends on which document you ask, so an agent that follows one of them can produce pages another tool flags as missing fields.
- **N5** `worker-source-fetcher` still writes `private:` into raw records and
  instructs `private: true` on pages. 14 raw records carry it.
  **Impact:** The helper that saves sources keeps stamping files with a privacy label nothing reads, which suggests a protection that doesn't exist and has already put the label on 14 records.
- **N6** A date can lose its quotes (one observed case, in `5cc416c`; writer
  unconfirmed, see section 0), and an unquoted date is a date object, not text,
  to YAML 1.1 readers such as PyYAML. The MCP's own date damage is N15.
  **Impact:** A date stored as text can silently become a real date value, harmless to today's tools but a trap for any future tool that reads the files with a standard YAML library.
- **N7** Marker defects beyond the brief, measured over 1,070 markers: 55 span a
  newline; 9 are hard-wrapped *inside* the slug; 8 carry a nested `source:`
  prefix; 5 cite two sources joined by "vs."; 6 cite a structural file; 4 are
  free prose; 2 cite a script path; 1 wraps a wikilink.
  **Impact:** 35 inline citations are written in ways no tool can follow, which adds noise to lint's missing-citation reports and leaves readers unable to trace those claims.
- **N8** `llm-wiki-prd` still says "Orient gate (enforced) … refuse any write",
  the fake-gate label A7 removed from the core skill.
  **Impact:** The PRD sub-skill still claims a write gate is enforced when nothing enforces it, which misleads the agent and anyone reading the skill about what is actually guaranteed.
- **N9** `worker-link-validator` resolves links only in
  entities/concepts/comparisons, so every link into `queries/` reads as broken.
  **Impact:** If the link-checking helper is ever used, it would report hundreds of working links into `queries/` as broken and bury any real problem.
- **N10** `raw/` record and binary asset share a stem in 2 cases (extracted
  `.md` plus the original PDF/PPTX). Harmless once IDs are defined over `.md`
  records outside `raw/assets/`.
  **Impact:** Two saved sources share a name with their original PDF or slide file, which is harmless today but would make a citation ambiguous under the new naming rules unless those originals are excluded.
- **N11** 11 of 153 raw `.md` records have no frontmatter; 2 raw files are
  referenced by no page.
  **Impact:** 11 saved sources carry no description of where or when they came from, and two were saved but never used, so their provenance is weaker or their purpose unclear.
- **N12** Two public fork files contain the names of real people or customer
  companies from the private wiki: `tests/test_lint.py` (2 lines) and the
  [Lint Frontmatter Checks Design](lint-frontmatter-checks-design.md) (4 lines).
  Product names and page-topic names (for example CFP) are not treated as private
  and stay. See decision D8.
  **Impact:** Names of people and customers from the private wiki are published in the public fork on GitHub, in one doc and a test file.
- **N13** `hooks/wiki-search.sh:12`: the stderr bug from the brief is confirmed by
  running the launcher in an empty directory. It was introduced by the v2.20.0 fix
  for A11, and A11's smoke test was never written.
  **Impact:** Every session started outside a wiki folder logs a misleading "No such file or directory" error from the wiki-search tool, which does no harm but looks like a failure and wastes troubleshooting time.
- **N14** `pre-write.sh:39` names snapshots by filename stem, so every
  `queries/<slug>/README.md` page snapshots to `_archive/README-<date>.md`.
  Only the first one per day survives (1 such file exists).
  **Impact:** Directory-style pages named `README.md` all share one backup filename, so on a day when several are edited only the first gets a backup, and the backup doesn't say which page it came from.
- **N15** 13 pages store dates as full timestamps (`YYYY-MM-DDT00:00:00.000Z`)
  instead of `YYYY-MM-DD`: 13 `created`, 3 `last_verified` and 1 `updated`
  values. **Mechanism confirmed, writer likely:** the wiki-search MCP's
  frontmatter merge (`mcp-tools.js` ~291–305, also `batch-edit.js` and
  `markdown-file-repository.js`) loads and dumps with js-yaml's default schema,
  which parses an unquoted date as a date object and writes it back as a
  timestamp. It was reproduced with the MCP's own js-yaml. New values entered the
  wiki in five commits (08-05 to 09-04), and `log.md` records MCP
  `frontmatter_set` use on 2026-08-05 and 2026-08-11. The later commits' writer is
  unconfirmed, because a third of the editing days have no saved transcript
  (review F4). It is the same full-file round-trip as
  PATCH-3d's bracket escaping (#47), and it is reported upstream as
  wirux/mcp-markdown-vault#49. Python 3.9's `datetime.fromisoformat` rejects the
  trailing `Z`, so lint's 90-day staleness and 120-day `last_verified` checks
  (`lint.py:537-593`) and session-start's stale/decay scan silently skip those
  values. The same round-trip writes *quoted* dates single-quoted, which lint's
  `updated` check (`lint.py:583`) and session-start's scan
  (`session-start.sh:177`) don't strip either (review F2).
  **Impact:** far larger than the timestamps alone. Lint's 90-day check can't read `updated` on 115 pages, and session-start's 30-day scan skips 92 of 143 knowledge pages: on 2026-09-28 the health line reported 49 stale pages when 66 were. Nothing reports that the checks were skipped.

---

## 4. Evaluating the candidates

The problem each option must solve: facts that arrive without an artifact (chat,
verbal relay, the user) must end up cited by an ID that resolves, without making
micro-capture a ceremony, and without an invariant that the MCP's serializer
breaks.

|                                                         | A. Path-only + daily file (undecided candidate)                                                                       | B. Mandated block-style lists                                                             | C. `raw/inbox/` queue + lint age warning (PLUGIN-REVIEW OD4)                                  | **D. Source IDs + write-once capture records (proposed)**                                                                                      |
| ------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Idea                                                    | Every `sources:` entry is an existing path; conversations are appended to `raw/internal/conversation-YYYY-MM-DD.md`   | Frontmatter lists are always block style, so an item can't be split by commas             | Unprocessed captures land in `raw/inbox/`; lint warns when one ages without being filed       | A's path rule plus a defined ID grammar and exact stem resolution shared by all three sites. One record per capture, written once, by a helper |
| Resolves I2                                             | Yes                                                                                                                   | **No.** A block item can still be `user, conversation, DATE`, so it only fixes shredding. | Partly: inbox items resolve, but moving them out when processed breaks every citation to them | Yes                                                                                                                                            |
| Resolves I3 (inline ↔ frontmatter)                      | Only if paired with a resolution rule; A doesn't define one                                                           | No                                                                                        | No                                                                                            | Yes, exact match                                                                                                                               |
| Survives MCP re-serialization                           | Yes (paths need no quoting)                                                                                           | Yes, and it matches MCP output style                                                      | Yes                                                                                           | Yes. Style becomes irrelevant, not mandated.                                                                                                   |
| Keeps `raw/` immutable                                  | **No.** Appending to today's file mutates a Layer-1 record several times a day, and two sessions can race the append. | n/a                                                                                       | Only if items never move, which defeats "queue"                                               | Yes. A record is complete when written.                                                                                                        |
| Micro-capture cost                                      | +1 Edit (append) per fact, and the agent must read the file first to append safely                                    | 0                                                                                         | +1 Write, plus a later triage                                                                 | +1 Write, or one `capture.py` call, per fact or per topic                                                                                      |
| Directory layout change (semver major per CONTRIBUTING) | No                                                                                                                    | No                                                                                        | **Yes** (`raw/inbox/`)                                                                        | No (`raw/internal/` exists)                                                                                                                    |
| Upstream conflict surface                               | Small                                                                                                                 | Small (templates)                                                                         | Medium (SCHEMA, lint, scaffold)                                                               | Small to medium: one new reference file, lint, hooks, a few SKILL.md lines                                                                     |
| Verdict                                                 | Right direction; the append mechanism is wrong                                                                        | Do it as a template default only. Unnecessary as a rule once IDs can't contain commas.    | Solves a different problem (deferred filing). Decline for now; OD4 stays open (section 6).    | **Adopt**                                                                                                                                      |

Why D instead of A: A gets the invariant right (every entry resolves to a file)
but leaves two gaps. It never says how an inline marker maps to a frontmatter
path, and the daily append file breaks the "no raw/ mutations" contract and
races concurrent sessions, which the wiki already guards against with
`.wiki-lock`. D keeps A's invariant, adds the one resolution function, and makes
records write-once.

**The cost to micro-capture, stated plainly.** Today a micro-capture is dedup
search → page edit → log line. Under D it is dedup search → **one Write of a
~6-line record** → page edit → log line. That is one extra tool call and no
extra reads. The ingest-guide read, crystallize, entity-promotion and
freshness-sweep skips all stay. `scripts/capture.py` (section 5.6) collapses the record
write and ID generation into one Bash call that prints the path and ID to paste.
This does break the literal reading of A13 ("exactly one mandatory step"), and I
consider it justified: the fast path's own citation shape is the single largest
source of unresolvable references in the wiki (217 markers, 58 frontmatter
entries), so the fast path is where the invariant has to be paid for.

---

## 5. Proposed rules and canonical formats

All normative text below goes into **one new file,
`skills/llm-wiki-pm/references/citation-spec.md`**. Every other location (AGENTS.md
Source Attribution, SCHEMA.md template Inline Provenance, ingest-guide ① "Current
conversation" and ⑤, update-guide section 3, sub-skills, templates) is reduced to a
one-line pointer plus at most one example (plan review P9). That makes it the
single spec location for I1–I3, I5 and I8.

### 5.1 Records (`raw/`)

- A **record** is a `.md` file under `raw/`, outside `raw/assets/`. Binary
  originals live in `raw/assets/` and are referenced from their record's
  `asset:` field. They are never cited directly.
- **ID** = the record's filename stem. Grammar: `[a-z0-9][a-z0-9._-]*`. It must
  be unique across all records and must not equal any page slug (I5). Today:
  0 collisions with page slugs, 0 stems outside the grammar, 2 record/asset
  stem pairs (allowed by the asset exclusion).
- Naming: `<descriptor>-<YYYY-MM-DD>` (or `-<YYYY>` for undated publications).
  Directory routing is as in `ingest-guide ①`. `worker-source-fetcher`'s table is
  replaced by a pointer to it. Two folders outside that routing,
  `raw/attachments/` and `raw/clippings/` (one file each today), are emptied into
  routed folders by the migration (section 7, review F15).
- Record frontmatter. All fields are optional; the block below is the
  recommended template, not a checked rule. `capture.py` and migration step M2
  write `source_type: conversation`, the one value a rule reads (R10). The
  earlier R13 check is dropped: no current record writer emits `source_type`, the
  fetcher writes `fetched:` and ingest-guide prescribes `source_date_range:`, and
  a filename-date filter never sees the 42 of 153 records without a full date
  (review F6).

```yaml
---
title: "Pricing page, competitor-x"
source_type: web            # web | pdf | transcript | chat | email | warehouse | conversation | internal | other
captured: '2026-01-15'
source_url: https://example.com/pricing      # web
source_channel: "Chat:#product-strategy"     # chat/email (existing field)
source_query_ref: "saved-query-123"          # warehouse (existing field)
source_snapshot: "month_id=202601"           # warehouse (existing field)
stated_by: user                              # conversation: user | <person-slug>
asset: raw/assets/example-deck-2026-01.pdf   # optional binary original
---
```

  `private:` is dropped from records (the page allowlist model governs export).
- **Write-once.** After creation a record is never edited. Pre-write warns on
  any edit to an existing record (section 5.11). If a saved record is itself
  wrong (a capture error, which has happened once in 156 records), save a new
  record, note in its body which record it replaces, and run the Update flow
  (§4) on the pages that cite the old one. A change in the world, or a later
  statement that differs from an earlier one, is not a correction: the old record
  is still an accurate capture, and the pages are revised through the Update flow
  as usual. No special field or rule is needed for either case.

### 5.2 Page slugs and IDs

- Page slug = filename stem, or the parent directory name for `README.md`
  (lint's existing `slug()`). Grammar as for IDs; unique across `entities/`,
  `concepts/`, `comparisons/`, `queries/`, and `briefings/` (added, section 5.11).
  R9 checks uniqueness; today lint silently keeps the last page on a collision
  (`lint.py:404`, review F11).
- **`slug()` is the one ID function** for every reference site. For a raw record
  it returns the filename stem (records are never named `README.md`). For a
  directory page, `queries/<slug>/README.md`, it returns the folder name, so the
  page is linked as `[[<slug>]]`, declared by its path
  `queries/<slug>/README.md`, cited as `[source: <slug>, …]`, and snapshotted as
  `_archive/<slug>-<date>.md`.
- **Other files inside a directory page.** Any other `.md` file in the folder
  must be either a real page (full frontmatter and a slug unique across the
  wiki, like a research sprint's part pages) or an artifact stored under the
  folder's `assets/` subfolder, which lint and the hooks skip. A bare `deck.md`
  next to `README.md`, as `output-formats.md` showed until step 5, would be scanned as a
  page with no frontmatter, and two directory pages each holding one would
  collide on the slug `deck`. Non-markdown artifacts (`.py`, `.png`, `.csv`,
  `.pdf`) may stay beside `README.md`, since lint only scans `.md` files.
- A wiki page may be a source (crystallize digest, concept page, persona's
  entity page). Its ID is its slug and it is declared by path. It is a
  **secondary** source for grounding purposes.
- Not sources: `log.md`, `index.md`, `SCHEMA.md`, `MY-INTEGRATIONS.md`,
  `_status.md`, `_archive/**`, any other root-level markdown file that isn't a
  page (the wiki has three, including an action-items file handled by NW4;
  review F15), absolute paths, anything outside the wiki.
  `SCHEMA.md` is Orient context, not a citable source: it is edited over time,
  so a citation to it would later point at different text without anyone
  noticing. Context kept in SCHEMA (for example the owner's role or org notes in
  its Domain section) stays where it is, because Orient reads it every session.
  A page that relies on one of those facts cites a user-statement record
  (`stated_by: user`) instead, exactly as for a fact stated in chat. 3 pages cite
  SCHEMA this way today (section 7). Where org structure should live, and
  whether Orient should read the relationship map, is left to the follow-on
  design on Orient content (NW1).

### 5.3 Frontmatter `sources:`

A list of canonical paths. Style is free; templates show block style because
that is what the MCP emits, which minimizes diff churn.

```yaml
# valid
sources:
  - raw/articles/competitor-x-pricing-2026-01-15.md
  - raw/internal/conversation-2026-01-15-pricing-tier.md
  - queries/crystallize-pricing-review-2026-01-10.md
sources: [raw/articles/competitor-x-pricing-2026-01-15.md]   # also valid

# invalid (each with the rule that reports it)
sources: [conversation, 2026-01-15]              # R6: not a path (shredded)
sources: ["user, conversation, 2026-01-15"]      # R6: not a path
sources: [raw/papers/competitor-x-pricing.md]    # R6: path does not exist
sources: [competitor-x-pricing-2026-01-15]       # R6: bare ID; declare the path
sources: [SCHEMA.md]                             # R6: structural file is not a source
sources: [raw/assets/deck-2026-01.pdf]           # R6: cite the record, not the asset
```

Grounding (existing `lint.py:502-520`) is redefined on what each entry names
(plan review P17): *primary* = the path of a record; *secondary* = the path of
a page. Anything else (a conversation shape, a URL, a root file) is neither,
where the old prefix test counted it as primary. A path counts even when its
file doesn't exist: R6 reports the missing file, and the grounding check keeps
treating the entry as what it names, which keeps `test_hooks.py`'s `TestLint`
fixtures valid. Pages with `lifecycle: dated-digest` are exempt from grounding
(D6). Both landed in step 6, and on a copy of the wiki they changed no page's
verdict.

### 5.4 Inline citations

Starts from `AGENTS.md`'s `[source: raw-slug, location]`, now formally:

```
marker   = "[source: " cite *( "; " cite ) "]"      ; one line, no newline inside
cite     = id [ ", " location ]
id       = [a-z0-9][a-z0-9._-]*                     ; must equal slug() of a sources: entry on this page
location = 1*( any char except "[" "]" ";" newline ) ; page, section, timestamp, "query <ref>"
```

```markdown
Valid
Competitor X lists three tiers [source: competitor-x-pricing-2026-01-15, "Plans"].
The team chose usage-based billing [source: conversation-2026-01-15-pricing-tier].
ARR was flat [source: metric-arr-202601, query saved-query-123].
Two sources agree [source: vendor-y-docs-2026, "Hooks"; competitor-x-docs-2026, "Hooks"].
Per the digest [source: crystallize-pricing-review-2026-01-10, Decisions].

Invalid
[source: user, conversation, 2026-01-15]         id "user" does not resolve (R3)
[source: raw/articles/competitor-x-pricing-2026-01-15.md]   path form; use the ID (R7, auto-fixable)
[source: source: competitor-x-pricing-2026-01-15]           nested prefix (R7, auto-fixable)
[source: competitor-x-
pricing-2026-01-15, p.3]                          wrapped marker (R7, auto-fixable when the join resolves)
[source: vendor-y-docs-2026 vs. competitor-x-docs-2026]     use ";" (R7)
[source: [[crystallize-pricing-review-2026-01-10]]]         wikilink inside a marker (R7)
[source: https://example.com/pricing, 2026-01-15]           URL; capture the page as a record (R3 and R7, see D2)
[source: SCHEMA.md org chart]                    structural file (R3 and R7)
```

Resolution is exact and page-local: split the marker on `"; "`, take the text
before the first `", "` as the ID, and look it up in
`{slug(p): p for p in sources}`, using the `slug()` function from section 5.2. No substring matching and no conversational
exemption. `_citation_matches_source` and `_is_conversation_citation` are
deleted. R4, which counts cited sources with `_citation_matches_source` today,
then counts a source as cited when a marker's ID equals its `slug()` (plan
review P18).

The ID is read once R7's mechanical defects are undone: a path becomes its
slug, a wrapped ID is joined, a nested `source:` is dropped, `a vs. b` is two
citations, and a wikilink gives its target (step 6). So a path-form or wrapped
citation of a declared source is R7 only, as the examples above show, while a
citation that is malformed and resolves to nothing, such as a URL or
`SCHEMA.md org chart`, is both R3 and R7.

`update-guide.md:77` and `output-formats.md:89-90` stop showing `[[raw/…]]`
wikilinks as citations. `update-guide.md`'s `ae33f9d` block (lines 84-96) and
`prd-templates.md:91` (`[source: [[wiki-page]]]`) change to the ID form too
(plan review P11). Prose citations of wiki pages ("Per [[page]]") remain
valid *as links* (I6). They are not source citations and need no declaration.

### 5.5 `## Sources` legend

Optional free prose, with no required format. A legend is **not** a declaration
site: `sources:` declares, markers cite, and lint doesn't read legends.

Revised 2026-09-28 (review F7, D4): the earlier ID-prefixed grammar, invariant
I4, rule R8 and migration step M6 are dropped. No skill, template or AGENTS.md
prescribes a legend. Agents added 49 legend headings in the wiki's first five
weeks, then none for two weeks and 2 in the week after. Only one drift instance was ever
found (ISSUE-3). Checking legends would have cost a human-confirmed migration of
up to 136 prose bullets and an auto-fix writing into human prose.

### 5.6 Conversational facts (micro-capture and Update)

Rule: **a fact with no artifact gets a record before it gets a citation.** It
applies to micro-capture, Update, Learn and CRM alike.

- Record: `raw/internal/conversation-YYYY-MM-DD-<topic>.md`, `source_type:
  conversation`, `stated_by:`, and the statement near-verbatim. One record per
  topic per conversation. A later fact on the same topic gets a new record with a
  `-2` suffix, never an append.
- `skills/llm-wiki-pm/scripts/capture.py <wiki> --topic <slug> [--stated-by
  user] < statement` writes the record with correct frontmatter (including
  `source_type: conversation`, which R10 reads), picks the next free suffix
  (`-2`, `-3`, …) when the topic already has a record that day, never
  overwrites, and prints the path (for `sources:`) and ID (for the marker). It is
  one Bash call, stdlib only, and writes through `wikifm` (section 5.10). Its
  tests go in `tests/test_capture.py` (plan review P12).
- Tool-retrieved facts (a chat thread read via MCP) are *not* conversation
  records. They follow the chat/email capture routes (`ingest-guide ①`), as today.
- The SKILL.md §2 fast path changes from `source: conversation | <date>` to
  "capture a record (`capture.py`), cite its ID". The §4 ③ text from `ae33f9d`
  shrinks to two lines pointing at this section. "Never coin an ID for a record
  that doesn't exist" survives verbatim as the one-line reason.

### 5.7 Non-file sources

- **Web**: captured as a record (`source_type: web`, `source_url`). The
  CRM enrichment steps and research's stub enrichment delegate capture to
  `worker-source-fetcher`, as research's sprints already do: fetch each source
  used, declare the record's path and cite its ID. Today both enrichment
  procedures cite `[source: <url>, <date>]` with no capture (plan review P10).
  D2 asks whether a URL may stand in as an ID for low-stakes enrichment. My
  recommendation is no.
- **Warehouse**: already file-shaped. The snapshot record
  `raw/internal/<metric>-<snapshot>.md` *is* the source, and `query <ref>` is the
  citation's location: `[source: metric-arr-202601, query saved-query-123]`. The
  existing `source_query_ref`/`source_snapshot` fields stay on the record, where
  they describe the artifact, as ingest-guide ① already prescribes (plan review
  P14).
- **Email/chat/transcripts/PDF**: unchanged routes. The ID is the record stem.
- **Live read without capture** (a fact read from a system but not saved): not
  citable. Capture a record of what was read, or leave the claim uncited and
  add it to `gaps:`. This is the source-depth guard's "open what you found", made
  concrete.

### 5.8 Page lifecycle

- **Create**: slug per section 5.2; required frontmatter per section 5.10; ≥2 outbound
  wikilinks (unchanged); sources limited to what the body cites or the page is
  genuinely built from.
- **Split** (new procedure; covers the >200-line rule, entity promotion W7, and
  history splits). Splits are frequent: 15 in one week, done by agent-written
  scripts, with 25 pages over the limit on 2026-09-28. They are also where
  errors multiply, since a split copies whatever is wrong on the parent onto
  every child.
  1. Snapshot the parent (automatic for tool writes).
  2. Set each child's `sources:` to the paths of exactly the IDs its body cites,
     computed with `lint.py --cited-sources <page>`. The new flag prints the
     canonical path of each ID the page cites, resolved against every record and
     page with `slug()` (a new child declares nothing yet, so page-local
     resolution would find nothing), lists IDs that resolve to nothing, and
     writes nothing: no report and no `log.md` entry (plan review P19).
  3. Run `--cited-sources` on the parent too, and trim its `sources:` to what it
     still cites (review F9: the procedure missed this step).
  4. Link parent and children to each other.
  5. Rewrite `[[parent#heading]]` anchors that point at moved sections.

  **Where agents find it (review F9).** The 200-line rule lives in SCHEMA.md and
  lint's warning, not in SKILL.md, and agents read this spec only on demand. So
  one line, "follow the split procedure in `citation-spec.md` and set each page's
  sources with `lint.py --cited-sources`", goes into:
  - the split rule in SCHEMA.md, in both the template and the live wiki's copy
    (a scaffolded copy doesn't update with the template);
  - lint's "> 200 lines — split candidate" warning;
  - `ingest-guide.md` ⑫ (entity promotion is a split);
  - post-validate's output, when a write takes a page over 200 lines
    (section 5.11, item 6). This is the one place the reminder reaches the agent
    at the moment it matters, since session-start doesn't pass lint's size
    warnings on.

  No `split_from` field and no stricter R4 tier. A label set by hand wouldn't be
  set by the scripts that caused the problem, and would pin a child to a
  stricter rule permanently. R3 (a child citing an undeclared source) and R4
  (a page declaring many uncited sources) already cover every page, with or
  without a label. If lint keeps flagging split pages after this lands, add a
  split command (for example `scripts/split_page.py`). The agent would choose
  which headings move, and the command would do steps 1–5 through `wikifm`.
- **Supersede**: unchanged fields and archive. The new page's sources follow the
  split rule, never a copy of the old page's list.
- **Archive**: unchanged, and snapshots are immutable. `_archive/**` is never a
  valid source and is exempt from all reference rules (1 of 242 snapshots does
  not parse today; leave it).
- **Naming vs `meta/contract.md`**: the wiki's prefixes (`crystallize-`,
  `research-`, `prd-`, dated suffixes) are the convention. The contract's
  "2–5 words, no prefixes" rule is removed (section 5.10).

### 5.9 Wikilinks

Format unchanged (CONTRIBUTING "do not change"). Additions: `briefings/` joins
the resolvable set, and briefs stay there permanently. The maintain skill's
7-day rotation into `_archive/briefings/` is removed: nothing reads a filed
brief, the rotation already broke one `index.md` link, and it would break a
digest that cites a brief (review F12). Lint scans `briefings/` as pages (link
targets, R9, escape checks), and pages with `lifecycle: dated-digest` are exempt
from lint's index-completeness check and its auto-fix, so filed briefs aren't
added to `index.md`. Without that exemption, the maintain loop's unattended
`--auto-fix` would add every brief (plan review P16). Dated digests are also
exempt from lint's 90-day staleness and 120-day `last_verified` warnings,
since a digest describes the wiki as of its date; otherwise each daily brief
would add a warning once it's 90 days old (decided at step 6). Also,
worker-link-validator runs `lint.py --json` instead of keeping its own
three-directory resolver (N9),
its `backlinks.py --all-orphans` call (a flag `backlinks.py` doesn't have) and
its four-key field list (N4). That lands in step 6, once `--json` writes nothing
(plan review P1). The post-write check runs on MCP writes too. A wikilink inside
a `[source: ...]` marker is invalid (R7), because the marker is an ID site, not a
link site.

### 5.10 Frontmatter profile, the single parser, and `meta/contract.md`

**Profile** (what a page's frontmatter may contain):

- `key: value` lines; keys `[a-z_][a-z0-9_]*`, unique (R5).
- Value: a plain or quoted scalar; a flow list `[a, "b"]` on one line; a block
  list of `  - item` lines directly under an empty `key:`, where more-indented
  lines continue the previous item, either as plain text folded with one space
  or after a `>-` marker, whose lines are kept as written and folded the same
  way, as YAML does (review F3; step 4 found that the 15 pages hold 40 `gaps:`
  items written with `>-`, the MCP's style for long text, and none use plain
  wrapping); or, for the persona keys only (`language_patterns`,
  `tone_by_channel`, `vocabulary_markers`), one level of `  subkey: value`,
  where a value is a scalar or a one-line flow list (the persona template has
  `signoff_patterns: []`).
- Comments and blank lines are allowed and ignored, as YAML does; the persona
  template and SCHEMA's field list use trailing comments. A comment ends a value,
  so the value can't continue on the next line. Tabs are allowed only inside
  quotes, comments and `>-` text, since PyYAML rejects them anywhere else.
- **Every scalar is a string.** Dates are validated by regex (`created`,
  `updated`, `last_verified`: `YYYY-MM-DD`, quoted or not), never type-coerced.
  This makes quoting irrelevant to every reader (N6).
- **The canonical written date form is single-quoted, `'YYYY-MM-DD'`** (review
  F2). It is what both js-yaml (the MCP) and PyYAML emit for a string date, so it
  survives either serializer unchanged. An unquoted date is turned into a
  timestamp by the MCP's round-trip and into a date object by PyYAML. Templates,
  `capture.py`, `wikifm.set_field`, R12's auto-fix and the migration all write
  this form. Existing single-quoted dates (176 values) need no change.
- Anything else is a profile violation (R12; 🟡 until the migration, then 🔴).
  R1 and R2 become two specific messages of this check. Shapes a YAML library
  writes that the profile doesn't list (list items at column 0, a value
  continued on the next line, `>-` on a key) are read the way YAML reads them,
  so no reader loses a value, and reported like the rest (step 4).
- Required keys: `title, created, updated, type, tags, sources` (as `lint.py`
  today). `coverage` is recommended and 🟡 on factual types (as today).
  CONTRIBUTING and worker-link-validator are corrected to match (N4). A missing
  frontmatter block or a missing required key stays 🔴, as today; only the other
  profile messages start at 🟡 (plan review P15).

**One parser, and one writer.** New `skills/llm-wiki-pm/scripts/wikifm.py`,
stdlib only:
- **Reading:** `parse(text) -> (fields, errors)` implementing the profile, and
  `parse_block()` for the text between the fences. Each error names its rule
  (R1, R2, R5, or R12 for the rest of the profile) and its line.
  `sources(fields)` and the accessors `str_field`, `list_field` and
  `date_field` return an empty value for a value of the wrong type, so a list
  where a string belongs can't crash a caller (review F8). `citations(body)` and
  `resolve(entry, wiki)` arrived with step 6, whose rules are their first
  callers. `resolve()` takes one `sources:` entry, since lint and post-validate
  already hold the parsed page. `slug()` moved into `wikifm.py` with them,
  because wikifm can't import lint, and `lint.slug` stays the same function.
- **Writing (review F4):** `set_field(text, key, value)` and
  `set_list(text, key, items)` change one frontmatter field in place and leave
  every other byte of the page untouched, the way the Edit tool does, and write
  dates in the canonical form. Ad-hoc scripts are the most frequent write path no
  hook sees (23 frontmatter-editing scripts in the saved transcripts). SKILL.md's
  Tool Selection rules require any script that edits frontmatter to use these,
  and `capture.py`, lint `--auto-fix` and `migrate_sources.py` use them too.
  Scripts that follow the rule are correct by construction; lint still catches
  ones that don't.
- **Callers:** `lint.py`, `pre-write.sh`, the new `post-validate` hook,
  **session-start's stale scan** (`session-start.sh:151-189`, review F2), and
  `capture.py` all import it. `backlinks.py` has no frontmatter parser, so it
  doesn't change (plan review P7).
  `parse_frontmatter`, `extract_sources`, `_split_flow_list`, `extract_tags`'s
  comma split, the copy in `pre-write.sh` and session-start's inline parser are
  deleted.
- **Tests:** PyYAML is not a runtime dependency. It is used in tests as an
  oracle: for every fixture, `wikifm.parse` must agree with
  `yaml.load(..., BaseLoader)` or report an error. The duplicate-key fixture is
  the documented case where it deliberately disagrees. Fixtures include wrapped
  list items and every date form found in the wiki. A further test runs `parse`
  over every page of a scratch copy of a real wiki and requires 0 exceptions
  (review F8). It reads the wiki's path from an environment variable (for
  example `WIKIFM_WIKI`) and skips when that's unset, since no wiki is in the
  repo. Step 4 ran it on a scratchpad copy on 2026-09-29: 701 `.md` files,
  archive snapshots and records included, with 0 exceptions, and every
  frontmatter block agreeing with PyYAML or reporting an error. The oracle
  tests skip without PyYAML (`pytest.importorskip`), and README's test recipe
  adds `pyyaml` (plan review P8).

**Contract reconciliation.** The MCP tells agents to read `meta/contract.md` for
frontmatter and naming. The default contract declares a different `type` enum, a
`status` field, no `sources`, a no-prefix naming rule, and a Note Template. The
template is advisory text an agent may copy; `vault.create` requires content and
never applies it (`mcp-tools.js:88-92`, review F10). The server creates the file
at startup if it is missing (`vault-auto-init.js`), never overwrites it, and says
to edit it. So:

- Ship `skills/llm-wiki-pm/templates/vault-contract.md`. Its Frontmatter Schema
  says "authoritative schema: `SCHEMA.md`; citation rules:
  `references/citation-spec.md`", lists the wiki's `type` enum, drops `status`,
  replaces the naming rule with SCHEMA's, and sets the Note Template to a valid
  wiki page skeleton with `sources:` (empty list, 🔴 until filled, which is
  correct).
- `session-start.sh` scaffold copies it to `$WIKI/meta/contract.md` when absent.
  The MCP server writes its default at startup, concurrently with the
  SessionStart hook, and which runs first is unverified. So on a new install the
  default may win (review F10).
- The scaffold treats a wiki directory that contains only `meta/` and
  `.markdown_vault_mcp/` as empty. Today an MCP that starts first makes a new
  wiki directory non-empty, and `session-start.sh:53-59` then skips the whole
  scaffold (no SCHEMA, index or log). Besides `meta/`, the MCP creates
  `.markdown_vault_mcp/`, its search index, on its first index flush (60 seconds
  after start) or at shutdown, so a wiki whose first session skipped the scaffold
  would hold both (plan review P24).
- Lint R11 🟡: `meta/contract.md` still carries the MCP default schema (detected
  by `generated_by: mcp-markdown-vault` plus a `status` enum line). It is the
  backstop for the startup race. The fix for the existing wiki is a one-time hand
  edit, which the file itself invites.
- Today this is latent: 0 pages use the contract's types or `status`.

### 5.11 Write-time enforcement (hooks, all exit 0)

1. **Matchers and the permission rule.**
   - **Deny the MCP `edit` tool (review F4).** Add a `permissions.deny` rule for
     `mcp__wiki-search__edit` and `mcp__plugin_llm-wiki-pm_wiki-search__edit` (the
     name when the plugin is installed) to `~/.claude/settings.json`. Every
     operation that re-serializes a page is in `edit`, agents have avoided it
     since 2026-08-11, and the Edit tool covers all its operations. A permission
     rule isn't a hook, so "hooks never deny" still holds. A plugin can't install
     permission rules, so the plugin README's install notes document it for other
     installs (review F13).
   - **Ask before MCP `vault` calls (plan review P5).** Add a `permissions.ask`
     rule for `mcp__wiki-search__vault` and
     `mcp__plugin_llm-wiki-pm_wiki-search__vault`, so every MCP write, including
     `vault.delete`, needs confirmation. Under `defaultMode: "auto"` an unlisted
     tool is decided by auto mode. Permission rules match on the tool name, so
     `vault` reads prompt too; agents rarely make them, since reads go through
     `view`. The README's install notes document this rule with the deny rule.
   - **Hook matchers.** PreToolUse matches
     `Write|Edit|MultiEdit|mcp__.*wiki-search__(vault|edit)`, which covers both
     tool-name forms (step 3). PostToolUse gets the same matcher in step 7, when
     post-validate replaces `post-write.sh`, which reads only `file_path` and
     would do nothing on an MCP call. The *registered* hooks are the user-level entries in
     `~/.claude/settings.json`, not `hooks/hooks.json`, so both must be updated
     (hooks.json for upstream parity).
   - **Filters (review F13).** The hooks read `tool_input.action` and act only on
     `vault` `create`, `create_from_template`, `update` and `delete`, exiting at
     once on reads. `create_from_template` also writes a new file (V1), so it is
     included (plan review P4). They skip any `edit` call with `dryRun: true`,
     which writes nothing.
   - **Live check (done 2026-09-29).** Claude Code documents hook matching on
     `mcp__<server>__<tool>` names, and step 3 checked it by hand in a session
     whose `.wiki-path` pointed at a scratch wiki (the hooks and the MCP resolve
     the same path, so nothing reached the private wiki). A `vault.update` on a
     scratch page prompted under the `ask` rule (twice: the agent read the page
     first), and the hook snapshotted the page before the write. The deny rule
     doesn't refuse an `edit` call: it removes the tool from the session, so the
     agent never sees it. `tests/test_write_hooks.py` covers MCP payloads with
     synthetic stdin JSON (plan review P3).
2. **Path extraction.** `tool_input.file_path` (Write/Edit/MultiEdit);
   `tool_input.path` (MCP single); `tool_input.operations[].path` (MCP batch).
   MCP paths are vault-relative and joined to `$WIKI`. The launcher and the hooks
   resolve `$WIKI` with the same chain, so they agree unless `.wiki-path` changes
   mid-session.
3. **Snapshot (pre).** On any existing page targeted by Write, Edit, MultiEdit,
   `vault.update`, `vault.delete`, or any `edit` op: copy to
   `_archive/<slug>-<date>.md`, where slug = `lint.py`'s `slug()`, which fixes the
   README collision (N14). One shared function makes the copy:
   `snapshot(page, wiki)` in `lint.py`, next to `slug()` (defined in
   `wikifm.py` since step 6). `pre-write.sh`, lint
   `--auto-fix` (item 8) and migration step M1 all call it, so backups are named
   one way everywhere (plan review P2). `briefings/` joins the gated set. The two
   root files the page rule skips get their own rule:
   - `overview.md` is snapshotted **only on a whole-file replacement**: `Write`,
     `vault.update` or `vault.delete`. Never on `Edit`, `MultiEdit` or an MCP
     `edit` op. The ISSUE-2 risk is the indexer (K2) replacing the page
     wholesale, and K2's instructions give it the `Write` tool for that. A
     regeneration done section by section through `Edit` would not be caught;
     that gap is accepted. The routine daily edits arrive as `Edit` and stay
     covered by git. Snapshotting every edit day
     would cost about 80 KB per active day for the two root files (the wiki had
     36 active days in two months, roughly 2.9 MB, more than the whole
     `_archive/` today) and would bury page snapshots under copies of the two
     most-edited files.
   - `index.md` is **never** snapshotted. It is derived: `lint --auto-fix` or K2
     can rebuild it from the pages, so a copy protects nothing that can't be
     regenerated.
   Both stay exempt from the freshness gate, as today.
4. **Raw guard (pre).** Any Write/Edit/MCP op on an *existing* `raw/` record →
   additionalContext: "records are write-once; save a new record and run an
   Update (§4)". New records pass silently.
5. **Freshness gate (pre).** Unchanged message, but it judges the *post-edit*
   text: Edit and MultiEdit apply `old_string → new_string` to the disk content
   first (fixes the brief-item-7 inversion). MCP `edit` ops are not simulated,
   so the gate is skipped for them. Post-validate covers them. `vault.create` and
   `vault.update` carry the whole post-image in `content`, so the gate judges them
   like Write; `create_from_template` is checked after the write, by
   post-validate (plan review P4). Pages with `lifecycle: dated-digest` are
   exempt wherever they live: digests summarize the wiki and have no sources by
   design (D6), and 5 of the 6 live ones are in `queries/`, not `briefings/`.
6. **Post-validate (new, synchronous PostToolUse, `hooks/post-validate.sh`).**
   Reads the written file(s) from disk and runs `wikifm` checks for I1–I3, the
   R7 grammar, escaped `\[`, and links. When a write takes a page over 200 lines,
   it adds the split-procedure pointer (section 5.8, review F9). It emits at most
   ~6 lines of additionalContext naming each violation and its fix. The existing async
   `post-write.sh` link check folds into it, and its `_status.md` append is kept.
   Budget: one python start plus one file parse plus a stat per declared source,
   well under 200 ms. It is synchronous because the agent must see the result in
   the same turn. Whether an *async* hook's context would reach the model is not
   something I verified, so the design doesn't rely on it. Its link check
   resolves against lint's page set, including `briefings/` (plan review P16).
   Post-validate is registered with item 1's matchers, as a synchronous
   PostToolUse entry in `~/.claude/settings.json` and `hooks/hooks.json`, in place
   of `post-write.sh`'s async entry. `post-write.sh` stays in the repo,
   unregistered, so `test_hooks.py`'s `TestPostWrite` (13 tests) keeps passing;
   removing it is proposed upstream together with those tests (plan review P23).
   It also runs item 5's freshness gate for `create_from_template` and MCP
   `edit`, whose result pre-write can't see. PostToolUse input carries no
   pre-image, so the split reminder is exact for Edit, MultiEdit and new files;
   a whole-file rewrite or MCP edit that leaves a page over 200 lines gets the
   reminder as well (decided at step 7). The `_status.md` append covers every
   problem it reports, but not the reminders.
7. **Session-start** (already runs lint): add the counts of I1–I3 violations to
   the additionalContext line and `_status.md`. Stop writing a report in
   `--json` mode (N1). If lint exits nonzero or its JSON doesn't parse, report
   "lint failed: health unknown" instead of zero counts. Today
   `session-start.sh:136` discards stderr and leaves the counts at 0, so a crash
   reads as a clean wiki (review F8). With that, every write path, including Bash,
   Obsidian and git, is detected within one session boundary. Step 6 put the
   I1–I3 counts in a sentence of their own, outside the health total: until a
   wiki is migrated they are a known backlog, as in D7. A missing `lint.py` also
   reads as health unknown.
8. **lint `--auto-fix`** imports the snapshot function and snapshots each page
   before writing it. The new content repairs (R7 marker fixes, R12 date
   normalization) run only under a separate `--auto-fix=content` flag. The
   maintain loop runs plain `--auto-fix` unattended because it is
   "non-destructive" (`llm-wiki-maintain/SKILL.md:74-75`). Plain `--auto-fix`
   keeps that meaning: index backfill and sort, de-escaping, supersession link
   redirects. Content repairs stay behind the migration's dry run and sign-off
   (review F5). `--auto-fix=content` runs the plain fixes plus the content
   repairs, and every auto-fix frontmatter write goes through `wikifm`.
   lint-guide.md documents both forms and says unattended runs never pass
   `=content` (plan review P20).
9. **Frontmatter edits (Tool Selection rule).** One line in SKILL.md's Tool
   Selection rules: edit frontmatter with the Edit tool, or, in a script, with
   `wikifm.set_field`/`set_list`. Never use a YAML library's load-and-dump. The
   MCP `edit` tool is denied by item 1. For installs without that rule, the rule
   names the damaging operations: `frontmatter_set` and the AST operations
   (`append`, `prepend`, `replace`, `delete`). `string_replace`, `line_replace`
   and `vault.update` don't re-serialize the page.

Honest summary:
- **Prevented by construction:**
  - comma-shredding and quoting dependence (ID grammar);
  - ID typos from capture (`capture.py` prints the ID);
  - README snapshot collisions;
  - MCP page re-serialization (permission rule, where installed);
  - date damage (canonical `'YYYY-MM-DD'`);
  - frontmatter damage from scripts that use `wikifm.set_field`.
- **Detected in the same turn:** I1–I3 and escapes for Write/Edit and MCP `vault`
  writes.
- **Detected by next session:** everything, for all writers, and a lint failure
  is reported rather than read as "clean".
- **Not detected:**
  - edits to a record through Bash, Obsidian or git (git history only);
  - a same-day second overwrite's pre-image (git only).

Permission note: `mcp__wiki-search__edit` is denied (item 1). Leave `vault` off
the allowlist. Permissions match on tool name, so allowing `vault` would also
allow `vault.delete`. `defaultMode: "auto"` does not guarantee a prompt for an
unlisted tool, so an explicit `permissions.ask` entry for both name forms of
`vault` confirms every MCP write (review F4; added in item 1, plan review P5).
Revisit the deny rule only if NW2 fixes the round-trip.

### 5.12 Revisit obligation (I8)

Lint R10 🔵: pages whose primary sources all resolve to records with `source_type:
conversation` or `reconstructed: true`. They are listed in `_status.md` under
"Secondhand, unverified". A page leaves the list only when a non-conversation
primary record is declared on it, meaning someone captured a real source.
Lint's JSON carries the list, and session-start writes it to `_status.md`. Lint
reads a record's frontmatter only for `source_type` and `reconstructed`, since
records aren't pages (11 have no frontmatter), and never reports R12 on a record
(plan review P21).

No date clears it (review F1). An earlier version cleared the flag on a
`last_verified` date less than 30 days old. Nothing in the skills or hooks sets
that field on verification. It moves with ordinary edits: 206 of 210 diffs that
change it also change `updated`, and 84 of 112 pages carry the same value in
both. So it can't show that anyone verified anything. About 4 pages will be
listed after the migration. The existing 120-day `last_verified` warning has the
same flaw and is left for NW1's review of freshness signals.

The same mechanism is offered to ISSUE-1 (action-item status) but not built
here.

### 5.13 `wiki-search.sh` fix and smoke test

```sh
FILE_WIKI=$(cat "$(pwd)/.wiki-path" 2>/dev/null | tr -d '[:space:]' || true)
```

This is how the other four hooks read the file: silent when it is missing, and
falling back to the next option when it can't be read. The bug is that a failed
`<` redirection is reported by the shell before `2>/dev/null` applies. Reproduced:
running the launcher in an empty directory prints `…/.wiki-path: No such file or
directory`.

Smoke test (`tests/test_wiki_search.py`, closes A11): run
`sh hooks/wiki-search.sh` with `HOME` set to a temp dir containing a fake npx
cache path (`.npm/_npx/x/node_modules/@wirux/mcp-markdown-vault/dist/index.js`),
and `PATH` set to a stub `node` that prints `$VAULT_PATH` and exits. Assert
(1) empty stderr from a directory without `.wiki-path`; (2) precedence
`.wiki-path` > `CLAUDE_PLUGIN_OPTION_wiki_path` > `WIKI_PATH` > cwd; (3) exit 127
with a message when no node is found. No network and no real MCP needed.

### 5.14 Test location and worker copies

- **Tests.** New lint and parser tests go in `tests/test_lint.py` (plus a new
  `tests/test_wikifm.py`). The 5-test `TestLint` class stays in
  `tests/test_hooks.py` untouched. Moving it would edit an upstream-owned file for
  no behavioral gain and create a merge conflict on the next upstream release.
  Add a one-line comment in `test_lint.py` pointing to it, and propose the move
  upstream together with the parser PR. New hook tests (MCP matchers, post-image,
  README snapshot) go in a new `tests/test_write_hooks.py`, not appended to
  `test_hooks.py`, for the same reason. Also correct the commit-message claim in
  the changelog, not in git history: a note in the
  [llm-wiki-pm Fork Changelog](llm-wiki-pm-fork-changelog.md) saying `91878dc`'s
  message wrongly calls `test_lint.py` the first lint test module. Step 4 adds
  both the pointer comment and the note (plan review P28).
- **Worker copies.** Replace per-project copies with user-level symlinks, the
  same way skills are installed: `~/.claude/agents/worker-*.md →
  ~/Projects/llm-wiki-pm/.claude/agents/`. Then delete `pm-wiki/.claude/agents/`
  (identical today, verified with `diff -r`). One source, visible in every
  project. The fork's own project copy is the same file. Separately, the workers
  reference `${CLAUDE_SKILL_DIR}`, which is a *skill* variable. Whether it is set
  in a subagent is unverified; step 9 checks it. Step 9 changes the wiki repo
  (deleting its copy) and user-level config (`~/.claude/agents/` doesn't exist
  yet, and its symlinks affect every session), so both need the user's
  confirmation first (plan review P25).

---

### 5.15 Lint rule catalog

Every R-numbered rule this document mentions, in one place. R1–R5 exist today
(commit `91878dc`); R6–R13 are proposed, and R8 and R13 were dropped by the
review. "Now" is the tier after plan step 6; "3.0" is the tier after plan step
11. 🔴 error, 🟡 warning, 🔵 info. Content auto-fixes run only under
`--auto-fix=content` (section 5.11, item 8).

| Rule | Checks for | Invariant | Status | Now | 3.0 | Auto-fix |
|---|---|---|---|---|---|---|
| R1 | A list item on the same line as its key (`tags: - x`) | I1 | Exists; becomes a message of R12 | 🔴 | 🔴 | No |
| R2 | Block list items under an already-closed `[...]` list | I1 | Exists; becomes a message of R12 | 🔴 | 🔴 | No. The merge suggested in the lint-checks design was never built, and R2 has no violations today (plan review P22) |
| R3 | An inline citation ID that equals the `slug()` of no `sources:` entry on the same page | I3 | Exists (🔵, loose substring match); **rewritten** as an exact match | 🟡 | 🔴 | No; the message names the path to declare, and a human adds it (M5 for the migration; plan review P22) |
| R4 | A page with 5+ sources citing fewer than half of them inline | none (heuristic) | Exists, kept; also the backstop for splits (the `split_from` escalation was dropped, review F9). Counts a source as cited by exact `slug()` match once R3 is rewritten (plan review P18) | 🟡 | 🟡 | No |
| R5 | The same frontmatter key twice | I1 | Exists, kept | 🔴 | 🔴 | No |
| R6 | A `sources:` entry that isn't a canonical path to an existing file | I2 | New | 🟡 | 🔴 | No |
| R7 | An inline citation that breaks the grammar (section 5.4): wrapped, nested `source:`, "X vs. Y", raw path form, URL, wikilink, or text that isn't an ID (prose, a root file, a script path), or a marker that isn't closed (step 6) | I3 | New | 🟡 | 🟡 | Mechanical classes (path form, wraps, nested prefix, "vs."), under `--auto-fix=content` only, and only when every ID in the marker names exactly one file (step 6) |
| R8 | **Dropped (review F7).** Was: a `## Sources` legend whose IDs differ from the declared IDs | — | — | — | — | — |
| R9 | Two records with the same ID, a record ID equal to a page slug, or two pages with the same slug (review F11) | I5, I6 | New | 🔴 | 🔴 | No |
| R10 | A page whose primary sources are all conversation or reconstructed records. Cleared only by declaring a non-conversation primary record; no date involved (review F1) | I8 | New | 🔵 | 🔵 | No |
| R11 | `meta/contract.md` is still the MCP's default contract | none (competing spec) | New | 🟡 | 🟡 | No |
| R12 | Frontmatter outside the profile (section 5.10), or a required key missing | I1 | New (replaces the key-presence check). 13 pages (the timestamp dates) violate it until migration M4, so it starts at 🟡 (review F3); the 15 pages with wrapped list items (`>-` items) pass, because the profile now allows them. R1, R2 and R5 keep their own 🔴, and so do missing frontmatter and a missing required key, which are 🔴 today (plan review P15) | 🟡 | 🔴 | Only for timestamp dates at exactly midnight (N15), under `--auto-fix=content`: rewrites them as `'YYYY-MM-DD'`, which is lossless |
| R13 | **Dropped (review F6).** Was: a record without `source_type` or `captured`, dated after the rule ships | — | — | — | — | — |

Other checks keep their current tiers and have no R-number: escaped `\[`
(PATCH-3d/3e), broken wikilinks, orphans, index drift, self-referential
sourcing, missing inline provenance, `coverage:`, stale `last_verified` (which
shares R10's old flaw, section 5.12). Lint's "> 200 lines — split candidate"
warning also gains the split-procedure pointer (section 5.8). Dated digests are
exempt from both staleness warnings (section 5.9).

## 6. Dispositions

### Fork commits

| Commit | Disposition | Reason |
|---|---|---|
| `91878dc` R1–R5 | **Revise.** R1/R2/R5 kept as messages of the profile parser: from step 4 `wikifm.parse` reports their conditions and lint keeps their messages and 🔴 tier, and step 6 folds them into R12's report (plan review P7). R3 **replaced** by exact ID resolution (🟡 in 2.22, 🔴 in 3.0). R4 kept as a ratio on every page (the `split_from` escalation was dropped, review F9). Tests kept and extended. | R3's permissive matcher and conversational exemption exist only because IDs were undefined. |
| `ae33f9d` §4 conversational citation | **Revise.** Keep "never coin an ID for an uncaptured artifact". Replace the `[source: user, conversation, DATE]` alternative with "capture a record". Move the detail to citation-spec. SKILL.md ③ drops from 402 to ~150 bytes of added text. | It legitimized one of the 12 shapes. |
| `543766c` quote-aware split | **Replace** when `wikifm` lands; keep until then (it is correct in the interim). Its shredding tests become R6 migration tests: step 4 rewrites its three tests against `wikifm.sources()` with the same expectations, and step 6 adds the R6 assertions (plan review P7). | Unnecessary once no valid entry contains a comma. |
| `11fa847` template refs | **Keep.** | Plumbing; unrelated to the rules. |

### [llm-wiki-pm Fork Changelog](llm-wiki-pm-fork-changelog.md)

| Item | Disposition |
|---|---|
| PATCH-1 auto-commit disabled | **Keep, fork-only** (environment-specific). |
| PATCH-2 backlinks README self-slug | **Keep; offer upstream.** |
| PATCH-3a block-list parsing | **Replace** with `wikifm` lists-as-lists. Joining into `"[a, b]"` reintroduces comma ambiguity for `extract_tags` and makes the two parsers disagree. |
| PATCH-3b `slug()` README | **Keep; offer upstream.** It is now also the snapshot naming function. |
| PATCH-3c overview/index link targets | **Keep; offer upstream.** Extend the same registration to `briefings/`: in step 6, `briefings/` joins lint's page set, with dated digests exempt from the index check (section 5.9, plan review P16). |
| PATCH-3d/3e escaped-bracket check | **Keep** until wirux/mcp-markdown-vault#47 is fixed. Checked 2026-09-26: #47 is open with no maintainer response, and the repo has had no activity since 2026-06-02. A comment now links it to #49, the date bug from the same code path. Post-validate now reports escaped brackets at write time. The permission rule on the MCP `edit` tool (section 5.11, item 1) removes the cause on this install. NW2 is deferred (review F4). |
| PATCH-4 relationship-map wiring | **Keep.** Its end-to-end verification is still pending and unrelated to this design. |
| ISSUE-1 action-item update mechanism | **Keep open, re-scoped.** Shares RC6. I8's horizon mechanism is the reusable piece; action-item status is out of scope here. |
| ISSUE-2 indexer overview regeneration | **Keep open, mitigated.** Snapshotting `overview.md` on whole-file replacements (section 5.11, item 3) makes a regeneration recoverable without a daily copy. The destructive behavior itself is untouched. |
| ISSUE-3 conversational citations / legend drift | **Close when steps 5–7 and M1–M5, M7–M8 land.** Part A → I2 + conversation records + reconstructed records. Part B → legends become optional free prose, not a declaration site, so there is nothing to drift from (review F7). Its open question "lint or pre-write hook?" is answered: both, with lint authoritative and a non-blocking post-write hook for same-turn feedback. Its proposed rule ("exempt `conversation, <date>` only if the dated file exists") is superseded: conversational citations stop being a special case. |

The step that settles each entry updates its status line in the fork changelog:
ISSUE-2 in step 3, PATCH-3a in step 4, and ISSUE-3 after step 10b (plan review
P28).

### PLUGIN-REVIEW items touched

| Item | Disposition |
|---|---|
| A4 snapshot hook | **Reopen/extend**: MCP matchers, README collision, `overview.md` snapshot on whole-file replacement only (`index.md` never), lint `--auto-fix` snapshots. |
| A11 wiki-search.sh path + smoke test | **Reopen**: the shipped fix introduced the stderr bug, and the smoke test was never added (section 5.13). |
| A13 micro-capture | **Revise**: +1 write per capture, stated and justified (section 4). |
| A14 tests | **Extend**: parser, hooks-on-MCP, post-image, launcher smoke. |
| A6 privacy drift | **Residue found**: worker-source-fetcher (N5), README, CONTRIBUTING (brief item 20). Close with doc fixes. |
| A7 fake gate | **Residue found**: `llm-wiki-prd` (N8). One-line fix. |
| A3 guard anchors | **Untouched.** Names and wording kept verbatim; this design gives the source-depth guard a concrete rule (section 5.7, "live read without capture"). |
| Open decision 4 (`raw/inbox/`) | **Decline for now; leave open.** D covers citable capture without a layout change. An inbox is only worth it if you want deferred filing (capture now, integrate later), which is a different need. |

---

## 7. Legacy migration (production wiki, measured 2026-09-25)

Current state against the new rules:

| Class | Count | Conversion |
|---|---|---|
| Frontmatter parse failures (live) | 0 of 245 (1 of 242 archive, leave) | none |
| Duplicate keys | 0 | none |
| `sources:` entries | 786 on 245 pages: 695 existing raw paths, 10 page paths, **81 invalid in 12 shapes** | below |
| · `user, conversation, DATE` | 30 | → reconstructed record path (M2) |
| · `conversation, DATE` | 26 | → same |
| · shredded `conversation` + bare date | 5 pages (10 items; 4 unquoted flow, 1 frozen block) | → same, one entry |
| · `user, conversation (context), DATE` | 2 | → same; the context goes into the record title |
| · structural-file references (SCHEMA org chart ×3; log/index/overview/SCHEMA on 2 brief pages ×8) | 11 | org-chart facts → one dated user-statement record capturing them, cited by the 3 pages (SCHEMA itself unchanged); briefs → `sources: []` + `lifecycle: dated-digest` (see D6) |
| · free text / absolute path outside the wiki | 2 | → capture a record of what was read, or remove; `gaps:` note |
| Inline markers | 1,070 on 209 pages: 841 bare raw IDs, 9 raw paths, 5 page IDs, 1 wikilink, **217 conversational**, **35 other defects** | below |
| · conversational | 217 | → reconstructed record ID (M2) |
| · raw path form | 9 | → ID (auto-fix) |
| · hard-wrapped, nested `source:` prefix | 9 + 8 | auto-fix; join or strip, then re-resolve |
| · "X vs. Y" | 5 | → `"; "` (auto-fix) |
| · structural file / script path / prose / wikilink | 6 + 2 + 4 + 1 | manual (13) |
| · multi-line markers (any) | 55 | auto-join |
| Raw-ID markers not declared on their page (I3) | 31 markers on 16 pages | auto-fix *proposes* adding the declaration; human confirms |
| Declared raw sources never cited (R4 territory) | 211 of 694 on 84 pages | none required; R4 flags 12 pages today |
| `## Sources` legends | 49 pages, 166 bullets: 136 prose, 19 conversational, 7 wikilinks, 4 raw paths | none; legends stay prose (review F7) |
| Raw records without frontmatter / with `private:` | 11 / 14 | leave records untouched (write-once); no rule (R13 dropped, review F6) |
| Raw record/asset stem pairs | 2 | allowed (asset exclusion) |
| Timestamp-format dates (N15) | 17 values on 13 pages | normalize to `'YYYY-MM-DD'` in M4 (lossless: every time part is `T00:00:00.000Z`) |
| Single-quoted dates | 176 values (114 `updated`, 62 `last_verified`) | none: already the canonical form (review F2) |
| Wrapped `gaps:` list items (`>-`) | 15 pages | none: the profile accepts them (review F3) |
| Source declared as a non-markdown file | 1 `.html` under `raw/attachments/`, on 1 page | M5: save a markdown record of it in a routed folder, move the original to `raw/assets/`, re-declare (review F15) |
| Files in unrouted `raw/` folders | `raw/attachments/` 1 (the `.html` above), `raw/clippings/` 1 (cited by no page) | M4/M5: empty both folders into routed folders; the clippings file goes to `raw/articles/` (review F15) |
| Briefs rotated into `_archive/briefings/` | 2 (one still linked from `index.md`) | M4: move back to `briefings/` (review F12) |
| `_archive/README-<date>.md` collision | 1 file | rename by hand to the right slug if its origin can be identified from git, else leave |
| `meta/contract.md` default | 1 | hand-edit (M7) |

Migration steps (a script, `skills/llm-wiki-pm/scripts/migrate_sources.py`,
dry-run by default, emitting a per-page before/after count table, per the LINT
doc's lesson that counts must be visible). The script is written and tested in
the fork first (step 10a), then run on the wiki (step 10b; plan review P26):

- **M1** Snapshot every page to be touched (bulk; 10+ pages needs sign-off per
  AGENTS.md), with the shared `snapshot()` function (section 5.11, item 3; plan
  review P2).
- **M2** For each of the **18 distinct conversation dates** (all 18 have a
  `log.md` entry that day), write `raw/internal/conversation-YYYY-MM-DD-reconstructed.md`
  with `source_type: conversation`, `reconstructed: true`,
  `reconstructed_on: '<migration date>'`, a body quoting that day's log entries,
  and the list of pages and claims that cite it. Read `log.md` **and** any
  rotated `log-*.md`: `log.md` was at 480 of its 500-entry rotation threshold on
  2026-09-28 (review F14).
- **M3** Rewrite the 58 conversational `sources:` entries and 5 shredded pairs to
  the M2 paths, and the 217 conversational markers to the M2 IDs, keeping any
  parenthetical context as the marker location.
- **M4** Auto-fix the mechanical marker classes (path form, wraps, nested
  prefix, "vs.", multi-line), and normalize timestamp-format dates to
  `'YYYY-MM-DD'` (N15), all through `wikifm.set_field` and `lint.py
  --auto-fix=content`. Move the 2 rotated briefs back to `briefings/`, and the
  `raw/clippings/` file to `raw/articles/`.
- **M5** Human pass on the 13 manual markers, the 11 structural-file entries,
  the 2 free-text entries, the 31 undeclared citations, the `.html` source
  (save a markdown record, move the original to `raw/assets/`, re-declare), and
  the `_archive/README-<date>.md` rename from the table above (plan review P26).
- **M6** *Dropped (review F7).* Legends are no longer converted.
- **M7** Replace `meta/contract.md` content with the reconciled template, and
  add the split-procedure pointer to the wiki's own SCHEMA.md split rule (a
  scaffolded copy doesn't pick up template changes; review F9).
- **M8** Re-run lint; the expected result is 0 R3/R6/R7/R12 findings, with R10
  listing every page resting only on reconstructed records (about 4). R12 can
  then move to 🔴.

**What cannot be recovered.** The content of the 18 dated conversations was
never captured. `log.md` records what the agent *did* that day, not what the
user *said*. So a reconstructed record gives the claim a resolvable ID and an
honest label, not evidence. Those claims keep their current confidence at best.
R10 lists them until each is re-sourced with a non-conversation primary record
(section 5.12). The phantom-slug class (finding 3) was already repaired in
`5cc416c`, but its 10 archive snapshots still contain the phantom ID. Archives
are immutable and exempt, so they stay as they are.

---

## 8. Implementation plan

Ordered by dependency. "Up" = candidate to offer upstream as a PR; "Fork" =
fork-only. Semver is per CONTRIBUTING's table, and is the bump each step implies
when it's offered upstream (D10). The fork doesn't bump versions (plan review
P29).

| Step | Change | Depends on | Semver | Up/Fork |
|---|---|---|---|---|
| 0 | Scrub real names from the current files and from git history, then update cited commit IDs (N12, D8; detail below the table) | — | — | Fork (public repo hygiene) |
| 1 | `wiki-search.sh` `.wiki-path` read fix + `tests/test_wiki_search.py` | — | patch | **Up** |
| 2 | Doc drift: README/CONTRIBUTING/GETTING_STARTED `private:`, CONTRIBUTING required-field list, worker-source-fetcher `private:` and routing table, `llm-wiki-prd` "(enforced)". `llm-wiki-maintain`: remove step ⑤ "Brief rotation" and the `_archive/briefings/` convention line (review F12), and reword step ⑥'s "non-destructive" note to name what plain `--auto-fix` does (review F5). The worker-link-validator item moved to step 6, since the validator needs lint's side-effect-free `--json` (plan review P1) | — | patch | **Up** |
| 3 | Hooks: MCP matchers for both tool-name forms (PreToolUse only; the PostToolUse matcher lands with step 7), with the `action`/`dryRun` filters, `create_from_template` included (plan review P4); `slug()`-named snapshots, made by one shared `snapshot()` function in `lint.py` that lint's auto-fix and M1 reuse (plan review P2); `overview.md` snapshot on whole-file replacement; `briefings/` gated; skip `assets/` subfolders of directory pages; Edit post-image, and `vault.create`/`update` judged from `content`; raw write-once warning; update `~/.claude/settings.json`, `hooks.json` and `hooks/README.md` (plan review P27); `tests/test_write_hooks.py` with synthetic MCP payloads, plus a manual live check, in a session pointed at a scratch wiki, that a PreToolUse hook fires on an MCP call (plan review P3). Permission rules: deny both name forms of the MCP `edit` tool and ask before both name forms of `vault` in `~/.claude/settings.json` (fork install), and document both in the README's install notes (review F4, F13; plan review P5). Mark ISSUE-2 mitigated in the fork changelog (plan review P28) | — | patch (bug fixes) + minor (MCP coverage) | **Up** (the README note; the settings entry is per-user) |
| 4 | `wikifm.py` profile parser, including wrapped list items (review F3), and its text-preserving `set_field`/`set_list` writers with the canonical `'YYYY-MM-DD'` date form (review F2, F4); lint, pre-write **and session-start's stale scan** switch to it (review F2), with the date-quote fix as the one intended behavior change and lint's and session-start's counts recorded before and after (plan review P6); delete the old parsers (replaces PATCH-3a, 543766c), rewriting `543766c`'s three tests against `wikifm.sources()` (plan review P7); PyYAML-oracle tests, skipped without PyYAML, with `pyyaml` added to README's test recipe, plus an opt-in whole-wiki no-exception test (review F8, plan review P8); the pointer comment in `test_lint.py`, a fork-changelog note correcting `91878dc`'s message, and PATCH-3a marked replaced (plan review P28) | — | patch | **Up** |
| 5 | `references/citation-spec.md` (the single spec); pointers from AGENTS.md (Source Attribution; "No raw/ mutations"; "Snapshot before destructive ops" relabeled as the rule for paths the hook can't see), the SCHEMA template (Inline Provenance; Grounding, whose primary sources become records; a block-style `sources:` example), ingest-guide ① "Current conversation" and ⑤, update-guide (the `ae33f9d` block and the `(per [[raw/…]])` example), crystallize-guide, and `prd-templates.md:91` (plan review P9, P11); llm-wiki-crm §2 company enrichment and llm-wiki-research's stub enrichment capture each source through `worker-source-fetcher` and cite its ID (plan review P10); `output-formats.md` artifact rule (markdown artifacts under `assets/`, section 5.2) and its `[[raw/…]]` sources appendix; `skills/llm-wiki-pm/scripts/capture.py`, which picks the next free suffix, with `tests/test_capture.py` (plan review P12); `lint.py --cited-sources` (section 5.8; plan review P13, P19); SKILL.md §2/§4 edits, the References and Scripts lists, the §4 snapshot sentence, and the Tool Selection line: frontmatter through the Edit tool or `wikifm.set_field`, never a YAML load-and-dump (section 5.11, item 9); split-procedure pointers in the SCHEMA.md template's split rule and `ingest-guide.md` ⑫ (review F9); templates write dates as `'YYYY-MM-DD'`; revise `ae33f9d` | 4 | minor | **Up as an issue first**: it is opinionated and changes the micro-capture contract |
| 6 | `wikifm.citations()` and `resolve()`, moved from step 4; `--cited-sources` (step 5) switches to `citations()` from lint's old marker parser. Lint: R6, R3 exact (with R4 counting by exact `slug()` match, plan review P18), R7 grammar, R9 record and page-slug uniqueness, R10 (date-free), R11 contract, R12 profile (with the midnight-timestamp auto-fix); tiers per the section 5.15 table (🟡/🔵 initially; only R9, with no existing violations, starts at 🔴; R12 starts at 🟡 because 13 pages violate it until M4, review F3, but missing frontmatter and missing required keys stay 🔴, plan review P15); grounding on resolved entries and the dated-digest exemption (section 5.3, D6; plan review P17); `briefings/` in lint's page set, with dated digests exempt from the index check (plan review P16); the split-procedure pointer in the "> 200 lines" warning; skip `assets/` subfolders of directory pages; content auto-fixes (mechanical markers, dates) behind `--auto-fix=content`, which also runs the plain fixes (review F5, plan review P20); auto-fix snapshots and writes through `wikifm`; `--json` stops writing a report and carries R10's page list and the index-gap and missing-field lists; session-start surfaces I1–I3 counts, writes R10's list to `_status.md`, and reports a lint failure instead of zero counts (review F8, plan review P21); worker-link-validator runs `lint.py --json` instead of its own resolver, orphan call and field list (moved from step 2, plan review P1); lint-guide.md documents the new rules, flags and split pointer (plan review P27) | 4, 5 | minor | **Up** |
| 7 | `post-validate.sh` synchronous PostToolUse (folds in post-write link check, resolving against lint's page set; split-procedure reminder when a page crosses 200 lines, review F9); registered with step 3's matchers in `~/.claude/settings.json` and `hooks.json` in place of `post-write.sh`, which stays in the repo unregistered so `TestPostWrite` keeps passing (plan review P23); tests in `tests/test_write_hooks.py`; `hooks/README.md` (plan review P27) | 3, 4, 6 | minor | **Up** |
| 8 | Vault contract template + scaffold copy; the scaffold treats a directory holding only `meta/` and `.markdown_vault_mcp/` as empty (review F10, plan review P24) | 5 | minor | **Up** |
| 9 | Worker agents → user-level symlinks in `~/.claude/agents/`; delete the wiki repo's copy; verify `CLAUDE_SKILL_DIR` in subagents. It changes the wiki repo and user-level config, so confirm both with the user first (plan review P25) | — | — | Fork (install layout) |
| 10a | `skills/llm-wiki-pm/scripts/migrate_sources.py`, dry-run by default, with fixture tests for every class in section 7's table, F14's rotated logs and F15's cases (plan review P26) | 4, 5, 6 | — | Fork until step 11, then **Up** with it |
| 10b | Wiki migration M1–M8 (dry-run, review, apply, commit in the wiki repo); mark ISSUE-3 closed in the fork changelog (plan review P28) | 8, 10a | — | Fork (wiki content) |
| 11 | Promote R3/R6 to 🔴, and R12 to 🔴 once M8 shows 0 violations | 10b | **major (3.0.0)**: it narrows the valid value space of `sources:`, a frontmatter-schema change that makes existing wikis report errors | **Up**, with the migration script |
| 12 | **Dropped (D11, review F2, F4).** Was: a pinned, patched local copy of the MCP using `CORE_SCHEMA`. The permission rule removes the damaging operations, and `CORE_SCHEMA` would write dates unquoted, which PyYAML reads as date objects (N6) | — | — | — |

**Step 0 in detail.** Do it before any implementation commit and before pushing
the unpushed local commits, so there is a single force-push.

1. **Scrub the current files.** Replace the names of people and customer
   companies in `tests/test_lint.py` and
   `fork-chgs/lint-frontmatter-checks-design.md` with placeholders (`person-a`,
   `customer-a`, …), using one replacement list, and commit. The list is kept
   outside the repo, since it contains the real names. Product and page-topic
   names stay.
2. **Rewrite history.** Run `git filter-repo --replace-text <list>` with the same
   list, so the identifiers disappear from every past version. The rewrite changes
   every commit from `4e61e6c` (2026-09-24, the first to add one) onward.
   filter-repo updates commit IDs mentioned in commit messages itself, and writes
   an old-to-new map to `.git/filter-repo/commit-map`.
3. **Verify.** Search the whole rewritten history for each identifier
   (`git log -p --all -S<string>` must find nothing), and run the test suite.
4. **Update cited commit IDs.** IDs written inside files aren't rewritten. Use the
   commit map to replace every rewritten fork ID cited in `fork-chgs/`: in this
   document these are `11fa847`, `91878dc`, `ae33f9d` and `543766c`, and the
   review cites `3cb4322`. Upstream IDs (`dfa3b93`, `56413ab`, `67c4adb`) and wiki
   repo IDs (`c910309`, `c4de70c`, `5cc416c` and others) don't change. Commit the
   update.
5. **Publish.** Force-push `main`. Re-clone any other local copies, because
   old clones still hold the identifiers. GitHub keeps orphaned commits reachable
   by ID for a while; ask GitHub support to purge them if that matters.

### Frontmatter changes and semver

No new *required* frontmatter field and no directory-layout change, so nothing
before step 11 is major. The design adds these fields, none of them required by
the schema. (`split_from` was dropped by review F9, and nothing checks
`source_type` or `captured` since R13 was dropped by review F6.)

| Field | Goes on | Purpose | Status | Defined in |
|---|---|---|---|---|
| `source_type` | raw records | kind of source (web, transcript, conversation, …) | optional; written by `capture.py` and M2; R10 reads `conversation` | section 5.1 |
| `captured` | raw records | date the source was saved | optional (recommended template) | section 5.1 |
| `stated_by` | raw records (conversations) | who said it: `user` or a person's page slug | optional | section 5.1 |
| `asset` | raw records | path to the original PDF or slides in `raw/assets/` | optional | section 5.1 |
| `reconstructed` | raw records (migration only) | marks the 18 rebuilt conversation records | set by the migration | section 7, step M2 |
| `reconstructed_on` | raw records (migration only) | date they were rebuilt | set by the migration | section 7, step M2 |

### SKILL.md size and upstream conflict surface

**Net SKILL.md size change (estimate):** §2 fast path +~120 bytes; §4 ③
−~250 bytes (402 → ~150); §4 snapshot sentence +~40; References list +~80;
Tool Selection line on frontmatter edits +~150.
**Net ≈ +140 bytes, i.e. about +0.6%** (24,625 → ~24,765). The new rules cost the
always-on budget nothing. They live in `citation-spec.md` (est. ~6–7 KB, read on
demand, like `ingest-guide.md`) and in lint and hooks.
Measured at step 5 (2026-09-30): +423 bytes, +1.7% (24,625 → 25,048). The
estimated parts came out close: fast path +108, §4 ③ −221, snapshot sentence +52,
References +100, Tool Selection +173. The difference is the Scripts list, which
the estimate left out: +211 for the `capture.py` line and `--cited-sources`.
`citation-spec.md` is 11.4 KB.

**Upstream conflict surface.** Heavily edited upstream files touched: `SKILL.md`
(~6 lines), `lint.py` (large: parser swap plus rules), `pre-write.sh` (large),
`hooks.json` (2 matchers), `ingest-guide.md`/`update-guide.md` (a few lines each).
To keep merges tractable: land step 4 first as a refactor whose one intended
behavior change is the date-quote fix (F2), with all existing tests green, so
later rule diffs are additive. That fix makes lint's 90-day check read about 115
more pages and raises session-start's stale count, so record both before and
after (plan review P6). Measured at step 4 on a copy of the wiki (2026-09-29):
lint's 90-day check read `updated` on 244 of 245 pages instead of 131, with its
report unchanged (0 🔴, 37 🟡, 44 🔵), and session-start's stale count rose from
49 to 66. Put new rules in `wikifm.py` and new lint functions
rather than inline in `main()`; put new tests in new files.

**Lint counts at step 6.** Measured on a copy of the wiki (2026-09-30; 246
pages, including the one brief now in lint's page set, and 153 records). The
report went from 0 🔴, 37 🟡, 44 🔵 to 0 🔴, 253 🟡, 13 🔵:

- R3 moved from 🔵 on 31 pages (loose match) to 🟡 on 101 pages (271
  citations); 39 of those citations name a file that exists but isn't
  declared, spread over 19 pages.
- R4 fired on 14 pages instead of 12 (plan review P18).
- R6 flagged 56 pages (82 entries), R7 43 pages (87 markers), R12 13 pages
  (the 17 timestamp dates) and R11 the default contract. R9 and R10 found
  nothing.
- Grounding by what an entry names changed no page's verdict.

`--auto-fix=content` on a second copy rewrote 56 markers and all 17 dates on
41 pages, leaving R7 on 19 pages, mostly wrapped markers holding a
`user, conversation` citation that wait for M3. It left R3 at 101. The counts
differ from section 7's 2026-09-25 measurements because the wiki has grown
(72 wrapped markers against 55).

---

## 9. Decisions

All decided 2026-09-28. Each shows the question, the decision, and the reason.
D4, D8, D9, D10 and D11 differ from this document's original recommendations; the
design review caused D4, D9 and D11 (review F7, F4, F2).

**D1. Adopt source IDs + write-once capture records (option D) over the daily
conversation file (A)?** **Decided: yes.** It keeps `raw/` immutable, avoids
append races, and costs the same one write.

**D2. May a URL stand in as a source ID** (CRM/research auto-enrichment from
search results) instead of capturing a record? **Decided: no.** A URL resolves
only syntactically and rots, and research already delegates capture to the
fetcher.

**D3. Micro-capture: accept +1 write per captured fact?** **Decided: yes**, via
`capture.py`. The alternative, keeping the uncaptured shape as a legal ID, is
exactly the defect class this design removes.

**D4. `## Sources` legend: keep with an ID-prefixed grammar, or drop the checks?**
**Decided: legends stay as optional free prose, with no grammar or check**
(changed by review F7). No skill prescribes them, agents have almost stopped
writing them, and one drift instance didn't justify a checked fourth
declaration site plus a human-confirmed migration of 136 bullets.

**D5. Reconstructed records for the 18 legacy conversation dates, or a single
sentinel ID (`legacy-uncaptured`) for all of them?** **Decided: per-date
reconstructed records.** They keep the date grouping and let each date be
retired independently once its claims are re-sourced.

**D6. Weekly-brief pages that cite `log.md`/`index.md`.** **Decided:**
`sources: []` plus `lifecycle: dated-digest`, with lint exempting dated digests
from the grounding check. Today lint's grounding check only fires when `srcs` is
non-empty, so an empty list already passes, but that is accidental and should be
made explicit. Step 6 adds the exemption (plan review P17).

**D7. Severity timeline.** **Decided:** 🟡 for R3/R6/R7/R12 through the
migration, then 🔴 for R3, R6 and R12 in a 3.0.0. R7 stays 🟡: a citation that
breaks the format but still resolves is cosmetic, and one that no longer
resolves is already an R3 error. Starting any of them at 🔴 would turn the
session-start health line red on day one for a known, scheduled backlog. R12 has
13 violating pages until M4 (review F3). Within R12, missing frontmatter and
missing required keys stay 🔴 throughout, as they are today (plan review P15).

**D8. Public-repo hygiene (N12).** One fork doc and one test file carry the names
of real people and customer companies from the wiki, and both are already on
GitHub. Product and page-topic names are not treated as private. **Decided 2026-09-28:
scrub the current files and rewrite git history** (step 0), instead of the
earlier recommendation to leave the identifiers in history. The rewrite is cheap
now: the fork has 0 forks, so it breaks no one else's copy, and the unpushed
local commits can go out in the same force-push. Every day and every fork
after this raises the cost. Costs accepted: rewritten commit IDs from `4e61e6c`
onward, with the IDs cited in `fork-chgs/` updated from the commit map (step 0,
item 4); a force-push; re-cloning other local copies; and orphaned commits staying
reachable by ID on GitHub until they are purged.

**D9. How should the MCP `edit` tool be handled after step 3?** **Decided: deny
it** with a permission rule, under both tool-name forms (section 5.11, item 1;
changed by review F4). It holds every operation that re-serializes a page (#47,
#49), agents have avoided it since 2026-08-11, and the Edit tool covers all its
operations. Leave `vault` off the allowlist (it includes delete), and add an
explicit `ask` entry if MCP writes should always prompt, since `defaultMode:
"auto"` doesn't guarantee one. **Decided 2026-09-29: add the `ask` entry** for
both name forms of `vault` (plan review P5). It also prompts on `vault` reads,
which agents rarely make, since reads go through `view`.

**D10. Upstream first or fork first?** **Decided 2026-09-29: fork first.**
Implement the whole plan in the fork, then offer it upstream as a separate task
once every step has landed. The "Up/Fork" column in section 8 marks which steps
are candidates for that later offer. When it happens, offer steps 1–4 as pull
requests (bug fixes plus a refactor, low controversy), and open an *issue* for
step 5's citation spec before a PR, since it changes the micro-capture contract
the author designed. This replaces the original recommendation to offer steps
1–4 upstream right away.

**D11. Run a locally patched copy of the MCP (plan step 12)?** **Decided: no;
step 12 is dropped** (changed by review F2, F4). The permission rule in D9
removes the operations that produce timestamp dates, at no maintenance cost. The
patch's `CORE_SCHEMA` would also write dates unquoted, which conflicts with the
canonical `'YYYY-MM-DD'` form and re-exposes N6. NW2 stays deferred.

---

## 10. Follow-on work (after this design)

Four pieces of work were deliberately left out of this design. They are recorded
here so they aren't lost.

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

## Provenance of this document

Written from direct reading of every file named in section 2 in the fork at `11fa847`:
all eight SKILL.md files, the eleven core references, templates (core, prd, crm),
the five hooks and `hooks.json`, the five worker agents, `lint.py`, both test
modules, README, CONTRIBUTING, AGENTS.md, CHANGELOG, PLUGIN-REVIEW, and the
fork-chgs documents. Wiki measurements were run with PyYAML and small scripts
against a scratch copy, and `lint.py` was run there (baseline reproduced:
0 errors, 37 warnings, 44 info; R3 on 31 pages, R4 on 12). Git archaeology in the
wiki repo covered `c910309`, `c4de70c` and `5cc416c`.

Not verified in this session, and flagged where used: that PreToolUse and
PostToolUse hooks fire on MCP tool calls on this install (documented behavior);
whether async hook output reaches the model; whether hooks fire inside
subagents and whether `CLAUDE_SKILL_DIR` is set there; the origin of the LINT doc's 18th hybrid page;
token counts (reported as bytes).

**Revision of 2026-09-28.** This document was revised to take in the accepted
findings (F1–F16) of
[Sources and References Review](sources-and-references-review.md).
The review checked every rule against a fresh scratch copy of the wiki, the hook
and MCP code, and the saved session transcripts. Its per-operation analysis of
the MCP is in
[Wiki-Search MCP Tools Analysis](wiki-search-mcp-tools-analysis.md).
Additional unverified points from the review: who wrote the timestamp dates
committed after 2026-08-11 (the saved transcripts miss about a third of the
wiki-editing days); the MCP-versus-SessionStart startup order; how auto mode
treats unlisted MCP write tools.

**Plan review of 2026-09-29.** After step 1 found design text that contradicted
the code, the implementation plan was audited against section 5, the review's
findings and the current code. The accepted issues (P1–P29) are in
[Sources and References Plan Review](sources-and-references-plan-review.md) and
are marked "(plan review Pn)" here. Newly unverified: which agent definition wins
when a user-level and a project-level agent share a name, as they will in the
fork after step 9.

---

## Appendices

The plain-language appendices are in a separate file,
[Sources and References Appendices](sources-and-references-appendices.md):

- **Appendix A.** Root causes RC1–RC7 in plain terms.
- **Appendix B.** New findings N1–N15 in plain terms.
