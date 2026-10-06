---
description: Compile raw sources into wiki pages (faithful read, then merge)
argument-hint: [<path>]
---

Turn uncompiled raw sources into wiki pages. Two passes: a WIKI-BLIND faithful
read, then an informed merge. Follow the injected conventions exactly.

0. Context: the prompt hook injected `vault_path`, `topic`, `templates_path`, and the conventions. If that context is missing (for example, a skill started this command), run `llm-wiki context --conventions "$PWD"` once, before any `cd`, and use its output. Use the `cwd` value from the context, in single quotes, for `<cwd>`, never `$PWD`: the shell can change directory during the command.
1. If `topic` in the context is empty, stop and tell the user to run `/llm-wiki:set-topic`. Let `W = <vault_path>/<topic>`. Read `<templates_path>/source-summary.md` (and `concept.md`/`person.md` as needed).
2. Identify sources (no content reads): run `llm-wiki compile-scan '<cwd>'`, or `llm-wiki compile-scan '<cwd>' '<path>' ['<path>' ...]` if `$ARGUMENTS` names sources. It prints each selected source with its sidecar frontmatter and its existing summary pages. Do not read the sidecars yourself.
   - If it prints "All sources are already compiled.", tell the user and stop.
3. Decide involvement, then read mode. A "focus" = what matters for this source, from discussion or stated in the invocation.
   - Involvement (single source -> discuss; batch -> silent unless asked):
     - Single source (one path): open a brief discussion before reading -- settle on an angle to focus on, or on a neutral overview. A touchpoint every time; but if the invocation already states the intent (neutral, or "focus on X"), that IS the discussion -- acknowledge and proceed, do not re-ask unless it is not clear.
     - Multiple sources (the default uncompiled set, or a path list): default to silent / less-supervised -- proceed without discussion. Only if the user asks to stay involved, run the single-source discussion for each source, in sequence.
   - Focus scope (nudge, not gate): for a silent batch driven by one shared focus, target a subset -- a path list or a query-selected set; do not smear the focus across the whole set. Applying it to the whole default set is fine when the corpus is new/recent/freshly added; only when the set is large AND established, offer to query-select first, then proceed as the user chooses. (An involved batch scopes each source on its own, so this does not apply.)
   - Read mode (what gets written):
     - fresh + no focus -> neutral read only.
     - fresh + focus -> neutral read + focused read(s).
     - already-compiled + focus -> append focused deep-read only (do NOT regenerate the Overview).
     - already-compiled + no focus -> nothing to do.
4. PASS 1 - faithful read. For each source/lens, dispatch a SOURCE-READER subagent (use your Agent/Task tool). Give it ONLY: the raw source file (PDFs: it reads them with the Read tool), the brief, and the source-summary template. It must be WIKI-BLIND - never give it existing wiki pages. The neutral brief is conversation-blind; a focused brief carries the user's angle AND that detail's surrounding context in the source. It returns: a framed summary (declared `frame`, lens-bound disclaimer, NO enumerated gaps) + candidate entities/claims.
5. PASS 2 - integrate (you, wiki-aware):
   a. Write/append the source-summary in `W/wiki/`: `## Overview -- frame: ...` for neutral; `## Deep read [YYYY-MM-DD] -- frame: ...` for focused. Copy the `source-file`, `source-uri`, and `source-type` lines verbatim, quotes included, from the sidecar frontmatter that `compile-scan` printed into the summary frontmatter -- NEVER synthesize a vault path for `source-uri` (the raw copy is located by `source-file`). Fix small factual errors in place with a `[corrected YYYY-MM-DD per deep read: <frame>]` note; only a genuinely new perspective gets a new section.
   b. For each candidate entity, reconcile aliases against existing pages, then create/update `W/wiki/<name>.md` from `concept.md`/`person.md`. Apply the per-claim citation discipline (link `[[source-summary-x]]` for source claims, `[[concept-y]]` for derived).
   c. Backlink audit: run `llm-wiki backlinks '<cwd>' <new or renamed page names>`. For each page it prints the pages that mention that page's title or name without linking it. Add the missing `[[wikilinks]]` where the mention means that page.
   d. Update `W/wiki/index.md`.
   e. Run `llm-wiki mark-compiled '<cwd>' <source file names>`. Do not edit the sidecars yourself.
6. Log, commit, and refresh search: `llm-wiki log-commit '<cwd>' compile -- '<title>' '<one-line description>'`. Put each free-text argument in single quotes and write each `'` in it as `'\''`. Do not edit `W/log.md` or run git or qmd yourself. Never push.
