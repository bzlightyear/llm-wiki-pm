"""
Tests for skills/llm-wiki-pm/scripts/wikifm.py, the frontmatter parser and
field writer, and for session-start's stale scan, which reads dates and tags
through it.

The oracle tests compare wikifm with PyYAML's BaseLoader, which reads every
value as a string, and skip when PyYAML isn't installed. The whole-wiki tests
run only when WIKIFM_WIKI points at a wiki; they only read it:

    WIKIFM_WIKI=~/path/to/wiki python3 -m pytest tests/test_wikifm.py

Run: python3 -m pytest tests/test_wikifm.py -v
"""

from __future__ import annotations

import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from test_hooks import REPO_ROOT, SESSION_START, make_wiki, run_hook, session_start_payload

sys.path.insert(0, str(REPO_ROOT / "skills" / "llm-wiki-pm" / "scripts"))
import wikifm  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures: frontmatter blocks (the text between the --- fences)
# ---------------------------------------------------------------------------

# In the profile: parse_block() reads these with no errors.
CLEAN = {
    "plain values": (
        "title: Competitor X pricing\ntype: entity\nshareable: false\n"
        "confidence_decay_days: 60\n",
        {"title": "Competitor X pricing", "type": "entity", "shareable": "false",
         "confidence_decay_days": "60"},
    ),
    "quoted values": (
        "title: 'It''s a \"page\"'\ncoverage: \"partial\"\nnote: \"tab\\there \\u00e9\"\n",
        {"title": 'It\'s a "page"', "coverage": "partial", "note": "tab\there \u00e9"},
    ),
    "empty values": (
        "superseded_by:\ngaps: []\n",
        {"superseded_by": "", "gaps": []},
    ),
    "flow lists": (
        "tags: [pricing, competitive]\n"
        "sources: [raw/a.md, \"user, conversation, 2026-01-15\", 'b, c',]\n",
        {"tags": ["pricing", "competitive"],
         "sources": ["raw/a.md", "user, conversation, 2026-01-15", "b, c"]},
    ),
    "block lists": (
        "sources:\n  - raw/articles/a-2026-01-15.md\n"
        "  - 'user, conversation, 2026-01-15'\n  - \"q\"\n",
        {"sources": ["raw/articles/a-2026-01-15.md", "user, conversation, 2026-01-15", "q"]},
    ),
    "wrapped list item": (
        "gaps:\n  - pricing for the enterprise tier\n    is not public yet\n"
        "  - renewal date\n",
        {"gaps": ["pricing for the enterprise tier is not public yet", "renewal date"]},
    ),
    # How the wiki-search MCP writes long list items: the text under '>-' is
    # kept as written, so ': ' and '#' in it are text.
    "folded list items": (
        "gaps:\n  - >-\n    pricing for the enterprise tier is not\n"
        "    public: see the 2026-01-15 call # not a comment\n"
        "  - >-\n    one line\n  - short\n",
        {"gaps": ["pricing for the enterprise tier is not public: see the "
                  "2026-01-15 call # not a comment", "one line", "short"]},
    ),
    "persona keys": (
        "language_patterns:\n  sentence_length: short\n  capitalization: standard\n"
        "vocabulary_markers:\n  hedging_level: low\n  signoff_patterns: [thanks, cheers]\n",
        {"language_patterns": {"sentence_length": "short", "capitalization": "standard"},
         "vocabulary_markers": {"hedging_level": "low", "signoff_patterns": ["thanks", "cheers"]}},
    ),
    # As in the persona template and SCHEMA.md's field list.
    "comments and blank lines": (
        "# a comment\ntitle: t  # trailing\n\ntags: [a] # trailing\n"
        "sources:  # trailing\n  - raw/a.md  # trailing\n\n  - raw/b.md\n"
        "tone_by_channel:        # one key per channel\n"
        "  private_chat: \"\"        # e.g. direct messages\n",
        {"title": "t", "tags": ["a"], "sources": ["raw/a.md", "raw/b.md"],
         "tone_by_channel": {"private_chat": ""}},
    ),
    "dates in every accepted form": (
        "created: 2026-01-15\nupdated: '2026-02-01'\nlast_verified: \"2026-03-01\"\n",
        {"created": "2026-01-15", "updated": "2026-02-01", "last_verified": "2026-03-01"},
    ),
    "values YAML reads as text": (
        "a: https://example.com/a#b\nb: x:y [z], w\nc: -5\nd: ~\ne: null\n"
        "f: the team's page — notes\ng: '#1'\n",
        {"a": "https://example.com/a#b", "b": "x:y [z], w", "c": "-5", "d": "~",
         "e": "null", "f": "the team's page — notes", "g": "#1"},
    ),
    "tabs inside quotes, comments and '>-' text": (
        "title: 'a\tb'  # c\td\ngaps:\n  - >-\n    x\ty\n",
        {"title": "a\tb", "gaps": ["x\ty"]},
    ),
}

