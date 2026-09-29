# Sources and References Implementation Prompt

created: 2026-09-29

Reusable prompt for implementing one step of the implementation plan in the
[Sources and References Design](sources-and-references-design.md) (section 8).
Start a new session with it for each step, or each small group of steps, and
change only the step number in the first line.

---

Implement step <N> of the implementation plan in ~/Projects/llm-wiki-pm/fork-chgs/sources-and-references-design.md (section 8).

<context>
- The design is the spec. Read section 8's row for this step and its "Depends on" column, then the sections that row points to (the rules in section 5, the lint catalog in 5.15, the migration in section 7), and the decisions in section 9. Changes marked "(review Fn)" came from sources-and-references-review.md; read that finding when you need the reasoning behind a rule.
- Also follow AGENTS.md (behavioral contract), CONTRIBUTING.md (semver, protected formats) and fork-chgs/doc-conventions-guide.md (for any fork-chgs doc you touch).
- Implement in the fork only. Offering changes upstream is a separate task after the whole plan is done, so don't open issues or pull requests. Still follow the design's merge-friendly layout (section 8, "Upstream conflict surface"): new tests go in new files, and new rules go in `wikifm.py` and separate lint functions.
- Steps 0 and earlier are done; check the design's status line and the git log for what else has landed. If a step this one depends on isn't done, stop and tell me.
</context>

<environment>
- Hooks registered in ~/.claude/settings.json point at this repo's hooks/ and run in every Claude Code session, so a broken hook affects all sessions at once. Change hook scripts only with tests covering the change. Show me any settings.json edit before making it.
- Test on the system Python, /usr/bin/python3 (3.9), which is what the hooks run under: `python3 -m pytest -q tests`. One failure predates this work and can be left alone unless this step touches it: TestPostWrite::test_parses_file_path_from_stdin_without_jq (upstream v2.20.0 made post-write.sh silent on clean writes but kept this test). Keep code compatible with Python 3.9.
- The private wiki is ~/Projects/pm-wiki. Only step 10 writes to it. For any measurement, or to run lint.py (which writes a report and appends to log.md), use a copy in your scratchpad.
- The fork is public. Use no real names of people or customer companies from the wiki in code, tests, docs or commit messages; product and page-topic names are fine. Describe wiki data with counts.
- ~/Projects/llm-wiki-pm-prerewrite-backup-2026-09-29.git holds pre-rewrite history with private names. Never push from it or copy from it.
</environment>

<process>
1. Before changing anything, tell me your plan: the files you'll change or add, how each part of the step's row will be met, and the tests you'll add. Point out anything in the design that is ambiguous, contradicts the code, or looks wrong, and ask rather than guess. Wait for my go-ahead.
2. Implement, then run the full test suite and any checks the design names for this step.
3. Show me a summary of the diff and the test results. Wait for approval.
4. On approval, commit (conventional commit style, one commit per step unless the step splits naturally), then update the design:
   - its status line, to "in progress" with the steps completed so far (or "implemented" after step 11);
   - a `revised on:` entry for today if the step changed the design's content, per the doc conventions guide.
   Don't push unless I ask.

If implementing the step shows that the design needs to change, propose the design edit alongside the code, and record it in the design once I approve.
</process>
