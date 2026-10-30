# NW Backlog Review

created: 2026-10-29

A re-check of the six open items in the
[llm-wiki-pm Fork Backlog](llm-wiki-pm-fork-backlog.md) against your fork and
pm-wiki as they are on 2026-10-29. Each item gets the finding that motivated it,
current evidence, a verdict and a fix analysis redone from scratch. It ends with
the original analysis's findings that nothing picked up, and a priority order.

## Status

**Status:** applied to the backlog on 2026-10-29.
- **Rewritten:** NW1 (split into NW1a and NW1b), NW7 and NW11 got a
  "Reviewed" bullet with the new scope, and NW9 got its re-measurement.
- **Closed:** NW2 (dropped) and NW4 (merged into NW1a).
- **Added:** NW17 (design step 11).
- **Decided 2026-10-30:** NW9 phase 2 drops the map's Org Chart table.
- **Done 2026-10-30:** the pm-wiki memory's reasons were rewritten.
- **Still open:** the NW1a decisions.

## About This Document

- **Open items reviewed:** NW1, NW2, NW4, NW7, NW9, NW11. NW3, NW5, NW6, NW8,
  NW10 and NW12–NW16 are closed and not reviewed.
- **Sources:** the
  [Sources and References Design Prompt](sources-and-references-design-prompt.md)
  (the original analysis, findings 1–20), the
  [Sources and References Design](sources-and-references-design.md) (which
  corrects some of them in section 0), the
  [Sources and References Review](sources-and-references-review.md), the
  [llm-wiki-pm Fork Changelog](llm-wiki-pm-fork-changelog.md), the NW6 and NW5
  analyses, your fork's code and pm-wiki.
- **How evidence was gathered:** read-only against pm-wiki, the running
  wiki-search server and GitHub. Lint ran on a scratch copy of the wiki, so
  nothing was written to pm-wiki.
- **Verdicts:** still relevant as written / relevant but needs rewriting /
  resolved by later work / no longer worth doing.

---

## Summary

| Item | Verdict | Change since it was written |
|---|---|---|
| NW1 | Relevant, needs rewriting | `overview.md` was condensed by hand (70 KB → 23 KB), but the root cause is untouched and the "Pete owes" bullet is accreting again |
| NW2 | No longer worth doing | The deny rule, MCP hook matchers and checkpoint commits cover it. 0 escaped links in pages |
| NW4 | Merge into NW1 | The file was last edited 2026-09-04. Briefs' "You owe" replaced it in practice |
| NW7 | Relevant, needs rewriting | M1 still does harm. Snapshots are gone, so M1 is the only collision, and lint could prevent the next one |
| NW9 | Still relevant as written, and worse | Reverse-link gaps grew from 3 to 5. The SCHEMA org chart hasn't changed since 2026-08-07 |
| NW11 | Relevant, needs rewriting, much smaller | Core `SKILL.md` now carries every AGENTS.md behavioral rule. What's left is dangling references |

---

## NW1. Orient content and `overview.md` freshness

### Finding

From the fork changelog's ISSUE-1 and ISSUE-2 (2026-08-30) and finding 13 of
the original analysis: once an action item or citation is written, no workflow
step goes back to it. Crystallize digests freeze action-item status at
creation. `overview.md` became the de facto tracker and grew inline
`**Update DATE**` clauses (70 KB). The indexer's dormant Overview Regeneration
mode would replace the curated structure.

### Current evidence

- **The symptoms were cleaned up by hand, not fixed.** pm-wiki commit
  `c4b4be6` (2026-10-06, "overview condensed") removed 1,181 lines from
  `overview.md`. It is now 23,321 bytes and 2,473 words (it was 8,626 words on
  2026-10-02). It has 0 inline `**Update/Resolved/New/Correction/Confirmed
  DATE**` markers and no Action Items section.
- **The accretion is coming back in a new shape.** Delivery (Q4 2026) has one
  "Pete owes" bullet that lists about 10 items in a single run-on sentence. It
  mixes in a closed item ("The 10/22 deck review happened"), and five more
  "Pete owes" mentions sit in other sections. Same cause, new location.
