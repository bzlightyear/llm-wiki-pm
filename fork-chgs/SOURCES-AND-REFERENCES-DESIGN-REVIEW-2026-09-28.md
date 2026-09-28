# Review: SOURCES-AND-REFERENCES-DESIGN-2026-09-25

Date: 2026-09-28 · Reviewer: fresh session, read-only · Assumes D1–D11 accepted as
recommended, including the step 0 scrub (D8).

Scope: the design doc; the fork at `5b21629` (same code as the design's `c105625`
for everything reviewed); hooks registered in `~/.claude/settings.json`; the MCP
(`@wirux/mcp-markdown-vault` 2.3.0, npx cache); a scratch copy of the private wiki
taken 2026-09-28 (246 live pages, 43 lint reports, 153 `raw/` records, 242
archive snapshots, wiki repo at `7ea0375`); Claude Code transcripts under
`~/.claude/projects/` (retained from 2026-08-07). Lint was run only against the
scratch copy. All wiki facts below are counts. No page names, people, companies
or source slugs appear in this report.

Companion document: [WIKI-SEARCH-MCP-TOOLS-2026-09-28.md](WIKI-SEARCH-MCP-TOOLS-2026-09-28.md)
lists every wiki-search MCP tool and operation with its risk, the full usage
counts under both tool-name forms, the transcript-coverage gap, and the
semantic-search measurement. Finding F4 summarizes it.

Labels: F1–F16 are this review's findings. All other IDs (I, R, M, N, NW, W, …)
are the design's own: for example, M1–M8 are its migration steps (section 7) and
NW1–NW2 its follow-on work (section 10).

Severity: **High** means a rule or guarantee in the design doesn't hold as written, or
builds on a false premise. **Med** means a real cost or side effect the design doesn't
state. **Low** means a correction or small gap.

---

## Summary

The core idea holds up against the data. The ID grammar, exact `slug()` resolution,
write-once conversation records and a single parser are sound. Every record stem
and page slug already fits the grammar, there are no collisions, and 788 inline
cites resolve exactly today. The problems sit around that core:

1. **R10/I8 repeats mistake pattern 2.** It clears on `last_verified`, which
   ordinary edits bump and nothing else writes.
2. **The date-quoting damage is about 100× larger than N15 says, and the "one
   parser" plan leaves out the parser where it hurts** (session-start's stale
   scan).
3. **R12 has existing violations on 21 pages**, so starting it at 🔴 is wrong.
4. **The MCP-specific machinery protects a path agents already abandoned.** MCP
   edits damaged pages in early August and have been avoided since. A permission
   rule settles it cheaply. The most frequent unhooked writer, ad-hoc Bash/Python
   frontmatter scripts, gets nothing beyond lint.
5. **Several new mechanisms cost more than they return:** legends (I4/R8/M6),
   R13, `split_from` + R4-🔴, and step 12. **Step 6's auto-fixes would run unattended**
   through the maintain loop before the reviewed migration.

---

## Findings

### F1. R10 / I8 clears on `last_verified`, which is not a verification signal (pattern 2)

- **Severity:** High. It's the exact failure the earlier pass removed from R14, and it
  sits under the design's only answer to RC6.
- **Affects:** I8, section 5.12, R10, section 7 "What cannot be recovered", M8.
- **What goes wrong:** R10 stops flagging a conversation-only page once
  `last_verified` is newer than 30 days. Any ordinary edit that bumps both dates
  clears the flag, so the "revisit obligation" can be satisfied without anyone
  verifying anything.
