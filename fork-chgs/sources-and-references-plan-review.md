# Sources and References Plan Review

created: 2026-09-29

Audit of the implementation plan (section 8) in the
[Sources and References Design](sources-and-references-design.md) against the
design's proposed changes, the findings of the
[Sources and References Review](sources-and-references-review.md), and the
current code. It lists 29 issues, each with a proposed design edit, and maps
every proposed change and every review finding to the step that implements it.

Reviewer: the session that implemented step 1.

Status: all 29 issues accepted on 2026-09-29, with the recommended answer to each
open decision, and applied to the design, its appendices and the implementation
prompt. Each edit there is marked "(plan review Pn)".

Scope: the design and its appendices at `556d1b4` (step 1 done); the review; the
[Sources and References Implementation Prompt](sources-and-references-implementation-prompt.md);
the fork's code at the same commit; the hook registrations and permission rules in
`~/.claude/settings.json`; the installed MCP (`@wirux/mcp-markdown-vault` 2.3.0,
npx cache). Steps 0 and 1 are done, step 12 is dropped, and section 10's
follow-on work is out of scope. No wiki measurements were taken: counts come from
the design and the review.

Why: step 1 found design text that contradicted the code. Section 5.13 said the
fix mirrored a `-f` test in `session-start.sh` that doesn't exist, and its snippet
dropped `|| true`, which would have stopped the launcher when `.wiki-path` exists
but can't be read.

Labels: P1–P14 are this review's issues. F1–F16 are the design review's findings.
All other IDs (I, R, M, N, D, NW, W, V, …) are the design's own.

Severity: **High** means a step implemented as written would weaken an existing
guarantee or keep producing the defects the design removes. **Med** means a step
leaves out part of a proposed change, would have to guess, or has a side effect
the design doesn't state. **Low** means a correction, a missing pointer, or
bookkeeping.

---

## Summary

The plan covers almost all of section 5, and every review finding is traced into
the design with its recommended fix. Where a finding offered options, the review's
status line records the one the design took. The problems sit at the edges of the
steps:

1. **Two guidance sites keep teaching the citation shapes the design removes.**
   ingest-guide ① still prescribes the daily conversation file and `user, <date>`
   attribution, and the CRM and research enrichment procedures cite URLs they
   never capture. Step 5's file list names neither (P9, P10).
2. **R12 starting at 🟡 would demote two of today's 🔴 errors**, missing
   frontmatter and missing required keys (P15).
3. **Several proposed changes have no step:** the grounding redefinition and D6's
   exemption, `briefings/` in lint, R4 after R3's rewrite, R10's `_status.md`
   list, post-validate's registration, and writing the migration script itself
   (P16–P18, P21, P23, P26).
4. **Some steps use something a later step builds:** the link-validator needs
   lint's side-effect-free `--json` (step 6), step 5's docs name
   `--cited-sources` (step 6), and M7 needs the contract template (step 8)
   (P1, P13, P26).
5. **Five design statements don't match the code:** step 4 isn't behavior-neutral,
   research's stub enrichment doesn't capture records, the warehouse fields are
   already record fields, `backlinks.py` has no parser to replace, and the
   link-validator's orphan command calls a flag `backlinks.py` doesn't have
   (P6, P10, P14, P7, P1).

Counts: 2 High, 12 Med, 15 Low.

Decisions (all taken as recommended): the shared snapshot function lives in
`lint.py` (P2); MCP `vault` calls get an `ask` rule (P5); `capture.py` picks the
next free suffix for a repeated topic (P12); filed briefs stay out of `index.md`
(P16); a missing page path still counts as secondary for grounding (P17); and
`post-write.sh` stays in the repo, unregistered (P23).

---

## Issues by plan step

### Step 2

#### P1. The link-validator can't defer to lint until step 6

- **Severity:** Med
- **Steps:** 2, 6
- **Design:** 5.9, 5.10 (required keys), N4, N9
- **What's wrong:**
  - Step 2 fixes the "worker-link-validator resolver", and 5.9 says the validator
    "defers to `lint.py`". But lint writes `queries/lint-<date>.md` on every run
    and appends to `log.md` outside `--json` mode (`lint.py:711-780`), while the
    validator's rules say "Do not modify any files". `--json` stops writing the
    report only in step 6 (N1).
  - The validator's orphan check runs `backlinks.py "$WIKI" --all-orphans`, a flag
    `backlinks.py` doesn't have. The script then fails on the missing slug
    argument.
  - Its "Missing frontmatter" check uses 4 required keys, N4's second definition.
    5.10 says the validator is "corrected to match", but step 2's row names only
    the resolver.
  - Lint's JSON carries broken links, orphans and counts, not the index gaps and
    missing fields the validator reports.
- **Why it matters:** done in step 2 as written, every validator run writes a lint
  report and a log entry into the wiki. Left alone, its orphan check fails and its
  field list disagrees with lint.
- **Proposed edit:** move the validator item from step 2 to step 6: "The
  worker-link-validator runs `lint.py --json` for broken links, orphans, index gaps
  and missing fields, and drops its own resolver, the `--all-orphans` call and its
  field list. Lint's JSON adds the index-gap and missing-field lists."

### Step 3

#### P2. The snapshot function has no importable home

