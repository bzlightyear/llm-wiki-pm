---
name: llm-wiki-brief
description: Structured daily/weekly briefs, tag digests, and check-ins from the PM wiki. Richer output than core catch-me-up.
when_to_use: Use for "daily brief", "weekly brief", "weekly checkin", "what happened this week", "what's new", "[tag] digest", "summarize [tag] pages", "what changed in [topic]", "brief me on [tag]". Core llm-wiki-pm handles these as fallback if this skill is not installed.
allowed-tools: Read Grep Bash
---

# LLM Wiki Brief

Structured briefs, digests, and check-ins from the PM wiki. Richer, more structured output than the §10/§11 fallbacks in the core llm-wiki-pm skill.

For ingest, update, query, lint, and all other wiki operations — the core `llm-wiki-pm` skill handles those. This skill is brief-only.

## When This Skill Activates

- "daily brief", "what happened today", "what happened yesterday"
- "weekly brief", "weekly checkin", "what happened this week", "week in review", "catch me up on the week"
- "[tag] digest", "brief me on [tag]", "summarize [tag] pages", "what's new in [topic]", "what changed in [competitive/customer/strategy/etc]"
- "what's thin", "what needs more work", "coverage brief"

## Wiki Path Resolution

```bash
WIKI=$(cat .wiki-path 2>/dev/null | tr -d '[:space:]')
WIKI=${WIKI:-${CLAUDE_PLUGIN_OPTION_wiki_path:-${WIKI_PATH:-$(pwd)}}}
```

## Orient (lightweight)

This skill is read-only by default, apart from each daily or weekly brief's own `log.md` line. Before any brief:
1. Read `$WIKI/_status.md` if it exists — surface any pre-computed warnings immediately
2. Read last 20-30 lines of `$WIKI/log.md` — know what's recent before summarizing

Full orient (AGENTS.md 4-step protocol) only required if filing output as a wiki page.

## Source-Completeness Guard (when briefs sweep live sources)

