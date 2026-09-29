# Sources and References Review Prompt

created: 2026-09-27

The prompt for the independent review of the sources and references design,
including the four error patterns the review was asked to hunt for.

> Review prompt for sources-and-references-design.md, written
> 2026-09-27 after the design session. It asks a fresh session to find gaps,
> weaknesses and side effects in the design, using the error patterns found
> during that session as a checklist.

You are reviewing a design document I will act on, and I need you to find what is wrong with it before I implement it. Work in Claude Code with read access to the files below.

<goal>
The design exists to answer this request: "a comprehensive design for the rules that govern how wiki files, frontmatter sources, and inline citations get written — one that makes broken references impossible to create, instead of another round of patches layered on earlier patches."
The full original prompt is ~/Projects/llm-wiki-pm/fork-chgs/sources-and-references-design-prompt.md. Read its <author_constraints> and <task> sections: they are the standard the design must meet. The constraints are mechanize or relabel, the SKILL.md token budget, non-blocking hooks, the keep-list, CONTRIBUTING's do-not-change items, semver, and upstream mergeability. Its numbered findings are background only. Where they conflict with the design's section 0, section 0 is correct.
</goal>

<context>
- Design under review: ~/Projects/llm-wiki-pm/fork-chgs/sources-and-references-design.md. It is an invariant-based redesign of how a PM wiki writes and checks raw/ source records, frontmatter `sources:`, inline `[source: …]` citations, `## Sources` legends and wikilinks. Section 1 has the invariants, section 5 the rules, section 5.15 the lint rule catalog, section 8 the implementation plan, section 9 the open decisions, and section 10 the follow-on work.
- The code it changes: the fork at ~/Projects/llm-wiki-pm, specifically skills/*/SKILL.md, skills/llm-wiki-pm/references/, templates, hooks/ (pre-write, post-write, session-start, session-stop, wiki-search.sh, hooks.json), .claude/agents/, skills/llm-wiki-pm/scripts/lint.py, and tests/. The hooks that actually run are registered in ~/.claude/settings.json.
- The content it governs: the private wiki at ~/Projects/pm-wiki (~245 pages).
- The wiki-search MCP is @wirux/mcp-markdown-vault v2.3.0. Its code is in the npx cache under ~/.npm/_npx/*/node_modules/@wirux/mcp-markdown-vault/dist.
</context>

<assumptions>
Assume I accept every recommendation in section 9, D1 through D11, including step 0's scrub of real names (D8). Review the design as it would be implemented under those choices.
</assumptions>

<why_this_review>
Earlier passes on this design made four kinds of mistakes, each caught only when I asked follow-up questions:
1. Cost out of proportion to frequency. It proposed a new `corrects:` field and lint rule for corrected raw records. Git history showed that happens about once in 156 records, and the existing Update flow already handles it. Both were dropped.
2. Relying on a signal nobody maintains. Lint rules (R10, and a since-dropped R14) cleared their warnings based on the `last_verified` date. Nothing in the skills or hooks ever sets that field. It turned out to be bumped as a side effect of ordinary edits, so it can't show that anyone actually verified anything.
3. Rules that fail on real file shapes. The citation resolution rule used the file stem. That breaks for directory pages (`queries/<slug>/README.md`) and for markdown artifacts stored inside those directories.
4. Unchecked data and dependencies. Timestamp-format dates (N15) turned up late, by accident. That led to finding that the MCP's frontmatter round-trip rewrites dates, which spawned a follow-on (F2).

Treat these as patterns to hunt for everywhere in the design, not just as instances to recheck.
</why_this_review>

<task>
Find the gaps, weaknesses and side effects in the design, and judge whether each proposed change is worth its cost. In particular:

- Check the design against the goal and every author constraint. Where it breaks one, is the justification sound? Where it only detects problems, is that stated honestly, and is the strongest available guarantee actually used? Has any part drifted back into the patch-on-patch pattern the goal rejects?
- For every new mechanism (field, lint rule, hook behavior, script, procedure): check how often the problem it addresses actually occurs, using wiki data or git history. Ask whether an existing flow already covers it. Recommend dropping or simplifying anything whose cost outweighs its benefit.
- For every field, date or signal a rule depends on: trace every writer across the skills, sub-skills, templates, hooks, workers, lint --auto-fix and the MCP. State whether the value is trustworthy for that use.
- For every resolution or matching rule: run it mentally, or better with a small script, against every file shape in the wiki. That includes directory pages, their artifacts, briefings/, root files (overview, index, log, SCHEMA), _archive/, raw/assets/, and records with unusual names.
- For every frontmatter field the design reads or writes: scan the actual values in the wiki for format variants.
- For every claim about hook or MCP behavior: verify it against the code, or test it, rather than inferring.
- Trace each invariant through every write path the design lists, and look for paths it missed. Report where the promised guarantee does not hold.
- Look for side effects the design doesn't mention: interactions between rules, migration steps that could lose data, conflicts with upstream merges, token or latency costs, and behavior changes users would notice.

Mark anything you couldn't verify as unverified; don't fill the gap with a guess.
</task>

<constraints>
- Read-only everywhere except your report file. Don't edit the design doc, the fork or the wiki, and don't post anything to GitHub.
- lint.py writes a report and appends to log.md in whatever wiki it runs against. To run it, or any other measurement, use a copy of the wiki in your scratchpad.
- The fork is public on GitHub and the wiki is private, so the report must use placeholder names. Use no real page names, people, companies or source slugs. Describe defect classes with counts.
</constraints>

<output>
Write the report to ~/Projects/llm-wiki-pm/fork-chgs/SOURCES-AND-REFERENCES-DESIGN-REVIEW-<today's date>.md.

For each finding, give:
- the design section or ID it affects
- what goes wrong, and on which path or file shape
- the evidence (file:line, a command, or counts)
- severity
- a recommendation: keep, simplify, drop, or fix, with the specific change

Order findings by severity. End with:
- a cost/benefit table of every new mechanism in the design, each marked keep, simplify or drop
- a short list of design-doc edits you recommend

Then give me a chat summary of the five most important findings.
</output>
