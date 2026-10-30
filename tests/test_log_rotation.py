"""
Tests for session-stop.sh's log rotation keeping the last 30 days in log.md,
so Orient and the briefs' windows still find recent entries after a rotation.
Upstream's TestSessionStop (tests/test_hooks.py) covers the threshold and the
rotation file names.

Run: python3 -m pytest tests/test_log_rotation.py -v
"""

from datetime import date, timedelta

from test_hooks import SESSION_STOP, make_wiki, run_hook, session_end_payload

YEAR = date.today().year


def day(days_ago):
    return (date.today() - timedelta(days=days_ago)).isoformat()


def entries(days_ago, n, label="ingest"):
    return [f"## [{day(days_ago)}] {label} | item-{days_ago}-{i}\n- a line\n" for i in range(n)]


def rotate(wiki, log_entries):
    (wiki / "log.md").write_text("# Wiki Log\n\n" + "\n".join(log_entries))
    result = run_hook(
        SESSION_STOP, session_end_payload(), {"CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki)}
    )
    assert result.returncode == 0
    return (wiki / f"log-{YEAR}.md").read_text(), (wiki / "log.md").read_text(), result.stderr


def test_recent_entries_stay_in_order_and_older_ones_move(tmp_path):
    old, recent = entries(40, 401), entries(29, 50) + entries(0, 50)
    moved, kept, stderr = rotate(make_wiki(tmp_path), old + recent)
    assert moved.count("\n## [") == 401 and day(29) not in moved
    assert kept.startswith(
        f"# Wiki Log\n\nRotated from log.md to log-{YEAR}.md on {day(0)}. "
        f"Entries from {day(29)} on stay here.\n\n## ["
    )
    assert kept.split("\n\n", 2)[2] == "\n".join(recent)
    assert "401 entries moved, 100 kept" in stderr


def test_all_old_entries_move(tmp_path):
    moved, kept, _ = rotate(make_wiki(tmp_path), entries(31, 501))
    assert moved.count("\n## [") == 501
    assert kept == f"# Wiki Log\n\nRotated from log.md to log-{YEAR}.md on {day(0)}.\n"


def test_at_most_250_entries_stay(tmp_path):
    log = entries(1, 501)
    moved, kept, _ = rotate(make_wiki(tmp_path), log)
    assert kept.count("## [") == 250 and kept.endswith(log[-1])
    assert moved.count("\n## [") == 251


def test_a_back_dated_entry_after_the_split_stays(tmp_path):
    log = entries(40, 451) + entries(2, 1) + entries(45, 1, "update") + entries(0, 49)
    _, kept, _ = rotate(make_wiki(tmp_path), log)
    assert f"## [{day(45)}] update" in kept and kept.count("## [") == 51


def test_every_entry_ends_up_in_exactly_one_file(tmp_path):
    log = entries(60, 300) + entries(10, 201)
    moved, kept, _ = rotate(make_wiki(tmp_path), log)
    for entry in log:
        assert (moved + kept).count(entry.splitlines()[0] + "\n") == 1
