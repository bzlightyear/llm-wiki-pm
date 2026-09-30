#!/usr/bin/env python3
"""Frontmatter parser and field writer for PM wiki pages.

The one reader of page frontmatter: lint.py, the pre-write hook and
session-start's stale scan all read pages through parse(), so they agree on
every page. It reads the frontmatter profile, the subset of YAML that pages
may use, in which every value is a string:

- `key: value` lines, keys `[a-z_][a-z0-9_]*`, each key once.
- A value is a plain or quoted string, or a flow list `[a, 'b, c']` on one
  line. Under an empty `key:` it is a block list of indented `- item` lines,
  or, for the persona keys, one level of indented `subkey: value` lines whose
  values are strings or one-line flow lists.
- A list item may continue on more-indented lines, joined with one space, or
  start with a `>-` marker whose lines below are kept as written and joined
  the same way, as YAML does.
- created, updated and last_verified are YYYY-MM-DD dates, quoted or not.
- Comments and blank lines are ignored.

Anything else is reported as an error rather than guessed at. Shapes that a
YAML library writes but the profile doesn't list (list items at column 0, a
value continued on the next line, `>-` on a key) are still read the way YAML
reads them, so no reader loses a value, and reported too.

set_field() and set_list() change one field in place and leave every other
byte of the page as it was, the way the Edit tool does. Scripts that edit
frontmatter use them instead of a YAML library's load-and-dump. They write
dates as 'YYYY-MM-DD', which both the wiki-search MCP's YAML library and
PyYAML keep unchanged.

slug(), citations() and resolve() apply references/citation-spec.md:
frontmatter declares the paths of records and pages, `[source: ...]` markers
cite IDs, and an ID is the slug() of the file it names.

Stdlib only.
"""

import re
from collections import namedtuple
from datetime import date, datetime
from pathlib import Path

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

DATE_KEYS = ("created", "updated", "last_verified")
PERSONA_KEYS = ("language_patterns", "tone_by_channel", "vocabulary_markers")
KEY_RE = re.compile(r"[a-z_][a-z0-9_]*")
DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")

# A `key:`, nested `  key:` or `- item` line; the last group is the rest of
# the line, from the whitespace after the ':' or '-'.
KEY_LINE_RE = re.compile(r"^([A-Za-z0-9_][A-Za-z0-9_.-]*):(?=[ \t]|$)(.*)$")
NESTED_LINE_RE = re.compile(r"^( +)([A-Za-z0-9_][A-Za-z0-9_.-]*):(?=[ \t]|$)(.*)$")
ITEM_LINE_RE = re.compile(r"^( *)-(?=[ \t]|$)(.*)$")

# rule is "R1" (list item on a key line), "R2" (list item under a closed flow
# list), "R5" (duplicate key) or "R12" (anything else outside the profile);
# line counts from the page's first line, the opening fence.
Error = namedtuple("Error", "rule line key message")


class _Bad(Exception):
    """A value outside the profile; the message says why."""


# ── Reading ──────────────────────────────────────────────────────────────────


