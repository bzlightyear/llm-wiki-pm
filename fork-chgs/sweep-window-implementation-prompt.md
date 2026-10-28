# Sweep Window Implementation Prompt

created: 2026-10-28

Handoff prompt for a fresh session that implements the
[Sweep Window Design](sweep-window-design.md) (NW14) together with NW8, B, D and
G from the [Daily and Weekly Briefs Brief](daily-and-weekly-briefs-brief.md)
(NW15), and part 1 of NW16 (the crystallize rule), then migrates pm-wiki. Paste
the text below the `---` into a new session started in this repo.

## Status

Status: ready to run. Every choice it implements was approved 2026-10-28; the
design docs are committed (6311602).

---

Implement the approved Sweep Window Design in your fork of llm-wiki-pm, with
the brief and crystallize changes approved alongside it, then migrate pm-wiki.
Everything to build is already decided; your job is to turn the designs into
skill prose, one commit per change, and check the result.

<context>
- Repo: /Users/pgoubert/Projects/llm-wiki-pm (your fork; branch `main`). Wiki:
  /Users/pgoubert/Projects/pm-wiki.
- Read first, in full:
  - `fork-chgs/sweep-window-design.md`: the design, including its 2026-10-28
    revision. Its "Proposal", "Changes" and "Migration" sections are the spec.
  - `fork-chgs/daily-and-weekly-briefs-brief.md`: B, D and G (the rest of NW15
    is out of scope).
  - NW14, NW15 and NW16 in `fork-chgs/llm-wiki-pm-fork-backlog.md`.
  - PATCH-20 in `fork-chgs/llm-wiki-pm-fork-changelog.md`, as the model for
    new changelog entries (the next is PATCH-21).
  - `fork-chgs/doc-conventions-guide.md` for any fork-chgs edits.
- The skills are prose and are symlinked into `~/.claude/skills/`, so a commit
  on `main` takes effect at the next session. There is no code to change.
</context>

<steps>
Commit each step separately on `main`. Don't push.

1. **NW8, cadence picks the brief** (its own commit, an upstream candidate):
   `skills/llm-wiki-maintain/SKILL.md` step ④ becomes "Brief": cadence from the
   user's words or the scheduled task's prompt, daily by default with no
   question; route to the daily or weekly brief and file it without offering.
   The weekly brief from maintain carries the Source Coverage ledger and Needs
   Review (`skills/llm-wiki-brief/SKILL.md` §2). "Brief lifecycle convention"
   adds the weekly path. Use `briefings/weekly-brief-YYYY-MM-DD.md` (run date)
   directly, not the `queries/` path NW8 first approved.
2. **NW14, per-source sweep windows:** every item under the design's "Changes →
   Skills and references" that isn't NW8's or NW15's: maintain steps ② and ③,
   `references/source-discipline.md` (completeness guard), the core
   `SKILL.md` Source-completeness summary and bound-output rule, the brief
   skill's ledger example, `templates/MY-INTEGRATIONS.md` (the Swept through
   column), and `references/ingest-guide.md` ⑨.
3. **NW15 B, D and G, briefs:** the design's "NW15 B, D and G" bullets under
   Changes: brief §1 and §2 windows, the "What each brief holds" table in
   place of their section lists, the weekly path with
   `lifecycle: dated-digest`, the log line; maintain step ⑥; core §10's
   `catchup` line.
4. **NW16 part 1, the crystallize rule:** `references/ingest-guide.md` ⑪ says
   every meeting transcript gets its own
   `queries/crystallize-<topic>-<meeting date>.md` in every kind of ingest
   (single, batch or maintenance), with no exceptions. The core `SKILL.md`
   ingest summary moves ⑪ ahead of the log and report steps so the log entry
   lists the page. Maintain step ③ names ⑪ and ⑫. Not the lint check or the
   backfill (NW16 parts 2 and 3).
5. **Changelog and backlog:** PATCH-21 (NW8), PATCH-22 (NW14), PATCH-23 (NW15
   B, D and G) and PATCH-24 (NW16 rule), each with commits and status; mark
   upstream candidates. Backlog: NW14 implemented and moved to Closed; NW15
   noted as B, D and G done; NW16 noted as part 1 done.
6. **pm-wiki migration** (one wiki commit, after the skill commits): add the
   Swept through column to `MY-INTEGRATIONS.md`'s Sweep Registry with Notion,
   Confluence and GitHub set to `2026-10-28T00:00-07:00` and Slack and Email
   blank, unless `log.md` shows a sweep after 2026-10-28 (then use the start of
   that sweep's day and say so). Add `briefings/weekly-brief-YYYY-MM-DD.md` to
   the brief path example in `meta/contract.md`. Stage with
   `':(exclude)_status.md'`.
7. **Check:** run `python3 -m pytest` from the repo root and report the counts.
   Grep the skills for leftovers: "24", "48h", "last 7 days", `queries/weekly`,
   "Monday", and old log-line forms. Re-read each changed section once.
</steps>

<rules>
- Match each file's existing style and keep edits to what the design names. If
  the design is silent or contradicts itself on something you need, stop and
  ask rather than deciding; list any such question before you start writing if
  you can see it from the reading.
- Refer to "your fork" or "upstream", never "the plugin", and don't propose
  upstream issues or PRs.
- I'm learning git: explain each git step briefly in plain terms as you do it.
- Out of scope: NW15 A's citation and `Usage Guide.md` parts, C, E and F;
  NW16 parts 2 and 3. Mention anything else you notice; don't fix it.
</rules>

<done>
All seven steps committed, tests passing, and a short report: the commits, the
files changed per step, the test counts, anything you couldn't follow from the
design, and what to check on my next interactive maintenance run (each ledger
line's window, which timestamps moved, the brief's path and log line). On that
run, when it asks where the brief starts, I answer `2026-10-28T00:00-07:00`.
</done>
