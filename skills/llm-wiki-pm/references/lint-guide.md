# Lint Guide

Lint runs programmatically via `scripts/lint.py` and writes a tiered report to
`wiki/queries/lint-YYYY-MM-DD.md`. Run every 5-10 ingests, or monthly.

## Severity Tiers

### 🔴 Errors, fix before next session

- **Broken `[[wikilinks]]`**: target page doesn't exist. Either create the
  target, fix the link, or remove it.
- **Missing frontmatter fields**: required: title, created, updated, type,
  tags, sources. Non-negotiable. So are a missing frontmatter block, a list
  item on its key's line (R1), list items under a closed `[...]` list (R2)
  and a key written twice (R5).
- **Tags not in SCHEMA.md taxonomy**: add to taxonomy first, or change the
  tag. No exceptions.
- **Duplicate IDs** (R9): two records with the same ID, a record ID that is
  also a page slug, or two pages with the same slug. A citation or link can't
  tell them apart. Rename one and update what cites or links to it.

These block the wiki's search/navigation/discipline. Fix immediately.

### 🟡 Warnings, triage with user

- **Orphan pages**: zero inbound links. Either add backlinks from related
  pages, or archive if truly standalone. Borderline pages may just need
  cross-references.
- **Pages not in index.md**: index is the catalog. Add it or archive the page.
  Dated digests (`lifecycle: dated-digest`) are exempt and stay out of it.
