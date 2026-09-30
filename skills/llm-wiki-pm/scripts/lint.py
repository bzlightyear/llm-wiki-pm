#!/usr/bin/env python3
"""Tiered lint for PM wiki. Writes report to queries/lint-YYYY-MM-DD.md.

Usage:
    lint.py <wiki_path>              # report only
    lint.py <wiki_path> --auto-fix   # report + repair safe issues
    lint.py <wiki_path> --cited-sources <page>   # paths for a page's sources:
"""

import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True  # don't leave __pycache__ in the plugin dir
import wikifm  # noqa: E402  (the frontmatter parser, beside this script)

REQUIRED_FRONTMATTER = {"title", "created", "updated", "type", "tags", "sources"}
WIKI_DIRS = ["entities", "concepts", "comparisons", "queries"]
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
FRONTMATTER_RE = wikifm.FRONTMATTER_RE
TAXONOMY_TAG_RE = re.compile(r"^- `([a-z0-9\-]+)`", re.MULTILINE)
INLINE_PROVENANCE_RE = re.compile(r"\[source:", re.IGNORECASE)
SOURCE_MARKER_RE = re.compile(r"\[source:\s*([^\]]*)\]", re.IGNORECASE)

# Interim workaround for the recurring wiki-search MCP bug that re-escapes
# `[` -> `\[` on write (wikilinks, `## [date]` log headers), until the
# upstream fix lands (wirux/mcp-markdown-vault#47). Matches inside fenced
# ```code blocks``` are skipped (see _fenced_ranges) — those are quoted
# source that may legitimately contain literal `\[`, e.g. a page documenting
# a diff.
ESCAPED_BRACKET_RE = re.compile(r"\\\[")

FENCE_LINE_RE = re.compile(r"^\s*```")
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


def _fenced_ranges(text):
    """Char-offset (start, end) ranges covering fenced ```...``` blocks
    (fence lines included). Content inside is quoted source, not prose."""
    ranges = []
    offset = 0
    fence_start = None
    for line in text.splitlines(keepends=True):
        if FENCE_LINE_RE.match(line):
            if fence_start is None:
                fence_start = offset
            else:
                ranges.append((fence_start, offset + len(line)))
                fence_start = None
        offset += len(line)
    return ranges


def _inline_code_ranges(text, fenced):
    """Char-offset ranges covering single-backtick inline code spans, e.g.
    `\\[`. Spans already inside a fenced block are skipped so fence
    delimiters aren't double-matched."""
    ranges = []
    for m in INLINE_CODE_RE.finditer(text):
        if any(start <= m.start() < end for start, end in fenced):
            continue
        ranges.append((m.start(), m.end()))
    return ranges


def find_escaped_brackets(rel_path, text, auto_fix):
    """Detect/repair escaped-bracket corruption. Returns (text, note-or-None).
    Ignores matches inside fenced code blocks and inline `code spans` —
    quoted source may legitimately contain a literal '\\['."""
    fenced = _fenced_ranges(text)
    protected = fenced + _inline_code_ranges(text, fenced)
    matches = [
        m for m in ESCAPED_BRACKET_RE.finditer(text)
        if not any(start <= m.start() < end for start, end in protected)
    ]
    count = len(matches)
    if not count:
        return text, None
    if auto_fix:
        new_text = text
        for m in reversed(matches):
            new_text = new_text[: m.start()] + "[" + new_text[m.end() :]
        return (
            new_text,
            f"de-escaped {count} corrupted '\\[' -> '[' in {rel_path}",
        )
    return text, (
        f"{count} escaped bracket(s) (\\[ -> [ corruption): {rel_path} — "
        f"run lint --auto-fix"
    )

# Grounding / freshness (anti-self-reinforcement). A wiki that only cites its own
# pages drifts from reality. Sources pointing back into these dirs are secondhand;
# a knowledge page needs at least one PRIMARY source (raw/, external/, web,
# conversation, slack, gmail, granola, etc.).
WIKI_PAGE_PREFIXES = ("entities/", "concepts/", "comparisons/", "queries/")
# Factual pages must be grounded in a primary source (🔴 if self-referential).
# Synthesis pages legitimately summarize other wiki pages (🟡 only).
FACTUAL_TYPES = {"entity", "concept", "comparison", "persona"}
# Structural / generated pages are exempt from grounding (they carry no world-claims).
GROUNDING_EXEMPT_STEMS = {"index", "log", "_status", "SCHEMA", "MY-INTEGRATIONS", "overview"}
LAST_VERIFIED_STALE_DAYS = 120


