#!/usr/bin/env bash
# post-validate.sh
# Runs AFTER a write to the wiki: Write/Edit/MultiEdit, and the wiki-search
# MCP's `vault` (create/create_from_template/update) and `edit` tools.
# Re-reads each written page and checks it with lint's own functions:
# - frontmatter (I1: R1, R2, R5, R12, missing frontmatter or required keys),
#   sources: entries (I2: R6), citations (I3: R3), the citation grammar (R7),
#   escaped \[ and broken [[wikilinks]], against lint's page set;
# - the freshness gate for the writes pre-write.sh can't judge beforehand
#   (MCP create_from_template and edit);
# - a split reminder when the write takes a page over 200 lines.
# Reports up to 6 lines as additionalContext in the same turn, and appends
# the problems (not the reminders) to _status.md.
# Non-blocking: never denies, always exits 0.
# Hook type: PostToolUse in Claude Code, synchronous (its output must reach
# the agent in the same turn).
# Input: JSON on stdin with tool_name, tool_input and tool_response fields.

set -euo pipefail

# ── Resolve wiki path (must match session-start.sh) ──────────────────────────
FILE_WIKI=$(cat "$(pwd)/.wiki-path" 2>/dev/null | tr -d '[:space:]' || true)
WIKI="${FILE_WIKI:-${CLAUDE_PLUGIN_OPTION_wiki_path:-${WIKI_PATH:-}}}"
[[ -z "$WIKI" ]] && exit 0

SCRIPTS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../skills/llm-wiki-pm/scripts" && pwd)"
INPUT=$(cat)

python3 - "$INPUT" "$WIKI" "$SCRIPTS" <<'PY' || true
import json, os, re, sys
from datetime import datetime
from pathlib import Path

raw, wiki, scripts = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    data = json.loads(raw)
except Exception:
    sys.exit(0)

sys.dont_write_bytecode = True  # don't leave __pycache__ in the plugin dir
sys.path.insert(0, scripts)
import lint
import wikifm

tool = data.get("tool_name") or ""
ti = data.get("tool_input") or {}
tr = data.get("tool_response")
tr = tr if isinstance(tr, dict) else {}

# Which vault paths the write touched; must match pre-write.sh. `kind` is the
# tool name for Write/Edit/MultiEdit, the action for MCP vault, and
# "mcp_edit" for the MCP edit tool. MCP paths are vault-relative.
if re.match(r"^mcp__.*wiki-search__vault$", tool):
    kind = ti.get("action")
    if kind not in ("create", "create_from_template", "update"):
        sys.exit(0)  # reads, and delete, which leaves nothing to check
    targets = [os.path.join(wiki, ti.get("path") or "")]
elif re.match(r"^mcp__.*wiki-search__edit$", tool):
    if ti.get("dryRun"):
        sys.exit(0)  # preview only, writes nothing
    kind = "mcp_edit"
    ops = ti.get("operations") or [{"path": ti.get("path") or ""}]
    targets = [os.path.join(wiki, op.get("path") or "") for op in ops]
else:
    kind = tool
    targets = [ti.get("file_path") or ""]

# Lint checks these root files for escaped \[ only; they aren't pages.
ROOT_FILES = ("log.md", "overview.md", "index.md", "MY-INTEGRATIONS.md")
WIKI_PREFIXES = ("entities/", "concepts/", "comparisons/", "queries/")
MAX_LINES = 6
SPLIT_LINES = 200

wiki_real = Path(os.path.realpath(os.path.abspath(wiki)))
_index = {}


def index():
    """Lint's page set and {ID: [paths]} over records and pages, built once."""
    if not _index:
        pages = lint.wiki_pages(wiki_real)
        slugs = {lint.slug(p) for p in pages}
        for root_name in ("overview.md", "index.md"):
            if (wiki_real / root_name).exists():
                slugs.add(lint.slug(root_name))
        _index.update(pages=set(pages), slugs=slugs,
                      files=lint.source_index(wiki_real, pages))
    return _index


def lines_before(text):
    """The page's line count before this write, or None when the payload
    doesn't say. Edit and MultiEdit give it by their line delta; a new file
    had none. Claude Code's PostToolUse input carries no pre-image."""
    if kind in ("create", "create_from_template"):
        return 0
    if kind == "Write":
        created = tr.get("status") == "created" or tr.get("type") == "create"
        return 0 if created else None
    if kind not in ("Edit", "MultiEdit"):
        return None
    delta = 0
    for e in [ti] if kind == "Edit" else (ti.get("edits") or []):
        old, new = e.get("old_string") or "", e.get("new_string") or ""
        if not old:
            return 0  # an Edit with an empty old_string creates the file
        d = new.count("\n") - old.count("\n")
        if d and e.get("replace_all"):
            return None  # how many places it replaced isn't known
        delta += d
    return text.count("\n") - delta