- **Severity:** Med
- **Steps:** 3, 6, 10
- **Design:** 5.11 items 3 and 8, I7, M1
- **What's wrong:** 5.11 item 8 says lint `--auto-fix` "imports the snapshot
  function", and M1 snapshots every page the migration touches. Today the snapshot
  is a few lines inside `pre-write.sh`'s embedded Python (`pre-write.sh:54-63`),
  which nothing can import. Item 3 names snapshots with "`lint.py`'s `slug()`", so
  the hook will import `lint.py` anyway. No step says where the shared function
  goes.
- **Why it matters:** steps 3, 6 and 10 would each write their own copy, which is
  the drift RC7 describes.
- **Proposed edit:** step 3: "Move the snapshot into `snapshot(page, wiki)` in
  `lint.py`, next to `slug()`. `pre-write.sh` imports both, and step 6's auto-fix
  and M1 import the same function." Step 4 may later move both into `wikifm.py`.
- **Decided:** `lint.py`.

#### P3. Step 3's live check would write to the private wiki

- **Severity:** Med
- **Steps:** 3
- **Design:** 5.11 item 1 ("Unverified"), step 3 row
- **What's wrong:** step 3 lists "`tests/test_write_hooks.py` incl. a live check
  that a PreToolUse hook fires on an MCP call". A pytest test can't make an MCP
  call through Claude Code, so the live check has to be manual. An MCP write also
  lands in whatever vault the server was started with, which in a normal session
  is the private wiki, and the implementation prompt allows only step 10 to write
  there.
- **Proposed edit:** "Live check (manual): start a session whose `.wiki-path`
  points at a scratch wiki, so the hooks and the MCP resolve the same path. Call
  `vault.create`, then `vault.update`, on a scratch page. Confirm the snapshot
  appears, and that the deny rule refuses an `edit` call. Record the result in the
  design's 'Not verified' list. `tests/test_write_hooks.py` covers MCP payloads
  with synthetic stdin JSON."

#### P4. The `vault` filter skips `create_from_template`

- **Severity:** Low
- **Steps:** 3, 7
- **Design:** 5.11 items 1, 5 and 6, F13, V1
- **What's wrong:**
  - Item 1 says the hooks "act only on `vault` `create`, `update` and `delete`".
    The `vault` tool has a seventh action, `create_from_template`, which writes a
    new file (`mcp-tools.js:123-140`); V1 lists it as a writer. Post-validate
    would skip pages created that way.
  - Item 5 says MCP `edit` ops aren't simulated, but doesn't say what the freshness
    gate does for `vault.create` and `vault.update`, whose payload carries the
    whole post-image in `content`.
- **Proposed edit:** item 1: "act only on `create`, `create_from_template`,
  `update` and `delete`". Item 5: "`vault.create` and `vault.update` are judged
  like Write, from `content`. `create_from_template` is checked after the write,
  by post-validate."

#### P5. D9's `ask` rule for `vault` is undecided

- **Severity:** Low
- **Steps:** 3
- **Design:** 5.11 permission note, D9, F4
- **What's wrong:** D9 says to add an explicit `permissions.ask` entry "if MCP
  writes should always prompt". Step 3's row adds only the deny rule.
  `~/.claude/settings.json` has `defaultMode: "auto"` and no `ask` or `deny`
  rules, so without the entry a `vault.delete` is decided by auto mode.
- **Proposed edit:** decide in step 3 and record it in D9: either "add `ask` for
  both name forms of `vault`" or "no `ask` rule; auto mode decides `vault`
  writes".
- **Decided:** add the `ask` rule. Permission rules match on the tool name, so
  it also prompts on `vault` reads, which agents rarely make (reads go through
  `view`).

### Step 4

#### P6. Step 4 changes health counts, so it isn't a pure refactor

- **Severity:** Med
- **Steps:** 4
- **Design:** section 8 "Upstream conflict surface", 5.10, F2
- **What's wrong:** the conflict-surface note says "land step 4 first as a pure
  refactor (no behavior change, all existing tests green)". Step 4 also carries
  F2's fix. Once lint and session-start read dates through `wikifm`,
  single-quoted dates stop being skipped. Lint's 90-day check
  (`lint.py:582-593`) starts reading `updated` on about 115 more pages, and
  session-start's stale count rises (it reported 49 against 66 real on
  2026-09-28).
- **Why it matters:** an implementer holding to "no behavior change" would keep
  the quote bug or stop and ask. A reviewer seeing the health line jump would
  suspect a regression.
- **Proposed edit:** "Land step 4 as a refactor with one intended behavior change,
  the date-quote fix (F2). Record lint's and session-start's counts before and
  after on a scratch copy of the wiki." Optionally commit the F2 part separately.

#### P7. Step 4's deletions and the tests that call them

- **Severity:** Low
- **Steps:** 4, 6
- **Design:** section 6 (`543766c`, `91878dc`), 5.10 callers, 5.15 R1/R2/R5,
  appendix N4
