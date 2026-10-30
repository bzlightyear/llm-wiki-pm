# Wiki Log

> Chronological record of all wiki actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`
> Actions: ingest, update, query, lint (auto-fix only), create, archive, delete
> Rotated when > 500 entries by the session-stop hook: entries older than 30 days
> move to `log-YYYY.md`, and the last 30 days (at most 250 entries) stay here.
