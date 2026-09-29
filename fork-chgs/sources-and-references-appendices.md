# Sources and References Appendices

created: 2026-09-28

Plain-language explanations of the design's seven root causes (RC1–RC7) and
fifteen new findings (N1–N15): what each is, what it costs, and how the plan fixes
it.

revised on: 2026-09-29
Narrowed N12 to the names of people and customer companies, in one doc and the
test file, to match the design's narrowed step 0 scrub.

Companion to [Sources and References Design](sources-and-references-design.md).
Section numbers, root-cause IDs (RC1–RC7) and finding IDs (N1–N15) refer to the
main document.

---

## Appendix A. Root causes in plain terms

The same seven root causes as section 3, explained without the jargon.

### RC1. Sources have no identity

RC1 is about *how a source is named*.

**How it works today:** a wiki page mentions its sources in three places: the
list at the top of the page (`sources:`), the tags beside individual claims
(`[source: ...]`), and sometimes a Sources section at the bottom. Each place
accepts whatever text the writer chooses. The top list usually holds a file
path, the tags hold a shortened name, and the bottom section holds a sentence
of description.

**The problem:** nothing defines what a source *is*, and nothing turns any of
that text into a file you can open. So:

- The same kind of source gets written a dozen different ways.
- A typo in a path looks exactly like a real path, and nothing notices.
- To check whether a tag matches the list at the top, lint has to guess whether
  two pieces of text are "close enough" to mean the same thing.
- The three places drift apart, because nothing ties them together.

**The analogy:** it's like a library where books have no catalog numbers.
Every reference describes the book in its own words ("the pricing report",
"pricing, January", "that analyst PDF"), and finding the actual book depends on
someone guessing right.

**Why it's a root cause:** most of the other defects (the many shapes, the
split entries, the invented citation, the typo'd paths, the fuzzy matching)
come from accepting free text as a source. Fixing each one separately leaves
the door open for the next variant.

**What the design does:** every source gets a catalog number, which is simply
its filename. The same number is used in the list at the top and in the tags
beside claims, and a lookup either finds exactly one file or reports an error
(section 5.4). The Sources section at the bottom stays free-form description
and isn't checked, because it's rarely written and has drifted only once. Because the number
can't contain commas or spaces, no file format can mangle it.

### RC2. The honest path for chat facts cost more than the shortcut

RC2 is about facts you tell the agent in chat, like "remember that we decided X".

**The rule:** every fact in the wiki should point back to a saved original, a
file in `raw/`, so anyone can check where it came from. For a chat fact, the
rule since v2.0.0 has been to save a summary of the conversation into `raw/`
first, then cite that file.

**The problem:** saving the conversation was only described inside the full
ingest procedure, a long checklist meant for articles, transcripts and similar
sources. Doing all of that for a single sentence was heavy. In v2.20.0 the
author added a shortcut for single facts (PLUGIN-REVIEW A13) that deliberately
skips the checklist. The shortcut says to label the fact
`source: conversation | <date>` and move on. It never says to save anything.

So the wiki offered two paths for the same situation:

- **The proper path** saves the conversation to a file, then cites it. It's
  slower, and it's buried in a long procedure.
- **The shortcut** writes "conversation, <date>" as the source and saves
  nothing. It's fast and sits right up front in the main instructions.

The agent naturally took the shortcut. The result is citations that look like
sources but point to nothing: no file exists for any of the 18 dates the wiki
cites conversations from. It's like a receipt that says "paid in cash, Tuesday"
with nothing to show what was bought.

**Why it got worse:** there was no single agreed way to write the shortcut
label, so it appears in several different forms, which is part of the 12
shapes. Written without quotes, some of those forms get split in two by the
frontmatter format. When a fact arrived in chat during an Update, one session
invented a raw-looking filename for it, which is the phantom citation. A later
fork fix (`ae33f9d`) made "user, conversation, DATE" an officially allowed form
for Updates, which added yet another shape instead of closing the gap.

