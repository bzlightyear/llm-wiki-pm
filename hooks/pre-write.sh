#!/usr/bin/env bash
# pre-write.sh
# Runs BEFORE a write to the wiki: Write/Edit/MultiEdit, and the wiki-search
# MCP's `vault` (create/create_from_template/update/delete) and `edit` tools.
# - Snapshots an existing page to _archive/<slug>-<YYYY-MM-DD>.md (lint.py's
#   snapshot()); overview.md only on a whole-file replacement, index.md never.
# - Warns when an existing raw/ record is modified (records are write-once).
# - Freshness gate: if the page as it will be after the write looks ungrounded
#   (no primary source, no inline provenance), injects a reminder to sweep live
#   tools before laundering secondhand mentions into the wiki.
# Non-blocking: emits additionalContext, never denies.
# Hook type: PreToolUse in Claude Code.
# Input: JSON on stdin with tool_name and tool_input fields.

set -euo pipefail

# ── Resolve wiki path (must match session-start.sh) ──────────────────────────
FILE_WIKI=$(cat "$(pwd)/.wiki-path" 2>/dev/null | tr -d '[:space:]' || true)
WIKI="${FILE_WIKI:-${CLAUDE_PLUGIN_OPTION_wiki_path:-${WIKI_PATH:-}}}"
[[ -z "$WIKI" ]] && exit 0

SCRIPTS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../skills/llm-wiki-pm/scripts" && pwd)"
INPUT=$(cat)

python3 - "$INPUT" "$WIKI" "$SCRIPTS" <<'PY' || true
import json, os, re, sys

raw, wiki, scripts = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    data = json.loads(raw)
except Exception:
    sys.exit(0)

sys.dont_write_bytecode = True  # don't leave __pycache__ in the plugin dir
sys.path.insert(0, scripts)
from lint import snapshot

tool = data.get("tool_name") or ""
ti = data.get("tool_input") or {}

# Work out what kind of write this is and which vault paths it touches.
# `kind` is the tool name for Write/Edit/MultiEdit, the action for MCP vault,
# and "mcp_edit" for the MCP edit tool. MCP paths are vault-relative.
if re.match(r"^mcp__.*wiki-search__vault$", tool):
    kind = ti.get("action")
    if kind not in ("create", "create_from_template", "update", "delete"):
        sys.exit(0)  # reads
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

CREATES = {"create", "create_from_template"}
WHOLE_FILE = {"Write", "update", "delete"}          # replaces or removes the file
GATED_BY_FRESHNESS = {"Write", "Edit", "MultiEdit", "create", "update"}
GATED_DIRS = ("entities/", "concepts/", "comparisons/", "queries/", "briefings/")
# Exempt: archives and structural/generated pages.
EXEMPT_DIRS = ("_archive/", "_drafts/", "drafts/")
EXEMPT_STEMS = {"index", "log", "_status", "SCHEMA", "MY-INTEGRATIONS", "overview"}
WIKI_PREFIXES = ("entities/", "concepts/", "comparisons/", "queries/")
DATED_DIGEST_RE = re.compile(r"^lifecycle:\s*['\"]?dated-digest\b", re.MULTILINE)

wiki_real = os.path.realpath(os.path.abspath(wiki))


def read(path):
    try:
        with open(path) as f:
            return f.read()
    except Exception:
        return None


def post_image(abs_fp):
    """The page text as it will be after this write. Write and MCP create/update
    carry it in `content`; Edit and MultiEdit are applied to the disk text."""
    if kind not in ("Edit", "MultiEdit"):
        content = ti.get("content")
        return content if content is not None else (read(abs_fp) or "")
    text = read(abs_fp) or ""
    edits = [ti] if kind == "Edit" else (ti.get("edits") or [])
    for e in edits:
        old, new = e.get("old_string") or "", e.get("new_string") or ""
        if not old:
            text = text or new  # Edit with an empty old_string creates the file
        elif e.get("replace_all"):
            text = text.replace(old, new)
        else:
            text = text.replace(old, new, 1)
    return text


def ungrounded(content):
    """True when the page has no primary source and no inline marker."""
    fm_m = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    srcs = []
    if fm_m:
        if DATED_DIGEST_RE.search(fm_m.group(1)):
            return False  # dated digests summarize the wiki; no sources by design
        lines = fm_m.group(1).splitlines()
        for i, line in enumerate(lines):
            if re.match(r"^sources:", line):
                rest = line.partition(":")[2].strip()
                if rest.startswith("["):
                    srcs += [s.strip().strip("'\"") for s in rest.strip("[]").split(",")]
                for nxt in lines[i + 1:]:
                    if re.match(r"^\s*-\s+", nxt):
                        srcs.append(re.sub(r"^\s*-\s+", "", nxt).strip().strip("'\""))
                    elif re.match(r"^\S", nxt):
                        break
                break
    primary = [s for s in srcs if s and not s.startswith(WIKI_PREFIXES)]
    has_inline = bool(re.search(r"\[source:", content, re.IGNORECASE))
    return not (primary or has_inline)


messages = []
for fp in targets:
    if not fp.endswith(".md"):
        continue
    abs_fp = os.path.realpath(os.path.abspath(fp))
    if not abs_fp.startswith(wiki_real + os.sep):
        continue
    rel = abs_fp[len(wiki_real) + 1:]
    stem = os.path.splitext(os.path.basename(abs_fp))[0]
    exists = os.path.isfile(abs_fp)

    # raw/ records are write-once; new records pass silently.
    if rel.startswith("raw/"):
        if exists and kind not in CREATES and not rel.startswith("raw/assets/"):
            messages.append(
                f"⚠️ Raw record '{rel}' already exists. Records in raw/ are "
                f"write-once: save a new record (note in its body which record "
                f"it replaces) and run an Update (§4) on the pages that cite it."
            )
        continue

    # overview.md: snapshot only a whole-file replacement (daily edits are in
    # git). index.md is derived, so it is never snapshotted.
    if rel == "overview.md":
        if exists and kind in WHOLE_FILE:
            try:
                snapshot(abs_fp, wiki_real)
            except Exception:
                pass
        continue

    if rel.startswith(EXEMPT_DIRS) or stem in EXEMPT_STEMS or stem.startswith("lint-"):
        continue
    if not rel.startswith(GATED_DIRS):
        continue
    # Artifacts under a directory page's assets/ subfolder are not pages.
    if "assets" in rel.split(os.sep)[2:-1]:
        continue

    # Pre-update snapshot: at most one per page per day, best-effort.
    if exists and kind not in CREATES:
        try:
            snapshot(abs_fp, wiki_real)
        except Exception:
            pass

    # MCP edit ops aren't simulated and delete writes nothing: no freshness gate.
    if kind not in GATED_BY_FRESHNESS or not ungrounded(post_image(abs_fp)):
        continue
    messages.append(
        f"⚠️ Freshness gate — '{rel}' is being written with no primary source "
        f"(sources are empty or point only to other wiki pages) and no inline "
        f"[source:] markers. Per the Freshness-first protocol: before writing a "
        f"knowledge page, sweep connected tools (Slack, Gmail, Granola, CRM, web) "
        f"for fresh primary information, capture it to raw/, and anchor claims with "
        f"[source: ...]. Don't build a page from the prose of other wiki pages alone "
        f"— that launders secondhand mentions into false confidence. If no tools are "
        f"connected, mark coverage: stub and list unknowns in gaps:."
    )

if messages:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": "\n\n".join(messages),
        }
    }))
PY