- **The root cause hasn't changed.** `crystallize-guide.md` still only creates
  digests, and line 96 still sends action items to "Roadmap pages", which aren't a
  page type. `update-guide.md` still never targets digests. Of 160 crystallize
  pages, 74 carry pending or open action-item rows and 12 show any done
  marker. 9 have been edited more than once since 2026-10-01.
- **Briefs depend on it.** `llm-wiki-brief` line 76 builds "You owe" from
  `overview.md`'s "Pete owes" "(until NW1)". The latest weekly brief
  (2026-10-28) has a "You owe" section.
- **The structure has diverged from the template.** pm-wiki's `overview.md`
  has 8 sections (Where Pete sits, Market position, Active bets, Delivery,
  Customers to watch, Org context, Open questions, Key entities).
  `templates/overview.md` has 5 (Current State, Active Bets, Open Questions,
  Recent Shifts, Key Entities).
- **The indexer is unchanged.** `.claude/agents/worker-wiki-indexer.md` still
  has Overview Regeneration (Theme Clusters and so on) behind its "> 7 days
  stale" trigger. It is still dormant, and checkpoint commits make it undoable.
- **Orient is lighter.** It is about 9,900 words now (core `SKILL.md` 3,668,
  `overview.md` 2,473, `SCHEMA.md` 2,555, `index.md` 813, the last 30 log
  lines 364), down from about 15,400. The cost argument in NW1 and NW11 has
  mostly gone away.
- **A deferred freshness question was dropped.** Design section 5.12 left the
  120-day `last_verified` warning "for NW1's review of freshness signals", but
  the NW1 text never mentions it. Session-start also reports 100 stale pages
  (`updated:` > 30 days) every session. Most are person and product entities
  that haven't changed, so the count is noise rather than signal.

### Verdict

**Relevant, needs rewriting.** Its two halves differ in size and urgency, so
split it:

- **NW1a, action-item tracking.** This is the real problem, and NW4 merges into
  it.
- **NW1b, overview structure, the indexer and freshness signals.** This is
  small, and nothing breaks today.

### NW1a fix analysis: where action-item status lives

| Option | How it works | Weakness |
|---|---|---|
| A. One living tracker page | `queries/open-action-items.md` holds status. Crystallize appends new items, Update closes them, overview and briefs link or read it | One more write per ingest that has action items |
| B. Status sync in digests | `update-guide.md` targets digests, and lists are generated on demand by scanning all digests | Closing one item can touch several digests. 160 digests to back-fill. Nothing can check it |
| C. Overview's "Pete owes" as the source of truth | Formalize today's practice in the template and skills | Only covers your own items. A run-on bullet is already the failure mode, and Orient pays for every line |

**Recommended: A.** It is the only option where status has exactly one
writable copy, and it is NW4's option 1 already half-built. Digests stay
point-in-time: their Action Items table is labeled "as captured" and never
updated. That is legitimate for a meeting record, and it removes the
expectation that they stay current.

- **Where it lives:** a pm-wiki page in `queries/` with standard frontmatter
  (`lifecycle:` not dated-digest), so lint, the hooks and `index.md` cover it.
  It gets a template in `templates/`.
- **Format:** one table row per item. Columns: ID, item, owner, due, status
  (open, done, dropped), source (a wikilink to the digest), closed date.
  Closed rows move to a "Closed (last 30 days)" section and then drop off, with
  git as the history.
- **Who writes it:**
  - `crystallize-guide.md`: a new step appends the digest's items.
  - `update-guide.md`: a statement that an item is done closes the row.
  - `llm-wiki-maintain`: after ingest, reconcile items the sweep shows closed.
  - `llm-wiki-brief`: "You owe" reads the tracker, and line 76's "(until NW1)"
    is removed.
- **overview.md:** "Pete owes" becomes one line with a count and a link.
- **Reporting:** optional phase 2 reuses I8's revisit pattern. Lint lists open
  items past their due date (🔵) in `_status.md`. Leave it out of phase 1
  until the tracker has been in use for a few weeks.
