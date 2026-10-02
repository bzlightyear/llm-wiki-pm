"""
How session-start.sh picks the wiki: WIKI_PATH is the default, and a project's
.wiki-path overrides it. A session using the default wiki gets no warning.

Run: python3 -m pytest tests/test_session_start_wiki_path.py -v
"""

from __future__ import annotations

import json

from test_hooks import SESSION_START, make_wiki, run_hook, session_start_payload


def start_session(project, wiki_path: str) -> dict:
    result = run_hook(
        SESSION_START,
        session_start_payload(),
        {"WIKI_PATH": wiki_path, "_CWD": str(project)},
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def context(output: dict) -> str:
    return output["hookSpecificOutput"]["additionalContext"]


def test_wiki_path_default_has_no_warning(tmp_path):
    """No .wiki-path: the session uses WIKI_PATH and shows no warning."""
    wiki = make_wiki(tmp_path)
    project = tmp_path / "project"
    project.mkdir()

    output = start_session(project, str(wiki))

    assert f"Wiki at {wiki}." in context(output)
    assert "systemMessage" not in output
    assert "set-wiki-path" not in context(output)


def test_wiki_path_file_overrides_default(tmp_path):
    """A project's .wiki-path names another wiki, and the session uses it."""
    default = make_wiki(tmp_path)
    other_root = tmp_path / "other"
    other_root.mkdir()
    other = make_wiki(other_root)
    project = tmp_path / "project"
    project.mkdir()
    (project / ".wiki-path").write_text(f"{other}\n")

    output = start_session(project, str(default))

    assert f"Wiki at {other}." in context(output)
    assert str(default) not in context(output)
    assert "systemMessage" not in output
