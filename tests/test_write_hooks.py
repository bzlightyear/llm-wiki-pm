"""
Tests for the write hooks' coverage of every write path: wiki-search MCP
payloads (both tool-name forms), slug-named snapshots, the overview.md rule,
briefings/, directory-page assets/, the raw write-once warning, and the
freshness gate judged on the post-edit text.

Kept apart from test_hooks.py (upstream-owned) to keep merges simple.

Run: python3 -m pytest tests/test_write_hooks.py -v
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

from test_hooks import PRE_WRITE, REPO_ROOT, make_entity, make_wiki, run_hook

sys.path.insert(0, str(REPO_ROOT / "skills" / "llm-wiki-pm" / "scripts"))
from lint import snapshot  # noqa: E402

TODAY = date.today().isoformat()
MCP_NAMES = ["mcp__wiki-search", "mcp__plugin_llm-wiki-pm_wiki-search"]

GROUNDED = (
    "---\ntitle: t\ntype: entity\ntags: [company]\n"
    "sources:\n  - raw/articles/x.md\n---\n"
    "# t\nClaim [source: x, p.1]\n[[a]] [[b]]\n"
)
UNGROUNDED = (
    "---\ntitle: t\ntype: entity\ntags: [company]\n"
    "sources:\n  - entities/other.md\n---\n"
    "# t\nSome prose with no primary source and no inline marker.\n"
)
DIGEST = (
    "---\ntitle: Brief\ntype: query\ntags: [meta]\nsources: []\n"
    "lifecycle: dated-digest\n---\n# Brief\nToday's summary.\n"
)


def pre(wiki: Path, tool: str, tool_input: dict):
    payload = {
        "session_id": "test-session-123",
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": tool_input,
        "cwd": "/tmp",
    }
    r = run_hook(PRE_WRITE, payload, {"CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki)})
    assert r.returncode == 0, r.stderr
    return r.stdout


def context(stdout: str) -> str:
    if not stdout.strip():
        return ""
    return json.loads(stdout)["hookSpecificOutput"]["additionalContext"]


def snaps(wiki: Path, name: str):
    return list((wiki / "_archive").glob(f"{name}-*.md"))


def write_page(wiki: Path, rel: str, text: str = GROUNDED) -> Path:
    p = wiki / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


# ---------------------------------------------------------------------------
# lint.snapshot()
# ---------------------------------------------------------------------------


class TestSnapshotFunction:
    def test_names_by_slug_and_copies(self, tmp_path):
        wiki = make_wiki(tmp_path)
        page = make_entity(wiki, "acme", updated=date.today())
        arc = snapshot(page, wiki)
        assert arc == wiki / "_archive" / f"acme-{TODAY}.md"
        assert arc.read_text() == page.read_text()

    def test_readme_page_named_by_folder(self, tmp_path):
        wiki = make_wiki(tmp_path)
        page = write_page(wiki, "queries/sprint-x/README.md")
        assert snapshot(page, wiki).name == f"sprint-x-{TODAY}.md"

    def test_keeps_first_snapshot_of_the_day(self, tmp_path):
        wiki = make_wiki(tmp_path)
        page = make_entity(wiki, "acme", updated=date.today())
        first = page.read_text()
        snapshot(page, wiki)
        page.write_text("changed")
        assert snapshot(page, wiki).read_text() == first

    def test_creates_archive_dir(self, tmp_path):
        wiki = make_wiki(tmp_path)
        (wiki / "_archive").rmdir()
        page = make_entity(wiki, "acme", updated=date.today())
        assert snapshot(page, wiki).exists()


# ---------------------------------------------------------------------------
# Snapshot naming and scope
# ---------------------------------------------------------------------------


class TestSnapshotScope:
    def test_readme_pages_no_longer_collide(self, tmp_path):
        wiki = make_wiki(tmp_path)
        a = write_page(wiki, "queries/sprint-a/README.md")
        b = write_page(wiki, "queries/sprint-b/README.md")
        for page in (a, b):
            pre(wiki, "Write", {"file_path": str(page), "content": GROUNDED})
        assert snaps(wiki, "sprint-a") and snaps(wiki, "sprint-b")
        assert not snaps(wiki, "README")

    def test_briefings_are_snapshotted(self, tmp_path):
        wiki = make_wiki(tmp_path)
        brief = write_page(wiki, "briefings/2026-01-15.md", DIGEST)
        pre(wiki, "Edit", {"file_path": str(brief), "old_string": "Today", "new_string": "Now"})
        assert snaps(wiki, "2026-01-15")

    def test_assets_subfolder_is_skipped(self, tmp_path):
        wiki = make_wiki(tmp_path)
        deck = write_page(wiki, "queries/sprint-a/assets/deck.md", UNGROUNDED)
        out = pre(wiki, "Write", {"file_path": str(deck), "content": UNGROUNDED})
        assert out.strip() == ""
        assert not snaps(wiki, "deck")

    def test_overview_snapshotted_on_write(self, tmp_path):
        wiki = make_wiki(tmp_path)
        pre(wiki, "Write", {"file_path": str(wiki / "overview.md"), "content": "new"})
        assert snaps(wiki, "overview")

    def test_overview_not_snapshotted_on_edit(self, tmp_path):
        wiki = make_wiki(tmp_path)
        pre(wiki, "Edit", {"file_path": str(wiki / "overview.md"),
                           "old_string": "Overview", "new_string": "Summary"})
        assert not snaps(wiki, "overview")

    def test_index_never_snapshotted(self, tmp_path):
        wiki = make_wiki(tmp_path)
        pre(wiki, "Write", {"file_path": str(wiki / "index.md"), "content": "new"})
        assert not snaps(wiki, "index")


# ---------------------------------------------------------------------------
# wiki-search MCP payloads
# ---------------------------------------------------------------------------


class TestMcpVault:
    def test_update_snapshots_under_both_tool_names(self, tmp_path):
        for prefix in MCP_NAMES:
            (tmp_path / prefix).mkdir()
            wiki = make_wiki(tmp_path / prefix)
            make_entity(wiki, "acme", updated=date.today())
            pre(wiki, f"{prefix}__vault",
                {"action": "update", "path": "entities/acme.md", "content": GROUNDED})
            assert snaps(wiki, "acme"), prefix

    def test_update_judged_from_content(self, tmp_path):
        wiki = make_wiki(tmp_path)
        make_entity(wiki, "acme", updated=date.today())
        out = pre(wiki, "mcp__wiki-search__vault",
                  {"action": "update", "path": "entities/acme.md", "content": UNGROUNDED})
        assert "Freshness gate" in context(out)

    def test_create_ungrounded_fires_gate(self, tmp_path):
        wiki = make_wiki(tmp_path)
        out = pre(wiki, "mcp__wiki-search__vault",
                  {"action": "create", "path": "entities/new.md", "content": UNGROUNDED})
        assert "Freshness gate" in context(out)
        assert not snaps(wiki, "new")

    def test_create_grounded_is_silent(self, tmp_path):
        wiki = make_wiki(tmp_path)
        out = pre(wiki, "mcp__wiki-search__vault",
                  {"action": "create", "path": "entities/new.md", "content": GROUNDED})
        assert out.strip() == ""

    def test_delete_snapshots(self, tmp_path):
        wiki = make_wiki(tmp_path)
        make_entity(wiki, "acme", updated=date.today())
        out = pre(wiki, "mcp__wiki-search__vault",
                  {"action": "delete", "path": "entities/acme.md"})
        assert snaps(wiki, "acme")
        assert out.strip() == ""

    def test_create_from_template_is_silent(self, tmp_path):
        wiki = make_wiki(tmp_path)
        out = pre(wiki, "mcp__wiki-search__vault",
                  {"action": "create_from_template", "path": "entities/new.md",
                   "templatePath": "templates/entity.md"})
        assert out.strip() == ""

    def test_reads_are_ignored(self, tmp_path):
        wiki = make_wiki(tmp_path)
        make_entity(wiki, "acme", updated=date.today())
        for action in ("read", "list", "stat"):
            out = pre(wiki, "mcp__wiki-search__vault",
                      {"action": action, "path": "entities/acme.md"})
            assert out.strip() == ""
        assert not snaps(wiki, "acme")

    def test_path_escaping_the_vault_is_ignored(self, tmp_path):
        wiki = make_wiki(tmp_path)
        outside = tmp_path / "entities" / "x.md"
        outside.parent.mkdir()
        outside.write_text(UNGROUNDED)
        out = pre(wiki, "mcp__wiki-search__vault",
                  {"action": "update", "path": "../entities/x.md", "content": UNGROUNDED})
        assert out.strip() == ""


class TestMcpEdit:
    def test_single_edit_snapshots_without_gate(self, tmp_path):
        for prefix in MCP_NAMES:
            (tmp_path / prefix).mkdir()
            wiki = make_wiki(tmp_path / prefix)
            make_entity(wiki, "acme", updated=date.today())
            out = pre(wiki, f"{prefix}__edit",
                      {"path": "entities/acme.md", "operation": "append",
                       "heading": "acme", "content": "more"})
            assert snaps(wiki, "acme"), prefix
            assert out.strip() == "", "MCP edit ops are not simulated"

    def test_batch_snapshots_every_path(self, tmp_path):
        wiki = make_wiki(tmp_path)
        make_entity(wiki, "acme", updated=date.today())
        make_entity(wiki, "beta", updated=date.today())
        pre(wiki, "mcp__wiki-search__edit",
            {"operations": [
                {"path": "entities/acme.md", "operation": "string_replace",
                 "searchText": "acme", "content": "Acme"},
                {"path": "entities/beta.md", "operation": "string_replace",
                 "searchText": "beta", "content": "Beta"},
            ]})
        assert snaps(wiki, "acme") and snaps(wiki, "beta")

    def test_dry_run_is_ignored(self, tmp_path):
        wiki = make_wiki(tmp_path)
        make_entity(wiki, "acme", updated=date.today())
        pre(wiki, "mcp__wiki-search__edit",
            {"path": "entities/acme.md", "operation": "frontmatter_set",
             "content": "status: x", "dryRun": True})
        assert not snaps(wiki, "acme")


# ---------------------------------------------------------------------------
# Raw write-once warning
# ---------------------------------------------------------------------------


class TestRawGuard:
    def test_edit_to_existing_record_warns(self, tmp_path):
        wiki = make_wiki(tmp_path)
        rec = write_page(wiki, "raw/articles/src-2026.md", "body")
        out = pre(wiki, "Edit", {"file_path": str(rec), "old_string": "body", "new_string": "x"})
        assert "write-once" in context(out)

    def test_mcp_update_to_existing_record_warns(self, tmp_path):
        wiki = make_wiki(tmp_path)
        write_page(wiki, "raw/articles/src-2026.md", "body")
        out = pre(wiki, "mcp__wiki-search__vault",
                  {"action": "update", "path": "raw/articles/src-2026.md", "content": "x"})
        assert "write-once" in context(out)

    def test_new_record_is_silent(self, tmp_path):
        wiki = make_wiki(tmp_path)
        rec = wiki / "raw" / "articles" / "new-2026.md"
        out = pre(wiki, "Write", {"file_path": str(rec), "content": "body"})
        assert out.strip() == ""

    def test_records_are_not_snapshotted(self, tmp_path):
        wiki = make_wiki(tmp_path)
        rec = write_page(wiki, "raw/articles/src-2026.md", "body")
        pre(wiki, "Write", {"file_path": str(rec), "content": "x"})
        assert not snaps(wiki, "src-2026")

    def test_raw_assets_are_not_records(self, tmp_path):
        wiki = make_wiki(tmp_path)
        asset = write_page(wiki, "raw/assets/deck.md", "body")
        out = pre(wiki, "Write", {"file_path": str(asset), "content": "x"})
        assert out.strip() == ""


# ---------------------------------------------------------------------------
# Freshness gate on the post-edit text
# ---------------------------------------------------------------------------


class TestPostImage:
    def test_edit_that_grounds_the_page_is_silent(self, tmp_path):
        wiki = make_wiki(tmp_path)
        page = write_page(wiki, "entities/acme.md", UNGROUNDED)
        out = pre(wiki, "Edit", {
            "file_path": str(page),
            "old_string": "no inline marker.",
            "new_string": "a marker [source: x, p.1].",
        })
        assert out.strip() == ""

    def test_edit_that_ungrounds_the_page_fires(self, tmp_path):
        wiki = make_wiki(tmp_path)
        page = write_page(wiki, "entities/acme.md", GROUNDED)
        text = GROUNDED.replace("  - raw/articles/x.md", "  - entities/other.md")
        page.write_text(text)
        out = pre(wiki, "Edit", {
            "file_path": str(page),
            "old_string": "Claim [source: x, p.1]",
            "new_string": "Claim",
        })
        assert "Freshness gate" in context(out)

    def test_multiedit_applies_edits_in_order(self, tmp_path):
        wiki = make_wiki(tmp_path)
        page = write_page(wiki, "entities/acme.md", UNGROUNDED)
        out = pre(wiki, "MultiEdit", {"file_path": str(page), "edits": [
            {"old_string": "no inline marker.", "new_string": "MARK"},
            {"old_string": "MARK", "new_string": "[source: x, p.1]"},
        ]})
        assert out.strip() == ""

    def test_replace_all(self, tmp_path):
        wiki = make_wiki(tmp_path)
        page = write_page(wiki, "entities/acme.md",
                          UNGROUNDED.replace("  - entities/other.md", "  - raw/a.md\n  - raw/b.md"))
        out = pre(wiki, "Edit", {"file_path": str(page), "old_string": "  - raw/",
                                 "new_string": "  - entities/", "replace_all": True})
        assert "Freshness gate" in context(out)

    def test_dated_digest_is_exempt_anywhere(self, tmp_path):
        wiki = make_wiki(tmp_path)
        for rel in ("briefings/2026-01-15.md", "queries/weekly-brief-2026-01-15.md"):
            out = pre(wiki, "Write", {"file_path": str(wiki / rel), "content": DIGEST})
            assert out.strip() == "", rel


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestMatcher:
    def _matcher(self):
        data = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text())
        (group,) = data["hooks"]["PreToolUse"]
        return group["matcher"]

    def test_pre_write_matches_every_write_tool(self):
        m = self._matcher()
        for tool in ["Write", "Edit", "MultiEdit"] + [
            f"{p}__{t}" for p in MCP_NAMES for t in ("vault", "edit")
        ]:
            assert re.fullmatch(m, tool), tool

    def test_pre_write_skips_read_tools(self):
        m = self._matcher()
        for tool in ("Read", "mcp__wiki-search__view", "mcp__wiki-search__system"):
            assert not re.fullmatch(m, tool), tool