- **Config, code and tests:** none in phase 1. These are doc and template
  changes. Phase 2 adds a lint rule with tests in `tests/test_lint.py`.
- **Migration:** seed from `overview.md`'s "Pete owes" mentions and the open
  rows in the 74 digests. The digest rows need your triage, since most are
  probably done or dead. Recommendation: seed only items you own or are
  waiting on, and leave other people's items in their digests.
- **Interactions:** retires NW4's file. NW9 doesn't overlap. Changes the
  brief's "You owe" source.
- **Cost:** one design pass, about 6 doc edits and a template. The ongoing
  cost is one extra edit per ingest that has action items.
- **Decisions for you:** the owner scope (only your items, or all items), and
  whether to back-fill from digests or start fresh from today.

### NW1b fix analysis

- **Template:** make `templates/overview.md` the curated structure in use,
  generalized, since the template ships to any new wiki.
- **Indexer:** remove the Overview Regeneration mode, keeping index rebuilds.
  Producing a curated synthesis by rule doesn't work, and the mode has never
  run. This is cheaper than teaching the indexer the new structure.
- **Freshness signals:** drop the session-start stale count from the health
  line, or limit it to pages that log activity touched (the core skill's
  Orient ⑥ already states that narrower rule). Retire the 120-day
  `last_verified` warning, since design section 5.12 showed the field moves
  with ordinary edits and proves nothing.
- **Cost:** small. Tests change for session-start's health line.

---

## NW2. Fork `wirux/mcp-markdown-vault`

### Finding

