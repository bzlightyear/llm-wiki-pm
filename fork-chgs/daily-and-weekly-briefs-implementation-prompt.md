# Daily and Weekly Briefs Implementation Prompt

created: 2026-10-29

Handoff prompt for a fresh session that implements the last parts of the
[Daily and Weekly Briefs Brief](daily-and-weekly-briefs-brief.md) (NW15): what
remains of A, then C and E together. B, D and G landed with NW14 (PATCH-23)
and F as PATCH-26. Paste the text below the `---` into a new session started
in this repo.

## Status

Status: ready to run. A, C and E were approved 2026-10-28.

---

Implement the rest of NW15 in your fork of llm-wiki-pm: what remains of A, and
C and E. They're approved; your job is to turn them into skill prose, check
the result, and record it. It's prose only, with no code or tests to change.

<context>
- Repo: /Users/pgoubert/Projects/llm-wiki-pm (your fork; branch `main`). Wiki:
  /Users/pgoubert/Projects/pm-wiki.
- Read first, in full:
  - `fork-chgs/daily-and-weekly-briefs-brief.md`, recommendations A, C and E
    and To approve.
  - NW15 in `fork-chgs/llm-wiki-pm-fork-backlog.md`, and PATCH-23 and PATCH-26
    in `fork-chgs/llm-wiki-pm-fork-changelog.md` (what's already built; the
    next entry is PATCH-27).
  - `skills/llm-wiki-brief/SKILL.md`, especially "Daily and Weekly Briefs" and
    §1 and §2, and `skills/llm-wiki-maintain/SKILL.md`.
  - `fork-chgs/doc-conventions-guide.md` for fork-chgs edits.
- **What's left of A.** Its §1 rewrite was overtaken by PATCH-23's windows and
  "What each brief holds" table, so only two parts remain:
  `skills/llm-wiki-pm/references/citation-spec.md` Grounding (a dated digest
  needs no primary source, but may declare raw records and should then use
  `[source:]` markers), and pm-wiki's `Usage Guide.md`, whose "Daily rhythm"
  still names New/Updated/Decisions/Open Questions sections that briefs no
  longer have. Confirm nothing else in A is still missing.
- **C, carry Needs Review forward.** The table already says a daily brief's
  Needs Review includes "unresolved items carried from the previous brief",
  but no procedure step does it. Add that step to brief §1 and §2 and maintain
  step ④: read the previous brief's Needs Review, and mark each item resolved
  (saying where it went) or carry it forward. "You owe" is out of scope; it
  stays with NW1, reading `overview.md`'s "Pete owes".
- **E, freeze briefs after their day.** A filed brief isn't edited after the
  day it was filed; later corrections go on the page that owns the fact and
  into the next brief's carry-forward. Same-day corrections are fine. One
  sentence each in `references/schema-guide.md` (`lifecycle: dated-digest`)
  and brief §1. pm-wiki's `log.md` shows later ingests editing briefs in place
  (for example "briefings/2026-10-17.md ('You owe')"), so also look for any
  step in the core skill, `references/ingest-guide.md` or
  `references/update-guide.md` that sends an agent to update a brief, and
  change it.
- The skills are symlinked into `~/.claude/skills/`, so a commit on `main`
  takes effect at the next session.
</context>

<steps>
Commit each step separately on `main`. Don't push.

1. **Before writing anything,** grep pm-wiki's project memories
   (`~/.claude/projects/-Users-pgoubert-Projects-pm-wiki/memory/`) for notes
   about briefs, Needs Review or editing briefs. Agents follow those over the
   skills, so list any that would contradict C or E and propose the change to
   each; don't edit them without my yes.
2. **A's remaining parts** in your fork: the `citation-spec.md` Grounding
   sentence.
3. **C and E** in your fork, in one commit, since E depends on C.
4. **Changelog and backlog:** PATCH-27 for A, C and E, following PATCH-26's
   format, marked upstream candidate where it applies. Move NW15 to Closed,
   with a status line naming every patch that built it (PATCH-21 to 23, 26,
   27). Update the brief's Status.
5. **pm-wiki** (one wiki commit, after the fork commits): rewrite the
   `Usage Guide.md` "Daily rhythm" lines to match the current briefs, and
   apply any memory changes I approved in step 1. Stage with
   `':(exclude)_status.md'`.
6. **Check:** grep the skills for leftovers (briefs edited later, Needs Review
   without carry-forward, "New/Updated" section names) and re-read each
   changed section once. Run `python3 -m pytest` from the repo root to confirm
   nothing broke, and report the counts.
</steps>

<rules>
- Match each file's existing style and change only what A, C and E name. If
  the brief is silent or unclear on something you need, stop and ask; list
  any such question before you start writing if you can see it from the
  reading. One I already see: should the first brief after the change carry
  forward only the latest brief's Needs Review, or also sweep older briefs for
  unresolved items (the 9/17 brief's CFP-8814 is one)? Ask me.
- Refer to "your fork" or "upstream", never "the plugin", and don't propose
  upstream issues or PRs.
- I'm learning git: explain each git step briefly in plain terms as you do it.
- Out of scope: NW3 (lint entries in `log.md`), NW1 and "You owe". Mention
  anything else you notice; don't fix it.
</rules>

<done>
All steps committed, tests passing, and a short report: the commits, files
changed per step, my answer to the carry-forward question and how it was
applied, any memory changes, and what to check on my next brief (Needs Review
carried or resolved, no edits to older briefs).
</done>