def _days_since(d):
    """Whole days from midnight UTC on date `d` to now."""
    midnight = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - midnight).days


def load_taxonomy(schema_path):
    if not schema_path.exists():
        return set()
    return set(TAXONOMY_TAG_RE.findall(schema_path.read_text()))


def slug(path):
    if path.name == "README.md":
        return path.parent.name
    return path.stem


def snapshot(page, wiki):
    """Copy `page` to _archive/<slug>-<YYYY-MM-DD>.md before it changes.
    At most one snapshot per page per day: an existing snapshot is kept.
    Shared by pre-write.sh, lint --auto-fix and the migration, so backups are
    named one way everywhere. Returns the snapshot path."""
    page, wiki = Path(page), Path(wiki)
    arc = wiki / "_archive" / f"{slug(page)}-{date.today().isoformat()}.md"
    if not arc.exists():
        arc.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(page, arc)
    return arc


def wiki_pages(wiki):
    """Lint's page set: every .md file under WIKI_DIRS except lint reports."""
    pages = []
    for d in WIKI_DIRS:
        for p in (wiki / d).rglob("*.md"):
            # skip lint reports — self-generated, would cause false positives
            if p.name.startswith("lint-"):
                continue
            pages.append(p)
    return pages


def is_shareable(fm):
    # Private-by-default: a page is in the export set only if it opts in.
    return wikifm.str_field(fm, "shareable").lower() in ("true", "yes")


_LINK_BULLET = re.compile(r"^\s*-\s*\[\[([^\]]+)\]\]")


def merge_sort_index(idx_text, additions):
    """Rebuild index.md so each `## ` section's `- [[slug]]` bullet run is
    alpha-sorted, backfilling any missing slugs from `additions`
    (header-line -> set of slugs). Non-bullet lines (sub-headers, comments,
    prose) keep their position; the sorted bullet block is placed where the
    section's first link bullet was, or right after the header if the section
    had none. Returns (new_text, changed: bool)."""
    lines = idx_text.split("\n")
    # locate section header line indices
    headers = [i for i, ln in enumerate(lines) if ln.startswith("## ")]
    bounds = []
    for n, h in enumerate(headers):
        end = headers[n + 1] if n + 1 < len(headers) else len(lines)
        bounds.append((lines[h].rstrip(), h, end))

    out = list(lines)
    changed = False
    # process bottom-up so earlier indices stay valid as we splice
    for header_text, start, end in reversed(bounds):
        body = list(range(start + 1, end))
        bullets = [(i, _LINK_BULLET.match(lines[i]).group(1)) for i in body
                   if _LINK_BULLET.match(lines[i])]
        if not bullets and header_text not in additions:
            continue
        existing = [b[1] for b in bullets]
        merged = sorted(set(existing) | additions.get(header_text, set()),
                        key=str.lower)
        new_bullets = [f"- [[{s}]]" for s in merged]
        if new_bullets == [lines[i] for i, _ in bullets]:
            continue  # already sorted, nothing to add
        changed = True
        bullet_idx = [i for i, _ in bullets]
        insert_at = bullet_idx[0] if bullet_idx else start + 1
        # drop old bullet lines (descending so indices stay valid)
        for i in sorted(bullet_idx, reverse=True):
            del out[i]
            if i < insert_at:
                insert_at -= 1
        out[insert_at:insert_at] = new_bullets
    return "\n".join(out), changed


def get_superseded_by(fm):
    v = wikifm.str_field(fm, "superseded_by")
    if v in ("", "null", "none", "~"):
        return None
    return v


# ── Frontmatter validity + provenance cross-reference ──
# Rationale and evidence: fork-chgs/lint-frontmatter-checks-design.md.
# wikifm.parse() reads frontmatter by its profile and reports what falls
# outside it, where the old line-partitioning parser silently discarded keys
# (a wiki-wide yaml.safe_load once found 23 unreadable pages while lint
# reported 0 errors). R1/R2 are the two structural corruption patterns found
# in the wiki; R5 is duplicate keys, which yaml.safe_load itself does NOT
# raise on (last-wins).


