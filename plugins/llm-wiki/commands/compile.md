---
description: Compile raw sources into wiki pages (faithful read, then merge)
argument-hint: [<path>]
---

Turn uncompiled raw sources into wiki pages. Two passes: a WIKI-BLIND faithful
read, then an informed merge. Follow the injected conventions exactly.

1. Resolve context: `llm-wiki-state context "$PWD"`. Need a `topic`; if empty, stop and tell the user to run `/llm-wiki:set-topic`. Let `W = <vault_path>/<topic>`. Read `<templates_path>/source-summary.md` (and `concept.md`/`person.md` as needed).
2. Identify sources (no content reads):
   - If `$ARGUMENTS` is a path: that source + its `.meta.md` sidecar.
   - Else: read `W/raw/articles/*.meta.md`; select those with `compiled: false`.
   - If none: "All sources are already compiled." Stop.
3. Decide the mode (never ask the user):
   - A "focus" = the user's comment/discussion about what matters for this source.
   - fresh + no focus -> neutral read only.
   - fresh + focus -> neutral read + focused read(s).
   - already-compiled + focus -> append focused deep-read only (do NOT regenerate the Overview).
   - already-compiled + no focus -> nothing to do.
4. PASS 1 - faithful read. For each source/lens, dispatch a SOURCE-READER subagent (use your Agent/Task tool). Give it ONLY: the raw source file (PDFs: it reads them with the Read tool), the brief, and the source-summary template. It must be WIKI-BLIND - never give it existing wiki pages. The neutral brief is conversation-blind; a focused brief carries the user's angle AND that detail's surrounding context in the source. It returns: a framed summary (declared `frame`, lens-bound disclaimer, NO enumerated gaps) + candidate entities/claims.
5. PASS 2 - integrate (you, wiki-aware):
   a. Write/append the source-summary in `W/wiki/`: `## Overview -- frame: ...` for neutral; `## Deep read [YYYY-MM-DD] -- frame: ...` for focused. Fix small factual errors in place with a `[corrected YYYY-MM-DD per deep read: <frame>]` note; only a genuinely new perspective gets a new section.
   b. For each candidate entity, reconcile aliases against existing pages, then create/update `W/wiki/<name>.md` from `concept.md`/`person.md`. Apply the per-claim citation discipline (link `[[source-summary-x]]` for source claims, `[[concept-y]]` for derived).
   c. Backlink audit: `grep -rln "<new title>" "W/wiki/"` and add missing `[[wikilinks]]`.
   d. Update `W/wiki/index.md`.
   e. Set `compiled: true` in each source's `.meta.md`.
6. Append a compile entry to `W/log.md`. Commit. Never push.
7. If `command -v qmd` succeeds: `qmd embed --collection <topic>`.
