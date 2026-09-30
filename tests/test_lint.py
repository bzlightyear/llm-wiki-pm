"""
Tests for the frontmatter, source and citation checks in
skills/llm-wiki-pm/scripts/lint.py: R1/R2/R5 structural, R3/R4 provenance,
and the rules of references/citation-spec.md (R6, R7, R9–R12), with
--auto-fix=content, --json, --cited-sources and what session-start reports
from lint.

Fixtures are drawn from the real defects catalogued in
fork-chgs/lint-frontmatter-checks-design.md and
fork-chgs/sources-and-references-design.md.

Run: python3 -m pytest tests/test_lint.py -v
"""

import importlib.util
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

from test_hooks import SESSION_START, make_wiki, run_hook, run_lint, session_start_payload

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


def r6_problems(tmp_path, sources):
    """What R6 says about each entry, in a wiki holding raw/a.md and raw/b.md."""
    for name in ("a.md", "b.md"):
        (tmp_path / "raw" / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / "raw" / name).write_text("x\n")
    return [wikifm.resolve(s, tmp_path).problem for s in sources]


def test_quoted_source_with_commas_stays_one_entry(tmp_path):
    t = '---\nsources: [raw/a.md, "user, conversation, 2026-08-14", raw/b.md]\n---\n\nbody\n'
    assert sources_of(t) == [
        "raw/a.md",
        "user, conversation, 2026-08-14",
        "raw/b.md",
    ]
    assert r6_problems(tmp_path, sources_of(t)) == [None, "not a path", None]


def test_unquoted_conversational_entry_still_splits(tmp_path):
    # genuinely ambiguous in YAML — the commas do create separate entries, so
    # this must keep reporting the fragments rather than silently repairing it
    t = "---\nsources: [raw/a.md, user, conversation, 2026-08-14]\n---\n\nbody\n"
    assert sources_of(t) == ["raw/a.md", "user", "conversation", "2026-08-14"]
    assert r6_problems(tmp_path, sources_of(t)) == [None] + ["a bare name, not a path"] * 3


def test_block_style_and_single_quotes(tmp_path):
    t = "---\nsources:\n  - raw/a.md\n  - 'user, conversation, 2026-08-14'\n---\n\nbody\n"
    assert sources_of(t) == ["raw/a.md", "user, conversation, 2026-08-14"]
    assert r6_problems(tmp_path, sources_of(t)) == [None, "not a path"]


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


def provenance(sources, body, files=None):
    """check_provenance_cross_reference() on a page with `body`, declaring
    `sources` (the parsed entries; the function doesn't read frontmatter)."""
    return lint.check_provenance_cross_reference(
        "p.md", page("sources: []", body), sources, files
    )


def test_r3_slug_plus_section_name_resolves():
    raw = "raw/internal/customer-a-product-update-customer-feedback-2026-09-10.md"
    notes = provenance([raw], f"[source: {lint.slug(raw)}, Recently Shipped]")
    assert notes == {"info": [], "warnings": []}


def test_r3_flags_a_conversation_citation_with_no_record():
    """No exemption for conversations: capture a record and cite its ID."""
    notes = provenance(
        ["This conversation, 2026-08-25"],
        "[source: user, conversation (planning meeting), 2026-08-12]",
    )
    assert notes["warnings"] == [
        "1 citation(s) of IDs not declared in sources: (R3): p.md — 'user'"
    ]


def test_r3_checks_each_citation_in_a_marker():
    raw = "raw/internal/cost-sharing-request-2026-08-25.md"
    notes = provenance([raw], f"[source: user, conversation, 2026-08-25;\n{raw}]")
    assert notes["warnings"] == [
        "1 citation(s) of IDs not declared in sources: (R3): p.md — 'user'"
    ]


def test_r3_matches_ids_exactly():
    """The old matcher accepted any substring; an ID now equals a slug or fails."""
    notes = provenance(
        ["raw/articles/competitor-x-pricing-2026-01-15.md"],
        "[source: competitor-x-pricing] [source: competitor-x-pricing-2026-01-15-v2]",
    )
    assert notes["warnings"] == [
        "2 citation(s) of IDs not declared in sources: (R3): p.md — "
        "'competitor-x-pricing', 'competitor-x-pricing-2026-01-15-v2'"
    ]


