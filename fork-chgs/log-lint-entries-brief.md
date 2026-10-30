# Log Lint Entries Brief

created: 2026-10-29

Every `lint.py` run outside `--json` appends an entry to pm-wiki's `log.md`,
and those entries are about half the log. This brief re-assesses backlog item
NW3 against your fork as it is now: it measures the entries, lists every reader
and writer of `log.md`, weighs the two options from the backlog and four new
ones, and looks at what a log rotation does to brief windows. It recommends
logging only lint runs that change pages (option 3), and having rotation keep
the last 30 days in `log.md` (option R2), with R1's rotated-log sentence in the
brief skill as well.

## Revision History

revised on: 2026-10-29
Recorded options 3, R2 and R1 as approved and implemented in your fork
(changelog PATCH-28), with pm-wiki's existing lint entries left in place. The
lint tests are two, not three: one test covers both runs that change nothing.
R1's rotated-log rule in the brief skill is the one addition to the prose
list.

## Status

Status: options 3, R2 and R1 implemented 2026-10-29 (changelog PATCH-28).
pm-wiki unchanged; its 57 lint entries stay in its log.
Backlog item: NW3 in the [llm-wiki-pm Fork Backlog](llm-wiki-pm-fork-backlog.md).
Related: review finding F14 in the
[Sources and References Review](sources-and-references-review.md), NW15 (brief
windows, the [Daily and Weekly Briefs Brief](daily-and-weekly-briefs-brief.md)),
NW1 (Orient content), NW16 (the crystallize lint warning), NW14 (sweep windows).

## Recommendation in brief

Keep NW3's direction, but not either of its options as written.

- **Lint logs only when it changed pages (option 3).** A plain run, and an
  `--auto-fix` run that fixed nothing, write their report to `queries/` and
  nothing to `log.md`. An `--auto-fix` run that fixed something appends one
  entry listing the fixes, since it is a wiki write like any other. That would
  have cut the 57 lint entries since the last rotation to 8. No reader uses the
  others: the session-start health check, the per-day report and git already
  hold what they say.
- **Rotation keeps the last 30 days (option R2).** Fewer entries only delays
  the next rotation, from about January 2027 to about March. When it comes,
  `session-stop.sh` today moves the whole log, so the next session's Orient
  reads an empty log and the next brief can't find the previous brief's line.
  Keeping the last 30 days of entries in the new `log.md`, at most 250, fixes
  that for every reader at once, without a rule about rotated logs in each
  skill.

The old reason for NW3 is gone: F14's risk, migration step M2 missing dates in
a rotated log, ended when `migrate_sources.py` learned to read `log-*.md` and
step 10b ran on 2026-09-30. The reasons that remain are the log's signal to
noise for Orient and the briefs, and the rotation's effect on brief windows,
which PATCH-23 created.

## What happens

`lint.py` (`skills/llm-wiki-pm/scripts/lint.py:1036-1044`; the backlog's
`772-780` has moved) appends, after writing the report:

```
## [YYYY-MM-DD] lint | <N>E <N>W <N>I <N>F
- Report: queries/lint-YYYY-MM-DD.md
- Auto-fix applied <N> repairs        (only with --auto-fix)
```

It does so whenever `log.md` exists, unless `--json` is given. The report file
is one per day and each run overwrites it, so a day's report holds only its
last run. The reports are tracked in pm-wiki's git (59 files, 2026-08-03 to
2026-10-29), and checkpoint commits catch most intermediate versions.

`session-stop.sh` (lines 28-56) counts lines starting `## [` at every session
end. Over 500, it renames the whole file to `log-YYYY.md` (or
`log-YYYY-part-N.md`) and writes a new `log.md` holding only a header. It last
ran on 2026-10-06.

### Measured

From pm-wiki's `log.md` and `log-2026.md`, 2026-10-29.