# Outside the profile: parse_block() reports each (rule, line), counting the
# opening fence as line 1. Where YAML has a clear reading, parse_block()
# still returns it, so no reader loses a value (the dict; None skips that
# check).
OUTSIDE = {
    "R1 list item on the key line": (
        "tags: - roadmap\n", [("R1", 2)], {"tags": "- roadmap"}),
    "R2 list item under a closed flow list": (
        "sources: [a.md]\n  - b.md\n", [("R2", 3)], {"sources": ["a.md"]}),
    "R5 duplicate key": (
        "coverage: stub\ncoverage: comprehensive\n", [("R5", 3)],
        {"coverage": "comprehensive"}),
    "timestamp date": (
        "created: 2026-09-03T00:00:00.000Z\n", [("R12", 2)],
        {"created": "2026-09-03T00:00:00.000Z"}),
    "impossible date": (
        "updated: 2026-02-30\n", [("R12", 2)], {"updated": "2026-02-30"}),
    "list items at column 0": (
        "sources:\n- raw/a.md\n- raw/b.md\n", [("R12", 3)],
        {"sources": ["raw/a.md", "raw/b.md"]}),
    "value continued on the next line": (
        "title: a long\n  title\n", [("R12", 3)], {"title": "a long title"}),
    "'>-' on a key": (
        "title: >-\n  a long\n  title\n", [("R12", 2)], {"title": "a long title"}),
    "nested keys outside the persona keys": (
        "meta:\n  owner: x\n", [("R12", 3)], {"meta": {"owner": "x"}}),
    "key outside the grammar": (
        "Title: x\n", [("R12", 2)], {"Title": "x"}),
    "literal block value": (
        "notes: |\n  line one\n  line two\n", [("R12", 2)], None),
    "block value on a list item": (
        "gaps:\n  - |\n    a\n", [("R12", 3)], None),
    "flow list over two lines": (
        "tags: [a,\n  b]\n", [("R12", 2)], None),
    "quote not closed on its line": (
        "title: 'open\n", [("R12", 2)], None),
    "text after a quoted value": (
        "title: 'a' b\n", [("R12", 2)], None),
    "flow mapping": (
        "tone_by_channel: {}\n", [("R12", 2)], None),
    "anchor": (
        "title: &t x\n", [("R12", 2)], None),
    "': ' in a value": (
        "title: a: b\n", [("R12", 2)], None),
    "comment inside a flow list": (
        "tags: [a # c, b]\n", [("R12", 2)], None),
    "list inside a list": (
        "tags:\n  - [a, b]\n", [("R12", 3)], None),
    "empty list item": (
        "tags:\n  -\n  - a\n", [("R12", 3)], None),
    "list items indented differently": (
        "tags:\n    - a\n  - b\n", [("R12", 4)], None),
    "blank line inside a wrapped item": (
        "gaps:\n  - a\n\n    b\n", [("R12", 5)], None),
    "comment inside a wrapped value": (
        "title: a\n# c\n  b\n", [("R12", 4)], None),
    "value wrapped after a trailing comment": (
        "gaps:\n  - a # c\n    b\n", [("R12", 4)], None),
    "'>-' lines indented differently": (
        "gaps:\n  - >-\n    a\n      b\n", [("R12", 5)], None),
    "key without a space after the colon": (
        "title:x\n", [("R12", 2)], None),
    "tab indentation": (
        "tags:\n\t- a\n", [("R12", 3)], None),
    # PyYAML reads no tab outside quotes, comments and '>-' text.
    "tab inside a value": (
        "title: a\tb\n", [("R12", 2)], None),
    "tab after a value": (
        "title: x\t\n", [("R12", 2)], None),
    "tab before a comment": (
        "title: 'x'\t# c\n", [("R12", 2)], None),
    "tab in a flow list": (
        "tags: [a,\tb]\n", [("R12", 2)], None),
    "tab-only line": (
        "title: x\n\t\ntype: y\n", [("R12", 3)], None),
}


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", CLEAN)
def test_profile_shapes_parse_cleanly(name):
    block, expected = CLEAN[name]
    assert wikifm.parse_block(block) == (expected, [])