def test_r3_names_the_path_to_declare():
    files = {"competitor-x-pricing-2026-01-15": ["raw/articles/competitor-x-pricing-2026-01-15.md"]}
    notes = provenance([], "[source: competitor-x-pricing-2026-01-15, p.3] [source: user]", files)
    assert notes["warnings"] == [
        "2 citation(s) of IDs not declared in sources: (R3): p.md — "
        "'competitor-x-pricing-2026-01-15' (declare "
        "raw/articles/competitor-x-pricing-2026-01-15.md), 'user'"
    ]


def test_r3_resolves_a_citation_by_what_it_names():
    """A path-form or wrapped citation of a declared source is R7's business,
    not R3's."""
    raw = "raw/articles/competitor-x-pricing-2026-01-15.md"
    notes = provenance([raw], f"[source: {raw}] [source: competitor-x-\npricing-2026-01-15]")
    assert notes == {"info": [], "warnings": []}


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


def test_r4_counts_a_source_as_cited_only_by_its_exact_slug():
    """The old matcher counted [source: s3] as citing raw/articles/s3-2026.md."""
    sources = [f"raw/articles/s{i}-2026.md" for i in range(6)]
    notes = provenance(sources, "[source: s1-2026] [source: s2-2026] [source: s3]")
    assert any(w.startswith("only 2/6 frontmatter sources cited inline (R4)") for w in notes["warnings"])


# ---------------------------------------------------------------------------
# The rules of references/citation-spec.md, run on whole wikis
# ---------------------------------------------------------------------------

TODAY = date.today().isoformat()
CONVERSATION = (
    "---\ntitle: Conversation\nsource_type: conversation\ncaptured: '2026-01-15'\n"
    "stated_by: user\n---\n\nThe team chose usage-based billing.\n"
)


def write(wiki, rel, text="x\n"):
    path = wiki / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def wiki_page(sources="[]", body="# t\n", extra="", type_="concept", tags="[ai]"):
    """A page with every required key, dated today. `extra` is more
    frontmatter lines, each ending in a newline."""
    return (
        f"---\ntitle: t\ncreated: '{TODAY}'\nupdated: '{TODAY}'\ntype: {type_}\n"
        f"tags: {tags}\nsources: {sources}\n{extra}---\n{body}"
    )


def lint_run(wiki, *args):
    return subprocess.run(
        [sys.executable, str(LINT_PATH), str(wiki), *args], capture_output=True, text=True
    )


def report(wiki, *args):
    """Run lint and return the text of its report."""
    result = lint_run(wiki, "--quiet", *args)
    assert result.returncode == 0, result.stderr
    return (wiki / "queries" / f"lint-{TODAY}.md").read_text()


def findings(wiki, *args):
    """Run lint and return its findings by tier: errors, warnings, info."""
    text = report(wiki, *args)
    tiers = {}
    for tier, header in (("errors", "## 🔴"), ("warnings", "## 🟡"), ("info", "## 🔵")):
        section = text.split(header, 1)[1].split("\n## ", 1)[0]
        tiers[tier] = [
            line[2:] for line in section.splitlines() if line.startswith("- ") and line != "- none"
        ]
    return tiers


def lint_json(wiki):
    result = lint_run(wiki, "--quiet", "--json")
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_r6_names_each_entry_that_isnt_an_existing_record_or_page(tmp_path):
    wiki = make_wiki(tmp_path)
    write(wiki, "raw/articles/competitor-x-pricing-2026-01-15.md")
    write(wiki, "concepts/p.md", wiki_page(
        "[raw/articles/competitor-x-pricing-2026-01-15.md, "
        "raw/papers/competitor-x-pricing-2026-01-15.md, "
        "'user, conversation, 2026-01-15', SCHEMA.md]",
        "[source: competitor-x-pricing-2026-01-15]\n",
    ))
    assert (
        "3 sources: item(s) not the path of an existing record or page (R6): concepts/p.md — "
        "'raw/papers/competitor-x-pricing-2026-01-15.md' (no such file: declare "
        "raw/articles/competitor-x-pricing-2026-01-15.md), "
        "'user, conversation, 2026-01-15' (not a path), "
        "'SCHEMA.md' (a root file isn't a source)"
    ) in findings(wiki)["warnings"]


