# Unattended Lint Fixes Brief

created: 2026-10-30

Backlog NW18 asks whether lint's mechanical fixes should run without you. This
brief measures what those fixes would actually catch in pm-wiki, and finds that
the work happens at write time, not in the maintain run. It recommends a skill
wording fix that removes most of that work, plus an R3 auto-fix in
`--auto-fix=content` that the maintain loop runs unattended, capped at 10
pages.

## Status

Status: approved as recommended and implemented 2026-10-30 (changelog
PATCH-31). Decisions: P included, the R3 fix in `--auto-fix=content`, a cap
of 10 pages. The tests are 6, not about 8: the ambiguous, missing and
plain-`--auto-fix` cases share one test.
Backlog item: NW18 in the [llm-wiki-pm Fork Backlog](llm-wiki-pm-fork-backlog.md).
Related: NW17 (changelog PATCH-30, R3, R6 and R12 are 🔴), review F5 and plan
review P22 (the decisions this revises), PATCH-27 (briefs are frozen after
their day), PATCH-28 (lint logs only runs that fix something).

## About This Document

- **Measured on:** pm-wiki's 14 daily lint reports from October, and the
  `post-validate.sh` messages in pm-wiki's session transcripts since
  2026-10-01.
- **NW18 as written:** let the maintain loop's lint run apply plain
  `--auto-fix`, the `--auto-fix=content` repairs, and a new R3 fix that
  declares a cited ID when it names exactly one file.

---

## What happens today

- **End of day is clean.** All 14 October lint reports show 0 R3, R6, R7 and
  R12 findings. Lint overwrites its report once per day, so this is the state
  after each day's work.
- **Write time is not.** `post-validate.sh` reported R3 214 times on 9 days in
  October: 136 distinct citations on pages agents had just written, mostly
  `concepts/` pages updated during ingests. **Every one of the 136 named
  exactly one file to declare**, so all were mechanical. Agents fixed each one
  by editing `sources:` by hand, which is why the end-of-day reports are clean.
- **The other rules barely fire.** R7 fired once (one wrapped marker,
  2026-10-15), and R6 and R12 never fired.
- **Why R3 fires:** core skill §2 ⑤ says to write "inline `[source: ...]`
  markers" but not to declare what they cite. `crystallize-guide.md` ⑤ tells
  agents to declare the record on entity pages, but its concept-page bullet
  ("reinforce or challenge, bump confidence") doesn't. The R3 findings are
  mostly concept pages.

So the cost NW18 aims at isn't errors left in the wiki. It's an extra
write-check-edit loop on most ingests. An unattended fix in the maintain run
can't remove that loop, because the hook reports R3 the moment a page is
written, before any maintain step runs.

## Options

| Option | What it does | Verdict |
|---|---|---|
| P. Prevent at the source | §2 ⑤ and crystallize ⑤ say: declare each cited record's path in `sources:` in the same edit | **Recommended.** It targets the 136 cases directly, and it's prose only |
| U. Unattended R3 fix in the maintain run | `--auto-fix=content` gains an R3 fix; autonomous maintain runs it, interactive offers it | **Recommended, as the safety net.** It catches what P misses, which is mostly runs with nobody watching |
| H. `post-validate.sh` applies the fix itself | The hook rewrites the page it just checked | **Rejected.** A hook that edits the file the agent just wrote makes the agent's next Edit fail on a stale read, and hooks are advisory by design |
| C. A per-page command for agents | `lint.py --declare-cited <page>` after an R3 message | **Rejected.** It costs the agent one call, the same as the Edit it replaces |
| S. Session-start fixes | session-start runs the fix | **Rejected.** Your fork memory rules it out: session start reports, it doesn't change pages |

## The recommendation in detail

### P. The wording fix

- **Core `SKILL.md` §2 ⑤:** "inline `[source: ...]` markers, declaring each
  cited record's path in `sources:` in the same edit".
- **`crystallize-guide.md` ⑤:** the concept-page bullet gets the same
  declare clause as the entity-page bullet.
- **Check:** if write-time R3 messages don't drop after a week of ingests, the
  cause is somewhere else. Counting them again needs only the transcript scan
  used here.

