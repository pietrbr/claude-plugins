# llm-wiki conventions (canonical)

These rules govern every operation. They are injected into context by the
resolution hook and are the base layer; a vault-root `CLAUDE.md` then a topic
`CLAUDE.md` may override them (last-wins). Keep them short.

## Output policy (chat)

- Stay SILENT on routine success. Do NOT narrate bookkeeping: no "saved",
  "compiled", "filed", "committed", "done", or "all went well" confirmations.
  A successful operation produces no chat output.
- Speak ONLY for things the user needs to act on or know about:
  - warnings and contradictions (`> [!WARNING]`);
  - a previously-flagged warning that a new source re-triggers or re-widens;
  - errors and blocks (e.g. no topic bound, missing source);
  - **no-op notices**: a command the user invoked that found nothing to do
    (e.g. `compile` when all sources are already compiled) -- surface it, since
    the user expected work to happen;
  - command deliverables and deliberate state changes: a `query` answer; a
    `doctor`/`lint` report; the result of a config/setup command
    (`set-vault`, `set-topic`, `init`), `merge`'s report, and `remove`'s recovery commit.
- The silence applies to the recurring content operations -- `ingest`,
  `compile`, `query` -- and their commit/bookkeeping noise, NOT to the
  deliverables above. (Exception: a single-source `compile` opens a brief
  pre-read scoping discussion -- that interaction is intended, not bookkeeping.)
- This governs chat prose only; `log.md` entries and commits are written as usual.

## Faithfulness (the core principle)

- The raw source is the only ground truth. Never bend a reading to fit existing
  wiki pages. Verification always re-grounds in the raw source, never in a summary.
- Avoiding hallucination is paramount. State what you actually read; do not invent.

## Naming & links

- Filenames: `lowercase-kebab-case.md`.
- Internal links: `[[wikilink]]` only (filename without extension). Never use
  standard markdown links for internal references.

## Source location vs provenance

- `source-file` (bare filename, no path) is the ONLY pointer to the local raw
  copy; resolve it against the `raw/` convention. Folder-agnostic on purpose.
- `source-uri` is provenance ONLY: a canonical external identifier (URL / DOI),
  or the original location the source was ingested from (a local path is valid
  provenance). Leave it EMPTY when neither exists. NEVER a vault-internal
  `raw/...` path -- that only duplicates `source-file` and breaks on moves.

## Per-claim citation discipline

- Every non-obvious claim links its basis:
  - `[[source-summary-x]]` = a source said this.
  - `[[concept-y]]` = derived from / connected to other wiki knowledge.
- This is how a reader tells "what a source said" from "what was concluded."
  There is NO ingested-vs-derived frontmatter flag; the distinction lives in the
  link target.

## Source types (provenance only)

- Recorded in each source's `.meta.md` `source-type`, and surfaced as metadata on the
  source-summary page and its index line. A provenance/trust label only -- it changes
  no compile/query behavior; boundaries are soft, misclassification is low-stakes.
  - `paper` -- peer-reviewed / scholarly (journal, conference, arXiv preprint).
  - `article` -- informal external writing (blog, news, magazine, product docs, datasheet, manual).
  - `standard` -- normative standards-body document (3GPP TS/TR, RFC, IEEE, ETSI, O-RAN).
  - `conversation` -- transcript of spoken/dialogic content (talk, interview, podcast, meeting, chat).
  - `user-note` -- the user's own authored note or synthesis; vouched at time of writing, still subject to staleness like any source.
- paper vs article: "was it scholarly-reviewed?" preprint -> `paper`; blog / whitepaper
  / product docs -> `article`. standard vs article: a standard is standards-body-produced
  and normative; product docs are single-vendor descriptive -> `article`.

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
