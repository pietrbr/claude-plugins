---
description: Save a source into the wiki's raw library, verbatim (does not compile)
argument-hint: <path|url> [--type <type>]
---

Acquire a source and save it verbatim. Do NOT read its full content and do NOT
create wiki pages (that is `compile`). No prompts; this is the default behavior.

1. Resolve context: `llm-wiki context "$PWD"`. If `topic` is empty, stop and tell the user to run `/llm-wiki:set-topic`. Let `W = <vault_path>/<topic>`.
2. Parse `$ARGUMENTS`: the source is the file path or URL; an optional `--type <t>` sets the source-type (else auto-classify in step 4).
3. Confirm existence WITHOUT reading full content:
   - File: `test -f "<path>"`; if missing, report and stop.
   - URL: proceed to step 5.
4. Classify + title cheaply (no full read):
   - Types (provenance only; see conventions): `paper` (peer-reviewed/scholarly), `article` (informal external writing, incl. product docs/datasheets/manuals), `standard` (normative standards-body doc: 3GPP TS/TR, RFC, IEEE, ETSI, O-RAN), `conversation` (transcript of talk/interview/meeting/chat), `user-note` (the user's own authored note). paper vs article: "scholarly-reviewed?" -- preprint=`paper`, blog/whitepaper/product docs=`article`.
   - Type: if `--type <t>` was given, use it. Else peek only the start of the file -- `head -40` for text, or the first page for a PDF -- and pick the best-fitting type from that peek. Do not read further; never ask the user when ambiguous -- take the best guess.
   - Title: first `#` heading or YAML `title:` in the peek (first page for a PDF); else from the filename.
5. Save verbatim to `W/raw/documents/YYYY-MM-DD-<slug>.<ext>`:
   - File: `cp "<path>" "W/raw/documents/YYYY-MM-DD-<slug>.<ext>"`. NEVER read-and-rewrite (it corrupts PDFs/binaries). If the file already lives under `W/raw/`, skip the copy.
   - URL: WebFetch the content; save as `W/raw/documents/YYYY-MM-DD-<slug>.md`.
   - Disambiguate slug collisions (same date+slug) with a numeric suffix.
6. Write a sidecar `W/raw/documents/YYYY-MM-DD-<slug>.meta.md`:
   ```yaml
   ---
   date: YYYY-MM-DD
   source-type: <paper|article|standard|conversation|user-note>
   source-uri: <canonical external URL/DOI, or the original path it was ingested from; leave empty if neither -- NEVER a vault-internal raw/ path (that is source-file's job)>
   source-file: YYYY-MM-DD-<slug>.<ext>
   title: <extracted or inferred title>
   compiled: false
   ---
   ```
7. Append an ingest entry to `W/log.md`. Commit. Never push.
8. Stay silent on success (see the Output policy). Speak only for warnings,
   conflicts, or errors.
