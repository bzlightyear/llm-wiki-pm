#!/usr/bin/env python3
"""Migrate a wiki's sources: entries and [source: ...] citations to
references/citation-spec.md.

Usage:
    migrate_sources.py <wiki_path>                  # dry run: print the plan, write nothing
    migrate_sources.py <wiki_path> --apply          # write it
    migrate_sources.py <wiki_path> --apply --declare-cited

A one-off for wikis written before the spec, when a fact stated in
conversation was cited as `user, conversation, <date>` (or `user, <date>`,
`conversation, <date>`), which names no file. The migration:

- writes one record per conversation date,
  raw/internal/conversation-<date>-reconstructed.md, marked `reconstructed:
  true`. Its body quotes that day's log entries and lists the claims that
  cite it. What was said was never captured, so the record gives those
  citations an ID that resolves, not evidence, and lint keeps the pages that
  rest on it on its revisit list (R10);
- rewrites those sources: entries, including ones an unquoted flow list
  split into `conversation` and a bare date, to the record's path, and those
  citations to its ID, with any "(context)" as the location. A page that
  cites a date declares its record. overview.md is migrated like a page,
  though lint doesn't check it;
- repairs mechanical citation defects and midnight timestamp dates, as
  lint --auto-fix=content does, and empties a dated digest's sources: of
  entries that name no record or page;
- moves briefs rotated into _archive/briefings/ back to briefings/, and
  records in raw/clippings/ to raw/articles/;
- replaces meta/contract.md while it is the wiki-search MCP's default, and
  adds the split-procedure pointer to SCHEMA.md's split rule;
- with --declare-cited, declares each file a page cites without declaring
  it, when the ID names exactly one file.

The dry run prints each page's R3, R6, R7 and R12 counts before and after,
and what is left for a hand pass. --apply snapshots each file before changing
it, writes frontmatter through wikifm, leaves `updated:` alone (what a page
says doesn't change) and appends a log.md entry. Run lint afterwards.

Stdlib only.
"""

import argparse
import re
import sys
from collections import defaultdict, namedtuple
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True  # don't leave __pycache__ in the plugin dir
import lint  # noqa: E402  (beside this script)
import wikifm  # noqa: E402

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"

# A citation or sources: entry naming a conversation by its date, with an
# optional "(context)" before the date and more text after it.
CONVERSATION_RE = re.compile(
    r"(?:user,\s*conversation|user|conversation)(?:\s*\((?P<context>[^()]*)\))?"
    r",\s*(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})(?:,\s*(?P<more>.*))?",
    re.IGNORECASE,
)
Conversation = namedtuple("Conversation", "date context more")
# A line that starts a list item, table row, heading or quote, not a
# paragraph's continuation.
BLOCK_START_RE = re.compile(r"[ \t]*(?:[-*+] |[0-9]+[.)] |[|#>])")

# `## [YYYY-MM-DD] action | subject`, the brackets possibly escaped by the
# wiki-search MCP; log.md is rotated into log-YYYY.md, then log-YYYY-part-N.md.
LOG_HEADER_RE = re.compile(
    r"^## \\?\[([0-9]{4}-[0-9]{2}-[0-9]{2})\\?\] *([^|\n]*)", re.MULTILINE
)
ROTATED_LOG_RE = re.compile(r"log-([0-9]{4})(?:-part-([0-9]+))?\.md")

# (folder, where its .md files go): briefs the maintain loop rotated into the
# archive, and records in a raw/ folder that ingest-guide.md doesn't route to.
MOVES = (("_archive/briefings", "briefings"), ("raw/clippings", "raw/articles"))
UNROUTED = ("raw/attachments", "raw/clippings")

# The split rule as the SCHEMA.md template wrote it before the pointer.
OLD_SPLIT_RULE = "- **Split** when page > 200 lines, break by sub-topic with cross-links"
SPLIT_RULE_RE = re.compile(r"^- \*\*Split\*\*.*(?:\n[ \t]+\S.*)*", re.MULTILINE)


def record_id(day):
    return f"conversation-{day}-reconstructed"


def record_path(day):
    return f"raw/internal/{record_id(day)}.md"


def conversation(text):
    """The Conversation that `text`, a citation or a sources: entry, names by
    its date, or None."""
    m = CONVERSATION_RE.fullmatch(" ".join(text.split()))
    if not m:
        return None
    try:
        date.fromisoformat(m.group("date"))
    except ValueError:
        return None
    return Conversation(m.group("date"), (m.group("context") or "").strip(), m.group("more") or "")


