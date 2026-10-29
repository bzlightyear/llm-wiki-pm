# Crystallize Coverage Design

created: 2026-10-28

PATCH-24 made every meeting transcript get its own crystallize page, but
nothing checks that the rule is followed, and 43 of pm-wiki's meetings never got
a page. This design covers NW16's other two parts: a lint warning for a
`raw/transcripts/` record that no crystallize page declares, shown in the
session-start health summary (part 2), and one signed-off batch that backfills
pages for the 43 meetings from their raw records (part 3). It also sets the
order of the two, how much to backfill, cost, logging and commits.

## Revision History

revised on: 2026-10-28
All eight choices approved, with option C. Batch 2, the smallest, now runs
first to measure usage before the other three, so the lint count drops
43 → 35 → 20 → 10 → 0.

revised on: 2026-10-28
Ingest ① now routes material by what it is, pasted or fetched, with signs
for meetings, chat threads and talk or podcast transcripts, and asks when
unclear (choice 3, approved). Added "How much to backfill" with options A to
C, and replaced the cost estimate with token usage counting context resends,
ways to lower it, and a measure-first batch; hours are now labelled as
Claude's time, apart from yours.

## Status

Status: approved 2026-10-28, all eight choices under To approve (option C,
all 43). Part 2 implemented 2026-10-28 (changelog PATCH-25): lint reports
pm-wiki's 43 and session-start 156 issues, as predicted. Part 3, the
backfill, not started; pm-wiki not changed.

## About This Document

- Backlog item: NW16, parts 2 and 3, in the
  [llm-wiki-pm Fork Backlog](llm-wiki-pm-fork-backlog.md). Part 1 is changelog
  PATCH-24 in the [llm-wiki-pm Fork Changelog](llm-wiki-pm-fork-changelog.md).
- Counts are from pm-wiki on 2026-10-28, after the 10/28 weekly run.
- **No meeting names here.** Your fork is public, and the record names carry
  customer and colleague names. This doc gives counts by date and kind. The
  named list is outside the repo, in the session notes folder as
  `nw16-backfill-list.md`, and once part 2 is built lint prints the same list
  from pm-wiki. The sign-off is on that list.

---

## What pm-wiki has today

- **156 transcript records, 113 with a crystallize page, 43 without.** The
  backlog's 43 came from 152 records. The four 10/28 meetings since then got
  pages, so 43 is still the count, and it's the same 43.
- **All 43 are meetings.** Each record is a Notion meeting page, a summary, a
  transcript or both. No record in `raw/transcripts/` was found that isn't a
  meeting.
- **Each of the 43 already feeds pages.** Each is declared by 1 to 7 pages: 46
  entity and concept pages in all (105 declarations), plus 6 briefs. So the
  facts are in the wiki. What's missing is the per-meeting digest and the
  link to it.
- **Shape of existing pages.** 108 crystallize pages declare one transcript
  each, and 93 of them are named `crystallize-<record ID>`. Two older pages
  each declare two or three meetings. No transcript is declared by two
  crystallize pages.

**The 43 by meeting date** (customer = a customer, analyst or CAB meeting;
1:1; internal = any other team meeting):

| Meeting dates | Count | Customer | 1:1 | Internal |
|---|---|---|---|---|
| 2026-03-26, 03-30 | 2 | 2 | | |
| 2026-06-16 | 1 | 1 | | |
| 2026-09-17 to 09-24 | 12 | 1 | 2 | 9 |
| 2026-09-28 to 09-30 | 5 | | 1 | 4 |
| 2026-10-02, 10-13, 10-16 | 3 | | | 3 |
| 2026-10-19 to 10-21 | 10 | 2 | 2 | 6 |
| 2026-10-22 to 10-27 | 10 | 3 | 2 | 5 |
| **Total** | **43** | **9** | **7** | **27** |

By day: 09-17 3, 09-18 2, 09-21 2, 09-22 1, 09-23 2, 09-24 2, 09-28 2, 09-29
2, 09-30 1, 10-02 1, 10-13 1, 10-16 1, 10-19 4, 10-20 3, 10-21 3, 10-22 3, 10-23
1, 10-26 3, 10-27 3.

## Part 2: the lint check

### What it checks

- **Records:** every `.md` file under `raw/transcripts/`, in subfolders too.
- **Covered:** a record is covered when a crystallize page's `sources:`
  declares its path. A crystallize page is a page under `queries/` whose file
  name starts with `crystallize-`. That is the path the rule names, so going
  by the name also catches a digest filed under another name. A page that
  declares two meetings covers both: lint doesn't enforce one page per meeting
  (see Not covered).
