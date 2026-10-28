# llm-wiki-pm Fork Backlog

created: 2026-10-01

Candidate work for the llm-wiki-pm fork: issues to fix, capabilities to add or
improve, and performance to tune. Each item records what is known when it's
captured. An item big enough to need one gets its own design, analysis or
proposal doc when the work starts.

## About This Document

The first seven items, NW1–NW7, were recorded during the sources and references
work and moved here word for word from section 10 of the
[Sources and References Design](sources-and-references-design.md) on
2026-10-01. IDs inside them, such as D9, I6, R12, N15, B3, a "section" number
or a "step" number, refer to that design unless an item says otherwise.
"Review F4" and the like refer to the
[Sources and References Review](sources-and-references-review.md).

**Adding an item:** give it the next ID (NW17 next), a bold one-line title, and
as much of this as is known: what happens, why it matters (with measurements and
dates), the proposal or scope of a fix, related items, and where it was found.
When an item is done or dropped, add a status line at its top and move it to
Closed.

---

## Open

**NW1. Orient content and `overview.md` freshness (separate design).**
`overview.md` only ever grows (70 KB), its action items and decisions are frozen
copies from meeting digests, and later updates never flow back into it, so Orient
loads stale and sometimes wrong information every session. The same design
covers what else Orient should load, including the org chart (NW9). Starting
points: the two findings below, and I8's revisit mechanism.
- **Action items have no update mechanism** (the fork changelog's ISSUE-1,
  found 2026-08-30).
  - **Symptoms in `overview.md`:** bullets under Active Bets, Action Items and
    Open Questions accrete inline `**Update DATE**` clauses into run-on
    paragraphs (the worst carry 3–4 rounds), the update markers vary in shape
    (`**Update DATE (context)**`, `**Resolved DATE**`, `**New DATE**`,
    `**Correction DATE**`, `**Confirmed DATE:**`), and the Action Items section
    isn't in `templates/overview.md`, which also asks for one line per bet or
    question.
  - **Root cause:** crystallize pages are point-in-time. `crystallize-guide.md`
    only creates them; its "update affected pages" step never names the digest
    itself, and `update-guide.md` never targets `queries/` digests. Decisions
    have a living home (the topic's concept or entity page), but actions
    don't: the "roadmap pages" `crystallize-guide.md` names as a place for them
    aren't a page type in `SCHEMA.md`. pm-wiki fills the gap with a concept page
    tagged `roadmap`.
  - **Measured in pm-wiki, 2026-08-30:** the Action Items tables of 3
    crystallize pages all kept their creation-time status (mostly "pending"),
    even for an item `overview.md` marked done on 2026-08-08. Since ingest step
    ⑦ is the only step that reliably sends an agent back to `overview.md`, its
    Action Items section became the de facto tracker, and its accretion is
    compensation for the missing update step.
  - **Briefs are another copy (NW15, 2026-10-28):** every daily brief since
    mid-October has a "You owe" list, and later ingests edited some of them in
    place to close items. NW15 leaves owed items to this design; until then a
    brief's "You owe" reads `overview.md`'s "Pete owes".
  - **Constraint on a fix:** compressing an overview bullet to one line plus a
    link to the digest would make the status signal worse, because the digest
    is the stale copy. A fix needs either a status-sync step in the update and
    crystallize flows, so the linked page becomes trustworthy first, or the
    compressed overview line as the source of truth for status, linking out
    only for rationale and history.
- **The indexer's Overview Regeneration mode** (the fork changelog's ISSUE-2,
  found 2026-08-30). If run (overview more than 7 days stale with log activity
  since), `worker-wiki-indexer` replaces everything below `overview.md`'s intro
  with generated Theme Clusters, Coverage, Recent Activity, Known Gaps and
  Stats sections, unlike the curated structure in use.
  - **Dormant:** no hook or skill triggers it. It's a judgment call in the
    product-manager role ("use after large ingests"), pm-wiki's `log.md` had no
    record of it ever running (327 entries, 2026-08-30), and near-daily edits
    keep `updated:` inside the 7-day window.
  - **Mitigated since 2026-09-29:** `pre-write.sh` snapshots `overview.md`
    before a whole-file replacement (`Write`, or the MCP's `vault` update or
    delete), so a regeneration can be undone (fork changelog PATCH-5). One done
    section by section through `Edit` would not be snapshotted. Since
    2026-10-13 (NW12) the mitigation is the checkpoint commit before a
    session's first write, which covers section-by-section edits too.
  - **For this design:** whatever structure it settles on for `overview.md`, the
    indexer's regeneration mode should produce it, or be removed.

