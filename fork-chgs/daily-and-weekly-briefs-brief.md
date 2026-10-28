# Daily and Weekly Briefs Brief

created: 2026-10-28

How your fork's skills say daily and weekly briefs are created, stored and
used, compared with the 18 briefs in pm-wiki's `briefings/` and their `log.md`
entries. It lists 13 issues and recommends seven groups of changes (A–G), one of
which revises the approved Sweep Window Design (NW14) before it is built.

## Revision History

revised on: 2026-10-28
Weekly briefs are now dated by the run day, not the Monday, and D's windows go
by when material was ingested rather than by calendar week (option 1), so a
weekly brief covers everything since the last weekly brief. The detailed rules
and each brief's contents are in the Sweep Window Design's 2026-10-28
revision.

## Status

Status: approved 2026-10-28, all four choices under To approve; not
implemented.
Backlog item: NW15 in the [llm-wiki-pm Fork Backlog](llm-wiki-pm-fork-backlog.md).
Related: NW14 and NW8 (the [Sweep Window Design](sweep-window-design.md)), NW4
(the action-items file), NW1 (`overview.md` freshness, including its "Pete
owes" list).

## About This Document

- Files read: `skills/llm-wiki-brief/SKILL.md` (§1 daily, §2 weekly),
  `skills/llm-wiki-maintain/SKILL.md` (step ④ and "Brief lifecycle
  convention"), `skills/llm-wiki-pm/SKILL.md` (§10 Catch Me Up),
  `references/schema-guide.md`, `references/citation-spec.md`,
  `references/source-discipline.md`, `scripts/lint.py`, `hooks/pre-write.sh`,
  `tests/test_write_hooks.py`, and in pm-wiki `briefings/`, `log.md`,
  `index.md`, `overview.md`, `Usage Guide.md` and `meta/contract.md`.
- Line numbers are as of commit 6ea6dd2.
- Anything marked unverified was not confirmed against a file.

---

## Recommendation in brief

The skills describe a brief built from `log.md`; the briefs you use are built
from each source sweep, in a format no skill defines. Write that format down (A),
settle one storage rule for weekly briefs before NW14 is built (B), and make
each brief carry the previous brief's Needs Review items forward (C), since
today a queued decision is lost once the next brief is written. Owed items are
left to NW1. D–G close smaller gaps: windows that leave material unbriefed,
edits to filed briefs, the index, and log entries.

## What happens

**Creation.** Brief §1 reads `log.md` for the last 24 hours, widening to 48. §2
reads the last 7 days. Both emit a Source Coverage ledger only when they sweep
live sources. Maintain step ④ routes to §1 after its sweep and ingest. NW14,
approved and not built, adds per-source sweep timestamps and has the run's
cadence pick the daily or weekly brief.

**Storage.** Dailies are filed as `briefings/YYYY-MM-DD.md` with
`lifecycle: dated-digest`. §2 offers to file weekly briefs as
`queries/weekly-brief-YYYY-MM-DD.md`. On 2026-10-28 you moved all five weekly
briefs to `briefings/` and listed every brief in `index.md` (pm-wiki
`log.md:366`).

**Use.** Lint exempts dated digests from the orphan, grounding, staleness and
index checks (`lint.py:710-716,904`), and the pre-write freshness gate exempts
them (`test_write_hooks.py:394`). `overview.md:15` points to two dailies as its
history. Pre-meeting briefs read the latest daily (`log.md:348`). The 10/19
weekly links three dailies. Nothing reads a brief's "You owe" or "Needs review"
list later.

## Findings

| # | Issue | Evidence | Impact | Sev |
|---|---|---|---|---|
| 1 | NW14 files weekly briefs at `queries/weekly-brief-…`, "where pm-wiki's four weekly briefs are" | sweep-window-design.md "Cadence picks the brief"; pm-wiki `log.md:366` | Building NW14 as written undoes the 10/28 move | High |
| 2 | Open items in a brief are never carried forward | "Needs review" in `2026-09-17.md`; `log.md:124,194,216`; "You owe" in every recent daily | Queued decisions and owed items are lost after the next brief. CFP-8814, in the 9/17 list, is on no wiki page (unverified whether dropped or settled) | High |
| 3 | Real dailies don't match the skill's format | Skill: New/Updated/Decisions/Questions/Warnings from `log.md` (SKILL.md:73). Actual: Headline / Decisions / Open, waiting / You owe / Source Coverage, from raw records | Output varies by run; `Usage Guide.md:5` names sections that don't exist | High |
| 4 | Some swept material appears in no brief | The 10/28 sweep covered 10/19–10/28 but its weekly brief stops at 10/23 (`log.md:356`); seven 10/26–10/27 transcripts were never briefed; no 10/23 daily | Gaps in the record of what happened | High |
| 5 | The skill's daily window is 24–48h; actual dailies run "since last sweep" | e.g. 10/08 to 10/12. NW14 fixes the sweep window, not a brief asked for on its own | A standalone daily misses gaps | Med |
| 6 | No rule on editing a filed brief | 10/08, 10/14, 10/15, 10/17 "updated in place" (`log.md:50,198,293`); 10/12 "left as is (dated digest)" (`log.md:258`) | A brief means "as of that day" sometimes, "as of now" others | Med |
| 7 | Index entries for briefs aren't maintained | Lint skips digests in its index check (`lint.py:904`); NW14 says "no entry needed"; 5 dailies were missing until 10/28 | They drift out of the index again | Med |
| 8 | The digest definition no longer fits | `citation-spec.md:92`: a digest "summarizes the wiki", `sources: []`. Recent dailies list raw sources and carry `[source:]` markers | Unclear whether briefs should cite | Med |
| 9 | Weekly briefs have no lifecycle rule or filing format | §2 never mentions `lifecycle`; `weekly-brief-2026-08-21.md` uses the query Question/Answer layout | Weeklies avoid the orphan count only by hand | Med |
| 10 | Weekly file dates follow no rule | 08-07, 08-21, 08-28 use the creation date; 08-31 and 10-19 the week start; 08-28 is "Week of 08-21", overlapping 08-21; 10-19 was written 10-28 | Hard to find a given week | Low |
| 11 | Brief log entries vary | `brief \| daily \| … \| filed: yes` until 10/15, then only "- Brief:" under the ingest entry; the weekly entry names the old `queries/` path; core §10 logs `catchup` | Briefs can't be found in the log reliably | Low |
| 12 | Weekly briefs re-sweep instead of reading the dailies | The 10/19 weekly's `sources:` repeats the dailies' raw records plus one | Duplicate work; NW14 fixes the re-sweep, nothing says to read the dailies | Low |
| 13 | Dailies have empty `tags:` | Every daily since 09-17 | Only tag digests are affected; no action proposed | Low |

## Recommendations

**A. Define the brief you use (fixes 3, 5, 8).**
- Rewrite brief §1 as two kinds:
  - **Sweep brief:** from maintain, or whenever sources are swept. Covers
    everything since the last brief, from NW14's timestamps. Sections: Headline,
    Decisions, Open/waiting, You owe, Needs Review, Source Coverage.
  - **Wiki-only brief:** asked for with no sweep. Reads `log.md` from the last
    brief's end, not a fixed 24–48h.
- `citation-spec.md` Grounding: a digest needs no primary source, but may
  declare raw records and should then use `[source:]` markers.
- pm-wiki `Usage Guide.md`: name the new sections.
- Prose only; no tests.

**B. Revise NW14 before building it (fixes 1, 9, 10).**
- Weekly briefs go to `briefings/weekly-brief-YYYY-MM-DD.md`, dated by the
  run, with the period in the title. A Monday date could give two weekly briefs
  the same name once periods start mid-week (D).
- Brief §2 ⑧ and maintain's "Brief lifecycle convention" state that path,
  `lifecycle: dated-digest` and the daily brief's section layout.
- Update the example in pm-wiki `meta/contract.md`.
- Don't rename the three older weekly briefs; the rule applies from now on.
- No code: `test_write_hooks.py:394` already exempts a digest at either path.

**C. Carry Needs Review forward (fixes 2).** Each brief starts by reading the
previous brief's Needs Review; each item is marked resolved, with where it went,
or carried forward. In brief §1/§2 and maintain step ④. These are decisions
about the wiki a run left for you (possible contradictions, splits, unclear
names), which NW1 doesn't cover.
- **Owed items belong to NW1.** Where action items live is NW1's open problem,
  and a brief's "You owe" is one more copy of them, beside `overview.md`'s
  "Pete owes", the crystallize pages and NW4's action-items file. Until NW1 is
  designed, a brief's "You owe" reads from "Pete owes" and keeps no list of its
  own.

**D. Close each window (fixes 4, 12).** Windows go by when material was
ingested, not by calendar week, since `log.md` dates entries by ingest and a
meeting's notes can arrive after its week. A daily brief covers from the latest
brief's end to the run; a weekly brief from the latest weekly brief's end. Items
are grouped by meeting date inside the brief. A weekly brief reads the dailies
in its window, or crystallize pages and `log.md` when there are none, and sweeps
only from NW14's timestamps. Detail in the Sweep Window Design's "Brief
windows" and "What each brief holds".

**E. Freeze briefs after their day (fixes 6).** Later corrections go on the page
that owns the fact and into the next brief's carry-forward; same-day corrections
are fine. One sentence each in schema-guide `dated-digest` and brief §1. Depends
on C, without which editing in place is the only way to close an item.

**F. Leave briefs out of the index (fixes 7).** Replace pm-wiki's
`## Briefings` list with one fixed line: "Briefs: `briefings/`, named
`YYYY-MM-DD` (daily) and `weekly-brief-YYYY-MM-DD` (weekly)."
- **Why:** Orient reads `index.md` before every write. Briefs are 18 of its 325
  entries now and would be about 200 more a year, close to 40% of the index,
  for pages agents find by date, by folder or through wiki-search, never
  through the catalog. Nothing depends on the list: lint already skips dated
  digests, and links to briefs point at the files.
- **Lint:** no change; it already agrees with NW14's "Index: no entry needed".
- **Check:** whether `worker-link-validator` reports dated digests as index
  gaps; if it does, give it lint's exemption.
- **Migration:** remove the list by hand, which reverses part of the 10/28
  index change; lint never removes index entries.
- **Brief skill:** the brief and maintain skills don't add briefs to
  `index.md`.

**G. One log format (fixes 11).** `## [date] brief | daily|weekly|catchup |
<window> | filed: <path>` as its own entry, even inside a maintenance run. Brief
§1/§2, maintain step ⑥, core §10. Old entries stay as they are.

**Order.** B and G with NW14's prose changes, since they touch the same lines;
then A; then C and E together; then F, which can go any time.

## To approve

All four approved 2026-10-28.

1. **Where owed items live (C).** NW1 decides. Until then a brief's "You owe"
   reads `overview.md`'s "Pete owes", and C carries forward Needs Review only.
2. **Weekly date (B).** The run day. First approved as the week's Monday, and
   changed the same day with option 1's windows (D).
3. **Index (F).** Briefs stay out of `index.md`, with one fixed pointer line.
4. **Edits after filing (E).** Frozen at the end of their day.