- **Pages > 200 lines**: split candidate. Break into sub-topics with cross-
  links. Big pages hide content. Follow the split procedure in
  `citation-spec.md` and set each page's sources with `lint.py
  --cited-sources`.
- **Stale pages**: `updated:` > 90 days ago with no correlated log activity.
  May be stable facts or genuinely neglected. Review with user. Dated digests
  are exempt: they describe the wiki as of their date.
- **Unresolved contradictions**: flagged in frontmatter but never closed.
  Revisit with latest info.
- **Sources and citations that don't resolve** (R3, R4, R6, R7) and
  **frontmatter outside the profile** (R12): see
  [Sources and citations](#sources-and-citations) below.
- **Default vault contract** (R11): `meta/contract.md` is still the
  wiki-search MCP's default, which describes another schema (a `status` field,
  no `sources`). Agents using the MCP read it. Edit it to follow SCHEMA.md and
  `citation-spec.md`.

Discuss trends, not just individual items. If 30% of pages are stale, the
wiki isn't being maintained actively enough.

### 🟠 Stale (STALE), review before next session

- **Stale overview/index**: `updated:` > 14 days ago AND log.md contains entries
  in the same window. The synthesis is behind known activity. Update it now.
- **Stale entity/concept/comparison**: `updated:` > 30 days ago AND log.md shows
  ingests or updates touching the same entity or topic in that period. The page is
  likely outdated, not just dormant.

For each flagged page: read the relevant log entries, identify what changed, then
run the Update flow. Don't mass-update blindly. Prioritize by log frequency.

Staleness with no log correlation = 🟡 Warning (might be fine).
Staleness with log correlation = 🟠 STALE (act on it).
### 🔵 Info, quarterly review

- **Tag usage frequency**: top tags dominate the domain. Rarely-used tags
  may be candidates for consolidation or removal.
- **Singleton tags** (used once), usually typos or impulsive additions.
  Consolidate into existing tags or justify and keep.
- **Log size**: rotate at 500 entries.
- **Secondhand, unverified** (R10): every primary source of the page is a
  conversation record (or one rebuilt from the log). Session-start lists
  these in `_status.md`. The page leaves the list once a record of a real
  source (the document, thread or dashboard behind the statement) is
  declared on it. No date clears it.

Not urgent. Save for quarterly taxonomy review.

## Sources and citations

The rules come from `references/citation-spec.md`: `sources:` declares the
paths of records and pages, `[source: <id>, <location>]` cites an ID, and an
ID is the slug of the file it names.

| Rule | Finds | Tier | Fix |
|---|---|---|---|
| R3 | A citation whose ID is the slug of no `sources:` entry on the same page | 🟡 | Declare the path the message names; for a statement with no record, capture one (`capture.py`) |
| R4 | A page with 5+ sources that cites fewer than half of them | 🟡 | Trim `sources:` to what the page cites or is built from |
| R6 | A `sources:` entry that isn't the path of an existing record or page (a bare name, a root file like SCHEMA.md, an asset, a missing file) | 🟡 | Declare `raw/<folder>/<id>.md` or the page's path; capture a record for anything else |
| R7 | A marker outside the grammar: wrapped over lines, a nested `source:`, "a vs. b", a path, a URL, a wikilink, or text that isn't an ID | 🟡 | `--auto-fix=content` repairs the first four when every ID in the marker names exactly one file; the rest by hand |
| R12 | Frontmatter outside the profile: value shapes, key names, dates that aren't `YYYY-MM-DD` | 🟡 | By hand; `--auto-fix=content` rewrites midnight timestamps. Missing frontmatter or required keys are 🔴 |

A citation that breaks the grammar but names a declared source is only R7. One
that names nothing declared, such as `[source: user, conversation, <date>]`,
is R3, and R7 too if it also breaks the grammar.

## Response Workflow

After lint:

1. Open the generated report at `wiki/queries/lint-YYYY-MM-DD.md`
2. Fix all 🔴 errors in one pass. Re-run lint to confirm.
3. Scan 🟡 warnings. Flag 3-5 for user discussion. Batch similar fixes.
3a. Review 🟠 STALE pages. For each, cross-check against log.md to confirm the
    page is actually behind, then run Update flow in priority order.
4. Note 🔵 info. Check back next quarter.
5. Update `overview.md` if the lint revealed drift in the synthesis.
## Auto-Fix Mode

```bash
python3 scripts/lint.py $WIKI --auto-fix
```

Safe repairs applied automatically:

- **Supersession link redirect**: rewrite `[[old-slug]]` → `[[new-slug]]` on
  every page where the old page has `superseded_by: new-slug` set
- **Broken link redirect**: if a broken link target has a supersession
  mapping, rewrite to the new target instead of erroring
- **Index backfill**: append missing non-superseded pages to `index.md`
  under the correct type section

Before changing a page, lint copies it to `_archive/<slug>-<YYYY-MM-DD>.md`
(at most once per page per day), as the pre-write hook does.

```bash
python3 scripts/lint.py $WIKI --auto-fix=content
```

Runs the safe repairs, then two that change page content:

- **Citation markers** (R7): joins a wrapped marker onto one line, drops a
  nested `source:`, turns "a vs. b" into "a; b" and a path into its ID, in
  markers whose IDs each name exactly one record or page.
- **Timestamp dates** (R12): rewrites a `created`, `updated` or
  `last_verified` timestamp at midnight, like `2026-09-03T00:00:00.000Z`, as
  `'2026-09-03'`.

Run it only when the user asks, after reading the R7 and R12 findings it
would repair. Unattended runs (scheduled, autonomous) never pass `=content`;
they use plain `--auto-fix`.

NOT auto-fixed (requires human judgement):
- Missing frontmatter fields
- Tags not in taxonomy (typo vs new tag)
- Orphan pages (need backlinks or archival)
- Stale pages (fine vs out of date)
- Unresolved contradictions
- Sources and citations that don't resolve (R3, R6)

Always re-run without `--auto-fix` after to confirm cleanup. Lint reports
themselves (`queries/lint-*.md`) are excluded from scans.

## Other flags

- `--cited-sources <page>`: prints the `sources:` a page needs, the path of
  each ID it cites resolved against every record and page, and lists IDs that
  resolve to nothing. Writes nothing. The split procedure uses it.
- `--json`: prints counts and lists (broken links, orphans, index gaps,
  missing fields, secondhand pages, and pages breaking the frontmatter, source
  and citation rules) and writes nothing. Session-start and
  `worker-link-validator` read it.

## Interpreting Trends

Run-over-run patterns matter more than single reports.

- **Orphans climbing**: ingest flow skipping backlink audit.
- **Broken links climbing**: pages being deleted/renamed without sweep.
- **Stale count climbing**: update discipline slipping, or domain expanding
  faster than curation.
- **Tag count sprawling**: taxonomy enforcement slipping.

Treat lint as the wiki's health dashboard, not a one-off cleanup.

## What lint doesn't catch

- Factual errors (requires domain knowledge)
- Missed cross-references (requires semantic understanding)
- Coverage gaps (what SHOULD exist but doesn't)
- Redundant pages on the same entity with different slugs

For these, periodic human review is required. Budget 30 min/quarter.
