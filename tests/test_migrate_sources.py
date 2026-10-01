"""
Tests for skills/llm-wiki-pm/scripts/migrate_sources.py, the one-off
migration of a wiki's sources: entries and citations to
references/citation-spec.md. One test or more per class in the migration
table of fork-chgs/sources-and-references-design.md (section 7), with the
rotated logs of review F14 and the unrouted files of review F15.

Run: python3 -m pytest tests/test_migrate_sources.py -v
"""

import subprocess
import sys
from datetime import date

import pytest

from test_hooks import REPO_ROOT, TEMPLATES_DIR, make_wiki

SCRIPTS = REPO_ROOT / "skills" / "llm-wiki-pm" / "scripts"
MIGRATE = SCRIPTS / "migrate_sources.py"
LINT = SCRIPTS / "lint.py"

sys.path.insert(0, str(SCRIPTS))
import lint  # noqa: E402
import migrate_sources  # noqa: E402
import wikifm  # noqa: E402

TODAY = date.today().isoformat()
D1, D2 = "2026-08-05", "2026-08-12"
ID1, ID2 = f"conversation-{D1}-reconstructed", f"conversation-{D2}-reconstructed"
REC1, REC2 = f"raw/internal/{ID1}.md", f"raw/internal/{ID2}.md"
DIGEST = "lifecycle: dated-digest\n"


def page(sources="[]", body="# t\n", extra=""):
    """A page whose body starts on line 10."""
    return (
        "---\ntitle: t\ncreated: '2026-01-01'\nupdated: '2026-01-01'\ntype: concept\n"
        f"tags: [ai]\n{extra}sources: {sources}\n---\n\n{body}"
    )


def brief(sources="[]"):
    return (
        "---\ntitle: Daily Brief\ncreated: '2026-08-11'\nupdated: '2026-08-11'\n"
        f"type: summary\ntags: [ai]\nsources: {sources}\n{DIGEST}---\n\n# Brief\n"
    )


def write(wiki, rel, text):
    path = wiki / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def run(wiki, *args):
    return subprocess.run(
        [sys.executable, str(MIGRATE), str(wiki), *args], capture_output=True, text=True
    )


def tree(wiki):
    """Every file under the wiki, with its content."""
    return {p.relative_to(wiki).as_posix(): p.read_bytes() for p in wiki.rglob("*") if p.is_file()}


def sources_of(wiki, rel):
    fields, _ = wikifm.parse((wiki / rel).read_text())
    return wikifm.sources(fields)


def body_of(wiki, rel):
    return (wiki / rel).read_text().split("\n---\n\n", 1)[1]


def hand_pass(result):
    return result.stdout.split("For the hand pass")[1]


# ---------------------------------------------------------------------------
# The dry run
# ---------------------------------------------------------------------------


def test_the_dry_run_writes_nothing_and_counts_each_pages_findings(tmp_path):
    wiki = make_wiki(tmp_path)
    write(wiki, "concepts/a.md", page(f'["user, conversation, {D1}"]',
                                      f"Chose X [source: user, conversation, {D1}].\n"))
    write(wiki, "_archive/briefings/2026-08-11.md", brief())
    before = tree(wiki)
    result = run(wiki)
    assert result.returncode == 0, result.stderr
    assert tree(wiki) == before
    out = result.stdout
    assert out.startswith("Dry run: nothing written.")
    assert f"  {REC1}: 0 log entries, cited by 1 page(s)\n" in out
    assert "  _archive/briefings/2026-08-11.md → briefings/2026-08-11.md\n" in out
    assert "Pages to change: 1," in out
    # R3 and R6 go from 1 to 0 on the page; R7 and R12 are clean before and after
    row = next(line for line in out.splitlines() if line.endswith("concepts/a.md"))
    assert row.split() == ["1", "→", "0", "1", "→", "0", "·", "·", "concepts/a.md"]
    # the page, the moved brief and make_wiki's overview.md
    assert next(line for line in out.splitlines() if line.endswith("all 3 pages")).split()[:6] == [
        "1", "→", "0", "1", "→", "0"]