- **What's wrong:**
  - Deleting `extract_sources` breaks three tests in `tests/test_lint.py` (the
    quote-aware split from `543766c`). Section 6 says they "become R6 migration
    tests", but R6 is step 6.
  - Section 6 says R1/R2/R5 are "kept as messages of the profile parser (step 4)".
    5.15 says R1 and R2 become messages of R12, which is step 6. Appendix N4's fix
    places R12 in step 4.
  - Step 4 switches `backlinks.py` to `wikifm`, but `backlinks.py` has no
    frontmatter parser.
- **Proposed edit:** step 4: "Rewrite the three `extract_sources` tests against
  `wikifm.sources()` with the same expectations. `wikifm.parse` reports the
  R1/R2/R5 conditions, and lint keeps their messages and 🔴 tier; step 6 folds
  them into R12's report." Drop `backlinks.py` from step 4 and from 5.10's caller
  list. Appendix N4: "(plan steps 2, 4, 6 and 8)".

#### P8. The whole-wiki test and the PyYAML oracle need a setup rule

- **Severity:** Low
- **Steps:** 4
- **Design:** 5.10 Tests, F8
- **What's wrong:** "A further test runs `parse` over every page of a scratch copy
  of a real wiki." The repo holds no wiki, and the private wiki stays out of the
  fork, so the test needs an opt-in path. The oracle tests need PyYAML, and
  README's test recipe installs only pytest.
- **Proposed edit:** "The whole-wiki test reads its path from an environment
  variable (for example `WIKIFM_WIKI`) and skips when it's unset. Step 4 runs it
  once against a scratchpad copy and records the page count. The oracle tests use
  `pytest.importorskip("yaml")`, and README's recipe adds `pyyaml`."

### Step 5

#### P9. ingest-guide ① still teaches the daily conversation file

- **Severity:** High
- **Steps:** 5
- **Design:** 5.6, D1, section 4 (option A), the list at the top of section 5
- **What's wrong:** section 5 lists the places reduced to a pointer, including
  "ingest-guide ⑤", and step 5 adds ⑫. Neither covers ①'s "Current
  conversation" bullet (`ingest-guide.md:38-43`): "Save a summary to
  `raw/internal/conversation-<YYYY-MM-DD>.md`" and "User-stated facts: attribute
  as `user, <date>`". That is option A's daily file, which D1 rejected because it
  mutates `raw/`, plus a citation shape R3 and R6 will flag.
- **Why it matters:** the full-ingest path would keep producing the records and
  citations the migration removes.
- **Proposed edit:** add to step 5 and to section 5's list: "ingest-guide ①
  'Current conversation': capture each topic with `capture.py` (5.6); tool-retrieved
  facts follow their own routes."

#### P10. CRM and research enrichment cite URLs without capturing them

- **Severity:** Med
- **Steps:** 5
- **Design:** 5.7, D2, N3
- **What's wrong:** 5.7 says "The CRM and research enrichment steps delegate
  capture to `worker-source-fetcher`, which research already does." Research
  delegates in its sprints (`llm-wiki-research/SKILL.md:68,151`), but its
  stub-enrichment pass searches the web and cites `[source: url, date]` with no
  capture (`:180-197`). CRM's company enrichment does the same with
  `[source: <url>, <date>]` (`llm-wiki-crm/SKILL.md:101-105`). Step 5's row says
  "prd/crm/research templates", but these are procedure steps in the two SKILL.md
  files, and they need a new capture step, not a pointer.
- **Why it matters:** under D2 every such citation is an R7 finding, and the
  procedures would keep producing them.
- **Proposed edit:** step 5: "llm-wiki-crm §2 company enrichment and
  llm-wiki-research's stub enrichment: fetch each source used through
  `worker-source-fetcher`, declare the record's path, and cite its ID." In 5.7,
  replace "which research already does" with "as research's sprints already do".

#### P11. Step 5's file list leaves out places section 5 changes