Finding 7 and finding 10 of the original analysis, review F2 and F4: the MCP's
full-file round-trip escapes `[[` (#47) and rewrites dates as timestamps (#49),
and MCP writes skipped the hooks.

### Current evidence

- **Settings:** `~/.claude/settings.json` denies both name forms of
  `wiki-search__edit` and asks before both forms of `vault`. The pre-write and
  post hooks match `mcp__.*wiki-search__(vault|edit)`.
- **Checkpoints:** since NW12, checkpoint commits cover every write after a
  session's first, MCP writes included.
- **No damage since:** 0 pages contain an escaped `\[[`.
- **Upstream:** 2.3.1 was released on 2026-10-03, and the maintainer merged an
  outside PR (#48, re-embedding skip). The maintainer is active again, but
  #45, #47 and #49 are still open with no maintainer reply.
- **NW12's reason is gone:** snapshots were dropped, not filtered.

### Verdict

**No longer worth doing.** Close it with a reopen trigger: "if upstream fixes
#47 and #49, lift the D9 deny rule, which is a settings change with no fork."
The deny rule costs nothing day to day, because the Edit tool covers every
`edit` operation.

**A side observation, not part of NW2:** `hooks/wiki-search.sh` runs the first
`dist/index.js` that `find` returns under `~/.npm/_npx`, so the version that
runs is whatever npx last cached, not a pinned one. It hasn't caused a
problem, so this is only worth knowing.

---

## NW4. The action-items file

### Finding

From review F15: a root-level action-items file sits outside lint, the hooks
and `index.md`, and no skill defines how it is updated.

### Current evidence

- **The file:** 408 lines. Its last full regeneration was 2026-08-21, and its
  last commit was 2026-09-04, eight weeks ago. No wiki page links to it.
  `log-2026.md` has 72 action-item mentions from August and September.
- **Its replacements:** briefs' "You owe" and overview's "Pete owes" took over
  its job in October, without anyone deciding that.

### Verdict

**Merge into NW1a.** NW4's option 1 is NW1a's option A, and option 2 is
NW1a's option B, which is rejected. After NW1a seeds the tracker, move the old
file to `_archive/` under the naming rule from NW7, or delete it. Its content
is in git either way.

---

## NW7. No link search finds every incoming link

### Finding

From the NW6 analysis, M1 and M4. `backlinks.py` skips `briefings/` and the
root files. The MCP lags, and it resolves a page's links to a same-name file
in `_archive/` (M1). The docs don't say which tool to use.

### Current evidence

- **M1 still does harm.** `concepts/cfp-ai-tokenization-history-2026-08-10.md`
  and `_archive/cfp-ai-tokenization-history-2026-08-10.md` share a name.
  - The MCP's `view(action=backlinks)` returns `count: 0` for the live page
    (2026-10-29, `watcherState: active`).
  - Grep finds 3 linking wiki files: `index.md`, a briefing and the topic's
    history page.
  - `backlinks.py` finds only the history page.
- **`backlinks.py` scope:** still `WIKI_DIRS = ["entities", "concepts",
  "comparisons", "queries"]`. `briefings/` and the root files other than the
  log hold 859 wikilinks.
- **Only one collision is left.** `_archive/` now holds 6 files, since NW12
  removed snapshots. M1 is the only same-name collision. Three of the other
  five also use bare names, so a future page with one of those names would
  collide.
- **Nothing reports it:** lint's page set leaves out `_archive/`, so R9 (one
  ID names two files) never sees M1. Lint on the scratch copy reported 0
  errors.
- **The docs are unchanged.**
  - The core skill's §4 ① and `update-guide.md` name `backlinks.py`.
  - §6 Archive still says "move to `_archive/` preserving path". In practice
    files sit flat in `_archive/`, so the rule doesn't say what name a move
    keeps.
  - The vault contract (template and pm-wiki copy) still says "Incoming links
    → `view.backlinks`".
- **Renames:** why the 2026-10-01 rename needed two reindexes is still not
  known.

### Verdict

**Relevant, needs rewriting.** Narrow the scope to what's still true, and
replace the "decide a naming rule" step with a check.

### Fix analysis

1. **`backlinks.py` reads `briefings/` and the root `.md` files,** except
   `log*.md`, which is history, and `_status.md`, which is generated. `raw/`
   and `_archive/` stay out. Tests go in the existing `backlinks.py` tests.
2. **R9 reads `_archive/` file names** and reports a stem shared with a live
   page or record (🔴, since there would be one existing violation, M1, fixed
   in step 3 first). This prevents the next M1 mechanically, which a naming
   rule in prose can't do.
3. **Rename M1's archived copy.** Use the `-archived` suffix,
   `_archive/cfp-ai-tokenization-history-2026-08-10-archived.md`, rather than
   another date, because the live slug already ends in a date. Then check that
   no link targets the archived copy by name. Since NW12, git is the undo and
   `_archive/` holds retired pages rather than snapshots. A rename changes the
   path, not the content, so it doesn't break `citation-spec.md`'s
   immutability, which is about content. Say so in one sentence in
   `citation-spec.md`.
4. **Docs:**
   - §6 Archive: "move to `_archive/<slug>.md`; R9 reports a name clash".
   - Name `backlinks.py` in §6 and the Supersede steps.
   - Vault contract: "Incoming links → `backlinks.py`; `view.backlinks` can
     lag and misresolve same-name files".
5. **Drop the rename investigation.** Once `backlinks.py` is the documented
   search, the MCP's rename behavior only affects ad-hoc queries.

- **Cost:** small. About 20 lines of code across two scripts, tests, 4 doc
  edits and a one-file wiki rename, committed separately (per the
  rename-commit rule).
- **Interactions:** NW4's file archive, if you choose that, uses this rule.

---

## NW9. Org structure is kept in three places

### Finding

Found in a session on 2026-09-26. Three copies of who reports to whom: the
SCHEMA Domain org chart, `concepts/relationship-map.md`, and person pages'
`reports_to`, `direct_reports` and `peers` fields. Nothing keeps them in step,
and an ingest was seen to update only the map.

### Current evidence (2026-10-29)

- **The SCHEMA org chart is untouched.** `git blame` dates every line of
  SCHEMA's org structure (lines 13–35) to 2026-08-05 through 2026-08-07.
  Orient still reads it every session.
- **Person-page fields:** 58 pages carry `reports_to` (it was 55).
- **Reverse links are getting worse:**
  - 14 non-mutual `peers` (unchanged).
  - 5 `reports_to` with no `direct_reports` reverse (it was 3).
  - 1 `direct_reports` with no `reports_to` reverse.
  - 4 values that name no person page.
- **The map:** 42 wikilinked rows in its tables, last changed 2026-10-15.
- **Nothing reads the fields:** lint and the other scripts never reference
  `reports_to`, `direct_reports` or `peers`.
- **The creation steps are unchanged.** Core skill §2 ⑫ still names only the
  map's `direct_reports` cell. The "3+ person entities" creation rule appears
  in the SCHEMA template, the core skill and the persona skill.

### Verdict

**Still relevant as written, and getting worse.** The measurements support
the backlog's lean toward the person-page fields as the source of truth. One
part changes: because Orient is now much lighter, the proposal to have Orient
read the map's org-chart section isn't needed. Replacing SCHEMA's chart with a
pointer is enough. That also avoids the upstream "discuss first" change to
Orient's reading list.

### Fix analysis (phase 1, mechanical)

1. **Lint reciprocity check (🟡):**
   - `reports_to` ↔ `direct_reports` and mutual `peers`.
   - Allows more than one manager.
   - Treats `null`, `unknown` and an empty list the same.
   - Reports values that name no person page.
   - `--auto-fix=content` fills in a missing `direct_reports` or `peers`
     reverse, never `reports_to`.
   - It reads the fields through `wikifm`, and the tests go in
     `tests/test_lint.py`.
2. **§2 ⑫, the persona skill and the SCHEMA template:** changing someone's org
   placement updates both pages' fields in the same edit, and the map if it
   keeps an org table. The creation rule counts internal people.
3. **Replace pm-wiki SCHEMA's org chart with a pointer** ("org structure: the
   person pages' `reports_to` fields; see [[relationship-map]]"), keeping
   role, products and competitors. Do the same in the template's guidance.

### Phase 2, a decision for you

Either generate the map's Org Chart table from the fields, or drop the table
and keep the map for interaction tiers and history. Dropping it is cheaper,
and it removes a copy without building a generator. The body Relationships
bullets go the same way: drop the `reports_to` and `direct_reports` lines and
keep the prose.

- **Cost of phase 1:** about 60 lines of lint code and tests, 4 doc edits, one
  SCHEMA edit, and an auto-fix run plus review of the 5 reports_to gaps by
  hand.

---

## NW11. Skills cite an `AGENTS.md` that wiki sessions never load

### Finding

From the NW10 analysis (2026-10-02) and finding 14. Sub-skills defer to
`AGENTS.md`, which loads only in sessions started in your fork's folder. The
worry was that rules stated only in `AGENTS.md` never reach wiki sessions.

### Current evidence

- **Every behavioral constraint is now in core `SKILL.md`:**

  | AGENTS.md rule | Core `SKILL.md` line |
  |---|---|
  | Show the diff first; confirm at 5+ pages | 289–290 |
  | Confirm mass updates at 10+ pages | 246, 378 |
  | New tags go in SCHEMA first | 122 |
  | Minimum 2 outbound links | 377 |
  | Checkpoint before destructive ops | 276–282 |
  | Verify writes | 297 |
  | Never mutate `raw/` | 158, 372 |
  | Dedup before capture | 64, 220 |

  The "Snapshot before destructive ops" rule that NW11 cited was replaced by
  "Checkpoint before destructive ops", which is in both files.
- **The references still dangle.** Four sub-skills refer to it 7 times:
  research 16, brief 34, 146 and 245, persona 145, prd 22 and 124.
  `citation-spec.md` line 5 also names it, but that line is accurate, since
  `AGENTS.md`'s Source Attribution does point to the spec.
- **`AGENTS.md`'s Wiki Path Resolution is current** (corrected 2026-10-30).
  This review first called its `.wiki-path` lines stale. NW5 removed the
  projects' `.wiki-path` files, but `.wiki-path` still marks a project that
  uses another wiki, and the core skill and hooks read it the same way.

### Verdict

**Relevant, needs rewriting, and much smaller.** The rules already reach wiki
sessions. "Ruled out: folding the rules into core `SKILL.md`" has in effect
already happened. Reading `AGENTS.md` during Orient would only add words
that duplicate the skill.

### Fix analysis

1. **Retarget the 7 sub-skill references** to the core skill:
   - "Orient per AGENTS.md" → "Orient per core `llm-wiki-pm` (Orient Every
     Session)".
   - "Behavioral Constraints (per AGENTS.md)" → "(per core `llm-wiki-pm`
     Rules)".
   - Leave `citation-spec.md` as it is.