# ---------------------------------------------------------------------------
# M2/M3 — conversations become reconstructed records
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("sources, expected", [
    (f'["user, conversation, {D1}"]', [REC1]),
    (f'["conversation, {D1}"]', [REC1]),
    (f"[conversation, {D1}]", [REC1]),  # split at its comma by an unquoted flow list
    (f"\n  - conversation\n  - {D1}", [REC1]),  # the same, frozen as a block list
    (f"[user, conversation, {D1}]", [REC1]),  # split twice
    (f'[conversation, {D1}, "user, conversation, {D2}"]', [REC1, REC2]),
    (f'["user, conversation, {D1}", "conversation, {D1}", raw/articles/x-2026.md]',
     [REC1, "raw/articles/x-2026.md"]),
    (f'["user, conversation (pricing call), {D2}"]', [REC2]),
    ('["user, conversation, 2026-02-30"]', ["user, conversation, 2026-02-30"]),  # no such day
])
def test_conversation_entries_become_their_records_path(tmp_path, sources, expected):
    wiki = make_wiki(tmp_path)
    write(wiki, "raw/articles/x-2026.md", "x\n")
    write(wiki, "concepts/a.md", page(sources))
    result = run(wiki, "--apply")
    assert result.returncode == 0, result.stderr
    assert sources_of(wiki, "concepts/a.md") == expected
    assert wikifm.parse((wiki / "concepts/a.md").read_text())[1] == []


def test_conversation_citations_cite_their_records_id(tmp_path):
    wiki = make_wiki(tmp_path)
    write(wiki, "raw/articles/x-2026.md", "x\n")
    write(wiki, "concepts/a.md", page("[raw/articles/x-2026.md]", (
        f"A [source: user, conversation, {D1}].\n"
        f"B [source: user, {D1}].\n"
        f"C [source: conversation, {D1}].\n"
        f"D [source: user, conversation (pricing call), {D2}].\n"
        f"E [source: user, conversation,\n{D1}].\n"
        f"F [source: user, conversation, {D1}, shared a link].\n"
        f"G [source: user, conversation, {D1}; raw/articles/x-2026.md, p.2].\n"
        f"H [source: x-2026; source: user, conversation, {D1}].\n"
    )))
    assert run(wiki, "--apply").returncode == 0
    assert body_of(wiki, "concepts/a.md") == (
        f"A [source: {ID1}].\n"
        f"B [source: {ID1}].\n"
        f"C [source: {ID1}].\n"
        f"D [source: {ID2}, pricing call].\n"
        f"E [source: {ID1}].\n"
        f"F [source: {ID1}, shared a link].\n"
        f"G [source: {ID1}; x-2026, p.2].\n"
        f"H [source: x-2026; {ID1}].\n"
    )
    # each record the page now cites is declared, in first-cited order
    assert sources_of(wiki, "concepts/a.md") == ["raw/articles/x-2026.md", REC1, REC2]
    title = wikifm.parse((wiki / REC2).read_text())[0]["title"]
    assert title == f"Conversation {D2} (reconstructed): pricing call"


def test_a_marker_with_prose_beside_a_conversation_is_left_for_the_hand_pass(tmp_path):
    wiki = make_wiki(tmp_path)
    before = page("[]", f"A [source: user, conversation, {D1}; read live in a browser].\n")
    write(wiki, "concepts/a.md", before)
    result = run(wiki, "--apply")
    assert result.returncode == 0, result.stderr
    assert (wiki / "concepts/a.md").read_text() == before
    assert (wiki / REC1).is_file()  # the date is cited, so the hand pass can use its record
    assert (f"  concepts/a.md:10: [source: user, conversation, {D1}; read live in a browser]: "
            "not an ID\n") in hand_pass(result)