def location(conv):
    """A conversation citation's location once it cites the record: its
    context and whatever followed the date."""
    return ", ".join(x for x in (conv.context, conv.more) if x)


def cite_text(c):
    """A citation as written, with the mechanical defects undone."""
    return c.id + (f", {c.location}" if c.location else "")


def conversation_runs(entries):
    """Group sources: entries into (entries, Conversation or None) runs. A run
    of two or three entries is one conversation that an unquoted flow list
    split at its commas, such as `[conversation, 2026-01-15]`, so it ends
    with the bare date. Any other entry is a run of its own."""
    runs, i = [], 0
    while i < len(entries):
        n, conv = 1, conversation(entries[i])
        for k in (3, 2):
            if conv or i + k > len(entries):
                continue
            joined = conversation(", ".join(entries[i:i + k]))
            if joined and not joined.more and entries[i + k - 1].strip() == joined.date:
                n, conv = k, joined
        runs.append((entries[i:i + n], conv))
        i += n
    return runs


def split(text):
    """(frontmatter with its fences, body)."""
    m = wikifm.FRONTMATTER_RE.match(text)
    head = m.end() if m else 0
    return text[:head], text[head:]


def claim(body, c):
    """The paragraph, list item or table row holding citation c's marker, on
    one line. A wrapped paragraph can leave a marker alone on its line."""
    start = body.rfind("\n", 0, c.start) + 1
    while start and not BLOCK_START_RE.match(body, start):  # a continued line
        above = body.rfind("\n", 0, start - 1) + 1
        line = body[above:start - 1].strip()
        if not line or line.startswith(("|", "#")):
            break
        start = above
    end = body.find("\n", c.end)
    while end != -1:
        below = body.find("\n", end + 1)
        line = body[end + 1:len(body) if below == -1 else below]
        if not line.strip() or BLOCK_START_RE.match(line):
            break
        end = below
    return " ".join(body[start:len(body) if end == -1 else end].split())


def log_entries(wiki):
    """{date: [entry, ...]} from the rotated logs and log.md, oldest first,
    leaving out lint runs, which record nothing about a conversation."""
    rotated = [p for p in wiki.glob("log-*.md") if ROTATED_LOG_RE.fullmatch(p.name)]
    rotated.sort(key=lambda p: [int(g or 1) for g in ROTATED_LOG_RE.fullmatch(p.name).groups()])
    entries = defaultdict(list)
    for path in rotated + [wiki / "log.md"]:
        if not path.is_file():
            continue
        text = path.read_text()
        heads = list(LOG_HEADER_RE.finditer(text))
        for m, nxt in zip(heads, heads[1:] + [None]):
            if m.group(2).strip() != "lint":
                entry = text[m.start():nxt.start() if nxt else len(text)]
                entries[m.group(1)].append(entry.rstrip())
    return entries


def record_text(day, contexts, entries, cited_by, today):
    """A reconstructed conversation record: the day's log entries quoted,
    then the claims that cite the conversation."""
    title = f"Conversation {day} (reconstructed)"
    if contexts:
        title += ": " + "; ".join(contexts)
    lines = [
        f"Reconstructed on {today} by migrate_sources.py. What was said in this "
        "conversation was never captured, so this record is not evidence: it gives "
        "the citations below an ID that resolves, and lint lists the pages resting "
        "on it until each claim is re-sourced (references/citation-spec.md, "
        '"Revisit").',
        "",
        f"## Log entries for {day}",
        "",
    ]
    if entries:
        lines += ["The wiki's log for that day, without its lint runs. It records "
                  "what the agent did, not what was said.", ""]
        for entry in entries:
            lines += [f"> {line}".rstrip() for line in entry.split("\n")] + [""]
    else:
        lines += ["The log has no entry for that day.", ""]
    lines += ["## Cited by", "", *(f"- {c}" for c in cited_by)]
    text = "---\n\n---\n\n" + "\n".join(lines) + "\n"
    for key, value in (
        ("title", title),
        ("source_type", "conversation"),
        ("stated_by", "user"),
        ("reconstructed", "true"),
        ("reconstructed_on", today),
    ):
        text = wikifm.set_field(text, key, value)
    return text


