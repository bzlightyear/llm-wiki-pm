# Sweep Window Design

created: 2026-10-22

A registry sweep has no rule for which time window to read from each source, so
each run picks one by guessing. This design adds a per-source "Swept through"
timestamp to the Sweep Registry. Each sweep reads from that point to the time of
the sweep, and moves the point forward only for sources it fully covered and
ingested. It also covers paging past the 15-result cap, how "daily" and "weekly"
requests relate to the window, and the migration of pm-wiki's registry. It also
folds in NW8: a maintenance run picks the daily or weekly brief from the run's
cadence and files it at that brief's path.

## Revision History

revised on: 2026-10-22
Folded in NW8, since without it a weekly run after daily runs would brief only
the last day. Added the "Cadence picks the brief" section, NW8's changes, and
four new choices, approved the same day. NW8's backlog item is closed as folded
into NW14.

revised on: 2026-10-22
Added a check for an explicit range that falls inside time already swept. In an
interactive run, the agent says so and asks whether to re-read or sweep only
since the last timestamp. Either way, items you set aside earlier aren't offered
again unless they changed. Added at your request after approval, so it counts as
approved.

## Status

Status: approved 2026-10-22, all nine choices under To approve; not
implemented.

## About This Document

- Backlog items: NW14, and NW8 folded in, in the
  [llm-wiki-pm Fork Backlog](llm-wiki-pm-fork-backlog.md).
- Related: a possible Slack capture skill that reads channels through Claude in
  Chrome, discussed 2026-10-22 and not started, which would need this window
  rule to know what is new.
- Scope: registry sweeps by `llm-wiki-maintain` and by `llm-wiki-brief` when it
  sweeps live sources. A single-page freshness check is out of scope and never
  moves a source's timestamp.

---

## What happens today

No skill defines the window a registry sweep reads.

- `llm-wiki-maintain` step ② says to sweep every registered source with the
  completeness guard, and says nothing about the time range.
- `llm-wiki-brief`'s "24h, widen to 48h if empty" and "last 7 days" filter the
  wiki's own `log.md`, not the sources.
- The completeness guard tells an agent to "widen the window" when a source
  comes back empty, with no limit, so a retry can read content an earlier run
  already ingested.
- The bound-output rule (`limit`≤15, narrow scope first) has no paging rule, so
  a busy source can be cut at 15 results and still be classed `hits`.

**What agents actually do.** The nine sweeps in pm-wiki's `log.md` from
2026-10-08 to 2026-10-22 each took their start date from the previous sweep's
log entry ("daily sweep 2026-10-08 to 2026-10-12"), so a skipped day was not
lost. That habit is unwritten, and it has three weak points:

