---
title: My Integrations
updated: 'YYYY-MM-DD'
---

# My Integrations

Sources used in this wiki, auto-discovered from ingest activity. The Active Sources
table is auto-maintained by the skill after each ingest. The Routing Notes section
below is user-editable — add preferences there, not in the table.

## Sweep Registry

Canonical list of sources a full "ingest all sources" / daily-brief sweep MUST
cover. This — not the agent's memory — defines what "all sources" means; the
sweep iterates every row and reports state (`hits` / `empty-after-retries` /
`failed`) for each. Established/confirmed the first time a multi-source sweep
runs; edit freely to add or retire sources. A source missing here is a source
that will be silently skipped, so keep it complete. **Swept through** is an ISO
8601 local time with offset (e.g. `2026-10-22T09:40-07:00`): every item in that
source created or changed at or before it has been seen by a sweep and ingested
or set aside. The next sweep reads from there; blank means never swept by this
rule.

| Source | Sweep? | Swept through | How to query | Notes |
|--------|--------|---------------|--------------|-------|
<!-- e.g.: | Slack | yes | 2026-10-22T09:40-07:00 | search #product-strategy, to:me, <@mentions> | most active |
     e.g.: | GitHub | yes | 2026-10-22T09:40-07:00 | issues assigned/mentioning me, recent PRs | high signal |
     e.g.: | Gmail | yes | | PM/ label | | -->

## Active Sources

| Source | Type | Last used | Times ingested | Notes |
|--------|------|-----------|----------------|-------|
<!-- rows appended by skill on each ingest -->

## Routing Notes

Add any routing preferences here — the skill reads this file at Pre-Flight to
tailor ingest defaults (e.g., preferred Slack channel naming, Gmail label patterns).

```
# Example entries (fill in after first few ingests):
# slack_workspace: your-workspace.slack.com
# gmail_label_filter: PM/
# preferred_transcript_format: zoom | meet | otter
```