**NW2. Fork `wirux/mcp-markdown-vault`. Deferred (review F4).** The permission
rule in D9 removes the damaging operations on this install at no cost, so the
fork is only worth doing if MCP edits are wanted back. The original plan
follows. The MCP's full-file round-trip causes
the bracket escaping (#47) and the timestamp dates (#49, N15), and its
maintainer has not responded since June 2026. The fork would be thin, on top of
upstream, with one fix per branch and a regression test in the project's vitest
suite: `CORE_SCHEMA` for #49 first, then text-preserving `frontmatter_set` and
`string_replace` for #47, and possibly #45 (orphaned server processes). Each fix
also goes back upstream as a pull request. `wiki-search.sh` then runs a pinned
build of the fork (a fork-only launcher difference). Costs: owning a
Node/TypeScript build and its dependency updates, and a small recurring merge fix
when upstream changes `wiki-search.sh`. If it lands, D9's deny rule can be
lifted. R12's auto-fix, the escaped-bracket check and the MCP hook matchers stay
as safety nets. `CORE_SCHEMA` alone isn't enough: it writes dates unquoted, so
the fork's #49 fix must keep string dates quoted (review F2).
Since NW5, the MCP runs as one shared server under launchd: a fork build means
repointing that LaunchAgent and restarting it, and streamable HTTP would go in
the fork if Claude Code drops SSE.
NW12 (2026-10-08): the server indexes `_archive/` snapshots, and its
`directory` filter can't exclude a folder. NW12 dropped snapshots on
2026-10-13 instead, so it gives no reason to fork.

**NW3. Lint log entries crowd out `log.md`.** Every lint run outside `--json`
mode appends an entry to `log.md` (`lint.py:772-780`). As of 2026-09-28 those
are 257 of the log's 480 entries, with up to 37 on a single day. That buries the
entries recording actual wiki work, and pushes the log toward `session-stop.sh`'s
500-entry rotation roughly twice as fast. The rotation is what forces migration
step M2 to read rotated `log-*.md` files (review finding F14). Options: append
at most one lint entry per day, updating it in place, or stop appending and rely
on the per-day report in `queries/`. Found in the design review
([Sources and References Review](sources-and-references-review.md), F14).

**NW4. The action-items file is outside the plugin's rules.**
- **What it is:** a root-level markdown file of open action items, ranked by
  urgency (about 400 lines, about 90 items). An agent created it at the user's
  request in a chat session, and it is regenerated or partly updated only when the
  user asks (39 `log.md` entries).
- **Why it drifts:**
  - It sits outside every page folder, so lint, the hooks and `index.md` skip it.
  - It has no frontmatter, sources or links, and no skill defines when or how it
    is updated.
  - Wiki pages mention it in prose, but none link to it.
- **Related work:** it has the same staleness problem as NW1: action-item
  status is never updated after capture, action items have no real page type,
  and `overview.md` holds frozen copies of them.
- **Options:**
  1. **Make it a first-class page,** for example `queries/open-action-items.md`,
     with standard frontmatter, sources and links. Define in the maintain skill
     when it is updated (for example on every run that ingests meetings), and let
     lint check it.
  2. **Remove it and generate the list on demand** from the action items in
     meeting digests, through a brief-skill command. There is no separate file to
     go stale, but it only works once digests' action items are marked done when
     resolved, which is NW1's open problem.

  They aren't exclusive: option 1 now, and option 2 once NW1 solves that.
- **Found in:** the design review (F15).

**NW7. No link search finds every incoming link.**
- **What happens:** archiving, superseding or renaming a page means updating
  every link to it, but none of the ways to find those links is complete:
  - `backlinks.py` reads `entities/`, `concepts/`, `comparisons/`, `queries/`
    and `_archive/`. It skips `briefings/`, `index.md`, `overview.md`, the
    action-items file and the other root files, which held 747 links to live
    pages on 2026-09-30 (analysis M4).
  - The wiki-search MCP's `view(action=backlinks)` reads every file, but a
    running server misses renamed and new pages until it's reindexed or its
    session restarts. On 2026-10-01 the first reindex after a rename didn't
    take, and a second one did.
  - When two files share a page's file name, the MCP can credit the page's
    links to the wrong one (M1, below).
  - The docs don't say which to use. Update ① names `backlinks.py`. The core
    skill's §6 Archive, `update-guide.md`'s Supersede steps and the SCHEMA
    template's Archive line name none, and the vault contract says "Incoming
    links to a note → `view.backlinks`".
- **M1, the one doing harm today:** one `_archive/` file has the exact file
  name of a live concept page. The page's slug ends in a date, so the name
  looks like a snapshot's. It came from a move into `_archive/` by hand on
  2026-08-11, not from `snapshot()`.
  - The MCP resolves the page's links to the archive copy (shortest path wins,
    and `_archive` sorts first), so it reports 0 backlinks for the live page.
    Rechecked 2026-10-01.
  - `backlinks.py` finds 8 links on 6 pages, but not the one in `index.md`.
  - A lookup by file name finds two files, and Obsidian sends the links from
    snapshots to the archive copy.
  - Lint doesn't read `_archive/`, so nothing reports it.
  - **Why it happened:** the core skill's §6 Archive says to move a page to
    `_archive/` "preserving path", so a move by hand keeps the bare name.
    `snapshot()` names its copies `<slug>-<date>`, but archiving doesn't use
    it.
- **Scope of the fix,** to be written up as a complete proposal before any
  change:
  1. `backlinks.py` also reads `briefings/` and the root files except
     `log.md`, which is history. `raw/` stays out, since records are
     immutable.
  2. The archive, supersede and rename docs name `backlinks.py` as the link
     search. The vault contract's "Incoming links" line points at it, or says
     that the MCP lags.
  3. Rename M1's archive copy to a dated name. `citation-spec.md` says
     `_archive/` is immutable, so the proposal has to say whether a rename
     counts as a change.
  4. Decide how archived pages are named from now on, so a bare-name copy
     can't come back: a doc rule (`_archive/<slug>-<date>.md`, as `snapshot()`
     names them) or a script.
- **Not included:** lint checking the links in `index.md` and `overview.md`
  (analysis M2), and the analysis's other optional follow-ups (its section 9).
- **Since NW5:** the one shared server can run for weeks, and its backlinks
  stay stale until a reindex, which adds to the case for `backlinks.py`.
- **How the server's index updates** (read from `mcp-markdown-vault` 2.3.0's
  `dist/use-cases/vault-indexer.js`, 2026-10-03):
  - **No periodic reindex.** Updates are driven by file events, with no timer
    for a full rescan.
  - At startup it watches the whole vault (chokidar) for `add`, `change` and
    `unlink` events.
  - An added or changed `.md` file is queued for indexing after a 500 ms
    per-file debounce. A deleted `.md` file is queued right away and leaves the
    index.
  - The `system` tool's `status` action reports `watcherState: active` while
    the watcher runs.
- **New files index live (confirmed 2026-10-03).** A server started before an
  ingest found the ingest's new pages through `semantic_search` the next day,
  with no reindex.
- **Renames are the open case.** A rename should arrive as a delete and an
  add, which the watcher handles. The failed first reindex on 2026-10-01
  points somewhere else. Two candidates, neither verified:
  - backlinks resolve against a cache that file events don't refresh
  - on macOS, chokidar reports some renames as a pair of `change` events,
    leaving the old path in the index
  Testing a rename before and after a reindex would show which.
- **A second same-name file (found 2026-10-08, NW12):**
  `_archive/cfp-mcp-ai-insights-history-2026-09-30.md` is a snapshot of the
  then-live `cfp-mcp-ai-insights-history`, taken by the migration on
  2026-09-30. A history split on 2026-10-06 gave a new live page the same
  name. A snapshot's name equals a split page's name whenever a slug ends in
  `-history`. NW12 removed snapshots on 2026-10-13, this one included. M1
  itself is an archived page and stays for step 3.
- **`backlinks.py` no longer scans `_archive`** (done 2026-10-13, NW12), part
  of step 1. Snapshots had been 35 of 57, 88 of 133 and 63 of 102 linking
  files for three busy pages on 2026-10-08. The rest of step 1 is open.
- **Found in:** the NW6 analysis (M1, M4). Split out of NW6's next step 4 on
  2026-10-01.

**NW9. Org structure is kept in three places.**
- **What happens:** three copies of who reports to whom, and nothing keeps them
  in step:
  - **SCHEMA.md's Domain section,** an org chart written by hand when the wiki
    was set up. Orient reads SCHEMA.md every session.
  - **`concepts/relationship-map.md`,** kept by the persona skill and, since
    fork changelog PATCH-14, by the entity-promotion scan. Orient never reads
    it; only pre-meeting briefing (core skill §9) does.
  - **Person pages' `reports_to` and `direct_reports` fields,** defined in
    SCHEMA's person-page frontmatter.
- **Measured in pm-wiki, 2026-10-02:** the Domain section's org chart was last
  edited 2026-08-06, and the map's content 2026-09-04. 16 of the map's 33
  people don't appear in the Domain section. Later the same day, the
  person-page fields were measured too (below).
