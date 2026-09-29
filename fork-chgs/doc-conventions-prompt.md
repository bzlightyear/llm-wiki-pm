# Doc Conventions Prompt

created: 2026-09-29

Prompt that renames the design documents in `fork-chgs/` to a consistent
`<subject>-<doctype>.md` convention, gives each one a standard opening section
(created date, purpose, dated revision entries), and updates every reference to
the renamed files.

---

Rename the design documents in ~/Projects/llm-wiki-pm/fork-chgs/ to a consistent naming convention, and give each one a standard opening section. Each follow-on work item (NW1–NW4) will produce its own design, review and companion docs, so the convention needs to scale.

<naming>
- File name: <subject>-<doctype>.md, all lowercase kebab case, for example sources-and-references-design.md or wiki-search-mcp-tools-analysis.md.
  - subject: the document's primary focus.
  - doctype: one word for its purpose: design, review, analysis, prompt, changelog, guide, etc. Choose what fits each file, and flag any where the choice isn't obvious.
- No dates in file names; dates live in the opening section.
- Inside documents, a doc's name is written in title case: its H1, and the text of any link to it, for example `[Sources and References Review](sources-and-references-review.md)`. Keep small words (and, of, the) lowercase, acronyms in capitals (MCP), and product names as normally written (llm-wiki-pm, wiki-search). Link targets and mentions in code keep the kebab-case file name. When a new H1 replaces a more descriptive old one, make sure the purpose statement keeps that description.
</naming>

<opening_section>
Every doc starts with this block, directly under the H1 title:

created: YYYY-MM-DD

<Purpose: 1–3 sentences on what the document is for and what it covers.>

revised on: YYYY-MM-DD
<2–3 sentences describing what that revision changed.>

revised on: YYYY-MM-DD
<…>

- Revision entries are listed newest first. Each later update adds a new entry at the top of the list; older entries are never edited. The newest entry's date is the doc's last-updated date.
- One entry per calendar day with substantive changes. Changes made on the creation day are part of the initial version: describe the final state in the purpose statement and add no entry. Typo or formatting-only changes don't need an entry.
- For existing docs, reconstruct the entries from git history (`git log --follow`) and from any revision notes already in the text (for example a "Revised 2026-09-28" paragraph).
- The block is additive. The doc's existing opening text stays below it, word for word, because it carries details such as status, scope, companions, label and severity conventions. Remove only text whose sole job is a creation date, last-updated date or revision note that the block now records. Where a line mixes a date with other items (for example "Date: … · Status: … · Scope: …"), remove just the date fragment and keep the other items, one per line. Where a revision note also states a lasting convention (for example how changes are marked), keep the convention as an undated sentence. Update file names that appear in titles or text.
</opening_section>

<scope>
- Every .md file in fork-chgs/.
- Cross-links: update every reference to a renamed file, both markdown links and plain-text mentions:
  - in fork-chgs/;
  - anywhere else in the repo, including code comments (for example lint.py cites the lint-checks doc);
  - in this project's Claude memory files under ~/.claude/projects/-Users-pgoubert-Projects-llm-wiki-pm/memory/.
  Search the whole repo rather than assuming where references live.
- Use `git mv`, so history follows each file.
- Record the convention (the naming and opening-section rules above) in fork-chgs/doc-conventions-guide.md, itself following the convention, so future work items can follow it.
</scope>

<process>
1. Before changing anything, show me:
   - a table of each current name → proposed name, with the doctype chosen and the created date;
   - for each doc, the proposed purpose statement and revision entries, and exactly which existing opening text would be removed or split (everything else stays);
   - every file outside fork-chgs/ that references a file being renamed.
   Then stop and wait for my approval or edits.
2. After I approve, rename the files, write the opening sections, and update all references.
3. Verify: search the repo and the memory directory again for every old file name (expect 0 hits), and check that every relative markdown link in fork-chgs/ resolves to an existing file.
4. Show me a summary of the changes. Don't commit until I say so.

If fork-chgs/ has uncommitted changes when you start, tell me before step 1, so I can commit them separately from the renames.
</process>