def parse(text):
    """Parse a page's frontmatter. Returns (fields, errors); fields is None
    when the page has no frontmatter block."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, []
    return parse_block(m.group(1))


def parse_block(block):
    """Parse the text between the frontmatter fences. Returns (fields, errors).
    A value is a string, a list of strings, or, for a key with nested keys, a
    dict of those."""
    fields, errors, key_lines = {}, [], {}
    key = mode = None  # mode: "open", "list", "map", "flow" or "done"
    item_indent = map_indent = None
    cont = None  # the value that more-indented lines continue

    def error(rule, n, message):
        errors.append(Error(rule, n, key, message))

    for n, line in enumerate(block.split("\n"), start=2):
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))

        if cont and stripped and indent > cont.owner:
            if cont.kind == "plain":
                if "\t" in line or stripped.startswith("#") or re.search(r" #|: |:$", stripped):
                    error("R12", n, f"'{key}': a tab, ': ' or '#' in a continued value")
                    cont.kind = "skip"
                    continue
                if cont.report:
                    error("R12", n, cont.report)
                    cont.report = None
                cont.add(stripped)
            elif cont.kind == "folded":
                if cont.indent is None:
                    cont.indent = indent
                if indent != cont.indent or line[indent] == "\t":
                    error("R12", n, f"'{key}': the lines of a '>-' value are indented differently")
                    cont.kind = "skip"
                    continue
                cont.add(line[indent:])
            continue
        cont = None
        if "\t" in line[:len(line) - len(line.lstrip())]:
            error("R12", n, "a tab in the indentation")
            continue
        if not stripped or stripped.startswith("#"):
            continue

        m = KEY_LINE_RE.match(line)
        if m:
            key, rest = m.groups()
            key_lines[key] = n
            mode = "done"
            if not KEY_RE.fullmatch(key):
                error("R12", n, f"key '{key}' isn't lowercase letters, digits and underscores")
            if key in fields:
                error("R5", n, f"duplicate key '{key}'")
            if re.match(r"\s*-(?:\s|$)", rest):
                error("R1", n, f"list item on the key line of '{key}'")
                fields[key] = rest.strip()
                cont = _Open(None, None, 0, "skip")
                continue
            try:
                kind, value, end = _value(rest)
            except _Bad as e:
                error("R12", n, f"'{key}': {e}")
                fields[key] = rest.strip()
                cont = _Open(None, None, 0, "skip")
                continue
            fields[key] = value
            if kind == "empty":
                mode = "open"
            elif kind == "flow":
                mode = "flow"
            elif kind == "plain" and not rest[end:].strip():  # a comment ends it
                cont = _Open(fields, key, 0, "plain", value,
                             f"'{key}' continues on the next line; write it on one line")
            elif kind == "folded":
                error("R12", n, f"'{key}': '>-' is only in the profile on list items")
                cont = _Open(fields, key, 0, "folded")
            continue

        m = ITEM_LINE_RE.match(line)
        if m:
            indent, text = len(m.group(1)), m.group(2)
            if key is None:
                error("R12", n, "list item before any key")
                continue
            if mode == "open":
                fields[key], mode, item_indent = [], "list", indent
                if indent == 0:
                    error("R12", n, f"the list items of '{key}' aren't indented")
            elif mode == "flow":
                error("R2", n, f"list item under the closed flow list of '{key}'")
                cont = _Open(None, None, indent, "skip")
                continue
            elif mode != "list":
                error("R12", n, f"list item under '{key}', which already has a value")
                cont = _Open(None, None, indent, "skip")
                continue
            elif indent != item_indent:
                error("R12", n, f"list item of '{key}' indented differently from the first")
                cont = _Open(None, None, indent, "skip")
                continue
            items = fields[key]
            try:
                kind, value, end = _value(text)
                if kind == "flow":
                    raise _Bad("a list inside a list")
                if kind == "empty":
                    raise _Bad("an empty list item")
            except _Bad as e:
                error("R12", n, f"'{key}': {e}")
                cont = _Open(None, None, indent, "skip")
                continue
            items.append(value)
            if kind == "plain" and not text[end:].strip():  # a comment ends it
                cont = _Open(items, len(items) - 1, indent, kind, value)
            elif kind == "folded":
                cont = _Open(items, len(items) - 1, indent, kind)
            continue

        m = NESTED_LINE_RE.match(line)
        if m and key is not None:
            indent, sub, rest = len(m.group(1)), m.group(2), m.group(3)
            if mode == "open":
                fields[key], mode, map_indent = {}, "map", indent
                if key not in PERSONA_KEYS:
                    error("R12", n, f"'{key}' has nested keys; only the persona keys may")
            elif mode != "map" or indent != map_indent:
                error("R12", n, f"nested key '{sub}' where '{key}' can't take one")
                cont = _Open(None, None, indent, "skip")
                continue
            mapping = fields[key]
            if sub in mapping:
                error("R12", n, f"duplicate key '{sub}' under '{key}'")
            if not KEY_RE.fullmatch(sub):
                error("R12", n, f"key '{sub}' isn't lowercase letters, digits and underscores")
            try:
                kind, value, _ = _value(rest)
                if kind == "folded":
                    raise _Bad("'>-' is only in the profile on list items")
            except _Bad as e:
                error("R12", n, f"'{key}': {e}")
                value = rest.strip()
                cont = _Open(None, None, indent, "skip")
            mapping[sub] = value
            continue

        if indent:
            error("R12", n, "an indented line that belongs to no value")
        else:
            error("R12", n, "not a 'key: value' line")

    for k in DATE_KEYS:
        if k in fields and date_field(fields, k) is None:
            message = f"'{k}' isn't a YYYY-MM-DD date: {fields[k]!r}"
            errors.append(Error("R12", key_lines[k], k, message))
    return fields, errors


class _Open:
    """A string value that more-indented lines continue: a plain value (lines
    joined with one space), a '>-' value (its lines as written, joined the
    same way) or, for "skip", lines that belong to a value already reported."""

    def __init__(self, container, index, owner, kind, first=None, report=None):
        self.container, self.index, self.owner, self.kind = container, index, owner, kind
        self.parts = [] if first is None else [first]
        self.indent = None  # the indentation of a '>-' value's lines
        self.report = report  # reported on the first continuation line

    def add(self, text):
        self.parts.append(text)
        self.container[self.index] = " ".join(self.parts)


def _value(s):
    """Parse a one-line value, the text after `key:` or `-`. Returns (kind,
    value, end): kind is "empty", "plain", "quoted", "flow" or "folded" (a
    `>-` marker), and s[end:] holds only spaces and a comment."""
    i = _spaces(s, 0)
    if i == len(s) or s[i] == "#":
        return "empty", "", i
    c = s[i]
    if c == "[":
        value, end = _flow(s, i)
        kind = "flow"
    elif c in "'\"":
        value, end = _quoted(s, i)
        kind = "quoted"
    elif s.startswith(">-", i) and s[i + 2:i + 3] in ("", " ", "\t"):
        value, end, kind = "", i + 2, "folded"
    elif c in "|>":
        raise _Bad("block values other than '>-' are outside the profile")
    elif c == "{":
        raise _Bad("a {…} mapping is outside the profile")
    else:
        value, _ = _plain(s, i, flow=False)
        return "plain", value, i + len(value)
    k = _spaces(s, end)
    if k < len(s) and not (s[k] == "#" and k > end):
        raise _Bad("unexpected text after the value")
    return kind, value, end


def _spaces(s, j):
    """The index of the first non-space at or after s[j]. PyYAML reads no tab
    outside quotes, comments and '>-' text, so neither does the profile."""
    while j < len(s) and s[j] == " ":
        j += 1
    if j < len(s) and s[j] == "\t":
        raise _Bad("a tab outside quotes")
    return j


def _plain(s, i, flow):
    """Read the unquoted value that starts at s[i]. It ends at a comment, at
    the end of the line or, in a flow list, at ',' or ']'. Returns (value,
    index where reading stopped)."""
    c = s[i]
    if c in "[]{},#&*!|>'\"%@`" or (c in "-?:" and s[i + 1:i + 2] in ("", " ")):
        raise _Bad(f"a value can't start with {c!r} unless it is quoted")
    j = i
    while j < len(s):
        c = s[j]
        if c == "\t":
            raise _Bad("a tab outside quotes")
        if c == "#" and s[j - 1] == " ":
            break
        if c == ":" and (s[j + 1:j + 2] in ("", " ") or (flow and s[j + 1] in ",[]{}")):
            raise _Bad("a ': ' in a value that isn't quoted")
        if flow and c in ",]":
            break
        if flow and c in "[{}":
            raise _Bad(f"a {c!r} in a list item that isn't quoted")
        j += 1
    return s[i:j].rstrip(" "), j


def _flow(s, i):
    """Read the one-line flow list that starts at s[i] ('['). Returns (items,
    index after the closing bracket)."""
    items, j = [], i + 1
    while True:
        j = _spaces(s, j)
        if j < len(s) and s[j] == "]":
            return items, j + 1
        if j == len(s):
            raise _Bad("a flow list not closed on its line")
        if s[j] in "'\"":
            item, j = _quoted(s, j)
        elif s[j] in "[{":
            raise _Bad("a list or mapping inside a list")
        elif s[j] == ",":
            raise _Bad("an empty item in a flow list")
        else:
            item, j = _plain(s, j, flow=True)
        items.append(item)
        j = _spaces(s, j)
        if j < len(s) and s[j] == ",":
            j += 1
        elif j == len(s) or s[j] != "]":
            raise _Bad("a flow list not closed on its line")


_ESCAPES = {
    "0": "\0", "a": "\a", "b": "\b", "t": "\t", "\t": "\t", "n": "\n", "v": "\v",
    "f": "\f", "r": "\r", "e": "\x1b", " ": " ", '"': '"', "/": "/", "\\": "\\",
    "N": "\x85", "_": "\xa0", "L": "\u2028", "P": "\u2029",
}
_HEX_ESCAPES = {"x": 2, "u": 4, "U": 8}


def _quoted(s, i):
    """Read the quoted value that starts at s[i]. Returns (value, index after
    the closing quote)."""
    q, out, j = s[i], [], i + 1
    while j < len(s):
        c = s[j]
        if c == q:
            if q == "'" and s[j + 1:j + 2] == "'":  # '' is a quote inside '…'
                out.append("'")
                j += 2
                continue
            return "".join(out), j + 1
        if c == "\\" and q == '"':
            e = s[j + 1:j + 2]
            n = _HEX_ESCAPES.get(e, 0)
            digits = s[j + 2:j + 2 + n]
            if e in _ESCAPES:
                out.append(_ESCAPES[e])
                j += 2
            elif n and len(digits) == n and all(d in "0123456789abcdefABCDEF" for d in digits):
                out.append(chr(int(digits, 16)))
                j += 2 + n
            else:
                raise _Bad("an unknown escape in a double-quoted value")
            continue
        out.append(c)
        j += 1
    raise _Bad("a quote not closed on its line")


def str_field(fields, key):
    """The value of `key` if it is a string, else ""."""
    value = fields.get(key) if fields else None
    return value if isinstance(value, str) else ""


def list_field(fields, key):
    """The value of `key` if it is a list, else []."""
    value = fields.get(key) if fields else None
    return value if isinstance(value, list) else []


def date_field(fields, key):
    """The value of `key` as a date, or None unless it is a YYYY-MM-DD string."""
    value = str_field(fields, key)
    return _date(value) if DATE_RE.fullmatch(value) else None


def sources(fields):
    """The page's `sources:` entries ([] when absent or not a list)."""
    return list_field(fields, "sources")


