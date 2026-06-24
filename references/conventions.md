# llm-wiki conventions (canonical)

These rules govern every operation. They are injected into context by the
resolution hook and are the base layer; a vault-root `CLAUDE.md` then a topic
`CLAUDE.md` may override them (last-wins). Keep them short.

## Faithfulness (the core principle)
- The raw source is the only ground truth. Never bend a reading to fit existing
  wiki pages. Verification always re-grounds in the raw source, never in a summary.
- Avoiding hallucination is paramount. State what you actually read; do not invent.

## Naming & links
- Filenames: `lowercase-kebab-case.md`.
- Internal links: `[[wikilink]]` only (filename without extension). Never use
  standard markdown links for internal references.

## Per-claim citation discipline
- Every non-obvious claim links its basis:
  - `[[source-summary-x]]` = a source said this.
  - `[[concept-y]]` = derived from / connected to other wiki knowledge.
- This is how a reader tells "what a source said" from "what was concluded."
  There is NO ingested-vs-derived frontmatter flag; the distinction lives in the
  link target.

## Summary framing (negative space by perspective)
- Each source-summary declares a specific **frame** (the lens it read through) and
  a one-line lens-bound disclaimer.
- Do NOT enumerate "other angles not covered" (that invites hallucination). The
  negative space is the implicit complement of a well-specified frame. A sharper
  frame means a sharper implied boundary.

## Reader isolation (compile)
- The source-reader is **wiki-blind**: it never sees existing wiki pages, only the
  raw source + a brief + the template.
- Neutral reads are also **conversation-blind**. Focused reads are
  conversation-aware (carry the user's angle + that detail's surrounding context in
  the source) but still wiki-blind.

## Cross-references
- Every page links to >= 1 other page when content warrants it.
- On compile, run a backlink audit: grep existing pages for mentions of new page
  titles and add `[[wikilinks]]` where missing (both directions).
- Flag contradictions inline: `> [!WARNING] Contradiction with [[other-page]]`.

## Index format (`wiki/index.md`)
- Read it FIRST when querying. Organized by domain. One line per page:
  `- [[page-name]] -- one-line description (YYYY-MM-DD)` (keep <= 80 chars).
- Update after every compile.

## Log format (`log.md`)
- Append-only; never edit existing entries. Grep-able prefix:
  `## [YYYY-MM-DD] <op> | <title>` then a one-line description.

## Git
- Commit to the vault repo after every operation. Manage history autonomously.
- NEVER push.

## Templates
- Page templates ship with the plugin at the injected `templates_path`. Read the
  one you need at runtime; do not copy them into the wiki. `index.md`/`log.md` are
  one-time scaffolds instantiated at init.