- **Evidence:**
  - No skill, sub-skill, worker, hook or lint auto-fix writes `last_verified`. The
    only mentions are `templates/SCHEMA.md:35,320` (prose: "set when you
    confirm") and the reader at `lint.py:537`.
  - Wiki git history: 210 per-file diffs change `last_verified`. 206 of them change
    `updated` in the same diff, and 182 set it to the same value as `updated`.
  - Today 84 of 112 pages that carry `last_verified` have it equal to `updated`.
- **Frequency:** after migration R10 would flag about 4 pages. That's my count of pages
  whose primary sources are all conversational, approximated by regex over
  `sources:`.
- **Recommendation: fix or drop.**
  - Preferred fix: make R10 date-free. Flag a page while every primary source
    resolves to a `source_type: conversation` or `reconstructed: true` record, and
    clear it only when a non-conversation primary record is declared. That signal
    needs a real new record, which is something a writer actually has to produce.
    Delete "stamping `last_verified:`" from 5.12 and section 7.
  - At roughly 4 pages, the alternative is to drop R10 and list those pages once in
    the migration report.
  - Out of scope but same flaw: the existing 120-day `last_verified` warning
    (`lint.py:537-548`).

### F2. Date-quote damage is far larger than N15, and the single-parser plan misses session-start

- **Severity:** High. A health metric users see every session is wrong today, and it
  stays wrong after the change.
- **Affects:** N15, N6, section 5.10 "One parser", R12 auto-fix, M4, step 4,
  step 12.
- **What goes wrong:** the MCP (and PyYAML) serialize string dates as
  *single-quoted* (`updated: '2026-09-04'`). The design notes that quoted dates stay
  quoted but misses the consequence:
  - `lint.py:583` doesn't strip quotes from `updated`, so `fromisoformat` fails and the
    90-day staleness check silently skips the page.
  - `session-start.sh:177` strips only `"`, so its 30-day stale scan skips
    single-quoted values too.
  - Section 5.10 lists what switches to `wikifm` (lint, pre-write, post-validate,
    backlinks, capture). It doesn't list the inline parser at
    `session-start.sh:151-189`, so the undercount survives the design.
- **Evidence:**
  - Live pages today: `updated` is single-quoted on 114, timestamp on 1, unquoted
    on 174. `last_verified` is single-quoted on 62, timestamp on 3, unquoted on 47.
  - Lint cannot parse `updated` on 115 pages.
  - Session-start parses 51 of 143 knowledge pages and skips 92. It reported
    **49 stale** in this session's health line; the true count of pages more than
    30 days old is **66**.
  - Reproduced with the MCP's js-yaml: an unquoted date comes back as a timestamp,
    and both `"…"` and `'…'` come back as `'…'`.
  - With `CORE_SCHEMA` (the step 12 patch) every date comes back **unquoted**. That
    re-exposes N6 for PyYAML readers and changes the quoting on every page the MCP
    touches.
  - Single-quoted dates entered in 16 wiki commits between 2026-08-05 and
    2026-09-25, so they keep arriving.
  - New timestamp values entered in 5 commits, not 4 (`2e819d8`, `889710d`,
    `a0afb9e`, `85b1963`, `76b1603`).
- **Recommendation: fix.**
  - Put `session-start.sh`'s scan on `wikifm` in step 4, and list it in 5.10 and RC3.
    There are at least four parsers, not three.
  - Make the canonical date form **single-quoted `'YYYY-MM-DD'`** in templates, in
    R12's auto-fix and in M4. It is the form both js-yaml and PyYAML emit and
    preserve, so N15 is prevented by format rather than detected. Normalizing to
    unquoted, as M4 says, sets the next MCP round-trip up to re-timestamp the value.
  - Correct N15's impact text: it's 115 pages for lint and 92 for session-start,
    not 1 and 3.
  - If step 12 is kept, it has to keep strings quoted. Otherwise drop it (see F4).

### F3. R12 has 21 existing violations; the "start at 🔴" rationale is false

- **Severity:** High. It turns the health line red on day one, the outcome D7 was
  written to avoid.
- **Affects:** section 5.10 profile, section 5.15 table, step 6 ("R9 and R12
  … have no existing violations and start at 🔴").
- **What goes wrong:** the profile allows only `  - item` lines in a block list. 15
  pages have `gaps:` items that wrap onto indented continuation lines. That's valid
  YAML (a multi-line plain scalar), and the MCP folds it into one line. 13 pages
  have timestamp dates, which fail the date regex. Step 6 lands before the step 10
  migration, so from step 6 on the session-start line reports 🔴 on 21 pages.
- **Evidence:** a frontmatter scan of the scratch copy. Union: 21 pages (13 timestamp,
  15 continuation). BaseLoader parses all 15 continuation pages without error.
- **Recommendation: fix.** Extend the profile so an indented non-dash line continues
  the previous list item (folded with one space, as YAML does), and add a fixture
  for it to the PyYAML-oracle tests. Ship R12 at 🟡 until M4 has normalized dates,
  or move date normalization ahead of R12's promotion.

### F4. MCP edits were a real but abandoned path; the frequent unhooked writer is ignored

- **Severity:** High for prioritization. The damaging operations have been avoided
  by convention since 2026-08-11, so a permission rule gives certainty for almost
  nothing. Step 12 and NW2 cost a Node build and upgrade work to make safe tools
  nobody needs, and the active unhooked path gets no write-time help.
- **Affects:** Bottom line item 4, I1/I7 "including MCP writes", section 1 "Which
  invariants inherit the MCP hole", 5.11 items 1–3, 6 and 9, permission note, D9,
  D11/step 12, NW2.
- **What goes wrong:** the design treats MCP writes as a live path that needs hook
  coverage, a patched MCP and eventually a fork. The evidence says MCP edits were
  used in early August, damaged pages, and were then deliberately avoided. Ad-hoc
  scripts, a writer that stays active, get no write-time help. Separately, the
  design's description of which MCP operations damage content is partly wrong.
- **Evidence:**
  - The wiki's own log records MCP edit use: a 2026-08-05 escaped-bracket fix, and
    a 2026-08-11 daily-maintenance session whose `string_replace` and
    `frontmatter_set` calls re-escaped wikilinks across whole files (that entry led
    to wirux/mcp-markdown-vault#47). From 2026-08-11 on, the log records agents
    choosing the Write tool or `sed` "to avoid re-triggering" the bug.
  - **The saved transcripts are incomplete, so they can't show the absence of MCP
    writes.** On 11 of 30 days since 2026-08-07 with non-lint `log.md` entries,
    no transcript touches the wiki (one of those days has 15 log entries). The
    2026-08-11 maintenance session is also missing, even though that day has 3
    transcripts. Where those sessions ran is unverified.
  - In the transcripts that do exist (both tool-name prefixes: the plugin-era
    `mcp__plugin_llm-wiki-pm_wiki-search__*`, used until 2026-09-25, and the
    current `mcp__wiki-search__*`), the only MCP calls are 31 reads and admin calls:
    28 `view`, 1 `vault.read`, and one `system.prepare_overview` and
    `save_overview`, the last on 2026-09-02. The same transcripts contain 1,138
    Write/Edit calls on wiki files and 23 Bash calls running ad-hoc Python
    frontmatter scripts over the wiki (1 with `yaml.dump`, 1 Node script).
  - New timestamp values entered in commits dated 08-05, 08-11, 08-28, 08-30 and
    09-04. The timestamp format is js-yaml's, and early-August MCP `frontmatter_set`
    use is recorded, so the MCP is the likely writer. That is not confirmed for the
    later commits: commits batch several days, and those sessions' transcripts
    are missing.
  - The installed MCP (2.3.0) arrived 2026-08-03 and hasn't changed, so the logged
    sessions ran the code reviewed here. In that code:
    - `string_replace` and `line_replace` are plain text operations
      (`freeform-editor.js`; `mcp-tools.js:254-285`), with no AST or YAML
      round-trip.
    - `vault.update` writes the content verbatim (`update-file.js:13`).
    - Only `frontmatter_set` (`mcp-tools.js:287-305`) and the AST operations
      (append, prepend, replace, delete, via `AstPatcher` plus `stringify`)
      re-serialize the page.

    So the 2026-08-11 log's blame on `string_replace` is most likely wrong. The
    `frontmatter_set` calls in the same session re-serialize the whole file, which
    explains the escaping. Both 5.11 item 9 and D9 repeat that attribution.
  - The permission note and D9 assume "on ask" means a human prompt. User settings
    have `defaultMode: "auto"` and no `ask` rules, so an unlisted MCP tool is decided
    by auto mode, not necessarily by a prompt (unverified how auto mode treats these
    tools).
- **Recommendations:**
  - **Prefer prevention:** add a `permissions.deny` (or explicit `permissions.ask`)
    entry for `mcp__wiki-search__edit`, in both its plugin-prefixed and plain
    names. It isn't a hook, so it doesn't breach "hooks never deny". The Edit tool
    already covers every operation it offers, so nothing is lost. This is your
    call.
  - **Simplify:** keep the MCP hook matchers, but match both name forms (for
    example `mcp__.*wiki-search__(vault|edit)`), because upstream users install the
    plugin and get the prefixed names. Drop step 12, and defer NW2 unless MCP edits
    are wanted back.
  - **Fix: serve the frequent writer.** Give `wikifm.py` a text-preserving
    `set_field(text, key, value)` / `set_list(...)`, and require it in SKILL.md
    Tool Selection for any script that edits frontmatter, and in lint auto-fix and
    `migrate_sources.py`. That turns ad-hoc scripts (B2) from lint-only into correct-by-construction
    for the common case.
  - **Fix the doc:** narrow 5.11 item 9 and D9 to `frontmatter_set` and the AST
    operations.
  - **Details:** the per-operation risk table and full usage counts are in
    [WIKI-SEARCH-MCP-TOOLS-2026-09-28.md](WIKI-SEARCH-MCP-TOOLS-2026-09-28.md).
- **Note the evidence gap:** the design's claims about write frequency, and this
    review's, rest on transcripts that miss about a third of the wiki-editing
    days.

### F5. Step 6's auto-fixes would run unattended before the reviewed migration

- **Severity:** Med.
- **Affects:** step 6, M4, M6, section 5.15 auto-fix column, maintain sub-skill.
- **What goes wrong:** `llm-wiki-maintain/SKILL.md:74-75` runs `lint.py --auto-fix` in
  autonomous mode because "it's non-destructive". Step 6 extends auto-fix to rewrite
  body markers, append to legends and normalize dates. Step 10's migration is
  dry-run, per-page tabled and signed off. Any autonomous run between step 6 and
  step 10 therefore performs most of M4/M6 across dozens of pages with no dry run and
  no sign-off. That breaks AGENTS.md "10+ pages → sign-off" and makes the maintain
  line false.
- **Evidence:** the auto-fixable classes in section 7 are 55 multi-line + 9 path-form + 8
  nested-prefix + 5 "vs." markers, dates on 13 pages, and appends to up to 49
  legend pages.
- **Recommendation: fix.** Put the new classes behind a separate flag
  (`--auto-fix=content`) that maintain never passes, or ship them only with step 10.
  Change the maintain line to name what auto-fix still does unattended (index
  backfill, de-escape).

### F6. R13 requires fields no writer produces; its date filter is blind to 27% of record shapes

- **Severity:** Med (pattern 2 variant: the rule depends on a field without a writer).
- **Affects:** section 5.1 record frontmatter, R13, frontmatter-changes table, steps 2 and 5.
- **What goes wrong:** R13 warns when `source_type` or `captured` is missing on new
  records, but the record writers don't produce them:
  - `source_type` appears in no skill, template or worker (0 writers).
  - `worker-source-fetcher.md:45` writes `fetched:`.
  - `ingest-guide.md:16,23` and SCHEMA prescribe `source_date_range`.

  After ship, every fetcher or transcript record will 🟡 unless both writers change,
  and neither step 2 nor step 5 says to change their field names. The 46 existing
  `source_type` values use a vocabulary (article, slack, meeting-notes variants,
  pptx, …) that doesn't match 5.1's enum. The "filename date after ship" filter never
  checks records named without a full date.
- **Evidence:**
  - Records by date field: 40 have only `source_date_range`, 21 only `fetched`,
    about 70 carry `captured` (alongside other fields), and 11 have no frontmatter.
    Eight different date keys are in use.
  - 42 of 153 record stems contain no `YYYY-MM-DD`.
  - N11's 11 frontmatter-less records came from two weeks (1 + 10).
  - Nothing reads `captured`. Only R10 reads `source_type`, and only for
    `conversation`, which `capture.py` writes.
- **Recommendation: drop R13.** Have `capture.py` and M2 write
  `source_type: conversation`, and keep 5.1's block as a recommended template. If
  R13 stays, steps 2 and 5 must change the fetcher and ingest-guide ① to emit
  `source_type` and `captured`, and R13 should key on a frozen baseline list of
  legacy record IDs, not on a filename date.

### F7. Legend machinery (I4, R8, M6) costs more than the problem it solves

- **Severity:** Med (pattern 1).
- **Affects:** I4, 5.5, R8, M6, D4.
- **What goes wrong:** no skill, template or AGENTS.md prescribes a `## Sources`
  legend (grep over `skills/` and `AGENTS.md`: 0 hits). Legends are an agent habit,
  and a fading one. The design turns them into a fourth declaration site with a
  grammar, a rule, an auto-fix that appends IDs into human prose, and a
  human-confirmed migration of up to 136 prose bullets.
- **Evidence:** legend headings added per ISO week: W32 20, W33 6, W35 17, W36 6,
  W37–38 0, W39 2. Drift instances found: 1 (ISSUE-3).
- **Recommendation: drop I4, R8, M6 and the legend grammar.** Declare legends optional
  free prose that isn't a declaration site. `sources:` plus markers already give
  exact resolution. This takes D4's alternative against its recommendation, for the
  cost reason above.

### F8. "Every write path is detected by the next session" rests on a lint call that swallows failure

- **Severity:** Med.
- **Affects:** Bottom line item 4c, 5.11 item 7, honest summary.
- **What goes wrong:** `session-start.sh:136` runs lint inside
  `if LINT_OUT=$(… 2>/dev/null)`. On a crash the counts stay 0 and the health line
  reads clean. Step 4 replaces every parser with new code, so a `wikifm` exception
  on an unexpected shape (F3 is an example) would silently turn "detected by next
  session" into "reported as clean".
- **Evidence:** `session-start.sh:134-142`. Lint runtime on the scratch copy is 0.10 s,
  so the cost of a fix isn't a concern.
- **Recommendation: fix.** On a nonzero exit or unparseable JSON, put "lint failed:
  health unknown" into `additionalContext`. Add a test that runs `wikifm.parse` over
  every page of a scratch wiki copy and requires 0 exceptions.

### F9. Split guidance is out of agents' sight; `split_from` + R4-🔴 catches almost nothing

- **Severity:** Med (pattern 2).
- **Affects:** 5.8 Split, R4 row, `--cited-sources` (step 6), post-validate
  (5.11 item 6), frontmatter-changes table, entity promotion (W7).
- **What goes wrong:**
  - **Splits are frequent, and they spread damage.** There were 15 "history splits"
    in one week, done in two batches by agent-written ad-hoc scripts (B2), and 25
    pages are over 200 lines now. A split copies whatever is wrong on the parent onto
    every child: the design's own history shows one invented citation copied into
    ten files.
  - **Agents won't find the procedure where it's documented.** The 200-line rule
    lives in SCHEMA.md (template `templates/SCHEMA.md:124`, and the wiki's own
    copy) and in `lint-guide.md:25`, not in SKILL.md. The design puts the split
    procedure in `citation-spec.md`, which agents read only on demand. Lint's
    "> 200 lines — split candidate" warning appears only in lint's report:
    `session-start.sh:136-141` passes on just the broken-link and orphan counts, so
    the warning never reaches an agent's context unless it runs lint or reads the
    report.
  - **The procedure misses a step.** It never trims the parent's `sources:` to what
    the parent still cites after sections move out.
  - **The 🔴 escalation depends on a label set by hand.** It fires only if the
    splitting agent adds `split_from`. An agent that follows the procedure and uses
    `--cited-sources` already gets a correct list, so the escalation adds nothing.
    An agent that writes its own script skips both, so the escalation never
    switches on.
  - **The label would also be permanent and could go stale.** A labeled child is
    held to the stricter rule forever, even when a later edit legitimately declares
    a source it's built from. If the parent is renamed or archived, `split_from`
    points at nothing.
- **Recommendation: fix the guidance, drop the label.**
  - **Keep `--cited-sources`,** and add a procedure step: run it on the parent too,
    and trim the parent's `sources:` to match.
  - **Point to the procedure where agents look.** One line, "follow the split
    procedure in `citation-spec.md` and set each page's sources with `lint.py
    --cited-sources`", in:
    - the split rule in SCHEMA.md, in both the template and the live wiki's copy (a
      scaffolded copy doesn't update when the template changes);
    - lint's "> 200 lines — split candidate" warning text;
    - `ingest-guide.md` ⑫ (entity promotion is a split).
  - **Add a write-time reminder.** When a write takes a page over 200 lines,
    post-validate adds the same line to the agent's context in that turn.
  - **Drop `split_from` and the R4 escalation.** Rely on the existing checks, which
    need no label and cover every page, including splits done by script:
    - R3 flags a child that cites a source it doesn't declare;
    - R4 flags a child or parent that declares many sources it doesn't cite.
  - **Escalation path:** if lint keeps flagging split pages after this lands, add a
    split command (for example `scripts/split_page.py`). The agent would choose
    which headings move; the command would do the rest: snapshot the parent, write
    each child with exactly its cited sources, trim the parent, add links both ways,
    and rewrite `[[parent#heading]]` links, all through `wikifm`.

    Not recommended up front, because:
    - it writes many pages at once, so a bug in it would spread just as copied lists
      do;
    - it needs tests for directory pages, history pages and anchors;
    - it waits on steps 4–5;
    - the checks above already catch most split mistakes.

### F10. Contract reconciliation rests on two wrong claims about the MCP

- **Severity:** Med for upstream users, Low for this wiki (M7 hand-edits it).
- **Affects:** section 1 MCP gaps ("`vault.create` without `content` falls back to
  the note template"), V1, 5.10 ("the wiki's version wins on new installs"),
  step 8, R11.
- **Evidence:**
  - `vault.create` throws without content (`mcp-tools.js:88-92`). The contract's Note
    Template is advisory text agents may read, not a code fallback.
  - The MCP creates `meta/contract.md` and `meta/overview.md` at server start
    (`index.js:123` → `vault-auto-init.js`), concurrently with the SessionStart
    hook. The order is unverified.
  - On a brand-new empty wiki dir, MCP auto-init makes the dir non-empty. That
    makes `session-start.sh:53-59` skip the whole scaffold (no SCHEMA, index or
    log), which is a pre-existing race that step 8 now relies on.
- **Recommendation: fix.**
  - Keep R11. It is the backstop that catches the race, so it earns its place for
    new installs.
  - Remove both claims.
  - Treat a wiki dir that contains only `meta/` as empty for scaffolding.

### F11. I6 claims page-slug uniqueness, but nothing checks it

- **Severity:** Low.
- `lint.py:404` builds `{slug(p): p}` and silently keeps the last page on a
  collision.
- Adding `briefings/` and directory part pages widens the namespace. There are 0
  collisions today.
- **Recommendation: fix cheaply** by adding a page-slug collision check to R9.

### F12. Briefings become link targets, but weekly rotation breaks those links

- **Severity:** Low.
- `llm-wiki-maintain/SKILL.md:68-69` moves briefs older than 7 days with `mv` and
  doesn't rewrite inbound links, unlike §6 Archive.
- Only `index.md` links a brief today, and index isn't link-checked.
- **Recommendation: fix** by making the rotation step rewrite inbound links to
  plain text, as §6 does.

### F13. MCP hook details the design doesn't handle

- **Severity:** Low.
- The `edit` tool's `dryRun: true` writes nothing (`mcp-tools.js:162`), but
  post-validate would re-report the unchanged file as if the call had broken it.
- The `vault` matcher also fires on `list`, `read` and `stat`, one Python start per
  read (about 0.02 s).
- **Recommendation: fix** by filtering on `action` and `dryRun` in step 3.

### F14. Migration step M2 assumes the old conversation dates are still in `log.md`

- **Severity:** Low.
- `log.md` has 480 entries against the 500-entry rotation threshold
  (`session-stop.sh:46`). 257 of those entries are lint lines.
- If rotation runs before the migration, those dates move to `log-2026.md`.
- **Recommendation: fix** by having migration step M2 read `log*.md`.

### F15. Migration table gaps

- **Severity:** Low.
- One `sources:` entry declares a non-`.md` file under `raw/attachments/`. It's
  R6-invalid under the canonical rule and not listed in section 7.
- Two raw dirs (`clippings`, `attachments`) are in no routing table, contrary to
  "routing as in ingest-guide ①".
- One page references a root file whose name has spaces. It is neither a structural
  file in 5.2's list nor a page.
- **Recommendation: fix** by adding these three cases to section 7's table.

### F16. Step 0 scope check (informational)

- **Severity:** Low.
- A slug-level scan of every tracked fork file against all wiki page slugs and
  record IDs finds real identifiers only in the three N12 files. Every other hit is
  a generic word.
- Free-text person and company names in prose weren't exhaustively checked
  (unverified).

---

## Checked and holding

- ID grammar: 0 record stems and 0 page slugs outside `[a-z0-9][a-z0-9._-]*`.
  0 duplicate record IDs, 0 record/page collisions, 0 duplicate page slugs.
- Directory pages: 4 exist. All 9 extra `.md` files inside them are full pages
  with every required key and unique slugs, so the `assets/` rule has nothing to
  migrate.
- Marker counts reconcile with section 7:
  - 788 cites resolve exactly under the new rule today.
  - 29 cites use a valid record ID that is undeclared on its page (design: 31).
  - About 214 cites are conversational.
  - The remaining shapes are the known wrap, "vs." and nested-prefix classes.
  - 0 markers sit inside code spans.
- `raw/` write-once: 1 modification in 157 file events, consistent with the
  design's 1/156.
- Performance: lint takes 0.10 s on the full wiki, and a Python start takes 0.02 s,
  so the post-validate budget is realistic.
- Upstream: the fork's merge base is upstream `2.21.0`, with 0 upstream commits
  since. Merge-conflict risk is nil today.

## Not verified

- That PreToolUse and PostToolUse fire on MCP tool calls. Testing it needs a settings
  change, which was out of scope.
- Who wrote the timestamp dates committed after 2026-08-11 (the MCP is likely; the transcripts are incomplete).
- Where the sessions missing from `~/.claude/projects` ran (11 of 30 editing days).
- The MCP-vs-SessionStart startup order.
- How auto mode treats unlisted MCP write tools.
- How Obsidian serializes dates.
- Hook and `CLAUDE_SKILL_DIR` behavior in subagents.
- Worker-symlink plan (step 9): not assessed.

---

## Cost/benefit of every new mechanism

| Mechanism | Evidence of need | Cost | Verdict |
|---|---|---|---|
| Source-ID grammar + exact `slug()` resolution | 81 invalid `sources:` entries, about 214 unresolvable cites; grammar already fits 100% of files | Low | **Keep** |
| `citation-spec.md` as single spec | Four conflicting definitions (N3, N4) | Low | **Keep** |
| Conversation records + `capture.py` | About 217 conversational markers on 72 pages | +1 call per capture | **Keep** |
| `wikifm.py` single parser | 115 + 92 silently skipped dates (F2) | Medium | **Keep, extend** to session-start's scan; add a text-preserving `set_field` (F4) |
| R12 profile | Real corruption history | Low | **Fix**: continuation lines; start 🟡 (F3) |
| R12 midnight-timestamp auto-fix | 13 pages | Low | **Simplify**: write `'YYYY-MM-DD'` (F2) |
| R3 exact | Replaces a permissive matcher | Low | **Keep** |
| R6 | Typo'd-path class | Low | **Keep** |
| R7 + mechanical auto-fix | 77 fixable markers | Low | **Keep**, but gate the auto-fix from autonomous runs (F5) |
| I4 + R8 + legend grammar + M6 | 1 drift instance; legends unprescribed and fading | High (136 bullets confirmed by a human) | **Drop** (F7) |
| R9 record uniqueness | 0 collisions, but resolution depends on it | Very low | **Keep**; add page slugs (F11) |
| I8 + R10 | About 4 pages; clears on an untrustworthy signal | Low, but misleading | **Drop, or make date-free** (F1) |
| R11 contract check | Backstop for the MCP auto-init race | Very low | **Keep** (F10) |
| R13 + `source_type`/`captured` requirement | 11 bad records from 2 weeks; 0 writers of `source_type` | Medium (writer changes) | **Drop** (F6) |
| Split procedure + `--cited-sources` | 15 splits in a week; 25 candidates now | Low | **Keep**; add parent trimming, pointers in SCHEMA.md and the lint warning, and a write-time reminder; build a split command only if lint keeps flagging splits (F9) |
| `split_from` + R4-🔴 | Depends on a manual field | Low | **Drop** (F9) |
| `lifecycle: dated-digest` grounding exemption (D6) | Existing field; makes current behavior explicit | Very low | **Keep** |
| `reconstructed` records (M2) | Legacy conversation dates | Low | **Keep**; read `log*.md` (F14) |
| Hook MCP matchers + path extraction | MCP edits used in early Aug, avoided since | Low | **Simplify**: keep, match both name forms, filter action/`dryRun` (F13), verify firing; prefer a deny rule (F4) |
| Slug-named snapshots (N14) | 1 real collision | Very low | **Keep** |
| `overview.md` whole-file snapshot, `index.md` never | ISSUE-2 | Very low | **Keep** |
| Raw write-once warning | 1 edit in 157 | Very low | **Keep** (cheap) |
| Freshness gate on post-edit text | Inverted today | Low | **Keep** |
| Synchronous post-validate | 1,138 Write/Edit wiki calls | Low (about 0.1 s) | **Keep** |
| Session-start I1–I4 counts + no report in `--json` | N1 | Low | **Keep**; surface lint failure (F8) |
| Lint auto-fix snapshots | W15 has no pre-image | Low | **Keep** |
| MCP write checklist (5.11 item 9) | Overstated scope | Very low | **Simplify**: `frontmatter_set` and AST ops only |
| Vault contract template + scaffold copy | N4 | Low | **Keep**; fix the race claim (F10) |
| `wiki-search.sh` fix + smoke test | N13 reproduced | Low | **Keep** |
| Step 12 patched MCP | Damaging ops avoided since 08-11; CORE_SCHEMA strips quotes | Medium, recurring | **Drop**; deny the edit tool instead (F2, F4) |
| NW2 MCP fork | Same | High, recurring | **Defer** unless MCP edits are wanted back |
| `migrate_sources.py` | Required for 3.0 | Medium, one-off | **Keep**; add F14/F15 cases |
| Worker symlinks (step 9) | RC7 | Low | Not assessed |

## Recommended design-doc edits

1. **5.12, I8, R10, section 7, M8:** remove `last_verified` as the clearing signal.
   Make R10 date-free, or drop it (F1).
2. **5.10 / RC3 / step 4:** list `session-start.sh:151-189` among the parsers
   replaced by `wikifm`. Add a text-preserving `set_field` to `wikifm`'s API and
   require it for scripts (F2, F4).
3. **N15 impact, N6, M4, R12 auto-fix, templates:** canonical date form
   `'YYYY-MM-DD'`. Correct the counts (115 lint, 92 session-start, 5 commits) (F2).
4. **5.10 profile, step 6:** allow continuation lines. R12 starts 🟡. Delete "no
   existing violations" (F3).
5. **Section 1 MCP gaps, 5.11 item 9, permission note, D9:** say that
   `string_replace`, `line_replace` and `vault.update` don't re-serialize. Record
   that MCP edits have been avoided since 2026-08-11. Prefer a deny or ask
   permission rule, matching both tool-name forms, over step 12 and NW2. Note
   `defaultMode: auto`, and that the transcript evidence misses about a third of
   the editing days (F4).
6. **Step 6 / maintain:** put the new auto-fix classes behind a flag autonomous runs
   don't pass. Update `llm-wiki-maintain/SKILL.md:74-75` (F5).
7. **5.1, R13, frontmatter table:** drop R13. If it's kept, name the fetcher and
   ingest-guide field changes and switch to a baseline list (F6).
8. **5.5, I4, R8, M6, D4:** make legends free prose and drop the rule and the
   migration step (F7).
9. **5.11 item 7:** surface lint failure at session start (F8).
10. **5.8, 5.11 item 6, R4, frontmatter table:** add the parent-trimming step.
    Point to the procedure from SCHEMA.md (template and live copy), the lint
    warning and ingest-guide ⑫. Add a post-validate reminder when a page crosses 200
    lines. Drop `split_from` and the R4 escalation (F9).
11. **Section 1, V1, 5.10:** fix the `vault.create` and "wiki version wins" claims.
    Keep R11 as the backstop (F10).
12. **I6/R9, S2 rotation, 5.11 item 2, M2, section 7:** page-slug collision check;
    rotation rewrites links; filter `action`/`dryRun`; read `log*.md`; add the
    attachment, raw-dir and root-file cases (F11–F15).
