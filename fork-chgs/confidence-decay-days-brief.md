# Confidence Decay Days Brief

created: 2026-09-30

Two gaps in the plugin's tooling, found on 2026-08-10 while using the PM wiki:
lint ignores the `confidence_decay_days` field, and it skips any page whose name
starts with `lint-`. Each is given as found and as checked against the fork on
2026-09-30.

Status: open, no fix proposed.

## Origin

- The findings were filed in the PM wiki on 2026-08-10 as a query page,
  `queries/confidence-decay-days-not-enforced.md`, while questions about the
  plugin were being asked from the wiki's project. The page documented the
  plugin rather than PM knowledge, and it cited the installed plugin's
  `lint.py` by an absolute path, which the citation spec's R6 rejects.
- On 2026-09-30, during step 10b of the
  [Sources and References Design](sources-and-references-design.md), the page
  was deleted from the wiki and its content moved here, as the
  [llm-wiki-pm Fork Changelog](llm-wiki-pm-fork-changelog.md) was on 2026-08-30.
- The wiki page it was written for is a concept page listing the customers that
  have a feature enabled. It sets `confidence_decay_days: 7`, because even a
  week's drift could make the list wrong. Its staleness note said lint doesn't
  enforce the field and linked to the query page. It now says session start
  flags the page instead.

## Finding 1: lint doesn't read `confidence_decay_days`

**As found (upstream 2.21.0).** SCHEMA documents the field: "Warn if
`updated:` is older than N days." But `lint.py` has only two fixed staleness
thresholds, `updated:` older than 90 days and `last_verified:` older than 120
days (`LAST_VERIFIED_STALE_DAYS`), and the field's name doesn't occur in the
script.

**Correction.** The field was already enforced, only not by lint. Since
upstream v2.20.0 (PLUGIN-REVIEW-2026-07-15 item A10), `session-start.sh` reads
it. A page under `entities/`, `concepts/` or `comparisons/` whose `updated:` is
older than its `confidence_decay_days`, or a `competitive`-tagged page older
than 60 days when the field isn't set, is listed under "Confidence Decay
Candidates" in `_status.md` and counted in the session-start health line. The
page that led to the finding is under `concepts/`, so it was covered all along.

**Still true in the fork:**

- `lint.py` doesn't read the field, so neither lint's report nor the maintain
  loop's health check ever shows a decayed page.
- Session start doesn't scan `queries/` or `briefings/`, so the field does
  nothing on a page there.
- The SCHEMA template's Confidence Decay section still says the orient step
  "greps for competitive-tagged pages", which describes the check before
  v2.20.0.

**Open questions (from the wiki page):**

- Does the field replace lint's flat 90-day threshold for that page, or add an
  earlier warning?
- Should lint report it, and at which tier, or is session start enough?
- Once decided, re-run lint across the wiki to check that no page with the field
  starts warning unexpectedly.

## Finding 2: any page named `lint-*` is skipped

**As found.** Lint skips every file whose name starts with `lint-`, to leave
its own reports (`queries/lint-YYYY-MM-DD.md`) out of the scan. The test is too
broad. The query page was first filed as
`queries/lint-py-confidence-decay-days-gap.md`, so lint left it out of the page
set and reported a link to it as broken. Renaming the page worked around it.

**Still true in the fork,** in four places:

- `lint.py`, in `wiki_pages()`, which is lint's page set and is also used by
  `migrate_sources.py` and `capture.py`;
- `lint.py`, in the grounding check;
- `backlinks.py`, in its page scan;
- `hooks/pre-write.sh`, in the check that decides which pages the freshness
  gate applies to.

**Proposed fix (from the wiki page):** match the report's exact name,
`lint-YYYY-MM-DD.md`, instead of the prefix.