def test_the_record_quotes_the_days_log_entries_and_lists_its_claims(tmp_path):
    wiki = make_wiki(tmp_path)
    # rotated by session-stop.sh: log-YYYY.md, then log-YYYY-part-N.md (F14)
    write(wiki, "log-2026.md", (
        f"# Wiki Log\n\n## [{D1}] ingest | first\n\n* raw/articles/x-2026.md\n\n"
        f"## [{D1}] lint | 0E 1W 4I 0F\n\n* Report: queries/lint-{D1}.md\n"
    ))
    write(wiki, "log-2026-part-2.md", f"# Wiki Log\n\n## [{D1}] update | second\n")
    write(wiki, "log.md", (
        f"# Wiki Log\n\n## \\[{D1}] query | third\n\n## [2026-08-06] update | another day\n"
    ))
    write(wiki, "concepts/a.md", page(f'["conversation, {D1}"]', (
        "- The team chose usage-based billing\n"
        f"  for the new tier [source: user, conversation,\n  {D1}].\n\n"
        f"| tier | usage-based [source: user, {D1}] |\n"
        "| next | row |\n\n"
        f"Wrapped prose that ends\n[source: user, {D2}]\nand goes on.\n"
    )))
    assert run(wiki, "--apply").returncode == 0

    text = (wiki / REC1).read_text()
    fields, errors = wikifm.parse(text)
    assert errors == []
    assert fields == {
        "title": f"Conversation {D1} (reconstructed)",
        "source_type": "conversation",
        "stated_by": "user",
        "reconstructed": "true",
        "reconstructed_on": TODAY,
    }
    assert f"reconstructed_on: '{TODAY}'\n" in text  # the canonical date form
    assert lint.is_secondhand(wiki / REC1, {})
    # that day's entries, oldest log first, without the lint run or other days
    assert [line for line in text.splitlines() if line.startswith("> ## ")] == [
        f"> ## [{D1}] ingest | first",
        f"> ## [{D1}] update | second",
        f"> ## \\[{D1}] query | third",
    ]
    assert "0E 1W" not in text and "another day" not in text
    assert text.endswith(
        "## Cited by\n\n"
        "- `concepts/a.md`, in `sources:`\n"
        "- `concepts/a.md`: - The team chose usage-based billing for the new tier "
        f"[source: user, conversation, {D1}].\n"
        f"- `concepts/a.md`: | tier | usage-based [source: user, {D1}] |\n"
    )
    # a date the log never mentions still gets its record
    text = (wiki / REC2).read_text()
    assert "The log has no entry for that day.\n" in text
    assert text.endswith(f"- `concepts/a.md`: Wrapped prose that ends [source: user, {D2}] "
                         "and goes on.\n")


def test_overview_is_migrated_like_a_page(tmp_path):
    # lint doesn't check it, but Orient reads it every session
    wiki = make_wiki(tmp_path)
    write(wiki, "overview.md", page(
        f'["user, conversation, {D1}"]', f"Chose X [source: user, {D1}].\n"
    ).replace("created: '2026-01-01'", "created: 2026-01-01T00:00:00.000Z"))
    result = run(wiki, "--apply")
    assert result.returncode == 0, result.stderr
    assert sources_of(wiki, "overview.md") == [REC1]
    assert body_of(wiki, "overview.md") == f"Chose X [source: {ID1}].\n"
    assert "\ncreated: '2026-01-01'\n" in (wiki / "overview.md").read_text()
    assert (wiki / REC1).read_text().endswith(
        "- `overview.md`, in `sources:`\n"
        f"- `overview.md`: Chose X [source: user, {D1}].\n"
    )
    assert (wiki / f"_archive/overview-{TODAY}.md").is_file()


# ---------------------------------------------------------------------------
# M4 — mechanical repairs and moves
# ---------------------------------------------------------------------------


