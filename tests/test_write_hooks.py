"""
Tests for the write hooks' coverage of every write path: wiki-search MCP
payloads (both tool-name forms), the checkpoint commit before a session's
first write (lint.checkpoint(), pre-write.sh and session-start.sh),
directory-page assets/, the raw write-once warning, the freshness gate judged
on the post-edit text, post-validate.sh's checks of the page as written, and
the recent-writer note that replaced .wiki-lock.

Kept apart from test_hooks.py (upstream-owned) to keep merges simple.

Run: python3 -m pytest tests/test_write_hooks.py -v
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

from test_hooks import (PRE_WRITE, REPO_ROOT, SESSION_START, make_entity, make_wiki,
                        run_hook, session_start_payload)

POST_VALIDATE = REPO_ROOT / "hooks" / "post-validate.sh"

sys.path.insert(0, str(REPO_ROOT / "skills" / "llm-wiki-pm" / "scripts"))
from lint import checkpoint  # noqa: E402

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


def pre(wiki: Path, tool: str, tool_input: dict, session: str = "test-session-123"):
    payload = {
        "session_id": session,
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": tool_input,
        "cwd": "/tmp",
    }
    # The checkpoint's per-session marker goes in TMPDIR: one per test.
    r = run_hook(PRE_WRITE, payload, {"CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
                                      "TMPDIR": str(wiki.parent)})
    assert r.returncode == 0, r.stderr
    return r.stdout


def context(stdout: str) -> str:
    if not stdout.strip():
        return ""
    return json.loads(stdout)["hookSpecificOutput"]["additionalContext"]


def git(wiki: Path, *args) -> str:
    return subprocess.run(["git", "-C", str(wiki), *args], capture_output=True,
                          text=True, check=True).stdout


def git_init(wiki: Path) -> Path:
    """Make the wiki a git repo with everything committed."""
    git(wiki, "init", "-q")
    git(wiki, "config", "user.name", "Test")
    git(wiki, "config", "user.email", "test@example.com")
    git(wiki, "config", "commit.gpgsign", "false")
    git(wiki, "add", "-A")
    git(wiki, "commit", "-q", "-m", "base")
    return wiki


def checkpoints(wiki: Path) -> list:
    """The subjects of the wiki's checkpoint commits, newest first."""
    if not (wiki / ".git").exists():
        return []
    log = git(wiki, "log", "--format=%s", "--grep=^checkpoint:")
    return [line for line in log.splitlines() if line]


def dirty_wiki(tmp_path: Path) -> Path:
    """A git wiki with one committed page, changed since the last commit."""
    wiki = make_wiki(tmp_path)
    make_entity(wiki, "acme", updated=date.today())
    git_init(wiki)
    (wiki / "entities" / "acme.md").write_text(GROUNDED)
    return wiki


def write_page(wiki: Path, rel: str, text: str = GROUNDED) -> Path:
    p = wiki / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


# ---------------------------------------------------------------------------
# lint.checkpoint()
# ---------------------------------------------------------------------------