### U. The R3 auto-fix

- **Where it lives:** a new `fix_undeclared_citations()` in `lint.py`'s
  `--auto-fix=content` section, next to `fix_citations()` and `fix_dates()`.
  It writes through `wikifm.set_list`, which preserves the rest of the
  frontmatter's text.
- **What it declares:** a cited ID that names exactly one file, the same rule
  as `migrate_sources.py --declare-cited`. It skips:
  - an ID that names no file or several, which stays an R3 error for you;
  - a citation with an R7 problem, which `fix_citations()` repairs first;
  - a page citing itself;
  - a dated digest filed before today, since PATCH-27 freezes briefs after
    their day.

  `migrate_sources.py` keeps its own copy. It's a one-time migration tool, and
  sharing code with it isn't worth the change.
- **Which level:** `--auto-fix=content`, not plain `--auto-fix`. It changes a
  page's frontmatter, and that flag is where page-content changes live (F5's
  split). This keeps plain `--auto-fix` limited to index and link repairs.
- **Who runs it:**
  - **Maintain ⑤, autonomous:** runs `lint.py --auto-fix=content` instead of
    plain `--auto-fix`.
  - **Maintain ⑤, interactive:** offers it, as it offers plain `--auto-fix`
    today.
  - **Session start and the workers:** unchanged, report only.
- **The 10-page cap:** if the content fixes (R3, R7, R12 together) would
  change more than 10 pages in one run, lint applies none of them, reports the
  count, and the maintain run puts "N pages need content fixes; review and run
  `lint.py --auto-fix=content`" in Needs Review. This keeps the core skill's
  rule that 10+ page changes need your sign-off, which is the part of F5 that
  still matters. Plain fixes still run.
- **Reporting:**
  - **Log:** lint's `log.md` entry already lists each fix (PATCH-28). The R3
    fix reads "declared `<path>` (R3) in `<page>`".
  - **Report:** each fix appears in the lint report's fixes list.
  - **Maintain:** ⑥'s summary gets "auto-fixed N" next to the health delta.
- **Undo:** `--auto-fix` already makes a checkpoint commit before it changes
  anything, so git can restore any fix.
- **Config:** none. The cap is a constant in `lint.py`.

### What this revises

- **Review F5:** content fixes may now run unattended, with the cap and only
  from the maintain loop. F5's concern was running before the migration's dry
  run and sign-off. The migration is done, and the cap covers the
  mass-update risk that remains.
- **Plan review P22:** R3 gets an auto-fix. P22 found no mechanism for one.
  This adds the mechanism, with exactly-one-file as the condition.
- **`lint-guide.md`:** the sentence "Unattended runs (scheduled, autonomous)
  never pass `=content`" is reversed, and the R3 row's Fix column names the
  auto-fix.

## Files, tests and cost

- **Code:**
  - `lint.py`: the fix, the cap, and the report lines. About 50 lines.
- **Docs:**
  - core `SKILL.md`: §2 ⑤ (P) and §5's auto-fix line.
  - `crystallize-guide.md` ⑤ (P).
  - `lint-guide.md`: the R3 row and the auto-fix section.
  - `llm-wiki-maintain` ⑤ and ⑥.
  - the design's section 5.15 R3 row, with a revision note.
  - changelog PATCH-31, and closing NW18.
- **Tests in `tests/test_lint.py`, about 8:**
  - declares an ID that names one file;
  - leaves an ambiguous ID and a missing ID as R3 errors;
  - skips a citation with an R7 problem;
  - skips a self-citation;
  - skips a dated digest filed before today, and fixes one filed today;
  - applies nothing above the cap, and reports the count;
  - plain `--auto-fix` doesn't declare anything.
- **Migration:** none. pm-wiki has no R3 findings today.
- **Upstream:** a candidate with PATCH-30, not filed.

## Decisions for you

1. **Include P, the wording fix, in NW18?** Recommended: yes. It's the change
   that removes most of the work.
2. **Put the R3 fix in `--auto-fix=content` rather than plain `--auto-fix`?**
   Recommended: `=content`.
3. **A cap of 10 pages per run?** Recommended: 10, matching the core skill's
   mass-update rule.