def test_mechanical_citations_and_midnight_timestamps_are_repaired(tmp_path):
    wiki = make_wiki(tmp_path)
    write(wiki, "raw/articles/x-2026.md", "x\n")
    write(wiki, "raw/articles/y-2026.md", "y\n")
    text = page("[raw/articles/x-2026.md, raw/articles/y-2026.md]", (
        "A [source: raw/articles/x-2026.md, p.1].\n"
        "B [source: x-\n2026, p.2].\n"
        "C [source: source: x-2026].\n"
        "D [source: x-2026 vs. y-2026].\n"
    ), extra="last_verified: '2026-01-02'\n")
    write(wiki, "concepts/a.md", text.replace("updated: '2026-01-01'",
                                              "updated: 2026-08-05T00:00:00.000Z"))
    assert run(wiki, "--apply").returncode == 0
    assert body_of(wiki, "concepts/a.md") == (
        "A [source: x-2026, p.1].\n"
        "B [source: x-2026, p.2].\n"
        "C [source: x-2026].\n"
        "D [source: x-2026; y-2026].\n"
    )
    after = (wiki / "concepts/a.md").read_text()
    # the timestamp keeps its date, and `updated` isn't moved to today
    assert "updated: '2026-08-05'\n" in after
    assert "created: '2026-01-01'\nupdated" in after and "last_verified: '2026-01-02'\n" in after


def test_rotated_briefs_and_clippings_move_to_their_folders(tmp_path):
    wiki = make_wiki(tmp_path)
    write(wiki, "_archive/briefings/2026-08-11.md", brief("[raw/clippings/clip-2026.md]"))
    write(wiki, "raw/clippings/clip-2026.md", "clip\n")
    write(wiki, "raw/attachments/deck-2026.html", "<html></html>\n")
    write(wiki, "concepts/a.md", page("[raw/clippings/clip-2026.md]",
                                      "A [source: raw/clippings/clip-2026.md]. [[2026-08-11]]\n"))
    result = run(wiki, "--apply")
    assert result.returncode == 0, result.stderr
    assert not (wiki / "_archive/briefings/2026-08-11.md").exists()
    assert (wiki / "briefings/2026-08-11.md").read_text() == brief("[raw/articles/clip-2026.md]")
    assert (wiki / "raw/articles/clip-2026.md").read_text() == "clip\n"
    assert not (wiki / "raw/clippings/clip-2026.md").exists()
    # a declaration follows the file it names; the ID, and so the citation, stay
    assert sources_of(wiki, "concepts/a.md") == ["raw/articles/clip-2026.md"]
    assert body_of(wiki, "concepts/a.md") == "A [source: clip-2026]. [[2026-08-11]]\n"
    hand = hand_pass(result)
    assert "  briefings/2026-08-11.md: lint never checked it in _archive/" in hand
    # a file that isn't a record stays where it is, for the hand pass (F15)
    assert (wiki / "raw/attachments/deck-2026.html").is_file()
    assert ("  raw/attachments/deck-2026.html: save a markdown record of it in a routed "
            "raw/ folder, move the original to raw/assets/, and declare the record "
            "instead\n") in hand


# ---------------------------------------------------------------------------
# Dated digests, undeclared citations, and what needs judgement (M5)
# ---------------------------------------------------------------------------


def test_dated_digests_keep_only_sources_that_name_a_record_or_page(tmp_path):
    wiki = make_wiki(tmp_path)
    write(wiki, "queries/weekly-brief-2026-08-07.md",
          page("[log.md, overview.md, index.md, SCHEMA.md]", extra=DIGEST))
    write(wiki, "queries/digest-2026-08-14.md", page("\n  - this session", extra=DIGEST))
    write(wiki, "concepts/org.md", page("[SCHEMA.md org chart]"))
    result = run(wiki, "--apply")
    assert result.returncode == 0, result.stderr
    assert sources_of(wiki, "queries/weekly-brief-2026-08-07.md") == []
    assert "sources: []\n" in (wiki / "queries/digest-2026-08-14.md").read_text()
    assert ("  queries/weekly-brief-2026-08-07.md: 'log.md', 'overview.md', 'index.md', "
            "'SCHEMA.md'\n") in result.stdout
    # a page that isn't a digest keeps them, for the hand pass
    assert sources_of(wiki, "concepts/org.md") == ["SCHEMA.md org chart"]
    assert "  concepts/org.md: sources: 'SCHEMA.md org chart': not a path\n" in hand_pass(result)