def _date(value):
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


# ── Writing ──────────────────────────────────────────────────────────────────


def set_field(text, key, value):
    """Return `text` with the frontmatter field `key` set to `value`, a string
    or a date, and every other byte unchanged. The field is replaced where it
    is, or added at the end of the frontmatter when absent, and a trailing
    comment on its key line is kept. Raises ValueError rather than guess (see
    _replace), and when created, updated or last_verified isn't given a date."""
    value = _string(value)
    if key in DATE_KEYS and not (DATE_RE.fullmatch(value) and _date(value)):
        raise ValueError(f"'{key}' must be a YYYY-MM-DD date, not {value!r}")
    return _replace(text, key, lambda old: [f"{key}: {_render(value)}"])


def set_list(text, key, items):
    """Return `text` with the frontmatter field `key` set to the list `items`,
    and every other byte unchanged. A flow list stays a flow list; any other
    value becomes a block list, indented like the list it replaces."""
    items = [_string(item) for item in items]

    def lines(old):
        if not items:
            return [f"{key}: []"]
        if old and _is_flow(old[0]):
            return [f"{key}: [" + ", ".join(_render(item, flow=True) for item in items) + "]"]
        indents = [m.group(1) for m in map(ITEM_LINE_RE.match, old[1:]) if m]
        indent = indents[0] if indents and indents[0] else "  "
        return [f"{key}:"] + [f"{indent}- {_render(item)}" for item in items]

    return _replace(text, key, lines)