**Why it's a root cause, not just a bug:** telling the agent to "be careful"
won't fix it while the careless option is the easy one.

**What the design does:** it makes the honest option cheap instead (section
5.6). Saving a chat fact becomes one small file, written by a helper script in
a single step, and citing that file is the only accepted form. The shortcut
stays short, one step longer than today, and it no longer produces citations
that lead nowhere.

### RC3. No agreed format, at least four different readers

RC3 is about *how the information at the top of each page gets read*.

**How it works today:** that information (the frontmatter) is written in YAML,
a format that allows many ways to write the same thing. A list, for example,
can go on one line inside brackets or on separate lines with dashes. The tools
don't use a real YAML reader. Instead there are at least four homemade ones: two
inside lint, a copy inside the before-change hook, and one in the session-start
health check. That last one can't read dates written in single quotes, which is
why the health line reported 49 stale pages when 66 were stale.

**The problem:**

- No document says which of YAML's many forms a wiki page may use, so each
  homemade reader supports a different subset and guesses at the rest.
- A page that one reader accepts, another can misread without any warning.
  Mixed list styles and duplicated keys were both read "successfully" while
  whole fields silently disappeared.
- An earlier local patch (PATCH-3a) taught one reader to handle one-per-line
  lists by gluing the items back together with commas, which reintroduced the
  comma confusion another fix had just removed.
- Obsidian, which does use a real reader, sometimes disagreed with all three.
  That is how some of the corruption was found.

**The analogy:** it's like three clerks reading the same handwritten form, each
guessing differently at the unclear letters, and none of them ever saying
"I can't read this".

**Why it's a root cause:** as long as the readers guess, a malformed page can
pass every check while the data inside it is being lost.

**What the design does:** it writes down exactly which forms are allowed
(section 5.10), and every tool, including the session-start check, uses one
shared reader. Anything outside the allowed forms is reported instead of guessed
at. The same module also gives scripts a safe way to *change* one field without
rewriting the rest of the page.

### RC4. The safety checks guard only some of the doors

RC4 is about *where the safety checks are attached*.

**How the checks work today:** the wiki's safety nets are hooks, small scripts
that run automatically around a change. One runs before a change: it saves a
backup copy and warns if a page has no sources. One runs after: it checks for
broken links. They're wired to three specific editing tools in Claude Code:
Write, Edit and MultiEdit. A hook fires only when one of those three tools is
used.

**The problem:** those three tools aren't the only way files change. At least
five other ways to modify the wiki slip past the hooks entirely:

- **The wiki-search MCP** can create, rewrite and delete files with its own
  tools. The hooks don't recognize them, so there's no backup and no check.
  That's why its write tools were left off the allowlist.
- **Shell commands and scripts.** A `mv`, a `sed`, or a one-off Python script
  like the page-splitting pass edits files directly.
- **Lint's own auto-fix** rewrites links and the index with no backup first.
- **Session start** runs lint, which quietly writes a report file into
  `queries/` every session (N1).
- **You, in Obsidian**, or git operations like checkout or merge.

There are also gaps in coverage by location:

- **`briefings/`**, where daily briefs go, sits outside the folders the hooks
  and lint look at (N2).
- **Pages named `README.md`** all get backed up under the same name, so all but
  the first one each day are lost (N14).

**The analogy:** it's like a building where the security guard checks badges at
the front door only, while there are side doors, a loading dock and windows.
The guard does a good job, just at one entrance.

**Why it's a root cause:** no matter how good the checks are, they only protect
changes that come through the watched door. Several of the corruptions found
earlier came through the unwatched ones.

**What the design does:**

- **One door locked:** the MCP's page-editing tool, the one that damaged pages
  in August, is blocked with a permission setting. Agents have avoided it since
  then, and Claude Code's normal Edit tool does the same jobs safely.
- **More doors watched:** the hooks are extended to recognize the MCP's other
  write tools (section 5.11), and `briefings/` joins the watched folders.
