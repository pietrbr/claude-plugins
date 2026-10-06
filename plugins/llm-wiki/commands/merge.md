---
description: Merge one wiki topic into another (dedupe sources, reconcile pages)
argument-hint: <from> <into>
---

Merge topic `<from>` into topic `<into>`, then delete `<from>`. The result must
read as one wiki compiled from the union of both source sets. Git can recover the
merge, so do NOT ask for confirmation. The program does every move that needs no
judgment. You decide possible duplicates and reconcile colliding pages under the
injected conventions. The raw source stays the only ground truth. Never settle a
conflict by trusting either wiki's summary.

Put each argument in single quotes and write each `'` in it as `'\''`. Do not move,
delete, or rename files with your own shell commands, except where a step says so.

0. Context: the prompt hook injected `vault_path` and the conventions. If that context is missing (for example, a skill started this command), run `llm-wiki context --conventions "$PWD"` and use its output.
1. Parse `$ARGUMENTS` as `<from> <into>`. Both are required. Let `F = <vault_path>/<from>` and `I = <vault_path>/<into>`. Read `<templates_path>/source-summary.md`, `concept.md`, and `person.md`.
2. Scan: run `llm-wiki merge-scan '<from>' '<into>'`. If it fails, report its error and stop. Look at each `raw` row with status `possible-duplicate`. Compare `head -40` (the first page for a PDF) of the `F` file and its `match` in `I`:
   - The same document: mark it `--same <file>`.
   - Different versions of one work (preprint and published, revisions, a page fetched on two dates): mark it `--distinct <file>`.
3. Move: run `llm-wiki merge-move '<from>' '<into>' [--same '<file>']... [--distinct '<file>']...`. If either topic holds uncommitted changes, it refuses. It moves new sources, deletes duplicate copies, renames clashing names, retargets `source-file` in the summaries, moves attachments and non-colliding pages, and prints a JSON state. Its `to_reconcile` list is your work list.
4. Reconcile each `to_reconcile` pair. The `from` page is in `F/wiki/` and the `into` page is in `I/wiki/`. First decide every `same-name` pair: a homonym (rule b) or the same subject (rule c). Do all homonym moves before you merge any text, and write each link to a renamed homonym with its new name. For each other pair, write the result into the `into` page, then delete the `from` page with `rm`. Never concatenate the two pages. For many pairs, dispatch one subagent per pair with these rules:
   a. `kind: same-source` (two summaries of one source): dispatch a wiki-blind VERIFIER subagent. Give it ONLY the raw file in `I/raw/documents/`, both `## Overview` sections, and the template. It compares each claim with the raw source. It reports the more faithful Overview and the wrong claims. Keep the more faithful Overview. Fix each flagged error in place with `[corrected YYYY-MM-DD per merge verification]`. If neither Overview is faithful, run the compile PASS 1 neutral read and use its Overview. Keep every `## Deep read` section from both pages. If two sections have the same frame, give both to the same VERIFIER and keep the better one. Join the two `## Entities` lists.
   b. `kind: same-name`, different subject (a homonym): move the `from` page with `mv` to `I/wiki/<new-name>.md`, with a clearer kebab-case name. Remember `<old-name>=<new-name>` for step 6.
   c. `kind: same-name`, same subject (concept, person, or query): rebuild one page from its template. Join `tags` and `informed-by`, and keep the earliest `date`. Merge the body claim by claim and keep every citation. If two claims disagree, re-read the cited raw sources. Keep the claim that the source supports. If the sources support both, add `> [!WARNING] Contradiction`.
5. Integrate:
   - Backlinks: run `llm-wiki backlinks '<cwd>' --topic '<into>' <pages from F and reconciled pages>`, and add the missing `[[wikilinks]]`.
   - Index: rebuild `I/wiki/index.md` from both indexes. Merge sections by domain, with one line per page. Apply the renames and remove the dropped duplicates. Update `Last updated`.
   - `I/CLAUDE.md`: widen the domain paragraph to cover `<from>`. Append the topic-specific overrides from `F/CLAUDE.md`. Report each override that conflicts with an override in `I`.
6. Finish: run `llm-wiki merge-finish '<from>' '<into>' [--rename '<old>=<new>']... --summary='<one-line summary>'`. It refuses while pages remain in `F/wiki/`. It rewrites links to replaced summaries and renamed pages. It moves the reports and other files, and it appends the `F` log entries and a merge entry to `I/log.md`. Then it deletes `F`, rebinds the directories of `<from>`, updates qmd, and commits.
7. Lint: run `llm-wiki lint-scan '<cwd>' --topic '<into>'`. Fix the dead links that the merge created. Leave the other findings to `/llm-wiki:lint`. If you fixed anything, run `llm-wiki log-commit` from a directory bound to `<into>`, or tell the user that the fixes are uncommitted.
8. Report the counts from `merge-finish`, the contradictions flagged, the rebound directories, and its recovery command.
