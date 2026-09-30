#!/usr/bin/env python3
"""Capture a fact stated in conversation as a write-once raw/ record.

Usage:
    capture.py <wiki_path> --topic <slug> [--stated-by user|<person-slug>] < statement

Writes raw/internal/conversation-<YYYY-MM-DD>-<topic>.md, with source_type,
captured and stated_by in its frontmatter and the statement from stdin as its
body. When that ID is already a record's or a page's, it adds -2, -3, ... and
it never overwrites a file. Prints the path to declare in `sources:` and the
ID to cite as `[source: <id>]`. The rules are in references/citation-spec.md,
"Conversational facts".

Stdlib only.
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True  # don't leave __pycache__ in the plugin dir
import wikifm  # noqa: E402  (beside this script)
from lint import slug, wiki_pages  # noqa: E402

ID_RE = re.compile(r"[a-z0-9][a-z0-9._-]*")


def taken_ids(wiki):
    """Every record ID under raw/ and every page slug. A new record's ID must
    differ from all of them."""
    ids = {p.stem for p in (wiki / "raw").rglob("*.md")}
    ids.update(slug(p) for p in wiki_pages(wiki))
    return ids


def record_text(today, topic, stated_by, statement):
    text = "---\n\n---\n\n" + statement + "\n"
    for key, value in (
        ("title", f"Conversation {today}: {topic}"),
        ("source_type", "conversation"),
        ("captured", today),
        ("stated_by", stated_by),
    ):
        text = wikifm.set_field(text, key, value)
    return text


def capture(wiki, topic, stated_by, statement):
    """Write the record and return its path. The first free ID wins; opening
    with "x" means an existing file is never overwritten, even by a capture
    racing this one."""
    today = date.today().isoformat()
    folder = wiki / "raw" / "internal"
    folder.mkdir(parents=True, exist_ok=True)
    text = record_text(today, topic, stated_by, statement)
    taken = taken_ids(wiki)
    base = f"conversation-{today}-{topic}"
    n = 1
    while True:
        rid = base if n == 1 else f"{base}-{n}"
        n += 1
        if rid in taken:
            continue
        path = folder / f"{rid}.md"
        try:
            with open(path, "x", encoding="utf-8") as f:
                f.write(text)
        except FileExistsError:
            continue
        return path


def main():
    parser = argparse.ArgumentParser(
        description="Capture a fact stated in conversation as a raw/ record. "
        "The statement is read from stdin."
    )
    parser.add_argument("wiki", help="the wiki's path")
    parser.add_argument("--topic", required=True, help="a short slug, e.g. pricing-tier")
    parser.add_argument(
        "--stated-by", default="user",
        help="who said it: 'user' (the default) or the person's page slug",
    )
    args = parser.parse_args()

    wiki = Path(args.wiki).expanduser().resolve()
    if not wiki.is_dir():
        sys.exit(f"error: {wiki} is not a directory")
    for flag, value in (("--topic", args.topic), ("--stated-by", args.stated_by)):
        if not ID_RE.fullmatch(value):
            sys.exit(
                f"error: {flag} must be lowercase letters, digits, '.', '_' and '-', "
                f"starting with a letter or digit: {value!r}"
            )
    statement = sys.stdin.read().strip()
    if not statement:
        sys.exit("error: no statement on stdin")

    path = capture(wiki, args.topic, args.stated_by, statement)
    print(f"path: {path.relative_to(wiki).as_posix()}")
    print(f"id: {path.stem}")


if __name__ == "__main__":
    main()