def test_r7_counts_markers_by_defect(tmp_path):
    wiki = make_wiki(tmp_path)
    write(wiki, "raw/articles/competitor-x-pricing-2026-01-15.md")
    write(wiki, "concepts/p.md", wiki_page(
        "[raw/articles/competitor-x-pricing-2026-01-15.md]",
        "One [source: raw/articles/competitor-x-pricing-2026-01-15.md].\n"
        "Two [source: competitor-x-\npricing-2026-01-15, p.3].\n"
        "Three [source: https://example.com/pricing].\n"
        "Four [source: competitor-x-pricing-2026-01-15, p.4].\n",
    ))
    warnings = findings(wiki)["warnings"]
    assert (
        "3 [source:] marker(s) outside the citation grammar (R7): concepts/p.md — "
        "1 wrapped, 1 path, 1 url (2 repairable with --auto-fix=content)"
    ) in warnings
    assert (
        "1 citation(s) of IDs not declared in sources: (R3): concepts/p.md — "
        "'https://example.com/pricing'"
    ) in warnings


def test_r9_every_id_names_one_file(tmp_path):
    wiki = make_wiki(tmp_path)
    write(wiki, "raw/articles/dup-2026.md")
    write(wiki, "raw/papers/dup-2026.md")
    write(wiki, "raw/internal/deep-dive.md")
    write(wiki, "queries/deep-dive/README.md", wiki_page(type_="query", tags="[question]"))
    write(wiki, "entities/acme.md", wiki_page(type_="entity", tags="[company]"))
    write(wiki, "concepts/acme.md", wiki_page())
    errors = findings(wiki)["errors"]
    assert "page slug 'acme' is not unique (R9): concepts/acme.md, entities/acme.md" in errors
    assert (
        "record ID 'deep-dive' is also a page slug (R9): "
        "queries/deep-dive/README.md, raw/internal/deep-dive.md"
    ) in errors
    assert (
        "record ID 'dup-2026' is not unique (R9): raw/articles/dup-2026.md, raw/papers/dup-2026.md"
    ) in errors


def test_r10_lists_pages_resting_only_on_conversation_records(tmp_path):
    wiki = make_wiki(tmp_path)
    write(wiki, "raw/internal/conversation-2026-01-15-pricing-tier.md", CONVERSATION)
    write(wiki, "raw/internal/conversation-2026-01-10-reconstructed.md",
          "---\nsource_type: conversation\nreconstructed: true\n---\nFrom log.md.\n")
    write(wiki, "raw/articles/competitor-x-pricing-2026-01-15.md", "---\nsource_type: web\n---\nx\n")
    write(wiki, "raw/articles/no-frontmatter-2026.md")
    write(wiki, "concepts/told.md", wiki_page(
        "[raw/internal/conversation-2026-01-15-pricing-tier.md, "
        "raw/internal/conversation-2026-01-10-reconstructed.md, concepts/checked.md]"
    ))
    write(wiki, "concepts/checked.md", wiki_page(
        "[raw/internal/conversation-2026-01-15-pricing-tier.md, "
        "raw/articles/competitor-x-pricing-2026-01-15.md]"
    ))
    write(wiki, "concepts/plain.md", wiki_page("[raw/articles/no-frontmatter-2026.md]"))
    r10 = [i for i in findings(wiki)["info"] if "(R10)" in i]
    assert r10 == [
        "secondhand, unverified (R10): concepts/told.md — its only primary sources "
        "are conversation or reconstructed records"
    ]
    assert lint_json(wiki)["secondhand"] == ["concepts/told.md"]


DEFAULT_CONTRACT = (
    "---\nschema_version: 1\ngenerated_by: mcp-markdown-vault\n"
    "generated_at: 2026-01-01T00:00:00.000Z\n---\n\n# Vault Contract\n\n"
    "## Frontmatter Schema\n\n- `title`: string — note title\n"
    "- `status`: enum — `draft` | `in_progress` | `done`\n"
)


def test_r11_flags_the_mcps_default_contract_until_it_is_edited(tmp_path):
    wiki = make_wiki(tmp_path)
    write(wiki, "meta/contract.md", DEFAULT_CONTRACT)
    assert any("(R11)" in w for w in findings(wiki)["warnings"])
    write(wiki, "meta/contract.md", DEFAULT_CONTRACT.replace(
        "- `status`: enum — `draft` | `in_progress` | `done`\n",
        "- `sources`: list — see SCHEMA.md\n",
    ))
    assert not any("(R11)" in w for w in findings(wiki)["warnings"])


