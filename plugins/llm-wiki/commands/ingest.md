---
description: Save a source into the wiki's raw library, verbatim (does not compile)
argument-hint: <path|url> [--type <type>]
---

Acquire a source and save it verbatim. Do NOT read its full content and do NOT
create wiki pages (that is `compile`). Do not ask the user any questions.

0. Context: the prompt hook injected `vault_path`, `topic`, `templates_path`, and the conventions. If that context is missing (for example, a skill started this command), run `llm-wiki context --conventions "$PWD"` once, before any `cd`, and use its output. Use the `cwd` value from the context, in single quotes, for `<cwd>`, never `$PWD`: the shell can change directory during the command.
1. If `topic` in the context is empty, stop and tell the user to run `/llm-wiki:set-topic`.
2. Parse `$ARGUMENTS`: the source is the file path or URL. An optional `--type <t>` sets the source-type. Without it, classify the source in step 3.
3. Classify + title cheaply (no full read):
   - Types (provenance only, see conventions): `paper` (peer-reviewed/scholarly), `article` (informal external writing, incl. product docs/datasheets/manuals), `standard` (normative standards-body doc: 3GPP TS/TR, RFC, IEEE, ETSI, O-RAN), `conversation` (transcript of talk/interview/meeting/chat), `user-note` (the user's own authored note). For paper vs article, ask "scholarly-reviewed?": a preprint is a `paper`, and a blog, whitepaper, or product doc is an `article`.
   - Type: if `--type <t>` was given, use it. Else peek only at the start of the file: `head -40` for text, or the first page for a PDF. Pick the best-fitting type from that peek. Do not read further. If the type is ambiguous, take the best guess and do not ask the user.
   - Title: the first `#` heading or YAML `title:` in the peek (the first page for a PDF). If there is neither, derive it from the filename.
   - Slug: a short kebab-case name, for example `1202.6501-lee-huang-optdensity`. It is optional for a file: if you omit it, the program uses the file name. It is required for a URL.
4. URL only: WebFetch the content and write it to a new temp file `<tmp>/<slug>.md`. Use that file as the path in step 5, and the URL as `--uri`. Delete the temp file after step 5.
5. Save, log, and commit in one call. Put each free-text value in single quotes and write each `'` in it as `'\''`:
   ```
   llm-wiki ingest '<cwd>' --type <t> --title='<title>' [--uri='<url or DOI>'] [--slug='<slug>'] -- '<path>'
   ```
   The program copies the file byte for byte to `raw/documents/YYYY-MM-DD-<slug>.<ext>`. On a name collision, it adds a numeric suffix. Then it writes the `.meta.md` sidecar with `compiled: false`, logs, and commits. Without `--uri`, it records the original path as `source-uri`. Do NOT copy files, write the sidecar, edit `log.md`, or run git yourself.
6. Stay silent on success (see the Output policy). Speak only for warnings,
   conflicts, or errors, and quote the program's error verbatim.