def _string(value):
    if isinstance(value, date) and not isinstance(value, datetime):
        value = value.isoformat()
    if not isinstance(value, str):
        raise TypeError(f"frontmatter values are strings, not {type(value).__name__}")
    if "\n" in value or "\r" in value:
        raise ValueError(f"frontmatter values are one line: {value!r}")
    return value


def _render(value, flow=False):
    """`value` as written in frontmatter: single-quoted when it is a date or
    wouldn't read back unchanged without quotes, else as it is."""
    try:
        if flow:
            plain = _flow(f"[{value}]", 0) == ([value], len(value) + 2)
        else:
            plain = _value(value)[:2] == ("plain", value)
    except _Bad:
        plain = False
    if plain and not DATE_RE.fullmatch(value):
        return value
    return "'" + value.replace("'", "''") + "'"


def _is_flow(key_line):
    rest = KEY_LINE_RE.match(key_line).group(2)
    try:
        return _value(rest)[0] == "flow"
    except _Bad:
        return False


def _replace(text, key, make_lines):
    """Replace the lines of frontmatter field `key` with make_lines(old lines),
    or append make_lines([]) when the key is absent. Raises ValueError when
    the page has no frontmatter, the key appears twice, or a comment or blank
    line sits inside the field, since any of those makes the field's extent
    a guess."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError("the page has no frontmatter block")
    lines = m.group(1).split("\n")
    starts = [i for i, line in enumerate(lines) if _key_of(line) == key]
    if len(starts) > 1:
        raise ValueError(f"duplicate key '{key}'; fix it by hand first")
    if not starts:
        lines = (lines if lines != [""] else []) + make_lines([])
    else:
        start = end = starts[0]
        for i in range(start + 1, len(lines)):
            line = lines[i]
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if line.startswith((" ", "\t")) or ITEM_LINE_RE.match(line):
                end = i
                continue
            break
        old = lines[start:end + 1]
        if any(not line.strip() or line.lstrip().startswith("#") for line in old[1:]):
            raise ValueError(f"a comment or blank line inside '{key}'; edit it by hand")
        new = make_lines(old)
        new[0] += _comment(old[0])
        lines[start:end + 1] = new
    return text[:m.start(1)] + "\n".join(lines) + text[m.end(1):]


def _key_of(line):
    m = KEY_LINE_RE.match(line)
    return m.group(1) if m else None


def _comment(key_line):
    """The trailing comment of a key line, with the spaces before it, or ""."""
    rest = KEY_LINE_RE.match(key_line).group(2)
    try:
        end = _value(rest)[2]
    except _Bad:
        return ""
    at = len(key_line) - len(rest) + end
    if "#" not in key_line[at:]:
        return ""
    at += key_line[at:].index("#")
    while key_line[at - 1] == " ":
        at -= 1
    return key_line[at:].rstrip()


# ── Sources and citations ────────────────────────────────────────────────────

# The folders that hold pages. A record is any .md file under raw/ outside
# raw/assets/.
PAGE_DIRS = ("entities", "concepts", "comparisons", "queries", "briefings")
ID_RE = re.compile(r"[a-z0-9][a-z0-9._-]*")

MARKER_RE = re.compile(r"\[source:", re.IGNORECASE)
BLANK_LINE_RE = re.compile(r"\n[ \t]*\n")
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")

# How a marker can break the citation grammar (lint rule R7). The mechanical
# ones are what lint --auto-fix=content repairs.
PROBLEMS = ("wrapped", "nested prefix", "vs.", "path", "url", "wikilink",
            "not an ID", "not closed")
MECHANICAL = ("wrapped", "nested prefix", "vs.", "path")

# id is what the citation names; problems are its PROBLEMS; body[start:end]
# is the whole marker, shared by the citations in it.
Citation = namedtuple("Citation", "id location problems start end")
# kind is "record", "page" or None; problem is None for a valid entry.
Resolution = namedtuple("Resolution", "kind path problem")


def slug(path):
    """The ID of a page or record: its filename stem, or the folder's name
    for a directory page's README.md. The one ID function: a page is linked,
    cited and snapshotted by it, and a sources: entry resolves by it."""
    path = Path(path)
    if path.name == "README.md":
        return path.parent.name
    return path.stem


def citations(body):
    """Every citation in the `[source: ...]` markers of `body`, the page text
    after its frontmatter, in order. A marker ends at the first ']' outside
    a [[wikilink]]; one that meets a blank line first is "not closed". The ID
    is what a citation names once the mechanical defects are undone: a
    path's slug, a wrapped ID joined up again, a nested "source:" dropped,
    "a vs. b" read as two citations, a wikilink's target."""
    found = []
    for m in MARKER_RE.finditer(body):
        end = _marker_end(body, m.end())
        if end is None:
            found.append(Citation("", "", ("not closed",), m.start(), m.end()))
            continue
        inner = body[m.end():end - 1]
        wrapped = "\n" in inner
        # a marker wrapped inside a blockquote continues after a '>'
        inner = re.sub(r"\n[ \t]*(?:>[ \t]?)*", "\n", inner)
        for part in inner.split(";"):
            found.extend(_part_citations(part, wrapped, m.start(), end))
    return found


