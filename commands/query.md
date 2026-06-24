---
description: Answer a question from the wiki, with citations, and file it
argument-hint: <question>
---
Answer a question against the active wiki and file the answer back.

1. Resolve context: `llm-wiki-state context "$PWD"`. Need a `topic`; if empty, stop and tell the user to run `/llm-wiki:set-topic`. Let `W = <vault_path>/<topic>`.
2. Question = `$ARGUMENTS`. A query is ONE question -> one filed answer (it may require reasoning). A long, multi-document exploration is NOT a query - that produces derived concept pages; use the conversation + `compile`/derived concepts instead.
3. Find relevant pages: read `W/wiki/index.md` FIRST. If `command -v qmd` succeeds, use `qmd query --collection <topic> "<question>"`; else grep `W/wiki/`. Open the relevant pages; follow one level of `[[wikilinks]]` for context. Do not read the whole wiki.
4. Synthesize an answer in prose with `[[wikilink]]` citations inline.
5. File it (mandatory, no prompt) to `W/wiki/queries/<slug>.md` using `<templates_path>/query.md` (`type: query`, `informed-by:` = pages used, `status: filed`).
6. If the answer is durable/new, offer to rewrite it as a derived concept page in `W/wiki/` (then set the query's `status: promoted`).
7. Append a query entry to `W/log.md`. Commit. Never push.