- **A check that looks at the file itself:** a new after-change check reads the
  file from disk after it changes, rather than trusting what the tool said it
  would do.
- **A regular sweep for the rest:** for the doors that can never be watched
  (shell, scripts, Obsidian, git), lint runs at every session start and reports
  rule violations. If lint itself fails, the health line says so instead of
  reporting a clean wiki. Nothing can change the wiki without being noticed by
  the next session at the latest.

Apart from the locked door, it detects problems rather than preventing them. The
hooks still never block a change, per the author's rule; the permission setting
is not a hook.

### RC5. No rules for pages made from other pages

RC5 is about *what a new page inherits when it's made from an existing one*.

**How it works today:** several operations create a page out of another page:

- **Splitting** a page that has grown past 200 lines.
- **Promoting** a person, company or product mentioned on a concept page to a
  page of their own.
- **Superseding** an old page with a new one.
- **Crystallizing** a meeting or research thread into a digest page.

**The problem:** none of these says which sources the new page should carry.
The easy move is to copy the whole source list across. So:

- Split-off pages claimed sources their text never used. The worst case listed
  22 sources while citing 3.
- One invented citation was copied along with everything else, into ten files
  including backup copies.
- Links pointing at a section that moves to a new page can stop leading anywhere
  useful, and nothing checks for it.

**The analogy:** it's like photocopying a book's full bibliography onto every
chapter, so each chapter claims to rely on sources it never mentions.

**Why it's a root cause:** these operations are exactly where errors multiply.
One mistake on a parent page becomes the same mistake on every child, and none
of it looks wrong, because every copied path is real.

**What the design does:** a written procedure for splits and the similar
operations (section 5.8). A new page lists exactly the sources its own text
cites (a lint helper computes the list), and the parent's list is trimmed to
what it still cites. Pointers to the procedure sit where agents actually look:
the split rule in SCHEMA.md, lint's "split candidate" warning, and a reminder
when a page grows past 200 lines. The existing check for pages that list many
sources they never cite catches any split that skips the procedure.

### RC6. Nothing ever comes back to check

RC6 is about *what happens to a citation after it's written*.

**How it works today:** every rule in the wiki applies at the moment of
writing: cite a source, show a diff, update the log.

**The problem:** once a citation or an action item is on a page, nothing ever
brings it back for review. There is no expiry date, no "last checked"
requirement, and no step in any workflow that revisits it. So:

- Things that were true when written quietly go stale.
- A secondhand fact looks just as solid a year later as a verified one.
- Mistakes that slip through at write time stay forever. In ISSUE-3, a source
  missing from one page's Sources section survived six later edits to that page.
- Action items in meeting digests stay frozen at "pending" long after they were
  resolved elsewhere (ISSUE-1).

**The analogy:** it's like groceries with no expiration dates. Everything in the
fridge looks equally fresh, and nothing tells you which items to check.

**Why it's a root cause:** write-time rules can only be as good as the
information available at that moment. Without a way back, the wiki's accuracy
can only decline.

**What the design does:** a revisit rule (R10, section 5.12). A page that rests
only on things said in conversation stays flagged until someone saves a real
source for it and adds it to the page. A date alone doesn't clear the flag,
because the "last verified" date on pages changes with ordinary edits and so
can't show that anyone checked anything. The same idea could later apply to the
overview page's action items, which is left to the follow-on design (NW1).

### RC7. Copies of the same instructions drift apart

RC7 is about *guidance that exists in more than one place*.

**How it works today:** the same rules are written out in several places:

- two identical copies of the helper agents, one in the plugin and one in the
  wiki
- the page templates
- the wiki-search MCP's own settings file (`meta/contract.md`)
- the README and contributing guide
- sub-skills written before the rules they describe changed

**The problem:** when one copy is updated, the others aren't, and an agent that
reads a stale copy follows outdated rules. For example:

- The source-saving helper still applies a privacy label the plugin retired in
  v2.20.0 (N5).