| | `log-2026.md` (2026-08-03 to 10-06) | `log.md` (2026-10-06 to 10-29) |
|---|---|---|
| Entries | 511 | 111 |
| Lint entries | 273 (53%) | 57 (51%) |
| Days with entries / with lint | 41 / 34 | 14 / 12 |
| Lint entries per lint day | 8.0 | 4.75 |
| Most in one day | 37 (08-11) | 12 (10-08) |
| Right after another lint entry | 147 | 27 |
| Same counts as the run before | 58 | 11 |
| `--auto-fix` runs | 39 | 20 |
| Runs that applied at least one fix | 31 | 8 |
| Carrying an agent's own note | 25 | 6 |

Lint entries are short: in `log.md` they are 38% of entry lines and 12% of the
bytes (6.3 of 51 KB). So they crowd the log by entry count, which is what
rotation counts, more than by reading length. In the last 30 lines, Orient's
read, 3 of the 7 entries are lint runs.

The other 54 entries since 10-06: 20 update, 17 ingest, 8 brief, 4
crystallize, 3 query, 1 split, 1 persona.

**Rate toward rotation.** 390 entries to go. The rate since 10-06 is about
half August's, so these dates are rough.

| | Entries per day | Next rotation, about |
|---|---|---|
| As now | 4.8 | 2027-01-18 |
| One lint entry per day (option 1) | 2.9 | 2027-03-14 |
| Only fixing runs (option 3) | 2.7 | 2027-03-22 |
| No lint entries (option 2) | 2.3 | 2027-04-13 |

### Who runs lint

