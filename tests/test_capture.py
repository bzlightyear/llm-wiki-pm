"""
Tests for skills/llm-wiki-pm/scripts/capture.py, which saves a fact stated in
conversation as a write-once raw/ record (references/citation-spec.md,
"Conversational facts").

Run: python3 -m pytest tests/test_capture.py -v
"""

import subprocess
import sys
from datetime import date

from test_hooks import REPO_ROOT, make_wiki

SCRIPTS = REPO_ROOT / "skills" / "llm-wiki-pm" / "scripts"
CAPTURE = SCRIPTS / "capture.py"

sys.path.insert(0, str(SCRIPTS))
import lint  # noqa: E402
import wikifm  # noqa: E402

TODAY = date.today().isoformat()


def run_capture(wiki, *args, stdin="The team chose usage-based billing.\n"):
    return subprocess.run(
        [sys.executable, str(CAPTURE), str(wiki), *args],
        input=stdin, capture_output=True, text=True,
    )


def output(result):
    """The printed path and ID, as a dict."""
    return dict(line.split(": ", 1) for line in result.stdout.splitlines())


def records(wiki):
    return sorted(p.name for p in (wiki / "raw" / "internal").glob("*.md"))


def test_writes_a_record_and_prints_its_path_and_id(tmp_path):
    wiki = make_wiki(tmp_path)
    result = run_capture(wiki, "--topic", "pricing-tier")
    assert result.returncode == 0, result.stderr
    rid = f"conversation-{TODAY}-pricing-tier"
    assert output(result) == {"path": f"raw/internal/{rid}.md", "id": rid}

    path = wiki / "raw" / "internal" / f"{rid}.md"
    assert lint.slug(path) == rid
    text = path.read_text()
    fields, errors = wikifm.parse(text)
    assert errors == []
    assert fields == {
        "title": f"Conversation {TODAY}: pricing-tier",
        "source_type": "conversation",
        "captured": TODAY,
        "stated_by": "user",
    }
    assert f"captured: '{TODAY}'\n" in text  # the canonical date form
    assert text.endswith("---\n\nThe team chose usage-based billing.\n")


def test_the_statement_is_kept_as_written(tmp_path):
    wiki = make_wiki(tmp_path)
    statement = "First line.\n\n---\n\n- a list: with a colon\n"
    result = run_capture(wiki, "--topic", "notes", stdin=statement)
    assert result.returncode == 0, result.stderr
    text = (wiki / output(result)["path"]).read_text()
    fields, errors = wikifm.parse(text)
    assert errors == [] and fields["source_type"] == "conversation"
    assert text.endswith("---\n\n" + statement)


def test_a_repeated_topic_gets_the_next_free_suffix(tmp_path):
    wiki = make_wiki(tmp_path)
    ids = []
    for n in range(3):
        result = run_capture(wiki, "--topic", "pricing-tier", stdin=f"statement {n}\n")
        assert result.returncode == 0, result.stderr
        ids.append(output(result)["id"])
    base = f"conversation-{TODAY}-pricing-tier"
    assert ids == [base, f"{base}-2", f"{base}-3"]
    # Nothing was overwritten: each record still holds its own statement.
    for n, rid in enumerate(ids):
        text = (wiki / "raw" / "internal" / f"{rid}.md").read_text()
        assert text.endswith(f"statement {n}\n")


def test_skips_an_id_held_by_a_record_in_another_folder(tmp_path):
    wiki = make_wiki(tmp_path)
    base = f"conversation-{TODAY}-pricing-tier"
    (wiki / "raw" / "articles" / f"{base}.md").write_text("x\n")
    result = run_capture(wiki, "--topic", "pricing-tier")
    assert output(result)["id"] == f"{base}-2"


def test_skips_an_id_held_by_a_page_slug(tmp_path):
    wiki = make_wiki(tmp_path)
    base = f"conversation-{TODAY}-pricing-tier"
    page = wiki / "queries" / base / "README.md"  # a directory page's slug
    page.parent.mkdir()
    page.write_text("---\ntitle: t\n---\n")
    result = run_capture(wiki, "--topic", "pricing-tier")
    assert output(result)["id"] == f"{base}-2"


def test_stated_by_a_person(tmp_path):
    wiki = make_wiki(tmp_path)
    result = run_capture(wiki, "--topic", "roadmap", "--stated-by", "person-a")
    assert result.returncode == 0, result.stderr
    fields, _ = wikifm.parse((wiki / output(result)["path"]).read_text())
    assert fields["stated_by"] == "person-a"


def test_creates_raw_internal_when_missing(tmp_path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    result = run_capture(wiki, "--topic", "pricing-tier")
    assert result.returncode == 0, result.stderr
    assert records(wiki) == [f"conversation-{TODAY}-pricing-tier.md"]


def test_rejects_a_topic_outside_the_id_grammar(tmp_path):
    wiki = make_wiki(tmp_path)
    for topic in ("Pricing", "pricing tier", "-pricing", "a/b", "a,b", ""):
        result = run_capture(wiki, "--topic", topic)
        assert result.returncode != 0, topic
        assert "--topic" in result.stderr, topic
    assert records(wiki) == []


def test_rejects_a_stated_by_outside_the_id_grammar(tmp_path):
    wiki = make_wiki(tmp_path)
    result = run_capture(wiki, "--topic", "roadmap", "--stated-by", "Person A")
    assert result.returncode != 0
    assert "--stated-by" in result.stderr
    assert records(wiki) == []


def test_rejects_an_empty_statement(tmp_path):
    wiki = make_wiki(tmp_path)
    result = run_capture(wiki, "--topic", "roadmap", stdin=" \n\n")
    assert result.returncode != 0
    assert "no statement" in result.stderr
    assert records(wiki) == []


def test_rejects_a_missing_wiki(tmp_path):
    result = run_capture(tmp_path / "nowhere", "--topic", "roadmap")
    assert result.returncode != 0
    assert "not a directory" in result.stderr
    assert not (tmp_path / "nowhere").exists()
