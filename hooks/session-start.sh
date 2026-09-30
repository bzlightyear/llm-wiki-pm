#!/usr/bin/env bash
# session-start.sh
# Runs at session start (SessionStart event).
# - Scaffolds the wiki on first run if it does not exist
# - Pre-computes wiki health and writes _status.md
# - Outputs a status summary as additionalContext for Claude
# Hook type: SessionStart (fires once per session, not on every prompt)
# Input: JSON on stdin (session_id, source, model, etc.)

set -euo pipefail

# Save stdin (JSON input) for later use
STDIN_JSON=$(cat)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Trust CLAUDE_PLUGIN_ROOT when set (always set during plugin execution).
# Fallback for local dev: script lives at <plugin-root>/hooks/
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
TEMPLATES_DIR="$PLUGIN_ROOT/skills/llm-wiki-pm/templates"
SCRIPTS_DIR="$PLUGIN_ROOT/skills/llm-wiki-pm/scripts"

# ① Resolve wiki path
# Priority: .wiki-path file (project) > CLAUDE_PLUGIN_OPTION_wiki_path (global) > WIKI_PATH env > cwd fallback
WIKI_PATH_FILE="$(pwd)/.wiki-path"
FILE_WIKI=$(cat "$WIKI_PATH_FILE" 2>/dev/null | tr -d '[:space:]' || true)

WIKI="${FILE_WIKI:-${CLAUDE_PLUGIN_OPTION_wiki_path:-${WIKI_PATH:-}}}"
DOMAIN="${CLAUDE_PLUGIN_OPTION_wiki_domain:-PM}"
GLOBAL_WARNING=""
if [[ -z "$WIKI" ]]; then
  WIKI="$(pwd)"
  GLOBAL_WARNING="llm-wiki-pm: no wiki path configured. Falling back to current directory ($WIKI). Run /llm-wiki-pm:set-wiki-path ~/your-path to set a permanent path."
elif [[ -z "$FILE_WIKI" ]]; then
  GLOBAL_WARNING="llm-wiki-pm: using global wiki path ($WIKI). Run /llm-wiki-pm:set-wiki-path ~/your-path from your project directory to set a project-specific path."
fi