| Caller | How | Writes an entry |
|---|---|---|
| `session-start.sh` ④ | `--quiet --json`, every session start | No |
| `worker-link-validator` | `--json` | No |
| `post-validate.sh` | Imports lint's functions, doesn't run it | No |
| Maintain ⑤ | Plain, then `--auto-fix` (pm-wiki's memory says run it unasked) | Yes, two or more per sweep |
| `lint-guide.md` Response Workflow | Re-run after fixing 🔴; "Always re-run without `--auto-fix` after" | Yes, the re-runs |
| `update-guide.md` supersede, core §6 | `--auto-fix` to rewrite links | Yes |
| Core §5, user asks | Plain | Yes |
| `worker-lint` | Plain; its rules say "the orchestrating session logs the lint run" | Yes, from lint.py itself, so possibly twice (unverified) |
| Agents checking their own work | Plain, after an update or ingest (4 entries also carry their own "Lint:" line) | Yes |
| Fork sessions checking pm-wiki | Plain, from the llm-wiki-pm project (NW15 and NW16 work on 10-28 and 10-29) | Yes |

From the log: of the 57 entries, 27 follow another lint entry (re-runs), 11
follow an ingest, 11 an update and 6 a brief. A transcript scan matched 21 of
the 57 runs to a session: 15 from pm-wiki sessions (maintenance sweeps and
updates), 6 from fork sessions. The rest call lint through a variable or a
worker, which the scan can't attribute, so the split by caller is
**unverified**. Whether scheduled runs ran lint is unverified too.

## Every reader and writer of `log.md`

### Writers

| Component | What it writes |
|---|---|
| `lint.py` | The lint entry above, after every non-JSON run |
| Agents following the skills | `ingest`, `update`, `query`, `crystallize`, `brief`, `archive`, `split`, `persona` entries, through Edit or `cat >>` (core §2-§10, `ingest-guide.md`, `learn-guide.md`, the brief, maintain, PRD, persona and research skills) |
| `migrate_sources.py --apply` | One entry per migration run |
| `session-start.sh` scaffold | Creates `log.md` from `templates/log.md` in a new wiki |
| `session-stop.sh` | Rotation: moves the file and writes a fresh header |
| `post-validate.sh` | Doesn't write; checks `log.md` for escaped `\[` after a tool write |
| `lint.py --auto-fix` | Repairs escaped brackets in `log.md` (line 643) |

### Readers

| Reader | What it reads | Uses lint entries? |
|---|---|---|
| Orient ③ (core, and brief, research, persona, PRD) | Last 20-30 lines | No, reads past them |
| Brief windows (PATCH-23) | The latest `brief \| daily\|weekly` line for the start, then the window's entries | No; a rotation can move the start line out |
| Brief §1 ②, §2 ② | Entries in the window, by type (ingest, update, decision, query) | No. The daily "Wiki health" row is "this run's lint warnings", from maintain ⑤ |
| Brief §4 ④ | Each slug's mentions in the last 30 days | No |
| Needs Review carry-forward (PATCH-27) | The latest brief's page, then the wiki and `log.md` to check each item | No |
| Core §9 pre-meeting | Last 5 entries mentioning a person | No |
| Core §10 catch-up | Last 7 days | No |
| Maintain ② | An earlier sweep's "Not ingested" line, in an explicit-range re-read | No |
| Maintain ⑥ | Reports a "lint health delta", with no source named | Possibly; the previous report's counts serve as well |
| PRD release notes | Entries since the last `release-notes` entry | No |
| `worker-people-updater` | Mentions of an entity in the last 30 days | No |
| `worker-wiki-indexer` | Last 7 days, for overview regeneration (dormant, NW1) | No |
| `lint.py` | Entry count, for the 🔵 rotation note | Counts them |
| `session-stop.sh` | Entry count, for rotation | Counts them |
| `migrate_sources.py` | All logs, rotated ones in year and part order | Skips them explicitly |
| `lint-guide.md` 3a | Cross-check of 🟠 stale pages against `log.md` | No |
| wiki-search, Obsidian | Index both files as notes (not checked) | No |

Not readers: sweeps since PATCH-22 take their windows from `MY-INTEGRATIONS.md`,
not the log. `_status.md` comes from `lint --json`. Checkpoint commits
(PATCH-19) don't read the log.

So no reader uses a lint entry's content. Two count them, and the rest read
past them. The only uses of lint history are agents comparing with an earlier
run, which the previous `queries/lint-*.md` serves, and the record that
`--auto-fix` changed pages, which only the fixing runs need.

## Options for the lint entries

### 1. One lint entry per day, updated in place (backlog)

- **Fixes:** 57 entries to 12, one per lint day.
- **Breaks:** `log.md` stops being append-only. When the day's entry isn't
  the last, lint rewrites the middle of the file, so an agent holding the file
  open gets Claude Code's "file changed since read" refusal on its next Edit,
  and each run's diff touches old text. Only the day's last counts survive,
  as in the report.
- **Keeps** one line per day that the report and git already hold.
- **Code:** about 25 lines in `lint.py` (find today's entry, replace it, write
  through a temp file). About 40 test lines.

### 2. No lint entries (backlog)

- **Fixes:** 57 entries to 0. The simplest code change: delete the append.
- **Loses:** the only log record that `--auto-fix` changed pages. The
  checkpoint commit before it is made only when there are uncommitted
  changes, and the report listing the fixes is overwritten by the re-run that
  `lint-guide.md` asks for. The changes are in git, but nothing says lint made
  them.
- **Code:** about 8 lines removed. About 25 test lines.

### 3. Log only runs that changed pages (recommended)

- **Fixes:** 57 entries to 8 since 10-06, 273 to 31 before.
- **Keeps** a record of every lint write, listing the fixes themselves, which
  the current entry's "Auto-fix applied N repairs" doesn't.
- **Matches the log's purpose:** it records changes to the wiki. A report-only
  run changes no page (its report is excluded from scans).
- **Code:** about 12 lines changed in `lint.py`. About 45 test lines.

### 4. Collapse consecutive identical runs

Skip the entry when the last entry is a lint entry with the same counts. 57 to
46. The re-runs differ in counts more often than not, so it fixes little.

### 5. Fewer runs, through skill prose

Drop `lint-guide.md`'s "Always re-run" and the 🔴 re-run. Prose only, but
agents also re-run on their own, and the session-start check already runs lint
every session. Worth doing only with option 1 or 4, since under 2 or 3 re-runs
cost nothing in the log.

## Options for rotation and brief windows

PATCH-23 made the latest brief's log line the start of the next brief's
window. After a rotation that line is in `log-YYYY.md`, and the brief skill
says that where no brief line exists "an interactive run asks where to start,
and an autonomous run starts 7 days back". A weekly brief after a rotation
would lose the days between its real start and 7 days back. Orient, catch-up,
pre-meeting, people-updater and brief §4 lose recent entries the same way,
for the days until the new log fills.

### R1. Briefs look in the rotated logs

One sentence in the brief skill: where `log.md` has no brief line of the kind
needed, read the rotated logs, newest first. Prose only. But "newest" is a
trap: by name, `log-2026-part-2.md` sorts before `log-2026.md`, so the rule has
to give year-then-part order, as `migrate_sources.py` does. A window that
straddles the rotation reads both files. It fixes the briefs only; Orient and
the other readers still lose their recent entries.

### R2. Rotation keeps the last 30 days (recommended)

`session-stop.sh` moves only entries older than 30 days into `log-YYYY.md`, and
the new `log.md` starts with the rest.

- **Fixes** every reader with a window up to 30 days: brief starts (daily and
  weekly briefs run daily and weekly), catch-up, Orient's tail, brief §4,
  `worker-people-updater`, and maintain ②'s "Not ingested" lookup.
- **Doesn't fix** a brief gap over 30 days, or a PRD release-notes cutoff
  older than that. The brief's existing "ask, or 7 days back" rule applies
  there, as it does to a wiki's first brief.
- **Code:** about 30 lines in `session-stop.sh`, inline `python3` as the other
  hooks use. About 60 test lines.

### R3. Leave rotation alone

Option 3 delays the next rotation to about March 2027. When it comes, the
first brief after it asks for a start, or goes 7 days back, and says so. A
known, rare, visible failure, but it repeats every rotation.

## Comparison

| | 1. Per day | 2. None | 3. Fixing runs | 4. Collapse |
|---|---|---|---|---|
| Lint entries since 10-06 | 12 | 0 | 8 | 46 |
| `log.md` stays append-only | No | Yes | Yes | Yes |
| Record of `--auto-fix` writes | Day's last only | None | Each, with fixes | As now |
| Code | About 25 lines | About 8 removed | About 12 | About 10 |
| Tests | About 40 lines | About 25 | About 45 | About 25 |

| | R1. Rotated-log rule | R2. Keep 30 days | R3. Nothing |
|---|---|---|---|
| Brief start after rotation | Found | Found, gaps up to 30 days | Asks, or 7 days back |
| Orient and other readers after rotation | Empty log | Last 30 days | Empty log |
| Where | Brief skill prose | `session-stop.sh` | — |
| Cost | Two sentences | About 30 lines, 60 test lines | None |

## Recommendation

Option 3 and R2, built together, with one changelog entry.

### What changes where

**`lint.py`** (lines 1036-1044, and the docstring):

- Append only when `fixes_applied` isn't empty:
  ```
  ## [YYYY-MM-DD] lint | auto-fix | <N> fixes | <N>E <N>W <N>I
  - <each fix, as in the report's Auto-fixes Applied>
  - Report: queries/lint-YYYY-MM-DD.md
  ```
- The docstring and usage line say a report-only run writes only the report.

**`session-stop.sh`** (steps ⑤-⑥):

- Over 500 entries, split `log.md` at the first entry dated within the last 30
  days (headers compare as text, `## [YYYY-MM-DD]`). Entries from there on stay,
  including any back-dated entry written later, at most the last 250, so the
  new log is always under the threshold.
- Write the older entries, with the old header, to the rotation target first,
  then replace `log.md` through a temp file and rename. On any error, rotate
  nothing and exit 0; the next session end tries again.
- The new header: "Rotated from log.md to `<name>` on `<date>`. Entries from
  `<first kept date>` on stay here." Accurate where today's "Rotated from
  log-2026.md" names the destination, and it keeps the "Rotated from" that
  upstream's test checks.
- The stderr message adds the kept count.

**Skill and doc prose:**

- Core `SKILL.md` §5: "`lint.py` adds a `log.md` entry only when `--auto-fix`
  changes pages. Don't log lint runs yourself; note lint results in the entry
  for the work they check." Pitfalls: "Rotate log" says the hook keeps the
  last 30 days.
- `lint-guide.md` opening: the same logging sentence.
- `worker-lint.md` Rules: "Lint runs aren't logged. Do not write to
  `$WIKI/log.md`." Its run is plain, so it never logs.
- Maintain ⑥: the lint health delta compares with the newest
  `queries/lint-*.md` dated before this run, read before ⑤ runs lint.
- `hooks/README.md` session-stop paragraph: the 30-day tail and the cap.
- `templates/log.md`: the actions line drops `lint` for `lint (auto-fix
  only)`, and the rotate line names the hook and the 30-day tail.
- No change to the brief skill is needed for R2, which keeps its brief lines
  in `log.md`. R1's sentence, approved with it, covers longer gaps.

### Who runs it

Nobody new. Lint and the hook run as now. Agents stop writing the "notes"
some added under lint entries; the skill line sends those to the entry for
the work.

### Reporting

Lint's stdout is unchanged. A fixing run's entry lists its fixes. Rotation
reports moved and kept counts on stderr.

### Tests

- `tests/test_lint.py`, 3 tests (about 45 lines): a plain run leaves `log.md`
  byte-identical; `--auto-fix` with nothing to fix leaves it identical;
  `--auto-fix` that sorts `index.md` appends one entry naming the fix.
- A new fork file, `tests/test_log_rotation.py`, 5 tests (about 60 lines):
  recent entries kept in order and older ones moved; all old, nothing kept;
  over 250 recent, the last 250 kept; a back-dated entry after the split
  stays; the two files hold every entry exactly once.
- Upstream's `TestSessionStop` in `tests/test_hooks.py` stays unchanged and
  should still pass: its entries are dated 2024, so all move, and the header
  still says "Rotated from".

### Migration

None. The 57 lint entries already in `log.md` stay, as an append-only log's
history, and leave at the next rotation. `log-2026.md` is untouched. Stripping
them would bring `log.md` from 111 to 54 entries, but rewrites history for a
rotation months away, so it isn't proposed.

### Interactions

- **NW1 (Orient content):** option 3 helps whatever NW1 decides. If NW1
  replaces Orient's log tail, R2 still serves the briefs and the other
  readers.
- **NW15 (done):** brief windows keep their start line through a rotation for
  gaps up to 30 days. Needs Review carry-forward reads brief pages and is
  unaffected.
- **NW16 (done):** the meeting warning reaches every session through
  `_status.md`, so it never needed a log entry.
- **NW14 / PATCH-22:** sweeps don't read the log for windows, so R2 matters
  for them only in maintain ②'s explicit-range re-read.
- **PATCH-19:** the checkpoint before `--auto-fix` is unchanged. The fixing
  run's entry and report are committed by the next checkpoint, as now.
- **F14:** closed in effect. `migrate_sources.py` already reads rotated logs,
  in year and part order, and skips lint entries.
- **Upstream:** the `lint.py` block and `session-stop.sh` are upstream code,
  so both diverge. Both are upstream candidates for the changelog entry.

### Cost

About 12 lines in `lint.py`, about 30 in `session-stop.sh`, about 105 test
lines, 7 prose edits, a changelog entry (PATCH-28) and NW3's closing status.
No pm-wiki change.

### Found in passing, not part of this change

- `lint-guide.md` lines 59-61 say a page is stale only when `log.md` shows
  activity since its update, but `lint.py` (lines 832-837) uses `updated:`
  alone.
- Whether `worker-lint`'s callers logged its runs a second time is
  unverified; option 3's wording change ends the question either way.

## To approve

- Option 3: chosen 2026-10-29.
- R2: chosen 2026-10-29, keeping the last 30 days, at most 250 entries.
- R1's sentence: chosen 2026-10-29, for brief gaps over 30 days.
- Leaving the existing lint entries in `log.md`: chosen 2026-10-29.