- **Severity:** Med
- **Steps:** 5
- **Design:** 5.2–5.4, 5.8, section 1 (I5, I7), section 8 size estimate, N3
- **What's wrong:** a session implementing step 5 from its row would miss:
  - **N3's sites:** `update-guide.md:77` (`(per [[raw/…]])`),
    `update-guide.md:84-96` (the `ae33f9d` block, whose "capture it, then cite
    the file" example uses the path form R7 rejects), `output-formats.md:89-90`
    (`[[raw/…]]` in a deck's sources appendix), and `prd-templates.md:91`
    (`[source: [[wiki-page]]]`).
  - **SCHEMA template:** its Grounding section counts "`raw/`, `external/`, web,
    or a captured conversation" as primary sources (`templates/SCHEMA.md:303-305`),
    where 5.3 makes primary mean "resolves to a record". Its `sources:` example is
    flow style (`:34`), where 5.3 says templates show block style.
  - **SKILL.md:** the References list (add `citation-spec.md`), the Scripts list
    (add `capture.py`), and the §4 snapshot sentence. Section 8's size estimate
    counts all three.
  - **AGENTS.md:** relabel "Snapshot before destructive ops" as the rule for the
    paths the hook can't see (section 1), and point "No raw/ mutations" at
    citation-spec's Records section (I5).
- **Proposed edit:** replace step 5's "pointers from …" clause with an explicit
  file list that adds these entries to the existing ones.

#### P12. `capture.py`'s location, tests and repeated-topic rule

- **Severity:** Low
- **Steps:** 5, and 10 for `migrate_sources.py`
- **Design:** 5.6, section 7
- **What's wrong:**
  - The design names `scripts/capture.py` and `scripts/migrate_sources.py`. The
    repo has a root `scripts/` folder (`update-safe.sh`) as well as
    `skills/llm-wiki-pm/scripts/`. Both new scripts import `wikifm`, so they
    belong in the second.
  - No step names tests for either script.
  - 5.6 says a later fact on the same topic gets "a `-2` suffix" and that
    `capture.py` "refuses to overwrite". It doesn't say whether `capture.py`
    picks the suffix or makes the agent retry.
- **Proposed edit:** "`skills/llm-wiki-pm/scripts/capture.py` picks the next free
  suffix, never overwrites, and prints the path and ID. Tests go in
  `tests/test_capture.py`." Use the same folder for `migrate_sources.py`.
- **Decided:** the script picks the suffix.

#### P13. Step 5 documents a flag that step 6 adds

- **Severity:** Low
- **Steps:** 5, 6
- **Design:** 5.8
- **What's wrong:** step 5 writes the split procedure and its pointers ("set each
  page's sources with `lint.py --cited-sources`"), but `--cited-sources` is in
  step 6, which depends on step 5.
- **Proposed edit:** move `--cited-sources` into step 5, since it needs only
  `wikifm` from step 4, or state that steps 5 and 6 land together.

#### P14. The warehouse fields are already record fields

- **Severity:** Low
- **Steps:** 5
- **Design:** 5.7 (Warehouse)
- **What's wrong:** 5.7 says "the existing `source_query_ref`/`source_snapshot`
  fields move from page frontmatter guidance to the record". The only guidance for
  them (`ingest-guide.md:25-37`) already puts them on the snapshot record. No
  page-frontmatter guidance mentions them.
- **Proposed edit:** "The existing `source_query_ref`/`source_snapshot` fields
  stay on the record, as ingest-guide ① already prescribes."

### Step 6

#### P15. R12 at 🟡 would demote two existing 🔴 errors

- **Severity:** High
- **Steps:** 6, 11
- **Design:** 5.10, 5.15 R12, I1, D7, F3
- **What's wrong:** 5.15 says R12 covers "a required key missing" and "replaces the
  key-presence check", and I1 puts a missing frontmatter block under the profile
  too. R12 starts at 🟡. Today both are 🔴 (`lint.py:452-465`: "missing
  frontmatter" and "frontmatter missing [...]"), and lint-guide calls the required
  fields "Non-negotiable". F3's reason for 🟡 was only the 13 pages with timestamp
  dates.
- **Why it matters:** from step 6 until step 11, a page with no `sources:` key or
  no frontmatter at all would drop from 🔴 to 🟡.
- **Proposed edit:** 5.15 R12: "Missing frontmatter and missing required keys stay
  🔴, as today and as for R1, R2 and R5. The other profile messages (date form,
  value shapes) start at 🟡." Change step 6's row to match.

#### P16. `briefings/` in lint: not in step 6, and it would fill `index.md`

- **Severity:** Med
- **Steps:** 6, 7
- **Design:** 5.2, 5.9, N2 and its appendix fix, PATCH-3c disposition, R9
- **What's wrong:**
  - Appendix N2's fix names step 6 for lint scanning `briefings/`, and PATCH-3c's
    disposition says "extend the same registration to `briefings/`". Step 6's row
    doesn't mention it.
  - If briefs join lint's page set, the index-completeness check
    (`lint.py:656-695`) has no `dated-digest` exemption, unlike the orphan check.
    Plain `--auto-fix`, which the maintain loop runs unattended, would then add
    every filed brief to `index.md`, in a section chosen by its `type` (`## Entities`
    by default).
  - Post-write's resolver (`post-write.sh:77-79`) and `backlinks.py`'s folder list
    skip `briefings/` too.
- **Why it matters:** either briefs stay invisible to lint and the link checks, or
  the daily loop starts rewriting `index.md` with no review.
- **Proposed edit:** step 6: "`briefings/` joins lint's page set (link targets,
  R9, escape checks). Pages with `lifecycle: dated-digest` are exempt from the
  index-completeness check and its auto-fix." Step 7's resolver uses lint's page
  set.
- **Confidence:** medium. The design may have meant link-target registration only
  (as PATCH-3c does for `overview.md`); the proposed edit works for either.
- **Decided:** filed briefs stay out of `index.md`. The two it links today can
  stay.

#### P17. The grounding redefinition and D6's exemption have no step

- **Severity:** Med
- **Steps:** 6
- **Design:** 5.2, 5.3, D6, 5.14
- **What's wrong:** 5.3 redefines grounding on resolved IDs ("primary = resolves
  to a record; secondary = resolves to a page"), and D6 makes lint exempt dated
  digests from grounding explicitly. Neither is in step 6's row. Implemented
  literally, the redefinition also breaks three `TestLint` tests in
  `tests/test_hooks.py`, whose only source is `concepts/other.md`, a page the
  tests never create. It would resolve to nothing rather than count as secondary.
  5.14 keeps `test_hooks.py` untouched.
- **Proposed edit:** add both to step 6: "Grounding classifies each entry by what
  it names: a record path is primary, and a page path is secondary whether or not
  the page exists (R6 reports a missing file separately). Pages with
  `lifecycle: dated-digest` are exempt."
- **Decided:** a missing page path counts as secondary.

#### P18. R4 loses its matcher when R3 becomes exact

- **Severity:** Med
- **Steps:** 6
- **Design:** 5.4, 5.15 R4
- **What's wrong:** R4 counts a source as cited using `_citation_matches_source`
  (`lint.py:369-377`), a substring match. 5.4 deletes that function in R3's
  rewrite, and 5.15 says R4 "Exists, kept". Nothing says what R4 matches on
  afterwards.
- **Proposed edit:** step 6 and 5.15: "R4 counts a source as cited when a marker's
  ID equals its `slug()`." Its counts will change, since the substring match also
  counted partial and conversational hits, so record them before and after on a
  scratch copy.

#### P19. `--cited-sources` is under-specified

- **Severity:** Med
- **Steps:** 6
- **Design:** 5.8 split procedure
- **What's wrong:** the procedure sets "each child's `sources:` to exactly the IDs
  its body cites, computed with `lint.py --cited-sources <page>`". `sources:`
  holds paths, not IDs. A new child declares nothing yet, so 5.4's page-local
  resolution finds nothing, and the flag has to resolve IDs across the whole wiki.
  Every lint run except `--json` also writes a report and appends to `log.md`
  (`lint.py:711-780`).
- **Proposed edit:** "`lint.py --cited-sources <page>` prints the canonical path
  of each ID the page cites, resolved against every record and page with
  `slug()`. It lists IDs that resolve to nothing and writes nothing."

#### P20. `--auto-fix=content` semantics and plumbing

- **Severity:** Low
- **Steps:** 6
- **Design:** 5.11 item 8, 5.10 writers, F5
- **What's wrong:** it isn't stated whether `--auto-fix=content` also runs the
  plain fixes. `lint.py:386` checks `"--auto-fix" in args`, so the new form
  wouldn't even switch plain auto-fix on. 5.10 says auto-fix writes through
  `wikifm.set_field`/`set_list`, but step 6's row doesn't.
- **Proposed edit:** "`--auto-fix=content` runs the plain fixes plus the content
  repairs. All auto-fix frontmatter writes go through `wikifm`. lint-guide.md says
  unattended runs never pass `=content`."

#### P21. R10's `_status.md` list, and how lint reads records

- **Severity:** Low
- **Steps:** 6
- **Design:** 5.12, R10
- **What's wrong:** 5.12 lists R10's pages in `_status.md` under "Secondhand,
  unverified". Session-start writes `_status.md` (`session-start.sh:202-247`) from
  lint's JSON, and step 6's row only adds I1–I3 counts. R10 also reads
  `source_type` and `reconstructed` from records, which aren't pages: 11 have no
  frontmatter, and they carry fields outside the page profile.
- **Proposed edit:** step 6: "Lint's JSON includes R10's page list, and
  session-start writes it to `_status.md` under 'Secondhand, unverified'. Lint
  reads record frontmatter only for those two keys and never reports R12 on
  records."

#### P22. Two catalog auto-fixes have no implementer

- **Severity:** Low
- **Steps:** 6
- **Design:** 5.15, R2 and R3 rows
- **What's wrong:**
  - R2's auto-fix ("merge into one block list, reporting item counts before and
    after") was suggested in the lint-checks design but never built, and no step
    builds it. R2 has no violations today.
  - R3's auto-fix ("proposes adding the declaration; a human confirms") has no
    mechanism in any step. M5 handles the 31 undeclared citations by hand.
- **Proposed edit:** R2's auto-fix column: "No". R3's: "No; the message names the
  path to declare."
- **Confidence:** medium. The R3 "proposal" may have meant exactly that message.

### Step 7

#### P23. Post-validate's registration, and what happens to `post-write.sh`

- **Severity:** Med
- **Steps:** 7
- **Design:** 5.11 item 6, 5.14
- **What's wrong:**
  - Step 7's row doesn't say post-validate must be registered. It needs a
    synchronous PostToolUse entry in `~/.claude/settings.json` (the implementation
    prompt requires showing that edit first) and in `hooks/hooks.json`, with step
    3's matchers, replacing `post-write.sh`'s async entry.
  - "Folds in post-write link check" suggests removing `post-write.sh`, but
    `TestPostWrite` in `tests/test_hooks.py` (13 tests) runs that script, and 5.14
    keeps `test_hooks.py` untouched.
- **Proposed edit:** "Register post-validate in both files in place of
  `post-write.sh`. Keep `post-write.sh` in the repo, unregistered, so
  `TestPostWrite` still passes, and propose removing it upstream together with its
  tests."
- **Decided:** keep `post-write.sh`, unregistered.

### Step 8

#### P24. The empty-directory rule misses the MCP's index folder

- **Severity:** Low
- **Steps:** 8
- **Design:** 5.10 contract reconciliation, F10
- **What's wrong:** besides `meta/contract.md` and `meta/overview.md`, the MCP
  creates `.markdown_vault_mcp/` in the vault root on its first index flush (60
  seconds after start) or at shutdown. Its `save()` creates the folder
  unconditionally (`persisted-flat-vector-store.js`). The first session is
  covered, because the hook runs within seconds. But a wiki whose first session
  skipped the scaffold would then hold `meta/` and `.markdown_vault_mcp/`, and stay
  unscaffolded.
- **Proposed edit:** "treats a directory holding only `meta/` and
  `.markdown_vault_mcp/` as empty".

### Step 9

#### P25. Step 9 writes outside the fork

- **Severity:** Low
- **Steps:** 9
- **Design:** 5.14 worker copies, implementation prompt
- **What's wrong:** step 9 deletes `pm-wiki/.claude/agents/`, a change in the wiki
  repo (the copy is identical to the fork's, confirmed with `diff -rq`), and
  creates symlinks in `~/.claude/agents/`, which don't exist yet and would affect
  every session. The implementation prompt says only step 10 writes to the wiki.
- **Proposed edit:** step 9's row: "touches the wiki repo and user-level config;
  confirm both with the user first". Change the implementation prompt's line to
  "Only steps 9 and 10 write to it."

### Step 10

#### P26. Step 10 bundles the migration script with the wiki run, and misses a dependency

- **Severity:** Med
- **Steps:** 10, 11
- **Design:** section 7 (M1–M8 and the migration table), steps 10 and 11
- **What's wrong:**
  - `migrate_sources.py` is fork code (step 11 offers it upstream "with the
    migration script"), but step 10 is "Fork (wiki content)", with no instruction
    to write, test and commit the script in the fork first.
  - M7 installs "the reconciled template" from step 8, but step 10 depends on
    "5, 6" only.
  - M1 needs the shared snapshot function (P2).
  - The migration table's `_archive/README-<date>.md` rename has no M-step.
- **Proposed edit:** split step 10:
  - **10a:** write `skills/llm-wiki-pm/scripts/migrate_sources.py`, dry-run by
    default, with fixture tests for every class in section 7's table, F14's
    rotated logs and F15's cases. Depends on 4, 5 and 6.
  - **10b:** dry run on the wiki, sign-off, apply, and commit in the wiki repo.
    Depends on 8 and 10a.

  Add the README snapshot rename to M5's hand pass.

### Cross-cutting

#### P27. Documentation no step updates

- **Severity:** Low
- **Steps:** 3, 6, 7 and the steps that add files
- **Design:** I7, F9, 5.11
- **What's wrong:**
  - **lint-guide.md** lists lint's checks and tiers, and no step adds R3–R12,
    `--auto-fix=content` or `--cited-sources`. F9 found the 200-line rule at
    `lint-guide.md:25`, but its recommended pointers skip that file.
  - **hooks/README.md** is where I7 says the snapshot mechanism is documented. It
    describes three scripts and doesn't mention `pre-write.sh`.
  - **README.md** says "43 tests", and its layout lists the hooks and scripts that
    steps 3–7 add to.
- **Proposed edit:** lint-guide.md goes in step 6 (rules, flags and the split
  pointer), hooks/README.md in steps 3 and 7, and README in each step that adds a
  file.

#### P28. Bookkeeping with no step

- **Severity:** Low
- **Steps:** 3, 4, 10
- **Design:** 5.14, section 6
- **What's wrong:**
  - 5.14 asks for a one-line comment in `test_lint.py` pointing to `TestLint`, and
    to "correct the commit-message claim in the changelog". Neither is in a step,
    and the changelog isn't named; the fork changelog doesn't mention the claim.
  - The fork changelog's entries for PATCH-3a (replaced in step 4), ISSUE-2
    (mitigated in step 3) and ISSUE-3 (closed after step 10) have no update step.
- **Proposed edit:** the comment and a note correcting the claim go in step 4,
  with the note in the fork changelog. Each PATCH or ISSUE status line changes in
  the step that settles it.

#### P29. The semver column describes the upstream offer

- **Severity:** Low
- **Steps:** all
- **Design:** section 8 table, D10
- **What's wrong:** CONTRIBUTING's bump protocol would change `plugin.json`,
  `marketplace.json` and CHANGELOG.md in each step. The fork has never bumped for
  its own commits (it's still at 2.21.0), and step 1 followed that.
- **Proposed edit:** one line under the table: "Semver is the bump each step
  implies when offered upstream (D10). The fork doesn't bump versions."

---

## Coverage

### Section 5 changes

| Change | Section | Steps | Status |
|---|---|---|---|
| Records: definition, ID grammar, uniqueness (I5) | 5.1 | 5 (spec), 6 (R9) | Covered |
| Record naming; the fetcher's routing table becomes a pointer | 5.1 | 2 | Covered |
| Unrouted `raw/` folders emptied | 5.1 | 10 (M4, M5) | Covered |
| Recommended record template; `private:` dropped from records | 5.1 | 2, 5 | Covered |
| Write-once warning | 5.1, 5.11 item 4 | 3 | Covered |
| Correcting a saved record | 5.1 | 5 (spec) | Covered |
| `slug()` as the one ID function | 5.2 | 3, 4, 6 | Partly: P2 |
| Slug uniqueness including `briefings/` | 5.2 | 6 (R9) | Partly: P16 |
| Directory pages: `assets/` rule | 5.2 | 3, 5, 6 | Covered |
| Wiki pages as secondary sources (grounding) | 5.2, 5.3 | none | Gap: P17 |
| Not-sources list; SCHEMA not citable | 5.2 | 5, 6 (R6), 10 (M5) | Covered |
| `sources:` holds canonical paths | 5.3 | 6 (R6) | Covered |
| Templates show block style | 5.3 | none | Gap: P11 |
| Inline citation grammar | 5.4 | 4, 5, 6 (R7) | Covered |
| Exact page-local resolution; the two matchers deleted | 5.4 | 6 (R3) | Partly: P18 |
| `[[raw/…]]` citation examples removed | 5.4 | 5 | Partly: P11 |
| Legends are optional prose | 5.5 | 5 (spec) | Covered |
| Conversation records and `capture.py` | 5.6 | 5 | Partly: P12 |
| §2 fast path and §4 ③ | 5.6 | 5 | Covered |
| ingest-guide ① conversation capture | 5.6 | none | Gap: P9 |
| Web facts captured as records (CRM, research) | 5.7, D2 | 5 | Partly: P10 |
| Warehouse fields on the record | 5.7 | none needed | P14 |
| Live reads aren't citable | 5.7 | 5 (spec) | Covered |
| Split procedure | 5.8 | 5 (spec), 6 (`--cited-sources`) | Partly: P13, P19 |
| Split pointers: SCHEMA template, ingest-guide ⑫ | 5.8 | 5 | Covered |
| Split pointer: the wiki's own SCHEMA.md | 5.8 | 10 (M7) | Covered |
| Split pointer: lint's 200-line warning | 5.8 | 6 | Covered |
| Split reminder at write time | 5.8 | 7 | Covered |
| Supersede: sources follow the split rule | 5.8 | 5 (spec) | Covered |
| Contract naming rule removed | 5.8 | 8 | Covered |
| `briefings/` resolvable | 5.9 | 3 (hooks) | Partly: P16 |
| Brief rotation removed; rotated briefs restored | 5.9 | 2, 10 (M4) | Covered |
| Link-validator defers to lint | 5.9 | 2 | Partly: P1 |
| Link check on MCP writes | 5.9 | 3, 7 | Covered |
| Frontmatter profile, including continuation lines | 5.10 | 4, 6 (R12) | Partly: P15 |
| Canonical `'YYYY-MM-DD'` dates | 5.10 | 4, 5, 6, 10 | Covered |
| Required keys; CONTRIBUTING and validator corrected | 5.10 | 2 | Partly: P1 |
| `wikifm` parser and writers; callers switch; old parsers deleted | 5.10 | 4 | Partly: P6, P7 |
| Parser tests: PyYAML oracle, whole-wiki run | 5.10 | 4 | Partly: P8 |
| Vault contract template, scaffold copy, `meta/`-only rule | 5.10 | 8 | Partly: P24 |
| R11 | 5.10 | 6 | Covered |
| Deny rule on the MCP `edit` tool; README note | 5.11 item 1 | 3 | Covered |
| Hook matchers and filters | 5.11 item 1 | 3 | Partly: P4 |
| `ask` rule for `vault` | 5.11 note, D9 | none | Undecided: P5 |
| Path extraction | 5.11 item 2 | 3, 7 | Covered |
| Slug-named snapshots; `overview.md` and `index.md` rules; `briefings/` gated | 5.11 item 3 | 3 | Covered |
| Freshness gate on the post-edit text | 5.11 item 5 | 3 | Partly: P4 |
| Post-validate | 5.11 item 6 | 7 | Partly: P23 |
| Session-start counts, no `--json` report, lint failure reported | 5.11 item 7 | 6 | Covered |
| Auto-fix snapshots; `--auto-fix=content` | 5.11 item 8 | 6 | Partly: P2, P20 |
| Tool Selection line on frontmatter edits | 5.11 item 9 | 5 | Covered |
| R10 | 5.12 | 6 | Partly: P21 |
| `wiki-search.sh` fix and smoke test | 5.13 | 1 | Done |
| Test locations | 5.14 | 3, 4, 6 | Partly: P28 |
| Worker symlinks | 5.14 | 9 | Partly: P25 |
| Lint catalog tiers and auto-fixes | 5.15 | 6, 11 | Partly: P15, P22 |

### Other proposed changes

| Change | Section | Steps | Status |
|---|---|---|---|
| AGENTS.md snapshot relabel; `hooks/README.md` as the mechanism's home | 1 (I7) | none | Gap: P11, P27 |
| `91878dc` revised | 6 | 4, 6 | Covered (P7) |
| `ae33f9d` revised | 6 | 5 | Covered |
| `543766c` replaced; its tests become R6 tests | 6 | 4, 6 | Partly: P7 |
| PATCH-3a replaced | 6 | 4 | Covered |
| PATCH-3b names snapshots | 6 | 3 | Covered |
| PATCH-3c extended to `briefings/` | 6 | none | Gap: P16 |
| ISSUE-2 and ISSUE-3 status | 6 | none | Gap: P28 |
| A6 and A7 residue | 6 | 2 | Covered |
| M1–M8 | 7 | 10 | Partly: P26 |
| `_archive/README-<date>.md` rename | 7 (table) | none | Gap: P26 |
| SKILL.md References, Scripts and §4 snapshot edits | 8 (size estimate) | none | Gap: P11 |
| Step 4 lands as a refactor | 8 (conflict surface) | 4 | Conflicts: P6 |
| Dated digests exempt from grounding | 9 (D6) | none | Gap: P17 |
| Deny rule, and an optional `ask` rule | 9 (D9) | 3 | Partly: P5 |

### Review findings

| Finding | Recommended fix | Where the design has it | Steps | Status |
|---|---|---|---|---|
| F1 | R10 date-free, or drop it | I8, 5.12, R10, section 7, M8 | 6 | Traced (date-free chosen) |
| F2 | Session-start's scan on `wikifm`; `'YYYY-MM-DD'`; N15's counts; no step 12 | RC3, 5.10, N15, M4, D11 | 4, 5, 6, 10 | Traced; see P6 |
| F3 | Continuation lines; an oracle fixture; R12 at 🟡 | 5.10, 5.15 | 4, 6 | Traced; see P15 |
| F4 | Deny rule under both names; `set_field`; item 9 narrowed; no step 12; NW2 deferred | section 1, 5.10, 5.11, D9, D11, NW2 | 3, 4, 5 | Traced (deny chosen); see P5 |
| F5 | `--auto-fix=content`; the maintain line reworded | 5.11 item 8 | 2, 6 | Traced (flag chosen); see P20 |
| F6 | Drop R13; `capture.py` and M2 write `source_type` | 5.1, 5.15 | 5, 10 | Traced (drop chosen) |
| F7 | Drop I4, R8, M6 and the legend grammar | 5.5, D4 | none needed | Traced |
| F8 | Report a lint failure; whole-wiki parse test | 5.11 item 7, 5.10 | 4, 6 | Traced; see P8 |
| F9 | Parent trim; pointers; write-time reminder; no `split_from` | 5.8, 5.11 item 6 | 5, 6, 7, 10 | Traced; see P13, P27 |
| F10 | Keep R11; remove two claims; `meta/`-only counts as empty | section 1, V1, 5.10 | 6, 8 | Traced; see P24 |
| F11 | Page-slug collisions in R9 | 5.2, R9 | 6 | Traced |
| F12 | Drop rotation; restore rotated briefs | 5.9, M4 | 2, 10 | Traced |
| F13 | `action`/`dryRun` filters; README note | 5.11 item 1 | 3 | Traced; see P4 |
| F14 | M2 reads `log*.md` | M2 | 10 | Traced |
| F15 | `.html` source; unrouted folders; extra root files | 5.1, 5.2, section 7 | 10 | Traced (move chosen) |
| F16 | Informational | none | 0 | Done |

No finding's fix was changed without a record. Where a finding offered options,
the review's status line names the one the design took (F1, F4, F5, F6, F15).

---

## Code facts checked

These held:

- **`lint.py`:** `slug()` (148); the last-wins slug map (404, F11); grounding
  (502-520); the `last_verified` check (537-548); the unquoted `updated` read (583,
  F2); the 200-line warning (570-573); the report written before `--json` returns
  (753, N1); the `log.md` append (772-780, NW3); the R3/R4 matchers (322-378).
- **`pre-write.sh`:** stem-named snapshots (39, 59, N14); Edit judged from disk
  (65-71); gated folders that exclude `briefings/` (47, N2); its own `sources:`
  parser (73-89).
- **`session-start.sh`:** the swallowed lint failure (136, F8); the stale scan
  stripping only `"` (177, F2); the scaffold skipping a non-empty folder (52-59,
  F10).
- **Skills and workers:** the maintain skill's rotation (68-70, 83) and
  "non-destructive" note (74-75); the PRD skill's "(enforced)" (36); the fetcher's
  `private:` (37-47, 59) and routing table (21-28); CONTRIBUTING's field list and
  `private:` line; README's three `private:` mentions.
- **Registered hooks:** the user-level entries in `~/.claude/settings.json`
  (`Write|Edit|MultiEdit` for PreToolUse and PostToolUse, post-write async). The
  permission settings are `defaultMode: "auto"` with no `deny` or `ask` rules.
- **MCP 2.3.0:** `vault` takes `action` and `path`, and `edit` takes `path` or
  `operations[].path` plus `dryRun`, so 5.11 item 2 holds. `vault.create` throws
  without content. Auto-init creates `meta/contract.md` and `meta/overview.md`, and
  the default contract carries `generated_by: mcp-markdown-vault` and a `status`
  enum line, so R11's test works.
- **Workers:** `pm-wiki/.claude/agents/` is identical to the fork's copy, and
  `CLAUDE_SKILL_DIR` is used by worker-lint and worker-link-validator.
- **Python 3.9:** `Path.rglob` on a missing folder returns nothing, so adding
  `briefings/` to lint's folders won't fail on a wiki without one.

These didn't hold: P1 (`--all-orphans`), P6, P7 (`backlinks.py`), P10, P14, P24.

## Not verified

- Whether PreToolUse and PostToolUse hooks fire on MCP tool calls (step 3's live
  check, P3).
- Whether `CLAUDE_SKILL_DIR` is set inside subagents (step 9).
- Which agent definition wins when a user-level and a project-level agent share a
  name, as they will in the fork after step 9.
