# Wiki Search & Retrieval Architecture

_Relocated 2026-08-30 from `pm-wiki/concepts/wiki-search-architecture.md` (a PM
knowledge wiki that runs on this plugin) — tooling/meta content, not PM domain
knowledge, so it belongs here instead. Originally created 2026-08-08, last
updated 2026-08-11._

## Definition / framing

How a wiki running this plugin's search and retrieval layer works, and how it
compares to `qmd`, the tool Andrej Karpathy's LLM Wiki gist recommends as the
scaling path for wikis like this one. Captured after a session Q&A thread that
inspected the installed package directly (not just its docs).

## Current state

### What runs the wiki's search

The `wiki-search` MCP server bundled by the llm-wiki-pm plugin is `@wirux/mcp-markdown-vault` v2.3.0 (MIT, `github.com/wirux/mcp-markdown-vault`), a headless server for Obsidian/Logseq/Dendron/Foam or any markdown folder — reads/writes `.md` files directly, no app or plugin dependency.

**Tool dispatcher** — five tools, each with sub-actions: `vault` (CRUD + templates), `edit` (AST-based patching + frontmatter + batch), `view` (search/read/backlinks), `workflow` (Petri-net state machine), `system` (server status/reindex/overview). Confirmed by grepping every skill in this plugin (`llm-wiki-pm`, `llm-wiki-brief`, `llm-wiki-persona`, `llm-wiki-crm`, `llm-wiki-prd`, `llm-wiki-research`, `llm-wiki-maintain`, all worker subagents, the CHANGELOG): **`workflow` is unused by any of them.** The server's own docs confirm it's inert by design — "manages session-specific state used for contextual hints... does not modify vault data or search indexes."

**AST-based editing** — edits target a parsed markdown syntax tree (via `remark`/`unified`) rather than raw text, so an append or frontmatter update can't accidentally corrupt YAML or land in the wrong section. Line/string replace exist as a fallback, flagged in the vendor's own docs as "last resort" since it needs exact literal matches. Real caveat from the source wiki's history: on 2026-08-05, an AST edit round-trip escaped literal double-square-bracket wikilinks into backslash-escaped brackets across 6 files during re-serialization, silently breaking link resolution until lint caught the resulting false-orphan flags. AST editing is safer against *structural* corruption than raw find/replace, not immune to its own serialization bugs.

**Search** — hybrid: cosine-similarity vector search + TF-IDF (keyword/rare-term scoring) + word-proximity, over heading-aware chunks so a query returns the relevant section, not the whole file. Embeddings are local: `all-MiniLM-L6-v2`, 384 dimensions, ~80MB, downloaded once from Hugging Face and cached in `.markdown_vault_mcp/` inside the vault. No API key, no per-query cost, fully offline after first download.

**Vector store** — default is a local flat-file store living inside the vault folder; optional swap to Qdrant (a dedicated vector database, run as its own service) via `VECTOR_STORE_URL`. Rough scaling estimate (not vendor-documented, this wiki-tooling cluster's own heuristic): flat-file stays comfortably fast into the low thousands of vectors; Qdrant starts earning its complexity in the tens-of-thousands-of-vectors range, or whenever concurrent/multi-client access or an index decoupled from the MCP server's own lifecycle is needed.

### Comparison: qmd

Karpathy's LLM Wiki gist (per secondary summaries — the gist itself wasn't fetched directly) recommends `qmd`, built by Tobi Lütke (Shopify CEO), as the scaling solution once a wiki's single `index.md` file gets too large to navigate comfortably — stated inflection point: **roughly 100-150 articles / 100 sources**.

| | This plugin's default (`@wirux/mcp-markdown-vault`) | `qmd` |
|---|---|---|
| Creator | Wirux (open-source project) | Tobi Lütke |
| Core purpose | Full read **and** write vault manager | Search/retrieval only |
| Search technique | Vector (cosine) + TF-IDF + word-proximity | BM25 (SQLite FTS5) + vector + **LLM cross-encoder reranking** + query expansion, fused via Reciprocal Rank Fusion |
| Local models | 1 embedding model, ~80MB | 3 models (embed + rerank + query-expansion), ~2GB total |
| Index storage | Flat-file (or optional Qdrant), inside the vault folder | SQLite + sqlite-vec, in a global cache (`~/.cache/qmd/`) |
| Chunking | Heading-aware (markdown structure) | ~900 tokens with 15% overlap, plus optional tree-sitter AST chunking for code |
| Editing | Full CRUD, AST-based patching, frontmatter management, dry-run diffs | None — explicitly read-only |
| MCP tools | 5 dispatchers (`vault`/`edit`/`view`/`workflow`/`system`) | 4 tools (`query`/`get`/`multi_get`/`status`) |

**The real difference is scope, not just search quality.** qmd invests more local compute per query (an actual reranker, not just embeddings) which should mean better relevance ranking, at the cost of a much heavier resource footprint and slower cold start. But it never touches files — everything a vault's ingest/update workflow does under the hood (`vault.create`, `edit.frontmatter_set`, AST section patches) is wirux's write side, which qmd has no equivalent for. Swapping to qmd wouldn't replace wirux; it would only replace the *search* half, with wirux (or direct file edits) still needed for writes — closer to a hybrid setup (qmd for retrieval, wirux for writes) than a substitution.

## Open questions

- Should a growing wiki adopt qmd as a complementary retrieval layer once page count clears the ~100-150 Karpathy threshold, or does wirux's existing hybrid search stay adequate well past that (given it's chunk-count, not page-count, that actually drives flat-file search performance)?
- Would pairing qmd's reranking with wirux's write operations need custom glue, or does Karpathy's own setup demonstrate a working pattern for running both side by side?
- Is there a large enough quality gap between the two search stacks (qmd's cross-encoder reranking vs. wirux's simpler blend) to matter at typical wiki scale, or is that only visible on much larger corpora?

## Sources

- Local npm package inspection (package.json, README) + GitHub repo for `@wirux/mcp-markdown-vault`, captured 2026-08-08
- GitHub repo (`tobi/qmd`) plus corroborating Medium coverage, captured 2026-08-08
- Secondary breakdowns of Karpathy's LLM Wiki gist (Substack, Proudfrog), captured 2026-08-08 — not the original gist itself
