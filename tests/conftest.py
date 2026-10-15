"""
Shared fixtures for the test suite.

The hooks read `$(pwd)/.wiki-path` before CLAUDE_PLUGIN_OPTION_wiki_path, and
some tests in test_hooks.py start them without cwd=, so they inherit pytest's
working directory. Run from a checkout whose .wiki-path points at a real wiki,
those hooks would use that wiki instead of the test's temp wiki. When neither
is set, the hooks fall back to WIKI_PATH, which a developer may also have
pointed at a real wiki.

The write hooks keep per-session markers in the temp folder, and pre-write.sh
reports other sessions' recent markers. TMPDIR points the hooks at the test's
own temp directory, so a test run neither reads a real session's markers nor
leaves one that a real session would report.
"""

import pytest


@pytest.fixture(autouse=True)
def isolated_wiki_path(tmp_path, monkeypatch):
    """Run every test from its own temp directory, with WIKI_PATH unset and
    TMPDIR set to it."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("WIKI_PATH", raising=False)
    monkeypatch.setenv("TMPDIR", str(tmp_path))
