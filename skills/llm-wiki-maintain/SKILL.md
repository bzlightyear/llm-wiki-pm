---
name: llm-wiki-maintain
description: Orchestrates the recurring daily-maintenance loop for the PM wiki — registry-driven multi-source sweep, ingest, daily brief, and a health check — with explicit interactive-vs-autonomous mode handling.
when_to_use: Use for "daily maintenance", "run the daily wiki", "morning sweep", "ingest all sources and brief me", "do the daily run", "maintain the wiki", or any scheduled/autonomous run that should sweep all sources and produce a brief. For a brief alone use llm-wiki-brief; for a single ingest use core llm-wiki-pm.
allowed-tools: Read Grep Bash Edit Write
---

# LLM Wiki Maintain

The recurring maintenance loop, as one defined operation. "Every day: sweep all
sources → ingest what's new → produce a brief → keep the wiki tidy" was
previously improvised step-by-step on faith; this skill makes the order, the
brief lifecycle, and the autonomous-mode behavior explicit.

This skill **orchestrates** — it does not reimplement. The actual work is done
by the core `llm-wiki-pm` skill (orient, ingest, lint) and `llm-wiki-brief`
(brief generation). Route to them at each step. If a sub-skill isn't installed,
fall back to the core skill's matching operation.

## Mode: interactive vs autonomous (decide first)

The skill's proactive behaviors (ambient "want me to add that?", per-step
confirmations, post-task offers) assume a human is watching. In a scheduled or
autonomous run nobody answers them — they stall or force a guess. So classify
the run before doing anything:

- **Interactive** — a human invoked this in a live chat. Normal behavior:
  surface takeaways, ask before mass updates (10+ pages), offer follow-ups.
- **Autonomous** — a scheduled/cron/loop run with no human in the loop (no one
  to answer a prompt). Then:
  - **Suppress interactive prompts.** Do not ask "want me to add this?" or wait
    on confirmations. Act on the clear cases.
  - **Act-then-report, never block.** Anything that *would* need a human
    decision (a risky mass update, an ambiguous create-vs-update, a possible
    contradiction) goes into a **Needs Review** queue in the brief instead of
    halting the run.
  - **Stay within safe bounds.** Never delete or supersede without a human;
    queue those. Snapshot before any overwrite (core rule still applies).

If you can't tell which mode you're in, ask once ("interactive or autonomous
run?") and proceed on the answer; default to interactive.

## The loop (ordered)

① **Orient.** Run the core Pre-Flight + orient (SCHEMA, index, log, overview,
   `_status.md`). Do not skip — every write still requires orient.

② **Registry-driven sweep.** Read the `## Sweep Registry` in
   `$WIKI/MY-INTEGRATIONS.md` and sweep **every** source listed, under the core
   **Source-completeness guard** (≥2 varied queries, classify
   `hits`/`empty-after-retries`/`failed`, bound output — concise/limit≤15/narrow
   scope first). One batch sweep up front satisfies freshness-first for the whole
   run (see the Freshness↔batch rule); do NOT re-sweep per page. If no registry
   exists, build it from connected tools + `Active Sources`, confirm (interactive)
   or queue for review (autonomous), and write it before sweeping.
   - **Each row's window** runs from its **Swept through** timestamp to the time
     the sweep's first query for that source runs (get it from `date` and record
     it before querying, so items posted during the sweep land in the next
     window). A blank Swept through starts at that source's Active Sources "Last
     used" date at 00:00, or 7 days back if there is none; say which in the
     ledger. Item times, paging and the 50-item ceiling:
     `references/source-discipline.md` → Source-completeness guard.
   - **An explicit range** ("sweep the last 3 days") is used as asked. When it
     starts before a source's Swept through: interactive, say before sweeping how
     much of it is already covered and ask once, for all sources, whether to
     re-read the whole range or sweep only since each Swept through; autonomous,
     sweep the range and note in the ledger which part was a re-read. In a
     re-read, an item named in an earlier sweep's "Not ingested" line in `log.md`
     isn't offered again unless its last-modified time is after that entry.

