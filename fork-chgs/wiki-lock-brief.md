# Wiki Lock Brief

created: 2026-10-13

`.wiki-lock` is meant to warn a session that another wiki session is active.
Because the hooks run in every Claude Code session in any project, the warning
fires whenever any other session is open, and any session's end clears another's
lock. This brief lists every reader and writer of the lock, measures how often
the warning fired and how often sessions really wrote to the wiki at the same
time, and weighs five options. It recommends dropping the lock and its warning,
and adding a note at a session's first wiki write when another session wrote to
the wiki in the last 30 minutes (option 2).

## Revision History

revised on: 2026-10-14
Recorded option 2 as implemented in your fork (changelog PATCH-20) and
pm-wiki's lock files as removed. Two details go beyond the plan: an MCP
`vault` delete also refreshes the session's marker, and the tests set
`TMPDIR` so a test run's markers never reach real sessions. The fork's own
`.gitignore` line for `.wiki-lock` was removed too.

revised on: 2026-10-14
Dropped the proposal to raise this upstream now. The change is for your fork,
and its fork changelog entry will mark it an upstream candidate for later.

revised on: 2026-10-14
Made option 2 the recommendation in place of option 1. Dropping the lock alone
leaves no signal that overlaps are becoming common, and option 2's note is that
signal for about 25 more lines of code. Recorded the choice of plain option 2,
without an overlap count.

## Status

Status: option 2 implemented 2026-10-14 (changelog PATCH-20), and pm-wiki's
`.wiki-lock` and its `.gitignore` lines removed.
Backlog item: NW13 in the [llm-wiki-pm Fork Backlog](llm-wiki-pm-fork-backlog.md).
Related: NW12 and NW10 (the checkpoint commits, which don't read the lock;
the finding is in the [Archive Snapshots in Search Brief](archive-snapshots-in-search-brief.md)),
NW5 (`$WIKI_PATH` as the default wiki, so every project's sessions resolve
pm-wiki).

## Recommendation in brief

Drop the lock and its warning, and replace them with a "recent writer" note
(option 2). The lock never blocked a write, a third of hook runs showed a
warning that matched no concurrent writing, and the two real overlaps in ten
weeks got no warning. Claude Code's own Write and Edit refuse a file that
changed since the session read it, and the checkpoint commit keeps the other
session's work recoverable, so dropping the lock loses no protection. But
dropping it alone (option 1) leaves nothing to say when overlaps become common.
Option 2's note, given at a session's first wiki write when another session
wrote to the wiki in the last 30 minutes, is that signal, from markers kept
outside the wiki.

## What happens

The hooks are configured in `~/.claude/settings.json`, so they run in every
session in any project, and `$WIKI_PATH` points them all at pm-wiki.

- **`session-start.sh` (step ②b)** reads `$WIKI/.wiki-lock` if present. A lock
  older than 2 hours, by the time written into it, is deleted. A younger one
  adds "LOCK WARNING: Another wiki session may be active (lock: …)" to the
  session-start context. Either way the hook then overwrites the file with its
  own `<session_id>:<UTC time>`.
- **`session-stop.sh`** sets an `EXIT` trap that deletes `$WIKI/.wiki-lock`
  whoever wrote it, on every path, including when there's no `log.md`.

So:

- **Every session writes the lock,** in any project, including sessions that
  never touch the wiki.
- **Any session's end clears it,** including another session's lock.
- **The file holds one owner,** the most recent session to start. The sessions
  before it are no longer recorded.
- **The age is time since the session started,** not since its last activity:
  a live session open for 2 hours has its lock deleted by the next start.
- **A restart within a session warns about itself.** SessionStart runs again
  after a compaction, finds the session's own lock and reports it as another
  session's.
- **Hand runs and tests write and clear it too.** A hand run of
  `session-start.sh` overwrites the lock with its own ID. Before 2026-09-30
  (`c98f84c`), the test suite's hook runs also used pm-wiki, which is where the
  `test-session-123` locks came from.
- **The warning only reaches the second session to start.** The first never
  learns of the second.

## Measured

From the Claude Code transcripts on this machine: 109 sessions between
2026-08-06 and 2026-10-13, measured on 2026-10-13.

**The warning fired at 50 of 152 hook runs (33%).** A hook run is a session
start, resume, `/clear` or compaction that produced the health-check context.
Whose lock each warning named:

| Lock owner | Warnings |
|---|---|
| Another session that never touched pm-wiki | 16 |
| Another session that touched pm-wiki only through Bash (reads included) | 12 |
| Another session that wrote to pm-wiki through tools at some point | 10 |
| An ID with no transcript, including 3 `test-session-123` | 11 |
| The session itself, after a manual compaction on 2026-09-21 | 1 |

Lock age at the warning: median 5 minutes, 3 over an hour.

**Real concurrent writing is rare, and the lock missed it.** 38 sessions wrote
to pm-wiki through Write, Edit, MultiEdit or the MCP's `vault`/`edit`. Only two
pairs had overlapping write windows:

- 2026-08-07: two sessions in pm-wiki, closest writes 76 minutes apart.
- 2026-09-01: a session in ai-forecasting and one in pm-wiki, closest writes
  4 minutes apart.

Neither later session got a warning, although the earlier one was still
writing: another session's end or a test run had already cleared the lock. So
none of the 50 warnings marked two sessions writing at once. Bash writes aren't
counted, since the transcripts don't separate them from Bash reads.

**Agents act on the noise.** On 2026-09-23 an agent flagged the warning before
writing. On 2026-09-28 one asked you to check that no other session was
working before it moved files. On 2026-09-30 one told you to close other
sessions before migration step 10b, then ran checks and found no lock file and
no other session.

## Every reader and writer of `.wiki-lock`

| Component | What it does | Owner |
|---|---|---|
| `hooks/session-start.sh` ②b (lines 99–130) | Reads, deletes after 2 hours, writes its own | Upstream code |
| `hooks/session-start.sh` (lines 317–319) | Adds the warning to the context | Upstream code |
| `hooks/session-start.sh` scaffold (lines 50–59) | Ignores the file when deciding a folder is empty | Your fork (PATCH-10, `09dfb6f`) |
| `hooks/session-stop.sh` (lines 17–19) | Deletes it on exit, whoever owns it | Upstream code |
| `hooks/README.md` (line 13) | Names it in the scaffold's empty-folder rule | Your fork's wording |
| Core `SKILL.md` Pitfalls (lines 381–382) | Says it "prevents concurrent-session corruption" | Upstream |
| Core `SKILL.md` Pre-Flight ⑤ (line 177) | Says to surface "lock warnings" from `_status.md` | Upstream |
| `llm-wiki-brief` `SKILL.md` (line 91) | Lists "lock state from _status.md" under Warnings | Upstream |
| `tests/test_scaffold.py` (lines 86–91) | Puts a lock in a folder that must still scaffold | Your fork |
| pm-wiki `.gitignore` (lines 1–2) | Ignores it | pm-wiki |
| Fork changelog PATCH-10 | Records the scaffold rule. Historical, stays as written | Your fork |

Not readers: `_status.md` has never recorded the lock, so the two skills that
send agents there for lock state find nothing. `AGENTS.md`, `lint.py`,
`checkpoint()`, `pre-write.sh`, `post-validate.sh`, the wiki-search server and
Obsidian don't read it. No test checks the lock's behavior: `tests/test_hooks.py`
(upstream's) and `tests/test_write_hooks.py` (your fork's) never mention it.

## Should the lock exist at all?

Its job was a warning, not a lock. Upstream's 2.5.0 changelog: "Lock warning
surfaced via additionalContext if another session is active." It never blocked
a write, and the skill's "prevents concurrent-session corruption" overstates
it. NW10 planned the first use as a gate, skipping a checkpoint while the lock
was held, and NW12 dropped that because the lock is held most of the time.

What guards against two sessions writing at once without it:

- **Write and Edit refuse a stale file.** Claude Code's built-in tools refuse
  to write a file that changed since the session last read it, and tell the
  agent to read it again. That covers every Write and Edit to a wiki page.
- **The checkpoint commit** before each session's first wiki write commits
  whatever another session left on disk, so a later overwrite can be undone
  from git.
- **Not guarded:** MCP `vault`/`edit` writes and Bash writes, which don't check
  for a changed file. The lock never guarded them either, since it only warns
  at session start.

So the lock adds nothing that works today, and fixing it only pays if you want
a concurrency signal beyond those two guards.

## Options

### 1. Drop the lock and its warning

- **Code:** remove ②b and the warning line from `session-start.sh` (about 35
  lines), and the lock and its trap from `session-stop.sh` (3 lines). Remove
  `.wiki-lock` from the scaffold's empty-folder rule, since nothing writes it.
- **Docs:** `hooks/README.md` line 13; core `SKILL.md` drops the Pitfalls
  bullet and says "staleness warnings" in Pre-Flight ⑤; `llm-wiki-brief` drops
  "lock state".
- **Tests:** in `tests/test_write_hooks.py`, one test that `session-start.sh`
  writes no `.wiki-lock` and adds no lock warning when a leftover lock is
  present (about 15 lines). `tests/test_scaffold.py` drops its lock line.
  No change to upstream's `tests/test_hooks.py`.
- **Migration:** after the hook change lands, delete pm-wiki's `.wiki-lock`
  (untracked, so a plain `rm`) and its two `.gitignore` lines in a pm-wiki
  commit. Old sessions run the new scripts from the fork clone, so nothing
  writes the file again.
- **Loses:** a warning that, as measured, never matched concurrent writing.
- **Leaves no signal:** nothing would show that overlaps had become common, for
  example once scheduled maintenance sweeps run beside interactive sessions.
  Finding out would mean rerunning this brief's transcript scan, and Claude
  Code can delete transcripts after 30 days.
