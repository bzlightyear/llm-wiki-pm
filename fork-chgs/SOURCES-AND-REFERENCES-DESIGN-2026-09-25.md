# Sources and references: invariant-based design

Date: 2026-09-25 · Status: **proposed, not implemented** · Scope: every rule that
governs how wiki pages, `raw/` records, frontmatter `sources:`, inline
`[source: ...]` citations, body `## Sources` legends and `[[wikilinks]]` are
written, parsed and checked.

Follows `LINT-FRONTMATTER-CHECKS-2026-09-23.md`. That document added checks. This
one steps back and asks which small set of properties would make a broken
reference impossible to create, or at least impossible to keep, and where each
property has to live.

Line references are against the fork at `c105625` (upstream `2.21.0` plus local
commits). Wiki measurements come from a scratch copy of the private production
wiki taken 2026-09-25 (245 live pages, 242 archive snapshots, 156 `raw/` files).
Every wiki example below is a placeholder. Defect classes are described with
counts, never quoted.

Reference convention: `§N` always means an operation number in the core
`SKILL.md` (for example §2 Ingest, §4 Update). "Section N" means a section of
this document; other files' sections are named with the file. A-numbers (A3,
A11, …) always mean PLUGIN-REVIEW-2026-07-15 items; this document's own IDs
use other prefixes (I, RC, N, W, S, H, K, V, B, R, M, D, F).

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
   the path, inline markers cite the ID, a legend (if present) lists the IDs, and
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
4. **Enforcement is honest about its limits.** Hooks never deny, so nothing on a
   write path is *prevented* except by grammar. What changes: (a) the snapshot
   hook and a new synchronous post-write validator also match the wiki-search MCP
   write tools, so agent writes through the MCP get a pre-image and a same-turn
   violation report; (b) all hand-rolled frontmatter parsers are replaced by one
   module; (c) lint remains the only check that sees Bash, script, Obsidian and
   git writes, and session-start already runs it, so every write path is detected
   by the next session at the latest.
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
| 11: "fe14c2f removed the comma ambiguity from extract_sources" | True only for quoted flow entries. `extract_tags()` still splits PATCH-3a's comma-joined string (`lint.py:133-139`), so a block-style tag with a comma would still shred. No tag contains one today. |
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
quoted dates quoted.

That means the unquoted `last_verified` in `5cc416c` was **not** produced by
this MCP version, even though the same commit's block-list conversion was. The
writer of that one value is unconfirmed; an Edit or Obsidian's properties editor
are the likely candidates. Either way, a quoted date can end up unquoted, and
PyYAML (YAML 1.1) then loads it as a `datetime.date`, not a string. Any parser
this design adopts must load every scalar as a string.

---

## 1. Invariants

Eight properties. If I1–I6 hold, every reference on a live page can be followed
to a file. I7 makes violations recoverable, and I8 makes them revisitable.

| # | Invariant | Single spec location | Write paths that can violate it | Enforcement | Resulting guarantee |
|---|---|---|---|---|---|
| I1 | **Parseable frontmatter.** Every wiki page starts with one frontmatter block that parses under the *frontmatter profile* (section 5.10): unique keys, values are strings, lists of strings, or one level of string mappings, and the required keys are present. | `references/citation-spec.md`, "Frontmatter profile" section (new). `SCHEMA.md` template keeps the field list and points there. | W1–W3, W5, W7–W12, W14–W16, V1–V4, B1–B6 (all page writers) | Write-time advisory (post-validate hook) for tool writes; lint 🔴 for all (R12, with R1/R2/R5 as specific messages) | Detected in the same turn for Write/Edit/MultiEdit/MCP writes; detected at next session start (or next lint) for Bash, script, Obsidian and git writes. Not prevented. |
| I2 | **Declared ⇒ exists.** Every `sources:` entry is a canonical path (`raw/<dir>/<id>.md` or `<wiki-dir>/<slug>.md`) to a file that exists. | `citation-spec.md`, "Declarations" section | Same as I1, plus any rename or deletion under `raw/` or of a page (B1, B3, V3) | Post-validate hook (stat each path); lint 🔴 (R6) | Same as I1. Because IDs have a closed grammar, a malformed entry *cannot be written by a correct writer*, and no serializer can split one. That is the only prevention-by-construction in the design. |
| I3 | **Cited ⇒ declared.** Every inline citation ID on a page equals the `slug()` of exactly one entry in that page's own `sources:` (section 5.2). | `citation-spec.md`, "Inline grammar" section | Any body edit, including split children and MCP `string_replace` | Post-validate hook; lint 🔴 (R3 rewritten as exact match) | Same as I1. With I2, this closes the chain claim → ID → declared path → file. |
| I4 | **Legend = declarations.** If a page has a `## Sources` legend, the set of IDs it lists equals the set declared in `sources:`. | `citation-spec.md`, "Legend" section | Any edit that adds a source to one site and not the other (ISSUE-3 part B) | Lint 🟡 (R8); `--auto-fix` appends missing IDs, never deletes | Detected. Drift can no longer survive silently across edits, as the ISSUE-3 instance did across six edits. |
| I5 | **Records are unique and write-once.** Every `raw/` record's ID (stem of a `.md` file outside `raw/assets/`) is unique across `raw/` and disjoint from all page slugs, and a record is never modified after creation. | `citation-spec.md`, "Records" section; `AGENTS.md` "No raw/ mutations" points there | W1, W4, V1–V2 (create or overwrite raw), fetcher worker (K1), Bash | Pre-write hook warns on any Write/Edit/MCP edit to an *existing* `raw/` file; lint 🔴 on ID collisions (R9) | Uniqueness is fully detected. Immutability is detected at write time for tool writes only. A Bash or Obsidian edit to a record is invisible except in git. |
| I6 | **Links resolve.** Every `[[target]]` on a live page resolves to exactly one page slug. Slugs are unique across the page directories. | `SCHEMA.md` Conventions (unchanged format; CONTRIBUTING protects it) | Rename, split, archive, supersede (W7–W10), MCP writes that escape `[` | post-write link check (existing); lint 🔴 (existing), supersession auto-fix | Unchanged from today, plus `briefings/` coverage and the escape check at write time. |
| I7 | **Recoverable.** Before an agent tool overwrites, deletes or archives a page, a pre-image exists in `_archive/<slug>-<date>.md`, or in git. | `AGENTS.md` "Snapshot before destructive ops" (kept as the behavioral rule), with the mechanism in `hooks/README.md` | Every page writer | PreToolUse hook extended to MCP `vault`/`edit`; lint `--auto-fix` snapshots before writing; Bash/script writers keep the behavioral rule | Guaranteed (best-effort I/O) for the first tool write per page per day, **including MCP writes after this change**. Not guaranteed for Bash, script, Obsidian or git writes, or for the second write of the day to the same page. For those, git is the undo, and the wiki is a git repo. |
| I8 | **Revisitable.** A page whose only primary sources are conversation records (or reconstructed records) carries a verification horizon: after 30 days without a newer `last_verified:`, lint surfaces it. | `citation-spec.md`, "Revisit" section | Time. Nothing writes this violation, it accrues. | Lint 🔵 (R10), listed in `_status.md` | Surfaced, never forced. This is the revisit obligation ISSUE-1 and ISSUE-3 lack (brief item 13). |

Not an invariant, by decision: *declared ⇒ cited*. `ingest-guide.md ⑤` says
frontmatter lists all sources while markers anchor specific claims. On this wiki,
211 of 694 declared raw sources are never cited inline, spread over 84 pages.
Most are legitimate. It stays a ratio heuristic (R4), and the split procedure
(section 5.8) is where it becomes a hard rule, because split children are exactly where
the copy-paste signature occurs.

### Which invariants inherit the MCP hole

Today the wiki-search MCP write tools trigger no hook, so for MCP writes **I1,
I2, I3, I5, I6 (write-time part) and I7 all degrade to lint-only**, and I7 is
simply absent: no snapshot, no undo except git. After step 3 of the plan (section 8)
the hook matchers include `mcp__wiki-search__vault` and `mcp__wiki-search__edit`,
and the remaining MCP-specific gaps are:

- `edit` operations are not simulated. The pre-hook snapshots but cannot compute
  the post-image, so validation happens after the write (PostToolUse), not
  before it.
