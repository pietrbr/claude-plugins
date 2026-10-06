---
description: Health-check the wiki; auto-fix mechanical issues, flag judgment ones
argument-hint: (no arguments)
---

Audit the active wiki. Follow the injected conventions. Bookkeeping is automatic;
judgment stays with the user.

0. Context: the prompt hook injected `vault_path`, `topic`, `templates_path`, and the conventions. If that context is missing (for example, a skill started this command), run `llm-wiki context --conventions "$PWD"` once, before any `cd`, and use its output. Use the `cwd` value from the context, in single quotes, for `<cwd>`, never `$PWD`: the shell can change directory during the command.
1. If `topic` in the context is empty, stop and tell the user to run `/llm-wiki:set-topic`. Let `W = <vault_path>/<topic>`.
2. Read `W/wiki/`. Build the `[[link]]` graph.
3. Handle:
   - Index drift, and missing MANDATORY section headers (the headers each type's template declares) -> AUTO-FIX (these are mechanical).
   - Dead links, orphan pages/concepts, contradictions (`> [!WARNING]`) -> REPORT.
   - Stale DERIVED concepts (a newer source appears to supersede a synthesized conclusion) -> FLAG and ASK the user; NEVER auto-update them.
   - Do NOT flag uncovered gaps in sources (those are fine).
4. Save a dated report to `W/outputs/reports/YYYY-MM-DD-lint.md` -- a sibling of `wiki/`, NOT inside it (`W/outputs/`, never `W/wiki/outputs/`). Reports must stay out of the `wiki/` graph/embedding scan; if you find prior reports under `wiki/`, they drifted -- do not follow them.
5. Log and commit: `llm-wiki log-commit '<cwd>' lint -- '<counts, e.g. 2 dead links, 1 orphan, 3 auto-fixed>'`. Put each free-text argument in single quotes and write each `'` in it as `'\''`. Do not edit `W/log.md` or run git yourself. Never push.