- The PRD template teaches a citation form that lint can't read (N3).
- The wiki-search settings file describes a different page format altogether,
  and the MCP tells agents to follow it.
- Four different places (lint, the contributing guide, a helper agent and the
  MCP settings file) list four different sets of "required" fields (N4).

**The analogy:** it's like an office where the same procedure is pinned to four
different noticeboards and only one of them was updated. Whoever reads an old
notice follows the old procedure.

**Why it's a root cause:** fixing a rule in one place gives a false sense that
it's fixed everywhere, and the stale copies keep producing the old defects.

**What the design does:**

- **One home per rule:** each rule lives in `references/citation-spec.md`, and
  every other place points there instead of restating it.
- **One set of helper agents:** the two copies become one shared set.
- **Settings file rewritten:** the wiki-search settings file points at the
  wiki's own schema instead of describing its own.

---

## Appendix B. New findings in plain terms

The fifteen new findings from section 3 (N1–N15), each explained without the
jargon: what it is, what it costs, and how the plan fixes it.

### N1. Every session start writes a lint report

**What N1 is:** every time a Claude Code session starts, the session-start hook
runs lint to fill in the health line ("Health check: N issues…"). Lint is only
meant to report numbers back to the hook in that mode, but it also writes its
full report into the wiki as `queries/lint-<today>.md`. So opening a session
changes the wiki, even if you never touch it.

**The impact:**

- **The wiki keeps changing even when you don't.** Every day you open any
  session, a new report file appears or today's gets rewritten. The production
  wiki's `queries/` held 41 of them after about eight weeks, and 29 wiki commits
  include lint report changes. They show up in `git status` as work to commit,
  mixed in with real edits.
- **A manual lint run can be overwritten.** There's one report file per day. If
  you run lint yourself, especially with `--auto-fix`, and then start another
  session that day, the automatic run replaces your report. The record of what
  your run found or fixed is gone. Only the one-line summary in `log.md`
  survives.
- **Search results get noisier (likely, not tested).** The wiki-search MCP
  indexes every markdown file it finds. Lint excludes its own reports when
  checking the wiki, but the search index probably doesn't, so page names
  mentioned in dozens of reports can crowd search results.
- **It's a write nobody watches.** This is one of the side doors from RC4. The
  report is written by a script, so none of the hooks see it.

None of this damages page content. The reports are harmless in themselves; the
cost is clutter, noisy diffs, and the occasional lost manual report.

**The fix (plan step 6):** when lint runs in the hook's quick-check mode, it
returns its numbers and writes no file. A report only appears when someone
deliberately runs lint. Existing reports can stay as history or be cleared out.

### N2. Daily briefs live outside every check

**What N2 is:** the daily-maintenance sub-skill files each day's brief as
`briefings/YYYY-MM-DD.md`, then later moves old ones to `_archive/briefings/`
with a shell `mv`. But `briefings/` isn't one of the folders the hooks or lint
know about. They only look at `entities/`, `concepts/`, `comparisons/` and
`queries/`.

**The impact:**

- **No backup before a brief changes.** The before-change hook ignores the
  folder, so editing or rewriting a brief leaves no copy in `_archive/`.
- **No checks after.** Broken links, missing sources and bad frontmatter inside
  a brief are never reported.
- **Links to briefs can't be checked.** Lint doesn't know briefs exist, so it
  would report a link to one from a content page as broken even when it's
  correct. The production wiki's only links to briefs sit in `index.md`, which
  lint doesn't check for broken links, so the problem hasn't surfaced yet.
- **The archive move breaks links, unwatched.** Rotating briefs into
  `_archive/briefings/` is a shell command, another side door from RC4. It has
  already broken one of those `index.md` links, and it would break a meeting
  digest that lists a brief among its sources.