2. **Drop the Orient-reads-AGENTS proposal.**

- **Cost:** 7 line edits. No code or tests.
- **Interactions:** none.
- **Done 2026-10-30:** changelog PATCH-29.

---

## Findings nothing picked up

Design steps 0–10b address all 20 findings of the original analysis. Checked:
- **Workers:** the agents are user-level symlinks, and pm-wiki's
  `.claude/agents/` copy is gone (finding 18).
- **Tests and the launcher:** the smoke test and launcher fix landed in step 1
  (finding 19).
- **Docs:** README, CONTRIBUTING and GETTING_STARTED no longer mention
  `private: true` (finding 20).
- **MCP coverage:** the MCP hook matchers landed in step 3 (finding 7).

The items below weren't on the backlog:

1. **Design step 11 is ready and not tracked.** It promotes R3 and R6 to 🔴,
   and R12 once M8 shows 0 violations. Lint on a scratch copy (383 pages)
   gives I1, I2 and I3 = 0, 0 errors, and no R3, R6 or R12 hits. The only
   source-rule output is 8 R10 🔵 secondhand pages, which is expected. Your
   memory notes mark step 11 as the point to decide whether mechanical
   auto-fixes run unattended. **Recommendation: add it as NW17 and do it.**
2. **The freshness signals left to NW1** (design section 5.12) were never
   recorded there. They are now in NW1b above.