- The `\[` re-escaping bug (wirux/mcp-markdown-vault#47) is detected at write
  time by the validator and repaired by lint `--auto-fix`. It is not prevented.
- AST re-serialization changes style and quoting. Under this grammar that is
  harmless (I2), so it stops being a defect and becomes diff noise.
- `vault.create` without `content` falls back to the note template in
  `meta/contract.md`, a competing schema. Fixed by reconciling the contract
  (section 5.10), not by a hook.

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
| S2 | maintain: `briefings/YYYY-MM-DD.md`; rotation `mv` to `_archive/briefings/`; autonomous `lint --auto-fix` | **`briefings/` is outside every hook gate and lint scan** (new finding N2) |
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
| V1 | MCP `vault.create` / `create_from_template` | new file; contract.md template when no content |
| V2 | MCP `vault.update` | whole-file overwrite, no snapshot today |
| V3 | MCP `vault.delete` | **deletion with no snapshot today** |
| V4 | MCP `edit` (append, prepend, replace, delete-section, line_replace, string_replace, frontmatter_set; batch ≤50 paths) | AST round-trip, `\[` bug |
| V5 | MCP `system.save_overview` | `meta/overview.md` (not a wiki page) |
| B1–B6 | Bash `mv`/`sed`/heredoc, ad-hoc scripts (the page-splitting script), Obsidian edits, `git` checkout/merge, user hand-edits, lint auto-fix | no hooks ever; lint only |

---

## 3. Root causes

Plain-language explanations of each root cause are in Appendix A.

| RC | Root cause | Findings it explains |
|---|---|---|
| **RC1** | **No source identity.** There is no definition of a source ID or a resolution function. Each of three declaration sites accepts free text, and "is this a source?" is answered by a prefix test (`not startswith(entities/…)`). **This is the biggest root cause.** | 1, 2, 3, 4, 6, 12, 14, 16; R3's permissive matcher; N3, N4, N7 |
| RC2 | **The honest path for conversational facts is more expensive than the dishonest one.** Capture-to-raw (v2.0.0) is a full ingest; the v2.20.0 fast path skips it by design (A13) and prescribes a citation shape that resolves to nothing. `32e42a3` then made a *third* shape official for Update. | 1, 3, 17, ISSUE-3 A |
| RC3 | **No frontmatter profile, three parsers.** No document says what subset of YAML a page may use, so each parser guesses: `parse_frontmatter`, `extract_sources`, and the copy in `pre-write.sh`. PATCH-3a added a fourth behavior by joining lists into strings. | 5, 10, 11 |
| RC4 | **Enforcement is attached to tool names, not to files.** The hooks match Write/Edit/MultiEdit, so MCP, Bash, scripts, lint `--auto-fix` and session-start are unseen writers, and `briefings/` sits outside the gate entirely. | 7, 10, 18; N1, N2, N14 |
| RC5 | **Derived-page operations have no reference procedure.** Split, entity promotion, supersede and crystallize say nothing about which sources and links the new page may carry. | 3 (propagation into 10 files), 8 |
| RC6 | **Nothing revisits a citation.** Write-time rules only. There is no horizon, verification date, or status that brings a citation back. | 13, ISSUE-1, ISSUE-3 |
| RC7 | **Duplicated surfaces drift.** Two worker copies, templates showing one shape, a default MCP contract, stale README/CONTRIBUTING, sub-skills that predate AGENTS.md's grammar. | 9, 15, 18, 20; N5, N8, N9 |

New findings (N) not in the brief. Appendix B explains each one in plain terms:

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
- **N12** Three public fork files contain real wiki page slugs, a real marker
  string, or real names (`tests/test_lint.py:115,129`,
  `LINT-FRONTMATTER-CHECKS-2026-09-23.md` 6 lines, `llm-wiki-pm-changelog.md`
  7 lines). See open decision D8.
  **Impact:** Private wiki names are published in the public fork on GitHub, in two docs and a test file.
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
  values. **Cause confirmed:** the wiki-search MCP's frontmatter merge
  (`mcp-tools.js` ~291–305, also `batch-edit.js` and
  `markdown-file-repository.js`) loads and dumps with js-yaml's default schema,
  which parses an unquoted date as a date object and writes it back as a
  timestamp. It was reproduced with the MCP's own js-yaml, and entered the wiki
  in four separate commits, so it recurs. It is the same full-file round-trip as
  PATCH-3d's bracket escaping (#47), and it is reported upstream as
  wirux/mcp-markdown-vault#49. Python 3.9's `datetime.fromisoformat` rejects the
  trailing `Z`, so lint's 90-day staleness and 120-day `last_verified` checks
  (`lint.py:537-593`) and session-start's stale/decay scan silently skip those
  values.
  **Impact:** 3 pages' verification dates and 1 page's update date are invisible to every staleness check, so those pages can never be flagged as stale, and nothing reports that the check was skipped.

---

## 4. Evaluating the candidates

The problem each option must solve: facts that arrive without an artifact (chat,
verbal relay, the user) must end up cited by an ID that resolves, without making
micro-capture a ceremony, and without an invariant that the MCP's serializer
breaks.

| | A. Path-only + daily file (undecided candidate) | B. Mandated block-style lists | C. `raw/inbox/` queue + lint age warning (PLUGIN-REVIEW OD4) | **D. Source IDs + write-once capture records (proposed)** |
|---|---|---|---|---|
| Idea | Every `sources:` entry is an existing path; conversations are appended to `raw/internal/conversation-YYYY-MM-DD.md` | Frontmatter lists are always block style, so an item can't be split by commas | Unprocessed captures land in `raw/inbox/`; lint warns when one ages without being filed | A's path rule plus a defined ID grammar and exact stem resolution shared by all three sites. One record per capture, written once, by a helper |
| Resolves I2 | Yes | **No.** A block item can still be `user, conversation, DATE`, so it only fixes shredding. | Partly: inbox items resolve, but moving them out when processed breaks every citation to them | Yes |
| Resolves I3 (inline ↔ frontmatter) | Only if paired with a resolution rule; A doesn't define one | No | No | Yes, exact match |
| Survives MCP re-serialization | Yes (paths need no quoting) | Yes, and it matches MCP output style | Yes | Yes. Style becomes irrelevant, not mandated. |
| Keeps `raw/` immutable | **No.** Appending to today's file mutates a Layer-1 record several times a day, and two sessions can race the append. | n/a | Only if items never move, which defeats "queue" | Yes. A record is complete when written. |
| Micro-capture cost | +1 Edit (append) per fact, and the agent must read the file first to append safely | 0 | +1 Write, plus a later triage | +1 Write, or one `capture.py` call, per fact or per topic |
| Directory layout change (semver major per CONTRIBUTING) | No | No | **Yes** (`raw/inbox/`) | No (`raw/internal/` exists) |
| Upstream conflict surface | Small | Small (templates) | Medium (SCHEMA, lint, scaffold) | Small to medium: one new reference file, lint, hooks, a few SKILL.md lines |
| Verdict | Right direction; the append mechanism is wrong | Do it as a template default only. Unnecessary as a rule once IDs can't contain commas. | Solves a different problem (deferred filing). Decline for now; OD4 stays open (section 6). | **Adopt** |

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
Source Attribution, SCHEMA.md template Inline Provenance, ingest-guide ⑤,
update-guide section 3, sub-skills, templates) is reduced to a one-line pointer plus at
most one example. That makes it the single spec location for I1–I5 and I8.

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
  replaced by a pointer to it.
- Record frontmatter (all optional except `source_type` and `captured`, which
  lint 🟡s when missing (R13), only on records whose filename date is after the
  rule ships, so existing records are never flagged):

