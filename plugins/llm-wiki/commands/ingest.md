---
description: Save a source into the wiki's raw library, verbatim (does not compile)
argument-hint: <path|url>
---

Acquire a source and save it verbatim. Do NOT read its full content and do NOT
create wiki pages (that is `compile`). No prompts; this is the default behavior.

1. Resolve context: `llm-wiki-state context "$PWD"`. If `topic` is empty, stop and tell the user to run `/llm-wiki:set-topic`. Let `W = <vault_path>/<topic>`.
2. Source = `$ARGUMENTS` (a file path or URL).
3. Confirm existence WITHOUT reading full content:
   - File: `test -f "<path>"`; if missing, report and stop.
   - URL: proceed to step 5.
4. Classify + title cheaply (no full read):
   - Type by extension: `.pdf` -> paper; `.md`/`.markdown`/`.txt` -> peek `head -40` to pick article|transcript|conversation.
   - Title: first `#` heading or YAML `title:` in the head peek; else from the filename.
5. Save verbatim to `W/raw/articles/YYYY-MM-DD-<slug>.<ext>`:
   - File: `cp "<path>" "W/raw/articles/YYYY-MM-DD-<slug>.<ext>"`. NEVER read-and-rewrite (it corrupts PDFs/binaries). If the file already lives under `W/raw/`, skip the copy.
   - URL: WebFetch the content; save as `W/raw/articles/YYYY-MM-DD-<slug>.md`.
   - Disambiguate slug collisions (same date+slug) with a numeric suffix.
6. Write a sidecar `W/raw/articles/YYYY-MM-DD-<slug>.meta.md`:
   ```yaml
   ---
   date: YYYY-MM-DD
   source-type: <classification>
   source-url: <original URL or path>
   source-file: YYYY-MM-DD-<slug>.<ext>
   title: <extracted or inferred title>
   compiled: false
   ---
   ```
7. Append an ingest entry to `W/log.md`. Commit. Never push.
8. Stay silent on success (see the Output policy). Speak only for warnings,
   conflicts, or errors.
