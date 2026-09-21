---
description: Report and fix comment slop on the changed lines (or a given target)
argument-hint: [paths...] [--all] [--since REF]
---

De-slop comments: run the detector, then fix what it found. The detector never
edits a file -- the edits in step 3 are yours.

1. Run it. With no argument, it scopes to lines changed since `HEAD`:

   ```bash
   comment-deslop-hook.sh                      # git-changed lines in the cwd's repo
   comment-deslop-hook.sh src/ --all           # every line under src/
   comment-deslop-hook.sh --since main app.py  # changed since main
   ```

   Forward the user's arguments as given. `--all` is required to sweep committed
   code: without it a file with no uncommitted changes reports nothing.

2. Read each flagged comment **with its surrounding code** before touching it.
   The detector reports shape; the code tells you what the deletion costs.

3. Fix by rule:

   | rule                                        | fix                                                                              |
   | ------------------------------------------- | -------------------------------------------------------------------------------- |
   | `restatement`, `bare-identifier`            | delete. If the line needed the gloss, rename the identifier instead.             |
   | `flow-narration`, `conditional-narration`   | delete. If the branch is hard to follow, extract it into a named function.       |
   | `history`                                   | delete. The fact belongs in the commit message -- offer to put it there.         |
   | `process-leak`                              | delete. Task and plan numbers do not survive the branch.                         |
   | `benchmark`                                 | delete the number. Keep a limit only if the code must satisfy it.                |
   | `reference`                                 | delete, or replace with a tracked path, or cite the spec by name/number/DOI.     |
   | `step-marker`, `narrative`                  | delete.                                                                          |
   | `verbose`                                   | cut to one line, or move the prose to the module docstring or the docs.          |
   | `redundant-docstring`                       | delete it, or replace it with the contract (arguments, returns, errors raised).  |
   | `budget`                                    | delete the weakest comment, or split the function so each part explains itself.  |
   | `density`                                   | delete the narration; keep at most the one comment that carries a constraint.    |

4. Delete the flagged comments. The checks already spare the ones that carry a
   constraint, a spec reference or a reason, so do not re-open that question. If
   one genuinely must stay, report it as a gap in the allowlist rather than
   keeping it quietly.

5. If the report has a `comment-deslop advisory:` block, **repeat it to the user
   verbatim and stop there**. Those rules are excluded by design; do not fix them,
   do not delete the comments, and do not argue for or against them. Add
   `--advisory all` to include the high-recall `unreviewed` sweep, or
   `--no-advisory` to drop the block.

6. Re-run the detector on the files you touched and report the remaining count.
   Never re-add a comment you just deleted.

## `--llm`

Always run the triage pass as well, after the report:

```bash
comment-deslop-hook.sh --all --llm <paths>
```

It prints `{"candidates": [{file, line, comment, code}]}` -- the short comments no
rule matched, each with its adjacent code line. Judge each one **yourself**; the
engine makes no model call. For each candidate, ask only:

- Does the comment state something the code cannot show -- an external
  constraint, a spec reference, an invariant the types do not carry? Keep it.
- Does it restate, narrate, or decorate the code? Propose deleting it.
- Cannot tell from the line alone? Read the surrounding function, then answer.

Report a verdict per candidate in one line each and propose the deletions as a
group. Do not delete anything before the user agrees: these verdicts are yours,
not the engine's, and they are not reproducible.

Rule ids can be narrowed with `--rules` / `--no-rules`; `comment-deslop doctor`
reports whether the tree-sitter rules are active, and `doctor --install` creates
the parser venv.