def test_r12_warns_on_the_profile_and_errs_on_missing_keys(tmp_path):
    wiki = make_wiki(tmp_path)
    write(wiki, "concepts/stamped.md", wiki_page().replace(
        f"created: '{TODAY}'", "created: 2026-01-15T00:00:00.000Z"
    ))
    write(wiki, "concepts/no-keys.md", "---\ntitle: t\ntype: concept\ntags: [ai]\n---\n# t\n")
    write(wiki, "concepts/no-frontmatter.md", "# t\n")
    tiers = findings(wiki)
    assert (
        "frontmatter outside the profile (R12): concepts/stamped.md — line 3: 'created' "
        "isn't a YYYY-MM-DD date: '2026-01-15T00:00:00.000Z' (--auto-fix=content "
        "rewrites midnight timestamps as 'YYYY-MM-DD')"
    ) in tiers["warnings"]
    assert "frontmatter missing ['created', 'sources', 'updated'] (R12): concepts/no-keys.md" in tiers["errors"]
    assert "missing frontmatter (R12): concepts/no-frontmatter.md" in tiers["errors"]
    assert not any("stamped" in e for e in tiers["errors"])


def test_content_fix_repairs_markers_and_dates_after_a_snapshot(tmp_path):
    wiki = make_wiki(tmp_path)
    write(wiki, "raw/articles/vendor-y-docs-2026.md")
    write(wiki, "raw/articles/competitor-x-docs-2026.md")
    original = wiki_page(
        "[raw/articles/vendor-y-docs-2026.md, raw/articles/competitor-x-docs-2026.md]",
        "One [source: raw/articles/vendor-y-docs-2026.md, p.1].\n"
        'Two [source: vendor-y-\n  docs-2026;\n  source: competitor-x-docs-2026, "Plans"].\n'
        "Three [source: vendor-y-docs-2026 vs. competitor-x-docs-2026].\n"
        "Four [source: user, conversation, 2026-01-15;\n  vendor-y-docs-2026].\n"
        "Five [source: https://example.com/pricing].\n",
    ).replace(f"updated: '{TODAY}'", "updated: 2026-01-15T00:00:00.000Z")
    page_path = write(wiki, "concepts/p.md", original)

    report(wiki, "--auto-fix")
    assert page_path.read_text() == original  # plain --auto-fix leaves content alone

    text = report(wiki, "--auto-fix=content")
    assert page_path.read_text() == (
        original
        .replace("[source: raw/articles/vendor-y-docs-2026.md, p.1]", "[source: vendor-y-docs-2026, p.1]")
        .replace('[source: vendor-y-\n  docs-2026;\n  source: competitor-x-docs-2026, "Plans"]',
                 '[source: vendor-y-docs-2026; competitor-x-docs-2026, "Plans"]')
        .replace("[source: vendor-y-docs-2026 vs. competitor-x-docs-2026]",
                 "[source: vendor-y-docs-2026; competitor-x-docs-2026]")
        .replace("updated: 2026-01-15T00:00:00.000Z", "updated: '2026-01-15'")
    )  # markers citing an ID that names no file, or a URL, are left for a person
    assert (wiki / "_archive" / f"p-{TODAY}.md").read_text() == original
    assert "Auto-fix: ON (content)" in text
    assert "- rewrote 3 [source:] marker(s) in the citation grammar (R7) in concepts/p.md" in text
    assert "- rewrote 1 timestamp date(s) as 'YYYY-MM-DD' (R12) in concepts/p.md" in text
    assert (
        "2 [source:] marker(s) outside the citation grammar (R7): concepts/p.md — 1 wrapped, 1 url"
    ) in text


def test_content_fix_keeps_a_path_whose_id_names_two_files(tmp_path):
    """Rewriting it as the ID would lose which file it means (R9 reports both)."""
    wiki = make_wiki(tmp_path)
    write(wiki, "raw/articles/dup-2026.md")
    write(wiki, "raw/papers/dup-2026.md")
    original = wiki_page("[raw/articles/dup-2026.md]", "[source: raw/articles/dup-2026.md]\n")
    page_path = write(wiki, "concepts/p.md", original)
    report(wiki, "--auto-fix=content")
    assert page_path.read_text() == original


def test_auto_fix_snapshots_a_page_before_changing_it(tmp_path):
    wiki = make_wiki(tmp_path)
    original = wiki_page(body="See \\[\\[other]].\n")
    page_path = write(wiki, "concepts/p.md", original)
    write(wiki, "concepts/other.md", wiki_page(body="See [[p]].\n"))
    report(wiki, "--auto-fix")
    assert page_path.read_text() == original.replace("\\[\\[", "[[")
    assert (wiki / "_archive" / f"p-{TODAY}.md").read_text() == original