def conversation_marker(marker, files):
    """The marker's citations rewritten in the grammar, each conversation
    citing its record, or None when another citation in it is neither valid
    nor mechanically repairable (lint's rule for --auto-fix=content), or
    the result isn't valid."""
    cites = []
    for c in marker:
        conv = conversation(cite_text(c))
        if conv:
            cites.append(record_id(conv.date) + (f", {location(conv)}" if location(conv) else ""))
        elif not c.problems or lint._repairable([c], files):
            cites.append(cite_text(c))
        else:
            return None
    new = "[source: " + "; ".join(cites) + "]"
    return None if any(c.problems for c in wikifm.citations(new)) else new


def rewrite_conversations(body, files):
    """Rewrite each marker holding a conversation citation, unless
    conversation_marker() leaves it for the hand pass."""
    for (start, end), marker in sorted(lint._markers(wikifm.citations(body)).items(), reverse=True):
        if any(conversation(cite_text(c)) for c in marker):
            new = conversation_marker(marker, files)
            if new:
                body = body[:start] + new + body[end:]
    return body


class Page:
    """A page of lint's page set, as it is and as the migration leaves it."""

    def __init__(self, rel, src):
        self.rel, self.src = rel, src  # its path after the migration; the file now
        self.before = self.after = src.read_text()
        self.dropped = []  # entries emptied from a dated digest's sources:
        self.refused = None  # why its sources: can't be rewritten


def migrate(page, wiki, moved, files, records, declare_cited):
    """Set page.after to the page migrated. `files` is the {ID: [paths]}
    index after the migration, `records` {ID: path} for the reconstructed
    records. A page whose sources: can't be rewritten is left as it is."""
    fm, _ = wikifm.parse(page.before)
    if fm is None:
        return  # nothing to declare into; lint reports it (R12)
    old = wikifm.sources(fm)
    new = []
    for run, conv in conversation_runs([moved.get(s, s) for s in old]):
        if not conv:
            new += run
        elif record_path(conv.date) not in new + old:
            new.append(record_path(conv.date))
    if wikifm.str_field(fm, "lifecycle") == "dated-digest":
        page.dropped = [s for s in new if wikifm.resolve(s, wiki).kind is None]
        new = [s for s in new if s not in page.dropped]

    head, body = split(page.before)
    text, _ = lint.fix_citations(head + rewrite_conversations(body, files), files)
    declared = {wikifm.slug(s) for s in new}
    for c in wikifm.citations(split(text)[1]):
        if c.problems or c.id in declared:
            continue
        if c.id in records:
            paths = [records[c.id]]
        else:
            paths = files.get(c.id, []) if declare_cited else []
        if len(paths) == 1 and paths[0] != page.rel:
            new.append(paths[0])
            declared.add(c.id)
    if new != old:
        if "sources" in fm and not isinstance(fm["sources"], list):
            page.refused = "isn't a list; edit it by hand"
            return
        try:
            text = wikifm.set_list(text, "sources", new)
        except ValueError as e:
            page.refused = str(e)
            return
    page.after, _ = lint.fix_dates(text)


def entry_problem(entry, wiki, exists):
    """Why a sources: entry isn't the path of an existing record or page
    (R6), or None. `exists` says whether a wiki-relative path is a file."""
    r = wikifm.resolve(entry, wiki)
    if r.kind is None:
        return r.problem
    return None if exists(entry) else "no such file"


def counts(text, wiki, exists):
    """A page's (R3, R6, R7, R12) findings: citations of IDs it doesn't
    declare, sources: entries that aren't the path of an existing record or
    page, markers outside the grammar, and frontmatter errors, with missing
    frontmatter or missing required keys counted once."""
    fm, errors = wikifm.parse(text)
    if fm is None:
        return (0, 0, 0, 1)
    entries = wikifm.sources(fm)
    declared = {wikifm.slug(s) for s in entries}
    cites = wikifm.citations(split(text)[1])
    return (
        sum(1 for c in cites if c.id and c.id not in declared),
        sum(1 for s in entries if entry_problem(s, wiki, exists)),
        sum(1 for m in lint._markers(cites).values() if any(c.problems for c in m)),
        sum(1 for e in errors if e.rule == "R12") + bool(lint.REQUIRED_FRONTMATTER - set(fm)),
    )


