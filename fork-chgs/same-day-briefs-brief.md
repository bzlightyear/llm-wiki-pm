# Same-Day Briefs Brief

created: 2026-10-30

Backlog NW19 asks what happens to a filed brief when a second run on the
same day files another. This brief measures how often runs land close
together in pm-wiki, compares four ways to handle a second brief, and
recommends filing it under the next free name (`YYYY-MM-DD-2.md`), which keeps
every existing brief rule as it is. The change is wording only.

## Status

Status: approved as recommended and implemented 2026-10-30 (changelog
PATCH-32). Decisions: B, the `-N` names; no hook guard; carry-forward reads
the latest filed brief. The vault-contract template's dated-names line also
gained the weekly name, which it lacked.
Backlog item: NW19 in the [llm-wiki-pm Fork Backlog](llm-wiki-pm-fork-backlog.md).
Related: NW15 (changelog PATCH-21 to PATCH-27, the brief rules this extends),
PATCH-27 (briefs are frozen after their day), the
[Daily and Weekly Briefs Brief](daily-and-weekly-briefs-brief.md) and the
[Sweep Window Design](sweep-window-design.md) (windows and run-date names).

## About This Document

- **Measured on:** pm-wiki's `log.md` brief and lint entries for October,
  `briefings/` and its git history, pm-wiki's Claude memory notes, and the
  scheduled tasks on this machine (none), on 2026-10-30.
- **NW19 as written:** names three options (sections in one file, a separate
  file, re-cover the day and replace) and asks for a short brief first.

---

## What happens today

- **The rules.** Maintain ④ files a daily brief at `briefings/YYYY-MM-DD.md`
  and a weekly one at `briefings/weekly-brief-YYYY-MM-DD.md`, both dated by
  the run. A brief's window starts where the latest brief's window ended.
  Brief §1 allows same-day corrections to a filed brief. No rule covers a
  second brief of the same kind on the same date.
- **What an agent would do.** The Write tool fails on an existing file the
  session hasn't read, so the agent reads the morning brief and then decides
  on its own: replace it, add to it, or pick another name. The wiki-search
  MCP's `vault` update has no such guard. If the agent replaces it, a brief
  covering a few hours takes the place of the full one. The pre-write
  checkpoint keeps the first version in git, but the page loses it.
- **No collision yet.** pm-wiki has 14 daily and 6 weekly briefs filed, with
  no two of a kind on one date.
- **But runs land close together, mostly around midnight.** You often run
  maintenance late: lint ran after the sweep at 22:11 on 10/19, 22:14 on
  10/21, 21:03 on 10/22, and the 10/29 brief's window ended at 21:59. On
  10/30 a daily brief ran at 01:03 covering 21:59 → 01:03 (about 3 hours),
  and a weekly brief ran 4 minutes later; neither was filed. Had the 01:03
  daily been filed, a normal daytime run on 10/30 would have collided with
  it. On 10/14–10/15 an evening run was followed by one the next morning
  ("2026-10-14 evening to 2026-10-15").
- **Runs are interactive.** No scheduled task or launchd job runs
  maintenance, so a collision needs you to run it twice, which the midnight
  pattern makes plausible.
- **pm-wiki's memory already states the intent.** The note on brief paths
  says "a re-run is a new brief, not an overwrite". Agents follow that note,
  but it names no path for the new brief.

## Options

| Option | What it does | Verdict |
|---|---|---|
| B. Next free name | A second brief of a kind on one date files as `YYYY-MM-DD-2.md` (`-3`, …); the first is untouched | **Recommended.** Every rule that assumes one brief per file holds, and it matches your memory note |
| A. One section per run | The second run adds its brief under a run heading in the existing file | **Rejected.** One file holds two Headline, Meetings and Needs Review sections, so "the latest brief's Needs Review" means a section, heading links become ambiguous, and `sources:` and `tags:` mix two briefs |
| C. Re-cover the day and replace | The second run starts its window where the previous date's brief ended and rewrites the file | **Rejected.** It overwrites a brief you may have read, re-reads the whole day's meetings, needs a window exception, and leaves the first run's log line pointing at content it no longer describes |
| D. Don't file the second | The second brief goes to chat and the log only | **Rejected for maintain.** Maintain must file, because its Needs Review queue lives in the filed brief; an unfiled queue has no home (see "Also found") |

