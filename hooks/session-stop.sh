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

# ⑤ Rotate: move entries older than 30 days to the archive name, and keep the
# rest (at most 250) in a fresh log.md, so Orient and the briefs' windows still
# find recent entries. On any error nothing moves, and the next session retries.
KEPT=$(python3 - "$LOG_FILE" "$DEST" "$BASE_NAME" <<'PY' 2>/dev/null
import os, re, sys
from datetime import date, timedelta
log, dest, name = sys.argv[1:]
text = open(log).read()
starts = [m.start() for m in re.finditer(r"^## \[", text, re.M)]
cutoff = (date.today() - timedelta(days=30)).isoformat()
# split at the first entry dated in the last 30 days; later back-dated entries stay
split = next((i for i in starts if text[i + 4:i + 14] >= cutoff), len(text))
keep = starts[starts.index(split):] if split in starts else []
if len(keep) > 250:
    split = keep[-250]
    keep = keep[-250:]
header = f"# Wiki Log\n\nRotated from log.md to {name} on {date.today().isoformat()}."
if keep:
    header += f" Entries from {text[split + 4:split + 14]} on stay here."
with open(dest, "x") as f:
    f.write(text[:split].rstrip("\n") + "\n")
try:
    tmp = log + ".tmp"
    with open(tmp, "w") as f:
        f.write(header + "\n" + ("\n" + text[split:] if keep else ""))
    os.replace(tmp, log)
except Exception:
    os.remove(dest)  # log.md is unchanged, so don't leave a copy of its entries
    raise
print(len(keep))
PY
) || exit 0

# ⑥ Report the rotation to stderr
echo "Wiki log rotated: log.md -> $BASE_NAME ($(( ENTRY_COUNT - KEPT )) entries moved, $KEPT kept)" >&2

exit 0