- **Finding:** one line per record:
  `meeting with no crystallize page: raw/transcripts/<id>.md — create
  queries/crystallize-<id>.md (ingest-guide.md ⑥)`.

### Rule ID and tier

- **No R number.** R3–R12 are the rules of `citation-spec.md`, about how
  sources and citations resolve. This check is about ingest following its own
  steps, like orphans and index gaps, which have no ID. If you'd rather it
  had one, it would be R15: R13 and R14 were dropped, but older docs still
  cite them.
- **Tier 🟡 warning.** Nothing is broken for navigation or search, and the
  fix (running crystallize) needs judgement, so it isn't 🔴 and isn't
  auto-fixed.

### Transcripts that aren't meetings

The folder is the only signal lint can use. Record frontmatter is too uneven
to mark meetings: of 156 records, 82 have `source_type: transcript`, 5 a
Notion meeting type, 60 none, and 9 have no frontmatter. Records are
write-once, so they can't be tagged afterwards either.

So the check treats every `raw/transcripts/` record as a meeting, and the
folder carries the agent's judgement at ingest to lint later. That needs the
routing in `ingest-guide.md` ① to be clear. Today its "Paste/transcript →
`raw/transcripts/`" line also matches a pasted Slack fragment, which the chat
route just below it sends to `raw/internal/`, and nothing says which wins.

The line becomes a short list that routes by what the material is, not by
whether it was pasted or fetched:

- **Meeting transcript or notes** → `raw/transcripts/`. Signs: several people
  in one call or room, speaker turns or notes from one session, often
  attendees, decisions and action items; or a meeting page found in a sweep.
- **Chat thread** → the chat route, `raw/internal/<channel>-<date>.md`.
  Signs: short messages with names and times, replies, a channel or thread;
  or a thread read through a chat tool.
- **Talk, video or podcast transcript** → `raw/articles/`. Signs: one speaker,
  or a host and guest, made for an audience, usually public, often a link.
  It's a publication, and the crystallize guide skips single-article ingests.
- **Still unclear** (a few pasted lines with no names): an interactive run
  asks you; an unattended run goes by where the material came from.

Micro-capture is unaffected: `capture.py` always writes conversation records
to `raw/internal/`, and the fast path skips crystallize. pm-wiki has no
misrouted record in `raw/transcripts/` today: its 9 Slack and Teams records
are all in `raw/internal/`. If a non-meeting does land in `raw/transcripts/`,
the warning stays visible until you decide what to do with it. That's rare
enough not to build an exemption for now.

The reverse case isn't checked: a meeting record filed outside
`raw/transcripts/`. pm-wiki has one, a March internal meeting saved to
`raw/internal/` as an extract for the customer's page. Confluence meeting-notes
pages in `raw/internal/` are documents, not transcripts, and stay out of scope.

### No date cutoff or exemptions

The rule says every meeting gets a page however it was ingested, and 9 of the
12 records from before August already have one. A cutoff (say, before
2026-08-20) would hide the 3 older ones, and also any old meeting imported
later. With the backfill done first (see Order), the check starts at zero
warnings with nothing exempt. If you leave the March and June meetings out of
the backfill, lint would warn on them for good, so leaving them out would also
need an exemption list. That's another reason to include them.

### Session-start health summary

- `lint.py --json` gains `"uncrystallized": [<record paths>]`.
- `session-start.sh` reads it like the secondhand list and adds a row to
  `_status.md`'s Health Summary, `| Meetings with no crystallize page | N |`,
  plus a "Meetings with no crystallize page" section listing up to 20 records.
- The count is added to the health total, since it's new drift rather than a
  migration backlog. The context line gains "Meetings with no crystallize
  page: N." only when N > 0, so a clean wiki's line doesn't change.
- If lint fails, the row says "unknown", like the others.

### Effect on pm-wiki's counts

Today `lint.py --json` gives 0 errors, 34 warnings and 21 info, and
session-start reports 113 issues (102 stale, 11 confidence decay).

| | Warnings | Health total | New row |
|---|---|---|---|
| Today | 34 | 113 | — |
| Part 2 built, before backfill | 77 | 156 | 43 |
| After the backfill | 34 | 113 | 0 |

The backfill adds 43 pages and edits 46. It shouldn't add warnings: the new
pages get inbound links and index entries, and none is near 200 lines. The 46
pages it edits get one to eleven short link lines each. Many are already over
200 lines and already warned on. A link line could push one just under 200
over the line, and that batch's lint run would show it.

### Size

- `lint.py`: about 20 lines. Collect covered paths in the existing page loop
  from `check_sources`' resolved records, compare after the loop, add the
  warning and the JSON key.