When a brief is asked to pull from external sources (whatever the user's connected stack — issue trackers, mail, chat, CRM, meeting notes, web), the core llm-wiki-pm **Source-completeness guard** applies in full: an empty or errored source is a signal to vary the query, not to declare the sweep done.

**A brief is exec-facing synthesis — the Provenance-tier & falsification guard applies (core skill → Session Defaults).** A brief reads as a complete, current picture, so a laundered claim does the most damage here. Tier every headline claim computed/primary/recalled; don't state a claim recalled from wiki prose as current fact without confirming it against a live source (a wiki page saying "pipeline is thin" does not override what the CRM says today). For any decision-bearing line, name and run the query that would disprove it before it goes in the brief, and mark claims you couldn't verify as unverified rather than asserting them.

- **Get the source set from the registry, not from memory.** Before sweeping, read the `## Sweep Registry` in `$WIKI/MY-INTEGRATIONS.md` and cover every source listed; the ledger below must have one row per registered source. If no registry exists, build the set from connected tools + the `Active Sources` table, confirm it with the user, and write it to the registry. Forgetting a registered source (e.g. omitting Slack or GitHub from the sweep) is the worst failure — it reads as complete while a high-signal source went unread.
- Read each source's window from its **Swept through** timestamp, as `llm-wiki-maintain` step ② does. A brief that sweeps but doesn't ingest never advances a timestamp.
- Run ≥2 varied queries per source before calling it empty (broaden terms, try aliases/handles/scope variants, switch syntax), inside the source's window. Keyword search tools commonly miss on first phrasing.
- Classify each requested source as `hits` / `empty-after-retries` / `failed`. Never collapse `failed` or `empty-after-retries` into "covered."
- **Always emit a Source Coverage ledger** (see below) listing every requested source and its state. A source that returned nothing must appear in the brief, not vanish from it. No "enough captured" while a requested source is `failed` or was abandoned after one query.

```markdown
### Source Coverage
- <source A>: hits (N items), 2026-10-21T09:40 → 2026-10-22T08:15
- <source B>: hits (partial, through 2026-10-22T07:30), 2026-10-21T09:40 → 2026-10-22T08:15
- <source C>: empty-after-retries, 2026-10-21T09:40 → 2026-10-22T08:15 — tried "X", "<scoped query> Y", "<author filter> Z"; quiet or query miss. Confirm scope/range?
- <source D>: failed — not connected; Swept through stays 2026-10-21T09:40
```

---

## Daily and Weekly Briefs

**Windows.** A brief's window is the stretch of `log.md` it reports on, by when material was ingested, separate from the sources' sweep windows.
- **Daily:** from where the latest brief's window ended, daily or weekly, to now. A daily brief after a three-day gap covers three days, with or without a sweep.
- **Weekly:** from where the latest weekly brief's window ended to now. A two-week gap gives one weekly brief covering two weeks, and a meeting whose notes arrive late is in the next weekly brief.
- **The previous end** comes from that brief's log line (below). Where no brief of the kind needed has that line yet, an interactive run asks where to start, and an autonomous run starts 7 days back and says so in the brief.
- A weekly brief counts as a brief, so the next daily brief starts where it ended.
- Inside a brief, order and group items by when they happened: a meeting's date from its crystallize page or its raw record.

**What each brief holds.** A daily brief lists what came in and needs attention now; a weekly brief says what changed over its period and where things stand. It summarizes what the dailies already itemized rather than repeating them.

| | Daily | Weekly |
|---|---|---|
| Headline | The few things that matter from this material | The period in one paragraph: themes and direction |
| Meetings | Each new meeting: what happened, decisions, who's waiting on what | Grouped by topic, linking each crystallize page and saying what it changed |
| Decisions | Each one as it was made | Those in the period, grouped, noting any that reversed or replaced an earlier one |
| Open questions | New ones raised | Added vs resolved in the period, and which older ones are still open |
| Needs Review | This run's queue, plus unresolved items carried from the previous brief | Everything still unresolved, with how long each has been open |
| You owe | From `overview.md`'s "Pete owes" (until NW1) | The same, with what closed and what was added in the period |
| Customers and people | When a meeting involves them | "Customers to watch": accounts with several signals in the period |
| Wiki health | This run's lint warnings | Staleness flags, stubs created in the period, activity by tag |
| Source Coverage | This run's sweep, one row per source | This run's sweep, if it swept |

**Needs Review carry-forward.** Every brief starts from the Needs Review section of the latest brief, daily or weekly. Check each item against the wiki and `log.md`: if it was settled, list it once as resolved, saying where it went (the page or log entry); if not, carry it forward with the date it was first raised. A brief with carried or new items has a Needs Review section, in interactive and autonomous runs alike. Only Needs Review is carried; "You owe" comes from where the table says.

**Log line.** Every daily and weekly brief gets its own `log.md` entry, filed or not, including one written inside a maintenance run:

```
## [YYYY-MM-DD] brief | daily|weekly | <from> → <to> | filed: <path or no>
```

`<from>` and `<to>` use the Sweep Registry's Swept through format, for example `2026-10-26T00:00-07:00 → 2026-10-28T09:40-07:00`.

---

## Operations

### 1. Daily Brief

**Triggers:** "daily brief", "what happened today", "what happened yesterday"

① Resolve `$WIKI`. Read `$WIKI/_status.md` if present.

② Read `$WIKI/log.md` across the daily window (Daily and Weekly Briefs above). Parse:
   - Pages created (`ingest`, `create`)
   - Pages updated (`update`)
   - Decisions logged (`decision`)
   - Open questions added (`query`, `question`)

   Read the latest brief's Needs Review and mark each item resolved or carried forward (Needs Review carry-forward above).

③ For decision and question entries, read the referenced page to pull the one-line summary or question text. For each meeting in the window, read its crystallize page, or its raw record if it has none.

④ Output: the Daily column of "What each brief holds", under `## Daily Brief — YYYY-MM-DD`. Structured, scannable, no prose padding.

If the window has no entries, say so.

**Log:** the brief's log line (Daily and Weekly Briefs above).

**If you file the brief as a page** (e.g. `briefings/YYYY-MM-DD.md`), stamp
`lifecycle: dated-digest` in its frontmatter. These are orphans by design;
the flag keeps them out of the lint orphan count (see schema-guide). Without
it, every daily brief permanently inflates the orphan metric. Don't add the
brief to `index.md`: lint skips briefs in its index check, and the index holds
one fixed line pointing to `briefings/`. Don't edit a filed brief after the
day it was filed: a later correction goes on the page that owns the fact and
into the next brief's carry-forward, while same-day corrections are fine.

---

### 2. Weekly Brief / Check-in

**Triggers:** "weekly brief", "weekly checkin", "what happened this week", "week in review", "what did I miss"

① Resolve `$WIKI`. Read `$WIKI/_status.md` if present.

② Read `$WIKI/log.md` across the weekly window (Daily and Weekly Briefs above; the user can name another period). Read the daily briefs in the window when there are any; otherwise work from the crystallize pages, `log.md` and this run's sweep. Read raw records only for a meeting with no crystallize page. Read the latest brief's Needs Review and mark each item resolved or carried forward (Needs Review carry-forward above).

③ Aggregate counts: pages created, updated, decisions logged, questions added vs resolved.

④ Identify top 3 areas of activity: grep mentioned slugs' frontmatter tags, count by tag frequency.

⑤ Lightweight staleness check on `overview.md` and `index.md`: if `updated:` older than 14 days AND log shows writes in the period, surface warning.

⑥ Coverage gaps: grep for `coverage: stub` pages created in the period only — not all stubs, just new ones.

⑦ Output: the Weekly column of "What each brief holds", under `## Weekly Brief: YYYY-MM-DD to YYYY-MM-DD` (its period).

⑧ Offer to file as `briefings/weekly-brief-YYYY-MM-DD.md`, dated by the run, with `lifecycle: dated-digest`. If yes, run full orient per AGENTS.md before writing.

**Run from `llm-wiki-maintain`:** add the Source Coverage ledger for the run's sweep, and put the run's queued items in Needs Review. Maintain files the brief at its weekly path, so skip the offer in ⑧.

**Log:** the brief's log line (Daily and Weekly Briefs above).

---

### 3. Tag Digest

**Triggers:** "[tag] digest", "brief me on [tag]", "summarize [tag] pages", "what's new in [tag]"

① Resolve `$WIKI`. Check tag exists in `$WIKI/SCHEMA.md` taxonomy. If not: "Tag '[x]' not in taxonomy. Did you mean: [closest matches]?"

② Grep for matching pages:
   ```bash
   grep -rl "tags:.*\b<tag>\b" $WIKI/entities $WIKI/concepts $WIKI/comparisons --include="*.md"
   ```

③ Sort by `updated:` desc. Read each page: title, type, updated, coverage, confidence, 2-3 sentence summary.

④ Cross-reference with log.md: grep each slug in last 30 days. Note recent activity.

⑤ Identify themes: recurring entities/concepts, what changed recently, open questions (question-tagged pages with matching tag), patterns, gaps.

⑥ Output format:

```markdown
## [Tag] Digest — YYYY-MM-DD
N pages tagged [tag]

### Key Themes
- [Theme]: [2-3 sentence synthesis]
  Sources: [[page-a]], [[page-b]]

### Recently Updated (last 14 days)
- [[slug]] (YYYY-MM-DD): what changed

### Open Questions
- [[query-slug]]: question text

### Notable Patterns
- [Pattern observed across pages]

### Coverage Notes
- [[slug]]: stub — gaps: X, Y
```

⑦ Offer to file as `queries/[tag]-digest-YYYY-MM-DD.md`. If yes, full orient before writing.

**Log:** `## [YYYY-MM-DD] digest | tag: <tag> | N pages | filed: yes/no` — only if filing.

---

### 4. Coverage Brief

**Triggers:** "what's thin", "what needs more work", "coverage brief"

① Scan `coverage:` frontmatter across `entities/`, `concepts/`, `comparisons/`. Count: stub, partial, comprehensive, missing.

② For stub/partial pages, collect `tags:` and `gaps:`. Group by primary tag.

③ Output format:

```markdown
## Coverage Brief — YYYY-MM-DD

### Summary
- Stub: N | Partial: N | Comprehensive: N | No marker: N

### Stubs by Domain
**[competitive]** — N stubs
- [[slug-a]], [[slug-b]]
- Top gaps: X, Y

**[customer]** — N stubs
- [[slug-c]]

### Partial Pages with Notable Gaps
- [[slug]]: gaps: [list]

### Recommended Next Actions
- [[slug]]: highest-priority — appears in N cross-references
```

④ Offer: "For full audit with orphan detection and taxonomy analysis, run Coverage Audit (§12) from llm-wiki-pm."

**No log entry** — pure read operation.

---

## Boundaries

This skill handles: daily brief, weekly brief, tag digest, coverage brief.

For everything else — ingest, update, query, lint, archive, persona, pre-meeting briefing — the core `llm-wiki-pm` skill handles those.

> "For full ingest/update/query operations, the core llm-wiki-pm skill handles those."

## Behavioral Constraints (per AGENTS.md)

- **No writes without orient.** Filing a brief requires full orient + SCHEMA.md compliance.
- **No schema drift.** Filed query pages use taxonomy tags only.
- **No orphan pages.** Filed briefs need min 2 outbound `[[wikilinks]]`.
- **Privacy.** Pages are private by default (only `shareable: true` pages are export-safe). For any non-shareable page, surface topic category only, not content.
- **Human tone.** Scannable over verbose. No em-dashes. No AI tells.