- **One window for every source.** On 2026-10-12 you limited the sweep to
  meetings. The next sweep started from 10/12 for every source, so the
  Confluence pages seen on 10/12 were carried to 10/14 by hand ("4 pages carried
  from 10/12"). A source that is `failed` or set aside has its time lost the same
  way. This matters more once a source can fail on its own, such as Slack read
  through your Chrome.
- **Dates, not times.** Windows are day-granular ("10/21 to 10/22"), so the
  boundary day is read twice and dedup relies on the ingest's
  search-before-create. A source with items timestamped later the same day can
  also slip if a sweep ran mid-day and the next starts from the following date
  (the 10/15 sweep covered "to 10/15", the next "10/16 to 10/17").
- **It lives in `log.md`.** The log is free text and is rotated (it was on
  2026-10-06), so the previous window can be hard to find or gone.

## Proposal

### The timestamp

- The Sweep Registry gets a **Swept through** column: an ISO 8601 local time with
  offset, for example `2026-10-22T09:40-07:00`. It means every item in that
  source created or changed at or before that time has been seen by a sweep and
  either ingested or explicitly set aside.
- **A row is one timestamp.** Split a source into rows when its parts are swept
  or can fail separately, for example one row per Slack channel read through
  Chrome. Parts swept by one query share a row.
- Blank means never swept by this rule.

### Reading the window

- **From** the row's Swept through, **to** the time the sweep's first query for
  that source runs (the agent gets it from `date`). Record the "to" time before
  querying, so items posted during the sweep land in the next window.
- **Blank timestamp:** use the Active Sources "Last used" date for that source at
  00:00, or 7 days back if there is none, and say which in the ledger.
- **Created or changed.** An item is in the window if it was created or changed
  after Swept through. Use the item's last-modified time where the tool gives
  one (Notion `last_edited_time`, Confluence `lastModified`, a commit date). A
  meeting held before the last sweep whose notes were finished after it is then
  still caught.
- **Day-granular tools.** Many tools only take a date (`after:2026-10-21`), and
  some treat it as advisory. Query from the timestamp's date, then drop items
  whose own time is at or before Swept through. This applies the existing "date
  operators are soft" rule.
- **Retries stay inside the window.** The completeness guard's "widen the
  window" no longer applies to registry sweeps: vary terms, scope and syntax
  instead. Widening still applies to an open-ended search.

### Paging

- Keep the first page bounded (`limit`≤15, concise). **A full page means more
  remain:** fetch the next page until the window is covered.
- **Ceiling: 50 items per source per run.** Past it, process the oldest items
  first where the tool can sort, and advance the timestamp only to the newest
  item processed in unbroken order. Where the tool can't sort or page, don't
  advance. Either way, the ledger shows the source as `hits (partial, through
  <time>)`, and an autonomous run adds it to Needs Review.

### Moving the timestamp forward

Advance a source's Swept through to its "to" time only when, for that source:

- the sweep finished as `hits` or `empty-after-retries`, and
- every hit in the window was ingested, or set aside by you ("your scope call")
  or queued in the brief's Needs Review.

Don't advance it when the source is `failed`, when you left the whole source out
of this run (as on 2026-10-12), or when the run stopped before that source's
ingest finished. The next run then reads that source's missed time.

**When:** at the end of maintain step ③, in one edit to `MY-INTEGRATIONS.md`,
for each source that qualifies. A run that stops partway through moves no
timestamps for unfinished sources, so they are re-read next time.

**Who:** the agent, with the Edit tool. `MY-INTEGRATIONS.md` is already exempt
from the freshness gate, and the pre-write checkpoint covers it like any wiki
write.

### What "daily" and "weekly" mean

The window comes from the timestamps, not from the request. A daily run after a
three-day gap reads three days, and a weekly run reads from each source's own
timestamp. Cadence chooses only the brief: daily or weekly format and filing
path (see "Cadence picks the brief" below).

**An explicit range you give** ("sweep the last 3 days") is used as asked. It
advances a source's timestamp only if the range starts at or before the current
Swept through, so a range that leaves a gap never marks the gap as covered.

**A range over time already swept.** When an explicit range starts before a
source's Swept through:

- **Interactive:** before sweeping, the agent says how much of the range is
  already covered ("all sources are swept through 2026-10-22T09:40; the last 3
  days were already read") and asks whether to re-read the whole range or sweep
  only since each source's Swept through. One question covers all sources.
- **Autonomous:** sweep the range as asked, and note in the ledger which part
  was a re-read.
- **Set-aside items stay set aside.** In a re-read, an item named in an earlier
  sweep's "Not ingested" line in `log.md` isn't offered again unless its
  last-modified time is after that log entry. Items already in the wiki are
  handled by the ingest's search-before-create, as now.

### Cadence picks the brief (NW8)

**Today:** maintain step ④ always writes the daily brief and files it as
`briefings/YYYY-MM-DD.md`. With the window above, a weekly run after a week of
daily runs reads only since the last one, so its daily brief, which lists the
last 24–48 hours of `log.md`, covers one day. Without this section the window
would make weekly runs worse than today, where a guessed 7-day window at least
put a week of material in the brief. A weekly sweep on 2026-08-28 was filed at
the daily path and moved by hand.

**The cadence:**

- **Interactive:** from your words. "Weekly", "this week", "week in review" or
  "what did I miss this week" make it weekly. Anything else, including "maintain
  the wiki", is daily, with no question asked: every run since 2026-10-08 has
  been daily.
- **Autonomous:** from the scheduled task's prompt, by the same words. A task
  whose prompt names no cadence is daily.
- The cadence never changes the sweep window.

**The brief:**

- **Daily:** as now, `llm-wiki-brief`'s daily brief, filed as
  `briefings/YYYY-MM-DD.md`.
- **Weekly:** `llm-wiki-brief`'s weekly brief, which reads the last 7 days of
  `log.md`, so it covers the whole week even when daily runs brought the
  material in. Filed as `queries/weekly-brief-YYYY-MM-DD.md`, the path the
  weekly brief already uses and where pm-wiki's four weekly briefs are.
- **Both** get `lifecycle: dated-digest`, the Source Coverage ledger for this
  run's sweep (with windows), and, in autonomous mode, Needs Review. The weekly
  brief's own format has neither section today; maintain adds them, as it does
  for the daily brief.
- **Filing:** a maintenance run files the brief it writes, weekly as well as
  daily. The weekly brief's "offer to file" step applies only when you ask for a
  weekly brief on its own.
- **Index:** no entry needed. Lint exempts `dated-digest` pages from the
  `index.md` check. pm-wiki's index lists its weekly briefs anyway, and
  `lint --auto-fix` may keep doing so.
- **Log:** the weekly brief's own line, `brief | weekly | last 7 days | filed:
  yes`.

### Reporting

- The Source Coverage ledger line gains the window:
  `- Notion: hits (4 items), 2026-10-21T09:40 → 2026-10-22T08:15`.
- The sweep's `log.md` entry records each source's window where they differ, and
  one shared window otherwise.

## Options considered

| | A. Column in the registry (recommended) | B. Formalize the log habit | C. State file |
|---|---|---|---|
| Where | `MY-INTEGRATIONS.md`, beside each row | `log.md` sweep entries | e.g. `meta/sweep-state.json` |
| Per source | Yes | No, one window per run unless entries grow per-source lines | Yes |
| Survives log rotation | Yes | No | Yes |
| Visible to you | In the table you already edit | In the log | Only if opened |
| Code needed | None | None | A script or helper to read and write it |
| Machine-checkable | Lint can parse the column | Fragile | Easy |

B fixes nothing on the 2026-10-12 case. C adds a file and a script for a value
only agents and you write, so its one advantage, easy parsing, is matched by a
table column with a fixed format.

## Changes

**Skills and references** (prose only):

- `skills/llm-wiki-maintain/SKILL.md` step ② (lines 48–55): read each row's
  window as above, including the check for a range over time already swept.
  Step ③ (lines 57–60): advance timestamps at the end. Step ④ (lines 62–66):
  ledger lines carry the window, and the step becomes "Brief": decide the
  cadence, route to the daily or weekly brief, and file at its path. "Brief
  lifecycle convention" (lines 77–83) adds the weekly path.
- `skills/llm-wiki-brief/SKILL.md` weekly brief (lines 105–152): when run from
  maintain, it includes the Source Coverage ledger and Needs Review and is
  filed without the offer.
- `skills/llm-wiki-pm/references/source-discipline.md` completeness guard
  (lines 46–57): the window rule, paging and the ceiling, and that retries in a
  registry sweep don't widen the window.
- `skills/llm-wiki-pm/SKILL.md`: the Source-completeness summary (lines 104–108)
  names Swept through. The bound-output rule (lines 142–146) adds "a full page
  means more remain" for registry sweeps.
- `skills/llm-wiki-brief/SKILL.md` (lines 42–50): the ledger example shows the
  window. A brief that sweeps but doesn't ingest never advances a timestamp.
- `skills/llm-wiki-pm/templates/MY-INTEGRATIONS.md`: the new column and one
  sentence on what it means in the Sweep Registry header.
- `skills/llm-wiki-pm/references/ingest-guide.md` ⑨: one sentence that Active
  Sources "Last used" is the last ingest of any kind, not the sweep window.

**Code and tests:** none required. Optional, not proposed now: a lint info line
when a `Sweep? = yes` row's Swept through is over 7 days old or isn't a valid
timestamp (about 25 lines in `lint.py`, about 30 in `tests/test_lint.py`). It
would show a source that keeps failing or being skipped. Worth adding only if
that happens.

**Verification:** run one interactive maintenance sweep on pm-wiki after the
change and check that each ledger line shows its window, that timestamps moved
only for covered sources, and that the log entry matches.

## Migration

One pm-wiki commit after the skill change:

- Add the Swept through column to the Sweep Registry.
- Seed Notion, Confluence and GitHub with `2026-10-22T00:00-07:00`, the start
  of the day of the last sweep (log entry "daily maintenance sweep (10/21 to
  10/22)"). Its run time isn't recorded, so the start of that day re-reads
  10/22 at most once, and dedup covers that.
- Leave Slack and Email blank: they are `Sweep? = no`.
- Your fork's template gets the column, so a new wiki starts with it.

## Interactions

- **NW8:** folded in. Upstream has it as `anh-chu#12`, so it gets its own
  commit and fork changelog entry, to keep it easy to offer upstream on its own.
- **Slack through Chrome (if built):** one registry row per channel, each with
  its own timestamp. A channel whose page didn't load stays put while others
  advance.
- **Autonomous runs:** the rules need no answers from you. A partial or failed
  source stays behind and appears in Needs Review.
- **Upstream:** `llm-wiki-maintain`, the Sweep Registry and the completeness
  guard came from upstream (its CHANGELOG lines 129 and 166), so the edits touch
  upstream-owned prose. The fork changelog entry will mark this an upstream
  candidate for later.

## Cost

About 40 lines of skill and reference prose across six files, plus about 20 for
NW8 in the maintain and brief skills, one template column, one pm-wiki commit,
and two fork changelog entries. No code. Each sweep does
one extra edit to `MY-INTEGRATIONS.md`, and a busy source may take extra paged
queries that it should have been taking already.

## To approve

All approved 2026-10-22:

- Option A, the Swept through column.
- The 50-item ceiling per source per run.
- The 7-day default for a source with no timestamp and no Active Sources date.
- Leaving the lint check out for now.
- The migration seed values.

NW8, all approved 2026-10-22:

- Cadence from your words or the task's prompt, daily by default, with no
  question asked.
- Weekly briefs filed at `queries/weekly-brief-YYYY-MM-DD.md`.
- A maintenance run files its weekly brief without offering.
- The weekly brief from maintain carries the Source Coverage ledger and Needs
  Review.
