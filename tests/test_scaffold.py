"""
Tests for session-start.sh's scaffold and the vault contract template
(templates/vault-contract.md), which it copies to meta/contract.md for the
wiki-search MCP.

Run: python3 -m pytest tests/test_scaffold.py -v
"""

import re

from test_hooks import (
    SESSION_START,
    TEMPLATES_DIR,
    make_wiki,
    run_hook,
    session_start_payload,
)
from test_lint import DEFAULT_CONTRACT, TODAY, findings, lint, wiki_page, wikifm, write

CONTRACT_TEMPLATE = TEMPLATES_DIR / "vault-contract.md"


def start(wiki):
    return run_hook(
        SESSION_START,
        session_start_payload(),
        {"CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki)},
    )


def scaffolded(wiki):
    return all((wiki / f).is_file() for f in ("SCHEMA.md", "index.md", "log.md", "overview.md"))


def note_template():
    """The page skeleton in the contract's Note Template section."""
    text = CONTRACT_TEMPLATE.read_text()
    section = text.split("## Note Template", 1)[1]
    return re.search(r"```markdown\n(.*?)```", section, re.DOTALL).group(1)


# ── the scaffold copies the contract ──


def test_new_wiki_gets_the_contract_template(tmp_path):
    wiki = tmp_path / "wiki"
    result = start(wiki)
    assert result.returncode == 0, result.stderr
    assert scaffolded(wiki)
    assert (wiki / "meta" / "contract.md").read_text() == CONTRACT_TEMPLATE.read_text()


def test_scaffold_keeps_a_contract_the_mcp_wrote_first(tmp_path):
    """The MCP writes its default at startup, maybe before this hook runs. The
    scaffold still runs and leaves the default for R11 to report."""
    wiki = tmp_path / "wiki"
    write(wiki, "meta/contract.md", DEFAULT_CONTRACT)
    write(wiki, "meta/overview.md", "# Overview\n")
    (wiki / ".markdown_vault_mcp").mkdir()
    result = start(wiki)
    assert result.returncode == 0, result.stderr
    assert scaffolded(wiki)
    assert (wiki / "meta" / "contract.md").read_text() == DEFAULT_CONTRACT
    assert any("(R11)" in w for w in findings(wiki)["warnings"])


def test_existing_wiki_gets_no_contract(tmp_path):
    """The copy is part of the scaffold, not of every session."""
    wiki = make_wiki(tmp_path)
    start(wiki)
    assert not (wiki / "meta").exists()


# ── what counts as an empty wiki directory ──


def test_meta_alone_counts_as_empty(tmp_path):
    wiki = tmp_path / "wiki"
    write(wiki, "meta/contract.md", DEFAULT_CONTRACT)
    start(wiki)
    assert scaffolded(wiki)


def test_what_a_skipped_first_session_left_counts_as_empty(tmp_path):
    """A wiki made before the meta/ rule, whose first session skipped the
    scaffold: the MCP's files plus this hook's own _status.md and lock."""
    wiki = tmp_path / "wiki"
    write(wiki, "meta/contract.md", DEFAULT_CONTRACT)
    (wiki / ".markdown_vault_mcp").mkdir()
    write(wiki, "_status.md", "# Wiki Status\n")
    write(wiki, ".wiki-lock", "other-session:2026-01-01T00:00:00Z\n")
    start(wiki)
    assert scaffolded(wiki)


def test_meta_beside_a_user_file_is_not_scaffolded(tmp_path):
    wiki = tmp_path / "wiki"
    write(wiki, "meta/contract.md", DEFAULT_CONTRACT)
    write(wiki, "my-notes.md", "important content")
    result = start(wiki)
    assert not (wiki / "SCHEMA.md").exists()
    assert (wiki / "my-notes.md").read_text() == "important content"
    assert "Skipping scaffold" in result.stderr


# ── the template itself ──


def test_template_is_not_reported_as_the_mcp_default(tmp_path):
    wiki = make_wiki(tmp_path)
    write(wiki, "meta/contract.md", CONTRACT_TEMPLATE.read_text())
    assert lint.check_contract(wiki) is None


def test_template_type_enum_matches_schema():
    schema_line = re.search(r"^type: (.+)$", (TEMPLATES_DIR / "SCHEMA.md").read_text(), re.MULTILINE)
    contract_line = re.search(r"^- `type`: enum — (.+)$", CONTRACT_TEMPLATE.read_text(), re.MULTILINE)
    schema_types = [t.strip() for t in schema_line.group(1).split("|")]
    contract_types = [t.strip(" `") for t in contract_line.group(1).split("|")]
    assert contract_types == schema_types


def test_note_template_is_a_page_lint_flags_until_its_source_is_filled(tmp_path):
    """Filled in except for sources: and the body text, the skeleton has
    every required key and no error, and R6 reports the placeholder entry."""
    page = (
        note_template()
        .replace("{{Title}}", "Usage pricing")
        .replace("{{YYYY-MM-DD}}", TODAY)
        .replace("{{entity | concept | comparison | query | summary | persona}}", "concept")
        .replace("{{tag from SCHEMA.md}}", "ai")
        .replace("{{page-slug}}", "neighbor")
    )
    fields, errors = wikifm.parse(page)
    assert errors == []
    assert lint.REQUIRED_FRONTMATTER <= set(fields)

    wiki = make_wiki(tmp_path)
    write(wiki, "concepts/usage-pricing.md", page)
    write(wiki, "concepts/neighbor.md", wiki_page(body="# n\n[[usage-pricing]]\n"))
    result = findings(wiki)
    assert not any("usage-pricing" in e for e in result["errors"])
    assert any(
        "(R6): concepts/usage-pricing.md" in w and "raw/{{folder}}/{{record-id}}.md" in w
        for w in result["warnings"]
    )
