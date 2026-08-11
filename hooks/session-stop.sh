#!/usr/bin/env bash
# session-stop.sh
# Runs at session end. Guards log rotation to keep log.md manageable.
# Hook type: SessionEnd (fires when session terminates, not after every turn)

set -euo pipefail

# ── Resolve WIKI path (must match session-start.sh) ──────────────────────────
FILE_WIKI=$(cat "$(pwd)/.wiki-path" 2>/dev/null | tr -d '[:space:]' || true)
WIKI="${FILE_WIKI:-${CLAUDE_PLUGIN_OPTION_wiki_path:-${WIKI_PATH:-$(pwd)}}}"

# ① Exit silently if wiki not initialized yet
if [[ ! -d "$WIKI" ]]; then
  exit 0
fi

LOCKFILE="$WIKI/.wiki-lock"
# Release lock on any exit path (early returns, errors, normal completion)
trap 'rm -f "$LOCKFILE" 2>/dev/null || true' EXIT

# ── Auto-commit wiki changes (runs every session end, not just on rotation) ──
# Disabled 2026-08-07: firing far more often than intended (SessionEnd fires
# per short-lived backend session in this hosting environment, not once per
# user conversation), producing dozens of near-duplicate commits. User commits
# manually now.
# if [[ -d "$WIKI/.git" ]]; then
#   git -C "$WIKI" add -A >/dev/null 2>&1 || true
#   git -C "$WIKI" commit -m "wiki update $(date +%Y-%m-%d_%H:%M)" >/dev/null 2>&1 || true
# fi

LOG_FILE="$WIKI/log.md"

# ② Exit silently if log.md does not exist
if [[ ! -f "$LOG_FILE" ]]; then
  exit 0
fi

# ③ Count log entries (each entry starts with '## [')
# grep -c prints 0 AND exits 1 on zero matches; `|| echo 0` would append a second
# line making ENTRY_COUNT="0\n0", which breaks the -le test below and wrongly
# rotates a fresh/empty log every session. Use `|| true` and default to 0.
ENTRY_COUNT=$(grep -c '^## \[' "$LOG_FILE" 2>/dev/null || true)
ENTRY_COUNT=${ENTRY_COUNT:-0}

# ④ Only rotate if log exceeds 500 entries
if [[ "$ENTRY_COUNT" -le 500 ]]; then
  exit 0
fi

# ── Determine rotation target filename ────────────────────────────────────────
YEAR=$(date +%Y)
BASE_NAME="log-${YEAR}.md"
DEST="$WIKI/$BASE_NAME"

# If log-YYYY.md already exists, find the next available part number
if [[ -f "$DEST" ]]; then
  PART=2
  while [[ -f "$WIKI/log-${YEAR}-part-${PART}.md" ]]; do
    PART=$(( PART + 1 ))
  done
  BASE_NAME="log-${YEAR}-part-${PART}.md"
  DEST="$WIKI/$BASE_NAME"
fi

# ⑤ Rotate: move log.md to the archive name
mv "$LOG_FILE" "$DEST"

# ⑥ Create fresh log.md with a rotation header
TODAY=$(date '+%Y-%m-%d')
printf '# Wiki Log\n\nRotated from %s on %s.\n' "$BASE_NAME" "$TODAY" > "$LOG_FILE"

# ⑦ Report the rotation to stderr
echo "Wiki log rotated: log.md -> $BASE_NAME ($ENTRY_COUNT entries)" >&2

exit 0