class TestCheckpointFunction:
    def test_commits_uncommitted_changes_but_not_status(self, tmp_path):
        wiki = dirty_wiki(tmp_path)
        (wiki / "_status.md").write_text("health\n")
        commit = checkpoint(wiki, "before x")
        assert commit and checkpoints(wiki) == ["checkpoint: before x"]
        assert git(wiki, "show", "HEAD:entities/acme.md") == GROUNDED
        assert git(wiki, "status", "--porcelain") == "?? _status.md\n"

    def test_clean_wiki_makes_no_commit(self, tmp_path):
        wiki = git_init(make_wiki(tmp_path))
        (wiki / "_status.md").write_text("health\n")
        assert checkpoint(wiki, "x") is None
        assert checkpoints(wiki) == []

    def test_wiki_that_isnt_a_git_repo_is_left_alone(self, tmp_path):
        wiki = make_wiki(tmp_path)
        assert checkpoint(wiki, "x") is None
        assert not (wiki / ".git").exists()

    def test_wiki_inside_a_larger_repo_is_left_alone(self, tmp_path):
        wiki = make_wiki(tmp_path)
        git_init(tmp_path)
        make_entity(wiki, "acme", updated=date.today())
        assert checkpoint(wiki, "x") is None
        assert checkpoints(tmp_path) == []

    def test_no_commit_during_a_merge(self, tmp_path):
        wiki = dirty_wiki(tmp_path)
        (wiki / ".git" / "MERGE_HEAD").write_text(git(wiki, "rev-parse", "HEAD"))
        assert checkpoint(wiki, "x") is None
        assert checkpoints(wiki) == []

    def test_a_held_index_lock_skips_without_raising(self, tmp_path):
        wiki = dirty_wiki(tmp_path)
        (wiki / ".git" / "index.lock").write_text("")
        assert checkpoint(wiki, "x") is None
        assert checkpoints(wiki) == []


# ---------------------------------------------------------------------------
# The checkpoint in the hooks
# ---------------------------------------------------------------------------


