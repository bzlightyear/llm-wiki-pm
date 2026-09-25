# lint.py — proposed frontmatter validity and provenance checks

Date: 2026-09-23 · Status: **proposed, not implemented** · Target file: `skills/llm-wiki-pm/scripts/lint.py`

Written after a working session on a 263-page wiki in which `lint.py` reported
`0 errors` while 23 pages had frontmatter that no YAML parser could read, and
while 9 freshly created pages carried `sources:` lists that were substantially
fabricated. Both defect classes were found by hand, not by lint.

Line references are against `lint.py` as of plugin version 2.21.0. The copy at
`skills/llm-wiki-pm/scripts/lint.py` in this repo is byte-identical to the
published 2.21.0 artifact, so the references hold for both.

---

## Bottom line

Two checks are missing. They are different propositions and should be judged
separately.

1. **Frontmatter structural validity.** Unambiguously in scope. `lint.py`
   already claims to validate frontmatter but its hand-rolled parser accepts
   input that silently discards keys. Fixable with two regex rules and no new
   dependency.
2. **Provenance cross-reference** between frontmatter `sources:` and inline
   `[source: ...]` markers. Worth adding, but **not as a set-equality check** —
   equality contradicts the skill's own documented convention and would fire on
   correct pages. The asymmetric form is the right one.

Neither check requires changing lint's output format, tiering, or auto-fix
model.

---

## Evidence from the 2026-09-23 session

A wiki-wide `yaml.safe_load` over every page with frontmatter returned **23
failures** across two distinct corruption patterns. `lint.py` reported
**0 errors** on the same tree, before and after.

| Pattern | Count | Example |
|---|---|---|
| Block list items appended under an inline flow list | 18 live pages | `sources: [a.md, b.md]` followed by `  - c.md` |
| Block list pasted onto its own key line | 5 concept pages | `tags: - roadmap` |
| **Duplicate top-level keys** | 2 concept pages | `last_verified`, `coverage`, `gaps`, `shareable` each present twice |

The third pattern was found last, and only because Obsidian's Properties panel
reported "invalid properties" on a page that every programmatic check had
already passed. It is the most instructive of the three: see R5 below.

Consequence of the first pattern: **everything after the first orphan line is
invisible to a parser.** On ten person entity pages — including `casey-doran`
and `eric-theriault` — that meant `reports_to`, `direct_reports`, `peers`,
`coverage`, `gaps` and `shareable` did not exist as far as any YAML consumer
was concerned. The org graph those pages are supposed to encode was silently
absent.

Separately, nine history pages created by a page-splitting script carried their
parent page's entire current `sources:` list rather than the subset their own
content cites. Worst case listed 22 sources where the body cited 3. Every entry
was a well-formed, existing `raw/` path, so nothing in lint's existing grounding
check objected.

---

## Check 1 — frontmatter structural validity

### Why it currently passes

`parse_frontmatter()` (`lint.py:103`) does not parse YAML. It walks lines and
partitions on the first `:`. The block-list branch at `lint.py:115-124` only
triggers when the key's value is empty:

```python
if not val:
    # possible block-style YAML list: key: \n  - item \n  - item
```

So `tags: - roadmap` parses as key `tags` with the non-empty string value
`- roadmap`. It never reaches the list branch. The key exists, so the
`REQUIRED_FRONTMATTER` check at `lint.py:307` is satisfied — that check tests
key presence only, never whether the value is well formed.

The orphan-continuation pattern passes for a related reason: `parse_frontmatter`
reads the inline `[...]` value, then the loop's `i += 1` moves past it, and the
orphan `  - item` lines fall through the `if ":" in line` test without matching
anything. They are neither consumed nor reported.

Note that `extract_sources()` (`lint.py:210`) is *more* tolerant still — it
deliberately handles both forms and will happily union an inline list with the
orphan lines beneath it (`lint.py:224-228`). So lint's two frontmatter readers
disagree with each other about the same file, and both disagree with YAML.