- **The person-page fields disagree with the map, and with each other**
  (measured in pm-wiki later on 2026-10-02):
  - **Map vs. fields:** all 55 person pages carry `reports_to`,
    `direct_reports` and `peers`. 34 of them have a row in the map's Org
    Chart table, and 21 don't. Comparing the 34, 11 people disagree
    between the map and their own page:
    - In 7 the page is more complete: a newer report, or a manager the map
      still lists as "unknown."
    - In 4 the map has a link the page lacks. 3 of those 4 are history
      written into a map cell ("moved from X," "formerly X," "temporary
      matrix"), which reads as a current relationship to anything parsing
      the links.
    - So neither copy is reliably the newer one.
  - **Fields vs. fields:** 18 links have no reverse on the other person's
    page. That's 14 non-mutual `peers`, 3 where A's `reports_to` names B
    but B's `direct_reports` lacks A, and 1 the other way. Nothing checks
    reciprocity.
  - **A fourth copy:** 38 of the 55 person pages repeat `reports_to` and
    `direct_reports` as bullets in a body Relationships section, so one
    page can disagree with itself.
  - **"Unknown" has two spellings:** the map writes `unknown`, and person
    pages write `null`.
- **Seen happening, 2026-10-02:** a daily-maintenance ingest created a person
  page from a user statement of who the person reports to. It added the map
  row and a body line on the manager's page. It did not set the new page's
  own `reports_to` and `peers` fields, or add the person to the manager's
  `direct_reports` or the new peer's `peers`. The user caught it. Two
  reasons it was easy to miss:
  - Core skill §2 ⑫ names only the map ("add the new person's org-chart
    row ... under their manager's `direct_reports` cell"). The person-page
    fields aren't mentioned, and that step's "`direct_reports` cell" is the
    map's.
  - Lint reads none of these fields, so the check the run ends with was
    clean.
- **Why it matters:** every session's Orient starts from the oldest and least
  complete copy, and a question like "who does X report to" can get different
  answers depending on which copy an agent reads.
- **Proposal** (agreed 2026-09-26 as part of NW1): replace SCHEMA's org chart
  with a pointer to the map, keeping the rest of the Domain section (role,
  products, tools, competitors). Give the map a compact "Org chart" section at
  the top, and have Orient read only that section, and only if the map exists.
  Changing Orient's reading list is a CONTRIBUTING "discuss first" item, so it
  starts fork-only or as an upstream issue.
- **To decide:**
  - Which copy is the source of truth: the map, or the person-page fields with
    the map's org chart built from them. The 2026-10-02 measurements point to
    the fields:
    - Every person page already has them.
    - They're one value per page, so they can be checked mechanically.
    - The map's cells mix current relationships with history prose.
    - Generating the map's Org Chart from the fields would remove a copy
      instead of adding a check between two.
  - Whether lint checks that the map and the person-page fields agree.
    Whatever the source of truth, lint should check the fields themselves (a
    🟡 warning):
    - `reports_to` and `direct_reports` are each other's reverse, and
      `peers` is mutual.
    - It must allow more than one `reports_to`, because matrix reporting
      exists in pm-wiki.
    - `unknown` and `null` count as the same value.
    - `--auto-fix` could fill in a missing `direct_reports` or `peers`
      reverse. It should not fill in `reports_to`, since a wrong guess there
      states the wrong manager.
  - Whether to drop the body Relationships bullets that repeat the fields,
    or have them generated.
  - Wording for §2 ⑫, the persona skill and the SCHEMA template: changing
    someone's org placement means updating the person's fields, the other
    side's fields, and the map in the same edit. This only matters until the
    map is generated.
- **Includes the map's creation rule.** The SCHEMA template's person-page
  section, the persona skill and the core skill's §2 ⑫ create the map once
  "3+ person entities" exist. Since `f5bd6b0` the map covers internal people
  only, so the rule should count internal people, or a wiki holding only
  customer contacts would get an empty map.
- **Related:** NW1 (what Orient loads).
- **Found in:** a session on 2026-09-26, recorded inside NW1. Split out
  2026-10-02. Field disagreement measured, and a missed reverse update seen
  during an ingest, also 2026-10-02.

**NW11. Skills cite an `AGENTS.md` that wiki sessions never load.**
- **What happens:** `AGENTS.md` is the plugin repo's behavioral contract. It
  loads only in sessions whose working folder is the plugin repo. Setup copies
  only the files in `skills/llm-wiki-pm/templates/` into a new wiki, and none
  of them is an `AGENTS.md` or `CLAUDE.md`. pm-wiki has neither. Yet several
  skills defer to it:
  - `llm-wiki-research`: "Orient per AGENTS.md before any writes".
  - `llm-wiki-brief`: "Full orient (AGENTS.md 4-step protocol)", and
    "Behavioral Constraints (per AGENTS.md)".
  - `llm-wiki-persona`: "Behavioral Constraints (per AGENTS.md)".
  - `llm-wiki-prd`: "Per AGENTS.md, orient before any write", and "Inherited
    from AGENTS.md".
  - `citation-spec.md` names AGENTS.md among the files that point to it.
  In a pm-wiki session these references lead nowhere. Rules stated only in
  `AGENTS.md`, such as the full "Snapshot before destructive ops", never
  reach the agent.
- **Likely cause:** upstream wrote `AGENTS.md` as a portable contract for
  porting the plugin to other agents (README: "the portable reference if you
  want to port to another agent"). It expected Claude Code to get the rules
  from the skills and hooks. The "per AGENTS.md" lines were probably written
  in the plugin repo, where the file does load.
- **Why it matters:** the skills' references resolve to nothing, and the
  contract isn't in context in wiki sessions.
  It would not have prevented NW10's missed snapshots, since that rule was in
  context from the core skill.
- **Proposal: read the contract during Orient.**
  - Add a step to core skill "Orient Every Session" that reads the fork's
    `AGENTS.md`. The skill finds it relative to its own folder
    (`${CLAUDE_SKILL_DIR}/../../AGENTS.md`), which holds for the symlinked
    install and for a plugin install, since both carry the whole repo. Orient
    already reads `$WIKI/SCHEMA.md` and the other root files by path, so the
    step works whichever project the session starts in.
  - The "per AGENTS.md" references in the sub-skills then point at something
    the agent has read. They can stay as they are.
  - There's one copy, so nothing can drift, and nothing has to be added to
    pm-wiki or to setup.
  - Clean up `AGENTS.md` first, since every Orient would read it (about 718
    words):
    - Its Wiki Path Resolution still reads `.wiki-path`, which NW5 removed.
    - Model Routing, Skill Architecture and Agent Surfaces are about the
      plugin, not wiki work. Move them to a plugin-side file or trim them.
    - The plugin repo's own development sessions load the same file as
      their project instructions, so keep a version that suits wiki
      sessions.
  - Like the rest of Orient, it's read once per session, so it can still be
    lost to compaction in a long session.
  - **Read only the Behavioral Constraints section.** Measured in pm-wiki on
    2026-10-02, Orient already loads about 15,400 words: core `SKILL.md`
    3,441, `overview.md` 8,626, `SCHEMA.md` 2,555, `index.md` 591, and the
    last 30 lines of `log.md` 171. The whole `AGENTS.md` (718 words) would
    add about 5%, and about 3% after the cleanup above. Most of what's left
    after the cleanup (the Orient protocol and source attribution) repeats
    the core skill. Behavioral Constraints (245 words) is the part the
    skills don't carry, so reading only that section adds about 1.5%.
    Trimming `overview.md` under NW1 would save far more than this costs.
- **Ruled out: a pm-wiki `CLAUDE.md`** importing `AGENTS.md`. It loads only
  in sessions started inside pm-wiki. The wiki is used from other projects
  (`$WIKI_PATH` since NW5), and Claude Code doesn't load a `CLAUDE.md` from
  an unrelated folder when a file there is read. That was tested on
  2026-10-02: reading a page in a scratch folder outside the session's
  working folder didn't load that folder's `CLAUDE.md`. Reads through Bash or
  the wiki-search MCP don't trigger loading at all. It could still be added
  for sessions started in pm-wiki, but it isn't the fix.
- **Ruled out: folding the rules into core `SKILL.md`** and dropping the
  "per AGENTS.md" references. That's simpler, but it duplicates rules and
  gives up `AGENTS.md` as the single contract.
- **Upstream:** changing Orient's reading list is a "discuss first" item in
  upstream's CONTRIBUTING (as in NW9). It doesn't block the fork.
- **Related:** NW10 (the snapshot rule lives in `AGENTS.md`), NW1 and NW9
  (other changes to what Orient reads), NW5 (`.wiki-path` removed, wiki used
  from any project).
- **Found in:** the NW10 analysis, an llm-wiki-pm session on 2026-10-02.

**NW15. Briefs are built, filed and used in ways the skills don't describe.**
- **Status: approved 2026-10-28, all four choices. B, D and G done
  2026-10-28 with NW14 (changelog PATCH-23); A, C, E and F not implemented.**
- **What happens:** daily briefs are built from each source sweep, in a format
  no skill defines; brief §1 still describes a 24–48h `log.md` summary. Weekly
  briefs have no lifecycle or date rule, and NW14 files them in `queries/`,
  where none have been since you moved them to `briefings/` on 2026-10-28. A
  brief's "You owe" and "Needs review" items are never carried into the next
  brief, filed briefs are sometimes edited later and sometimes not, lint never
  adds briefs to `index.md`, and brief log entries take three forms.
- **Seen:** the 10/28 weekly sweep covered 10/19–10/28 but its brief stops at
  10/23, so seven 10/26–10/27 transcripts are in no brief. CFP-8814, queued in
  the 9/17 brief's Needs review, is on no wiki page.
- **Proposal:** seven groups of changes (A–G), in the
  [Daily and Weekly Briefs Brief](daily-and-weekly-briefs-brief.md). B and D
  revise NW14 and are best done before or with it. Owed items ("You owe") are
  left to NW1; briefs stay out of `index.md`, with one pointer line.
- **Related:** NW14 and NW8, NW4 (the action-items file), NW1 (`overview.md`'s
  "Pete owes" list).
- **Found in:** a session on 2026-10-28 analyzing how briefs are created,
  stored and used.

**NW16. Meetings stop getting crystallize pages.**
- **Decided 2026-10-28:** every meeting gets its own crystallize page, dated
  with the meeting date, however it was ingested. Part 1 (the rule) is
  approved to be built with NW14; parts 2 and 3 need a short design first
  (lint details, cost, the backfill list).
- **Part 1 done 2026-10-28** (changelog PATCH-24). Crystallize is now ingest
  step ⑥, not ⑪, and the old ⑥–⑩ are ⑦–⑪. Parts 2 and 3 not started.
- **What happens:** ingest step ⑪ (`ingest-guide.md:139`) says to crystallize
  every transcript, but 43 of pm-wiki's 152 transcripts are in no crystallize
  page's `sources:` (17 from September, 23 from October, 3 from March and June).
  Counted by meeting date: every transcript got one from 2026-08-20 to 09-16; 5
  of 23 did from 09-17 to 10-02; nearly all did from 10-01 to 10-15; none of 21
  has since 10-16. No log entry, session or skill change records a decision to
  stop. The only logged exception is three meetings on 10-14 "fed straight into
  concept pages" (pm-wiki `log.md:178`).
- **Likely causes (inferred, not confirmed):**
  - Maintain step ③ summarizes ingest as "capture raw → thresholds →
    write/update → backlinks → log → MY-INTEGRATIONS", which leaves out ⑪ and
    ⑫. Every sweep since 10-17 is logged as a "maintenance sweep".
  - ⑪ comes after "⑩ Report every file touched" in the core skill's summary, so
    a batch run reaches it after its work looks finished.
  - Orient reads recent `log.md` entries, which since 10-14 show meetings going
    straight into concept pages as dated sections, a pattern a later run can
    copy.
  - Entity promotion (⑫) is probably skipped the same way (not checked).
- **Proposal:**
  1. **The rule:** `ingest-guide.md` ⑪ says every meeting transcript gets
     `queries/crystallize-<topic>-<meeting date>.md` in every ingest, single,
     batch or maintenance, with no exceptions. The core skill's ingest summary
     moves ⑪ ahead of the log and report steps, so the log entry lists the
     page. Maintain step ③ names ⑪ and ⑫.
  2. **Lint:** a warning for a `raw/transcripts/` record that no crystallize
     page declares in `sources:`, so drift shows in the session-start health
     check whatever caused it. About 20 lines in `lint.py` plus tests.
  3. **Backfill:** crystallize pages for the 43 transcripts from their raw
     records, as one batch in pm-wiki, separate from your fork's changes. It is
     a mass update, so the list gets your sign-off first. The 3 from March and
     June predate current conventions and could be left out.
- **Related:** NW1 (crystallize action items go stale; this adds more of them
  until NW1 is designed), NW15 (a weekly brief could group a week's meetings by
  their crystallize pages), NW14 (maintain step ③ is edited by both).
- **Found in:** the 2026-10-28 brief analysis (NW15), checking whether meetings
  have meeting-dated pages.

## Closed

**NW5. One wiki-search server per wiki.**
- **Status: done 2026-10-02.** pm-wiki is served by one shared server under
  launchd (`local.wiki-search`, SSE on port 3100 with a bearer token), and every
  project's sessions connect to it. `$WIKI_PATH` is the default wiki: the
  projects' `.wiki-path` files were removed, and a `.wiki-path` now only marks a
  project that uses another wiki. See the
  [NW5 Shared Wiki-Search Analysis](nw5-shared-wiki-search-analysis.md) and the
  [Wiki-Search Launchd Guide](wiki-search-launchd-guide.md), which also covers
  adding a second wiki. The text below describes the problem as found.
- **What happens:** `wiki-search` is registered at user scope in
  `~/.claude.json` as a stdio server (`sh …/hooks/wiki-search.sh`), so every
  Claude Code session in any project starts its own copy at session start,
  whether or not it uses the wiki. The SessionStart hook doesn't start it; its
  npx step only warms the package cache when it's missing. Measured 2026-09-30:
  one copy uses about 580 MB. Every open session adds another, and each one
  writes the same `.markdown_vault_mcp/` vector index.
- **Wanted:** wiki access from every project (all 13 `.wiki-path` files point at
  pm-wiki), served by a single process.
- **Proposal:** the MCP already has a multi-client mode (`MCP_TRANSPORT_TYPE=sse`:
  `GET /sse` per client, shared vault, index and embedder, separate workflow
  state per client). This is a local install change, with no plugin change.
  1. A LaunchAgent, `~/Library/LaunchAgents/local.wiki-search.plist`, like the
     existing `local.wiki-path-env.plist`. It runs `sh hooks/wiki-search.sh` at
     login with `KeepAlive`, `MCP_TRANSPORT_TYPE=sse`, `PORT=3100` (3000 is a
     common dev-server port), `HOST_BIND_ADDRESS=127.0.0.1`, the vault fixed to
     pm-wiki through `WIKI_PATH` and a pm-wiki working directory, and a log in
     `~/Library/Logs/wiki-search.log`.
  2. Replace the user-scope entry with
     `claude mcp add --transport sse -s user wiki-search http://127.0.0.1:3100/sse`.
     The server name stays `wiki-search`, so tool names, D9's deny and `ask`
     rules, and the pre-write and post-validate matchers are unchanged.
  3. Verify from a new session that the tools work and exactly one server
     process runs.
- **Costs and open points:**
  - A port on 127.0.0.1 can be reached by any local process, and in principle by
    a web page through DNS rebinding, while a stdio copy talks only to its own
    session. pm-wiki holds customer and 1:1 content, so set `MCP_AUTH_TOKEN` in
    the plist and a matching `Authorization: Bearer` header in the Claude Code
    entry.
  - A package upgrade, or switching to NW2's fork build, needs
    `launchctl kickstart -k`. Sessions open at the time may have to reconnect.
  - The vault is fixed to pm-wiki for every project. A project whose
    `.wiki-path` pointed at another wiki would still get pm-wiki.
  - The plugin manifest keeps its per-session stdio server for plugin installs.
    Whether the plugin should document the shared setup is left open.
- **Related:** NW2's possible #45 fix (orphaned server processes).
- **Found in:** a check of running servers after step 8, 2026-09-30.

**NW6. Folder pages don't resolve outside the fork's own tools.**
- **Status: fixed 2026-10-01** (next steps 1-3 below), with option 4 of the
  [analysis](nw6-page-name-resolution-analysis.md) (its section 9): the wiki's four
  folder pages were renamed `queries/<slug>/<slug>.md` (pm-wiki `fbfb8d7`,
  `82c63d8`), and the fork's docs and `slug()` changed with them (`84aeeac`).
  The text below describes the gap as found. Next step 4 moved to NW7, and
  next step 5 is done, so NW6 is closed.
- **What happens:** a multi-file page is a folder whose main page is
  `README.md` (`queries/<slug>/README.md`, section 5.2). `slug()` names that file
  after its folder, so lint, `backlinks.py`, the post-write check, `sources:`
  entries and citations all resolve `[[<slug>]]` to it. Obsidian and the
  wiki-search MCP resolve a link by file name instead. No file is named
  `<slug>.md`, so for them the link points at nothing.
- **Measured 2026-09-30:** 32 links point at the wiki's 4 folder pages (3
  research sprints and a PRD): 23 on 15 pages, 4 in `index.md`, 3 in `log.md`
  and 2 in a reconstructed record that quotes the log. Lint reports no broken
  links. For the Kiro sprint's `README.md`, the MCP's `view(action=backlinks)`
  returns 0 links, while `backlinks.py` finds 21 on 15 pages, archives included.
  No agent has used the MCP's lookup: across the 128 Claude Code sessions saved
  since 2026-08-07, agents made 47 MCP read calls (31 of them semantic searches)
  and no backlinks call, while `backlinks.py` ran in 64 sessions. The only two
  backlinks calls were the tests that found this gap.
- **Impact until fixed.** No page's content or frontmatter is changed by the
  mismatch itself. Two things can still go wrong:
  - **Obsidian:** the links show as unresolved (dimmed, no hover preview), and
    the `README.md`'s backlinks pane misses them. The graph draws none of them,
    because this vault hides unresolved links. Clicking one creates an
    empty note named after the folder at the wiki root, Obsidian's default
    location for new notes. That happened once on 2026-09-30, and the note was
    deleted. While such a note exists, Obsidian resolves the link to it, so the
    link opens a blank page instead of looking broken. Lint and session start
    don't scan root files, so nothing reports it, and a `git add -A` in the
    wiki would commit it. If Obsidian's new-note location were set to the
    current file's folder, the note would instead share the folder page's
    slug, and lint would report both (R9, R12).
  - **Agents:** possible but not seen. The core skill lists the MCP's
    backlinks action among its tools, and the vault contract (`meta/contract.md`)
    says "Incoming links to a note → `view.backlinks`". An agent that used it
    on a folder page would conclude nothing links there. Update ① uses
    `backlinks.py`, but nothing says which tool archive, supersede and rename
    use. One that archived, superseded or renamed a folder page that way would
    leave its inbound links broken. Lint reports those as 🔴 at its next run,
    and session start shows its counts, so the break would show within a
    session and could be undone from `_archive/` and git.
  - **Scope and growth:** only the 4 folder pages and their 32 links. Each new
    research sprint or PRD adds another folder page.
- **Until fixed:** don't click those links in Obsidian, and delete any empty
  note a click creates at the wiki root.
- **Why the design missed it:** section 5.2 makes `slug()` "the one ID function
  for every reference site", and I6 requires each link to resolve to a slug.
  The design and both reviews checked resolution only against the fork's own
  code. Obsidian appears only as a writer (B3), and the wiki-search MCP
  analysis covered its writes, not how it resolves links. No invariant says a
  page's name must resolve to the same file for every reader. `slug()` and the
  file name agree for every page except a folder's `README.md`.
- **Next steps:**
  1. **Audit every reader first, with a trial of the fix.** Done 2026-09-30, in
     [NW6 Page Name Resolution Analysis](nw6-page-name-resolution-analysis.md).
     The fix resolved every link for every reader tested, and the audit
     found five other mismatches. Its section 9 compares four fixes and records
     the one chosen, and leaves the other mismatches as optional follow-ups.
     List each component
     that turns a page name or path into a file:
     - the fork's scripts, hooks and docs, including anything that treats the
       name `README.md` specially;
     - each MCP action that takes a name or path (`backlinks`, `read`, `outline`,
       `frontmatter_get`, `bulk_read`);
     - Obsidian: links, embeds, `[[page#heading]]` and aliased links, the graph,
       the backlinks pane, the file explorer, search, and Dataview queries;
     - the Orient files (`index.md`, `overview.md`).

     Test each one on the live wiki, read-only, and on a scratch copy with the
     fix in step 3 applied. Point a separate wiki-search MCP at the copy, and
     have the user open the copy as an Obsidian vault and click a few folder
     links. The result is a table of reader and link form, today and with the
     fix. It decides whether the fix is enough, shows whether anything depends
     on the name `README.md`, and may find other mismatches to fix in the same
     change.
  2. **Extend I6** so a page's name resolves to the same file for every reader,
     not only to a slug, and add a lint check that keeps it true, such as a
     page's slug equalling its file stem. Otherwise each new folder page brings
     the gap back. Done without a new rule: `slug()` is now the file stem, so
     lint names a page the way every other reader does, and links to a page
     saved as `README.md` are reported as broken.
  3. **Fix, done 2026-10-01: name a folder's main page after the folder,**
     `queries/<slug>/<slug>.md`, instead of `README.md`.
     - The slug doesn't change, so no link changes, and the fork's tools keep
       working, while Obsidian and the MCP find the file by name. That removes
       both risks above, and every Obsidian link form resolves.
     - The wiki needs 4 renames, 6 prose lines on the 3 sprint pages that call
       themselves "this README" or give their own path, and 2 lines in its
       `meta/contract.md`, which mirror the template. No `sources:` entry names
       a folder page's path, and no link names `README`. Delete any stray root
       note first, or two files would share the name. After the rename,
       reindex every running wiki-search server or restart its session. A
       running server doesn't see renamed or new pages until it rebuilds.
     - The fork needs 19 doc lines changed in 9 files, among them the core
       SKILL's Query step, `output-formats.md`, `citation-spec.md`, and the
       research and PRD sub-skills (the analysis's section 10 lists them all).
     - Opening a page by clicking its folder in Obsidian's file explorer still
       needs the Folder notes plugin. Its default naming, `{{folder_name}}`,
       matches this one, so it would work without setup.
     - `slug()` dropped its `README.md` rule, and `backlinks.py` its copy.
       Without it, an un-renamed wiki loses 23 links, but the fork has one
       wiki, renamed in the same step.
     - `<folder>/<folder>.md` is also the default naming of the Obsidian Folder
       notes plugin.
     - Upstream's docs prescribe `README.md`, but its lint already names a
       page by its file stem, so the convention breaks upstream's own links.
       No upstream issue is filed for now.
  4. **Moved to NW7, 2026-10-01.** **Make archive, supersede and rename name
     their link search:**
     `backlinks.py`, not the MCP's lookup. Point the vault contract's
     "Incoming links" line at it too. First `backlinks.py` has to read
     `briefings/`, `index.md`, `overview.md` and the other root files. It skips
     them today, missing 747 links to live pages.
  5. **Done 2026-10-01: the user set it to `raw/assets` in Obsidian.**
     **Point Obsidian's attachments at a routed folder.** The wiki's
     `.obsidian/app.json` sets `attachmentFolderPath` to `raw/attachments`, so
     a file pasted or dropped into a note in Obsidian recreates the unrouted
     folder the migration emptied (review F15). Set it to `raw/assets` (Settings
     → Files and links). The file still needs a markdown record before a page
     can cite it.
- **Alternatives set aside:**
  - **Links with a path,** `[[<slug>/README|<slug>]]`: lint, `backlinks.py`
    and the post-write check would all need changing, and agents would have to
    remember the special form.
  - **An Obsidian folder-notes plugin:** it opens a folder's note when the
    folder is clicked, but doesn't change how links resolve, in Obsidian or
    the MCP.
  - **Frontmatter `aliases:`:** Obsidian doesn't use aliases to resolve a
    `[[name]]` link.
- **Found in:** the user, viewing a research sprint page in Obsidian after step
  10b, 2026-09-30.

**NW10. Script writes to pages get no snapshot.**
- **Status: merged into NW12 on 2026-10-13, and done with it the same day**
  (fork changelog PATCH-19). NW12 proposed dropping
  snapshots and relying on git, with this item's checkpoint commit made before
  a session's first write to the wiki. That covers script writes, so the
  snapshot fill below isn't needed. The checkpoint doesn't check `.wiki-lock`:
  `session-start.sh` writes that lock at the start of every session in any
  project, and `session-stop.sh` clears it at the end of any session, so the
  check below would skip most checkpoints. The user's commits, called rare
  below, have come every 1 to 5 days since 2026-09-30. The text below
  describes the problem as found.
- **What happens:** the pre-write hook snapshots a page only when the Write,
  Edit, MultiEdit or MCP `vault`/`edit` tools change it. A page changed by a
  Bash command (a `python3 - <<'EOF'` heredoc, or a helper script run through
  Bash) gets no `_archive/<slug>-<date>.md`. The design accepts this: I7's
  guarantee excludes "Bash, script, Obsidian or git writes", with git as the
  undo and a behavioral rule ("snapshot by hand before a script edit") for
  agents.
- **Seen happening, 2026-10-02:** the first big daily-maintenance sweep after
  the sources and references work changed 9 concept pages with Edit and 11
  pages with Bash heredocs (10 person pages and `concepts/relationship-map.md`).
  `_archive/` got the 9 concept snapshots, each identical to git HEAD, and none
  of the 11.
- **Why the rule was missed:** distance from the decision, not absence. The
  sweep's transcript shows the agent read the rule ("by hand before a script
  edit") at entry 29 of 1,198, when the core skill loaded. Its first script
  write to a page came at entry 646, and the context was never compacted. So
  the rule was in context the whole time, about 600 to 800 steps before the
  writes, while the agent worked through 18 large meeting notes.
  - In the skills, agents see the rule only as a parenthetical in core skill
    §4 Update and in the split procedure (`citation-spec.md` "Page
    lifecycle"). Its full statement, `AGENTS.md`'s "Snapshot before
    destructive ops", isn't loaded in pm-wiki sessions (see NW11).
  - The two places that point agents to scripts, and that an agent rereads
    when it decides to script, say nothing about snapshots: core `SKILL.md`
    "Edit frontmatter with the Edit tool (in a script,
    `wikifm.set_field`/`set_list`)", and `citation-spec.md`'s "Editing
    frontmatter" snippet.
  - Bulk person and org-chart updates make script writes routine, not the
    rare case I7 assumed.
  - Reading the full contract every session (NW11's Orient step) would not
    have prevented this miss, since the rule was already in context.
- **Why it matters (low to moderate):** snapshots exist only so a bad change
  can be rolled back, and the user hasn't used that so far. They are read
  automatically, though not for rollback: the wiki-search MCP indexes them,
  and `grep -r` and `backlinks.py` read them (NW12, 2026-10-08). That hurts
  queries, not this item's exposure. The exposure is content added since the
  last commit and then damaged by a later script write. Git still has
  everything in the last commit. The user commits rarely, often not for many
  sessions, so that window is wide.
- **Options ruled out:**
  - **Auto-commit at session end** (the fork's `dc6bc6c`, backed out in
    `dfdd98c`, changelog Background): SessionEnd fires per short-lived backend
    session. Since the move to user-level `settings.json` hooks and NW5's
    `$WIKI_PATH` default, `session-stop.sh` also runs at the end of every
    Claude Code session on the machine, in any project, and targets pm-wiki.
    An auto-commit there would commit a pm-wiki sweep's partial work whenever
    any other session ends. A likely cause of the old flood, not verified:
    `session-start.sh` rewrites `_status.md` every session, and the old
    snippet ran `git add -A`, so almost every session end had a change.
  - **Filling missing snapshots from git HEAD at session end alone:** with
    rare commits, HEAD can be many sessions old. A page script-edited on two
    days in a row would get the old HEAD version both times, and the first
    day's version could not be restored.
- **Proposal:** a session-start checkpoint plus a git-based snapshot fill.
  - **Checkpoint:** when a session starts with pm-wiki as its working folder
    (from the hook input's `cwd`, not `$WIKI_PATH`), commit any leftover
    changes, excluding `_status.md`, before work begins. No changes, no
    commit. Skip it when another session holds `.wiki-lock`, so one session
    never commits another's work in progress. Expected rate: about one commit
    per sweep.
  - **Snapshot fill:** at session end, and in `lint.py --auto-fix` as a second
    chance, for each changed file in a page directory with no
    `_archive/<slug>-<today>.md`, write one from `git show HEAD:<path>`
    through `lint.py`'s `snapshot()`. Never overwrite a snapshot the hook
    already made. The checkpoint makes HEAD the state at session start, so
    the fill saves the right pre-image whatever the user's commit habit.
  - **Docs:** put the snapshot sentence next to both pieces of script advice
    (core `SKILL.md` and `citation-spec.md`), where an agent reads it at the
    moment it decides to script. Update I7's guarantee text,
    `hooks/README.md`, and the changelog.
- **Alternatives if checkpoint commits are unwanted:**
  - **Session-start copy:** `session-start.sh` copies the page directories
    (303 files, 2.3 MB in pm-wiki on 2026-10-02) to a per-session scratch
    folder. `session-stop.sh` snapshots every changed page from that copy and
    deletes it. The next session start processes a copy left by a session
    that ended without its stop hook. This needs no commits but more
    machinery.
  - **One write helper:** a `wikifm.write_page()` that calls `snapshot()`
    first, plus a pre-write warning when a Bash command writes into a page
    directory. This is cheaper, but it still depends on agent behavior and
    misses ad-hoc `open().write()` heredocs like the 2026-10-02 ones.
- **To decide:**
  - Whether unreviewed checkpoint commits are acceptable. They can be
    tidied or undone later.
  - Measure how often SessionEnd fires (a day of logging in the hook) before
    choosing between the checkpoint and the session-start copy.
- **Related:** I7 (design section 1), changelog PATCH-5 and Background
  ("Auto-commit"), NW5 (`$WIKI_PATH` default), NW11 (`AGENTS.md` not loaded
  in a wiki).
- **Found in:** a pm-wiki maintenance session on 2026-10-02 (the agent's own
  report), analyzed in an llm-wiki-pm session the same day.

**NW12. `_archive/` snapshots crowd live pages out of search.**
- **Status: done 2026-10-13.** Git checkpoint commits replaced pre-write
  snapshots in your fork (commit `0b93311`, changelog PATCH-19), with step 1
  included: `backlinks.py` no longer scans `_archive/`, and the query and
  update steps call `_archive/` hits retired pages. pm-wiki's 441 snapshots
  were removed in its commit `4d680a3`, and `overview.md` points at git for
  its pre-2026-10-06 text. The measured query then returned no `_archive/`
  hits, and the current page three times in the top 10. The text below
  describes the problem and the proposal as approved.
- **What happens:** pre-write snapshots live in `_archive/` inside the wiki
  folder, and three readers treat them as pages:
  - **The wiki-search MCP** indexes every `.md` file under the wiki
    (`listNotes()` skips nothing). A `semantic_search` on 2026-10-08 returned
    6 `_archive/` snapshots in its top 10, including the top hit. The live
    history page with the same text ranked third, and the current page wasn't
    in the 10.
  - **`grep -r "$WIKI"`,** which several skills use, reads `_archive/`.
  - **`backlinks.py`** scans `_archive/` on purpose. Snapshots were about 60%
    of the linking files for three busy pages.
  - **Obsidian** already hides `_archive/`.
  - **No skill** tells agents to skip `_archive/` hits, although
    `citation-spec.md` says `_archive/` is never a source.
- **Why it matters:** agents can quote stale, uncited snapshot text, and the
  current page can drop out of the results an agent reads. On 2026-10-13
  `_archive/` held 447 files: 441 snapshots, 5 superseded entity pages and
  NW7's M1 page. No `_archive/` file was ever changed after it was
  created, so the harm is to reading, not writing.
- **Options weighed:** a query rule alone (depends on agent behavior and can't
  undo the crowding), server-side exclusion (the `directory` filter is an
  include-only prefix applied after retrieval, so a real exclusion needs
  NW2's fork), moving snapshots outside the wiki folder (takes them out of the
  wiki's Claude project), combinations that keep snapshots, and dropping
  snapshots for git.
- **Snapshots in use:** never used for an undo (NW10). The one log entry
  calling them a backstop (2026-09-22) was restored from the agent's context;
  no snapshot of that page existed that day. 310 of the 441 are identical to a
  committed version of a live file, and git holds all 441 as `_archive/`
  files.
- **Proposal: drop snapshots, checkpoint into git** (merges NW10):
  1. **Now:** `backlinks.py` drops `_archive` (with NW7 step 1), and the
     query and update steps gain a rule: an `_archive/` hit is a retired page,
     not current.
  2. **`checkpoint()` replaces `snapshot()`** in `lint.py`: when the wiki has
     uncommitted changes (other than `_status.md`) and no merge or rebase is
     in progress, it commits them with a `checkpoint:` message, best-effort.
     `pre-write.sh` calls it before a session's first wiki write from any
     project, `session-start.sh` when a session starts in the wiki folder,
     and `--auto-fix` and `migrate_sources.py` before they write. No caller
     checks `.wiki-lock`, which every session in any project writes and
     clears. "Undo that" becomes a git restore the agent runs, and the
     by-hand snapshot rule for script edits goes.
  3. **Delete the 441 snapshots** in one pm-wiki commit, with the user's OK,
     and point `overview.md`'s "Pre-2026-10-06 text" at `7db03cd:overview.md`.
  It covers more than snapshots do (a second session the same day, and Bash
  or script writes after a session's first write or in a session started in
  pm-wiki), and fixes search without NW2. Not covered, as now: script-only
  writes from another project's session, and text written and then damaged in
  the same session.
- **Costs:** automatic commits in pm-wiki's history (at most one per writing
  session that starts with uncommitted changes, plus `--auto-fix` runs), which
  can include an overlapping session's half-done edits. Undo goes through
  git. About 40 code lines, about 60 test lines rewritten (temporary wikis
  need `git init`), about 14 doc edits including `AGENTS.md`, I7 and NW1's
  overview mitigation line. More divergence from upstream.
- **Alternative if automatic commits are unwanted:** keep snapshots in a
  `_snapshots/` folder inside pm-wiki that the server ignores, through an
  ignore list as NW2's first fix, plus a grep rule. That needs NW2's Node
  build, and leaves NW10's script gap open. Moving snapshots outside the wiki
  instead avoids NW2 but takes them out of the wiki's Claude project.
- **To decide:** automatic `checkpoint:` commits, deleting the 441 snapshots,
  and step 1 now.
- **Upstream:** upstream snapshots into `_archive/` too, with the same server.
  The search problem goes up as an issue with the measurements and this
  approach. Upstream would need an answer for wikis that aren't git repos.
- **Full analysis:** [Archive Snapshots in Search Brief](archive-snapshots-in-search-brief.md).
- **Related:** NW10 (merged into this item), NW7 (same-name `_archive/`
  copies, `backlinks.py`'s folder list), NW2 (the ignore list, only for the
  alternative), NW11 (`AGENTS.md` holds the snapshot rule), NW1 (its overview
  mitigation is a pre-write snapshot).
- **Found in:** an llm-wiki-pm session on 2026-10-08, from a wiki-search query
  in pm-wiki.

**NW13. `.wiki-lock` warns about every session, in any project.**
- **Status: done 2026-10-14.** Option 2 is in your fork (changelog PATCH-20):
  the lock and its warning are gone, and at a session's first wiki write
  `pre-write.sh` names other sessions that wrote to the wiki in the last 30
  minutes, from markers `post-validate.sh` keeps in the temp folder. pm-wiki's
  `.wiki-lock` and its two `.gitignore` lines were removed in a pm-wiki commit
  the same day. The text below describes the problem and the proposal as
  approved.
- **What happens:** the hooks run in every session in any project, with
  `$WIKI_PATH` pointing them at pm-wiki. `session-start.sh` writes
  `$WIKI/.wiki-lock` at every session start and warns "Another wiki session may
  be active" when it finds a lock under 2 hours old. `session-stop.sh` deletes
  the lock at the end of any session, whoever wrote it. The file holds only
  the latest session, a compaction warns a session about its own lock, and hand
  runs of the hooks write and clear it too.
- **Measured** in this machine's transcripts, 2026-08-06 to 2026-10-13: the
  warning fired at 50 of 152 hook runs. 16 of the warnings named a session
  that never touched pm-wiki, 11 an ID with no transcript (3 were tests'
  `test-session-123`), and 1 the session itself after a compaction. Only two
  pairs of sessions wrote to pm-wiki in overlapping windows (2026-08-07 and
  2026-09-01), and neither got a warning. Agents passed the warning on to you
  or ran extra checks before writing (2026-09-23, 09-28, 09-30).
- **Why it matters:** the warning is noise that agents act on, and nothing can
  rely on the lock, as NW10's planned checkpoint gate found. It never blocked a
  write. Two skills send agents to `_status.md` for lock state it never
  records, and the core skill says the lock "prevents concurrent-session
  corruption".
- **Proposal (option 2, chosen 2026-10-14): drop the lock and add a "recent
  writer" note.**
  - Remove the lock from both hooks and the scaffold's empty-folder rule, fix
    `hooks/README.md`, core `SKILL.md` (Pitfalls, Pre-Flight ⑤) and
    `llm-wiki-brief`, and then delete pm-wiki's `.wiki-lock` and its
    `.gitignore` lines in a pm-wiki commit. Claude Code's Write and Edit
    already refuse a file changed since it was read, and the checkpoint commit
    keeps another session's work recoverable.
  - `post-validate.sh` updates a per-session marker in the temp folder after
    each wiki write. At a session's first wiki write, `pre-write.sh` tells the
    agent when another session wrote to the wiki in the last 30 minutes. That
    note is the signal that overlaps are becoming common, which dropping the
    lock alone (option 1, the first recommendation) wouldn't give.
  - About 40 lines removed, about 25 added, and about 55 test lines in
    `tests/test_write_hooks.py`.
- **Not chosen:** an overlap count in the session-start summary (about 15 more
  lines; trends only matter once overlaps are common). Ruled out: a lock
  scoped to wiki sessions with owner-checked removal (one owner per file,
  still needs staleness), owner-checked removal alone (more warnings), and a
  staleness change alone.
- **Upstream:** same code. A user-scope plugin install gets the same noise,
  and with no wiki path configured the hooks write the lock into each
  project's folder. The change is for your fork: its fork changelog entry
  marks it an upstream candidate, to offer later if you choose.
- **Full analysis:** [Wiki Lock Brief](wiki-lock-brief.md).
- **Related:** NW12 and NW10 (the checkpoint doesn't read the lock), NW5
  (`$WIKI_PATH` as every project's default wiki).
- **Found in:** the NW12 work, an llm-wiki-pm session on 2026-10-13.

**NW8. The maintain skill files a weekly brief as a daily one.**
- **Status: folded into NW14 2026-10-22.** The cadence check is the
  "Cadence picks the brief" section of the
  [Sweep Window Design](sweep-window-design.md), to be implemented with NW14
  in its own commit.
- **What happens:** `llm-wiki-maintain` step ④ routes to `llm-wiki-brief`'s
  daily brief and files it as `briefings/YYYY-MM-DD.md`, whatever the sweep's
  cadence. Its triggers include "maintain the wiki" and scheduled runs that
  aren't daily, and `llm-wiki-brief` has its own weekly convention
  (`queries/weekly-brief-YYYY-MM-DD.md`, offered for filing), which maintain
  never routes to.
- **Seen:** a weekly sweep on 2026-08-28 filed weekly content at a daily path,
  left out of `index.md`, until it was moved by hand to the weekly path.
- **Since step 2 of the sources design:** maintain no longer rotates briefs into
  `_archive/briefings/`, so a misfiled weekly brief is no longer archived as a
  daily one. The misfiling itself remains. Dated briefs are exempt from lint's
  index check, so nothing reports it.
- **Proposal:** a cadence check at step ④ (ask when unclear in interactive mode,
  take it from the run's declared scope in autonomous mode), routing to the
  daily or weekly brief and its filing path.
- **Upstream:** filed from this fork as `anh-chu#12` (2026-08-29), open on
  2026-10-02. Its rotation part is already fixed here.
- **Found in:** pm-wiki, 2026-08-29.

**NW14. Registry sweeps have no rule for their time window.**
- **Status: done 2026-10-28.** Implemented in your fork (changelog PATCH-22),
  with NW8 (PATCH-21) and NW15's B, D and G (PATCH-23). pm-wiki's Sweep
  Registry got the Swept through column in a pm-wiki commit the same day. The
  text below describes the problem as found.
- **What happens:** no skill says what time range a registry sweep reads from
  each source. Agents chain each sweep from the previous sweep's dates in
  `log.md`: one window for all sources, day-granular, in free text that gets
  rotated. The completeness guard's "widen the window" can re-read old content,
  and `limit`≤15 has no paging rule, so a busy source can be cut short and still
  count as `hits`.
- **Seen:** on 2026-10-12 you limited the sweep to meetings. The next sweep
  started from 10/12 for every source, and the Confluence pages seen on 10/12
  were carried to 10/14 by hand.
- **Proposal:** a per-source Swept through timestamp in the Sweep Registry,
  advanced only for sources fully covered and ingested, with paging and a
  50-item ceiling. Full design in the
  [Sweep Window Design](sweep-window-design.md).
- **Related:** NW8 (folded in: cadence picks the brief), NW15 (revises the
  design's weekly brief path and brief windows before it is built), and a possible Slack capture skill using Claude in Chrome, which
  would need per-channel windows.
- **Found in:** an llm-wiki-pm session on 2026-10-22, asking how a Slack channel
  would be swept.