def check_frontmatter_structure(rel_path, fm_block_text):
    """R1/R2/R5 structural frontmatter errors, as wikifm reports them. Takes
    the raw text between the --- fences; returns a list of 🔴 error strings.
    wikifm also reports the rest of the profile (R12), which lint doesn't
    report yet."""
    _, fm_errors = wikifm.parse_block(fm_block_text)
    # R1 — a key's value may not begin with a list-item dash
    errors = [
        f"malformed frontmatter — block list item on key line '{e.key}:' (R1): {rel_path}"
        for e in fm_errors if e.rule == "R1"
    ]
    # R2 — a closed flow list leaves nothing for an indented item to join
    orphan_count = sum(1 for e in fm_errors if e.rule == "R2")
    if orphan_count:
        errors.append(
            f"malformed frontmatter — {orphan_count} orphan block list item(s) "
            f"under a closed flow list, unreachable by any parser (R2): {rel_path}"
        )
    for key, n in Counter(e.key for e in fm_errors if e.rule == "R5").items():
        errors.append(
            f"duplicate frontmatter key '{key}' (x{n + 1}, last wins — earlier "
            f"value silently discarded) (R5): {rel_path}"
        )
    return errors


def _inline_citations(body):
    """Raw citation strings from every `[source: ...]` marker, split on ';' so
    multi-source markers yield one entry per source."""
    citations = []
    for m in SOURCE_MARKER_RE.finditer(body):
        for part in m.group(1).split(";"):
            part = part.strip()
            # a marker containing a wikilink ("...; see [[page]]") is truncated
            # at the link's own bracket — prose, not a source identifier
            if part and "[[" not in part:
                citations.append(part)
    return citations


def _is_conversation_citation(citation):
    """`user, conversation (X), DATE` style markers carry their own commas and
    parentheses; resolving them against a sources: entry is not reliable, so
    they are never counted as dangling."""
    return bool(re.match(r"^(user|conversation)\b", citation, re.IGNORECASE))


def _citation_matches_source(citation, source):
    """Deliberately permissive: the marker grammar is loose (bare slug, slug +
    section name, qualified raw/ path), and a false 'dangling' report is worse
    than a miss."""
    c, s = citation.lower(), source.lower()
    if c in s or s in c:
        return True
    candidate = c.split(",")[0].strip()
    return bool(candidate) and candidate in s


def check_provenance_cross_reference(rel_path, text, sources):
    """R3 (inline marker resolving to no frontmatter source) and R4 (bulk
    uncited sources). Returns {"info": [...], "warnings": [...]}.

    R3 reports 🔵 info, never 🔴: the marker grammar is loose enough that a
    strict tier would produce false positives and be tuned out. Frontmatter
    sources: legitimately lists more than the body cites (ingest-guide ⑤), so
    R4 is a ratio check, not set equality."""
    notes = {"info": [], "warnings": []}
    fm_m = FRONTMATTER_RE.match(text)
    body = text[fm_m.end():] if fm_m else text
    citations = _inline_citations(body)
    if not citations:
        return notes

    unresolved = sum(
        1
        for c in citations
        if not _is_conversation_citation(c)
        and not any(_citation_matches_source(c, s) for s in sources)
    )
    if unresolved:
        notes["info"].append(
            f"{unresolved} inline [source:] marker(s) resolve to no frontmatter "
            f"sources: entry (R3): {rel_path}"
        )

    # Only meaningful once a list is long enough for a ratio to mean something;
    # a page citing 3 of 22 sources is the copy-paste signature this catches.
    if len(sources) >= 5:
        cited = sum(
            1 for s in sources if any(_citation_matches_source(c, s) for c in citations)
        )
        if cited / len(sources) < 0.5:
            notes["warnings"].append(
                f"only {cited}/{len(sources)} frontmatter sources cited inline "
                f"(R4) — check for a copy-pasted sources: list: {rel_path}"
            )
    return notes


# ── --cited-sources: the split procedure's helper ──
# references/citation-spec.md, "Page lifecycle": a split child's sources: is
# set to the paths of exactly the IDs its body cites.


