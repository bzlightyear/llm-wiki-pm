"""
Shared fixtures for the test suite.

The hooks read `$(pwd)/.wiki-path` before CLAUDE_PLUGIN_OPTION_wiki_path, and
some tests in test_hooks.py start them without cwd=, so they inherit pytest's
working directory. Run from a checkout whose .wiki-path points at a real wiki,
those hooks would use that wiki instead of the test's temp wiki. When neither
is set, the hooks fall back to WIKI_PATH, which a developer may also have
pointed at a real wiki.
"""

import pytest


@pytest.fixture(autouse=True)
def isolated_wiki_path(tmp_path, monkeypatch):
    """Run every test from its own temp directory, with WIKI_PATH unset."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("WIKI_PATH", raising=False)
