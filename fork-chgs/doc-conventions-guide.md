# Doc Conventions Guide

created: 2026-09-29

The naming and opening-section conventions for documents in `fork-chgs/`, for
future design, review and companion docs to follow. They were first applied by the
[Doc Conventions Prompt](doc-conventions-prompt.md).

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

Every doc starts with this block, directly under the H1:

```
created: YYYY-MM-DD

<Purpose: 1–3 sentences on what the document is for and what it covers.>

revised on: YYYY-MM-DD
<2–3 sentences describing what that revision changed.>

revised on: YYYY-MM-DD
<…>
```

- **Revision entries are newest first.** Each later update adds a new entry at the
  top of the list; older entries are never edited. The newest entry's date is the
  doc's last-updated date.
- **One entry per calendar day with substantive changes.** Changes made on the
  creation day are part of the initial version: the purpose statement describes
  the final state, and there is no entry. Typo, formatting and rename-only
  changes don't need an entry.
- **Other opening material follows the block.** Status, scope, companions, and
  label or severity conventions go below it, one item per line where they used to
  share a line with a date.

## Updating an existing doc to the convention

- Reconstruct revision entries from git history (`git log --follow`) and from
  revision notes already in the text.
- The block is additive. The doc's existing opening text stays, word for word.
  Remove only text whose sole job is a date or revision note that the block now
  records. Where a line mixes a date with other items, remove just the date. Where
  a revision note also states a lasting convention, keep the convention as an
  undated sentence.
- When a new title-case H1 replaces a more descriptive old one, make sure the
  purpose statement keeps that description.
- Rename with `git mv`, and update every reference: markdown links and plain-text
  mentions in `fork-chgs/`, anywhere else in the repo (including code comments),
  and this project's Claude memory notes.
- Prompts are historical records: update references to files that exist, but
  leave the output-name patterns they gave (for example `…-<today's date>.md`).