def test_undeclared_citations_are_declared_only_with_declare_cited(tmp_path):
    wiki = make_wiki(tmp_path)
    write(wiki, "raw/articles/x-2026.md", "x\n")
    write(wiki, "concepts/b.md", page())
    write(wiki, "concepts/a.md", page("[]", (
        "A [source: x-2026, p.1]. B [source: b]. C [source: missing-2026].\n"
    )))
    result = run(wiki, "--apply")
    assert result.returncode == 0, result.stderr
    assert sources_of(wiki, "concepts/a.md") == []
    hand = hand_pass(result)
    assert ("  concepts/a.md:10: cites 'x-2026', which sources: doesn't declare: declare "
            "raw/articles/x-2026.md (--declare-cited does)\n") in hand
    assert ("  concepts/a.md:10: cites 'missing-2026', which sources: doesn't declare: "
            "it names no record or page\n") in hand

    result = run(wiki, "--apply", "--declare-cited")
    assert result.returncode == 0, result.stderr
    assert sources_of(wiki, "concepts/a.md") == ["raw/articles/x-2026.md", "concepts/b.md"]
    assert "cites 'x-2026'" not in result.stdout
    assert "cites 'missing-2026', which sources: doesn't declare" in result.stdout


def test_what_needs_judgement_is_listed_and_left_as_it_is(tmp_path):
    wiki = make_wiki(tmp_path)
    write(wiki, "raw/attachments/deck-2026.html", "<html></html>\n")
    write(wiki, "concepts/other.md", page())
    write(wiki, "_archive/README-2026-08-08.md", "x\n")
    sources = ('["SCHEMA.md org chart", "Open Action Items.md", "/Users/someone/notes.md", '
               'raw/attachments/deck-2026.html, "this session"]')
    before = page(sources, (
        "A [source: SCHEMA.md org chart].\n"
        "B [source: scripts/lint.py, read 2026-08-10].\n"
        "C [source: web search].\n"
        "D [source: see [[other]]].\n"
        "E [source: raw/attachments/deck-2026.html].\n"
    ))
    write(wiki, "concepts/a.md", before)
    result = run(wiki, "--apply")
    assert result.returncode == 0, result.stderr
    assert (wiki / "concepts/a.md").read_text() == before
    hand = hand_pass(result)
    for item in (
        "concepts/a.md: sources: 'SCHEMA.md org chart': not a path",
        "concepts/a.md: sources: 'Open Action Items.md': a root file isn't a source",  # F15
        "concepts/a.md: sources: '/Users/someone/notes.md': not a path inside the wiki",
        "concepts/a.md: sources: 'raw/attachments/deck-2026.html': not a markdown file",
        "concepts/a.md: sources: 'this session': not a path",
        "concepts/a.md:10: [source: SCHEMA.md org chart]: not an ID",
        "concepts/a.md:11: [source: scripts/lint.py, read 2026-08-10]: not an ID",
        "concepts/a.md:12: [source: web search]: not an ID",
        "concepts/a.md:13: [source: see [[other]]]: wikilink, not an ID",
        "concepts/a.md:14: [source: raw/attachments/deck-2026.html]: not an ID",
        "_archive/README-2026-08-08.md: rename it to _archive/<slug>-<date>.md if git "
        "shows which directory page it snapshots",
    ):
        assert f"  {item}\n" in hand


