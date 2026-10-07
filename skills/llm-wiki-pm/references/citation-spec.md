# Citation Spec — sources, records and citations

The one definition of how a page names its sources: `raw/` records, page slugs,
frontmatter `sources:`, inline `[source: …]` citations, and the frontmatter
profile they sit in. AGENTS.md, SCHEMA.md, the guides and the sub-skills point
here. Read it before capturing a fact stated in conversation, splitting a page,
or writing a script that edits frontmatter.

Every claim follows one chain: the claim carries `[source: <id>, <location>]`;
`<id>` is the slug of exactly one entry in the page's `sources:`; that entry is
the path of a file that exists. Frontmatter **declares** paths, markers **cite**
IDs, and matching is exact.

## Records (`raw/`)

- A **record** is a `.md` file under `raw/`, outside `raw/assets/`. Binary
  originals (PDF, slides) live in `raw/assets/`, and the record points at its
  original with `asset:`. Never declare or cite a file in `raw/assets/`.
- A record's **ID** is its filename stem: lowercase letters, digits, `.`, `_`
  and `-`, starting with a letter or digit. It is unique across `raw/` and
  differs from every page slug.
- Name records `<descriptor>-<YYYY-MM-DD>` (`-<YYYY>` for an undated
  publication), in the folder `ingest-guide.md` ① routes the source to.
- **Write-once.** A record is complete when written and is never edited. If a
  saved record is itself wrong (a capture error), save a new record, say in its
  body which record it replaces, and run Update (SKILL.md §4) on the pages that
  cite the old one. A change in the world, or a later statement that differs
  from an earlier one, is not a correction: the old record is still an accurate
  capture, and the pages are revised through Update as usual.
- Record frontmatter is optional. Recommended, plus the source-specific fields
  `ingest-guide.md` ① lists:

```yaml
---
title: "Pricing page, competitor-x"
source_type: web            # web | pdf | transcript | chat | email | warehouse | conversation | internal | other
captured: '2026-01-15'
source_url: https://example.com/pricing      # web
stated_by: user                              # conversation: user | <person-slug>
asset: raw/assets/example-deck-2026-01.pdf   # optional binary original
---
```

  No `private:` field: the page allowlist governs export (`privacy-guide.md`).

## Page slugs

- A page's **slug** is its filename stem, the name Obsidian and the
  wiki-search MCP match links by. A directory page is named after its folder,
  `queries/<slug>/<slug>.md`, never `README.md`. Same grammar as record IDs,
  and unique across `entities/`, `concepts/`, `comparisons/`, `queries/` and
  `briefings/`. A page is linked as `[[<slug>]]`, declared by its path, cited as
  `[source: <slug>, …]`, and snapshotted as `_archive/<slug>-<date>.md`.