def test_grounding_counts_only_records_as_primary(tmp_path):
    wiki = make_wiki(tmp_path)
    write(wiki, "concepts/other.md", wiki_page())
    for name, sources in (
        ("said", "['user, conversation, 2026-01-15', concepts/other.md]"),
        ("typo", "[raw/articles/missing-2026.md, concepts/other.md]"),
    ):
        write(wiki, f"entities/{name}.md", wiki_page(
            sources, type_="entity", tags="[company]", extra="coverage: stub\n"
        ))
    errors = findings(wiki)["errors"]
    # a conversation entry isn't a record; a missing record path still names
    # one (R6 reports that it's missing)
    assert any("self-referential" in e and "entities/said.md" in e for e in errors)
    assert not any("entities/typo.md" in e for e in errors)


def test_dated_digests_skip_grounding_staleness_and_the_index(tmp_path):
    wiki = make_wiki(tmp_path)
    (wiki / "index.md").write_text("# Index\n\n## Concepts\n\n## Queries\n")
    digest = (
        "---\ntitle: Brief\ncreated: '2024-01-01'\nupdated: '2024-01-01'\ntype: query\n"
        "tags: [question]\nsources: [concepts/pricing-model.md]\nlifecycle: dated-digest\n"
        "last_verified: '2024-01-01'\n---\n# Brief\n"
    )
    write(wiki, "briefings/2024-01-01.md", digest)
    write(wiki, "queries/weekly-2024-01-01.md", digest)
    # briefs are link targets
    write(wiki, "concepts/pricing-model.md", wiki_page(body="See [[2024-01-01]].\n"))
    tiers = findings(wiki)
    reported = "\n".join(tiers["errors"] + tiers["warnings"])
    assert "2024-01-01" not in reported
    assert "not in index.md: concepts/pricing-model.md" in tiers["warnings"]
    report(wiki, "--auto-fix")
    index = (wiki / "index.md").read_text()
    assert "[[pricing-model]]" in index and "2024-01-01" not in index


def test_artifacts_under_a_directory_pages_assets_arent_pages(tmp_path):
    wiki = make_wiki(tmp_path)
    write(wiki, "queries/deep-dive/README.md", wiki_page(type_="query", tags="[question]"))
    write(wiki, "queries/deep-dive/assets/one-pager.md", "# No frontmatter\n")
    assert "one-pager" not in report(wiki)


def test_the_split_warning_points_at_the_split_procedure(tmp_path):
    wiki = make_wiki(tmp_path)
    text = wiki_page(body="line\n" * 210)
    write(wiki, "concepts/long.md", text)
    assert (
        f"page > 200 lines ({text.count(chr(10))}): concepts/long.md — split candidate: "
        "follow the split procedure in references/citation-spec.md and set each page's "
        "sources with lint.py --cited-sources"
    ) in findings(wiki)["warnings"]


def test_json_writes_nothing_and_carries_the_lists(tmp_path):
    wiki = make_wiki(tmp_path)
    write(wiki, "raw/internal/conversation-2026-01-15-pricing-tier.md", CONVERSATION)
    write(wiki, "concepts/told.md", wiki_page(
        "[raw/internal/conversation-2026-01-15-pricing-tier.md]", "[source: user]\n"
    ))
    write(wiki, "concepts/bare.md", "---\ntitle: t\ntype: concept\ntags: [ai]\n---\n# t\n")
    before = {p: p.read_bytes() for p in wiki.rglob("*") if p.is_file()}
    data = lint_json(wiki)
    after = {p: p.read_bytes() for p in wiki.rglob("*") if p.is_file()}
    assert after == before  # no report, no log.md entry
    assert sorted(data["index_gaps"]) == ["concepts/bare.md", "concepts/told.md"]
    assert data["missing_fields"] == [
        {"page": "concepts/bare.md", "missing": ["created", "sources", "updated"]}
    ]
    assert data["secondhand"] == ["concepts/told.md"]
    assert data["invariants"] == {"I1": 1, "I2": 0, "I3": 1}


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
        "D [source: deck-2026-01].\n"
        "E [source: conversation-2026-01-15-pricing-tier].\n"
        "F [source: https://example.com/pricing, 2026-01-15].\n",
    )
    (wiki / "raw" / "assets" / "deck-2026-01.md").write_text("x\n")  # never a source
    result = run_cited_sources(wiki, "concepts/child.md")
    assert result.returncode == 1
    assert result.stdout == (
        "sources:\n"
        "  - raw/internal/conversation-2026-01-15-pricing-tier.md\n"
        "unresolved:\n"
        "  - user\n"
        "  - deck-2026-01\n"
        "  - https://example.com/pricing\n"
    )