# ①b Ensure wiki-search package is in npx cache (background, non-blocking)
# First session after install will use npx (slow); this ensures the cache
# exists for wiki-search.sh's fast path on subsequent runs.
# Fixed-depth glob instead of `find` — find deep-traverses the entire _npx tree
# (can be 100k+ files → multi-second stall); the glob only stats the exact path shape.
_npx_hit=""
for _p in "${HOME}"/.npm/_npx/*/node_modules/@wirux/mcp-markdown-vault/dist/index.js; do
  [[ -e "$_p" ]] && { _npx_hit=1; break; }
done
if [[ -z "$_npx_hit" ]]; then
  npx -y @wirux/mcp-markdown-vault --version &>/dev/null &
fi

# ② Scaffold wiki on first run — only if dir is new or truly empty
# Never overwrite files in an existing non-empty directory.
SCAFFOLD=false
if [[ ! -e "$WIKI" ]]; then
  SCAFFOLD=true
elif [[ -z "$(find "$WIKI" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]; then
  SCAFFOLD=true
elif [[ ! -f "$WIKI/SCHEMA.md" ]]; then
  echo "Warning: $WIKI exists and is non-empty but has no SCHEMA.md. Skipping scaffold to avoid overwriting files." >&2
fi

if [[ "$SCAFFOLD" == true ]]; then
  mkdir -p "$WIKI"
  for subdir in \
    raw/articles raw/papers raw/transcripts raw/internal raw/assets \
    entities concepts comparisons queries _archive; do
    mkdir -p "$WIKI/$subdir"
  done

  TODAY=$(date '+%Y-%m-%d')

  # Copy and customize SCHEMA.md (Python for safe replacement of any domain string)
  python3 -c "
import sys
text = open(sys.argv[1]).read()
text = text.replace('Product management knowledge base.', sys.argv[2] + ' knowledge base.')
text = text.replace('# Wiki Schema, PM', '# Wiki Schema, ' + sys.argv[2])
open(sys.argv[3], 'w').write(text)
" "$TEMPLATES_DIR/SCHEMA.md" "$DOMAIN" "$WIKI/SCHEMA.md"
  sed "s/YYYY-MM-DD/$TODAY/g" "$TEMPLATES_DIR/index.md" > "$WIKI/index.md"
  sed "s/YYYY-MM-DD/$TODAY/g" "$TEMPLATES_DIR/overview.md" > "$WIKI/overview.md"
  {
    cat "$TEMPLATES_DIR/log.md"
    echo ""
    echo "## [$TODAY] create | Wiki initialized"
    echo "- Domain: $DOMAIN"
    echo "- Structure scaffolded automatically by llm-wiki-pm plugin"
  } > "$WIKI/log.md"
fi

# ②b Concurrent session lock
LOCKFILE="$WIKI/.wiki-lock"
LOCK_WARNING=""
if [[ -f "$LOCKFILE" ]]; then
  LOCK_OWNER=$(cat "$LOCKFILE" 2>/dev/null || true)
  LOCK_AGE=0
  if [[ -n "$LOCK_OWNER" ]]; then
    LOCK_TS=$(echo "$LOCK_OWNER" | cut -d: -f2- || true)
    if [[ -n "$LOCK_TS" ]]; then
      LOCK_EPOCH=$(python3 -c "
from datetime import datetime
import sys
try:
    print(int(datetime.fromisoformat(sys.argv[1].replace('Z','+00:00')).timestamp()))
except Exception:
    print(0)
" "$LOCK_TS" 2>/dev/null || echo 0)
      if [[ "$LOCK_EPOCH" -gt 0 ]]; then
        LOCK_AGE=$(( $(date +%s) - LOCK_EPOCH ))
      fi
    fi
  fi
  # Stale lock threshold: 2 hours (session probably crashed)
  if [[ "$LOCK_AGE" -gt 7200 ]]; then
    rm -f "$LOCKFILE"
  else
    LOCK_WARNING="Another wiki session may be active (lock: $LOCK_OWNER). Concurrent writes risk data loss. Proceed with caution or wait for the other session to end."
  fi
fi
# Write our lock
SESSION_ID=$(echo "$STDIN_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('session_id','unknown'))" 2>/dev/null || echo "$$")
echo "${SESSION_ID}:$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$LOCKFILE" 2>/dev/null || true

# ③ Gather health metrics
NOW_TS=$(date +%s)
NOW_FMT=$(date '+%Y-%m-%d %H:%M')
THRESHOLD_STALE=$(( NOW_TS - 30 * 86400 ))
THRESHOLD_DECAY=$(( NOW_TS - 60 * 86400 ))

BROKEN_LINKS=0
ORPHANS=0
BAD_FRONTMATTER=0  # pages breaking I1: frontmatter profile, required keys
BAD_SOURCES=0      # I2: sources: entries that aren't existing files (R6)
BAD_CITATIONS=0    # I3: citations of IDs the page doesn't declare (R3)
SECONDHAND_PAGES=()  # R10: primary sources all conversation or reconstructed records
LINT_OK=false
STALE_PAGES=()
DECAY_PAGES=()

# ④ Run lint (--json writes nothing to the wiki). A crash, a missing lint.py
# or output that isn't lint's JSON is reported as "health unknown", never as
# a clean wiki.
if LINT_OUT=$(python3 "$SCRIPTS_DIR/lint.py" "$WIKI" --quiet --json 2>/dev/null) \
  && LINT_VALUES=$(python3 -c '
import json, sys
d = json.load(sys.stdin)
i = d["invariants"]
print(len(d["broken_links"]), len(d["orphans"]), i["I1"], i["I2"], i["I3"])
for page in d["secondhand"]:
    print(page)
' <<< "$LINT_OUT" 2>/dev/null); then
  LINT_OK=true
  read -r BROKEN_LINKS ORPHANS BAD_FRONTMATTER BAD_SOURCES BAD_CITATIONS <<< "$LINT_VALUES"
  mapfile -t SECONDHAND_PAGES < <(tail -n +2 <<< "$LINT_VALUES")
fi

# ⑤ Scan for stale and decayed pages.
# Single python pass over all pages. Previously a bash loop spawned ~12
# subprocesses per file (basename/grep/sed/tr/xargs/date/awk...); with 100+
# pages that dominated session-start latency (8s+). One python process does the
# same work in-process (~0.2s). Semantics unchanged: stale = updated >30d ago;
# decay = explicit confidence_decay_days elapsed, else competitive-tagged >60d.
# Frontmatter is read with wikifm, the parser lint uses, so a quoted date
# counts like any other.
# (STALE_PAGES / DECAY_PAGES already initialized in ③.)
mapfile -t _SCAN_OUT < <(python3 - "$WIKI" "$NOW_TS" "$THRESHOLD_STALE" "$THRESHOLD_DECAY" "$SCRIPTS_DIR" <<'PYEOF' 2>/dev/null || true
import os, sys
from datetime import datetime
wiki, now_ts, th_stale, th_decay = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
sys.dont_write_bytecode = True  # don't leave __pycache__ in the plugin dir
sys.path.insert(0, sys.argv[5])
import wikifm
for d in ("entities", "concepts", "comparisons"):
    dp = os.path.join(wiki, d)
    if not os.path.isdir(dp):
        continue
    for fn in sorted(os.listdir(dp)):
        if not fn.endswith(".md"):
            continue
        slug = fn[:-3]
        try:
            text = open(os.path.join(dp, fn), encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        fm, _ = wikifm.parse(text)
        updated = wikifm.date_field(fm, "updated")
        if updated is None:
            continue
        uts = int(datetime(updated.year, updated.month, updated.day).timestamp())
        if uts < th_stale:
            print(f"STALE\t{d}/{slug} ({updated})")
        decay_days = wikifm.str_field(fm, "confidence_decay_days")
        if decay_days.isdecimal():
            if uts < now_ts - int(decay_days) * 86400:
                print(f"DECAY\t{d}/{slug} ({updated})")
        elif any("competitive" in t for t in wikifm.list_field(fm, "tags")) and uts < th_decay:
            print(f"DECAY\t{d}/{slug} ({updated})")
PYEOF
)
for _line in "${_SCAN_OUT[@]}"; do
  case "$_line" in
    STALE$'\t'*) STALE_PAGES+=("${_line#STALE$'\t'}") ;;
    DECAY$'\t'*) DECAY_PAGES+=("${_line#DECAY$'\t'}") ;;
  esac
done

STALE_COUNT="${#STALE_PAGES[@]}"
DECAY_COUNT="${#DECAY_PAGES[@]}"
SECONDHAND_COUNT="${#SECONDHAND_PAGES[@]}"
TOTAL=$(( BROKEN_LINKS + ORPHANS + STALE_COUNT + DECAY_COUNT ))
REFERENCE_ISSUES=$(( BAD_FRONTMATTER + BAD_SOURCES + BAD_CITATIONS ))

# A count from lint, or "unknown" when lint failed.
lint_count() {
  if [[ "$LINT_OK" == true ]]; then echo "$1"; else echo "unknown"; fi
}

# ⑥ Write _status.md
STATUS_FILE="$WIKI/_status.md"
{
  echo "# Wiki Status"
  echo ""
  echo "Last checked: $NOW_FMT"
  echo ""
  echo "> ⚠️ Session-start snapshot only — frozen at the timestamp above. Counts go"
  echo "> stale as soon as you create or edit pages this session. For live numbers,"
  echo "> re-run \`lint.py\`; do not quote these figures after a bulk ingest."
  echo ""
  echo "## Health Summary"
  echo ""
  echo "| Metric | Count |"
  echo "|--------|-------|"
  echo "| Broken links | $(lint_count "$BROKEN_LINKS") |"
  echo "| Orphan pages | $(lint_count "$ORPHANS") |"
  echo "| Stale pages (>30 days) | $STALE_COUNT |"
  echo "| Confidence decay (past decay window) | $DECAY_COUNT |"
  echo "| Pages with invalid frontmatter (I1) | $(lint_count "$BAD_FRONTMATTER") |"
  echo "| Pages with unresolved sources (I2) | $(lint_count "$BAD_SOURCES") |"
  echo "| Pages with unresolved citations (I3) | $(lint_count "$BAD_CITATIONS") |"
  echo "| Secondhand, unverified (R10) | $(lint_count "$SECONDHAND_COUNT") |"
  if [[ "$LINT_OK" != true ]]; then
    echo ""
    echo "**lint failed: health unknown.** Run \`lint.py\` to see the error."
  fi

  if [[ "$DECAY_COUNT" -gt 0 ]]; then
    echo ""
    echo "## Confidence Decay Candidates"
    echo ""
    i=0
    for p in "${DECAY_PAGES[@]}"; do
      [[ "$i" -ge 20 ]] && { echo "- (+$(( DECAY_COUNT - 20 )) more)"; break; }
      echo "- $p"; i=$(( i + 1 ))
    done
  fi

  if [[ "$STALE_COUNT" -gt 0 ]]; then
    echo ""
    echo "## Stale Pages"
    echo ""
    i=0
    for p in "${STALE_PAGES[@]}"; do
      [[ "$i" -ge 20 ]] && { echo "- (+$(( STALE_COUNT - 20 )) more)"; break; }
      echo "- $p"; i=$(( i + 1 ))
    done
  fi

  if [[ "$SECONDHAND_COUNT" -gt 0 ]]; then
    echo ""
    echo "## Secondhand, unverified"
    echo ""
    echo "Every primary source of these pages is a conversation record or a"
    echo "reconstructed one. A page leaves the list once a record of a real"
    echo "source is declared on it."
    echo ""
    i=0
    for p in "${SECONDHAND_PAGES[@]}"; do
      [[ "$i" -ge 20 ]] && { echo "- (+$(( SECONDHAND_COUNT - 20 )) more)"; break; }
      echo "- $p"; i=$(( i + 1 ))
    done
  fi

  echo ""
  echo "---"
  echo "*Generated by session-start.sh. Do not edit manually.*"
} > "$STATUS_FILE"

# ⑦ Output additionalContext JSON so Claude sees the summary immediately
if [[ "$LINT_OK" == true ]]; then
  CONTEXT="Wiki at $WIKI. Health check: $TOTAL issues."
  if [[ "$TOTAL" -gt 0 ]]; then
    CONTEXT="$CONTEXT Broken links: $BROKEN_LINKS. Orphans: $ORPHANS."
    CONTEXT="$CONTEXT Stale: $STALE_COUNT. Confidence decay: $DECAY_COUNT."
  fi
  # Kept out of the total: before a wiki's sources migration these counts are
  # a known backlog, not new damage.
  if [[ "$REFERENCE_ISSUES" -gt 0 ]]; then
    CONTEXT="$CONTEXT Pages with invalid frontmatter: $BAD_FRONTMATTER,"
    CONTEXT="$CONTEXT unresolved sources: $BAD_SOURCES, unresolved citations: $BAD_CITATIONS."
  fi
  if [[ $(( TOTAL + REFERENCE_ISSUES )) -gt 0 ]]; then
    CONTEXT="$CONTEXT See _status.md for details."
  fi
else
  CONTEXT="Wiki at $WIKI. Health check: lint failed, health unknown."
  CONTEXT="$CONTEXT Stale: $STALE_COUNT. Confidence decay: $DECAY_COUNT."
  CONTEXT="$CONTEXT See _status.md for details."
fi
if [[ -n "$LOCK_WARNING" ]]; then
  CONTEXT="$CONTEXT LOCK WARNING: $LOCK_WARNING"
fi

# Context-aware primer.
# When the session is running INSIDE the wiki, the user is here to do wiki work —
# so inject an unconditional "invoke on turn 1" directive (reliable, always-on).
# Elsewhere (the plugin is multi-project), fall back to a slim conditional primer
# that only fires on real triggers, to avoid loading the ~8k-token SKILL.md when
# it isn't relevant.
CWD_REAL="$(cd "$(pwd)" && pwd -P 2>/dev/null || pwd)"
WIKI_REAL="$(cd "$WIKI" 2>/dev/null && pwd -P || echo "$WIKI")"
IN_WIKI=false
if [[ "$CWD_REAL" == "$WIKI_REAL" || "$CWD_REAL" == "$WIKI_REAL"/* ]]; then
  IN_WIKI=true
fi

if [[ "$IN_WIKI" == true ]]; then
  PRIMER="The llm-wiki-pm wiki (a PM second-brain) is at the path above and this session is running inside it — so it IS your working context. Before responding to the first user message — regardless of what it is — invoke the llm-wiki-pm skill (Skill tool) so its full instructions and proactive behaviors are loaded. Do this on turn 1, unconditionally."
else
  PRIMER="llm-wiki-pm (a PM second-brain wiki) is available at the path above but is NOT loaded yet. Invoke the llm-wiki-pm skill (Skill tool) as soon as the conversation touches PM knowledge work, so its full instructions and proactive behaviors load. Triggers — invoke on ANY of:
- the user asks to ingest/query/update/lint the wiki, catch up, brief, run a digest, coverage audit, or pre-meeting prep, or references 'my wiki / knowledge base / notes';
- the user drops a wikifiable PM fact in passing: a named company/person/product, a decision ('we decided', 'going with X'), a competitor move, a customer or roadmap fact, or an open question the wiki should hold;
- natural-memory phrases: 'remember that', 'note that', \"don't forget\", 'log this', 'what do we know about X', 'what am I missing'.
Do NOT load it for unrelated coding or chit-chat. When unsure and a PM entity or decision was mentioned, load it — ambient capture is the whole point of a set-and-forget second brain."
fi

python3 -c "
import json, sys
out = {
  'hookSpecificOutput': {
    'hookEventName': 'SessionStart',
    'additionalContext': sys.argv[1] + '\n\n' + sys.argv[3]
  }
}
if sys.argv[2]:
    out['systemMessage'] = sys.argv[2]
print(json.dumps(out))
" "$CONTEXT" "$GLOBAL_WARNING" "$PRIMER"

exit 0