def cited_sources(wiki, page):
    """Resolve the IDs `page` cites against every raw/ record and wiki page,
    not against the page's own sources:, since a new split child declares
    nothing yet. An ID is the text of a citation before its first comma.
    Returns (paths, unresolved, ambiguous): the path of each cited ID in the
    order first cited, the IDs that match no file, and {ID: paths} for IDs
    that match more than one."""
    files = defaultdict(list)
    raw = wiki / "raw"
    for p in raw.rglob("*.md"):
        if raw / "assets" not in p.parents:
            files[p.stem].append(p)
    for p in wiki_pages(wiki):
        files[slug(p)].append(p)

    text = page.read_text()
    fm_m = FRONTMATTER_RE.match(text)
    body = text[fm_m.end():] if fm_m else text
    paths, unresolved, ambiguous = [], [], {}
    for citation in _inline_citations(body):
        cid = " ".join(citation.split(",")[0].split())  # a wrapped ID shows its break
        matches = files.get(cid, [])
        if len(matches) > 1:
            ambiguous[cid] = sorted(matches)
        elif matches and matches[0] not in paths:
            paths.append(matches[0])
        elif not matches and cid not in unresolved:
            unresolved.append(cid)
    return paths, unresolved, ambiguous


def print_cited_sources(wiki, page_arg):
    """Print `sources:` for the page, then any IDs that don't resolve to
    exactly one file. Writes nothing. Returns the exit status: 0 when every
    ID resolves, 1 when some don't, 2 when the page doesn't exist."""
    page = Path(page_arg).expanduser()
    if not page.is_absolute() and (wiki / page).is_file():
        page = wiki / page
    if not page.is_file():
        print(f"error: {page_arg} is not a file", file=sys.stderr)
        return 2
    paths, unresolved, ambiguous = cited_sources(wiki, page)
    if paths:
        print("sources:")
        print("\n".join(f"  - {p.relative_to(wiki).as_posix()}" for p in paths))
    else:
        print("sources: []")
    if unresolved:
        print("unresolved:")
        print("\n".join(f"  - {cid}" for cid in unresolved))
    if ambiguous:
        print("ambiguous:")
        for cid, matches in ambiguous.items():
            print(f"  - {cid}: " + ", ".join(p.relative_to(wiki).as_posix() for p in matches))
    return 1 if unresolved or ambiguous else 0