def _marker_end(body, i):
    """The index just past the ']' that closes the marker whose text starts
    at body[i], or None when a blank line or the end of `body` comes first."""
    depth = 0  # inside a [[wikilink]]
    while i < len(body):
        if body.startswith("[[", i):
            depth, i = depth + 1, i + 2
        elif depth and body.startswith("]]", i):
            depth, i = depth - 1, i + 2
        elif body[i] == "]" and not depth:
            return i + 1
        elif body[i] == "\n" and BLANK_LINE_RE.match(body, i):
            return None
        else:
            i += 1
    return None


def _part_citations(part, wrapped, start, end):
    """The citations in one ';'-separated part of a marker: one, or two or
    more joined with "vs.". The location, after the first ',', goes with the
    last of them."""
    problems = ["wrapped"] if wrapped else []
    part = part.strip()
    prefix = re.match(r"(?:source:\s*)+", part, re.IGNORECASE)
    if prefix:
        problems.append("nested prefix")
        part = part[prefix.end():]
    if "[[" in part:
        problems.append("wikilink")
    text, _, location = part.partition(",")
    location = " ".join(location.split())
    names = re.split(r"\s+vs\.?\s+", text.strip())
    if len(names) > 1:
        problems.append("vs.")
    found = []
    for n, name in enumerate(names):
        cid, more = _cited_id(name)
        found.append(Citation(cid, location if n == len(names) - 1 else "",
                              tuple(problems + more), start, end))
    return found