def hand_items(page, wiki, files, exists, declare_cited):
    """What is left on a page for the hand pass, one line each."""
    text = page.before if page.refused else page.after
    fm, errors = wikifm.parse(text)
    if fm is None:
        return [f"{page.rel}: no frontmatter block"]
    items = [f"{page.rel}: sources: {page.refused}"] if page.refused else []
    items += [f"{page.rel}:{e.line}: frontmatter: {e.message}" for e in errors if e.rule == "R12"]
    missing = lint.REQUIRED_FRONTMATTER - set(fm)
    if missing:
        items.append(f"{page.rel}: frontmatter is missing {', '.join(sorted(missing))}")
    entries = wikifm.sources(fm)
    for s in entries:
        why = entry_problem(s, wiki, exists)
        if why:
            items.append(f"{page.rel}: sources: '{s}': {why}")
    head, body = split(text)
    declared = {wikifm.slug(s) for s in entries}
    for (start, end), marker in sorted(lint._markers(wikifm.citations(body)).items()):
        line = head.count("\n") + body.count("\n", 0, start) + 1
        where = f"{page.rel}:{line}"
        problems = [p for p in wikifm.PROBLEMS if any(p in c.problems for c in marker)]
        if problems:
            shown = body[start:start + 60] + "…" if "not closed" in problems else body[start:end]
            items.append(f"{where}: {' '.join(shown.split())}: {', '.join(problems)}")
            continue
        for c in marker:
            if c.id in declared:
                continue
            paths = files.get(c.id, [])
            if len(paths) == 1:
                hint = f"declare {paths[0]}" + ("" if declare_cited else " (--declare-cited does)")
            elif paths:
                hint = f"it names {len(paths)} files: " + ", ".join(paths)
            else:
                hint = "it names no record or page"
            items.append(f"{where}: cites '{c.id}', which sources: doesn't declare: {hint}")
    return items


class Plan:
    """The whole migration, worked out before anything is written."""

    def __init__(self):
        self.records = []  # (path, text, log entries, citing pages) to write
        self.kept = []  # reconstructed records already written
        self.moved = {}  # old path -> new path
        self.pages = []
        self.root = []  # (path, new text, what changes) for root files
        self.hand = []  # the hand pass, one line each
        self.conflicts = []  # anything that stops the migration
        self.total = self.after_total = (0, 0, 0, 0)
        self.rows = []  # (page, before counts, after counts)