- **Other files in a directory page.** Another `.md` file in `queries/<slug>/`
  is either a real page (full frontmatter and a slug unique across the wiki,
  like a research sprint's part pages) or an artifact under the folder's
  `assets/` subfolder, which lint and the hooks skip (a Marp deck, a
  one-pager). Non-markdown artifacts (`.png`, `.csv`, `.py`, `.pdf`) may sit
  beside the page.
- A page may be a source (a crystallize digest, the entity page a persona
  builds on). It is a **secondary** source; a record is a **primary** one.
- **Not sources:** root files (`log.md`, `index.md`, `overview.md`,
  `SCHEMA.md`, `MY-INTEGRATIONS.md`, `_status.md` and any other), anything in
  `_archive/`, absolute paths, and anything outside the wiki. A fact kept in
  SCHEMA.md (the owner's role, org notes) is cited through a record of the
  user's statement (Conversational facts, below).

## Declarations: `sources:`

A list of paths to existing files: `raw/<folder>/<id>.md` for a record,
`<page-dir>/<slug>.md` or `queries/<slug>/<slug>.md` for a page. List what the
body cites and what the page is genuinely built from. Flow and block style both
work; templates use block style, which is what the wiki-search MCP writes.

```yaml
# valid
sources:
  - raw/articles/competitor-x-pricing-2026-01-15.md
  - raw/internal/conversation-2026-01-15-pricing-tier.md
  - queries/crystallize-pricing-review-2026-01-10.md

# invalid
sources: [conversation, 2026-01-15]              # not a path
sources: ["user, conversation, 2026-01-15"]      # not a path
sources: [competitor-x-pricing-2026-01-15]       # a bare ID: declare the path
sources: [raw/papers/competitor-x-pricing.md]    # no such file
sources: [SCHEMA.md]                             # not a source
sources: [raw/assets/deck-2026-01.pdf]           # declare the record, not the asset
```

**Grounding.** A factual page (entity, concept, comparison, persona) needs at
least one primary source (SCHEMA.md → Grounding). A dated digest
(`lifecycle: dated-digest`) summarizes the wiki and needs none: declare
`sources: []` rather than listing root files.

## Inline citations

```
marker   = "[source: " cite *( "; " cite ) "]"      ; on one line
cite     = id [ ", " location ]
id       = the slug of an entry in this page's sources:
location = text without "[", "]", ";" or a line break
```

The location is a page number, section name, timestamp, or `query <ref>`.
Keep each marker on one line, even when wrapping prose.

```markdown
Valid
Competitor X lists three tiers [source: competitor-x-pricing-2026-01-15, "Plans"].
The team chose usage-based billing [source: conversation-2026-01-15-pricing-tier].
ARR was flat [source: metric-arr-202601, query saved-query-123].
Two sources agree [source: vendor-y-docs-2026, "Hooks"; competitor-x-docs-2026, "Hooks"].
Per the digest [source: crystallize-pricing-review-2026-01-10, Decisions].

Invalid
[source: user, conversation, 2026-01-15]                    no record: capture one
[source: raw/articles/competitor-x-pricing-2026-01-15.md]   a path: cite the ID
[source: source: competitor-x-pricing-2026-01-15]           nested prefix
[source: vendor-y-docs-2026 vs. competitor-x-docs-2026]     join cites with "; "
[source: [[crystallize-pricing-review-2026-01-10]]]         a wikilink: cite the slug
[source: https://example.com/pricing, 2026-01-15]           a URL: capture the page as a record
[source: SCHEMA.md org chart]                               not a source: cite a record
```

To resolve a marker, split it on `"; "`, take each cite's text before the first
`", "` as its ID, and find the one `sources:` entry whose slug equals it. Only
the page's own `sources:` count, so declare everything the page cites. Never
coin an ID for a record that doesn't exist.

"Per [[page]]" in prose is a link, not a citation, and needs no declaration.

A `## Sources` section is optional free prose. It declares nothing, and lint
doesn't read it.

## Conversational facts

**A fact with no artifact gets a record before it gets a citation.** This holds
for micro-capture, Update, Learn and CRM alike.

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/capture.py" "$WIKI" --topic pricing-tier <<'EOF'
<the statement, near-verbatim>
EOF
```

- It writes `raw/internal/conversation-<YYYY-MM-DD>-<topic>.md` with
  `source_type: conversation`, `captured` and `stated_by`, and prints the path
  to declare and the ID to cite. When the ID is taken it adds `-2`, `-3`, …;
  it never overwrites.
- `--stated-by` is `user` (the default) or the slug of the person who said it.
- One record per topic per conversation. A later statement on the same topic
  gets a new record, never an append.
- Apply the privacy filter (`privacy-guide.md`) to the statement first.
- Facts a tool retrieved (a chat thread or email read through an MCP) aren't
  conversation records: capture them by their own route (`ingest-guide.md` ①).

## Non-file sources

- **Web:** capture the page as a record (`worker-source-fetcher`, or
  `ingest-guide.md` ①), declare it and cite its ID. A URL is never an ID.
- **Warehouse:** the snapshot record `raw/internal/<metric>-<snapshot>.md` is
  the source, and the query is the location:
  `[source: metric-arr-202601, query saved-query-123]`.
- **Email, chat, transcripts, PDF:** the routes in `ingest-guide.md` ①; the ID
  is the record's stem.
- **A live read you didn't capture** is not citable. Capture a record of what
  you read, or leave the claim uncited and add it to `gaps:`.

## Page lifecycle

- **Create:** slug and frontmatter as above, at least 2 outbound wikilinks, and
  `sources:` limited to what the body cites or the page is built from.
- **Split** (a page over 200 lines, entity promotion, a history split):
  1. Snapshot the parent (automatic for Write/Edit and MCP `vault` writes; by
     hand before a script edits it).
  2. In each child and in what stays in the parent, turn every source named
     in prose ("Source: raw/…", a meeting and its date, a link to a digest)
     into a marker on the claims it backs, after checking the record says
     so. `--cited-sources` reads only markers, so a source named in prose
     would drop out of `sources:`. A claim no record backs stays uncited
     and goes into `gaps:`.
  3. Set each child's `sources:` to the paths
     `python3 "${CLAUDE_SKILL_DIR}/scripts/lint.py" "$WIKI" --cited-sources <child>`
     prints. It resolves every ID the child cites against all records and
     pages, lists IDs that resolve to nothing, and writes nothing.
  4. Run it on the parent too, and trim the parent's `sources:` to what it
     still cites.
  5. Link parent and children to each other.
  6. Rewrite `[[parent#heading]]` and `#heading` links whose section moved
     to a child.
- **Supersede:** fields and archive as in `update-guide.md`. The new page's
  `sources:` is what it cites, never a copy of the old page's list. Text
  carried over from the old page gets markers first, as in step 2 of Split.
- **Archive:** `_archive/` is immutable, never a source, and exempt from these
  rules.

## Frontmatter profile

The subset of YAML a page may use. `scripts/wikifm.py` reads and writes it, and
lint and the hooks read every page through it.

- `key: value` lines; keys are lowercase letters, digits and `_`, each once.
- A value is a plain or quoted string, or a flow list `[a, 'b, c']` on one
  line. Under an empty `key:` comes a block list of indented `- item` lines; an
  item may continue on more-indented lines, or start with `>-`. The persona keys
  (`language_patterns`, `tone_by_channel`, `vocabulary_markers`) may instead
  hold one level of indented `subkey: value` lines.
- Comments and blank lines are ignored. Tabs only inside quotes, comments and
  `>-` text.
- **Every value is a string.** `created`, `updated` and `last_verified` are
  `YYYY-MM-DD` dates.
- **Write dates single-quoted, `'YYYY-MM-DD'`.** The wiki-search MCP and PyYAML
  keep that form, but turn an unquoted date into a timestamp or a date object.
- Required keys: `title`, `created`, `updated`, `type`, `tags`, `sources`
  (SCHEMA.md lists the optional ones).

**Editing frontmatter.** Use the Edit tool, or in a script `wikifm.set_field`
and `wikifm.set_list`, which change one field and leave every other byte as it
was. Never load and re-dump frontmatter with a YAML library.

```python
sys.path.insert(0, "<skill-dir>/scripts"); import wikifm
text = wikifm.set_list(text, "sources", paths)
text = wikifm.set_field(text, "updated", "2026-01-15")
```

Don't use the wiki-search MCP's `edit` tool (the README's install notes deny
it): `frontmatter_set` and its `append`, `prepend`, `replace` and `delete`
operations rewrite the whole page, escaping `[` and turning dates into
timestamps. `string_replace`, `line_replace` and `vault.update` write text as
given.

## Revisit

A page whose primary sources are all conversation records
(`source_type: conversation`) or reconstructed ones (`reconstructed: true`)
rests on secondhand statements. It stays on the revisit list ("Secondhand,
unverified" in `_status.md`) until a record of a real source (the document,
thread or dashboard behind the statement) is declared on it. No date clears it.