```yaml
---
title: "Pricing page, competitor-x"
source_type: web            # web | pdf | transcript | chat | email | warehouse | conversation | internal | other
captured: 2026-01-15
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
  next to `README.md`, as `output-formats.md` shows today, would be scanned as a
  page with no frontmatter, and two directory pages each holding one would
  collide on the slug `deck`. Non-markdown artifacts (`.py`, `.png`, `.csv`,
  `.pdf`) may stay beside `README.md`, since lint only scans `.md` files.
- A wiki page may be a source (crystallize digest, concept page, persona's
  entity page). Its ID is its slug and it is declared by path. It is a
  **secondary** source for grounding purposes.
- Not sources: `log.md`, `index.md`, `SCHEMA.md`, `MY-INTEGRATIONS.md`,
  `_status.md`, `_archive/**`, absolute paths, anything outside the wiki.
  `SCHEMA.md` is Orient context, not a citable source: it is edited over time,
  so a citation to it would later point at different text without anyone
  noticing. Context kept in SCHEMA (for example the owner's role or org notes in
  its Domain section) stays where it is, because Orient reads it every session.
  A page that relies on one of those facts cites a user-statement record
  (`stated_by: user`) instead, exactly as for a fact stated in chat. 3 pages cite
  SCHEMA this way today (section 7). Where org structure should live, and
  whether Orient should read the relationship map, is left to the follow-on
  design on Orient content.

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

Grounding (existing `lint.py:502-520`) is redefined on resolved IDs: *primary* =
resolves to a record; *secondary* = resolves to a page. Behavior is otherwise
unchanged.

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
[source: https://example.com/pricing, 2026-01-15]           URL; capture the page as a record (R7, see D2)
[source: SCHEMA.md org chart]                    structural file (R3)
```

Resolution is exact and page-local: split the marker on `"; "`, take the text
before the first `", "` as the ID, and look it up in
`{slug(p): p for p in sources}`, using the `slug()` function from section 5.2. No substring matching and no conversational
exemption. `_citation_matches_source` and `_is_conversation_citation` are
deleted.

`update-guide.md:77` and `output-formats.md:89-90` stop showing `[[raw/…]]`
wikilinks as citations. Prose citations of wiki pages ("Per [[page]]") remain
valid *as links* (I6). They are not source citations and need no declaration.

### 5.5 `## Sources` legend

Optional. When present, each bullet starts with a backticked ID, followed by any
annotation the author wants:

```markdown
## Sources
- `competitor-x-pricing-2026-01-15`: public pricing page, captured after the tier change
- `conversation-2026-01-15-pricing-tier`: decision stated by the user in chat
```

I4: legend ID set = declared ID set. `--auto-fix` appends missing IDs (with the
record's `title:` as annotation) and never deletes. Today's 49 legends are 82%
prose (136 of 166 bullets), so none is machine-checkable yet. Migration step
M6 (section 7) converts them. Alternative in D4: drop legends altogether.

### 5.6 Conversational facts (micro-capture and Update)

Rule: **a fact with no artifact gets a record before it gets a citation.** It
applies to micro-capture, Update, Learn and CRM alike.

- Record: `raw/internal/conversation-YYYY-MM-DD-<topic>.md`, `source_type:
  conversation`, `stated_by:`, and the statement near-verbatim. One record per
  topic per conversation. A later fact on the same topic gets a new record with a
  `-2` suffix, never an append.
- `scripts/capture.py <wiki> --topic <slug> [--stated-by user] < statement`
  writes the record with correct frontmatter, refuses to overwrite, and prints
  the path (for `sources:`) and ID (for the marker). It is one Bash call and
  stdlib only.
- Tool-retrieved facts (a chat thread read via MCP) are *not* conversation
  records. They follow the chat/email capture routes (`ingest-guide ①`), as today.
- The SKILL.md §2 fast path changes from `source: conversation | <date>` to
  "capture a record (`capture.py`), cite its ID". The §4 ③ text from `32e42a3`
  shrinks to two lines pointing at this section. "Never coin an ID for a record
  that doesn't exist" survives verbatim as the one-line reason.

### 5.7 Non-file sources

- **Web**: captured as a record (`source_type: web`, `source_url`). The
  CRM and research enrichment steps delegate capture to `worker-source-fetcher`,
  which research already does. D2 asks whether a URL may stand in as an ID for
  low-stakes enrichment. My recommendation is no.
- **Warehouse**: already file-shaped. The snapshot record
  `raw/internal/<metric>-<snapshot>.md` *is* the source, and `query <ref>` is the
  citation's location: `[source: metric-arr-202601, query saved-query-123]`. The
  existing `source_query_ref`/`source_snapshot` fields move from page
  frontmatter guidance to the record, where they describe the artifact.
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
  history splits): (1) snapshot the parent (automatic for tool writes);
  (2) each child's `sources:` = exactly the IDs its body cites, computed with
  `lint.py --cited-sources <page>` (a new read-only flag); (3) children carry
  `split_from: <parent-slug>` (new optional field); (4) parent and children
  link to each other; (5) `[[parent#heading]]` anchors pointing at moved
  sections are rewritten. On pages with `split_from`, R4 becomes 🔴: an uncited
  declaration on a split child is always a copy.
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
the resolvable set; worker-link-validator defers to `lint.py` instead of keeping
its own three-directory resolver (N9); the post-write check runs on MCP writes
too. A wikilink inside a `[source: ...]` marker is invalid (R7), because the
marker is an ID site, not a link site.

### 5.10 Frontmatter profile, the single parser, and `meta/contract.md`

**Profile** (what a page's frontmatter may contain):

- `key: value` lines; keys `[a-z_][a-z0-9_]*`, unique (R5).
- Value: a plain or quoted scalar; a flow list `[a, "b"]` on one line; a block
  list of `  - item` lines directly under an empty `key:`; or, for the persona
  keys only (`language_patterns`, `tone_by_channel`, `vocabulary_markers`), one
  level of `  subkey: scalar`.
- **Every scalar is a string.** Dates are validated by regex (`created`,
  `updated`, `last_verified`: `YYYY-MM-DD`), never type-coerced. This makes the
  MCP's quote-stripping irrelevant (N6).
- Anything else is a profile violation (🔴, R12). R1 and R2 become two specific
  messages of this check.
- Required keys: `title, created, updated, type, tags, sources` (as `lint.py`
  today). `coverage` is recommended and 🟡 on factual types (as today).
  CONTRIBUTING and worker-link-validator are corrected to match (N4).

**One parser.** New `skills/llm-wiki-pm/scripts/wikifm.py`, stdlib only:
`parse(text) -> (fields, errors)` implementing the profile; `sources(fields)`,
`citations(body)`, `legend_ids(body)`, `resolve(page, wiki)`. `lint.py`,
`pre-write.sh`, the new `post-validate` hook, `backlinks.py` if needed, and
`capture.py` all import it. `parse_frontmatter`, `extract_sources`,
`_split_flow_list`, `extract_tags`'s comma split, and the copy in `pre-write.sh`
are deleted. PyYAML is not a runtime dependency. It is used in tests as an
oracle: for every fixture, `wikifm.parse` must agree with
`yaml.load(..., BaseLoader)` or report an error. The duplicate-key fixture is the
documented case where it deliberately disagrees.

**Contract reconciliation.** The MCP tells agents to read `meta/contract.md` for
frontmatter and naming. The default contract declares a different `type` enum, a
`status` field, no `sources`, a no-prefix naming rule, and a `vault.create` note
template. The server never overwrites the file and says to edit it. So:

- Ship `skills/llm-wiki-pm/templates/vault-contract.md`. Its Frontmatter Schema
  says "authoritative schema: `SCHEMA.md`; citation rules:
  `references/citation-spec.md`", lists the wiki's `type` enum, drops `status`,
  replaces the naming rule with SCHEMA's, and sets the Note Template to a valid
  wiki page skeleton with `sources:` (empty list, 🔴 until filled, which is
  correct).
- `session-start.sh` scaffold copies it to `$WIKI/meta/contract.md` when absent.
  The MCP creates the file only if it doesn't exist, so the wiki's version wins
  on new installs.
- Lint R11 🟡: `meta/contract.md` still carries the MCP default schema (detected
  by `generated_by: mcp-markdown-vault` plus a `status` enum line). The fix for
  the existing wiki is a one-time hand edit, which the file itself invites.
- Today this is latent: 0 pages use the contract's types or `status`.

### 5.11 Write-time enforcement (hooks, all exit 0)

1. **Matchers.** PreToolUse and PostToolUse match
   `Write|Edit|MultiEdit|mcp__wiki-search__vault|mcp__wiki-search__edit`. The
   *registered* hooks are the user-level entries in `~/.claude/settings.json`, not
   `hooks/hooks.json`, so both must be updated (hooks.json for upstream parity).
   Claude Code documents PreToolUse/PostToolUse matching on `mcp__<server>__<tool>`
   names. I have not tested it on this machine; step 3 includes that check.
2. **Path extraction.** `tool_input.file_path` (Write/Edit/MultiEdit);
   `tool_input.path` (MCP single); `tool_input.operations[].path` (MCP batch).
   MCP paths are vault-relative and joined to `$WIKI`. The launcher and the hooks
   resolve `$WIKI` with the same chain, so they agree unless `.wiki-path` changes
   mid-session.
3. **Snapshot (pre).** On any existing page targeted by Write, Edit, MultiEdit,
   `vault.update`, `vault.delete`, or any `edit` op: copy to
   `_archive/<slug>-<date>.md`, where slug = `lint.py`'s `slug()`, which fixes the
   README collision (N14). `briefings/` joins the gated set. The two root files
   the page rule skips get their own rule:
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
   so the gate is skipped for them. Post-validate covers them.
6. **Post-validate (new, synchronous PostToolUse, `hooks/post-validate.sh`).**
   Reads the written file(s) from disk and runs `wikifm` checks for I1–I4, the
   R7 grammar, escaped `\[`, and links. It emits at most ~6 lines of
   additionalContext naming each violation and its fix. The existing async
   `post-write.sh` link check folds into it, and its `_status.md` append is kept.
   Budget: one python start plus one file parse plus a stat per declared source,
   well under 200 ms. It is synchronous because the agent must see the result in
   the same turn. Whether an *async* hook's context would reach the model is not
   something I verified, so the design doesn't rely on it.
7. **Session-start** (already runs lint): add the counts of I1–I4 violations to
   the additionalContext line and `_status.md`. Stop writing a report in
   `--json` mode (N1). This makes every write path, including Bash, Obsidian and
   git, detected within one session boundary.
8. **lint `--auto-fix`** imports the snapshot function and snapshots each page
   before writing it.
9. **MCP write path (checklist, not enforced).** Until the MCP's full-file
   round-trip is fixed (#47, #49, follow-on F2, or the step 12 patch), change
   frontmatter with the Edit tool, not MCP `frontmatter_set` or `vault.update`,
   and prefer Edit over MCP `string_replace` for body edits. This is one line
   in SKILL.md's Tool Selection rules. Nothing can enforce it, so items 6 and 7
   and R12's auto-fix catch what slips through.

Honest summary: **prevented by construction**: comma-shredding and quoting
dependence (ID grammar); ID typos from capture (`capture.py` prints the ID);
README snapshot collisions. **Detected in the same turn**: I1–I4 and escapes
for agent tool writes, now including MCP. **Detected by next session**:
everything, for all writers. **Not detected**: edits to a record through Bash,
Obsidian or git (git history only); a same-day second overwrite's pre-image
(git only).

Permission note: keep both `mcp__wiki-search__edit` and `mcp__wiki-search__vault`
on ask. Snapshots make MCP writes recoverable, but every MCP frontmatter or
`string_replace` edit can still damage content elsewhere in the page (#47,
#49). `vault` stays on ask regardless, because permissions match on tool name,
so allowing `vault` would also allow `vault.delete`. Revisit `edit` once
follow-on F2 or the step 12 patch has fixed the round-trip.

### 5.12 Revisit obligation (I8)

Lint R10 🔵: pages whose primary sources are all `source_type: conversation`
(or `reconstructed: true`) records and whose `last_verified` is absent or more
than 30 days old. They are listed in `_status.md` under "Secondhand, unverified".
Verifying against a live source means stamping `last_verified:` and, where
possible, adding a primary record. The same horizon mechanism is offered to
ISSUE-1 (action-item status) but not built here.

### 5.13 `wiki-search.sh` fix and smoke test

```sh
FILE_WIKI=""
if [ -f "$(pwd)/.wiki-path" ]; then
  FILE_WIKI=$(tr -d '[:space:]' < "$(pwd)/.wiki-path")
fi
```

This mirrors `session-start.sh`'s `-f` test. The bug is that a failed `<`
redirection is reported by the shell before `2>/dev/null` applies. Reproduced:
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
  the changelog, not in git history.
- **Worker copies.** Replace per-project copies with user-level symlinks, the
  same way skills are installed: `~/.claude/agents/worker-*.md →
  ~/Projects/llm-wiki-pm/.claude/agents/`. Then delete `pm-wiki/.claude/agents/`
  (identical today, verified with `diff -r`). One source, visible in every
  project. The fork's own project copy is the same file. Separately, the workers
  reference `${CLAUDE_SKILL_DIR}`, which is a *skill* variable. Whether it is set
  in a subagent is unverified; step 9 checks it.

---

### 5.15 Lint rule catalog

Every R-numbered rule this document mentions, in one place. R1–R5 exist today
(commit `faaf2d8`); R6–R13 are proposed. "Now" is the tier after plan step 6;
"3.0" is the tier after plan step 11. 🔴 error, 🟡 warning, 🔵 info.

| Rule | Checks for | Invariant | Status | Now | 3.0 | Auto-fix |
|---|---|---|---|---|---|---|
| R1 | A list item on the same line as its key (`tags: - x`) | I1 | Exists; becomes a message of R12 | 🔴 | 🔴 | No |
| R2 | Block list items under an already-closed `[...]` list | I1 | Exists; becomes a message of R12 | 🔴 | 🔴 | Merge into one block list, reporting item counts before and after |
| R3 | An inline citation ID that equals the `slug()` of no `sources:` entry on the same page | I3 | Exists (🔵, loose substring match); **rewritten** as an exact match | 🟡 | 🔴 | Proposes adding the declaration; a human confirms |
| R4 | A page with 5+ sources citing fewer than half of them inline | none (heuristic) | Exists, kept | 🟡 | 🟡; 🔴 on `split_from` pages | No |
| R5 | The same frontmatter key twice | I1 | Exists, kept | 🔴 | 🔴 | No |
| R6 | A `sources:` entry that isn't a canonical path to an existing file | I2 | New | 🟡 | 🔴 | No |
| R7 | An inline citation that breaks the grammar (section 5.4): wrapped, nested `source:`, "X vs. Y", raw path form, URL, wikilink | I3 | New | 🟡 | 🟡 | Mechanical classes (path form, wraps, nested prefix, "vs.") |
| R8 | A `## Sources` legend whose IDs differ from the declared IDs | I4 | New | 🟡 | 🟡 | Appends missing IDs; never deletes |
| R9 | Two records with the same ID, or a record ID equal to a page slug | I5 | New | 🔴 | 🔴 | No |
| R10 | A page whose primary sources are all conversation or reconstructed records and whose `last_verified` is absent or older than 30 days | I8 | New | 🔵 | 🔵 | No |
| R11 | `meta/contract.md` is still the MCP's default contract | none (competing spec) | New | 🟡 | 🟡 | No |
| R12 | Frontmatter outside the profile (section 5.10), or a required key missing | I1 | New (replaces the key-presence check) | 🔴 | 🔴 | Only for timestamp dates at exactly midnight (N15): rewrites them as `YYYY-MM-DD`, which is lossless |
| R13 | A record without `source_type` or `captured`, dated after the rule ships | I5 | New | 🟡 | 🟡 | No |

Other checks keep their current tiers and have no R-number: escaped `\[`
(PATCH-3d/3e), broken wikilinks, orphans, index drift, self-referential
sourcing, missing inline provenance, `coverage:`, stale `last_verified`.

## 6. Dispositions

### Fork commits

| Commit | Disposition | Reason |
|---|---|---|
| `faaf2d8` R1–R5 | **Revise.** R1/R2/R5 kept as messages of the profile parser (step 4). R3 **replaced** by exact ID resolution (🟡 in 2.22, 🔴 in 3.0). R4 kept as a ratio and made 🔴 on `split_from` pages. Tests kept and extended. | R3's permissive matcher and conversational exemption exist only because IDs were undefined. |
| `32e42a3` §4 conversational citation | **Revise.** Keep "never coin an ID for an uncaptured artifact". Replace the `[source: user, conversation, DATE]` alternative with "capture a record". Move the detail to citation-spec. SKILL.md ③ drops from 402 to ~150 bytes of added text. | It legitimized one of the 12 shapes. |
| `fe14c2f` quote-aware split | **Replace** when `wikifm` lands; keep until then (it is correct in the interim). Its shredding tests become R6 migration tests. | Unnecessary once no valid entry contains a comma. |
| `c105625` template refs | **Keep.** | Plumbing; unrelated to the rules. |

### `llm-wiki-pm-changelog.md`

| Item | Disposition |
|---|---|
| PATCH-1 auto-commit disabled | **Keep, fork-only** (environment-specific). |
| PATCH-2 backlinks README self-slug | **Keep; offer upstream.** |
| PATCH-3a block-list parsing | **Replace** with `wikifm` lists-as-lists. Joining into `"[a, b]"` reintroduces comma ambiguity for `extract_tags` and makes the two parsers disagree. |
| PATCH-3b `slug()` README | **Keep; offer upstream.** It is now also the snapshot naming function. |
| PATCH-3c overview/index link targets | **Keep; offer upstream.** Extend the same registration to `briefings/`. |
| PATCH-3d/3e escaped-bracket check | **Keep** until wirux/mcp-markdown-vault#47 is fixed. Checked 2026-09-26: #47 is open with no maintainer response, and the repo has had no activity since 2026-06-02. A comment now links it to #49, the date bug from the same code path. Post-validate now reports escaped brackets at write time. The real fix is follow-on F2. |
| PATCH-4 relationship-map wiring | **Keep.** Its end-to-end verification is still pending and unrelated to this design. |
| ISSUE-1 action-item update mechanism | **Keep open, re-scoped.** Shares RC6. I8's horizon mechanism is the reusable piece; action-item status is out of scope here. |
| ISSUE-2 indexer overview regeneration | **Keep open, mitigated.** Snapshotting `overview.md` on whole-file replacements (section 5.11, item 3) makes a regeneration recoverable without a daily copy. The destructive behavior itself is untouched. |
| ISSUE-3 conversational citations / legend drift | **Close when steps 5–7 and M1–M6 land.** Part A → I2 + conversation records + reconstructed records. Part B → I4 + legend grammar. Its open question "lint or pre-write hook?" is answered: both, with lint authoritative and a non-blocking post-write hook for same-turn feedback. Its proposed rule ("exempt `conversation, <date>` only if the dated file exists") is superseded: conversational citations stop being a special case. |

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
| `## Sources` legends | 49 pages, 166 bullets: 136 prose, 19 conversational, 7 wikilinks, 4 raw paths | M6 |
| Raw records without frontmatter / with `private:` | 11 / 14 | leave records untouched (write-once); lint rules for new records only |
| Raw record/asset stem pairs | 2 | allowed (asset exclusion) |
| Timestamp-format dates (N15) | 17 values on 13 pages | normalize to `YYYY-MM-DD` in M4 (lossless: every time part is `T00:00:00.000Z`) |
| `_archive/README-<date>.md` collision | 1 file | rename by hand to the right slug if its origin can be identified from git, else leave |
| `meta/contract.md` default | 1 | hand-edit (M7) |

Migration steps (a script, `scripts/migrate_sources.py`, dry-run by default,
emitting a per-page before/after count table, per the LINT doc's lesson that
counts must be visible):

- **M1** Snapshot every page to be touched (bulk; 10+ pages needs sign-off per
  AGENTS.md).
- **M2** For each of the **18 distinct conversation dates** (all 18 have a
  `log.md` entry that day), write `raw/internal/conversation-YYYY-MM-DD-reconstructed.md`
  with `source_type: conversation`, `reconstructed: true`,
  `reconstructed_on: <migration date>`, a body quoting that day's `log.md`
  entries, and the list of pages and claims that cite it.
- **M3** Rewrite the 58 conversational `sources:` entries and 5 shredded pairs to
  the M2 paths, and the 217 conversational markers to the M2 IDs, keeping any
  parenthetical context as the marker location.
- **M4** Auto-fix the mechanical marker classes (path form, wraps, nested
  prefix, "vs.", multi-line), and normalize timestamp-format dates to
  `YYYY-MM-DD` (N15).
- **M5** Human pass on the 13 manual markers, the 11 structural-file entries,
  the 2 free-text entries, and the 31 undeclared citations.
- **M6** Legends: prefix each bullet with its ID where the annotation matches a
  declared record unambiguously (script proposes, human confirms). Append missing
  IDs. Bullets that match nothing become a `gaps:` note or are dropped with sign-off.
- **M7** Replace `meta/contract.md` content with the reconciled template.
- **M8** Re-run lint; the expected result is 0 R3/R6/R7 findings, with R10
  listing every page resting only on reconstructed records.

**What cannot be recovered.** The content of the 18 dated conversations was
never captured. `log.md` records what the agent *did* that day, not what the
user *said*. So a reconstructed record gives the claim a resolvable ID and an
honest label, not evidence. Those claims keep their current confidence at best.
R10 lists them until each is verified against a live source (`last_verified`)
or re-sourced. The phantom-slug class (finding 3) was already repaired in
`5cc416c`, but its 10 archive snapshots still contain the phantom ID. Archives
are immutable and exempt, so they stay as they are.

---

## 8. Implementation plan

Ordered by dependency. "Up" = candidate to offer upstream as a PR; "Fork" =
fork-only. Semver is per CONTRIBUTING's table.

| Step | Change | Depends on | Semver | Up/Fork |
|---|---|---|---|---|
| 0 | Scrub real names from `tests/test_lint.py` and the two fork-chgs docs (N12, D8) | — | — | Fork (public repo hygiene) |
| 1 | `wiki-search.sh` `-f` fix + `tests/test_wiki_search.py` | — | patch | **Up** |
| 2 | Doc drift: README/CONTRIBUTING `private:`, CONTRIBUTING required-field list, worker-source-fetcher `private:` and routing table, `llm-wiki-prd` "(enforced)", worker-link-validator resolver | — | patch | **Up** |
| 3 | Hooks: MCP matchers; `slug()`-named snapshots; `overview.md` snapshot on whole-file replacement; `briefings/` gated; skip `assets/` subfolders of directory pages; Edit post-image; raw write-once warning; update `~/.claude/settings.json` and `hooks.json`; `tests/test_write_hooks.py` incl. a live check that a PreToolUse hook fires on an MCP call | — | patch (bug fixes) + minor (MCP coverage) | **Up** |
| 4 | `wikifm.py` profile parser; lint, pre-write and backlinks switch to it; delete the old parsers (replaces PATCH-3a, fe14c2f); PyYAML-oracle tests | — | patch | **Up** |
| 5 | `references/citation-spec.md` (the single spec); pointers from AGENTS.md, SCHEMA template, ingest-guide, update-guide, crystallize-guide, prd/crm/research templates; `output-formats.md` artifact rule (markdown artifacts under `assets/`, section 5.2); `capture.py`; SKILL.md §2/§4 edits and the Tool Selection line to edit frontmatter with the Edit tool, not the MCP (section 5.11, item 9); revise `32e42a3` | 4 | minor | **Up as an issue first**: it is opinionated and changes the micro-capture contract |
| 6 | Lint: R6, R3 exact, R7 grammar, R8 legend, R9 record uniqueness, R10 horizon, R11 contract, R12 profile (with the midnight-timestamp auto-fix), R13 record fields, R4 on `split_from`; tiers per the section 5.15 table (🟡/🔵 initially, except R9 and R12, which have no existing violations and start at 🔴); `--cited-sources`; skip `assets/` subfolders of directory pages; auto-fix for mechanical markers and legend append; auto-fix snapshots; `--json` stops writing a report; session-start surfaces I1–I4 counts | 4, 5 | minor | **Up** |
| 7 | `post-validate.sh` synchronous PostToolUse (folds in post-write link check) | 3, 4, 6 | minor | **Up** |
| 8 | Vault contract template + scaffold copy | 5 | minor | **Up** |
| 9 | Worker agents → user-level symlinks; delete the wiki's copy; verify `CLAUDE_SKILL_DIR` in subagents | — | — | Fork (install layout) |
| 10 | Wiki migration M1–M8 (dry-run, review, apply, commit in the wiki repo) | 5, 6 | — | Fork (wiki content) |
| 11 | Promote R3/R6 to 🔴 | 10 | **major (3.0.0)**: it narrows the valid value space of `sources:`, a frontmatter-schema change that makes existing wikis report errors | **Up**, with the migration script |
| 12 | *Optional (D11).* Pinned local copy of the MCP (v2.3.0) with a version-checked patch that passes `{schema: yaml.CORE_SCHEMA}` to the frontmatter `load`/`dump` calls; `wiki-search.sh` runs it instead of the npx cache; a test in `tests/test_wiki_search.py` asserts `created: 2026-09-03` survives a `frontmatter_set` round-trip | 1 | — | Fork |

### Frontmatter changes and semver

No new *required* frontmatter field and no directory-layout change, so nothing
before step 11 is major. The design adds these fields, none of them required by
the schema:

| Field | Goes on | Purpose | Status | Defined in |
|---|---|---|---|---|
| `split_from` | wiki pages | names the page a split-off page came from | optional; tightens R4 on that page | section 5.8 |
| `source_type` | raw records | kind of source (web, transcript, conversation, …) | recommended; R13 warns if missing on new records | section 5.1 |
| `captured` | raw records | date the source was saved | recommended; R13 warns if missing on new records | section 5.1 |
| `stated_by` | raw records (conversations) | who said it: `user` or a person's page slug | optional | section 5.1 |
| `asset` | raw records | path to the original PDF or slides in `raw/assets/` | optional | section 5.1 |
| `reconstructed` | raw records (migration only) | marks the 18 rebuilt conversation records | set by the migration | section 7, step M2 |
| `reconstructed_on` | raw records (migration only) | date they were rebuilt | set by the migration | section 7, step M2 |

### SKILL.md size and upstream conflict surface

**Net SKILL.md size change (estimate):** §2 fast path +~120 bytes; §4 ③
−~250 bytes (402 → ~150); §4 snapshot sentence +~40; References list +~80;
Tool Selection line on MCP frontmatter edits +~150.
**Net ≈ +140 bytes, i.e. about +0.6%** (24,625 → ~24,765). The new rules cost the
always-on budget nothing. They live in `citation-spec.md` (est. ~6–7 KB, read on
demand, like `ingest-guide.md`) and in lint and hooks.

**Upstream conflict surface.** Heavily edited upstream files touched: `SKILL.md`
(~6 lines), `lint.py` (large: parser swap plus rules), `pre-write.sh` (large),
`hooks.json` (2 matchers), `ingest-guide.md`/`update-guide.md` (a few lines each).
To keep merges tractable: land step 4 first as a pure refactor (no behavior
change, all existing tests green) so later rule diffs are additive; put new
rules in `wikifm.py` and new lint functions rather than inline in `main()`; put
new tests in new files.

---

## 9. Open decisions (need you)

**D1. Adopt source IDs + write-once capture records (option D) over the daily
conversation file (A)?** Recommend **yes**. It keeps `raw/` immutable, avoids
append races, and costs the same one write.

**D2. May a URL stand in as a source ID** (CRM/research auto-enrichment from
search results) instead of capturing a record? Recommend **no**. A URL resolves
only syntactically and rots, and research already delegates capture to the
fetcher. If you want the cheaper path for enrichment anyway, allow a `web-url`
ID kind that lint counts as 🔵 and that never satisfies grounding.

**D3. Micro-capture: accept +1 write per captured fact?** Recommend **yes**, via
`capture.py`. The alternative, keeping the uncaptured shape as a legal ID, is
exactly the defect class this design removes.

**D4. `## Sources` legend: keep with the ID-prefixed grammar, or drop legends and
treat frontmatter as the only declaration?** Recommend **keep**. The prose
annotations are useful to human readers, and the prefix makes them checkable.
Dropping them is simpler if you don't read them.

**D5. Reconstructed records for the 18 legacy conversation dates, or a single
sentinel ID (`legacy-uncaptured`) for all of them?** Recommend **per-date
reconstructed records**. They keep the date grouping and let each date be
retired independently once verified.

**D6. Weekly-brief pages that cite `log.md`/`index.md`.** Recommend
`sources: []` plus `lifecycle: dated-digest`, with lint exempting dated digests
from the grounding check. Today lint's grounding check only fires when `srcs` is
non-empty, so an empty list already passes, but that is accidental and should be
made explicit.

**D7. Severity timeline.** Recommend 🟡 for R3/R6/R7 through the migration, then
🔴 for R3 and R6 in a 3.0.0. R7 stays 🟡: a citation that breaks the format but
still resolves is cosmetic, and one that no longer resolves is already an R3
error. The alternative (🔴 now) turns the session-start health line red
on day one for a known, scheduled backlog.

**D8. Public-repo hygiene (N12).** Two existing fork docs and one test file carry
real wiki identifiers. Recommend scrubbing them to placeholders in step 0 and
accepting that the strings remain in git history, or rewriting history if that
matters to you. Your call: history rewrite is destructive for anyone who forked.

**D9. `mcp__wiki-search__edit` on the allowlist after step 3?** Recommend
**no, not yet.** Snapshots make its writes recoverable, but every frontmatter or
`string_replace` edit can still damage other parts of the page (#47, #49).
Revisit once follow-on F2 or the step 12 patch fixes the round-trip. Keep `vault`
on ask in any case (it includes delete).

**D10. Upstream first or fork first?** Recommend offering steps 1–4 upstream
right away (bug fixes plus a refactor, low controversy), and opening an *issue*
for step 5's citation spec before a PR, since it changes the micro-capture
contract the author designed.

**D11. Run a locally patched copy of the MCP now (plan step 12)?** It stops new
timestamp dates at the source for about a day's work, but the patch has to be
re-applied and re-tested on any MCP upgrade, and it's fork-only. Recommend
**yes, if new timestamps keep appearing after step 5's Edit-tool rule**;
otherwise leave it to follow-on F2. It does not fix the bracket escaping (#47).

---

## 10. Follow-on work (after this design)

Two pieces of work were deliberately left out of this design. They are recorded
here so they aren't lost.

**F1. Orient content and `overview.md` freshness (separate design).**
`overview.md` only ever grows (70 KB), its action items and decisions are frozen
copies from meeting digests, and later updates never flow back into it, so Orient
loads stale and sometimes wrong information every session. The same design
covers what else Orient should load. The org chart kept in SCHEMA's Domain
section is weeks older than `concepts/relationship-map.md`, which Orient never
reads. The proposal is a pointer from SCHEMA to the map, plus Orient reading only
a compact org-chart section of it. Starting points: ISSUE-1, ISSUE-2, and I8's
revisit mechanism.

**F2. Fork `wirux/mcp-markdown-vault`.** The MCP's full-file round-trip causes
the bracket escaping (#47) and the timestamp dates (#49, N15), and its
maintainer has not responded since June 2026. The fork would be thin, on top of
upstream, with one fix per branch and a regression test in the project's vitest
suite: `CORE_SCHEMA` for #49 first, then text-preserving `frontmatter_set` and
`string_replace` for #47, and possibly #45 (orphaned server processes). Each fix
also goes back upstream as a pull request. `wiki-search.sh` then runs a pinned
build of the fork (a fork-only launcher difference). Costs: owning a
Node/TypeScript build and its dependency updates, and a small recurring merge fix
when upstream changes `wiki-search.sh`. Once it lands, the Edit-tool rule
(section 5.11, item 9) and D9's "keep on ask" can be retired. R12's auto-fix, the
escaped-bracket check and the MCP hook matchers stay as safety nets. Step 12, if
adopted, is superseded.

## Provenance of this document

Written from direct reading of every file named in section 2 in the fork at `c105625`:
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

---

## Appendix A. Root causes in plain terms

The same seven root causes as section 3, explained without the jargon.

### RC1. Sources have no identity

RC1 is about *how a source is named*.

**How it works today:** a wiki page mentions its sources in three places: the
list at the top of the page (`sources:`), the tags beside individual claims
(`[source: ...]`), and sometimes a Sources section at the bottom. Each place
accepts whatever text the writer chooses. The top list usually holds a file
path, the tags hold a shortened name, and the bottom section holds a sentence
of description.

**The problem:** nothing defines what a source *is*, and nothing turns any of
that text into a file you can open. So:

- The same kind of source gets written a dozen different ways.
- A typo in a path looks exactly like a real path, and nothing notices.
- To check whether a tag matches the list at the top, lint has to guess whether
  two pieces of text are "close enough" to mean the same thing.
- The three places drift apart, because nothing ties them together.

**The analogy:** it's like a library where books have no catalog numbers.
Every reference describes the book in its own words ("the pricing report",
"pricing, January", "that analyst PDF"), and finding the actual book depends on
someone guessing right.

**Why it's a root cause:** most of the other defects (the many shapes, the
split entries, the invented citation, the typo'd paths, the fuzzy matching)
come from accepting free text as a source. Fixing each one separately leaves
the door open for the next variant.

**What the design does:** every source gets a catalog number, which is simply
its filename. The same number is used in all three places, and a lookup either
finds exactly one file or reports an error (section 5.4). Because the number
can't contain commas or spaces, no file format can mangle it.

### RC2. The honest path for chat facts cost more than the shortcut

RC2 is about facts you tell the agent in chat, like "remember that we decided X".

**The rule:** every fact in the wiki should point back to a saved original, a
file in `raw/`, so anyone can check where it came from. For a chat fact, the
rule since v2.0.0 has been to save a summary of the conversation into `raw/`
first, then cite that file.

**The problem:** saving the conversation was only described inside the full
ingest procedure, a long checklist meant for articles, transcripts and similar
sources. Doing all of that for a single sentence was heavy. In v2.20.0 the
author added a shortcut for single facts (PLUGIN-REVIEW A13) that deliberately
skips the checklist. The shortcut says to label the fact
`source: conversation | <date>` and move on. It never says to save anything.

So the wiki offered two paths for the same situation:

- **The proper path** saves the conversation to a file, then cites it. It's
  slower, and it's buried in a long procedure.
- **The shortcut** writes "conversation, <date>" as the source and saves
  nothing. It's fast and sits right up front in the main instructions.

The agent naturally took the shortcut. The result is citations that look like
sources but point to nothing: no file exists for any of the 18 dates the wiki
cites conversations from. It's like a receipt that says "paid in cash, Tuesday"
with nothing to show what was bought.

**Why it got worse:** there was no single agreed way to write the shortcut
label, so it appears in several different forms, which is part of the 12
shapes. Written without quotes, some of those forms get split in two by the
frontmatter format. When a fact arrived in chat during an Update, one session
invented a raw-looking filename for it, which is the phantom citation. A later
fork fix (`32e42a3`) made "user, conversation, DATE" an officially allowed form
for Updates, which added yet another shape instead of closing the gap.

**Why it's a root cause, not just a bug:** telling the agent to "be careful"
won't fix it while the careless option is the easy one.

**What the design does:** it makes the honest option cheap instead (section
5.6). Saving a chat fact becomes one small file, written by a helper script in
a single step, and citing that file is the only accepted form. The shortcut
stays short, one step longer than today, and it no longer produces citations
that lead nowhere.

### RC3. No agreed format, three different readers

RC3 is about *how the information at the top of each page gets read*.

**How it works today:** that information (the frontmatter) is written in YAML,
a format that allows many ways to write the same thing. A list, for example,
can go on one line inside brackets or on separate lines with dashes. The tools
don't use a real YAML reader. Instead there are three homemade ones: two inside
lint and a copy inside the before-change hook.

**The problem:**

- No document says which of YAML's many forms a wiki page may use, so each
  homemade reader supports a different subset and guesses at the rest.
- A page that one reader accepts, another can misread without any warning.
  Mixed list styles and duplicated keys were both read "successfully" while
  whole fields silently disappeared.
- An earlier local patch (PATCH-3a) taught one reader to handle one-per-line
  lists by gluing the items back together with commas, which reintroduced the
  comma confusion another fix had just removed.
- Obsidian, which does use a real reader, sometimes disagreed with all three.
  That is how some of the corruption was found.

**The analogy:** it's like three clerks reading the same handwritten form, each
guessing differently at the unclear letters, and none of them ever saying
"I can't read this".

**Why it's a root cause:** as long as the readers guess, a malformed page can
pass every check while the data inside it is being lost.

**What the design does:** it writes down exactly which forms are allowed
(section 5.10), and every tool uses one shared reader. Anything outside the
allowed forms is reported instead of guessed at.

### RC4. The safety checks guard only some of the doors

RC4 is about *where the safety checks are attached*.

**How the checks work today:** the wiki's safety nets are hooks, small scripts
that run automatically around a change. One runs before a change: it saves a
backup copy and warns if a page has no sources. One runs after: it checks for
broken links. They're wired to three specific editing tools in Claude Code:
Write, Edit and MultiEdit. A hook fires only when one of those three tools is
used.

**The problem:** those three tools aren't the only way files change. At least
five other ways to modify the wiki slip past the hooks entirely:

- **The wiki-search MCP** can create, rewrite and delete files with its own
  tools. The hooks don't recognize them, so there's no backup and no check.
  That's why its write tools were left off the allowlist.
- **Shell commands and scripts.** A `mv`, a `sed`, or a one-off Python script
  like the page-splitting pass edits files directly.
- **Lint's own auto-fix** rewrites links and the index with no backup first.
- **Session start** runs lint, which quietly writes a report file into
  `queries/` every session (N1).
- **You, in Obsidian**, or git operations like checkout or merge.

There are also gaps in coverage by location:

- **`briefings/`**, where daily briefs go, sits outside the folders the hooks
  and lint look at (N2).
- **Pages named `README.md`** all get backed up under the same name, so all but
  the first one each day are lost (N14).

**The analogy:** it's like a building where the security guard checks badges at
the front door only, while there are side doors, a loading dock and windows.
The guard does a good job, just at one entrance.

**Why it's a root cause:** no matter how good the checks are, they only protect
changes that come through the watched door. Several of the corruptions found
earlier came through the unwatched ones.

**What the design does:**

- **More doors watched:** the hooks are extended to recognize the MCP's write
  tools (section 5.11), and `briefings/` joins the watched folders.
- **A check that looks at the file itself:** a new after-change check reads the
  file from disk after it changes, rather than trusting what the tool said it
  would do.
- **A regular sweep for the rest:** for the doors that can never be watched
  (shell, scripts, Obsidian, git), lint runs at every session start and reports
  rule violations. Nothing can change the wiki without being noticed by the
  next session at the latest.

It detects problems; it doesn't prevent them. The hooks still never block a
change, per the author's rule.

### RC5. No rules for pages made from other pages

RC5 is about *what a new page inherits when it's made from an existing one*.

**How it works today:** several operations create a page out of another page:

- **Splitting** a page that has grown past 200 lines.
- **Promoting** a person, company or product mentioned on a concept page to a
  page of their own.
- **Superseding** an old page with a new one.
- **Crystallizing** a meeting or research thread into a digest page.

**The problem:** none of these says which sources the new page should carry.
The easy move is to copy the whole source list across. So:

- Split-off pages claimed sources their text never used. The worst case listed
  22 sources while citing 3.
- One invented citation was copied along with everything else, into ten files
  including backup copies.
- Links pointing at a section that moves to a new page can stop leading anywhere
  useful, and nothing checks for it.

**The analogy:** it's like photocopying a book's full bibliography onto every
chapter, so each chapter claims to rely on sources it never mentions.

**Why it's a root cause:** these operations are exactly where errors multiply.
One mistake on a parent page becomes the same mistake on every child, and none
of it looks wrong, because every copied path is real.

**What the design does:** a written procedure for splits and the similar
operations (section 5.8). A new page lists exactly the sources its own text
cites (a lint helper computes the list), it records which page it came from,
and it gets a stricter check against copied source lists.

### RC6. Nothing ever comes back to check

RC6 is about *what happens to a citation after it's written*.

**How it works today:** every rule in the wiki applies at the moment of
writing: cite a source, show a diff, update the log.

**The problem:** once a citation or an action item is on a page, nothing ever
brings it back for review. There is no expiry date, no "last checked"
requirement, and no step in any workflow that revisits it. So:

- Things that were true when written quietly go stale.
- A secondhand fact looks just as solid a year later as a verified one.
- Mistakes that slip through at write time stay forever. In ISSUE-3, a source
  missing from one page's Sources section survived six later edits to that page.
- Action items in meeting digests stay frozen at "pending" long after they were
  resolved elsewhere (ISSUE-1).

**The analogy:** it's like groceries with no expiration dates. Everything in the
fridge looks equally fresh, and nothing tells you which items to check.

**Why it's a root cause:** write-time rules can only be as good as the
information available at that moment. Without a way back, the wiki's accuracy
can only decline.

**What the design does:** a revisit rule (R10, section 5.12). A page that rests
only on things said in conversation is flagged after 30 days unless someone has
re-checked it against a real source. The same idea could later apply to the
overview page's action items, which is left to the follow-on design.

### RC7. Copies of the same instructions drift apart

RC7 is about *guidance that exists in more than one place*.

**How it works today:** the same rules are written out in several places:

- two identical copies of the helper agents, one in the plugin and one in the
  wiki
- the page templates
- the wiki-search MCP's own settings file (`meta/contract.md`)
- the README and contributing guide
- sub-skills written before the rules they describe changed

**The problem:** when one copy is updated, the others aren't, and an agent that
reads a stale copy follows outdated rules. For example:

- The source-saving helper still applies a privacy label the plugin retired in
  v2.20.0 (N5).
- The PRD template teaches a citation form that lint can't read (N3).
- The wiki-search settings file describes a different page format altogether,
  and the MCP tells agents to follow it.
- Four different places (lint, the contributing guide, a helper agent and the
  MCP settings file) list four different sets of "required" fields (N4).

**The analogy:** it's like an office where the same procedure is pinned to four
different noticeboards and only one of them was updated. Whoever reads an old
notice follows the old procedure.

**Why it's a root cause:** fixing a rule in one place gives a false sense that
it's fixed everywhere, and the stale copies keep producing the old defects.

**What the design does:**

- **One home per rule:** each rule lives in `references/citation-spec.md`, and
  every other place points there instead of restating it.
- **One set of helper agents:** the two copies become one shared set.
- **Settings file rewritten:** the wiki-search settings file points at the
  wiki's own schema instead of describing its own.

---

## Appendix B. New findings in plain terms

The fifteen new findings from section 3 (N1–N15), each explained without the
jargon: what it is, what it costs, and how the plan fixes it.

### N1. Every session start writes a lint report

**What N1 is:** every time a Claude Code session starts, the session-start hook
runs lint to fill in the health line ("Health check: N issues…"). Lint is only
meant to report numbers back to the hook in that mode, but it also writes its
full report into the wiki as `queries/lint-<today>.md`. So opening a session
changes the wiki, even if you never touch it.

**The impact:**

- **The wiki keeps changing even when you don't.** Every day you open any
  session, a new report file appears or today's gets rewritten. The production
  wiki's `queries/` held 41 of them after about eight weeks, and 29 wiki commits
  include lint report changes. They show up in `git status` as work to commit,
  mixed in with real edits.
- **A manual lint run can be overwritten.** There's one report file per day. If
  you run lint yourself, especially with `--auto-fix`, and then start another
  session that day, the automatic run replaces your report. The record of what
  your run found or fixed is gone. Only the one-line summary in `log.md`
  survives.
- **Search results get noisier (likely, not tested).** The wiki-search MCP
  indexes every markdown file it finds. Lint excludes its own reports when
  checking the wiki, but the search index probably doesn't, so page names
  mentioned in dozens of reports can crowd search results.
- **It's a write nobody watches.** This is one of the side doors from RC4. The
  report is written by a script, so none of the hooks see it.

None of this damages page content. The reports are harmless in themselves; the
cost is clutter, noisy diffs, and the occasional lost manual report.

**The fix (plan step 6):** when lint runs in the hook's quick-check mode, it
returns its numbers and writes no file. A report only appears when someone
deliberately runs lint. Existing reports can stay as history or be cleared out.

### N2. Daily briefs live outside every check

**What N2 is:** the daily-maintenance sub-skill files each day's brief as
`briefings/YYYY-MM-DD.md`, then later moves old ones to `_archive/briefings/`
with a shell `mv`. But `briefings/` isn't one of the folders the hooks or lint
know about. They only look at `entities/`, `concepts/`, `comparisons/` and
`queries/`.

**The impact:**

- **No backup before a brief changes.** The before-change hook ignores the
  folder, so editing or rewriting a brief leaves no copy in `_archive/`.
- **No checks after.** Broken links, missing sources and bad frontmatter inside
  a brief are never reported.
- **Links to briefs can't be checked.** Lint doesn't know briefs exist, so it
  would report a link to one from a content page as broken even when it's
  correct. The production wiki's only link to a brief sits in `index.md`, which
  lint doesn't check for broken links, so the problem hasn't surfaced yet.
- **The archive move is unwatched too.** Rotating briefs into
  `_archive/briefings/` is a shell command, another side door from RC4.

**The fix (plan steps 3 and 6):** `briefings/` joins the folders the hooks watch
and lint scans, and brief names become valid link targets.

### N3. The docs teach citations lint can't follow

**What N3 is:** three places in the plugin's own templates and guides show
citation formats that the checking tools can't match to anything:

- **A wikilink inside a citation** (`[source: [[wiki-page]]]`), shown in the PRD
  template. Lint's citation reader stops at the first closing bracket, so it
  sees only `[[wiki-page` and can't match it.
- **A wikilink to a raw file** (`per [[raw/articles/...]]`), shown in the update
  guide and the output-formats guide. Lint only knows page names, so it would
  report this as a broken link, an error.
- **A web address as the source** (`[source: <url>, <date>]`), shown in the CRM
  and research sub-skills. A web address isn't a saved file and can't be matched
  to a `sources:` entry.

**The impact:**

- **Following the instructions produces errors.** An agent that copies the
  template exactly gets citations that lint reports as broken or unresolvable.
  The agent did nothing wrong; the template is inconsistent with the checker.
- **It undermines trust in lint.** Once reports include warnings caused by the
  official templates, people learn to ignore them, and real problems get
  ignored along with them.
- **Mostly a future cost so far.** These forms are rare in the production wiki
  today (a handful), but every PRD, CRM enrichment or research sprint that
  follows the templates adds more.

**The fix (plan steps 5 and 6):** the templates and guides are updated to the
one citation format (section 5.4) and point at the single spec. Lint's R7 then
flags any leftover old-style citation by name, with an automatic fix for the
simple cases.

### N4. Four different lists of required fields

**What N4 is:** four places each say which fields every page must have at the
top, and they disagree:

- **Lint** requires title, created, updated, type, tags and sources.
- **The contributing guide** lists title, type, tags, sources, updated and
  coverage. It adds `coverage` and leaves out `created`.
- **The link-checking helper agent** checks only title, type, tags and updated.
- **The wiki-search MCP's settings file** (`meta/contract.md`) lists title,
  tags, type, created, updated and a `status` field, with no sources at all.

**The impact:**

- **"Complete" depends on who you ask.** A page can pass one check and fail
  another. An agent that follows the contributing guide leaves out `created`,
  and lint then reports an error.
- **The MCP's version is actively misleading.** The MCP tells agents to read its
  settings file for page conventions, so an agent writing through the MCP is
  pointed at a schema with no `sources` field at all.
- **Fixes don't stick.** Correcting one list leaves the other three to keep
  steering agents the old way (RC7).

**The fix (plan steps 2, 4 and 8):** one definition of the required fields,
enforced by lint (R12, section 5.10). The contributing guide and the helper
agent are corrected to match, and the MCP's settings file is rewritten to point
at the wiki's own schema.

### N5. The source-saving helper still uses a retired privacy label

**What N5 is:** the helper agent that saves web pages and pasted text into
`raw/` (K1) still writes `private: true` or `private: false` at the top of each
file it saves. It also tells the main agent to mark resulting wiki pages
`private: true`. The plugin retired that label in v2.20.0. Every page is now
private automatically, and only pages marked `shareable: true` can be exported.
The v2.20.0 cleanup missed this helper.

**The impact:**

- **A false sense of protection.** The label looks like a privacy control but
  nothing reads it, so it gives someone reading the file the wrong idea about
  what keeps it private.
- **It has already spread.** 14 saved records in the production wiki carry the
  label.
- **The helper's filing rules also disagree with the ingest guide.** It names
  and describes saved files differently from the main ingest guide, so the same
  kind of source ends up filed differently depending on who saved it. Under this
  design a filename becomes a permanent citation ID, so one rule matters.

No private information has leaked because of it; the export rule is unaffected.

**The fix (plan step 2):** remove the label from the helper, and replace its
filing table with a pointer to the ingest guide. The 14 existing records stay as
they are, since saved records are never edited.

### N6. The wiki-search tool can change a date's type

**What N6 is:** a date written with quote marks, like `'2026-09-14'`, is
text. Without the quote marks, `2026-09-14`, some YAML readers (including
PyYAML, the one Python tools usually use) treat it as a real date value instead
of text. One commit in the wiki shows a quoted date losing its quotes. At first
this was blamed on the wiki-search MCP, but testing its actual code showed it
keeps quoted dates quoted, so the writer of that one change is unconfirmed. (The
MCP damages *unquoted* dates in a different way; that's N15.)

**The impact:**

- **Harmless today.** The wiki's own tools read these values as plain text
  either way, and the dates themselves are unchanged.
- **A trap for later.** Any tool that reads the files with a standard YAML
  library, including a future version of lint, gets text for some pages and
  date values for others. Comparisons and string handling can then fail in
  confusing ways.
- **Rules about quoting can't be relied on.** Quotes can be lost without anyone
  noticing, so a rule that says "this value must be quoted" isn't a safe
  foundation.

**The fix (plan step 4):** the single shared reader treats every value as text
and checks dates by their pattern, so it doesn't matter whether a date is quoted.

### N7. Citations written in ways no tool can follow

**What N7 is:** measuring all 1,070 inline citations in the production wiki
turned up a set of defects beyond the ones already known:

- **9 are broken across a line inside the source name**, so the name is split in
  two.
- **8 contain a doubled prefix** (`source: source: ...`).
- **5 cite two sources joined by "vs."** instead of the separator the format
  uses.
- **6 cite a structural file**, such as the schema page, instead of a source.
- **4 are free prose** rather than a source name.
- **2 cite a script file.**
- **1 wraps a wikilink.**

That's 35 in total. Separately, 55 citations run across more than one line; many
of those still work, but they're fragile.

**The impact:**

- **Readers can't trace those claims.** A citation that doesn't name a real
  source gives no way to check the claim it supports.
- **Noise in lint's reports.** These show up among the missing-citation reports
  (R3), mixed in with real gaps, which makes the real ones harder to spot.
- **They can't be fixed by guessing.** The current lint matches loosely to avoid
  false alarms, which also means it can't point at exactly what's wrong.

**The fix (plan steps 6 and 10):** the new format rule (R7) names each of these
defects specifically. Lint repairs the mechanical ones automatically (line
breaks, doubled prefixes, "vs."), and the migration hands the rest (13 citations)
to a person to fix.

### N8. A sub-skill still claims a gate is enforced

**What N8 is:** the plugin review (PLUGIN-REVIEW A7) found that the core skill
described its "orient first" rule as *enforced*, with the agent refusing to
write until it had read the key files. Nothing actually enforced that. The core
skill was relabeled as a checklist in v2.20.0, but the PRD sub-skill still says
"Orient gate (enforced): … refuse any write".

**The impact:**

- **It overstates what's guaranteed.** Anyone reading the PRD sub-skill would
  think writes are blocked until orientation happens. They aren't.
- **It can make the agent behave inconsistently.** The same rule reads as a hard
  gate in one skill and a checklist in another.
- **Small, but it's the pattern the review set out to remove.** Guardrails that
  claim to fire but can't are exactly the problem PLUGIN-REVIEW named.

**The fix (plan step 2):** a one-line change to match the core skill's checklist
wording.

### N9. The link-checking helper would report hundreds of false breaks

**What N9 is:** the link-checking helper agent checks each `[[link]]` by looking
for the target in `entities/`, `concepts/` and `comparisons/`. It never looks in
`queries/`, where digests, research and filed answers live.

**The impact:**

- **Hundreds of false alarms.** The production wiki has 411 links into
  `queries/` across 138 pages. Every one would be reported as broken.
- **Real problems get buried.** A genuinely broken link would be lost in that
  list.
- **Latent so far.** The helper only runs when asked, and lint (which does check
  `queries/`) is what normally reports broken links, so this hasn't caused
  visible trouble yet.

**The fix (plan step 2):** the helper uses lint's link check instead of keeping
its own, so there's one definition of a valid link.

### N10. Two saved sources share a name with their original file

**What N10 is:** when a PDF or slide deck is saved, the original goes in
`raw/assets/` and an extracted text version goes in another `raw/` folder. In two
cases the text version and the original have the same name apart from the file
extension.

**The impact:**

- **Harmless today.** Nothing currently uses the bare name to find a file.
- **A potential ambiguity under the new rules.** This design uses a file's name,
  without the extension, as its citation ID. Without a rule, those two names
  would each point at two files.

**The fix (plan step 5):** the ID rule (section 5.1) counts only text records
and excludes `raw/assets/`, so the original file is reached through its text
record and each ID points at exactly one file. No files need to change.

### N11. Some saved sources lack details, and two are unused

**What N11 is:** 11 of the 153 saved text records in `raw/` have no information
block at the top: no capture date, source type or original location. Separately,
2 of the 156 files in `raw/` aren't referenced by any page.

**The impact:**

- **Weaker provenance for 11 records.** Without a capture date or origin, it's
  harder to judge how current or reliable they are, or to find the original
  again.
- **Two sources saved for nothing (so far).** Either an ingest stopped partway,
  or they're waiting to be used. Either way, nothing in the wiki draws on them.
- **Small in scale.** Most records are complete and nearly all are used.

**The fix (plan step 6, partly):** a new rule (R13) requires the key details on
records saved *after* it ships. Existing records are left alone because saved
records are never edited. The design doesn't address the two unused files; they
can be cited or left as they are.

### N12. Private wiki names appear in the public fork

**What N12 is:** the fork is public on GitHub, but three files in it contain
names from the private wiki: a test file uses a real page name and a real
citation string, and two earlier fork-chgs documents quote real page names and
citations as examples.

**The impact:**

- **Private information is publicly readable.** Anyone browsing the fork can
  see names of customers, colleagues or internal projects that were meant to
  stay in the private wiki.
- **It's already in git history.** Scrubbing the files stops it being visible in
  current versions, but the old versions stay reachable unless the history is
  rewritten.
- **It goes against the plugin's own practice.** The upstream author scrubbed
  real names from distributed files in v2.20.0 for this reason.

**The fix (plan step 0):** replace the names with placeholders. Whether to also
rewrite git history is open decision D8, because a history rewrite causes
problems for anyone who has already copied the fork.

### N13. The wiki-search launcher logs a false error

**What N13 is:** the script that starts the wiki-search MCP first looks for a
`.wiki-path` file in the current folder. It reads the file in a way that makes
the shell itself complain when the file doesn't exist, before the script's
"ignore errors" handling can take effect. So every session started in a folder
without `.wiki-path` logs "No such file or directory". This was reproduced
directly.

**The impact:**

- **It looks like a failure when nothing failed.** The launcher carries on
  correctly and falls back to the next way of finding the wiki.
- **It wastes troubleshooting time.** Anyone investigating a real connection
  problem sees this message first in the MCP's logs and may chase the wrong
  cause.
- **It slipped through because there was no test.** It was introduced by the
  v2.20.0 fix for PLUGIN-REVIEW A11, whose requested smoke test was never
  written.

**The fix (plan step 1):** check whether the file exists before reading it, as
the session-start hook already does, and add the smoke test A11 asked for
(section 5.13).

### N14. All README pages share one backup name

**What N14 is:** some wiki pages are folders, like a PRD or a research sprint,
whose main page is called `README.md`. The before-change hook names each backup
after the file's name, so every one of these pages is backed up as
`_archive/README-<date>.md`. The hook also makes only one backup per name per
day.

**The impact:**

- **Lost backups.** If two folder-style pages are edited on the same day, only
  the first gets a backup; the second is silently skipped.
- **Unlabeled backups.** A backup named `README-<date>.md` doesn't say which page
  it came from. The production wiki has 4 folder-style pages and one such backup
  file, whose origin isn't recorded.
- **Undo doesn't work for them.** Recovering one of these pages means digging
  through git, which only helps if the change was committed.

**The fix (plan step 3):** name backups by the page's real name (the folder name
for a `README.md`), the same way lint already names pages. Each backup then
points at exactly one page.

### N15. Some dates are stored in a format the checks can't read

**What N15 is:** dates at the top of a page are normally written as
`2026-09-03`. On 13 pages some dates are written as full timestamps instead,
`2026-09-03T00:00:00.000Z`: 13 creation dates, 3 last-verified dates and 1
last-updated date.

**The cause is confirmed.** When the wiki-search MCP changes a page's
frontmatter, it reads the whole block and writes it back using a library
(js-yaml) whose default setting treats an unquoted date as a date and writes it
back as a timestamp. That was reproduced with the MCP's own copy of the library.
The timestamps arrived in four separate commits, so it keeps happening. It's the
same "rebuild the whole file" behavior that escapes brackets (PATCH-3d, upstream
issue #47). It has been reported to the MCP's maintainer as issue #49, who has
not responded to anything since June 2026.

**The impact:**

- **Staleness checks silently skip them.** Lint and the session-start scan use a
  Python date reader that, on the Python version on this machine, rejects the
  trailing `Z`. The error is swallowed, so the check is simply skipped with no
  message.
- **Pages that can never go stale.** The page with a timestamp `updated` date will
  never appear in the stale-pages list, and the three with timestamp
  `last_verified` dates will never be flagged for re-verification, however old
  they get.
- **The creation dates are harmless for now.** Nothing checks `created` except
  that it exists, so those 13 values cause no visible problem today.
- **It supports not trusting `last_verified`.** A date that no check can read gives
  a false sense that the page has been looked after.

**The fix:** the minimum workarounds now, a real fix later.

- **Avoid it (plan step 5):** change frontmatter with the Edit tool, not the
  MCP (section 5.11, item 9).
- **Catch and heal it (plan steps 4, 6 and 7):** the shared reader checks every
  date against the `YYYY-MM-DD` pattern and reports anything else (R12). The
  post-write check reports it in the same turn, and lint `--auto-fix` turns a
  midnight timestamp back into a plain date.
- **Clean up (plan step 10):** the migration rewrites the 17 existing values.
  That's lossless, because every one has a time of exactly midnight.
- **Optionally stop it at the source (plan step 12):** run a pinned local copy
  of the MCP patched to read dates as text (D11).
- **Fix it properly later (follow-on F2):** fork the MCP.

