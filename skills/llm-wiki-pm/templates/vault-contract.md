---
schema_version: 1
generated_by: llm-wiki-pm
---

# Vault Contract

<!-- Copied by llm-wiki-pm when it scaffolds the wiki. The wiki-search MCP
     never overwrites this file, and connected agents read it for frontmatter
     and naming. SCHEMA.md stays the authoritative schema; keep this file in
     step with it. -->

## Frontmatter Schema

Authoritative schema: `SCHEMA.md` at the wiki root. Citation rules: the
llm-wiki-pm skill's `references/citation-spec.md`. Required on every page:

- `title`: string — page title
- `created`: date — written `'YYYY-MM-DD'`, single-quoted
- `updated`: date — written `'YYYY-MM-DD'`, single-quoted; bump on every edit
- `type`: enum — `entity` | `concept` | `comparison` | `query` | `summary` | `persona`
- `tags`: string[] — only tags from SCHEMA.md's Tag Taxonomy
- `sources`: string[] — wiki-relative paths of the page's sources: `raw/` records or wiki pages. Cite each non-obvious claim inline as `[source: <id>, <location>]`, where `<id>` is the source's file name without `.md`

Optional fields are listed in SCHEMA.md.

## Tag Conventions

- Only tags from SCHEMA.md's Tag Taxonomy. A new tag needs a SCHEMA.md update first
- Lowercase, hyphen-separated: `machine-learning`, `project-alpha`

## Search Hints

- Conceptual / fuzzy queries → `view.semantic_search`
- Exact phrases or regex patterns → `view.global_search`
- Reading a specific section → `view.read` with `heading` parameter
- Structure overview → `view.outline`
- YAML metadata → `view.frontmatter_get`
- Incoming links to a note → `view.backlinks`
- Reading multiple files at once → `view.bulk_read`

## Naming Conventions

- Files: lowercase, hyphens, no spaces. Page slugs and record IDs match `[a-z0-9][a-z0-9._-]*` and are unique across the wiki
- Pages: `entities/`, `concepts/`, `comparisons/`, `queries/`, `briefings/`
- Records: `raw/<folder>/<descriptor>-<YYYY-MM-DD>.md`, written once and never edited
- Prefixes and dated names as the skill sets them, e.g. `queries/crystallize-<topic>-<date>.md`, `queries/research-<topic>-<date>/research-<topic>-<date>.md`, `briefings/YYYY-MM-DD.md`

## Note Template

<!-- A starting point for a new page. Replace every {{placeholder}}, including
     the sources: entry, which lint reports until it names a real file. -->

```markdown
---
title: {{Title}}
created: '{{YYYY-MM-DD}}'
updated: '{{YYYY-MM-DD}}'
type: {{entity | concept | comparison | query | summary | persona}}
tags: [{{tag from SCHEMA.md}}]
sources:
  - raw/{{folder}}/{{record-id}}.md
---

# {{Title}}

{{Body. Cite each non-obvious claim: [source: {{record-id}}, {{location}}].}}

## Related

- [[{{page-slug}}]]
- [[{{page-slug}}]]
```