**The fix (plan steps 2, 3, 6 and 10):** `briefings/` joins the folders the
hooks watch and lint scans, and brief names become valid link targets. Briefs
stay in `briefings/` permanently: the 7-day rotation is removed from the
maintenance skill, since nothing reads old briefs from the archive, and the two
already-rotated briefs are moved back (review F12).

### N3. The docs teach citations lint can't follow

**What N3 is:** three places in the plugin's own templates and guides show
citation formats that the checking tools can't match to anything:

- **A wikilink inside a citation** (`[source: [[wiki-page]]]`), shown in the PRD
  template. Lint's citation reader stops at the first closing bracket, so it
  sees only `[[wiki-page` and can't match it.
- **A wikilink to a raw file** (`per [[raw/articles/...]]`), shown in the update
  guide and the output-formats guide. Lint only knows page names, so it would
  report this as a broken link, an error.
- **A web address as the source** (`[source: <url>, <date>]`), shown in the CRM
  and research sub-skills. A web address isn't a saved file and can't be matched
  to a `sources:` entry.

**The impact:**

- **Following the instructions produces errors.** An agent that copies the
  template exactly gets citations that lint reports as broken or unresolvable.
  The agent did nothing wrong; the template is inconsistent with the checker.
- **It undermines trust in lint.** Once reports include warnings caused by the
  official templates, people learn to ignore them, and real problems get
  ignored along with them.
- **Mostly a future cost so far.** These forms are rare in the production wiki
  today (a handful), but every PRD, CRM enrichment or research sprint that
  follows the templates adds more.

**The fix (plan steps 5 and 6):** the templates and guides are updated to the
one citation format (section 5.4) and point at the single spec. Lint's R7 then
flags any leftover old-style citation by name, with an automatic fix for the
simple cases.

### N4. Four different lists of required fields

**What N4 is:** four places each say which fields every page must have at the
top, and they disagree:

- **Lint** requires title, created, updated, type, tags and sources.
- **The contributing guide** lists title, type, tags, sources, updated and
  coverage. It adds `coverage` and leaves out `created`.
- **The link-checking helper agent** checks only title, type, tags and updated.
- **The wiki-search MCP's settings file** (`meta/contract.md`) lists title,
  tags, type, created, updated and a `status` field, with no sources at all.

**The impact:**

- **"Complete" depends on who you ask.** A page can pass one check and fail
  another. An agent that follows the contributing guide leaves out `created`,
  and lint then reports an error.
- **The MCP's version is actively misleading.** The MCP tells agents to read its
  settings file for page conventions, so an agent writing through the MCP is
  pointed at a schema with no `sources` field at all.
- **Fixes don't stick.** Correcting one list leaves the other three to keep
  steering agents the old way (RC7).

**The fix (plan steps 2, 4 and 8):** one definition of the required fields,
enforced by lint (R12, section 5.10). The contributing guide and the helper
agent are corrected to match, and the MCP's settings file is rewritten to point
at the wiki's own schema.

### N5. The source-saving helper still uses a retired privacy label

**What N5 is:** the helper agent that saves web pages and pasted text into
`raw/` (K1) still writes `private: true` or `private: false` at the top of each
file it saves. It also tells the main agent to mark resulting wiki pages
`private: true`. The plugin retired that label in v2.20.0. Every page is now
private automatically, and only pages marked `shareable: true` can be exported.
The v2.20.0 cleanup missed this helper.

**The impact:**

- **A false sense of protection.** The label looks like a privacy control but
  nothing reads it, so it gives someone reading the file the wrong idea about
  what keeps it private.
- **It has already spread.** 14 saved records in the production wiki carry the
  label.
- **The helper's filing rules also disagree with the ingest guide.** It names
  and describes saved files differently from the main ingest guide, so the same
  kind of source ends up filed differently depending on who saved it. Under this
  design a filename becomes a permanent citation ID, so one rule matters.

No private information has leaked because of it; the export rule is unaffected.

**The fix (plan step 2):** remove the label from the helper, and replace its
filing table with a pointer to the ingest guide. The 14 existing records stay as
they are, since saved records are never edited.