@pytest.mark.parametrize("name", OUTSIDE)
def test_shapes_outside_the_profile_are_reported(name):
    block, expected_errors, expected_fields = OUTSIDE[name]
    fields, errors = wikifm.parse_block(block)
    assert [(e.rule, e.line) for e in errors] == expected_errors
    if expected_fields is not None:
        assert fields == expected_fields


def test_parse_reads_only_the_frontmatter_block():
    text = "---\ntitle: t\ntags: - x\n---\n# Body\ntitle: not frontmatter\n"
    fields, errors = wikifm.parse(text)
    assert fields == {"title": "t", "tags": "- x"}
    assert [(e.rule, e.line, e.key) for e in errors] == [("R1", 3, "tags")]


def test_no_frontmatter_block():
    assert wikifm.parse("# Just a body\n") == (None, [])


def test_accessors_return_empty_for_the_wrong_type():
    fields = {"type": ["entity"], "tags": "roadmap", "updated": ["2026-01-01"]}
    assert wikifm.str_field(fields, "type") == ""
    assert wikifm.list_field(fields, "tags") == []
    assert wikifm.date_field(fields, "updated") is None
    assert wikifm.sources(None) == [] and wikifm.str_field(None, "type") == ""


def test_date_field_reads_only_calendar_dates():
    fields = {"a": "2026-01-15", "b": "2026-01-15T00:00:00.000Z",
              "c": "2026-02-30", "d": "15/01/2026"}
    assert wikifm.date_field(fields, "a") == date(2026, 1, 15)
    assert [wikifm.date_field(fields, k) for k in "bcd"] == [None, None, None]


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

PAGE = (
    "---\n"
    "title: Competitor X\n"
    "created: 2026-01-15\n"
    "updated: 2026-01-20  # last edit\n"
    "type: entity\n"
    "tags: [pricing, competitive]\n"
    "sources:\n"
    "  - raw/articles/competitor-x-pricing-2026-01-15.md\n"
    "  - raw/internal/pricing-notes-2026-01-20.md\n"
    "gaps:\n"
    "  - >-\n"
    "    enterprise pricing\n"
    "    not public\n"
    "coverage: partial\n"
    "---\n"
    "# Competitor X\n"
    "\n"
    "updated: body text that looks like a field\n"
)


def test_set_field_replaces_one_field_in_place():
    after = wikifm.set_field(PAGE, "coverage", "comprehensive")
    assert after == PAGE.replace("coverage: partial\n", "coverage: comprehensive\n")


def test_set_field_writes_dates_quoted_and_keeps_a_trailing_comment():
    after = wikifm.set_field(PAGE, "updated", date(2026, 2, 1))
    assert after == PAGE.replace("updated: 2026-01-20  # last edit\n",
                                 "updated: '2026-02-01'  # last edit\n")


def test_set_field_appends_a_missing_field():
    after = wikifm.set_field(PAGE, "last_verified", "2026-02-01")
    assert after == PAGE.replace("coverage: partial\n---\n",
                                 "coverage: partial\nlast_verified: '2026-02-01'\n---\n")


def test_set_field_replaces_a_whole_list():
    after = wikifm.set_field(PAGE, "gaps", "none known")
    assert after == PAGE.replace(
        "gaps:\n  - >-\n    enterprise pricing\n    not public\n", "gaps: none known\n")