## The recommendation in detail

### Naming and filing

- **Name:** `briefings/YYYY-MM-DD-N.md` for a daily brief and
  `briefings/weekly-brief-YYYY-MM-DD-N.md` for a weekly one, where N is the
  lowest number from 2 up whose file doesn't exist. The first brief of a day
  keeps the plain name, so nothing filed today changes.
- **How the agent picks it:** before filing, check whether the plain path
  exists; if it does, use the next free `-N`. Filing never writes over an
  existing brief.
- **Title:** `Daily Brief: 2026-10-30 (run 2)`, and the weekly equivalent.
- **Opening note:** as now, it says where the window starts, which is now
  the earlier brief: "It starts where [[2026-10-30]] ended."

### What stays the same

- **Window and log line.** The window rule is unchanged: the second brief
  starts where the first ended. Its log line is its own entry, and `filed:`
  names the `-N` path.
- **Carry-forward.** The second brief starts from the first brief's Needs
  Review, as it would from any latest brief. Items the first brief raised
  and the second settles are listed as resolved in the second, not edited
  out of the first.
- **The first brief.** A later run doesn't edit it. Same-day corrections by
  hand stay allowed, as brief §1 says.
- **Weekly briefs.** Weekly ② reads "the daily briefs in the window", which
  includes `-N` files with no change.
- **Lint and hooks.** No change. Lint treats a brief by its frontmatter
  (`lifecycle: dated-digest`), not its name; `2026-10-30-2` is a valid,
  unique slug; `briefings/` is already a page folder for the hooks.
- **Link readers.** Obsidian, the wiki-search MCP and lint's link check
  all resolve `[[2026-10-30-2]]` as a plain page name; nothing parses brief
  names as dates.

### Not included: a hook guard

`pre-write.sh` could warn when a whole-file write replaces an existing
dated digest. It isn't recommended now: no collision has happened, the Write
tool already fails on an unread file, and hooks are advisory. If a brief is
overwritten after this change, a guard is the next step (decision 2).

## Files, tests and cost

- **Code:** none.
- **Docs, in your fork:**
  - `llm-wiki-brief`: the filing paragraph after Daily ④ (the `-N` rule and
    title), and Weekly ⑧'s path.
  - `llm-wiki-maintain`: ④'s Daily and Weekly paths, and the Brief
    lifecycle convention.
  - `templates/vault-contract.md`: the dated-names line gets the `-N`
    forms.
  - changelog PATCH-32, and closing NW19.
- **pm-wiki:** `meta/contract.md` (the same line), `index.md`'s Briefings
  line, and the memory note on brief paths, which gets the `-N` name next to
  "a re-run is a new brief, not an overwrite".
- **Tests:** none; no code reads brief names. The existing dated-digest
  tests in `tests/test_lint.py` cover a brief at any name.
- **Migration:** none. No date has two briefs of a kind.
- **Config:** none.
- **Upstream:** not filed. Upstream still rotates briefs, so this depends on
  PATCH-21 to PATCH-27 going first.

## Also found: unfiled briefs and carry-forward

Every brief "starts from the Needs Review section of the latest brief". An
unfiled brief's Needs Review exists only in chat and a one-line log note: the
10/30 01:03 daily brief carried items 1–5, 7 and 8 without filing them, so
the next brief can only find their text in `briefings/2026-10-29.md`. Reading
"the latest brief" as "the latest filed brief" makes this work, since an
unfiled brief changes no page. This is a one-sentence clarification in brief
§1 (decision 3).

## Decisions for you

1. **File a second brief of a kind on one date as `-2`, `-3` (B)?**
   Recommended: yes.
2. **Add a `pre-write.sh` warning for a write that replaces a dated digest?**
   Recommended: not now; revisit if a brief is overwritten.
3. **Clarify that carry-forward reads the latest filed brief, as part of
   NW19?** Recommended: yes, in the same change.