- **Cost:** about 40 lines removed, about 15 test lines, 4 doc edits, one
  pm-wiki commit. A fork changelog entry.

### 2. Replace it with a "recent writer" note at the first wiki write (recommended)

Everything in option 1, plus:

- `post-validate.sh` touches a per-session marker in the temp folder after
  each wiki write, beside `pre-write.sh`'s checkpoint marker.
- At a session's first wiki write, `pre-write.sh` lists other sessions'
  markers touched in the last 30 minutes and adds: "Session `<id>` wrote to the
  wiki N minutes ago. Re-read a page before changing it."
- Nothing in the wiki, nothing to remove at session end, and no staleness
  beyond the time window. Sessions that never write are never reported.
- **The signal:** the agent normally passes the note on, as agents did with the
  lock warning, so you hear of each overlap when it happens. Unlike the lock
  warning, it fires only on real wiki writes.
- **Docs:** `hooks/README.md` describes the note under `pre-write.sh` and the
  marker under `post-validate.sh`. The core `SKILL.md` Pitfalls bullet about
  the lock is replaced by one about the note, rather than dropped.
- **Limits:** covers tool writes only, not Bash. Only the later session to
  write is told. Of the two measured overlaps, it would have fired for
  2026-09-01 (4 minutes apart) and not for 2026-08-07 (76 minutes).
- **Cost:** option 1's removals, plus about 25 lines in the two write hooks and
  about 40 test lines in `tests/test_write_hooks.py`.
- **Variant not chosen: an overlap count.** Each note also appends a line to a
  log outside the wiki, and the session-start summary reports the count for the
  last 30 days. About 15 more lines. It adds trends, which matter only if
  overlaps become common, and the notes themselves would show that.

### 3. Scope the lock to sessions that use the wiki

- `session-start.sh` writes the lock only when the session's folder is the
  wiki. `pre-write.sh` writes it at a session's first wiki write, from any
  project.
- `session-stop.sh` removes it only when it holds the ending session's ID
  (SessionEnd's input carries `session_id`).
- `session-start.sh` skips the warning when the lock is its own (compaction).
- **Still broken:** the file holds one owner, so a second writer takes it over
  and the first is unrecorded. A session that stays open, or ends without
  running SessionEnd, keeps the lock, so it depends on staleness anyway, and a
  2-hour age from session start is wrong for that. A fair staleness rule needs
  the lock refreshed on every write and judged by idle time. At that point it is option
  2 with a file in the wiki and more to get wrong.
- **Cost:** about 60 lines across three hooks, about 60 test lines, and the
  same doc fixes, which would be rewritten rather than removed.

### 4. Owner-checked removal only

`session-stop.sh` removes the lock only when it holds its own session ID
(about 5 lines). Sessions stop clearing each other's locks, but every session
in any project still writes one, so the warning fires more often: a session
that's open but idle keeps it for up to 2 hours. Worse than today on its own.

### 5. A different staleness rule only

A shorter age, or age from last activity, makes the warning fire less but
doesn't make it mean a wiki session is running. It only helps as part of
option 3.

## Comparison

| | 1. Drop | 2. Recent writer | 3. Scoped lock |
|---|---|---|---|
| False warnings | None | Rare: only real wiki writes in the last 30 minutes | Fewer, still from idle sessions holding it |
| Catches real overlaps | No | One of the two measured | Only if the first session's lock survives |
| Signal that overlaps are common | None | A note through the agent, each time | The warning, when it fires |
| Files in the wiki | None | None | `.wiki-lock` |
| Session-end handling | None | None | Owner check |
| Code | About 40 lines removed | Plus about 25 lines | About 60 lines changed |
| Tests | About 15 lines | About 55 lines | About 60 lines |

## Upstream

Upstream has the same code and docs (`hooks/session-start.sh` line 91,
`hooks/session-stop.sh` line 17, `SKILL.md` line 363) and hasn't changed its
hooks since your last merge (`0667f75`), up to its 2.22.0 release
(`62f3453`, fetched 2026-10-13).

- A plugin enabled at user scope runs its hooks in every project, so upstream
  users get the same noise and the same cross-clearing.
- With no wiki path configured, both hooks fall back to the current folder,
  so the lock is written into, and removed from, whichever project the session
  runs in. Upstream's own `.gitignore` lists `.wiki-lock` under "Wiki/vault
  runtime artifacts (generated per-session, not plugin source)", which suggests
  it turned up in the plugin repo that way.
- The lock isn't on upstream's CONTRIBUTING list of things not to change
  without discussion.
- The change is for your fork. Its fork changelog entry, written when it's
  implemented, marks it an upstream candidate, so it can be offered upstream
  later, with these measurements, if you choose.
- Divergence from upstream: two removed regions and the note's additions in
  upstream-owned hooks, which conflict only if upstream edits those lines.

## To approve

- Option 2: chosen 2026-10-14, without the overlap count.
- Deleting pm-wiki's `.wiki-lock` and its `.gitignore` lines, in a pm-wiki
  commit, after the hook change.