### Proposed rules

Both corruption patterns are detectable without a YAML parser, within the
existing regex approach:

- **R1 — block item on a key line.** A frontmatter line matching
  `^([A-Za-z_][A-Za-z0-9_]*):\s+-\s` is malformed. A key's value may not begin
  with a list-item dash. Catches the 5-page pattern.
- **R2 — orphan block item under a flow list.** An indented `-` line whose
  nearest preceding key line carried a closed `[...]` value is unreachable.
  Catches the 18-page pattern.

- **R5 — duplicate top-level key.** The same key appearing more than once in
  one frontmatter block. **`yaml.safe_load` does not raise on this** — YAML is
  last-wins, so a duplicate key parses cleanly and silently discards the earlier
  value. A parseability check therefore cannot catch it, and neither can R1 or
  R2. Obsidian's Properties panel *does* flag it, which is how it surfaced.
  Detection is a `Counter` over top-level key matches.

Suggested tier: 🔴 error. These are not stylistic — they destroy data visibility,
and the affected keys include `shareable`, which governs the export allowlist
(`is_shareable()`, `lint.py:151`). A page whose `shareable` line sits below an
orphan is being evaluated for export on a field lint cannot actually read.

### On adding PyYAML

The cleanest implementation is `yaml.safe_load` in a try/except. `lint.py`
currently imports only stdlib (`re`, `sys`, `collections`, `datetime`,
`pathlib`), and PyYAML is not stdlib, so a hard dependency would be a real
change in the plugin's install surface. That constraint plausibly explains the
hand-rolled parser in the first place.

Recommended compromise: attempt `yaml.safe_load` inside a guarded import, fall
back to R1 and R2 when PyYAML is unavailable. Full coverage where the
dependency exists, the two known structural patterns everywhere else.

**But do not treat a successful `yaml.safe_load` as sufficient.** R5 is the
counterexample: duplicate keys parse cleanly and are invisible to the parser by
design. R5 must run as its own line-level check regardless of whether PyYAML is
available. A frontmatter validator built solely on "does this parse" will keep
reporting clean on files that a Markdown editor refuses to render.

### Suggested auto-fix

Both patterns have a lossless mechanical repair: merge the flow contents and the
orphan lines into a single block list. This was done by hand across 20 pages in
the source session without incident, and fits the existing `--auto-fix` model
alongside the index backfill and supersession-redirect repairs.

**Caveat, learned the hard way.** One of the 20 pages had its list items
*destroyed* rather than orphaned — only the first entry of each list survived,
so the file was recoverable-looking but lossy. Repairing it in place would have
converted real data loss into valid YAML and closed the case. An auto-fix should
therefore report before-and-after item counts per page, not just "fixed N
files", so a suspicious drop is visible.

---

## Check 2 — provenance cross-reference

### What lint does today

`extract_sources()` feeds exactly one rule, the grounding check at
`lint.py:348-366`. That rule asks a single binary question: is at least one
source non-wiki (primary), or are they all wiki-internal (self-referential)?

A `sources:` list of 22 valid `raw/` paths passes trivially, whether the page
cites all 22, three, or none. There is no rule anywhere in the file that relates
frontmatter `sources:` to the `[source: ...]` markers in the body. The closest is
the inline-provenance check at `lint.py:370-377`, which only tests whether *any*
marker exists on a long factual page.

### Why equality is the wrong check

The session verification used set equality in both directions. That was correct
for its narrow situation — freshly split pages whose bodies were known to be
self-contained — and is **wrong as a general lint rule**.

Per the skill's own convention (`ingest-guide.md` step ⑤): frontmatter `sources:`
lists *all* sources for the page, while inline markers anchor *specific claims*.
A source in frontmatter with no inline marker is therefore legitimate. Enforcing
equality would fire on correct pages, including every page written before the
inline-marker convention was adopted.