### N6. The wiki-search tool can change a date's type

**What N6 is:** a date written with quote marks, like `'2026-09-14'`, is
text. Without the quote marks, `2026-09-14`, some YAML readers (including
PyYAML, the one Python tools usually use) treat it as a real date value instead
of text. One commit in the wiki shows a quoted date losing its quotes. At first
this was blamed on the wiki-search MCP, but testing its actual code showed it
keeps quoted dates quoted, so the writer of that one change is unconfirmed. (The
MCP damages *unquoted* dates in a different way; that's N15.)

**The impact:**

- **Harmless today.** The wiki's own tools read these values as plain text
  either way, and the dates themselves are unchanged.
- **A trap for later.** Any tool that reads the files with a standard YAML
  library, including a future version of lint, gets text for some pages and
  date values for others. Comparisons and string handling can then fail in
  confusing ways.
- **Rules about quoting can't be relied on.** Quotes can be lost without anyone
  noticing, so a rule that says "this value must be quoted" isn't a safe
  foundation.

**The fix (plan steps 4 and 5):** the single shared reader treats every value as
text and checks dates by their pattern, so it doesn't matter to the wiki's own
tools whether a date is quoted. For everything else, dates are written in one
standard form, with single quotes (`'2026-09-14'`). That's the form both the
wiki-search MCP and Python's YAML library already write for a text date, so it
comes through either one unchanged, and no reader mistakes it for a date value
(review F2).

### N7. Citations written in ways no tool can follow

**What N7 is:** measuring all 1,070 inline citations in the production wiki
turned up a set of defects beyond the ones already known:

- **9 are broken across a line inside the source name**, so the name is split in
  two.
- **8 contain a doubled prefix** (`source: source: ...`).
- **5 cite two sources joined by "vs."** instead of the separator the format
  uses.
- **6 cite a structural file**, such as the schema page, instead of a source.
- **4 are free prose** rather than a source name.
- **2 cite a script file.**
- **1 wraps a wikilink.**

That's 35 in total. Separately, 55 citations run across more than one line; many
of those still work, but they're fragile.

**The impact:**

- **Readers can't trace those claims.** A citation that doesn't name a real
  source gives no way to check the claim it supports.
- **Noise in lint's reports.** These show up among the missing-citation reports
  (R3), mixed in with real gaps, which makes the real ones harder to spot.
- **They can't be fixed by guessing.** The current lint matches loosely to avoid
  false alarms, which also means it can't point at exactly what's wrong.

**The fix (plan steps 6 and 10):** the new format rule (R7) names each of these
defects specifically. Lint can repair the mechanical ones (line breaks, doubled
prefixes, "vs."), but only when asked to with a separate option, so the
unattended daily run never rewrites citations; the migration uses it after a
reviewed dry run (review F5). The migration hands the rest (13 citations) to a
person to fix.

### N8. A sub-skill still claims a gate is enforced

**What N8 is:** the plugin review (PLUGIN-REVIEW A7) found that the core skill
described its "orient first" rule as *enforced*, with the agent refusing to
write until it had read the key files. Nothing actually enforced that. The core
skill was relabeled as a checklist in v2.20.0, but the PRD sub-skill still says
"Orient gate (enforced): … refuse any write".

**The impact:**

- **It overstates what's guaranteed.** Anyone reading the PRD sub-skill would
  think writes are blocked until orientation happens. They aren't.
- **It can make the agent behave inconsistently.** The same rule reads as a hard
  gate in one skill and a checklist in another.
- **Small, but it's the pattern the review set out to remove.** Guardrails that
  claim to fire but can't are exactly the problem PLUGIN-REVIEW named.

**The fix (plan step 2):** a one-line change to match the core skill's checklist
wording.

### N9. The link-checking helper would report hundreds of false breaks

**What N9 is:** the link-checking helper agent checks each `[[link]]` by looking
for the target in `entities/`, `concepts/` and `comparisons/`. It never looks in
`queries/`, where digests, research and filed answers live.

**The impact:**

- **Hundreds of false alarms.** The production wiki has 411 links into
  `queries/` across 138 pages. Every one would be reported as broken.
- **Real problems get buried.** A genuinely broken link would be lost in that
  list.
- **Latent so far.** The helper only runs when asked, and lint (which does check
  `queries/`) is what normally reports broken links, so this hasn't caused
  visible trouble yet.

**The fix (plan step 2):** the helper uses lint's link check instead of keeping
its own, so there's one definition of a valid link.

### N10. Two saved sources share a name with their original file

**What N10 is:** when a PDF or slide deck is saved, the original goes in
`raw/assets/` and an extracted text version goes in another `raw/` folder. In two
cases the text version and the original have the same name apart from the file
extension.

**The impact:**

- **Harmless today.** Nothing currently uses the bare name to find a file.
- **A potential ambiguity under the new rules.** This design uses a file's name,
  without the extension, as its citation ID. Without a rule, those two names
  would each point at two files.

**The fix (plan step 5):** the ID rule (section 5.1) counts only text records
and excludes `raw/assets/`, so the original file is reached through its text
record and each ID points at exactly one file. No files need to change.

### N11. Some saved sources lack details, and two are unused

**What N11 is:** 11 of the 153 saved text records in `raw/` have no information
block at the top: no capture date, source type or original location. Separately,
2 of the 156 files in `raw/` aren't referenced by any page.

**The impact:**

- **Weaker provenance for 11 records.** Without a capture date or origin, it's
  harder to judge how current or reliable they are, or to find the original
  again.
- **Two sources saved for nothing (so far).** Either an ingest stopped partway,
  or they're waiting to be used. Either way, nothing in the wiki draws on them.
- **Small in scale.** Most records are complete and nearly all are used.

**The fix:** none beyond a recommended template for new records. A rule
requiring the details (R13) was dropped: none of the tools that save records
writes the field it would check, the records use eight different date fields,
and all 11 bare records came from two weeks in August (review F6). The helper
that saves conversation facts writes its record's type itself, which is the
one field a rule reads. Existing records are left alone because saved records are
never edited. The two unused files can be cited or left as they are.

### N12. Private wiki names appear in the public fork

**What N12 is:** the fork is public on GitHub, but two files in it contain the
names of real people and customer companies from the private wiki: a test file
uses two real source names that include customer names, and the earlier
lint-checks design quotes them, along with two colleagues' page names, as
examples. Product names and page-topic names also appear, but those aren't
treated as private.

**The impact:**

- **Private information is publicly readable.** Anyone browsing the fork can
  see names of customers and colleagues that were meant to stay in the private
  wiki.
- **It's already in git history.** Scrubbing the files stops it being visible in
  current versions, but the old versions stay reachable unless the history is
  rewritten.
- **It goes against the plugin's own practice.** The upstream author scrubbed
  real names from distributed files in v2.20.0 for this reason.

**The fix (plan step 0):** replace the names with placeholders, and rewrite git
history so the old versions no longer contain them (decided in D8). It's cheap
now, because nobody has copied the fork yet. The commit IDs this design cites
change as a result, and are updated from the rewrite tool's old-to-new map.

### N13. The wiki-search launcher logs a false error

**What N13 is:** the script that starts the wiki-search MCP first looks for a
`.wiki-path` file in the current folder. It reads the file in a way that makes
the shell itself complain when the file doesn't exist, before the script's
"ignore errors" handling can take effect. So every session started in a folder
without `.wiki-path` logs "No such file or directory". This was reproduced
directly.

**The impact:**

- **It looks like a failure when nothing failed.** The launcher carries on
  correctly and falls back to the next way of finding the wiki.
- **It wastes troubleshooting time.** Anyone investigating a real connection
  problem sees this message first in the MCP's logs and may chase the wrong
  cause.
- **It slipped through because there was no test.** It was introduced by the
  v2.20.0 fix for PLUGIN-REVIEW A11, whose requested smoke test was never
  written.

**The fix (plan step 1):** check whether the file exists before reading it, as
the session-start hook already does, and add the smoke test A11 asked for
(section 5.13).

### N14. All README pages share one backup name

**What N14 is:** some wiki pages are folders, like a PRD or a research sprint,
whose main page is called `README.md`. The before-change hook names each backup
after the file's name, so every one of these pages is backed up as
`_archive/README-<date>.md`. The hook also makes only one backup per name per
day.

**The impact:**

- **Lost backups.** If two folder-style pages are edited on the same day, only
  the first gets a backup; the second is silently skipped.
- **Unlabeled backups.** A backup named `README-<date>.md` doesn't say which page
  it came from. The production wiki has 4 folder-style pages and one such backup
  file, whose origin isn't recorded.
- **Undo doesn't work for them.** Recovering one of these pages means digging
  through git, which only helps if the change was committed.

**The fix (plan step 3):** name backups by the page's real name (the folder name
for a `README.md`), the same way lint already names pages. Each backup then
points at exactly one page.

