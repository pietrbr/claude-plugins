---
description: Answer a question from the wiki, with citations, and file it
argument-hint: <question>
---

Answer a question against the active wiki and file the answer back.

0. Context: the prompt hook injected `vault_path`, `topic`, `templates_path`, and the conventions. If that context is missing (for example, a skill started this command), run `llm-wiki context --conventions "$PWD"` once, before any `cd`, and use its output. Use the `cwd` value from the context, in single quotes, for `<cwd>`, never `$PWD`: the shell can change directory during the command.
1. If `topic` in the context is empty, stop and tell the user to run `/llm-wiki:set-topic`. Let `W = <vault_path>/<topic>`.
2. Question = `$ARGUMENTS`. A query is ONE question -> one filed answer (it may require reasoning). A long, multi-document exploration is NOT a query - that produces derived concept pages; use the conversation + `compile`/derived concepts instead.
3. Find relevant pages: read `W/wiki/index.md` FIRST. If `command -v qmd` succeeds, use `qmd query --collection <topic> "<question>"`; else grep `W/wiki/`. Open the relevant pages; follow one level of `[[wikilinks]]` for context. Do not read the whole wiki.
4. Synthesize an answer in prose with `[[wikilink]]` citations inline.
5. Gap check -- ONLY if a gap in the wiki layer could make the answer wrong, incomplete, or misleading (a missing material page, or a contradiction / possibly-stale claim the answer rests on): add a one-line caveat in the answer prose naming the gap and suggesting a focused `/llm-wiki:compile <source>` (or a new source). NOT for merely thin-but-adequate coverage. Nothing goes in frontmatter.
6. File it (mandatory, no prompt) to `W/wiki/queries/<slug>.md` using `<templates_path>/query.md` (`type: query`, `informed-by:` = pages used, `status: filed`).
7. Promote ONLY if BOTH hold: the answer is a reusable synthesis (a comparison, analysis, or connection with value beyond this one question -- not a one-off lookup) AND no existing concept page covers it. Then offer to rewrite it as a derived concept page in `W/wiki/` and set the query's `status: promoted`. If a concept page already covers it, fold the insight into that page instead; if it is a one-off lookup, leave it as the query record.
8. Log and commit: `llm-wiki log-commit '<cwd>' query -- '<question>' '<one line: pages used, filed slug>'`. Put each free-text argument in single quotes and write each `'` in it as `'\''`. Do not edit `W/log.md` or run git yourself. Never push.