def test_legends_records_archives_and_valid_pages_are_left_alone(tmp_path):
    wiki = make_wiki(tmp_path)
    keep = [
        write(wiki, "raw/internal/no-frontmatter-2026.md", "just text\n"),
        write(wiki, "raw/internal/private-2026.md", "---\ntitle: p\nprivate: true\n---\n\nx\n"),
        # a record and its asset share a stem, which the asset exclusion allows
        write(wiki, "raw/papers/deck-2026.md", "---\nasset: raw/assets/deck-2026.pdf\n---\n\nx\n"),
        write(wiki, "raw/assets/deck-2026.pdf", "%PDF\n"),
        # archive snapshots are immutable, even one that doesn't parse
        write(wiki, "_archive/old-2026-08-01.md",
              f"---\ntitle: [broken\n---\n\n[source: user, conversation, {D1}]\n"),
    ]
    many = [f"raw/articles/s{n}-2026.md" for n in range(6)]
    for rel in many:
        write(wiki, rel, "s\n")
    keep.append(write(wiki, "concepts/legend.md", page(
        "[" + ", ".join(many) + "]",  # 6 declared, 1 cited: R4, which needs no change
        "Claim [source: s0-2026].\n\n## Sources\n\n"
        f"- user, conversation, {D1} (the pricing call)\n- s1-2026: the vendor docs\n",
        extra="gaps:\n  - >-\n    a wrapped\n    gap item\nlast_verified: '2026-01-02'\n",
    )))
    # sources: can't be rewritten where the key is doubled, so nothing on the page is
    keep.append(write(wiki, "concepts/dup.md", page(
        f'["user, conversation, {D1}"]', f"A [source: user, conversation, {D1}].\n",
        extra="sources: [raw/articles/s0-2026.md]\n",
    )))
    before = {p: p.read_bytes() for p in keep}
    result = run(wiki, "--apply")
    assert result.returncode == 0, result.stderr
    assert {p: p.read_bytes() for p in keep} == before
    assert ("  concepts/dup.md: sources: duplicate key 'sources'; fix it by hand first\n"
            in hand_pass(result))
    assert "raw/assets" not in result.stdout


# ---------------------------------------------------------------------------
# M7 — the contract and SCHEMA.md's split rule
# ---------------------------------------------------------------------------

DEFAULT_CONTRACT = (
    "---\nschema_version: 1\ngenerated_by: mcp-markdown-vault\n"
    "generated_at: 2026-01-01T00:00:00.000Z\n---\n\n# Vault Contract\n\n"
    "## Frontmatter Schema\n\n- `title`: string — note title\n"
    "- `status`: enum — `draft` | `in_progress` | `done`\n"
)


def test_the_default_contract_and_the_old_split_rule_are_replaced(tmp_path):
    wiki = make_wiki(tmp_path)
    write(wiki, "meta/contract.md", DEFAULT_CONTRACT)
    schema = (wiki / "SCHEMA.md").read_text()
    rule = migrate_sources.SPLIT_RULE_RE.search(schema).group(0)
    old_schema = schema.replace(rule, migrate_sources.OLD_SPLIT_RULE)
    write(wiki, "SCHEMA.md", old_schema)
    result = run(wiki, "--apply")
    assert result.returncode == 0, result.stderr
    assert (wiki / "SCHEMA.md").read_text() == schema
    contract = (TEMPLATES_DIR / "vault-contract.md").read_text()
    assert (wiki / "meta/contract.md").read_text() == contract
    assert (wiki / f"_archive/SCHEMA-{TODAY}.md").read_text() == old_schema
    assert (wiki / f"_archive/contract-{TODAY}.md").read_text() == DEFAULT_CONTRACT
    assert lint.check_contract(wiki) is None


def test_a_split_rule_edited_by_hand_is_left_for_the_hand_pass(tmp_path):
    wiki = make_wiki(tmp_path)
    schema = (wiki / "SCHEMA.md").read_text()
    rule = migrate_sources.SPLIT_RULE_RE.search(schema).group(0)
    edited = schema.replace(rule, "- **Split** pages over 150 lines by sub-topic")
    write(wiki, "SCHEMA.md", edited)
    result = run(wiki, "--apply")
    assert (wiki / "SCHEMA.md").read_text() == edited
    assert ("  SCHEMA.md: add the split-procedure pointer to its split rule, as in "
            "templates/SCHEMA.md\n") in hand_pass(result)
    # the template's own rule, pointer included, needs nothing
    write(wiki, "SCHEMA.md", schema)
    assert "SCHEMA.md" not in run(wiki).stdout


# ---------------------------------------------------------------------------
# Applying: snapshots, the log, a second run, conflicts, and lint afterwards
# ---------------------------------------------------------------------------