def test_set_list_keeps_a_block_list_block():
    after = wikifm.set_list(PAGE, "sources", ["raw/a.md", "user, conversation", "2026-01-15"])
    assert after == PAGE.replace(
        "  - raw/articles/competitor-x-pricing-2026-01-15.md\n"
        "  - raw/internal/pricing-notes-2026-01-20.md\n",
        "  - raw/a.md\n  - user, conversation\n  - '2026-01-15'\n")


def test_set_list_keeps_a_flow_list_flow():
    after = wikifm.set_list(PAGE, "tags", ["pricing", "a, b", "2026-01-15"])
    assert after == PAGE.replace("tags: [pricing, competitive]\n",
                                 "tags: [pricing, 'a, b', '2026-01-15']\n")


def test_set_list_empty_and_new_lists():
    assert wikifm.set_list(PAGE, "gaps", []) == PAGE.replace(
        "gaps:\n  - >-\n    enterprise pricing\n    not public\n", "gaps: []\n")
    assert wikifm.set_list(PAGE, "supersedes", ["old-page"]) == PAGE.replace(
        "coverage: partial\n---\n", "coverage: partial\nsupersedes:\n  - old-page\n---\n")


def test_set_list_indents_column_0_items():
    text = "---\ntitle: t\nsources:\n- raw/a.md\n---\n"
    assert wikifm.set_list(text, "sources", ["raw/b.md"]) == (
        "---\ntitle: t\nsources:\n  - raw/b.md\n---\n")


def test_writers_refuse_rather_than_guess():
    page = "---\ntitle: t\n---\n"
    with pytest.raises(ValueError):
        wikifm.set_field("# no frontmatter\n", "title", "t")
    with pytest.raises(ValueError):
        wikifm.set_field("---\na: 1\na: 2\n---\n", "a", "3")
    with pytest.raises(ValueError):
        wikifm.set_field(page, "title", "two\nlines")
    with pytest.raises(ValueError):
        wikifm.set_field(page, "updated", "yesterday")
    with pytest.raises(ValueError):
        wikifm.set_list("---\ntags:\n  - a\n  # why\n  - b\n---\n", "tags", ["c"])
    with pytest.raises(TypeError):
        wikifm.set_field(page, "title", 3)
    with pytest.raises(TypeError):
        wikifm.set_field(page, "updated", datetime(2026, 1, 1, 9, 30))


# Values a naive writer would get wrong without quotes.
AWKWARD = [
    "", " lead", "trail ", "a: b", "a #b", "#a", "- a", "-a", "? a", "[a]", "{a}",
    "'q'", '"q"', "it's", "a, b", "a]b", "&a", "*a", "!a", "|a", ">a", ">-", "%a",
    "@a", "`a`", "a:", "https://x.com/a#b", "yes", "null", "~", "2026-01-15",
    "2026-01-15T00:00:00.000Z", "tab\tinside", "ünïcode — dash",
]


def written(value):
    """A page with `value` written by set_field, by set_list as a block list,
    and by set_list as a flow list."""
    page = "---\ntitle: t\nflow: []\n---\n"
    page = wikifm.set_field(page, "note", value)
    page = wikifm.set_list(page, "block", [value, "x"])
    return wikifm.set_list(page, "flow", [value, "x"])


@pytest.mark.parametrize("value", AWKWARD)
def test_written_values_read_back_unchanged(value):
    fields, errors = wikifm.parse(written(value))
    assert errors == []
    assert (fields["note"], fields["block"], fields["flow"]) == (value, [value, "x"], [value, "x"])


# ---------------------------------------------------------------------------
# PyYAML as the oracle
# ---------------------------------------------------------------------------

REJECTED = object()


@pytest.fixture(scope="module")
def base_load():
    yaml = pytest.importorskip("yaml")

    def load(block):
        try:
            return yaml.load(block, Loader=yaml.BaseLoader)
        except yaml.YAMLError:
            return REJECTED

    return load


def agrees_or_reports(block, load):
    """parse_block() reads the block as YAML does or reports an error, and it
    always reports an error when YAML rejects the block."""
    fields, errors = wikifm.parse_block(block)
    expected = load(block)
    if expected is REJECTED:
        return bool(errors)
    return bool(errors) or fields == (expected or {})


