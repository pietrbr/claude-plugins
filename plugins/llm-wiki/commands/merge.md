---
description: Merge one wiki topic into another (dedupe sources, reconcile pages)
argument-hint: <from> <into>
---

Merge topic `<from>` into topic `<into>`, then delete `<from>`. The result must
read as one wiki compiled from the union of both source sets. Git can recover the
merge, so do NOT ask for confirmation. Resolve every collision yourself under the
injected conventions. The raw source stays the only ground truth. Never settle a
conflict by trusting either wiki's summary.

1. Resolve context: `llm-wiki context "$PWD"`. Parse `$ARGUMENTS` as `<from> <into>`. Both are required. Let `F = <vault_path>/<from>` and `I = <vault_path>/<into>`. Read `<templates_path>/source-summary.md`, `concept.md`, and `person.md`.
2. Guard: `git -C "<vault_path>" status --porcelain -- "<from>" "<into>"` must print nothing. If it prints anything, stop and tell the user to commit or discard first. Record the recovery commit: `git -C "<vault_path>" rev-parse --short HEAD`.
3. Inventory: run `llm-wiki merge-scan "<from>" "<into>"`. If it exits non-zero, report its error and stop. This output is the work list. Do not re-derive it.
   - `raw`: each `F` source with a `status` against `I`: `new`, `duplicate` (identical bytes), or `possible-duplicate` (same `source-uri` or same title, different bytes). A row with a `match` also gives `match_sidecar` and `match_compiled`. `name_clash` marks a file or sidecar name that already exists in `I/raw/documents/`.
   - `attachments`: each `F` attachment as `new`, `identical`, or `name-clash`.
   - `pages_new`, and `pages_colliding` as `{from, into}` pairs with the same file stem. Wikilinks resolve by stem, so a pair in different subfolders still collides.
   - `reports_colliding`: `F` lint reports whose names exist in `I`.
   - `unhandled`: other `F` files that no step below moves.
4. Raw sources. Move files with `git mv`. Never rewrite a raw file. You can edit sidecar fields.
   - `possible-duplicate`: compare `head -40` (the first page for a PDF) of both files. If both are the same document, treat the row as `duplicate`. Different versions of one work (preprint and published, revisions, a page fetched on two dates) are distinct sources: treat the row as `new`.
   - `new`: move the file and its sidecar to `I/raw/documents/`. If `name_clash` is true, add a numeric suffix (`-2`) to the stem of both, as ingest does. Then update `source-file` in the moved sidecar and in the `F` summary page.
   - `duplicate`: keep the `I` copy. Run `git rm` on the `F` file and its sidecar. Fill empty fields of `match_sidecar` (`source-uri`, `title`) from the `F` sidecar. Set `source-file` in the `F` summary to the `match` file. If the `F` row is compiled, set `compiled: true` in `match_sidecar`.
   - `attachments`: move `new` files to `I/raw/attachments/`. Run `git rm` on `identical` files. Move each `name-clash` file with a numeric suffix, and rewrite its references in the `F` pages.
5. Wiki pages. Find the summary of a source with `grep -rl "^source-file: <file>" <topic>/wiki/`. After step 4, a duplicate source can have two summaries with different names. Add each such pair to `pages_colliding`, named after the `I` summary. Move every other page in `pages_new` with `git mv` to the same path under `I/wiki/`. Reconcile each colliding pair into the `into` page. Never concatenate the two pages. For many pairs, dispatch one subagent per pair, with these rules:
   a. Two summaries of one source: dispatch a wiki-blind VERIFIER subagent. Give it ONLY the raw file, both `## Overview` sections, and the template. It compares each claim with the raw source. It reports the more faithful Overview and the wrong claims. Keep the more faithful Overview. Fix each flagged error in place with `[corrected YYYY-MM-DD per merge verification]`. If neither Overview is faithful, run the compile PASS 1 neutral read and use its Overview. Keep every `## Deep read` section from both pages. If two sections have the same frame, give both to the same VERIFIER and keep the better one. Join the two `## Entities` lists.
   b. Same stem, different subject (a homonym): keep the `I` page. Rename the `F` page to a clearer kebab-case name.
   c. Same subject (concept, person, or query): rebuild one page from its template. Join `tags` and `informed-by`, and keep the earliest `date`. Merge the body claim by claim and keep every citation. If two claims disagree, re-read the cited raw sources. Keep the claim that the source supports. If the sources support both, add `> [!WARNING] Contradiction`.
   d. Links: in every page from `F`, rewrite each link to a page renamed in (b). Also rewrite each link to an `F` summary that was merged into an `I` summary with a different name.
6. Cross-references: run the compile backlink audit in both directions, between pages from `F` and the existing `I` pages. Then list each `[[target]]` with no `target.md` under `I/wiki/`. Fix the dead links that the merge created. Leave the other dead links to lint.
7. Index: rebuild `I/wiki/index.md` from both indexes. Merge sections by domain, with one line per page. Apply the renames and remove the dropped duplicates. Update `Last updated`.
8. Other files:
   - Move `F/outputs/reports/*` to `I/outputs/reports/`. Add the prefix `<from>-` to each name in `reports_colliding`.
   - Move each `unhandled` file to the same relative path under `I`. If that path exists, add the prefix `<from>-` to the file name.
   - `I/CLAUDE.md`: widen the domain paragraph to cover `<from>`. Append the topic-specific overrides from `F/CLAUDE.md`. Report each override that conflicts with an override in `I`.
   - `I/log.md`: append the `F` log entries verbatim, which are all lines after its header comment. Then append `## [YYYY-MM-DD] merge | <from> into <into>` with a one-line count summary, so the merge is the last entry.
9. Remove `F`: run `git rm -r` on its remaining tracked files, then delete the directory. Rebind: for each line of `llm-wiki topic-list` with topic `<from>`, run `llm-wiki topic-set "<dir>" "<into>"`. If `command -v qmd` succeeds, run `qmd collection remove <from>`.
10. Commit to the vault repo (`merge: <from> into <into>`). Never push. If `command -v qmd` succeeds, run `qmd embed --collection <into>`.
11. Report the counts: sources moved, deduplicated, and renamed. Pages moved, reconciled, renamed, and recompiled. Also report the contradictions flagged, the rebound directories, and the recovery commit.