- `session-start.sh`: about 15 lines (parse, row, list section, total, context).
- `tests/test_lint.py`: about 60 lines, 5 tests:
  - warns on a transcript no page declares;
  - silent when `queries/crystallize-*.md` declares it;
  - a concept page or a non-`crystallize-` query declaring it doesn't count;
  - `--json` carries the list;
  - session-start shows the row and section, and the context line names the
    count only when it's above zero.

  The existing exact-line test keeps passing because the context text is
  added only when N > 0.
- Lint's runtime doesn't change in any way you'd notice: it reuses the page
  loop.

## Part 3: the backfill

### How much to backfill

Nothing breaks without the backfill: the facts are already on entity and
concept pages, and briefs fall back to a meeting's raw record. What's lost is
each meeting's decisions, action items and open questions in one place, which
"what did we decide about X" queries read. And unless every meeting is
covered, lint needs a cutoff date, or it warns on the rest forever and a new
miss is lost among them. A cutoff also exempts any old meeting imported
later, which is rare, since sweeps bring in recent material.

| | Backfill | Lint cutoff | Tokens (rough) | Gap left |
|---|---|---|---|---|
| A. None | 0 | meetings before 10/28 | none | 9/17–10/27, March, June |
| B. October only | 23 | meetings before 10/01 | ~8–15M | 9/17–9/30, March, June |
| C. All (recommended) | 43 | none | ~15–30M | none |

C is the only option that makes "every meeting has a page" true and needs no
cutoff. B gets most of the value for about half the cost if you rarely look
back more than a month: October's meetings are the ones whose action items
and open questions may still be live. A leaves the most recent six weeks
without digests. Token figures are explained under Cost. C was chosen on
2026-10-28, and the rest of this section describes it. Under B, the batch list drops to batches 3 and 4 plus the
October part of batch 2, and lint gets the cutoff constant (about 3 lines and
a test).

### What's in it

All 43, including the March and June ones. The backlog said
those three "predate current conventions". They don't: their records have the
same shape as the September ones, and 9 of 12 meetings from January to June
already have pages. They're short (488 to 867 words), so they cost little.

The March internal meeting in `raw/internal/` (see above) is left out: it's a
partial extract made for the customer's page, not the meeting's record, and
lint doesn't flag it. Optional add if you want it.

### Each page

- **Path:** `queries/crystallize-<record ID>.md`, so the topic is the record's
  descriptor and the date is the meeting date, as 93 existing pages do. None
  of the 43 names is taken.
- **Built from the raw record only.** No re-fetching Notion. Where the record
  holds only a summary, the page says so in Context.