def make_plan(wiki, declare_cited):
    """Work out the whole migration without writing anything."""
    plan, today = Plan(), date.today().isoformat()
    files = lint.source_index(wiki, lint.wiki_pages(wiki))  # {ID: [paths]} now
    after = {i: list(ps) for i, ps in files.items()}  # and after the migration

    for folder, target in MOVES:
        for p in sorted((wiki / folder).glob("*.md")):
            old, new = p.relative_to(wiki).as_posix(), f"{target}/{p.name}"
            taken = (wiki / new).exists() or (target == "briefings" and wikifm.slug(new) in files)
            if taken:
                plan.conflicts.append(f"{old} can't move to {new}: that name is taken")
                continue
            plan.moved[old] = new
            rid = wikifm.slug(new)
            after[rid] = [x for x in after.get(rid, []) if x != old] + [new]
            if target == "briefings":
                plan.hand.append(f"{new}: lint never checked it in _archive/; fix what "
                                 "lint reports on it")
    for folder in UNROUTED:
        for p in sorted((wiki / folder).glob("*")):
            rel = p.relative_to(wiki).as_posix()
            if rel in plan.moved or p.name.startswith("."):  # .DS_Store and the like
                continue
            if p.suffix == ".md":
                plan.hand.append(f"{rel}: move it to the raw/ folder ingest-guide.md routes it to")
            else:
                plan.hand.append(f"{rel}: save a markdown record of it in a routed raw/ folder, "
                                 "move the original to raw/assets/, and declare the record instead")
    for p in sorted((wiki / "_archive").glob("README-*.md")):
        plan.hand.append(
            f"{p.relative_to(wiki).as_posix()}: rename it to _archive/<slug>-<date>.md "
            "if git shows which directory page it snapshots"
        )

    plan.pages = [Page(p.relative_to(wiki).as_posix(), p) for p in lint.wiki_pages(wiki)]
    plan.pages += [Page(new, wiki / old) for old, new in plan.moved.items()
                   if new.split("/")[0] in wikifm.PAGE_DIRS]
    # Outside lint's page set, but it cites like a page and Orient reads it
    # every session, so its old citations would keep being copied.
    if (wiki / "overview.md").is_file():
        plan.pages.append(Page("overview.md", wiki / "overview.md"))

    # M2: the conversations the pages cite, and what cites them
    contexts, claims, citing = defaultdict(list), defaultdict(list), defaultdict(set)
    for page in plan.pages:
        fm, _ = wikifm.parse(page.before)
        if fm is None:
            continue
        for _, conv in conversation_runs(wikifm.sources(fm)):
            if conv:
                _add(contexts[conv.date], location(conv))
                _add(claims[conv.date], f"`{page.rel}`, in `sources:`")
                citing[conv.date].add(page.rel)
        body = split(page.before)[1]
        for c in wikifm.citations(body):
            conv = conversation(cite_text(c))
            if conv:
                _add(contexts[conv.date], conv.context)
                _add(claims[conv.date], f"`{page.rel}`: {claim(body, c)}")
                citing[conv.date].add(page.rel)
    logs = log_entries(wiki)
    for day in sorted(claims):
        rel = record_path(day)
        others = [p for p in files.get(record_id(day), []) if p != rel]
        if others:
            plan.conflicts.append(f"{rel} can't be written: its ID names {', '.join(others)}")
        elif (wiki / rel).is_file():
            fm, _ = wikifm.parse((wiki / rel).read_text())
            if wikifm.str_field(fm, "reconstructed").lower() == "true":
                plan.kept.append(rel)
            else:
                plan.conflicts.append(f"{rel} exists and isn't a reconstructed record")
        else:
            text = record_text(day, contexts[day], logs[day], claims[day], today)
            plan.records.append((rel, text, len(logs[day]), len(citing[day])))
            after[record_id(day)] = [rel]

    added = {r[0] for r in plan.records} | set(plan.moved.values())

    def exists_after(rel):
        return rel in added or (rel not in plan.moved and (wiki / rel).is_file())

    def exists_now(rel):
        return (wiki / rel).is_file()

    records = {record_id(day): record_path(day) for day in claims}
    totals = [[0] * 4, [0] * 4]
    for page in plan.pages:
        migrate(page, wiki, plan.moved, after, records, declare_cited)
        before = counts(page.before, wiki, exists_now)
        now = counts(page.after, wiki, exists_after)
        for total, n in zip(totals, (before, now)):
            total[:] = [a + b for a, b in zip(total, n)]
        if page.after != page.before or any(before) or any(now):
            plan.rows.append((page, before, now))
        plan.hand += hand_items(page, wiki, after, exists_after, declare_cited)
    plan.total, plan.after_total = totals

    # M7: the contract and SCHEMA.md's split rule
    if lint.check_contract(wiki):
        plan.root.append(("meta/contract.md", (TEMPLATES / "vault-contract.md").read_text(),
                          "replaced with templates/vault-contract.md (R11)"))
    schema = wiki / "SCHEMA.md"
    if schema.is_file():
        text = schema.read_text()
        m = SPLIT_RULE_RE.search(text)
        new_rule = SPLIT_RULE_RE.search((TEMPLATES / "SCHEMA.md").read_text()).group(0)
        if m and m.group(0) == OLD_SPLIT_RULE:
            plan.root.append(("SCHEMA.md", text[:m.start()] + new_rule + text[m.end():],
                              "its split rule gains the split-procedure pointer"))
        elif not (m and "citation-spec.md" in m.group(0)):
            plan.hand.append("SCHEMA.md: add the split-procedure pointer to its split rule, "
                             "as in templates/SCHEMA.md")
    return plan


def _add(items, item):
    if item and item not in items:
        items.append(item)


def apply(plan, wiki):
    """Write the plan: snapshots first (M1), then records, moves, pages and
    root files. Returns the paths whose file doesn't read back as written."""
    changed = [p for p in plan.pages if p.after != p.before]
    for page in changed:
        lint.snapshot(page.src, wiki)
    for rel, _, _ in plan.root:
        lint.snapshot(wiki / rel, wiki)
    written = {}
    for rel, text, _, _ in plan.records:
        (wiki / rel).parent.mkdir(parents=True, exist_ok=True)
        with open(wiki / rel, "x", encoding="utf-8") as f:  # never overwrite
            f.write(text)
        written[rel] = text
    for old, new in plan.moved.items():
        (wiki / new).parent.mkdir(parents=True, exist_ok=True)
        (wiki / old).rename(wiki / new)
    for rel, text in [(p.rel, p.after) for p in changed] + [(r, t) for r, t, _ in plan.root]:
        (wiki / rel).write_text(text)
        written[rel] = text
    failed = [rel for rel, text in written.items() if (wiki / rel).read_text() != text]
    log = wiki / "log.md"
    if not failed and log.is_file() and (written or plan.moved):
        today = date.today().isoformat()
        lines = [
            f"\n## [{today}] migrate | sources and citations to the citation spec\n",
            f"- {len(plan.records)} reconstructed conversation record(s) in raw/internal/",
            f"- {len(changed)} page(s) changed, each snapshotted to _archive/ first",
        ]
        lines += [f"- moved {old} → {new}" for old, new in plan.moved.items()]
        lines += [f"- {rel}: {what}" for rel, _, what in plan.root]
        lines.append(f"- {len(plan.hand)} item(s) left for a hand pass; "
                     "migrate_sources.py lists them")
        with log.open("a") as f:
            f.write("\n".join(lines) + "\n")
    return failed


