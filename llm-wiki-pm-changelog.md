# llm-wiki-pm — Local Changes & Open Issues

_Relocated 2026-08-30 from `pm-wiki/concepts/llm-wiki-pm-plugin-patches.md` (a PM
knowledge wiki that runs on this plugin) — tooling/meta content, not PM domain
knowledge, so it belongs here instead. Originally created 2026-08-11, last updated
2026-08-29. Renamed and reorganized 2026-08-30 (same session): corrected a
stale patch count and a dangling cross-reference (see PATCH-4 note below),
adopted `PATCH-N`/`ISSUE-N` IDs, merged five overlapping Open Issues entries
into one (now ISSUE-1), and added a status line to each open issue._

## About this document

This file has two jobs: a durable record of locally applied patches to the
installed `llm-wiki-pm` plugin, and a tracker for open design/workflow gaps
that don't have a concrete fix proposed yet.

**Applied patches** (below): four local, uncommitted-turned-committed patches
to the installed `llm-wiki-pm` plugin (version 2.21.0, upstream
`github.com/anh-chu/llm-wiki-pm`), applied directly to the cached install at
`~/.claude/plugins/cache/anh-chu-plugins/llm-wiki-pm/2.21.0` and committed
locally as commits `4b74c51`, `79c9f3b`, and `f7faab5` on top of the plugin's
own `main` (`0667f75 chore(release): 2.21.0`). PATCH-3 bundles five related
sub-fixes to the same file (3a-3e) under one patch. These commits do **not**
survive a plugin update — see "Why this doesn't survive an update" below —
so the diffs are captured here in full for manual re-application.

**Open issues** (further below): design/workflow gaps surfaced while
auditing the plugin's guidance and this wiki's usage of it — real problems,
not yet fixed, each with its own status line.

## Applied Patches

### Why this doesn't survive an update