def ungrounded(text, fm):
    """pre-write.sh's freshness gate: no primary source and no inline marker."""
    if wikifm.str_field(fm, "lifecycle") == "dated-digest":
        return False
    primary = [s for s in wikifm.sources(fm) if s and not s.startswith(WIKI_PREFIXES)]
    return not (primary or re.search(r"\[source:", text, re.IGNORECASE))


def check_page(page, rel, text):
    """(problems, reminders) for one page, problems in lint's own words."""
    problems, reminders = [], []
    idx = index()
    fm, fm_errors = wikifm.parse(text)
    if fm is None:
        problems.append(f"missing frontmatter (R12): {rel}")
    else:
        m = lint.FRONTMATTER_RE.match(text)
        if m:
            problems.extend(lint.check_frontmatter_structure(rel, m.group(1)))
        note = lint.check_frontmatter_profile(rel, fm, fm_errors)
        if note:
            problems.append(note)
        missing = lint.REQUIRED_FRONTMATTER - set(fm.keys())
        if missing:
            problems.append(f"frontmatter missing {sorted(missing)} (R12): {rel}")
        if page.stem not in lint.GROUNDING_EXEMPT_STEMS:
            srcs = wikifm.sources(fm)
            note, _ = lint.check_sources(rel, srcs, wiki_real, idx["files"])
            if note:
                problems.append(note)
            prov = lint.check_provenance_cross_reference(rel, text, srcs, idx["files"])
            problems.extend(w for w in prov["warnings"] if "(R3)" in w)
            body = text[m.end():] if m else text
            note = lint.check_citation_grammar(rel, wikifm.citations(body), idx["files"])
            if note:
                problems.append(note)
    _, note = lint.find_escaped_brackets(rel, text, False)
    if note:
        problems.append(note)
    broken = dict.fromkeys(
        t.strip() for t in lint.WIKILINK_RE.findall(text) if t.strip() not in idx["slugs"]
    )
    if broken:
        problems.append(
            f"{len(broken)} broken [[wikilink]](s): {rel} — "
            + ", ".join(f"[[{t}]]" for t in broken)
        )

    if kind in ("create_from_template", "mcp_edit") and fm is not None and ungrounded(text, fm):
        reminders.append(
            f"freshness gate: {rel} has no primary source and no inline [source:] "
            f"marker — sweep connected tools, capture what you find to raw/ and cite "
            f"it; with no tools, mark coverage: stub and list unknowns in gaps:"
        )
    n = text.count("\n")
    before = lines_before(text)
    if n > SPLIT_LINES and (before is None or before <= SPLIT_LINES):
        reminders.append(f"page is now {n} lines (> {SPLIT_LINES}): {rel} — {lint.SPLIT_POINTER}")
    return problems, reminders


problems, reminders, by_page = [], [], []
for fp in dict.fromkeys(targets):
    if not fp.endswith(".md"):
        continue
    abs_fp = Path(os.path.realpath(os.path.abspath(fp)))
    try:
        rel = abs_fp.relative_to(wiki_real).as_posix()
    except ValueError:
        continue  # outside the wiki
    if not abs_fp.is_file():
        continue
    try:
        text = abs_fp.read_text()
    except (OSError, UnicodeDecodeError):
        continue
    if rel in ROOT_FILES:
        _, note = lint.find_escaped_brackets(rel, text, False)
        p, r = ([note] if note else []), []
    elif abs_fp in index()["pages"]:
        p, r = check_page(abs_fp, rel, text)
    else:
        continue  # raw/ records, _archive/, lint reports, assets/, other files
    problems += p
    reminders += r
    if p:
        by_page.append((rel, p))

lines = reminders + problems
if not lines:
    sys.exit(0)
if len(lines) > MAX_LINES:
    more = len(lines) - (MAX_LINES - 1)
    lines = lines[:MAX_LINES - 1] + [f"…and {more} more — run lint.py for the full list"]
header = "Post-write check (rules and fixes: references/citation-spec.md):"
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": "\n".join([header] + [f"- {l}" for l in lines]),
    }
}))

# Record the problems in _status.md, as post-write.sh did for broken links.
# session-start.sh rewrites the file each session.
if by_page:
    status = wiki_real / "_status.md"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    out = [] if status.exists() else ["# Wiki Status", ""]
    out += ["", "## Recent Write Issues", ""]
    for rel, p in by_page:
        out += [f"**[{now}] write | {lint.slug(rel)}**", ""]
        out += [f"  - {l}" for l in p]
        out.append("")
    try:
        with status.open("a") as f:
            f.write("\n".join(out) + "\n")
    except OSError:
        pass
PY
exit 0