- **Structure:** the crystallize guide's: Context, Decisions, Action Items,
  Open Questions, Lessons/Patterns, Links. Frontmatter `title`, `created` and
  `updated` (the day it's written), `type: query`, existing taxonomy tags,
  `sources: [raw/transcripts/<id>.md]`, and no `shareable`.
- **Citations:** `[source: <record ID>, <section>]` markers as usual.
- **Action items:** status `not tracked`, and Context says "Backfilled on
  <date> from the raw record; action-item status not checked." Calling a
  September item `pending` would be wrong, and these meetings are 1 to 6
  weeks old. NW1 covers stale action items generally.
- **Not re-ingested:** the facts are already in the concept and entity pages,
  so crystallize workflow steps ③ and ⑤ (extract lessons, update affected
  pages) are limited to backlinks. `overview.md` isn't touched.

### Links

- **Outbound:** each page links the entity and concept pages that already
  declare its record (1 to 7 per meeting), so every page has at least 2
  outbound links.
- **Inbound:** each of those pages gets `[[crystallize-<id>]]` in the dated
  section that covers that meeting, as existing pages do ("digest:
  [[…]]"), or in its related section if it has no dated one. That's 105 links
  on 46 pages. Briefs aren't edited: they're dated digests.
- **`index.md`:** each page added under Queries, in alphabetical order.

### Batches

Four batches by meeting date, each one session, one after another: batch 2
first, the smallest, to measure usage (see Cost), then 1, 3 and 4. Running
them in parallel would put two sessions on the same pages: one concept page
takes 11 of the links.

| Batch | Meetings | Pages created |
|---|---|---|
| 1 | March, June, 09-17 to 09-24 | 15 |
| 2 | 09-28 to 10-16 | 8 |
| 3 | 10-19 to 10-21 | 10 |
| 4 | 10-22 to 10-27 | 10 |

Each batch: Orient, read the batch's records, write the pages, add backlinks
and index entries, append the log entry, run lint and check the count went
down by the batch size, then commit.

### Sign-off

43 pages created and 46 edited is a mass update, so per AGENTS.md you sign off
on the list first. Once part 2 is built, the first backfill session runs
`lint.py $WIKI` and shows the "meeting with no crystallize page" lines. If
they still match `nw16-backfill-list.md` (or differ only by meetings you've
added since), you approve that list once, for all four batches. A batch that
finds a page already exists for one of its meetings skips that meeting and
says so.

### Log

One entry per batch, in the crystallize guide's form:

```
## [YYYY-MM-DD] crystallize | backfill, meetings <from> to <to> (NW16)
- Not new material: these meetings were ingested and briefed earlier.
- Created: queries/crystallize-<id>.md, ...
- Updated (backlinks): entities/..., concepts/...
- index.md: added N crystallize pages
```

The "not new material" line is there for the brief: brief windows follow
`log.md` by ingest time, so the next daily or weekly brief would otherwise
report 43 old meetings as new.

### Commits

In pm-wiki, on its `main`, not pushed:

- **Automatic checkpoint first.** The pre-write hook commits whatever was
  uncommitted before the session's first write (a `checkpoint:` commit), so
  git can undo the batch.
- **One commit per batch** after the batch's lint check:
  `git add -A -- . ':(exclude)_status.md'` then
  `git commit -m "Backfill crystallize pages for meetings <from> to <to>"`.
  `git add` picks the changes that go into the next commit. The
  `':(exclude)_status.md'` part leaves out the status file session-start
  rewrites on every start. The `':!'` short form errors on its underscore.
- **Renames:** the backfill creates pages and doesn't rename any. If a batch
  has to rename something (a name clash found on the day), the rename gets
  its own commit before the edits. Git spots a rename by matching the old
  and new file's contents. Edits in the same commit, or a hook's checkpoint
  in between, can break the match, and the history then shows a deleted file
  and a new one.

Your fork's commits for part 2 name the mechanism only, with no wiki page or
meeting names.

## Order

Part 2 first, then part 3, ideally the same day or the next.

- Lint gives the exact, current list for sign-off, rather than this doc's
  snapshot going stale.
- Each batch checks itself: the count drops 43 → 35 → 20 → 10 → 0 (batch 2
  first, then 1, 3 and 4).
- Until the backfill ends, session-start's health total includes the
  remaining count (156 today). That's the progress meter, not new damage.

Backfill first would mean checking coverage with a one-off script and then
landing lint at zero. That's a cleaner first health line but no verification
tool during the batches.

## Changes

**Your fork** (one commit for code and tests, one for docs, then the
changelog):

- `skills/llm-wiki-pm/scripts/lint.py`: the check, the warning and the JSON
  key. Docstring usage unchanged.
- `hooks/session-start.sh`: the row, the section, the total and the context
  text.
- `tests/test_lint.py`: the 5 tests above.
- `skills/llm-wiki-pm/references/lint-guide.md`: the warning under 🟡 Warnings
  (after "Unresolved contradictions", line 38); the "NOT auto-fixed" list
  (line 144); the `--json` description (line 160).
- `skills/llm-wiki-pm/references/ingest-guide.md` ① (line 14): the
  "Paste/transcript" line becomes the routing list above, by what the
  material is, with its signs and the ask-if-unclear rule (about 10 lines).
- `hooks/README.md` session-start (lines 23–28): one sentence on the new count
  and list.
- Fork changelog PATCH-25; backlog NW16 updated (part 2 done; part 3 done or
  in progress).

**pm-wiki:** the 43 pages, 105 backlinks on 46 pages, 43 `index.md` lines, and 4
log entries, in 4 commits, plus the hook's checkpoint commits.

**Not changed:** `crystallize-guide.md` and ingest ⑥ already state the rule;
maintain's health step already surfaces lint's warnings; the brief skill
already reads a meeting's crystallize page when there is one;
`worker-link-validator` reads only the JSON keys it already uses.

## Proposal checklist

- **Where it lives:** the check in `lint.py`, the display in
  `session-start.sh`, the docs in `lint-guide.md` and `hooks/README.md`, the
  routing line in `ingest-guide.md` ①. The backfill is pm-wiki content only.
- **Who runs it:** lint runs at every session start (`--json`), in
  maintain's health step ⑤, and by hand. The backfill is four interactive
  sessions you start, after sign-off.
- **Reporting:** the lint report's 🟡 section, the `_status.md` row and list,
  the session-start context line, and maintain's health summary.
- **Fixes:** none automatic. The fix is ingest ⑥ for the named record.
- **Config:** none. No threshold, cutoff or exemption list.
- **Docs:** listed under Changes.
- **Tests:** 5 new; existing session-start tests unchanged.
- **Interactions:** below.
- **Migration:** the backfill is the migration. No record or schema changes,
  and no new tags.
- **Cost:** below.

## Interactions

- **NW1 (stale action items):** the backfill adds 43 pages with action items,
  all marked `not tracked`, so none read as open. NW1's design should decide
  how these are treated.
- **NW15 and the brief windows:** handled by the log entry's "not new
  material" line. Check the first brief after batch 1 for it.
- **Maintain:** a sweep that ingests a meeting and skips ⑥ now shows up in that
  same run's health step ⑤, and at the next session start.
- **pm-wiki memories:** none override the rule. Checked
  `~/.claude/projects/-Users-pgoubert-Projects-pm-wiki/memory/`: one note says
  to use Write and Edit, not scripts, for wiki pages (the hook doesn't see
  Bash edits), so the backfill writes pages with Write and Edit. Another says
  pushing pm-wiki needs a request, so nothing is pushed.
- **Upstream:** lint and session-start came from upstream, so the fork
  changelog entry marks this an upstream candidate for later, like PATCH-24.

## Not covered

- **One page per meeting** isn't enforced: two older pages declare several
  meetings each, and lint accepts them. Splitting them would rewrite 5
  meetings' digests and their links, which isn't worth it now. A later check
  for a crystallize page declaring two or more transcripts could be added if
  it happens again.
- **Entity promotion (ingest ⑫)** was probably skipped the same way (backlog
  NW16) and isn't checked here.

## Cost

- **Your fork:** about 35 lines of code, 60 of tests and 20 of prose, three
  commits, one changelog entry.
- **pm-wiki backfill, content:** the 43 records total about 35,000 words
  (median 784, maximum 1,447), about 46,000 tokens to read. The pages come to
  about 24,000 words (500 to 600 each, like the October pages), about 32,000
  output tokens. Backlinks mean reading the matching section of 46 pages and
  making 105 small edits.
- **pm-wiki backfill, usage:** a session resends its whole context on every
  tool call, so usage depends on the number of calls and how large the
  context has grown, not on the content alone. Reasoned out, not measured:

  | | Per batch | All four |
  |---|---|---|
  | Tool calls | 60–90 | 250–350 |
  | Context at start (system prompt, skills, Orient) | ~50k | — |
  | Context by the end | ~120–150k | — |
  | New content read | ~70–100k | ~350k |
  | Output (pages, edits, reasoning) | ~30–45k | ~120–170k |
  | Input processed, counting resends | ~4–7M | ~15–30M |

  Most of the input processed is cache reads; about 1–2M in all is new. How
  your plan's limits weigh cache reads isn't known here. Option B is about
  half.
- **Ways to lower it:** write each page in a short-lived subagent that reads
  only its record, so the long context isn't resent, and leave only links
  and index lines to the main session; and do the mechanical link edits on a
  cheaper model, as AGENTS.md routes I/O work to Sonnet. Page writing is
  synthesis, which AGENTS.md routes to Opus. Neither is measured.
- **Measure first:** run batch 2 (8 meetings) first and read its usage from
  the session afterwards. That gives a real per-meeting figure before the
  other three batches.
- **Time, rough:** about 3 to 4 minutes of session time per meeting, under 3
  hours for all 43. That's Claude's elapsed time, not your attention. Your
  part: approve the list once, start each session, answer prompts and look
  over each batch, maybe 10 to 15 minutes per batch.
- **Ongoing:** none beyond the warning, which should stay at zero.

## To approve

All approved 2026-10-28:

1. **Lint check scope:** every `raw/transcripts/` record, covered by any
   `queries/crystallize-*` page declaring it; 🟡; no R number.
2. **No date cutoff and no exemptions.**
3. **Ingest ① routes by what the material is,** pasted or fetched: meetings
   to `raw/transcripts/`, chat threads to the chat route, talk, video or
   podcast transcripts to `raw/articles/`, with signs for each; when unclear,
   ask (interactive) or go by the source (unattended).
4. **Session-start:** a Health Summary row and list, counted in the health
   total, named in the context line only when above zero.
5. **Option C:** backfill all 43, March and June included, with no lint
   cutoff. Leave out the March `raw/internal/` extract.
6. **Page form:** `queries/crystallize-<record ID>.md` from the raw record only,
   action items `not tracked`, backlinks in the matching dated section, no
   concept-page re-ingest, no `overview.md` change.
7. **Four sequential batches,** one commit and one log entry each, with the
   "not new material" line.
8. **Order:** part 2 first, sign-off on lint's list, then the batches, batch
   2 first to measure usage.
