"""
Tests for the frontmatter-validity and provenance-cross-reference checks in
skills/llm-wiki-pm/scripts/lint.py (R1/R2/R5 structural, R3/R4 provenance).

Fixtures are drawn from the real defects catalogued in
fork-chgs/lint-frontmatter-checks-design.md.

Run: python3 -m pytest tests/test_lint.py -v
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

from test_hooks import make_wiki, run_lint

# TestLint in tests/test_hooks.py holds more lint tests; it stays there so that
# upstream file isn't edited.

REPO_ROOT = Path(__file__).resolve().parent.parent
LINT_PATH = REPO_ROOT / "skills" / "llm-wiki-pm" / "scripts" / "lint.py"

sys.path.insert(0, str(LINT_PATH.parent))  # lint imports wikifm from beside it
import wikifm  # noqa: E402

_spec = importlib.util.spec_from_file_location("lint", LINT_PATH)
lint = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lint)


FM_HEAD = "title: t\ncreated: 2026-01-01\nupdated: 2026-01-01\ntype: concept\n"


def fm_block(rest):
    return FM_HEAD + rest


def page(sources_line, body):
    return (
        "---\n" + FM_HEAD + "tags: [ai]\n" + sources_line + "\n---\n\n" + body
    )


# ---------------------------------------------------------------------------
# R1 / R2 / R5 — frontmatter structural validity
# ---------------------------------------------------------------------------


def test_r1_block_item_pasted_onto_key_line():
    errs = lint.check_frontmatter_structure("p.md", fm_block("tags: - roadmap\n"))
    assert any("R1" in e for e in errs)


def test_r2_orphan_item_under_flow_list():
    errs = lint.check_frontmatter_structure(
        "p.md", fm_block("sources: [a.md, b.md]\n  - c.md\n")
    )
    assert any("R2" in e for e in errs)


def test_well_formed_lists_stay_silent():
    assert lint.check_frontmatter_structure(
        "p.md", fm_block("sources: [a.md, b.md]\n")
    ) == []
    assert lint.check_frontmatter_structure(
        "p.md", fm_block("sources:\n  - a.md\n  - b.md\n")
    ) == []


def test_key_after_orphan_line_still_reported():
    errs = lint.check_frontmatter_structure(
        "p.md", fm_block("sources: [a.md]\n  - b.md\ntags: [x]\n")
    )
    assert any("R2" in e for e in errs)


def test_r5_duplicate_key_fires_and_still_parses_as_yaml():
    block = fm_block("coverage: stub\ngaps: []\ncoverage: comprehensive\n")
    errs = lint.check_frontmatter_structure("p.md", block)
    assert any("R5" in e and "coverage" in e for e in errs)

    # R5 cannot be folded into a parse check: YAML is last-wins, so this
    # loads without error while silently discarding the first value.
    try:
        import yaml
    except ImportError:
        return
    loaded = yaml.safe_load(block)
    assert loaded["coverage"] == "comprehensive"


# ---------------------------------------------------------------------------
# wikifm.sources — quote-aware flow-list parsing
# ---------------------------------------------------------------------------


def sources_of(text):
    return wikifm.sources(wikifm.parse(text)[0])


def test_quoted_source_with_commas_stays_one_entry():
    t = '---\nsources: [raw/a.md, "user, conversation, 2026-08-14", raw/b.md]\n---\n\nbody\n'
    assert sources_of(t) == [
        "raw/a.md",
        "user, conversation, 2026-08-14",
        "raw/b.md",
    ]


def test_unquoted_conversational_entry_still_splits():
    # genuinely ambiguous in YAML — the commas do create separate entries, so
    # this must keep reporting the fragments rather than silently repairing it
    t = "---\nsources: [raw/a.md, user, conversation, 2026-08-14]\n---\n\nbody\n"
    assert sources_of(t) == ["raw/a.md", "user", "conversation", "2026-08-14"]


def test_block_style_and_single_quotes():
    t = "---\nsources:\n  - raw/a.md\n  - 'user, conversation, 2026-08-14'\n---\n\nbody\n"
    assert sources_of(t) == ["raw/a.md", "user, conversation, 2026-08-14"]


# ---------------------------------------------------------------------------
# Dates and tags read through wikifm
# ---------------------------------------------------------------------------


def test_stale_check_reads_single_quoted_updated(tmp_path):
    """The MCP and PyYAML write dates single-quoted; lint used to skip them."""
    wiki = make_wiki(tmp_path)
    (wiki / "entities" / "old.md").write_text(
        "---\ntitle: t\ncreated: '2024-01-01'\nupdated: '2024-01-01'\ntype: entity\n"
        "tags: [company]\nsources: [raw/articles/a.md]\ncoverage: stub\n---\n# t\n"
    )
    assert "d since update): entities/old.md" in run_lint(wiki)


def test_block_style_tags_are_checked_against_the_taxonomy(tmp_path):
    wiki = make_wiki(tmp_path)
    (wiki / "entities" / "acme.md").write_text(
        "---\ntitle: t\ncreated: 2024-01-01\nupdated: 2024-01-01\ntype: entity\n"
        "tags:\n  - company\n  - not-in-taxonomy\nsources: [raw/articles/a.md]\n---\n# t\n"
    )
    report = run_lint(wiki)
    assert "tag 'not-in-taxonomy' not in SCHEMA.md taxonomy: entities/acme.md" in report
    assert "tag 'company' not in" not in report


# ---------------------------------------------------------------------------
# R3 / R4 — provenance cross-reference
# ---------------------------------------------------------------------------


def test_r3_slug_plus_section_name_resolves():
    slug = "customer-a-product-update-customer-feedback-2026-09-10"
    notes = lint.check_provenance_cross_reference(
        "p.md",
        page(f"sources: [{slug}]", f"[source: {slug}, Recently Shipped]"),
        [slug],
    )
    assert notes["info"] == []


def test_r3_user_conversation_marker_never_flagged():
    notes = lint.check_provenance_cross_reference(
        "p.md",
        page(
            'sources: ["This conversation, 2026-08-25"]',
            "[source: user, conversation (CFP Coordination meeting), 2026-08-12]",
        ),
        ["This conversation, 2026-08-25"],
    )
    assert notes["info"] == []
    assert notes["warnings"] == []


def test_r3_semicolon_joined_marker_resolves_both_halves():
    raw = "raw/internal/customer-b-cost-sharing-request-2026-08-25.md"
    sources = ["user, conversation, 2026-08-25", raw]
    notes = lint.check_provenance_cross_reference(
        "p.md",
        page(
            f'sources: ["user, conversation, 2026-08-25", {raw}]',
            f"[source: user, conversation, 2026-08-25;\n{raw}]",
        ),
        sources,
    )
    assert notes["info"] == []


def test_r4_fires_on_22_listed_3_cited():
    sources = [f"raw/articles/s{i}.md" for i in range(22)]
    body = " ".join(f"[source: {s}]" for s in sources[:3])
    notes = lint.check_provenance_cross_reference(
        "p.md", page("sources: [" + ", ".join(sources) + "]", body), sources
    )
    assert any("R4" in w for w in notes["warnings"])


def test_r4_silent_on_8_listed_8_cited():
    sources = [f"raw/articles/s{i}.md" for i in range(8)]
    body = " ".join(f"[source: {s}]" for s in sources)
    notes = lint.check_provenance_cross_reference(
        "p.md", page("sources: [" + ", ".join(sources) + "]", body), sources
    )
    assert notes["warnings"] == []


# ---------------------------------------------------------------------------
# --cited-sources — the split procedure's helper
# ---------------------------------------------------------------------------


def run_cited_sources(wiki, page_arg, cwd=None):
    return subprocess.run(
        [sys.executable, str(LINT_PATH), str(wiki), "--cited-sources", str(page_arg)],
        capture_output=True, text=True, cwd=cwd,
    )


def split_wiki(tmp_path, body):
    """A wiki holding two records, a page and a directory page, plus a new
    split child, concepts/child.md, that cites with `body` and declares
    nothing yet."""
    wiki = make_wiki(tmp_path)
    for rel in (
        "raw/articles/competitor-x-pricing-2026-01-15.md",
        "raw/internal/conversation-2026-01-15-pricing-tier.md",
        "queries/crystallize-pricing-review-2026-01-10.md",
        "queries/pricing-deep-dive/README.md",
    ):
        (wiki / rel).parent.mkdir(parents=True, exist_ok=True)
        (wiki / rel).write_text("---\ntitle: t\n---\nx\n")
    (wiki / "concepts" / "child.md").write_text(page("sources: []", body))
    return wiki


def test_cited_sources_prints_paths_in_first_cited_order(tmp_path):
    wiki = split_wiki(
        tmp_path,
        "The team chose usage-based billing [source: conversation-2026-01-15-pricing-tier].\n"
        'Three tiers [source: competitor-x-pricing-2026-01-15, "Plans"; '
        "crystallize-pricing-review-2026-01-10, Decisions].\n"
        "See [[pricing-deep-dive]] [source: pricing-deep-dive, Findings].\n"
        "Again [source: competitor-x-pricing-2026-01-15, p.3].\n",
    )
    result = run_cited_sources(wiki, "concepts/child.md")
    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        "sources:\n"
        "  - raw/internal/conversation-2026-01-15-pricing-tier.md\n"
        "  - raw/articles/competitor-x-pricing-2026-01-15.md\n"
        "  - queries/crystallize-pricing-review-2026-01-10.md\n"
        "  - queries/pricing-deep-dive/README.md\n"
    )


def test_cited_sources_lists_ids_that_resolve_to_nothing(tmp_path):
    wiki = split_wiki(
        tmp_path,
        "A [source: user, conversation, 2026-01-15].\n"
        "B [source: raw/articles/competitor-x-pricing-2026-01-15.md].\n"
        "C [source: competitor-x-\npricing-2026-01-15, p.3].\n"
        "D [source: deck-2026-01].\n"
        "E [source: conversation-2026-01-15-pricing-tier].\n",
    )
    (wiki / "raw" / "assets" / "deck-2026-01.md").write_text("x\n")  # never a source
    result = run_cited_sources(wiki, "concepts/child.md")
    assert result.returncode == 1
    assert result.stdout == (
        "sources:\n"
        "  - raw/internal/conversation-2026-01-15-pricing-tier.md\n"
        "unresolved:\n"
        "  - user\n"
        "  - raw/articles/competitor-x-pricing-2026-01-15.md\n"
        "  - competitor-x- pricing-2026-01-15\n"
        "  - deck-2026-01\n"
    )


def test_cited_sources_lists_ids_that_match_two_files(tmp_path):
    wiki = split_wiki(tmp_path, "A [source: dup-2026, p.1].\nB [source: pricing-deep-dive].\n")
    (wiki / "raw" / "articles" / "dup-2026.md").write_text("x\n")
    (wiki / "raw" / "papers" / "dup-2026.md").write_text("x\n")
    (wiki / "raw" / "internal" / "pricing-deep-dive.md").write_text("x\n")  # a page's slug
    result = run_cited_sources(wiki, "concepts/child.md")
    assert result.returncode == 1
    assert result.stdout == (
        "sources: []\n"
        "ambiguous:\n"
        "  - dup-2026: raw/articles/dup-2026.md, raw/papers/dup-2026.md\n"
        "  - pricing-deep-dive: queries/pricing-deep-dive/README.md, "
        "raw/internal/pricing-deep-dive.md\n"
    )


def test_cited_sources_with_no_citations(tmp_path):
    wiki = split_wiki(tmp_path, "No citations here.\n")
    result = run_cited_sources(wiki, "concepts/child.md")
    assert (result.returncode, result.stdout) == (0, "sources: []\n")


def test_cited_sources_takes_an_absolute_or_wiki_relative_page(tmp_path):
    wiki = split_wiki(tmp_path, "A [source: pricing-deep-dive].\n")
    for page_arg in (wiki / "concepts" / "child.md", "concepts/child.md"):
        result = run_cited_sources(wiki, page_arg, cwd=tmp_path)
        assert result.returncode == 0, result.stderr
        assert result.stdout == "sources:\n  - queries/pricing-deep-dive/README.md\n"
    result = run_cited_sources(wiki, "concepts/missing.md", cwd=tmp_path)
    assert result.returncode == 2
    assert "not a file" in result.stderr


def test_cited_sources_writes_nothing(tmp_path):
    wiki = split_wiki(tmp_path, "A [source: pricing-deep-dive].\n")
    before = {p: p.read_bytes() for p in wiki.rglob("*") if p.is_file()}
    run_cited_sources(wiki, "concepts/child.md")
    after = {p: p.read_bytes() for p in wiki.rglob("*") if p.is_file()}
    assert after == before  # no lint report, no log.md entry