### N15. Some dates are stored in a format the checks can't read

**What N15 is:** dates at the top of a page are normally written as
`2026-09-03`. On 13 pages some dates are written as full timestamps instead,
`2026-09-03T00:00:00.000Z`: 13 creation dates, 3 last-verified dates and 1
last-updated date.

**The cause.** When the wiki-search MCP changes a page's frontmatter, it reads
the whole block and writes it back using a library (js-yaml) whose default
setting treats an unquoted date as a date and writes it back as a timestamp.
That was reproduced with the MCP's own copy of the library. New timestamps
arrived in five separate commits between early August and early September. The
wiki's own log records agents using the MCP's frontmatter tool in early August;
for the later commits the writer isn't confirmed, because about a third of the
days the wiki was edited have no saved session record. It's the same "rebuild
the whole file" behavior that escapes brackets (PATCH-3d, upstream issue #47).
It has been reported to the MCP's maintainer as issue #49, who has not responded
to anything since June 2026.

The same rewrite puts single quotes around dates that were already quoted
(`'2026-09-03'`), and Python's YAML library does the same. That's harmless in
itself, but lint's staleness check and the session-start scan don't expect the
quotes either.

**The impact:**

- **Staleness checks silently skip them.** Lint and the session-start scan use a
  Python date reader that rejects the trailing `Z` of a timestamp and the quote
  marks of a single-quoted date. The error is swallowed, so the check is simply
  skipped with no message.
