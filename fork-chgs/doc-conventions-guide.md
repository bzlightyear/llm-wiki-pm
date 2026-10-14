# Doc Conventions Guide

created: 2026-09-29

The naming and opening-section conventions for documents in `fork-chgs/`, for
future design, review and companion docs to follow. They were first applied by the
[Doc Conventions Prompt](doc-conventions-prompt.md).

## Revision History

revised on: 2026-10-14
Each substantive revision now gets its own entry, so several can share a date,
and a change made on the creation day after the first commit gets one too. The
entries sit under a `## Revision History` header, and the other opening material
moves to its own section after it. Every doc in `fork-chgs/` was moved to this
layout the same day.

## File names

- `<subject>-<doctype>.md`, all lowercase kebab case. For example,
  `sources-and-references-design.md` or `wiki-search-mcp-tools-analysis.md`.
- **subject:** the document's primary focus. Docs that belong together share a
  subject: a design, its review and its prompts all start with
  `sources-and-references-`.
- **doctype:** one word for the document's purpose, such as `design`, `review`,
  `analysis`, `prompt`, `guide`, `changelog` or `appendices`. A prompt is named
  after what it produces, for example `sources-and-references-review-prompt.md`.
- No dates in file names. Dates live in the opening section.

## Names inside documents

A doc's name is written in title case wherever a document names it: its H1, and
the text of any link to it. For example,
`[Sources and References Review](sources-and-references-review.md)`.

- Small words (and, of, the) are lowercase, acronyms are in capitals (MCP), and
  product names stay as normally written (llm-wiki-pm, wiki-search).
- Link targets, and mentions in code or command paths, use the kebab-case file
  name.

## Opening section

Every doc opens with these parts, in this order:

```
# <Title>

created: YYYY-MM-DD

<Purpose: 1–3 sentences on what the document is for and what it covers.>

## Revision History

revised on: YYYY-MM-DD
<2–3 sentences describing what that revision changed.>

revised on: YYYY-MM-DD
<…>

## Status

<The other opening material, one item per line.>
```

The body follows, after a `---` rule where the doc uses one. In a prompt, the
`---` rule separates the opening from the prompt text.

- **The purpose statement describes the doc as it stands.** A revision that
  changes what the doc covers or recommends updates it.
- **One entry per substantive revision.** Several entries can share a date. A
  doc's initial version is what was first committed, so any later substantive
  change gets an entry, including one made on the creation day. Typo, formatting
  and rename-only changes don't need an entry.
- **Revision entries are newest first,** including among entries with the same
  date. Each later revision adds a new entry at the top of the list; older entries
  are never edited. The newest entry's date is the doc's last-updated date.
- **A doc with no revision entries leaves out Revision History** until its first
  revision.
- **Other opening material gets its own section after Revision History,** so it
  doesn't read as part of the history: status, backlog item, related docs,
  companions, scope, provenance notes, and label or severity conventions, one item
  per line where they used to share a line with a date. Name the section for its
  content: `## Status` when it holds only status, backlog item and related-doc
  lines, and `## About This Document` when it holds more. A doc with no other
  opening material leaves the section out.

## Updating an existing doc to the convention

- Reconstruct revision entries from git history (`git log --follow`) and from
  revision notes already in the text, one entry per substantive revision.
- The opening is additive. The doc's existing opening text stays word for word,
  moved into the section after Revision History. Remove only text whose sole job
  is a date or revision note that Revision History now records. Where a line
  mixes a date with other items, remove just the date. Where a revision note also
  states a lasting convention, keep the convention as an undated sentence.
- When a new title-case H1 replaces a more descriptive old one, make sure the
  purpose statement keeps that description.
- Rename with `git mv`, and update every reference: markdown links and plain-text
  mentions in `fork-chgs/`, anywhere else in the repo (including code comments),
  and this project's Claude memory notes.
- Prompts are historical records: update references to files that exist, but
  leave the output-name patterns they gave (for example `…-<today's date>.md`).