def test_cited_sources_resolves_what_a_malformed_citation_names(tmp_path):
    """A path, a wrapped ID, a nested prefix and a wikilink still name one
    file each; R7 reports the form."""
    wiki = split_wiki(
        tmp_path,
        "B [source: raw/articles/competitor-x-pricing-2026-01-15.md].\n"
        "C [source: competitor-x-\npricing-2026-01-15, p.3].\n"
        "G [source: source: conversation-2026-01-15-pricing-tier].\n"
        "H [source: [[pricing-deep-dive]]].\n",
    )
    result = run_cited_sources(wiki, "concepts/child.md")
    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        "sources:\n"
        "  - raw/articles/competitor-x-pricing-2026-01-15.md\n"
        "  - raw/internal/conversation-2026-01-15-pricing-tier.md\n"
        "  - queries/pricing-deep-dive/README.md\n"
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


# ---------------------------------------------------------------------------
# What session-start reports from lint
# ---------------------------------------------------------------------------


def fake_plugin(tmp_path, lint_source):
    """A plugin root whose lint.py is `lint_source`, beside the real
    wikifm.py that session-start's stale scan imports."""
    scripts = tmp_path / "plugin" / "skills" / "llm-wiki-pm" / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy(LINT_PATH.parent / "wikifm.py", scripts)
    (scripts / "lint.py").write_text(lint_source)
    return tmp_path / "plugin"


class TestSessionStartHealth:
    def start(self, wiki, **env):
        """The first line of session-start's context, and _status.md."""
        result = run_hook(
            SESSION_START, session_start_payload(),
            {"CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki), **env},
        )
        assert result.returncode == 0, result.stderr
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        return context.split("\n")[0], (wiki / "_status.md").read_text()

    def test_counts_reference_problems_apart_from_the_total(self, tmp_path):
        wiki = make_wiki(tmp_path)
        write(wiki, "concepts/p.md", wiki_page(
            "['user, conversation, 2026-01-15']", "[source: user]\n"
        ).replace(f"created: '{TODAY}'", "created: 2026-01-15T00:00:00.000Z"))
        line, status = self.start(wiki)
        assert line.endswith(
            "Health check: 1 issues. Broken links: 0. Orphans: 1. Stale: 0. "
            "Confidence decay: 0. Pages with invalid frontmatter: 1, unresolved "
            "sources: 1, unresolved citations: 1. See _status.md for details."
        )
        for row in (
            "| Pages with invalid frontmatter (I1) | 1 |",
            "| Pages with unresolved sources (I2) | 1 |",
            "| Pages with unresolved citations (I3) | 1 |",
            "| Secondhand, unverified (R10) | 0 |",
        ):
            assert row in status
        assert not list((wiki / "queries").glob("lint-*.md"))  # --json writes no report

    def test_a_clean_wiki_reports_no_reference_problems(self, tmp_path):
        line, _ = self.start(make_wiki(tmp_path))
        assert line.endswith("Health check: 0 issues.")

    def test_lists_secondhand_pages(self, tmp_path):
        wiki = make_wiki(tmp_path)
        write(wiki, "raw/internal/conversation-2026-01-15-pricing-tier.md", CONVERSATION)
        write(wiki, "concepts/told.md", wiki_page(
            "[raw/internal/conversation-2026-01-15-pricing-tier.md]"
        ))
        _, status = self.start(wiki)
        assert "| Secondhand, unverified (R10) | 1 |" in status
        section = status.split("## Secondhand, unverified\n", 1)[1]
        assert "\n- concepts/told.md\n" in section

    def test_a_lint_crash_reads_as_health_unknown(self, tmp_path):
        wiki = make_wiki(tmp_path)
        plugin = fake_plugin(tmp_path, "raise SystemExit('lint crashed')\n")
        line, status = self.start(wiki, CLAUDE_PLUGIN_ROOT=str(plugin))
        assert "Health check: lint failed, health unknown." in line
        assert "| Broken links | unknown |" in status
        assert "| Pages with unresolved citations (I3) | unknown |" in status
        assert "**lint failed: health unknown.**" in status

    def test_output_that_isnt_lints_json_reads_as_health_unknown(self, tmp_path):
        wiki = make_wiki(tmp_path)
        plugin = fake_plugin(tmp_path, "print('{}')\n")
        line, _ = self.start(wiki, CLAUDE_PLUGIN_ROOT=str(plugin))
        assert "Health check: lint failed, health unknown." in line