def test_apply_snapshots_first_logs_once_and_a_second_run_changes_nothing(tmp_path):
    wiki = make_wiki(tmp_path)
    original = page(f'["user, conversation, {D1}"]', f"A [source: user, {D1}].\n")
    write(wiki, "concepts/a.md", original)
    result = run(wiki, "--apply")
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("Applied.")
    assert (wiki / f"_archive/a-{TODAY}.md").read_text() == original  # M1
    log = (wiki / "log.md").read_text()
    assert log.count("] migrate |") == 1
    assert "- 1 reconstructed conversation record(s) in raw/internal/\n" in log
    assert "- 1 page(s) changed, each snapshotted to _archive/ first\n" in log

    first = tree(wiki)
    again = run(wiki, "--apply")
    assert again.returncode == 0, again.stderr
    assert tree(wiki) == first  # no page, record or log entry rewritten
    assert "Records written (M2): 0\n" in again.stdout
    assert "Pages changed: 0," in again.stdout

    # a later citation of the same date reuses the record, which stays as written
    record = (wiki / REC1).read_bytes()
    write(wiki, "concepts/c.md", page("[]", f"C [source: user, conversation, {D1}].\n"))
    later = run(wiki, "--apply")
    assert later.returncode == 0, later.stderr
    assert "Records already written, kept: 1\n" in later.stdout
    assert (wiki / REC1).read_bytes() == record
    assert sources_of(wiki, "concepts/c.md") == [REC1]
    assert body_of(wiki, "concepts/c.md") == f"C [source: {ID1}].\n"


def test_conflicts_stop_the_run_before_anything_is_written(tmp_path):
    wiki = make_wiki(tmp_path)
    write(wiki, REC1, "---\ntitle: a capture\nsource_type: conversation\n---\n\nx\n")
    write(wiki, f"raw/transcripts/{ID2}.md", "x\n")  # the ID, elsewhere
    write(wiki, "_archive/briefings/2026-08-11.md", brief())
    write(wiki, "briefings/2026-08-11.md", brief())
    write(wiki, "concepts/a.md", page(f'["user, conversation, {D1}", "conversation, {D2}"]'))
    before = tree(wiki)
    result = run(wiki, "--apply")
    assert result.returncode == 1
    assert tree(wiki) == before
    conflicts = result.stdout.split("Conflicts")[1]
    assert f"  {REC1} exists and isn't a reconstructed record\n" in conflicts
    assert f"  {REC2} can't be written: its ID names raw/transcripts/{ID2}.md\n" in conflicts
    assert ("  _archive/briefings/2026-08-11.md can't move to briefings/2026-08-11.md: "
            "that name is taken\n") in conflicts


def test_lint_finds_none_of_the_migrated_defects_afterwards(tmp_path):
    wiki = make_wiki(tmp_path)
    write(wiki, "raw/articles/x-2026.md", "---\nsource_type: web\n---\n\nx\n")
    text = page(f"[conversation, {D1}]", (
        f"A [source: user, {D1}]. B [source: raw/articles/x-2026.md, p.2]. [[b]]\n"
        f"C [source: user, conversation,\n{D2}].\n"
    ))
    write(wiki, "concepts/a.md", text.replace("updated: '2026-01-01'",
                                              "updated: 2026-08-05T00:00:00.000Z"))
    write(wiki, "concepts/b.md", page(f'["user, conversation, {D1}"]',
                                      f"B [source: user, conversation, {D1}]. [[a]]\n"))
    write(wiki, "queries/weekly-brief-2026-08-07.md", page("[log.md, index.md]", extra=DIGEST))
    result = run(wiki, "--apply", "--declare-cited")
    assert result.returncode == 0, result.stderr

    subprocess.run([sys.executable, str(LINT), str(wiki), "--quiet"], check=True)
    report = (wiki / "queries" / f"lint-{TODAY}.md").read_text()
    for rule in ("(R3)", "(R6)", "(R7)", "(R12)"):
        assert rule not in report
    # b rests only on a reconstructed record, so it stays on the revisit list
    assert "(R10): concepts/b.md" in report
    assert "(R10): concepts/a.md" not in report