class TestCheckpointHooks:
    def test_first_write_of_a_session_commits_once(self, tmp_path):
        wiki = dirty_wiki(tmp_path)
        page = wiki / "entities" / "acme.md"
        out = pre(wiki, "Write", {"file_path": str(page), "content": GROUNDED})
        assert checkpoints(wiki) == ["checkpoint: before session test-ses writes"]
        assert "restore --source=" in context(out)
        page.write_text(GROUNDED + "more\n")
        pre(wiki, "Write", {"file_path": str(page), "content": GROUNDED})
        assert len(checkpoints(wiki)) == 1, "once per session"
        pre(wiki, "Write", {"file_path": str(page), "content": GROUNDED}, session="other-session")
        assert len(checkpoints(wiki)) == 2, "a new session commits again"

    def test_clean_wiki_is_silent(self, tmp_path):
        wiki = make_wiki(tmp_path)
        page = make_entity(wiki, "acme", updated=date.today())
        git_init(wiki)
        out = pre(wiki, "Write", {"file_path": str(page), "content": GROUNDED})
        assert out.strip() == "" and checkpoints(wiki) == []

    def test_write_outside_the_wiki_makes_no_checkpoint(self, tmp_path):
        wiki = dirty_wiki(tmp_path)
        pre(wiki, "Write", {"file_path": str(tmp_path / "notes.md"), "content": "x"})
        assert checkpoints(wiki) == []

    def test_nothing_is_written_to_archive(self, tmp_path):
        wiki = dirty_wiki(tmp_path)
        pre(wiki, "Write", {"file_path": str(wiki / "entities" / "acme.md"),
                            "content": GROUNDED})
        pre(wiki, "Write", {"file_path": str(wiki / "overview.md"), "content": "new"})
        assert list((wiki / "_archive").iterdir()) == []

    def test_session_start_inside_the_wiki_commits(self, tmp_path):
        wiki = dirty_wiki(tmp_path)
        r = run_hook(SESSION_START, session_start_payload(),
                     {"CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki), "_CWD": str(wiki)})
        assert r.returncode == 0, r.stderr
        assert checkpoints(wiki) == ["checkpoint: session start"]
        assert "Checkpoint " in json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]

    def test_session_start_elsewhere_doesnt_commit(self, tmp_path):
        wiki = dirty_wiki(tmp_path)
        r = run_hook(SESSION_START, session_start_payload(),
                     {"CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki)})
        assert r.returncode == 0, r.stderr
        assert checkpoints(wiki) == []


class TestAssets:
    def test_assets_subfolder_is_skipped(self, tmp_path):
        wiki = make_wiki(tmp_path)
        deck = write_page(wiki, "queries/sprint-a/assets/deck.md", UNGROUNDED)
        out = pre(wiki, "Write", {"file_path": str(deck), "content": UNGROUNDED})
        assert out.strip() == ""


# ---------------------------------------------------------------------------
# wiki-search MCP payloads
# ---------------------------------------------------------------------------


class TestMcpVault:
    def test_update_checkpoints_under_both_tool_names(self, tmp_path):
        for prefix in MCP_NAMES:
            (tmp_path / prefix).mkdir()
            wiki = dirty_wiki(tmp_path / prefix)
            pre(wiki, f"{prefix}__vault",
                {"action": "update", "path": "entities/acme.md", "content": GROUNDED})
            assert len(checkpoints(wiki)) == 1, prefix

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

    def test_create_grounded_is_silent(self, tmp_path):
        wiki = make_wiki(tmp_path)
        out = pre(wiki, "mcp__wiki-search__vault",
                  {"action": "create", "path": "entities/new.md", "content": GROUNDED})
        assert out.strip() == ""

    def test_delete_checkpoints_without_gate(self, tmp_path):
        wiki = dirty_wiki(tmp_path)
        out = pre(wiki, "mcp__wiki-search__vault",
                  {"action": "delete", "path": "entities/acme.md"})
        assert len(checkpoints(wiki)) == 1
        assert "Freshness gate" not in context(out)

    def test_create_from_template_is_silent(self, tmp_path):
        wiki = make_wiki(tmp_path)
        out = pre(wiki, "mcp__wiki-search__vault",
                  {"action": "create_from_template", "path": "entities/new.md",
                   "templatePath": "templates/entity.md"})
        assert out.strip() == ""

    def test_reads_are_ignored(self, tmp_path):
        wiki = dirty_wiki(tmp_path)
        for action in ("read", "list", "stat"):
            out = pre(wiki, "mcp__wiki-search__vault",
                      {"action": action, "path": "entities/acme.md"})
            assert out.strip() == ""
        assert checkpoints(wiki) == []

    def test_path_escaping_the_vault_is_ignored(self, tmp_path):
        wiki = make_wiki(tmp_path)
        outside = tmp_path / "entities" / "x.md"
        outside.parent.mkdir()
        outside.write_text(UNGROUNDED)
        out = pre(wiki, "mcp__wiki-search__vault",
                  {"action": "update", "path": "../entities/x.md", "content": UNGROUNDED})
        assert out.strip() == ""


class TestMcpEdit:
    def test_single_edit_checkpoints_without_gate(self, tmp_path):
        for prefix in MCP_NAMES:
            (tmp_path / prefix).mkdir()
            wiki = dirty_wiki(tmp_path / prefix)
            out = pre(wiki, f"{prefix}__edit",
                      {"path": "entities/acme.md", "operation": "append",
                       "heading": "acme", "content": "more"})
            assert len(checkpoints(wiki)) == 1, prefix
            assert "Freshness gate" not in context(out), "MCP edit ops are not simulated"

    def test_batch_checkpoints_once(self, tmp_path):
        wiki = dirty_wiki(tmp_path)
        make_entity(wiki, "beta", updated=date.today())
        pre(wiki, "mcp__wiki-search__edit",
            {"operations": [
                {"path": "entities/acme.md", "operation": "string_replace",
                 "searchText": "acme", "content": "Acme"},
                {"path": "entities/beta.md", "operation": "string_replace",
                 "searchText": "beta", "content": "Beta"},
            ]})
        assert len(checkpoints(wiki)) == 1

    def test_dry_run_is_ignored(self, tmp_path):
        wiki = dirty_wiki(tmp_path)
        pre(wiki, "mcp__wiki-search__edit",
            {"path": "entities/acme.md", "operation": "frontmatter_set",
             "content": "status: x", "dryRun": True})
        assert checkpoints(wiki) == []


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

    def test_post_validate_registered_synchronously_with_same_matcher(self):
        data = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text())
        (group,) = data["hooks"]["PostToolUse"]
        assert group["matcher"] == self._matcher()
        (hook,) = group["hooks"]
        assert hook["command"].endswith("/hooks/post-validate.sh")
        assert not hook.get("async"), "its output must reach the agent in the same turn"


# ---------------------------------------------------------------------------
# post-validate.sh
# ---------------------------------------------------------------------------

CLEAN = (
    "---\ntitle: Acme\ncreated: '2026-01-01'\nupdated: '2026-01-02'\n"
    "type: entity\ntags: [company]\nsources:\n  - raw/articles/acme-2026.md\n---\n"
    "# Acme\nClaim [source: acme-2026, p.1]. See [[beta]] and [[overview]].\n"
)


def post(wiki: Path, tool: str, tool_input: dict, tool_response: dict = None,
         session: str = "test-session-123"):
    payload = {
        "session_id": session,
        "hook_event_name": "PostToolUse",
        "tool_name": tool,
        "tool_input": tool_input,
        "tool_response": tool_response or {},
        "cwd": "/tmp",
    }
    # The recent-writer marker goes in TMPDIR, the folder pre() uses.
    r = run_hook(POST_VALIDATE, payload, {"CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
                                          "TMPDIR": str(wiki.parent)})
    assert r.returncode == 0, r.stderr
    assert r.stderr == "", r.stderr
    return r.stdout


def valid_wiki(tmp_path: Path) -> Path:
    """A wiki where CLEAN, written to entities/acme.md, breaks no rule."""
    wiki = make_wiki(tmp_path)
    write_page(wiki, "raw/articles/acme-2026.md", "---\ntitle: src\n---\nbody\n")
    write_page(wiki, "entities/beta.md", CLEAN.replace("Acme", "Beta").replace("[[beta]]", "[[acme]]"))
    return wiki


def write_acme(wiki: Path, text: str, tool: str = "Write", response: dict = None):
    """Write entities/acme.md, then run post-validate as a Write of it."""
    p = write_page(wiki, "entities/acme.md", text)
    return post(wiki, tool, {"file_path": str(p), "content": text},
                response or {"path": str(p), "status": "updated"})


def status_text(wiki: Path) -> str:
    s = wiki / "_status.md"
    return s.read_text() if s.exists() else ""


class TestPostValidateChecks:
    def test_clean_page_is_silent(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        assert write_acme(wiki, CLEAN) == ""
        assert status_text(wiki) == ""

    def test_block_item_on_key_line(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        out = write_acme(wiki, CLEAN.replace("tags: [company]", "tags: - company"))
        assert "(R1)" in context(out)

    def test_missing_required_key(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        out = write_acme(wiki, CLEAN.replace("type: entity\n", ""))
        assert "frontmatter missing ['type'] (R12)" in context(out)

    def test_missing_frontmatter(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        out = write_acme(wiki, "# Acme\nNo frontmatter. [[beta]]\n")
        assert "missing frontmatter (R12)" in context(out)

    def test_date_outside_profile(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        out = write_acme(wiki, CLEAN.replace("'2026-01-02'", "2026-01-02T00:00:00Z"))
        assert "(R12)" in context(out)

    def test_source_that_does_not_exist(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        out = write_acme(wiki, CLEAN.replace("acme-2026.md", "missing-2026.md"))
        ctx = context(out)
        assert "(R6)" in ctx and "raw/articles/missing-2026.md" in ctx

    def test_undeclared_citation_names_the_path_to_declare(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        write_page(wiki, "raw/articles/other-2026.md", "body")
        out = write_acme(wiki, CLEAN.replace("p.1]", "p.1] [source: other-2026, p.2]"))
        ctx = context(out)
        assert "(R3)" in ctx and "declare raw/articles/other-2026.md" in ctx

    def test_citation_outside_the_grammar(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        out = write_acme(wiki, CLEAN.replace("[source: acme-2026, p.1]",
                                             "[source: raw/articles/acme-2026.md, p.1]"))
        ctx = context(out)
        assert "(R7)" in ctx and "(R3)" not in ctx

    def test_escaped_bracket(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        out = write_acme(wiki, CLEAN.replace("See [[beta]]", "See \\[[beta]]"))
        assert "escaped bracket" in context(out)

    def test_broken_link(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        out = write_acme(wiki, CLEAN + "Also [[nowhere]] and [[nowhere|again]].\n")
        assert "1 broken [[wikilink]](s): entities/acme.md — [[nowhere]]" in context(out)

    def test_links_resolve_against_lints_page_set(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        write_page(wiki, "briefings/brief-2026-01-01.md", DIGEST)
        write_page(wiki, "concepts/pricing/pricing.md", CLEAN)
        out = write_acme(wiki, CLEAN + "[[brief-2026-01-01]] [[pricing]] [[index]] [[beta#h|b]]\n")
        assert out == ""

    def test_link_match_is_exact_as_in_lint(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        out = write_acme(wiki, CLEAN + "[[Beta]]\n")
        assert "[[Beta]]" in context(out)

    def test_problems_appended_to_status(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        write_acme(wiki, CLEAN + "[[nowhere]]\n")
        s = status_text(wiki)
        assert "## Recent Write Issues" in s
        assert "write | acme**" in s and "[[nowhere]]" in s

    def test_output_capped_at_six_lines(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        bad = (
            "---\ntitle: Acme\ntitle: again\ncreated: 2026-01-01T10:00:00Z\n"
            "tags: - x\nsources:\n  - nowhere\n---\n"
            "[source: ghost] [source: a vs. b] \\[x] [[nowhere]]\n"
        )
        lines = context(write_acme(wiki, bad)).splitlines()
        assert len(lines) == 7  # header + 6
        assert lines[-1].startswith("- …and ") and "run lint.py" in lines[-1]
        # _status.md keeps every problem, uncapped
        assert status_text(wiki).count("\n  - ") > 6


class TestPostValidateScope:
    def test_root_file_gets_escape_check_only(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        p = write_page(wiki, "overview.md", "# Overview\n\\[[beta]] [[nowhere]]\n")
        ctx = context(post(wiki, "Write", {"file_path": str(p)}))
        assert "escaped bracket" in ctx and "nowhere" not in ctx

    def test_records_archive_and_reports_are_not_checked(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        for rel in ("raw/articles/x-2026.md", "_archive/acme-2026-01-01.md",
                    "queries/lint-2026-01-01.md", "SCHEMA.md",
                    "concepts/pricing/assets/deck.md"):
            p = write_page(wiki, rel, "[[nowhere]] \\[ no frontmatter\n")
            assert post(wiki, "Write", {"file_path": str(p)}) == "", rel

    def test_outside_wiki_and_non_markdown_ignored(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        outside = tmp_path / "outside.md"
        outside.write_text("[[nowhere]]")
        png = write_page(wiki, "entities/pic.png", "[[nowhere]]")
        assert post(wiki, "Write", {"file_path": str(outside)}) == ""
        assert post(wiki, "Write", {"file_path": str(png)}) == ""

    def test_unparseable_stdin_exits_zero(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        r = subprocess.run(["bash", str(POST_VALIDATE)], input="not json",
                           capture_output=True, text=True,
                           env={**os.environ, "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki)})
        assert r.returncode == 0 and r.stdout == ""


class TestPostValidateMcp:
    def test_vault_update_under_both_tool_names(self, tmp_path):
        for prefix in MCP_NAMES:
            (tmp_path / prefix).mkdir()
            wiki = valid_wiki(tmp_path / prefix)
            text = CLEAN.replace("acme-2026.md", "missing-2026.md")
            write_page(wiki, "entities/acme.md", text)
            out = post(wiki, f"{prefix}__vault",
                       {"action": "update", "path": "entities/acme.md", "content": text})
            assert "(R6)" in context(out), prefix

    def test_batch_edit_checks_every_path(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        write_page(wiki, "entities/acme.md", CLEAN + "[[nowhere-a]]\n")
        write_page(wiki, "entities/beta.md", CLEAN + "[[nowhere-b]]\n")
        out = post(wiki, "mcp__wiki-search__edit", {"operations": [
            {"path": "entities/acme.md", "operation": "string_replace"},
            {"path": "entities/beta.md", "operation": "string_replace"},
        ]})
        ctx = context(out)
        assert "[[nowhere-a]]" in ctx and "[[nowhere-b]]" in ctx

    def test_reads_deletes_and_dry_runs_ignored(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        write_page(wiki, "entities/acme.md", CLEAN + "[[nowhere]]\n")
        for tool, ti in [
            ("mcp__wiki-search__vault", {"action": "read", "path": "entities/acme.md"}),
            ("mcp__wiki-search__vault", {"action": "delete", "path": "entities/acme.md"}),
            ("mcp__wiki-search__edit", {"path": "entities/acme.md", "dryRun": True}),
        ]:
            assert post(wiki, tool, ti) == "", ti

    def test_freshness_gate_after_create_from_template(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        write_page(wiki, "entities/new.md", UNGROUNDED)
        out = post(wiki, "mcp__wiki-search__vault",
                   {"action": "create_from_template", "path": "entities/new.md",
                    "templatePath": "templates/entity.md"})
        assert "freshness gate: entities/new.md" in context(out)

    def test_freshness_gate_after_mcp_edit(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        write_page(wiki, "entities/acme.md", UNGROUNDED)
        out = post(wiki, "mcp__wiki-search__edit",
                   {"path": "entities/acme.md", "operation": "string_replace"})
        assert "freshness gate" in context(out)

    def test_no_freshness_gate_where_pre_write_judged_it(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        out = write_acme(wiki, UNGROUNDED)
        assert "freshness gate" not in context(out)

    def test_dated_digest_exempt_from_gate(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        write_page(wiki, "briefings/brief.md", DIGEST)
        out = post(wiki, "mcp__wiki-search__edit",
                   {"path": "briefings/brief.md", "operation": "append"})
        assert "freshness gate" not in context(out)


def long_page(n: int) -> str:
    """CLEAN padded to exactly n lines."""
    return CLEAN + "x\n" * (n - CLEAN.count("\n"))


class TestSplitReminder:
    def test_edit_that_crosses_200_lines(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        text = long_page(203)
        p = write_page(wiki, "entities/acme.md", text)
        out = post(wiki, "Edit", {"file_path": str(p), "old_string": "x\n",
                                  "new_string": "x\ny\ny\ny\ny\n"})
        ctx = context(out)
        assert "page is now 203 lines (> 200)" in ctx and "--cited-sources" in ctx
        assert status_text(wiki) == "", "a reminder isn't a problem"

    def test_edit_to_a_page_already_over_200_lines(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        p = write_page(wiki, "entities/acme.md", long_page(250))
        out = post(wiki, "MultiEdit", {"file_path": str(p), "edits": [
            {"old_string": "x\n", "new_string": "x\ny\n"},
            {"old_string": "y\n", "new_string": "z\n"},
        ]})
        assert out == ""

    def test_new_page_over_200_lines(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        out = write_acme(wiki, long_page(210), response={"status": "created"})
        assert "page is now 210 lines" in context(out)

    def test_rewrite_with_unknown_old_length(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        out = write_acme(wiki, long_page(210))  # status "updated"
        assert "page is now 210 lines" in context(out)

    def test_replace_all_with_unknown_count(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        p = write_page(wiki, "entities/acme.md", long_page(250))
        out = post(wiki, "Edit", {"file_path": str(p), "old_string": "x",
                                  "new_string": "x\n", "replace_all": True})
        assert "page is now 250 lines" in context(out)

    def test_short_page_no_reminder(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        assert write_acme(wiki, long_page(200), response={"status": "created"}) == ""


# ---------------------------------------------------------------------------
# No .wiki-lock; the recent-writer note
# ---------------------------------------------------------------------------


def marker(wiki: Path, session: str, minutes_ago: float = 0) -> Path:
    """Another session's recent-writer marker, last touched minutes_ago."""
    m = wiki.parent / f"llm-wiki-pm-wrote-{session}"
    m.touch()
    when = time.time() - minutes_ago * 60
    os.utime(m, (when, when))
    return m


def first_write(wiki: Path, session: str = "this-session") -> str:
    """The context pre-write.sh gives a grounded page write."""
    page = wiki / "entities" / "acme.md"
    return context(pre(wiki, "Write", {"file_path": str(page), "content": GROUNDED},
                       session=session))


class TestNoLock:
    def test_session_start_ignores_a_leftover_lock(self, tmp_path):
        wiki = make_wiki(tmp_path)
        lock = wiki / ".wiki-lock"
        lock.write_text(f"other-session:{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n")
        before = lock.read_text()
        r = run_hook(SESSION_START, session_start_payload(),
                     {"CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki)})
        assert r.returncode == 0, r.stderr
        ctx = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
        assert "LOCK" not in ctx and "Another wiki session" not in ctx
        assert lock.read_text() == before, "the hook writes no lock"

    def test_session_start_writes_no_lock(self, tmp_path):
        wiki = make_wiki(tmp_path)
        r = run_hook(SESSION_START, session_start_payload(),
                     {"CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki)})
        assert r.returncode == 0, r.stderr
        assert not (wiki / ".wiki-lock").exists()


class TestRecentWriter:
    def test_wiki_write_touches_the_sessions_marker(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        write_acme(wiki, CLEAN)
        m = tmp_path / "llm-wiki-pm-wrote-test-session-123"
        assert m.exists() and time.time() - m.stat().st_mtime < 60
        assert list(wiki.rglob("llm-wiki-pm-wrote-*")) == [], "nothing in the wiki"

    def test_mcp_delete_touches_the_marker(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        post(wiki, "mcp__wiki-search__vault", {"action": "delete", "path": "entities/gone.md"})
        assert (tmp_path / "llm-wiki-pm-wrote-test-session-123").exists()

    def test_write_outside_the_wiki_leaves_no_marker(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        outside = write_page(tmp_path, "notes.md", "x")
        post(wiki, "Write", {"file_path": str(outside)})
        assert not (tmp_path / "llm-wiki-pm-wrote-test-session-123").exists()

    def test_another_sessions_write_is_noted_at_the_first_write(self, tmp_path):
        wiki = valid_wiki(tmp_path)
        post(wiki, "Write", {"file_path": str(wiki / "entities" / "beta.md")},
             session="other-session")
        ctx = first_write(wiki)
        assert ("Session `other-session` wrote to the wiki 1 minute ago. "
                "Re-read a page before changing it.") in ctx
        assert first_write(wiki) == "", "only at the session's first write"

    def test_minutes_and_each_recent_session(self, tmp_path):
        wiki = make_wiki(tmp_path)
        marker(wiki, "session-a", minutes_ago=5)
        marker(wiki, "session-b", minutes_ago=29)
        ctx = first_write(wiki)
        assert "Session `session-a` wrote to the wiki 5 minutes ago." in ctx
        assert "Session `session-b` wrote to the wiki 29 minutes ago." in ctx

    def test_older_marker_is_not_noted(self, tmp_path):
        wiki = make_wiki(tmp_path)
        marker(wiki, "other-session", minutes_ago=31)
        assert first_write(wiki) == ""

    def test_own_marker_is_not_noted(self, tmp_path):
        wiki = make_wiki(tmp_path)
        marker(wiki, "this-session", minutes_ago=1)
        assert first_write(wiki) == ""