③ **Ingest findings.** For each new/changed signal, route to the core ingest
   flow (capture raw → thresholds → write/update → ⑥ crystallize each meeting
   → backlinks → log → MY-INTEGRATIONS → ⑫ entity promotion scan). Pages are
   private by default; never mark a digest `shareable`. Stamp
   `lifecycle: stub-intentional` on by-design thin stubs.
   The sweep's `log.md` entry records each source's window where they differ,
   and one shared window otherwise.

   **Advance Swept through** at the end of ③, in one edit to
   `MY-INTEGRATIONS.md`, to each source's "to" time when that source finished
   `hits` or `empty-after-retries` and every hit in its window was ingested, set
   aside by the user ("your scope call") or queued in Needs Review. Don't advance
   a source that `failed`, was left out of this run, or whose ingest didn't
   finish, so the next run re-reads its time. An explicit range advances a
   source only if it started at or before its Swept through; a source past the
   paging ceiling advances only as `source-discipline.md` allows.

④ **Brief.** Decide the cadence, then route to `llm-wiki-brief` and file the
   brief it writes, without offering:
   - **Cadence.** Interactive: from the user's words. "Weekly", "this week",
     "week in review" or "what did I miss this week" make it weekly; anything
     else, including "maintain the wiki", is daily, with no question asked.
     Autonomous: from the scheduled task's prompt, by the same words; a prompt
     that names no cadence is daily. The cadence never changes the sweep window.
   - **Daily:** the daily brief, filed as `briefings/YYYY-MM-DD.md`.
   - **Weekly:** the weekly brief, filed as
     `briefings/weekly-brief-YYYY-MM-DD.md`.
   - **A second run that day:** never replaces the first brief of its kind. It
     files at the next free name, `YYYY-MM-DD-2.md`, then `-3`, and the weekly
     equivalent (`llm-wiki-brief` §1).

   Both are dated by the run and get `lifecycle: dated-digest` (keeps them out
   of the orphan count). Either brief MUST include the Source Coverage ledger
   (one row per registered source, each with its window:
   `- Notion: hits (4 items), <from> → <to>`). Either brief starts from the
   latest filed brief's Needs Review, marking each item resolved, with where it
   went, or carried forward (`llm-wiki-brief` → Needs Review carry-forward).
   Its **Needs Review** section holds the carried items and this run's queue,
   in either mode, and is left out only when both are empty.

⑤ **Health check.** Run `scripts/lint.py $WIKI`. Surface the tiered summary,
   the export-surface (shareable) audit, and any new orphans/broken links.
   Then `lint.py $WIKI --auto-fix=content` (interactive: offer it; autonomous: run
   it). It backfills and alpha-sorts `index.md`, repairs escaped `\[\[` brackets
   and redirects links to superseded pages, and repairs citation markers (R7),
   declares cited sources that name exactly one file (R3) and rewrites midnight
   timestamps (R12). When the content fixes would change more than 10 pages it
   applies none of them and says so in a 🟡 warning: put that in Needs Review
   for the user to review and run by hand.

⑥ **Report.** One consolidated summary: sweep coverage ledger, pages
   created/updated, brief link, lint health delta with the number of fixes
   auto-fix applied, and the Needs Review queue.
   The delta compares ⑤'s counts with the newest `queries/lint-*.md` dated
   before this run, read before ⑤ runs lint.
   The brief's `log.md` line is its own entry (`llm-wiki-brief` → Daily and
   Weekly Briefs), not a "- Brief:" line under the ingest entry.

## Brief lifecycle convention

- `briefings/YYYY-MM-DD.md` — daily brief; `briefings/weekly-brief-YYYY-MM-DD.md`
  — weekly brief. Both dated by the run, `lifecycle: dated-digest`. A second
  brief of a kind on one date takes the next free `-2`, `-3` name and leaves
  the first as it is. Briefs
  stay in `briefings/` permanently; never move or archive them, since that
  breaks links to them.
- Briefs are orphans by design; the `dated-digest` flag keeps them out of lint's
  orphan count. Never link-spam pages just to de-orphan a brief.
- Briefs are not listed in `index.md`: lint skips them in its index check, and
  the index holds one fixed line pointing to `briefings/`. Don't add a brief to
  the index.

## What this skill does NOT do

Single ingests, ad-hoc queries, updates, persona/PRD/research/CRM work — route
to the core skill or the matching sub-skill. This skill is the daily loop only.