def render(plan, applied):
    """The plan as text: records, moves, root files, the count table, what
    was dropped and the hand pass."""
    def did(things, verb, done):
        return f"{things} {done}" if applied else f"{things} to {verb}"

    out = ["Applied." if applied else "Dry run: nothing written. Run with --apply to write it.", ""]
    out.append(f"{did('Records', 'write', 'written')} (M2): {len(plan.records)}")
    out += [f"  {rel}: {n} log entries, cited by {pages} page(s)"
            for rel, _, n, pages in plan.records]
    if plan.kept:
        out.append(f"Records already written, kept: {len(plan.kept)}")
    out.append(f"{did('Files', 'move', 'moved')} (M4): {len(plan.moved)}")
    out += [f"  {old} → {new}" for old, new in plan.moved.items()]
    out.append(f"{did('Root files', 'change', 'changed')} (M7): {len(plan.root)}")
    out += [f"  {rel}: {what}" for rel, _, what in plan.root]
    changed = sum(1 for p in plan.pages if p.after != p.before)
    out += ["", f"{did('Pages', 'change', 'changed')}: {changed}, each snapshotted to "
            "_archive/ first (M1)", ""]

    def cell(before, now):
        return f"{before} → {now}" if before or now else "·"

    table = [("R3", "R6", "R7", "R12", "page")]
    table += [tuple(cell(b, a) for b, a in zip(before, now)) + (page.rel,)
              for page, before, now in sorted(plan.rows, key=lambda r: r[0].rel)]
    table.append(tuple(cell(b, a) for b, a in zip(plan.total, plan.after_total))
                 + (f"all {len(plan.pages)} pages",))
    widths = [max(len(row[i]) for row in table) for i in range(4)]
    out += ["  " + "  ".join(c.ljust(w) for c, w in zip(row, widths)) + "  " + row[4]
            for row in table]
    out += ["", "  R3 citations of undeclared IDs, R6 sources: entries that aren't a file's "
            "path, R7 markers outside the grammar, R12 frontmatter errors"]
    dropped = [p for p in plan.pages if p.dropped]
    if dropped:
        out += ["", "Emptied from dated digests' sources: (they name no record or page)"]
        out += [f"  {p.rel}: " + ", ".join(f"'{s}'" for s in p.dropped) for p in dropped]
    out += ["", f"For the hand pass (M5): {len(plan.hand)}"]
    out += [f"  {item}" for item in plan.hand]
    if plan.conflicts:
        out += ["", "Conflicts (nothing is written until they're resolved):"]
        out += [f"  {c}" for c in plan.conflicts]
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(
        description="Migrate a wiki's sources: entries and citations to "
        "references/citation-spec.md. Without --apply, a dry run."
    )
    parser.add_argument("wiki", help="the wiki's path")
    parser.add_argument("--apply", action="store_true", help="write the migration")
    parser.add_argument(
        "--declare-cited", action="store_true",
        help="also declare each file a page cites but doesn't declare, when its ID "
        "names exactly one file",
    )
    args = parser.parse_args()

    wiki = Path(args.wiki).expanduser().resolve()
    if not wiki.is_dir():
        sys.exit(f"error: {wiki} is not a directory")
    plan = make_plan(wiki, args.declare_cited)
    if plan.conflicts or not args.apply:
        print(render(plan, applied=False))
        sys.exit(1 if plan.conflicts else 0)
    failed = apply(plan, wiki)
    print(render(plan, applied=True))
    if failed:
        sys.exit("error: these files don't read back as written, so log.md wasn't "
                 "updated: " + ", ".join(failed))
    print(f"\nNow run lint (M8): python3 {Path(__file__).parent / 'lint.py'} {wiki}")


if __name__ == "__main__":
    main()