@pytest.mark.parametrize("name", list(CLEAN) + list(OUTSIDE))
def test_agrees_with_pyyaml_or_reports(name, base_load):
    block = (CLEAN.get(name) or OUTSIDE.get(name))[0]
    assert agrees_or_reports(block, base_load)


@pytest.mark.parametrize("name", CLEAN)
def test_profile_shapes_read_as_pyyaml_reads_them(name, base_load):
    block, expected = CLEAN[name]
    assert base_load(block) == expected


def test_duplicate_key_is_the_documented_disagreement(base_load):
    """YAML keeps the last value without a word; wikifm keeps it too, but
    reports R5, because the first value was silently lost."""
    block = "coverage: stub\ncoverage: comprehensive\n"
    assert base_load(block) == {"coverage": "comprehensive"}
    fields, errors = wikifm.parse_block(block)
    assert fields == {"coverage": "comprehensive"} and [e.rule for e in errors] == ["R5"]


@pytest.mark.parametrize("value", AWKWARD)
def test_written_values_read_back_unchanged_by_pyyaml(value, base_load):
    block = wikifm.FRONTMATTER_RE.match(written(value)).group(1)
    loaded = base_load(block)
    assert (loaded["note"], loaded["block"], loaded["flow"]) == (value, [value, "x"], [value, "x"])


# ---------------------------------------------------------------------------
# A real wiki (opt-in: set WIKIFM_WIKI)
# ---------------------------------------------------------------------------

WIKI = os.environ.get("WIKIFM_WIKI")
needs_wiki = pytest.mark.skipif(not WIKI, reason="set WIKIFM_WIKI to a wiki's path")


def wiki_texts():
    files = sorted(Path(WIKI).expanduser().rglob("*.md"))
    assert files, f"no .md files under {WIKI}"
    return [p.read_text(encoding="utf-8", errors="replace") for p in files]


@needs_wiki
def test_whole_wiki_parses_without_exceptions():
    for text in wiki_texts():
        wikifm.parse(text)


@needs_wiki
def test_whole_wiki_agrees_with_pyyaml_or_reports(base_load):
    blocks = [m.group(1) for m in map(wikifm.FRONTMATTER_RE.match, wiki_texts()) if m]
    disagreeing = [b for b in blocks if not agrees_or_reports(b, base_load)]
    assert not disagreeing, f"{len(disagreeing)} of {len(blocks)} frontmatter blocks"


# ---------------------------------------------------------------------------
# slug(), citations() and resolve(): references/citation-spec.md
# ---------------------------------------------------------------------------


def test_slug_is_the_stem_or_a_directory_pages_folder():
    assert wikifm.slug("raw/articles/competitor-x-pricing-2026-01-15.md") == (
        "competitor-x-pricing-2026-01-15"
    )
    assert wikifm.slug(Path("queries/pricing-deep-dive/README.md")) == "pricing-deep-dive"


def cites(body):
    """(id, location, problems) for each citation in `body`."""
    return [(c.id, c.location, c.problems) for c in wikifm.citations(body)]


def test_citations_in_the_grammar():
    body = (
        'Competitor X lists three tiers [source: competitor-x-pricing-2026-01-15, "Plans"].\n'
        "The team chose usage-based billing [source: conversation-2026-01-15-pricing-tier].\n"
        "ARR was flat [source: metric-arr-202601, query saved-query-123].\n"
        'Two sources agree [source: vendor-y-docs-2026, "Hooks"; competitor-x-docs-2026, "Hooks"].\n'
        "Per the digest [source: crystallize-pricing-review-2026-01-10, Decisions].\n"
    )
    assert cites(body) == [
        ("competitor-x-pricing-2026-01-15", '"Plans"', ()),
        ("conversation-2026-01-15-pricing-tier", "", ()),
        ("metric-arr-202601", "query saved-query-123", ()),
        ("vendor-y-docs-2026", '"Hooks"', ()),
        ("competitor-x-docs-2026", '"Hooks"', ()),
        ("crystallize-pricing-review-2026-01-10", "Decisions", ()),
    ]


