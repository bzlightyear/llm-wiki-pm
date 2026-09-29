"""
Smoke tests for hooks/wiki-search.sh, the wiki-search MCP launcher.

Each test runs the launcher the way the plugin manifest does
(`sh wiki-search.sh`), with a temp HOME holding a fake npx cache entry and a
stub `node` that prints $VAULT_PATH and exits. No network and no real MCP.

Run: python3 -m pytest tests/test_wiki_search.py -v
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
WIKI_SEARCH = REPO_ROOT / "hooks" / "wiki-search.sh"

# System tools the launcher needs (cat, tr, dirname, find), without a node
# from a version manager or Homebrew.
SYSTEM_PATH = "/usr/bin:/bin"

OPTION_AND_ENV = {
    "CLAUDE_PLUGIN_OPTION_wiki_path": "/wiki/from-option",
    "WIKI_PATH": "/wiki/from-env",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def launcher_env(
    tmp_path: Path, extra: dict | None = None, stub_node: bool = True
) -> dict:
    """Build the launcher's entire environment.

    Nothing is inherited, so a WIKI_PATH or CLAUDE_PLUGIN_OPTION_wiki_path set
    in the caller's shell can't leak in. HOME holds a fake npx cache entry, so
    the launcher takes its cached-binary path rather than npx (network). With
    stub_node, PATH starts with a `node` that prints $VAULT_PATH and exits.
    """
    home = tmp_path / "home"
    cached = home / ".npm/_npx/x/node_modules/@wirux/mcp-markdown-vault/dist/index.js"
    cached.parent.mkdir(parents=True)
    cached.write_text("")
    path = SYSTEM_PATH
    if stub_node:
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        node = bin_dir / "node"
        node.write_text("#!/bin/sh\nprintf '%s\\n' \"$VAULT_PATH\"\n")
        node.chmod(0o755)
        path = f"{bin_dir}:{path}"
    return {"HOME": str(home), "PATH": path, **(extra or {})}


def run_launcher(cwd: Path, env: dict) -> subprocess.CompletedProcess:
    """Run the launcher as the plugin manifest does: `sh wiki-search.sh`."""
    return subprocess.run(
        ["sh", str(WIKI_SEARCH)],
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd,
    )


def system_node_installed() -> bool:
    """True if node sits where the launcher looks even with a clean HOME and
    PATH (/usr/bin, /bin, /usr/local/bin)."""
    return bool(shutil.which("node", path=SYSTEM_PATH)) or os.access(
        "/usr/local/bin/node", os.X_OK
    )


# ---------------------------------------------------------------------------
# Launcher
# ---------------------------------------------------------------------------


class TestWikiSearchLauncher:
    def test_no_stderr_without_wiki_path_file(self, tmp_path):
        """A missing .wiki-path is the normal case outside a wiki: silent (N13).

        The shell reports a failed `< file` redirection before 2>/dev/null
        applies, so reading the file that way logged "No such file or
        directory" on every such start."""
        project = tmp_path / "project"
        project.mkdir()

        result = run_launcher(project, launcher_env(tmp_path))

        assert result.returncode == 0
        assert result.stderr == ""

    @pytest.mark.parametrize(
        "file_wiki, extra, expected",
        [
            ("  /wiki/from-file \n", OPTION_AND_ENV, "/wiki/from-file"),
            (None, OPTION_AND_ENV, "/wiki/from-option"),
            (None, {"WIKI_PATH": "/wiki/from-env"}, "/wiki/from-env"),
            (None, {}, None),
        ],
        ids=["wiki-path-file", "plugin-option", "wiki-path-env", "cwd"],
    )
    def test_vault_path_precedence(self, tmp_path, file_wiki, extra, expected):
        """.wiki-path > CLAUDE_PLUGIN_OPTION_wiki_path > WIKI_PATH > cwd, as in
        the other hooks. Whitespace in .wiki-path is stripped; expected=None
        means the cwd."""
        project = tmp_path / "project"
        project.mkdir()
        if file_wiki is not None:
            (project / ".wiki-path").write_text(file_wiki)

        result = run_launcher(project, launcher_env(tmp_path, extra))

        assert result.returncode == 0
        assert result.stdout == f"{expected or project.resolve()}\n"

    @pytest.mark.skipif(
        system_node_installed(),
        reason="node is installed where the launcher always looks",
    )
    def test_exit_127_when_node_missing(self, tmp_path):
        """No node on PATH or in any probed location: exit 127 with a message."""
        project = tmp_path / "project"
        project.mkdir()

        result = run_launcher(project, launcher_env(tmp_path, stub_node=False))

        assert result.returncode == 127
        assert "node not found" in result.stderr
