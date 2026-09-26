# Prompt

> Kept as written for provenance. Section 0 of
> [SOURCES-AND-REFERENCES-DESIGN-2026-09-25.md](SOURCES-AND-REFERENCES-DESIGN-2026-09-25.md)
> corrects several claims below (version dates in findings 14 and 17, the
> 18-page count in finding 10, and the current counts for findings 2 and 4);
> where they differ, the design doc supersedes this prompt.

I maintain a personal PM wiki built on llm-wiki-pm, a Claude Code skill I've forked from anh-chu/llm-wiki-pm. I need a comprehensive design for the rules that govern how wiki files, frontmatter sources, and inline citations get written — one that makes broken references impossible to create, instead of another round of patches layered on earlier patches.

<background>
Locations:
- Fork (the code to change): ~/Projects/llm-wiki-pm — skills/ (core llm-wiki-pm plus sub-skills brief, crm, maintain, persona, prd, research, set-wiki-path), hooks/ (session-start, pre-write, post-write, session-stop, the wiki-search.sh MCP launcher, hooks.json), .claude/agents/ (five worker subagents), skills/llm-wiki-pm/scripts/lint.py, tests/ (test_hooks.py, test_lint.py).
- Wiki (the content these rules govern, ~263 pages): ~/Projects/pm-wiki — raw/, entities/, concepts/, comparisons/, queries/, _archive/, log.md, index.md, SCHEMA.md, meta/ (the wiki-search MCP server's vault contract), .claude/agents/ (a second copy of the worker subagents).
- Author intent and history, in the fork root: README.md, CONTRIBUTING.md, AGENTS.md, PLUGIN-REVIEW-2026-07-15.md, CHANGELOG.md, and three feedback docs dated 2026-06-22.
- fork-chgs/ in the fork: LINT-FRONTMATTER-CHECKS-2026-09-23.md (the proposal that started this work) and llm-wiki-pm-changelog.md (local patches and open issues).

Setup: this no longer uses the marketplace plugin. Skills are symlinked from the fork into ~/.claude/skills/, the four hooks are registered at user level in ~/.claude/settings.json with absolute fork paths, and the wiki-search MCP server is registered in ~/.claude.json. The fork's files are what runs, in every project. The wiki path resolves via .wiki-path in the working directory (no parent-directory walk), then WIKI_PATH set in the launchd environment. I also want to keep merging upstream releases from anh-chu/llm-wiki-pm through the fork's `upstream` git remote.

What began as adding lint checks kept exposing deeper problems. Findings from previous sessions — verify before relying on them, since those sessions got several claims wrong on first pass:

1. No single spec for conversational sources; competing instructions. ingest-guide.md (~line 38) says capture to raw/internal/conversation-<YYYY-MM-DD>.md, but no such file exists in the wiki. The same bullet says to attribute user facts as `user, <date>`, which reads like a sources format. SKILL.md's micro-capture fast path prescribes `source: conversation | <date>` and says to skip reading ingest-guide. §4 Update had no raw-capture step. Result: 12 distinct shapes across ~81 non-path sources entries.
2. Unquoted comma-bearing entries (`conversation, 2026-08-07`) split into separate YAML list items — found on 11 pages, in date-clustered batches.
3. A phantom citation: a source slug was coined during an Update for data that arrived in chat and was never captured. It looked like a raw slug and propagated through a page split into 10 files, including archive snapshots.
4. Typo'd raw paths in frontmatter (wrong directory, dropped word) went undetected, because the grounding check only asks whether a source is non-wiki.
5. Frontmatter is parsed by three hand-rolled parsers that disagree: parse_frontmatter() and extract_sources() in lint.py, plus a copy inside hooks/pre-write.sh. None is real YAML. Known corruption patterns: a block item on a key line, orphan block items under a closed flow list, and duplicate keys (last-wins, so they parse cleanly).
6. The same source is written differently in two places: a full raw/ path in frontmatter, but a bare slug with an optional section qualifier or `;`-joined list in inline `[source: ...]` markers. Nothing maps one to the other exactly, so cross-checking needs fuzzy matching. Markers also cite wiki pages (crystallize digests, concepts) that aren't declared in sources, and markers containing a [[wikilink]] get truncated at its bracket.
7. Write paths differ in what they trigger. pre-write.sh is a PreToolUse hook matching Write|Edit|MultiEdit, so writes through the wiki-search MCP (edit frontmatter_set, vault update) never trigger it. That MCP also has a known bug that re-escapes `[` as `\[` on write (wirux/mcp-markdown-vault#47). pre-write.sh is advisory by design (it never denies), and on Edit it reads pre-edit content from disk.
8. A page-splitting pass copied the parent's full sources list onto each child.
9. Templates only ever show file paths in sources:.
10. The wiki-search MCP write path round-trips frontmatter through an AST and re-emits it, changing serialization and quoting as a side effect of unrelated edits. Observed in pm-wiki commit 5cc416c: an edit to one body line converted every inline flow list on the page to block style and stripped quotes from last_verified, applying YAML-minimal quoting. Values were preserved. Two consequences to assess: any invariant phrased as "must be quoted" is unstable under a path that strips quotes, and block style structurally prevents comma-shredding since one item per line cannot split. Also evaluate whether this round-trip, rather than the page-splitting script, produced the 18-page flow/block hybrid corruption described in LINT-FRONTMATTER-CHECKS.
11. fork-chgs/llm-wiki-pm-changelog.md documents earlier applied patches (PATCH-1 to PATCH-4) and open issues (ISSUE-1 to ISSUE-3). Read it and give a disposition for each. Two are directly in scope:
    - ISSUE-3 (opened 2026-08-30, still unfixed) is a superset of finding 3: a `conversation, <date>` source implies raw/internal/conversation-<date>.md per ingest-guide, and those files do not exist. Its "not yet decided" section proposes a lint rule plus a frontmatter-vs-body-Sources diff — weigh that against your own design rather than duplicating it.
    - PATCH-3a added block-style parsing to parse_frontmatter() but normalizes block lists into a comma-joined flow string, re-introducing the comma ambiguity that fe14c2f removed from extract_sources and making the two parsers disagree a second way. Assess whether it needs rewriting.
12. Sources are declared in THREE places, not two: frontmatter sources:, inline [source: ...] markers, and a body "## Sources" legend present on 49 pages. All three can drift — ISSUE-3 part B documents an entry that reached frontmatter and inline markers but never the legend, and survived six later edits. Treat the legend as a first-class declaration site in the invariants.
13. ISSUE-1 and ISSUE-3 share a root pattern: a citation or action item, once written, has no workflow step that revisits or verifies it. Consider whether the invariants need a revisit/verify obligation, not only write-time rules.
14. AGENTS.md is a spec location the findings above don't account for. It defines the inline grammar as `[source: raw-slug, location]` (documented since about v2.8 per CHANGELOG), requires both frontmatter sources and inline markers, and states "snapshot before destructive ops" as an agent obligation independent of the pre-write hook. So the bare-slug form in inline markers (finding 6) is the documented spec, not drift — and conversational markers like `[source: user, conversation, DATE]` violate it, since under that grammar they parse as a slug named `user`.
15. pm-wiki/meta/contract.md is the wiki-search MCP server's own vault contract, still the uncustomized default. It declares a different frontmatter schema (type: note|reference|log|template, a status field, and no sources field at all), a naming rule ("2–5 words, no prefixes") that the wiki's dated slugs violate, and a vault.create note template. The MCP server's instructions direct agents to read it for frontmatter and naming conventions, so it is the competing spec attached to exactly the write path pre-write.sh cannot see. No page has used it yet (0 pages with those type values or a status field), so this is latent. The file says the server never overwrites it and to edit freely.
16. Not every source is a file. ingest-guide lists nine source types (web, chat, email, transcript, pdf, conversation, warehouse, internal, other), and warehouse facts cite a query and snapshot (source_query_ref and source_snapshot frontmatter, `[source: <metric-slug>-<snapshot>, query <ref>]` inline) rather than a raw/ path. Any "every source resolves to a file" invariant must handle these.
17. The conversational-source conflict (finding 1) has a traceable origin: the capture-to-raw rule arrived around v2.5; the competing `conversation | <date>` form arrived with the v2.20.0 micro-capture fast path (PLUGIN-REVIEW item A13), which deliberately skips the ingest-guide read to avoid a 14-step ceremony for a single fact. Any design requiring capture for every conversational fact trades directly against that author goal and must say how micro-capture stays cheap. PLUGIN-REVIEW open decision 4 already proposes a raw/inbox/ capture queue with a lint age warning, deferred until micro-capture was in use — it now is.
18. The five worker subagents are write paths: worker-source-fetcher saves into raw/ and worker-wiki-indexer rewrites index.md and overview.md. Identical copies live in the fork's .claude/agents/ and pm-wiki's .claude/agents/; each copy runs only in its own project, and a change to one does not reach the other.
19. Tests are split: tests/test_hooks.py already has a TestLint class (5 tests, added in 2.20.0) alongside the newer tests/test_lint.py (13 tests), so faaf2d8's commit message is wrong to call test_lint.py the first lint test module. PLUGIN-REVIEW item A11 asked for a wiki-search.sh smoke test that was never added. pytest isn't installed on this machine; README gives a venv recipe.
20. Several upstream docs are stale against shipped behavior: README and CONTRIBUTING still describe a `private: true` flag that v2.18.0 deprecated and v2.20.0 removed in favor of the `shareable: true` allowlist, and CONTRIBUTING's frontmatter checklist lists coverage as required while lint.py's REQUIRED_FRONTMATTER does not (and lint requires created, which CONTRIBUTING omits).

Changes already committed and pushed to the fork but still provisional pending this analysis — recommend keeping, revising, or replacing each: lint rules R1–R5 (faaf2d8), a §4 Update rule requiring capture or a conversational citation (32e42a3), and quote-aware sources parsing in lint.py (fe14c2f). A fourth commit, c105625, fixed three unresolvable template references in the skills and is migration plumbing rather than a rules change. A separate wiki-side repair is committed in pm-wiki as 5cc416c.

Current lint baseline on the wiki: 0 errors, 37 warnings, 44 info; R3 fires on 31 pages, R4 on 12.

One candidate direction was discussed but not decided: every sources entry must be a path that exists on disk, with conversations appended to a daily raw/internal/conversation-YYYY-MM-DD.md file.
</background>

<author_constraints>
The upstream author has stated goals and limits. Treat them as constraints; where your design needs to break one, say so explicitly and justify it.
- Mechanize or relabel. PLUGIN-REVIEW and the v2.20.0 release name the core failure as guardrails "in prose that structurally could not fire", and the fix pattern as converting mechanizable guards into hooks or lint and relabeling the rest as checklists rather than presenting them as enforced. Use that framing for your prevented-versus-detected distinction.
- Token budget. v2.20.0 cut SKILL.md from ~8.2k to ~4.3k tokens. Put detail in references/ and enforcement in lint or hooks, not SKILL.md prose, and report your net SKILL.md size change.
- Hooks stay non-blocking. PLUGIN-REVIEW's keep-list endorses "always-exit-0 non-blocking" hooks, so a design in which any hook denies a write breaks an explicit author principle.
- Also on the keep-list: the three-layer data model, supersession-with-archive, confidence and coverage as independent axes, and the three named source-discipline guard anchors that sub-skills cite by name.
- CONTRIBUTING's "do not change without discussion": the three-layer architecture, the orient gate, and the [[wikilink]] format. (Its fourth item, `private: true`, is stale — see finding 20.)
- Semver. CONTRIBUTING classes a new required frontmatter field or a changed directory layout as a major version. Classify your changes accordingly.
- Upstream mergeability. I want to keep merging anh-chu's releases, so prefer changes that keep conflict surface small in heavily edited upstream files, and flag which changes are general enough to offer upstream as PRs versus fork-only.
</author_constraints>

<task>
Analyze the rules governing creation and update of every wiki file type and every reference form, then design a coherent replacement. Cover at minimum:
- raw capture: naming, directory, when capture is mandatory, and how non-file sources (warehouse queries, web) are cited
- page creation, naming, split, supersede, and archive
- the frontmatter schema — including reconciling it with pm-wiki/meta/contract.md — and how it is written and parsed
- sources: entries, inline [source: ...] citations, and the body "## Sources" legend — one grammar, starting from the AGENTS.md definition, and how each resolves
- wikilinks

Start from invariants rather than fixes. State the small set of properties that, if they hold, make broken references impossible — for example, "every sources entry resolves to a file" and "every inline citation resolves to a declared source." For each invariant, identify the single place it should be specified, every write path that can violate it, and where it gets enforced.

Build the write-path inventory yourself: read every SKILL.md, reference guide, template, hook, worker agent, and lint.py in the fork, plus the author-intent docs listed above, and list each operation that creates or modifies a page or a raw file. The findings above are a starting point, not the inventory.

Be explicit about the difference between "impossible by construction" and "detected after the fact." Where true prevention isn't achievable (MCP writes bypassing hooks is one likely case), say so and state the strongest guarantee that is available. I'd rather know the real limits than be told everything is prevented.

Evaluate the undecided path-only candidate against at least three alternatives on their merits: mandated block-style frontmatter lists, the raw/inbox/ capture queue from PLUGIN-REVIEW open decision 4, and one of your own.

Three specific items to fold in:
- The write-side wiki-search MCP dispatchers (vault, edit, system) are deliberately left off the permission allowlist because pre-write.sh never fires on MCP writes, so no _archive/ snapshot is taken and those writes have no undo. Treat closing that gap as in scope: extend hook coverage, route frontmatter edits through the Write tool, or state plainly that the snapshot guarantee does not hold for MCP writes. Note which of your invariants inherit the same hole, and how AGENTS.md's behavioral snapshot rule applies.
- hooks/wiki-search.sh:12 reads .wiki-path with `< "$(pwd)/.wiki-path"`, so when the file is absent the shell itself reports the failure before any command runs, and neither 2>/dev/null nor || true suppresses it. Every session started in a directory without .wiki-path prints a spurious "No such file or directory" to stderr. The other three hooks avoid this with `cat ... 2>/dev/null`, and session-start.sh tests with -f first. Include the fix, together with the smoke test PLUGIN-REVIEW A11 asked for.
- Decide where lint tests should live, given the TestLint/test_lint.py split, and how the two copies of the worker agents should be kept consistent.
</task>

<constraints>
- This is analysis and design only. Don't modify the fork or the wiki; the one file to create is the deliverable below.
- To measure anything against the wiki, run lint.py on a copy in your scratchpad. It writes queries/lint-YYYY-MM-DD.md and appends to log.md in whatever wiki it runs against.
- Verify each claim against the files before stating it, and mark anything you couldn't verify.
- The fork is public on GitHub, so the deliverable will be too, while the wiki is private. In the design doc, use placeholder names in every example: no real wiki page names, customer, company, or person names, or real source slugs. Describe defect classes rather than quoting instances, with counts where useful. The author scrubbed proper nouns from distributed files in v2.20.0 for the same reason.
</constraints>

<output>
Write the design to fork-chgs/SOURCES-AND-REFERENCES-DESIGN-<today's date>.md in the fork, in the style of the existing LINT-FRONTMATTER-CHECKS doc. Include:
1. The invariants, each with its spec location, the write paths that can violate it, its enforcement point (write-time, lint, or none), and the resulting guarantee.
2. Root causes, mapped to the findings above plus any new ones you find.
3. The proposed rules and canonical formats, with placeholder examples of valid and invalid entries.
4. A disposition for each already-committed fork change (faaf2d8, 32e42a3, fe14c2f, c105625), each patch and issue in llm-wiki-pm-changelog.md (PATCH-1 to PATCH-4, ISSUE-1 to ISSUE-3), and any still-open PLUGIN-REVIEW items your design touches: keep, revise, replace, or close.
5. Legacy content migration: what currently violates the new rules, with counts, and how to convert it, including content that can't be recovered.
6. An ordered implementation plan with dependencies, including the semver classification, the net SKILL.md size change, and which changes are candidates to offer upstream.
7. Open decisions that need me, with your recommendation for each.

Then give me a short summary in chat: the invariants, the biggest root cause, and the decisions you need from me.
</output>