`installed_plugins.json` pins the install to a version-specific path
(`.../llm-wiki-pm/2.21.0`) tied to an exact `gitCommitSha`, and the plugin's
own directory is a git repo with no local commits ahead of `origin/main`
before this patch. All observed evidence (version number baked into the
install path, `installedAt`/`lastUpdated` frozen since first install, the
marketplace catalog's own `lastUpdated` moving independently) points to
updates being fetched into a **new** version directory (e.g. `2.22.0`) rather
than a `git pull` inside the existing one. Nothing merges the two — a commit
made inside `2.21.0` stays inert there once Claude Code repoints at a newer
directory. This is inference from directory/version structure, not from
documented plugin-installer internals.

### PATCH-1 — `hooks/session-stop.sh`: disable auto-commit block

**Problem:** the hook's auto-commit fired once per short-lived backend
session in this hosting environment, not once per real user conversation,
producing dozens of near-duplicate git commits in the wiki repo.

**Fix:** comment out the auto-commit block; user commits manually now.

```diff
--- a/hooks/session-stop.sh
+++ b/hooks/session-stop.sh
@@ -18,6 +18,16 @@ LOCKFILE="$WIKI/.wiki-lock"
 # Release lock on any exit path (early returns, errors, normal completion)
 trap 'rm -f "$LOCKFILE" 2>/dev/null || true' EXIT
 
+# ── Auto-commit wiki changes (runs every session end, not just on rotation) ──
+# Disabled 2026-08-07: firing far more often than intended (SessionEnd fires
+# per short-lived backend session in this hosting environment, not once per
+# user conversation), producing dozens of near-duplicate commits. User commits
+# manually now.
+# if [[ -d "$WIKI/.git" ]]; then
+#   git -C "$WIKI" add -A >/dev/null 2>&1 || true
+#   git -C "$WIKI" commit -m "wiki update $(date +%Y-%m-%d_%H:%M)" >/dev/null 2>&1 || true
+# fi
+
 LOG_FILE="$WIKI/log.md"
 
 # ② Exit silently if log.md does not exist
```

### PATCH-2 — `skills/llm-wiki-pm/scripts/backlinks.py`: README self-link fix

**Problem:** `scan()` compared a page's own slug via `p.stem`, which is
always `"README"` for a directory-as-page (`slug()` in `lint.py` already
special-cased this — `backlinks.py` hadn't caught up). A directory-page's own
outbound links to itself were never excluded from its own backlink scan.

**Fix:** compute `self_slug` the same way `lint.py`'s `slug()` does — parent
directory name for `README.md`, filename stem otherwise.

```diff
--- a/skills/llm-wiki-pm/scripts/backlinks.py
+++ b/skills/llm-wiki-pm/scripts/backlinks.py
@@ -22,7 +22,8 @@ def scan(wiki: Path, target: str, include_context: bool = False):
         for p in (wiki / d).rglob("*.md"):
             if p.name.startswith("lint-"):
                 continue
-            if p.stem == target:
+            self_slug = p.parent.name if p.name == "README.md" else p.stem
+            if self_slug == target:
                 continue  # self
             text = p.read_text()
             line_hits = []
```

### PATCH-3 — `skills/llm-wiki-pm/scripts/lint.py`: four bundled fixes

All four landed in one commit since they touch the same file; each is
independent and can be re-applied separately.

**3a. Block-style YAML frontmatter parsing.** `parse_frontmatter()` only
handled inline `key: [a, b]` lists. A `sources:` (or any) field written in
block style (`key:\n  - item\n  - item`) parsed as an empty string, silently
losing the list. Logged 2026-08-06 as "lint.py block-style YAML tag parsing
bug."

```diff
--- a/skills/llm-wiki-pm/scripts/lint.py
+++ b/skills/llm-wiki-pm/scripts/lint.py
@@ -38,10 +62,25 @@ def parse_frontmatter(text):
     if not m:
         return None
     fm = {}
-    for line in m.group(1).splitlines():
+    lines = m.group(1).splitlines()
+    i = 0
+    while i < len(lines):
+        line = lines[i]
         if ":" in line:
             k, _, v = line.partition(":")
-            fm[k.strip()] = v.strip()
+            key, val = k.strip(), v.strip()
+            if not val:
+                # possible block-style YAML list: key: \n  - item \n  - item
+                items = []
+                j = i + 1
+                while j < len(lines) and re.match(r"^[ \t]+-\s*(.*)$", lines[j]):
+                    items.append(re.match(r"^[ \t]+-\s*(.*)$", lines[j]).group(1).strip())
+                    j += 1
+                if items:
+                    val = "[" + ", ".join(items) + "]"
+                    i = j - 1
+            fm[key] = val
+        i += 1
     return fm
```

**3b. `slug()` README fix** — same fix as PATCH-2, on the `lint.py` side:

```diff
@@ -61,6 +100,8 @@ def load_taxonomy(schema_path):
 
 
 def slug(path):
+    if path.name == "README.md":
+        return path.parent.name
     return path.stem
```

**3c. `overview.md`/`index.md` as valid wikilink targets.** These two
root-level singletons live outside `WIKI_DIRS` (`entities`, `concepts`,
`comparisons`, `queries`), so `[[overview]]`/`[[index]]` links to them
false-flagged as broken. Registered them in the `slugs` map without routing
them through the full per-page pipeline (frontmatter/tag/orphan/index
checks — they're structural, not content pages).

```diff
--- a/skills/llm-wiki-pm/scripts/lint.py
+++ b/skills/llm-wiki-pm/scripts/lint.py
@@ -170,6 +211,14 @@ def main():
             pages.append(p)
 
     slugs = {slug(p): p for p in pages}
+    # root-level architecture singletons (overview.md, index.md) are valid
+    # [[wikilink]] targets but live outside WIKI_DIRS — don't run them through
+    # the full page pipeline (frontmatter/tag/orphan/index checks), just make
+    # links to them resolve.
+    for root_name in ("overview.md", "index.md"):
+        root_p = wiki / root_name
+        if root_p.exists():
+            slugs.setdefault(slug(root_p), root_p)
     taxonomy = load_taxonomy(wiki / "SCHEMA.md")
```

**3d. Escaped-bracket detection + `--auto-fix`.** New check for the
recurring `wiki-search` MCP bug (`@wirux/mcp-markdown-vault`, filed upstream
at `wirux/mcp-markdown-vault#47`) whose `string_replace`/`frontmatter_set`
AST round-trip re-escapes `[` → `\[` across a whole file on write — corrupting
double-square-bracket wikilinks and `## [date]` log headers, breaking link resolution and
backlink detection until caught by false-orphan lint warnings. This recurred
three times in the source wiki's history (2026-08-05, then twice more on
2026-08-11) before the check existed.

Detects a stray backslash before any open-bracket in every page under
`entities/`, `concepts/`, `comparisons/`, `queries/`, plus the root
singletons `log.md`, `overview.md`, `index.md`, `MY-INTEGRATIONS.md`
(these sit outside `WIKI_DIRS` so need a separate pass). Flagged 🔴 (same
tier as broken links, since the effect is the same); `--auto-fix` repairs by
stripping the backslash.

**Known limitation (resolved by PATCH-3e):** the original fix was a global
`\[` → `[` substitution with no way to distinguish corruption from a
deliberate literal `\[` in prose (e.g. quoting a shell/regex command). That
gap stopped being theoretical the moment this page existed — its own diff
hunks quote 11 literal `\[` characters as real source being documented, and
`--auto-fix` would have silently corrupted every one of them. See PATCH-3e,
directly below, for the fenced-code-block and inline-code-span guard that
fixes this properly.

```diff
--- a/skills/llm-wiki-pm/scripts/lint.py
+++ b/skills/llm-wiki-pm/scripts/lint.py
@@ -20,6 +20,30 @@ TAG_LINE_RE = re.compile(r"tags:\s*\[(.*?)\]")
 TAXONOMY_TAG_RE = re.compile(r"^- `([a-z0-9\-]+)`", re.MULTILINE)
 INLINE_PROVENANCE_RE = re.compile(r"\[source:", re.IGNORECASE)
 
+# Interim workaround for the recurring wiki-search MCP bug that re-escapes
+# `[` -> `\[` on write (wikilinks, `## [date]` log headers), until the
+# upstream fix lands (wirux/mcp-markdown-vault#47). Global `\[` -> `[` is
+# safe: empirically the only literal `\[` this wiki has ever contained
+# outside this bug was one line of prose quoting a sed command describing
+# the bug itself — everywhere else it's corruption.
+ESCAPED_BRACKET_RE = re.compile(r"\\\[")
+
+
+def find_escaped_brackets(rel_path, text, auto_fix):
+    """Detect/repair escaped-bracket corruption. Returns (text, note-or-None)."""
+    count = len(ESCAPED_BRACKET_RE.findall(text))
+    if not count:
+        return text, None
+    if auto_fix:
+        return (
+            ESCAPED_BRACKET_RE.sub("[", text),
+            f"de-escaped {count} corrupted '\\[' -> '[' in {rel_path}",
+        )
+    return text, (
+        f"{count} escaped bracket(s) (\\[ -> [ corruption): {rel_path} — "
+        f"run lint --auto-fix"
+    )
+
 # Grounding / freshness (anti-self-reinforcement). A wiki that only cites its own
 # pages drifts from reality. Sources pointing back into these dirs are secondhand;
 # a knowledge page needs at least one PRIMARY source (raw/, external/, web,
```

```diff
--- a/skills/llm-wiki-pm/scripts/lint.py
+++ b/skills/llm-wiki-pm/scripts/lint.py
@@ -184,8 +233,29 @@ def main():
     intentional_stubs = set()  # lifecycle: stub-intentional — exempt from orphan nag
     shareable_pages = []  # export allowlist (private-by-default model)
 
+    # escaped-bracket corruption also hits root-level singletons (log.md,
+    # overview.md, index.md, MY-INTEGRATIONS.md), which sit outside WIKI_DIRS
+    # and never pass through the per-page loop below.
+    for root_name in ("log.md", "overview.md", "index.md", "MY-INTEGRATIONS.md"):
+        root_p = wiki / root_name
+        if not root_p.exists():
+            continue
+        root_text = root_p.read_text()
+        fixed_root_text, root_note = find_escaped_brackets(
+            root_name, root_text, auto_fix
+        )
+        if root_note:
+            (fixes_applied if auto_fix else errors).append(root_note)
+            if auto_fix:
+                root_p.write_text(fixed_root_text)
+
     for p in pages:
         text = p.read_text()
+        text, escape_note = find_escaped_brackets(p.relative_to(wiki), text, auto_fix)
+        if escape_note:
+            (fixes_applied if auto_fix else errors).append(escape_note)
+            if auto_fix:
+                p.write_text(text)
         fm = parse_frontmatter(text)
 
         if fm is None:
```

**3e. fenced-block + inline-code-span guard for the escaped-bracket check**: follow-up patch to `skills/llm-wiki-pm/scripts/lint.py`, landed in its own commit (`79c9f3b`) on top of PATCH-3d rather than folded into it, so the check's history stays legible as "add check, then fix its known gap."

**Problem:** raised while this page still lived in the source wiki — "what if
`lint --auto-fix` is run, will the errors in [this] page get 'fixed' when they
shouldn't?" PATCH-3d's own "Known limitation" note (above) predicted the
failure mode; this page was the concrete instance of it.
`find_escaped_brackets()` did a literal-text `\[` → `[` substitution with no
Markdown awareness, so it flagged all 11 literal `\[` characters quoted in the
diff hunks above as corruption. `--auto-fix` would have de-escaped them,
silently corrupting the quoted source — defeating this page's entire
byte-for-byte-fidelity purpose.

**Fix:** add `_fenced_ranges()` (tracks ` ``` ` fence open/close line by
line) and `_inline_code_ranges()` (single-backtick spans, skipping any
already covered by a fenced range so fence delimiters aren't double-matched),
then filter `ESCAPED_BRACKET_RE` matches against both before counting or
auto-fixing.

**Verification:** ran against the source wiki before and after. Escaped-bracket
errors on this page: 11 → 0 (8 caught by the fence guard alone; the
remaining 3 — in this page's own prose, quoting the bug in inline code
spans — needed the inline-code guard too). The two remaining
double-square-bracket-shaped broken-link errors on this page were a separate,
unfenced check — left alone, since the task that produced this patch was
scoped to the escaped-bracket check only.

```diff
--- a/skills/llm-wiki-pm/scripts/lint.py
+++ b/skills/llm-wiki-pm/scripts/lint.py
@@ -22,21 +22,64 @@ INLINE_PROVENANCE_RE = re.compile(r"\[source:", re.IGNORECASE)
 
 # Interim workaround for the recurring wiki-search MCP bug that re-escapes
 # `[` -> `\[` on write (wikilinks, `## [date]` log headers), until the
-# upstream fix lands (wirux/mcp-markdown-vault#47). Global `\[` -> `[` is
-# safe: empirically the only literal `\[` this wiki has ever contained
-# outside this bug was one line of prose quoting a sed command describing
-# the bug itself — everywhere else it's corruption.
+# upstream fix lands (wirux/mcp-markdown-vault#47). Matches inside fenced
+# ```code blocks``` are skipped (see _fenced_ranges) — those are quoted
+# source that may legitimately contain literal `\[`, e.g. a page documenting
+# a diff.
 ESCAPED_BRACKET_RE = re.compile(r"\\\[")
 
+FENCE_LINE_RE = re.compile(r"^\s*```")
+INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
+
+
+def _fenced_ranges(text):
+    """Char-offset (start, end) ranges covering fenced ```...``` blocks
+    (fence lines included). Content inside is quoted source, not prose."""
+    ranges = []
+    offset = 0
+    fence_start = None
+    for line in text.splitlines(keepends=True):
+        if FENCE_LINE_RE.match(line):
+            if fence_start is None:
+                fence_start = offset
+            else:
+                ranges.append((fence_start, offset + len(line)))
+                fence_start = None
+        offset += len(line)
+    return ranges
+
+
+def _inline_code_ranges(text, fenced):
+    """Char-offset ranges covering single-backtick inline code spans, e.g.
+    `\\[`. Spans already inside a fenced block are skipped so fence
+    delimiters aren't double-matched."""
+    ranges = []
+    for m in INLINE_CODE_RE.finditer(text):
+        if any(start <= m.start() < end for start, end in fenced):
+            continue
+        ranges.append((m.start(), m.end()))
+    return ranges
+
 
 def find_escaped_brackets(rel_path, text, auto_fix):
-    """Detect/repair escaped-bracket corruption. Returns (text, note-or-None)."""
-    count = len(ESCAPED_BRACKET_RE.findall(text))
+    """Detect/repair escaped-bracket corruption. Returns (text, note-or-None).
+    Ignores matches inside fenced code blocks and inline `code spans` —
+    quoted source may legitimately contain a literal '\\['."""
+    fenced = _fenced_ranges(text)
+    protected = fenced + _inline_code_ranges(text, fenced)
+    matches = [
+        m for m in ESCAPED_BRACKET_RE.finditer(text)
+        if not any(start <= m.start() < end for start, end in protected)
+    ]
+    count = len(matches)
     if not count:
         return text, None
     if auto_fix:
+        new_text = text
+        for m in reversed(matches):
+            new_text = new_text[: m.start()] + "[" + new_text[m.end() :]
         return (
-            ESCAPED_BRACKET_RE.sub("[", text),
+            new_text,
             f"de-escaped {count} corrupted '\\[' -> '[' in {rel_path}",
         )
     return text, (
         f"{count} escaped bracket(s) (\\[ -> [ corruption): {rel_path} — "
         f"run lint --auto-fix"
     )
```

### PATCH-4 — `skills/llm-wiki-pm/SKILL.md` + `skills/llm-wiki-persona/SKILL.md`: wire relationship-map update into entity-promotion scan

**Problem:** promoting a person to their own entity page (core skill §2⑫)
never triggered a `concepts/relationship-map.md` update in the source wiki.
The map's own doc (`llm-wiki-persona/SKILL.md`) said "update whenever a new
person entity is added," but nothing actually called that out as part of the
promotion step — it only got updated when someone was already in a
persona-building session, or asked directly. Concretely: two direct reports
were promoted 2026-08-28 during a coverage audit, and the map sat stale until
manually caught and fixed 2026-08-29.

**Fix:** two doc-only edits, no script logic changed.

```diff
--- a/skills/llm-wiki-pm/SKILL.md
+++ b/skills/llm-wiki-pm/SKILL.md
@@ -232,7 +232,10 @@ In brief:
 ⑩ Report every file touched; confirm before mass-updating (10+ pages).
 ⑪ **Crystallize** transcripts/research chains into a `queries/` digest (`references/crystallize-guide.md`).
 ⑫ **Entity promotion scan** — promote people/companies/products with 3+ attributes
-   to their own page (confirm first). Offer a persona page (`llm-wiki-persona`) for any promoted person.
+   to their own page (confirm first). Offer a persona page (`llm-wiki-persona`) for any promoted person. If the promoted entity is a person, update
+   `concepts/relationship-map.md`: create it (per SCHEMA.md's 3+ person-entity
+   rule) if it doesn't exist yet, or add the new person's org-chart row and
+   reflect them under their manager's `direct_reports` cell if it does.
 
 ### 3. Query
 ① **Search first**: `view(action=semantic_search)` → grep → file read.
```

```diff
--- a/skills/llm-wiki-persona/SKILL.md
+++ b/skills/llm-wiki-persona/SKILL.md
@@ -104,7 +104,9 @@ updated: YYYY-MM-DD
 | [[lead-pm]] | [[data-team]] | roadmap input | weekly |
```

-Update whenever a new person entity is added. Link to it from each person entity page.
+Update whenever a new person entity is added — this is triggered automatically
+by the core skill's entity-promotion scan (§2⑫), not a separate manual step.
+Link to it from each person entity page.
 
 Interaction frequency values:
 - `daily`: regular async chat or daily syncs


**Verification:** not yet re-tested end-to-end against a fresh promotion (the
fix landed after the earlier gap was manually corrected, not before it
recurred) — flagged as an open question below.

### Re-application checklist against a newer plugin version

1. Diff the new version's `lint.py`/`backlinks.py`/`session-stop.sh` against
   `2.21.0`'s originals first — if the upstream author fixed any of these
   independently, that patch is now redundant, not conflicting.
2. PATCH-3a/3b/3c, PATCH-1, and PATCH-2 are small, self-contained hunks —
   low risk even if line numbers shifted; reapply by hand if `git apply`
   fails on context.
3. PATCH-3d (escaped-bracket check) and PATCH-3e (its fenced-block /
   inline-code guard) are the largest and most likely to still be needed,
   since their root cause (`wirux/mcp-markdown-vault#47`) is a separate
   upstream project the plugin merely depends on — check that issue's status
   before reapplying; if fixed upstream in the MCP server, both become
   optional cleanup rather than load-bearing. Apply 3d first — 3e's hunks
   are context-dependent on it.
4. After reapplying, run `lint.py <wiki_path>` then `lint.py <wiki_path>
   --auto-fix` against a representative wiki to confirm 0E 0W, same as the
   verification done when these patches first landed.
5. PATCH-4 is doc-only (`SKILL.md` prose in both `llm-wiki-pm` and
   `llm-wiki-persona`) — no script logic, so `git apply` context is unlikely
   to shift much; reapply by hand if the surrounding §2 numbering changed
   upstream.

### Open questions

- Should PATCH-3a (block-style YAML), PATCH-3b/PATCH-2 (README slug), and
  PATCH-3c (overview/index as link targets) be filed as issues or a PR
  against `github.com/anh-chu/llm-wiki-pm`? They read as genuine bugs rather
  than environment-specific preferences (unlike the `session-stop.sh`
  disable, which is specific to the source wiki's hosting environment's
  `SessionEnd` firing behavior). PATCH-3d is an interim workaround for a bug
  in a *different* upstream project (`wirux/mcp-markdown-vault`) and
  wouldn't apply as-is to the `llm-wiki-pm` repo, though the underlying need
  might be worth a mention in `llm-wiki-pm`'s own issue tracker as a "known
  dependency bug" note.
- No `.claude/roles/` or other environment-specific config was checked for
  whether the `SessionEnd`-fires-per-backend-session behavior (motivating
  PATCH-1) is specific to that hosting environment or general — unconfirmed
  gap.
- PATCH-4 hasn't been verified against a live re-run of the entity-promotion
  scan — it was written and committed after manually fixing the gap it
  targets, not proven by watching the next promotion pick it up
  automatically. Worth confirming next time a person entity is promoted.
- Same open question as PATCH-3a/3b/3c applies to PATCH-4: worth
  upstreaming as a PR against `github.com/anh-chu/llm-wiki-pm`? It's a
  small, generally useful doc fix (closes a real staleness gap, not
  environment-specific), unlike PATCH-1.
  <!-- Corrected 2026-08-30: previously misreferenced as "Patch 6", which
  was never defined anywhere in this doc — description matches PATCH-4. -->

### Process decisions

Committed the four original patches locally (commit `4b74c51`), then the
PATCH-3e follow-up as a separate commit (`79c9f3b`) rather than squashing
it in, so the escaped-bracket check's history stays legible as "add check,
then fix its known gap" — rather than leaving either as an uncommitted
working-tree diff, on the reasoning that a commit is more durable against
accidental loss (`git clean`, a bad checkout) even though it does not
survive a plugin version update on its own — re-application still requires
the checklist above. Decided not to file upstream yet; flagged as an open
question rather than a firm no.

Committed PATCH-4 locally (commit `f7faab5`) the same day it was written,
following the established pattern rather than leaving it as a working-tree
diff. Ported to this clone (`~/Projects/llm-wiki-pm`) as of this relocation.

Forked `anh-chu/llm-wiki-pm` to `bzlightyear/llm-wiki-pm` rather than a
plain clone: not for merge mechanics (a clone tracks `origin` fine on its
own), but because there's no write access to the upstream repo, so a fork
is the only remote to push patch commits to — a durable backup outside the
plugin-cache directory the installer can orphan on the next version bump,
and a clean path to open PRs for the patches flagged as candidates above
(3a/3b/3c) if that's decided later.


----
## Open Issues

Design/workflow gaps found while auditing the plugin's own guidance and
this wiki's usage of it. Not plugin-code patches — see "About this
document" above — so nothing here is applied; each entry states what's
still blocking a fix.

### ISSUE-1 — Action Items/Open Questions readability has no update mechanism

**Status:** open, no fix proposed.

_Surfaced 2026-08-30 auditing `llm-wiki-pm`'s crystallize/update-flow
design, prompted by a readability complaint about `pm-wiki/overview.md`'s
Action Items/Open Questions bullets._

**Symptom — readability.** Bullets under Active Bets / Action Items / Open
Questions in `pm-wiki/overview.md` accrete inline `**Update YYYY-MM-DD**:
...` clauses over time with no visual separation, turning into single
unreadable run-on paragraphs (worst examples: daily-granularity forecasting
bullet, AI-planning-wedge bullet, CFP MCP integration bullet — each carrying
3-4 rounds of embedded updates).

**Symptom — inconsistent update-tag formatting.** The inline update markers
vary in shape: `**Update DATE (context)**`, `**Resolved DATE**`, `**New
DATE**`, `**Correction DATE**`, plain `**Confirmed DATE:**` — no single
scannable pattern.

**Symptom — template drift.** `skills/llm-wiki-pm/templates/overview.md`
only defines Current State / Active Bets / Open Questions / Recent Shifts /
Key Entities — it has no Action Items section at all. pm-wiki's actual
`overview.md` grew a full Action Items section organically, outside the
template. The template's own guidance for Active Bets/Open Questions ("one
line each, link to concept page") already prescribes the compact format —
actual usage has drifted far from it.

**Root cause — this is the deepest finding, and the reason the symptoms
above exist in the first place.**

- **Crystallize pages are point-in-time by design.** `crystallize-guide.md`'s
  workflow is entirely creation-oriented; its "update affected pages" step
  (§⑤) lists entity/concept/roadmap pages but never the crystallize page
  itself. `update-guide.md`'s revision/sweep discipline never targets
  `queries/`/crystallize pages either. Architecturally they're mutable
  (Layer 2), but no workflow step ever revisits one after creation.
- **Decisions do have a designated living home**: the topic's concept/entity
  page, kept current via the standard Update flow (three-way search,
  diff-before-write, dated history, logged).
- **Actions do not.** "Roadmap pages" is named once (`crystallize-guide.md`)
  as a place action items should also land, but it isn't a real page type
  in `SCHEMA.md`/`WIKI_DIRS` — no structural convention, no status-field
  discipline. The concrete pm-wiki instance of this pattern is
  [`../pm-wiki/concepts/cfp-q3-q4-roadmap-planning.md`](../pm-wiki/concepts/cfp-q3-q4-roadmap-planning.md) —
  a `type: concept` page (tags: `roadmap, cfp`) that tracks the CFP
  planning process/meta-decisions across 11 sources, exactly the informal
  "roadmap page" role the guide gestures at without ever formalizing.
- **Empirically verified in pm-wiki**: spot-checked 3 crystallize pages'
  Action Items tables — all Status cells frozen at their creation-time value
  (mostly "pending"), even for items `overview.md` itself separately marked
  resolved weeks later. Concrete example: `crystallize-cfp-coord-sync-2026-08-05.md`
  still shows "Post in Ask CFP / SME Slack... — Status: pending," while
  `overview.md` (line 261-263) shows the same item `~~done 2026-08-08~~`.
- **Consequence**: `overview.md`'s Action Items section — itself outside the
  official template — has become the de facto action-item tracker by
  default, because `ingest-guide.md` §⑦ is the only workflow step that
  reliably sends anyone back to touch it. The unreadable accretion above is
  that page compensating for a missing update mechanism elsewhere in the
  design, not just a formatting choice that drifted for no reason.

**Implication for a fix.** Naively compressing Action Items/Open Questions
bullets to one line + "see crystallize page" would not just drop history —
it would **regress the accuracy of the current-status signal**, since the
crystallize page it points to is stale/frozen and `overview.md`'s inline
text is currently the only accurate record of what's actually resolved. A
safe fix needs one of:
- a real status-sync step added to the update/crystallize workflow so the
  linked page becomes trustworthy before overview.md stops carrying status
  inline, or
- explicitly treating overview.md's compressed line as the source of truth
  itself (link out only for rationale/history, not current status).

### ISSUE-2 — `worker-wiki-indexer`'s Overview Regeneration mode: latent, dormant risk

**Status:** open, no fix proposed — currently mitigated only by never firing.

- If ever triggered (overview.md >7 days stale + `log.md` shows activity
  since), it wipes everything in `overview.md` below the intro paragraph and
  replaces it with auto-generated Theme Clusters / Coverage / Recent
  Activity / Known Gaps / Stats sections — which bear no resemblance to the
  hand-curated Active Bets/Action Items/Open Questions/Recent Shifts
  structure actually in use.
- Confirmed dormant: nothing wires this agent into any automatic trigger
  (not `session-start.sh`, not `session-stop.sh`, not `llm-wiki-maintain`'s
  daily loop, which only runs `lint.py` for its health check). It's a
  manual/judgment call per `product-manager.md`'s role guidance ("use after
  large ingests"). Grepped pm-wiki's `log.md` (327 entries) for its mandated
  output line — zero hits. It has never once run in this wiki's history.
- Also gated by staleness: `overview.md`'s `updated:` frontmatter stays
  fresh via near-daily manual edits (`ingest-guide.md` §⑦), so the 7-day
  threshold rarely trips even if someone did invoke it.

### ISSUE-3 — `[source: user, conversation, <date>]` citations aren't verified against `raw/` — and drift silently from the body Sources legend

**Status:** open, no fix proposed.

_Surfaced 2026-08-30, same session as ISSUE-1/ISSUE-2, while explaining
`hooks/pre-write.sh`'s freshness gate to the user, who then spotted the gap
firsthand in a live page._

**Problem, part A — missing raw file.** `ingest-guide.md:38-43` mandates
that a "current conversation" source (`user says "from this conversation"`)
gets a backing capture at `raw/internal/conversation-<YYYY-MM-DD>.md`, with
user-stated facts attributed inline as `[source: user, conversation, <date>]`.
In `pm-wiki/concepts/cfp-q3-q4-roadmap-planning.md`, this format is used
twice — `"conversation, 2026-08-13"` and `"conversation, 2026-08-21"`, both
in frontmatter `sources:` and as inline markers (lines 64, 77) — but neither
`raw/internal/conversation-2026-08-13.md` nor `raw/internal/conversation-2026-08-21.md`
exists, nor ever did (checked `pm-wiki`'s git history for deletions: none).
The citation string looks grounded but resolves to nothing on disk.

**Problem, part B — frontmatter/body Sources drift.** The same page's body
`## Sources` legend lists the 2026-08-13 conversation entry but not the
2026-08-21 one, even though both are in frontmatter and both have inline
markers. Diffing against the hook's own pre-edit snapshot
(`pm-wiki/_archive/cfp-q3-q4-roadmap-planning-2026-08-21.md`) shows the
08-21 entry was never added when that day's edit introduced the citation —
and the gap survived six subsequent edits (08-25, 08-26 ×2, 08-27 ×2, 08-28)
untouched.

**Root cause — no automated check covers either gap.** `hooks/pre-write.sh`'s
freshness gate (lines 91-97) only checks that *some* primary source or
inline marker exists anywhere on the page; it has no way to confirm a cited
`raw/`-slug or `"conversation, <date>"` string actually resolves to a file.
`lint.py`'s provenance check (~lines 210-219, 352-376) only confirms
`sources:` exists and that at least one inline `[source:]` marker appears
somewhere in the body — it never diffs the frontmatter list against the body
Sources section, and never verifies a referenced raw file exists. Same
underlying pattern as ISSUE-1: a citation, once written, has no workflow
step that revisits or verifies it.

**Not yet decided:** whether the fix belongs in `lint.py` (a new check:
every frontmatter/inline source either resolves to a `raw/` file or is
exempted as `user, conversation, <date>` *only if* the matching
`raw/internal/conversation-<date>.md` exists; plus a frontmatter-vs-body-Sources
diff check) or in `hooks/pre-write.sh` (block/warn at write-time instead of
lint-time). Flagged here, not implemented.

----

## Sources

_Covers Applied Patches provenance only — Open Issues evidence is cited
inline within each ISSUE-N entry above rather than listed here._

- Local git repo: `~/.claude/plugins/cache/anh-chu-plugins/llm-wiki-pm/2.21.0`,
  commits `4b74c51c136f9b0780646b479fdc0cbde4b26a56` and
  `79c9f3bb95a938989ceae651085895165ac1decd`, captured 2026-08-11 via
  `git show` and `git diff`
- Local git repo, same path, commit `f7faab5e7cb53f350fe5ad6217cc082af4457cca`
  (PATCH-4), captured 2026-08-29 via `git diff` before committing
- All five patches ported from the plugin-cache repo onto this source clone
  (`~/Projects/llm-wiki-pm`, single commit, all patches bundled — unlike the
  plugin-cache repo's two-commit split), then this clone forked to
  `github.com/bzlightyear/llm-wiki-pm` (`gh repo fork --remote`) and pushed
  as commit `dfdd98c` (patches) plus `1e74e9f` (`.gitignore` cleanup,
  unrelated to the patches themselves). Verified 2🔴/1🟡 against a test wiki
  from this clone's own copy of `lint.py`, matching the plugin-cache repo's
  baseline; `--auto-fix` confirmed non-destructive on a throwaway copy.