### Proposed rules

- **R3 — dangling inline marker.** An inline `[source: x]` whose `x` does not
  resolve to any entry in frontmatter `sources:` is a severed provenance chain:
  a reader cannot get from the claim to the artifact. Suggested tier: 🔴 error,
  subject to the resolution caveat below.
- **R4 — bulk uncited sources.** Frontmatter entries never cited inline are not
  individually a defect, but a high ratio is the signature of a copy-paste. A
  page listing 22 sources and citing 3 should be flagged. Suggested tier: 🟡
  warning, on a ratio threshold rather than per-entry, so it stays quiet on
  normal pages. This rule alone would have caught all nine bad pages from the
  source session.

### Implementation caveat: the marker grammar is loose

This is the part most likely to produce a noisy, ignored check. Real markers
observed in a single wiki:

```
[source: cfp-reqmts-sync-2026-09-08]
[source: cba-product-update-customer-feedback-2026-09-10, Recently Shipped]
[source: user, conversation, 2026-09-16]
[source: user, conversation (CFP Coordination meeting), 2026-08-12]
[source: raw/internal/ask-cfp-2026-08-06.md]
[source: user, conversation, 2026-08-25;
raw/internal/underwriteme-cost-sharing-request-2026-08-25.md]
```

So a resolver must handle: bare slug, slug plus section name after a comma,
already-qualified `raw/` path, self-describing `user,`/`conversation,` citation
whose own text contains commas and parentheses, multiple sources joined by `;`,
and markers wrapped across a newline. A naive "split on the first comma"
normalization is wrong — it collapses the fourth example to bare `user`.

**Treat unresolvable markers as 🔵 info, never as an error.** A provenance check
that emits false positives on legitimate prose will be tuned out within a week,
which is worse than not having the check.

---

## Testing

`tests/test_hooks.py` covers hooks only; there is no test module for `lint.py`.
Adding these checks is a reasonable moment to start `tests/test_lint.py`,
following the existing fixture pattern (temp wiki via `tmp_path`, run the
script, assert on output).

Minimum fixtures worth encoding, all drawn from real files:

- flow list followed by orphan block items → R2 fires
- block list pasted onto key line → R1 fires
- well-formed inline list, well-formed block list → neither fires
- a key appearing *after* an orphan line is correctly reported as unreachable
- the same key twice in one block → R5 fires, **and** the file still
  `yaml.safe_load`s without error (assert both, so the test documents why R5
  cannot be folded into a parse check)
- inline marker with a section name after a comma → resolves, R3 silent
- `user, conversation (X), DATE` marker → resolves or is 🔵, never 🔴
- `;`-joined multi-source marker → both halves resolve
- 22 listed / 3 cited → R4 fires; 8 listed / 8 cited → silent

Per `CONTRIBUTING.md`, the PR checklist item "`scripts/lint.py` runs without
error on a test wiki" should be read as necessary but not sufficient here: the
scaffolded test wiki has well-formed frontmatter and will pass regardless of
whether these checks exist.

---

## Out of scope

- Changing lint's tiering, report format, or JSON output shape.
- The `parse_frontmatter` / `extract_sources` divergence noted above is worth
  reconciling eventually, but is a refactor, not part of these checks.
- Auto-fixing `sources:` content. R3 and R4 should report only. Recomputing a
  correct source list requires reading the body's citations and is too
  judgment-laden to automate safely — the session that prompted this document
  needed two hand-verified attempts to get it right on nine pages.

---

## Provenance of this document

Written from direct inspection of `lint.py` 2.21.0 and from a 2026-09-23 session
on a 263-page production wiki. Both defect classes and all example markers above
are real, taken from that wiki. The page-splitting script whose bugs exposed
this was a one-off written during that session, not plugin code — the plugin
ships no page-splitting tool, and neither defect originates in `lint.py` itself.
The gap is only that lint reported clean throughout.