def main():
    args = sys.argv[1:]
    usage = "usage: lint.py <wiki_path> [--auto-fix] | <wiki_path> --cited-sources <page>"
    if not args:
        print(usage, file=sys.stderr)
        sys.exit(1)
    cited_page = None
    if "--cited-sources" in args:
        i = args.index("--cited-sources")
        if i + 1 == len(args):
            print(usage, file=sys.stderr)
            sys.exit(1)
        cited_page = args.pop(i + 1)
    auto_fix = "--auto-fix" in args
    output_json = "--json" in args
    quiet = "--quiet" in args
    args = [a for a in args if not a.startswith("--")]
    wiki = Path(args[0]).expanduser().resolve()
    if not wiki.exists():
        print(f"error: {wiki} does not exist", file=sys.stderr)
        sys.exit(2)

    if cited_page is not None:
        sys.exit(print_cited_sources(wiki, cited_page))

    today = date.today().isoformat()
    pages = wiki_pages(wiki)

    slugs = {slug(p): p for p in pages}
    # root-level architecture singletons (overview.md, index.md) are valid
    # [[wikilink]] targets but live outside WIKI_DIRS — don't run them through
    # the full page pipeline (frontmatter/tag/orphan/index checks), just make
    # links to them resolve.
    for root_name in ("overview.md", "index.md"):
        root_p = wiki / root_name
        if root_p.exists():
            slugs.setdefault(slug(root_p), root_p)
    taxonomy = load_taxonomy(wiki / "SCHEMA.md")

    errors, warnings, info = [], [], []
    orphans_list = []
    fixes_applied = []

    inbound = defaultdict(set)
    broken = []
    tag_usage = Counter()
    superseded_pages = set()
    supersede_map = {}  # old-slug -> new-slug
    intentional_stubs = set()  # lifecycle: stub-intentional — exempt from orphan nag
    shareable_pages = []  # export allowlist (private-by-default model)

    # escaped-bracket corruption also hits root-level singletons (log.md,
    # overview.md, index.md, MY-INTEGRATIONS.md), which sit outside WIKI_DIRS
    # and never pass through the per-page loop below.
    for root_name in ("log.md", "overview.md", "index.md", "MY-INTEGRATIONS.md"):
        root_p = wiki / root_name
        if not root_p.exists():
            continue
        root_text = root_p.read_text()
        fixed_root_text, root_note = find_escaped_brackets(
            root_name, root_text, auto_fix
        )
        if root_note:
            (fixes_applied if auto_fix else errors).append(root_note)
            if auto_fix:
                root_p.write_text(fixed_root_text)

    for p in pages:
        text = p.read_text()
        text, escape_note = find_escaped_brackets(p.relative_to(wiki), text, auto_fix)
        if escape_note:
            (fixes_applied if auto_fix else errors).append(escape_note)
            if auto_fix:
                p.write_text(text)
        fm, _ = wikifm.parse(text)

        if fm is None:
            errors.append(f"missing frontmatter: {p.relative_to(wiki)}")
            continue
        fm_block_m = FRONTMATTER_RE.match(text)
        if fm_block_m:
            errors.extend(
                check_frontmatter_structure(p.relative_to(wiki), fm_block_m.group(1))
            )

        missing = REQUIRED_FRONTMATTER - set(fm.keys())
        if missing:
            errors.append(
                f"frontmatter missing {sorted(missing)}: {p.relative_to(wiki)}"
            )

        # supersession tracking
        sb = get_superseded_by(fm)
        if sb:
            superseded_pages.add(slug(p))
            supersede_map[slug(p)] = sb
            if sb not in slugs:
                errors.append(
                    f"superseded_by points to unknown page '{sb}': {p.relative_to(wiki)}"
                )

        # orphan-by-design pages, exempt from the orphan warning so health
        # metrics don't punish correct behavior:
        #   stub-intentional — thin pages awaiting signal (fresh warehouse/
        #                      account/escalation stubs)
        #   dated-digest     — one-shot dated pages (daily briefs, synthesis
        #                      digests) that never earn inbound links by design
        if wikifm.str_field(fm, "lifecycle") in ("stub-intentional", "dated-digest"):
            intentional_stubs.add(slug(p))

        # export allowlist audit (private-by-default): surface what would leave
        # the wiki on an export, so the shareable set stays reviewable.
        if is_shareable(fm):
            shareable_pages.append(str(p.relative_to(wiki)))

        # tags
        tags = wikifm.list_field(fm, "tags")
        for t in tags:
            tag_usage[t] += 1
            if taxonomy and t not in taxonomy:
                errors.append(
                    f"tag '{t}' not in SCHEMA.md taxonomy: {p.relative_to(wiki)}"
                )

        # ── grounding / freshness (anti-self-reinforcement) ──
        stem = p.stem
        if not stem.startswith("lint-") and stem not in GROUNDING_EXEMPT_STEMS:
            ptype = wikifm.str_field(fm, "type")
            srcs = wikifm.sources(fm)
            primary_srcs = [s for s in srcs if not s.startswith(WIKI_PAGE_PREFIXES)]
            wiki_srcs = [s for s in srcs if s.startswith(WIKI_PAGE_PREFIXES)]
            # self-referential: every source points back into the wiki, none primary
            if srcs and not primary_srcs and wiki_srcs:
                msg = (
                    f"self-referential sources (no primary source, only wiki pages): "
                    f"{p.relative_to(wiki)} — verify against live tools, add a raw/ source"
                )
                # 🔴 for factual pages AND for decision-bearing syntheses (a
                # decision/strategy artifact laundered from wiki prose is the exact
                # failure mode we guard against). Ordinary digests stay 🟡.
                decision_bearing = any(t in ("decision", "strategy") for t in tags)
                is_error = ptype in FACTUAL_TYPES or decision_bearing
                (errors if is_error else warnings).append(msg)
            # provenance cross-reference (R3 dangling marker, R4 bulk uncited)
            prov = check_provenance_cross_reference(p.relative_to(wiki), text, srcs)
            info.extend(prov["info"])
            warnings.extend(prov["warnings"])
            # factual page with body but no inline provenance markers
            fm_m = FRONTMATTER_RE.match(text)
            body = text[fm_m.end():] if fm_m else text
            if (
                ptype in FACTUAL_TYPES
                and body.count("\n") > 15
                and not INLINE_PROVENANCE_RE.search(body)
            ):
                warnings.append(
                    f"no inline [source:] provenance markers: {p.relative_to(wiki)}"
                )
            # provenance gone stale — re-check against live sources
            lv = wikifm.date_field(fm, "last_verified")
            lv_age = _days_since(lv) if lv else 0
            if lv_age > LAST_VERIFIED_STALE_DAYS:
                warnings.append(
                    f"provenance unverified for {lv_age}d (last_verified {lv}): "
                    f"{p.relative_to(wiki)} — re-check live sources"
                )
            # coverage marker (deterministic replacement for the prose "set
            # coverage:/gaps: on every entity/concept page" rule). Warn only —
            # pre-existing wikis predate the field.
            if ptype in FACTUAL_TYPES:
                coverage = wikifm.str_field(fm, "coverage")
                if not coverage:
                    warnings.append(
                        f"no coverage: marker (stub/partial/comprehensive): "
                        f"{p.relative_to(wiki)}"
                    )

        # wikilinks
        for link in WIKILINK_RE.findall(text):
            target = link.strip()
            if target in slugs and slugs[target] != p:
                inbound[target].add(slug(p))
            elif target not in slugs:
                broken.append((p, target))

        # page size
        lines = text.count("\n")
        if lines > 200:
            warnings.append(
                f"page > 200 lines ({lines}): {p.relative_to(wiki)} — split candidate"
            )

        # contradictions flagged
        if "contradictions:" in text and not re.search(
            r"contradictions:\s*\[\s*\]", text
        ):
            warnings.append(f"unresolved contradictions flag: {p.relative_to(wiki)}")

        # stale
        updated = wikifm.date_field(fm, "updated")
        age_days = _days_since(updated) if updated else 0
        if age_days > 90:
            warnings.append(
                f"stale ({age_days}d since update): {p.relative_to(wiki)}"
            )

    # broken links → auto-fix if possible
    for p, target in broken:
        if auto_fix and target in supersede_map:
            new_target = supersede_map[target]
            t = p.read_text()
            t2 = re.sub(
                rf"\[\[{re.escape(target)}(\|[^\]]+)?\]\]",
                f"[[{new_target}]]",
                t,
            )
            if t2 != t:
                p.write_text(t2)
                fixes_applied.append(
                    f"rewrote broken [[{target}]] → [[{new_target}]] in {p.relative_to(wiki)}"
                )
                continue
        errors.append(f"broken [[{target}]] in {p.relative_to(wiki)}")

    # redirect links pointing to superseded pages (even if not broken)
    if auto_fix and supersede_map:
        for p in pages:
            if slug(p) in superseded_pages:
                continue  # don't rewrite the archive-bound old page itself
            text = p.read_text()
            new_text = text
            for old, new in supersede_map.items():
                new_text = re.sub(
                    rf"\[\[{re.escape(old)}(\|[^\]]+)?\]\]",
                    f"[[{new}]]",
                    new_text,
                )
            if new_text != text:
                p.write_text(new_text)
                fixes_applied.append(
                    f"redirected superseded links in {p.relative_to(wiki)}"
                )

    # orphans (superseded pages are allowed to be orphans; intentional stubs too)
    intentional_stub_orphans = 0
    for p in pages:
        s = slug(p)
        if s in superseded_pages:
            continue
        if s not in inbound:
            if s in intentional_stubs:
                intentional_stub_orphans += 1
                continue
            warnings.append(f"orphan (zero inbound links): {p.relative_to(wiki)}")
            orphans_list.append(str(p.relative_to(wiki)))
    if intentional_stub_orphans:
        info.append(
            f"{intentional_stub_orphans} page(s) exempt from orphan check "
            f"(lifecycle: stub-intentional / dated-digest)"
        )
    if shareable_pages:
        info.append(
            f"export surface: {len(shareable_pages)} shareable page(s) (all others "
            f"private by default) — review before any export: "
            + ", ".join(sorted(shareable_pages))
        )

    # index completeness → auto-fix by appending missing entries
    idx_path = wiki / "index.md"
    missing_in_index = []
    if idx_path.exists():
        idx_text = idx_path.read_text()
        for p in pages:
            s = slug(p)
            if s in superseded_pages:
                continue
            if f"[[{s}]]" not in idx_text and s not in idx_text:
                missing_in_index.append(p)
                warnings.append(f"not in index.md: {p.relative_to(wiki)}")

        # map missing pages to their target section header
        section_map = {
            "entity": "## Entities",
            "concept": "## Concepts",
            "comparison": "## Comparisons",
            "query": "## Queries",
            "summary": "## Entities",
        }
        additions = defaultdict(set)
        for p in missing_in_index:
            fm, _ = wikifm.parse(p.read_text())
            t = wikifm.str_field(fm, "type") or "entity"
            additions[section_map.get(t, "## Entities")].add(slug(p))

        # detect/repair section drift: bullets out of alpha order or missing
        new_idx, changed = merge_sort_index(idx_text, additions)
        if changed:
            if auto_fix:
                idx_path.write_text(new_idx)
                note = "alpha-sorted index.md sections"
                if missing_in_index:
                    note += f" (+{len(missing_in_index)} missing entries)"
                fixes_applied.append(note)
            else:
                warnings.append(
                    "index.md sections need sorting/backfill — run lint --auto-fix"
                )

    # log rotation
    log_path = wiki / "log.md"
    if log_path.exists():
        entries = log_path.read_text().count("\n## [")
        if entries > 500:
            info.append(f"log.md has {entries} entries — rotate to log-YYYY.md")

    # tag frequency
    for t, n in tag_usage.most_common(10):
        info.append(f"tag '{t}': {n} uses")
    rare = [t for t, n in tag_usage.items() if n == 1]
    if rare:
        info.append(f"singleton tags (consolidate?): {', '.join(sorted(rare))}")

    # report
    report_dir = wiki / "queries"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"lint-{today}.md"

    out = [
        "---",
        f"title: Lint Report {today}",
        f"created: {today}",
        f"updated: {today}",
        "type: query",
        "tags: [question]",
        "sources: []",
        "---",
        "",
        f"# Lint Report — {today}",
        "",
        f"Pages scanned: {len(pages)} | Errors: {len(errors)} | "
        f"Warnings: {len(warnings)} | Info: {len(info)}",
        f"Auto-fix: {'ON' if auto_fix else 'off'} | Fixes applied: {len(fixes_applied)}",
        "",
        f"## 🔴 Errors ({len(errors)})",
        "",
    ]
    out += [f"- {e}" for e in errors] or ["- none"]
    out += ["", f"## 🟡 Warnings ({len(warnings)})", ""]
    out += [f"- {w}" for w in warnings] or ["- none"]
    out += ["", f"## 🔵 Info ({len(info)})", ""]
    out += [f"- {i}" for i in info] or ["- none"]
    if fixes_applied:
        out += ["", f"## 🔧 Auto-fixes Applied ({len(fixes_applied)})", ""]
        out += [f"- {f}" for f in fixes_applied]
    out += ["", "## Suggested Actions", ""]
    if errors:
        out.append(
            "1. Fix 🔴 errors — broken links and missing frontmatter block navigation."
        )
    if warnings:
        out.append("2. Triage 🟡 warnings — orphans may need backlinks or archival.")
    if info:
        out.append("3. Note 🔵 info for quarterly taxonomy review.")

    report_path.write_text("\n".join(out) + "\n")

    # Output structured JSON when requested (used by hooks for health checks).
    # Using --json implies no prose on stdout.
    if output_json:
        import json

        broken_list = [e for e in errors if e.startswith("broken [[")]
        print(
            json.dumps(
                {
                    "broken_links": broken_list,
                    "orphans": orphans_list,
                    "errors": len(errors),
                    "warnings": len(warnings),
                }
            )
        )
        return
    if log_path.exists():
        with log_path.open("a") as f:
            f.write(
                f"\n## [{today}] lint | {len(errors)}E {len(warnings)}W "
                f"{len(info)}I {len(fixes_applied)}F\n"
            )
            f.write(f"- Report: queries/lint-{today}.md\n")
            if auto_fix:
                f.write(f"- Auto-fix applied {len(fixes_applied)} repairs\n")

    if not quiet:
        print(f"ok: {report_path.relative_to(wiki)}")
        print(
            f"  🔴 {len(errors)}  🟡 {len(warnings)}  🔵 {len(info)}  "
            f"🔧 {len(fixes_applied)}"
        )


if __name__ == "__main__":
    main()