def test_the_id_ends_at_the_first_comma():
    assert cites("[source: user, conversation (planning call), 2026-01-15]") == [
        ("user", "conversation (planning call), 2026-01-15", ())
    ]


# Each ID is what the citation names once the mechanical defects are undone.
OUTSIDE_THE_GRAMMAR = {
    "path form": (
        "[source: raw/articles/competitor-x-pricing-2026-01-15.md]",
        [("competitor-x-pricing-2026-01-15", "", ("path",))],
    ),
    "directory page path": (
        "[source: queries/pricing-deep-dive/README.md, Findings]",
        [("pricing-deep-dive", "Findings", ("path",))],
    ),
    "nested prefix": (
        "[source: source: competitor-x-pricing-2026-01-15]",
        [("competitor-x-pricing-2026-01-15", "", ("nested prefix",))],
    ),
    "ID wrapped mid-word": (
        "[source: competitor-x-\n  pricing-2026-01-15, p.3]",
        [("competitor-x-pricing-2026-01-15", "p.3", ("wrapped",))],
    ),
    "wrapped between citations": (
        "[source: vendor-y-docs-2026, section\n  2; competitor-x-docs-2026]",
        [("vendor-y-docs-2026", "section 2", ("wrapped",)),
         ("competitor-x-docs-2026", "", ("wrapped",))],
    ),
    "wrapped inside a blockquote": (
        "> Quoted [source: vendor-y-docs-2026;\n> source: competitor-x-docs-2026, p.2]",
        [("vendor-y-docs-2026", "", ("wrapped",)),
         ("competitor-x-docs-2026", "p.2", ("wrapped", "nested prefix"))],
    ),
    "wrapped prose isn't joined": (
        "[source: the pricing\n  page]",
        [("the pricing page", "", ("wrapped", "not an ID"))],
    ),
    "vs.": (
        '[source: vendor-y-docs-2026 vs. competitor-x-docs-2026, "Hooks"]',
        [("vendor-y-docs-2026", "", ("vs.",)),
         ("competitor-x-docs-2026", '"Hooks"', ("vs.",))],
    ),
    "vs without a dot": (
        "[source: vendor-y-docs-2026 vs competitor-x-docs-2026]",
        [("vendor-y-docs-2026", "", ("vs.",)), ("competitor-x-docs-2026", "", ("vs.",))],
    ),
    "wikilink": (
        "[source: [[crystallize-pricing-review-2026-01-10]]]",
        [("crystallize-pricing-review-2026-01-10", "", ("wikilink",))],
    ),
    "wikilink in the location": (
        "[source: vendor-y-docs-2026, see [[pricing-deep-dive]]]",
        [("vendor-y-docs-2026", "see [[pricing-deep-dive]]", ("wikilink",))],
    ),
    "URL": (
        "[source: https://example.com/pricing, 2026-01-15]",
        [("https://example.com/pricing", "2026-01-15", ("url",))],
    ),
    "root file and prose": (
        "[source: SCHEMA.md org chart]",
        [("SCHEMA.md org chart", "", ("not an ID",))],
    ),
    "empty": ("[source: ]", [("", "", ("not an ID",))]),
    "not closed": ("[source: vendor-y-docs-2026\n\nNext paragraph.]", [("", "", ("not closed",))]),
}


@pytest.mark.parametrize("name", OUTSIDE_THE_GRAMMAR)
def test_citations_outside_the_grammar(name):
    body, expected = OUTSIDE_THE_GRAMMAR[name]
    assert cites(body) == expected


def test_vs_in_a_location_is_prose():
    assert cites("[source: vendor-y-docs-2026, pricing vs. packaging]") == [
        ("vendor-y-docs-2026", "pricing vs. packaging", ())
    ]


def test_citations_share_their_markers_span():
    body = "A [source: vendor-y-docs-2026; competitor-x-docs-2026, p.2] B [source: x-2026]"
    found = wikifm.citations(body)
    assert [body[c.start:c.end] for c in found] == [
        "[source: vendor-y-docs-2026; competitor-x-docs-2026, p.2]",
        "[source: vendor-y-docs-2026; competitor-x-docs-2026, p.2]",
        "[source: x-2026]",
    ]