def _cited_id(text):
    """The ID a citation's text names, and what else is wrong with it."""
    if "\n" in text:
        joined = re.sub(r"\s*\n\s*", "", text)  # a hard-wrapped ID
        text = joined if ID_RE.fullmatch(joined) or _is_path(joined) else " ".join(text.split())
    link = WIKILINK_RE.fullmatch(text)
    if link:
        return link.group(1).strip(), []  # "wikilink" is already noted
    if re.match(r"https?://", text):
        return text, ["url"]
    if _is_path(text):
        return slug(text), ["path"]
    return text, ([] if ID_RE.fullmatch(text) else ["not an ID"])


def _is_path(text):
    return (text.endswith(".md") and "/" in text and not text.startswith("/")
            and not any(c.isspace() for c in text))


def resolve(entry, wiki):
    """Resolve one sources: entry. Returns Resolution(kind, path, problem):
    kind is what the entry names, "record" for a path under raw/ and "page"
    for a path in a page folder, whether or not the file exists, or None for
    anything else; path is that file; problem is None when the entry is the
    path of an existing record or page, else why it isn't (lint rule R6)."""
    parts = entry.split("/")
    if re.match(r"https?://", entry):
        return Resolution(None, None, "a URL: capture it as a record")
    if parts[:2] == ["raw", "assets"]:
        return Resolution(None, None, "an asset: declare its record")
    if not entry.endswith(".md"):
        if len(parts) == 1 and ID_RE.fullmatch(entry):
            return Resolution(None, None, "a bare name, not a path")
        if len(parts) > 1 and not any(c.isspace() for c in entry):
            return Resolution(None, None, "not a markdown file")
        return Resolution(None, None, "not a path")
    if entry.startswith("~") or any(p in ("", ".", "..") for p in parts):
        return Resolution(None, None, "not a path inside the wiki")
    if len(parts) == 1:
        return Resolution(None, None, "a root file isn't a source")
    if parts[0] == "raw":
        kind = "record"
    elif parts[0] in PAGE_DIRS and "assets" not in parts[2:-1]:
        kind = "page"
    elif parts[0] in PAGE_DIRS:
        return Resolution(None, None, "an artifact under assets/ isn't a page")
    elif parts[0] == "_archive":
        return Resolution(None, None, "an archive snapshot isn't a source")
    else:
        return Resolution(None, None, "not in raw/ or a page folder")
    path = Path(wiki) / entry
    return Resolution(kind, path, None if path.is_file() else "no such file")
