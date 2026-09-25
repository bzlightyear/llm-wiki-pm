"""
Tests for the frontmatter-validity and provenance-cross-reference checks in
skills/llm-wiki-pm/scripts/lint.py (R1/R2/R5 structural, R3/R4 provenance).

Fixtures are drawn from the real defects catalogued in
fork-chgs/LINT-FRONTMATTER-CHECKS-2026-09-23.md.

Run: python3 -m pytest tests/test_lint.py -v
"""

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LINT_PATH = REPO_ROOT / "skills" / "llm-wiki-pm" / "scripts" / "lint.py"

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
# R3 / R4 — provenance cross-reference
# ---------------------------------------------------------------------------


def test_r3_slug_plus_section_name_resolves():
    slug = "cba-product-update-customer-feedback-2026-09-10"
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
    raw = "raw/internal/underwriteme-cost-sharing-request-2026-08-25.md"
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