def test_resolve_classifies_by_what_an_entry_names(tmp_path):
    for rel in ("raw/articles/a-2026.md", "queries/deep-dive/README.md", "briefings/2026-01-15.md"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("x\n")
    resolved = {e: wikifm.resolve(e, tmp_path) for e in (
        "raw/articles/a-2026.md", "queries/deep-dive/README.md", "briefings/2026-01-15.md",
        "raw/papers/a-2026.md", "concepts/other.md",
    )}
    assert {e: (r.kind, r.problem) for e, r in resolved.items()} == {
        "raw/articles/a-2026.md": ("record", None),
        "queries/deep-dive/README.md": ("page", None),
        "briefings/2026-01-15.md": ("page", None),
        # a missing file still names a record or page (grounding counts it);
        # R6 reports that it's missing
        "raw/papers/a-2026.md": ("record", "no such file"),
        "concepts/other.md": ("page", "no such file"),
    }
    assert resolved["raw/articles/a-2026.md"].path == tmp_path / "raw/articles/a-2026.md"


NOT_SOURCES = {
    "user, conversation, 2026-01-15": "not a path",
    "conversation": "a bare name, not a path",
    "competitor-x-pricing-2026-01-15": "a bare name, not a path",
    "SCHEMA.md": "a root file isn't a source",
    "log.md": "a root file isn't a source",
    "raw/assets/deck-2026-01.pdf": "an asset: declare its record",
    "raw/assets/deck-2026-01.md": "an asset: declare its record",
    "_archive/acme-2026-01-15.md": "an archive snapshot isn't a source",
    "queries/deep-dive/assets/deck.md": "an artifact under assets/ isn't a page",
    "meta/contract.md": "not in raw/ or a page folder",
    "/home/someone/notes.md": "not a path inside the wiki",
    "raw/../SCHEMA.md": "not a path inside the wiki",
    "https://example.com/pricing": "a URL: capture it as a record",
    "raw/attachments/page.html": "not a markdown file",
}


@pytest.mark.parametrize("entry", NOT_SOURCES)
def test_resolve_says_why_an_entry_isnt_a_source(tmp_path, entry):
    assert wikifm.resolve(entry, tmp_path) == (None, None, NOT_SOURCES[entry])


# ---------------------------------------------------------------------------
# session-start's stale scan reads through wikifm
# ---------------------------------------------------------------------------


def write_entity(wiki: Path, name: str, updated: str, tags: str = "tags: [company]"):
    (wiki / "entities" / f"{name}.md").write_text(
        f"---\ntitle: {name}\ncreated: 2024-01-01\nupdated: {updated}\n"
        f"type: entity\n{tags}\nsources: []\n---\n# {name}\n"
    )


def health(wiki: Path):
    """(stale, decay) counts from the _status.md that session-start writes."""
    run_hook(SESSION_START, session_start_payload(),
             {"CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki)})
    status = (wiki / "_status.md").read_text()
    stale = re.search(r"\| Stale pages \(>30 days\) \| (\d+) \|", status).group(1)
    decay = re.search(r"\| Confidence decay \(past decay window\) \| (\d+) \|", status).group(1)
    return int(stale), int(decay)


class TestSessionStartScan:
    def test_single_quoted_updated_is_read(self, tmp_path):
        """The MCP and PyYAML write dates single-quoted; the old scan skipped them."""
        wiki = make_wiki(tmp_path)
        write_entity(wiki, "quoted", f"'{date.today() - timedelta(days=45)}'")
        assert health(wiki) == (1, 0)

    def test_block_style_competitive_tags_decay(self, tmp_path):
        wiki = make_wiki(tmp_path)
        write_entity(wiki, "rival", str(date.today() - timedelta(days=75)),
                     tags="tags:\n  - company\n  - competitive")
        assert health(wiki) == (1, 1)

    def test_timestamp_updated_is_still_skipped(self, tmp_path):
        """Timestamp dates are profile errors; the migration rewrites them."""
        wiki = make_wiki(tmp_path)
        write_entity(wiki, "stamped", f"{date.today() - timedelta(days=45)}T00:00:00.000Z")
        assert health(wiki) == (0, 0)
