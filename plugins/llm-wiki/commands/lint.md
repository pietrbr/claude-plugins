---
description: Health-check the wiki; auto-fix mechanical issues, flag judgment ones
argument-hint: (no arguments)
---

Audit the active wiki. Follow the injected conventions. Bookkeeping is automatic;
judgment stays with the user.

1. Resolve context: `llm-wiki-state context "$PWD"`. Need a `topic`. Let `W = <vault_path>/<topic>`.
2. Read `W/wiki/`. Build the `[[link]]` graph.
3. Handle:
   - Index drift, and missing MANDATORY section headers (the headers each type's template declares) -> AUTO-FIX (these are mechanical).
   - Dead links, orphan pages/concepts, contradictions (`> [!WARNING]`) -> REPORT.
   - Stale DERIVED concepts (a newer source appears to supersede a synthesized conclusion) -> FLAG and ASK the user; NEVER auto-update them.
   - Do NOT flag uncovered gaps in sources (those are fine).
4. Save a dated report to `W/outputs/reports/YYYY-MM-DD-lint.md` -- a sibling of `wiki/`, NOT inside it (`W/outputs/`, never `W/wiki/outputs/`). Reports must stay out of the `wiki/` graph/embedding scan; if you find prior reports under `wiki/`, they drifted -- do not follow them.
5. Append a lint entry to `W/log.md`. Commit. Never push.
