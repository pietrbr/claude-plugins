---
description: Compile raw sources into wiki pages (faithful read, then merge)
argument-hint: [<path>]
---

Turn uncompiled raw sources into wiki pages. Two passes: a WIKI-BLIND faithful
read, then an informed merge. Follow the injected conventions exactly.

1. Resolve context: `llm-wiki-state context "$PWD"`. Need a `topic`; if empty, stop and tell the user to run `/llm-wiki:set-topic`. Let `W = <vault_path>/<topic>`. Read `<templates_path>/source-summary.md` (and `concept.md`/`person.md` as needed).
2. Identify sources (no content reads):
   - If `$ARGUMENTS` is a path: that source + its `.meta.md` sidecar.
   - Else: read `W/raw/documents/*.meta.md`; select those with `compiled: false`.
   - If none: "All sources are already compiled." Stop.
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
   a. Write/append the source-summary in `W/wiki/`: `## Overview -- frame: ...` for neutral; `## Deep read [YYYY-MM-DD] -- frame: ...` for focused. Copy `source-file`, `source-uri`, and `source-type` verbatim from the sidecar into the summary frontmatter -- NEVER synthesize a vault path for `source-uri` (the raw copy is located by `source-file`). Fix small factual errors in place with a `[corrected YYYY-MM-DD per deep read: <frame>]` note; only a genuinely new perspective gets a new section.
   b. For each candidate entity, reconcile aliases against existing pages, then create/update `W/wiki/<name>.md` from `concept.md`/`person.md`. Apply the per-claim citation discipline (link `[[source-summary-x]]` for source claims, `[[concept-y]]` for derived).
   c. Backlink audit: `grep -rln "<new title>" "W/wiki/"` and add missing `[[wikilinks]]`.
   d. Update `W/wiki/index.md`.
   e. Set `compiled: true` in each source's `.meta.md`.
6. Append a compile entry to `W/log.md`. Commit. Never push.
7. If `command -v qmd` succeeds: `qmd embed --collection <topic>`.