3. **A pm-wiki project memory has a stale reason.** "Don't allowlist wiki write
   tools" says MCP writes get no pre-write snapshot. Since NW12, checkpoint
   commits cover them. The rule itself still holds, so only the reason needs
   correcting. Agents in pm-wiki sessions read that memory.
4. **Step 0's residue:** pre-rewrite commits still resolve by ID on GitHub. Your
   memory notes making the fork private as the fix. That's a repo setting, not
   backlog work, so it's listed here only for completeness.

---

## Priority Order

1. **NW11 (rewritten).** Minutes of work. It fixes references that lead
   nowhere in wiki sessions.
2. **NW1a with NW4 merged: the action-item tracker.** It has the highest daily
   impact. "You owe" and "Pete owes" are what you act on, and they are
   re-accreting. It needs your two decisions, then a short design, then doc
   edits.
3. **NW9 phase 1: the reciprocity lint and wording.** The drift is measurably
   growing, and an ingest was seen getting it wrong. The work is mechanical
   and self-contained.
4. **NW17: design step 11.** Small and unblocked. It locks in the zeroed
   invariants before new drift starts. It ranks below NW9 because hooks and
   lint already warn on these rules.
5. **NW7 (rewritten).** The harm is real but narrow: one page's backlinks, and
   archive operations are rare. The R9 extension stops a repeat.
6. **NW1b: overview template, indexer and freshness signals.** Nothing is
   broken: the indexer mode is dormant and undoable. Do it after NW1a settles
   what `overview.md` holds.
7. **NW9 phase 2: the map's org table.** Decide after phase 1 has run for a
   while.

**Close:** NW2, with a reopen trigger.

## To approve

- Backlog edits:
  - Rewrite NW1 (split into NW1a and NW1b), NW7 and NW11 per this review.
  - Close NW2 and NW4 (NW4 merged into NW1a).
  - Add NW17 (design step 11).
  - Add the side findings above where you want them.
- NW1a decisions: the owner scope, and back-fill or a fresh start.
- NW9 phase 2: generate the map's org table, or drop it.
- Whether to correct the pm-wiki memory's stale reason.