- **Far more pages than the timestamps suggest.** Lint's 90-day check can't read
  the update date on 115 pages, and the session-start scan skips 92 of 143
  knowledge pages. On 2026-09-28 the health line said 49 pages were stale when 66
  were (review F2).
- **The creation dates are harmless for now.** Nothing checks `created` except
  that it exists, so those 13 values cause no visible problem today.
- **It supports not trusting `last_verified`.** A date that no check can read gives
  a false sense that the page has been looked after.

**The fix:**

- **Stop it at the source (plan step 3):** the MCP's page-editing tool is blocked
  with a permission setting, so the rewrite can't happen on this install
  (review F4).
- **Write dates in a form that survives (plan steps 4 and 5):** dates are written
  single-quoted, `'2026-09-03'`, which neither the MCP nor Python's library
  changes.
- **Read every form (plan step 4):** the one shared reader, now also used by the
  session-start scan, accepts a date quoted or not, and reports anything else
  (R12). The post-write check reports it in the same turn.
- **Clean up (plan step 10):** the migration rewrites the 17 timestamp values in
  the single-quoted form, using the content-repair option of lint's auto-fix.
  That's lossless, because every one has a time of exactly midnight.
- **Not needed now:** the patched local MCP copy (step 12) is dropped, and the MCP
  fork (NW2) is deferred.
