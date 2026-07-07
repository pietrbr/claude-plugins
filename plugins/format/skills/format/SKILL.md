---
name: format
description: Format files. Use when the user asks to format, reformat, pretty-print, or clean up the formatting of files, a directory, the repo, or files of a given type. Accepts targets — specific files, directories, globs, or an extension filter — and defaults to git-changed files when none is given.
---

# Format files

Run the shared formatter script. It is the single source of truth for which
tool formats which extension and with what args (mirrors a conform.nvim + mason
setup). Do **not** reimplement formatting logic here — just translate the user's
request into a script invocation.

## Command

```bash
claude-format.sh [options] [paths...]
```

(The script ships in this plugin's `bin/`, which Claude Code adds to `PATH`, so
invoke it by its bare name — no path needed.)

- `paths` — files and/or directories (dirs are walked recursively). Shell globs
  work (`src/**/*.py`). With **no paths**, it formats git-changed files in the
  current repo.
- `--ext LIST` — comma-separated extensions to include, e.g. `--ext py,md,toml`.
  Filters the collected set.
- `--all` — format ALL supported files under the given dirs (or cwd).
- `--changed` — format git-changed files (the default with no paths).
- `--dry-run` — list the files that would be formatted; run nothing.

## How to map the user's request

| User says                                                       | Run                                                      |
| --------------------------------------------------------------- | -------------------------------------------------------- |
| "format the files you edited" / "format my changes" / no target | `claude-format.sh` (git-changed default)                 |
| "format `foo.py` and `bar.md`"                                  | `claude-format.sh foo.py bar.md`                         |
| "format the `src/` dir"                                         | `claude-format.sh src/`                                  |
| "format all python files"                                       | `claude-format.sh --ext py --all`                        |
| "format the markdown in `docs/`"                                | `claude-format.sh --ext md docs/` (txt-style: trim only) |
| "format everything"                                             | `claude-format.sh --all`                                 |
| "what would formatting touch?"                                  | `claude-format.sh --dry-run <target>`                    |

If the user passed arguments to the skill invocation, forward them as-is unless
they're clearly a natural-language description, in which case translate per the
table above.

## Behavior notes (surface these only if relevant)

- Python runs the full chain: `isort` -> `autopep8` -> `ruff check --fix`
  (lint autofix, never fails the run) -> `ruff format`.
- Repo-local config wins: prettier (`.prettierrc`), ruff (`[tool.ruff]` /
  `ruff.toml`), stylua (`stylua.toml`), shfmt (`.editorconfig`), taplo
  (`.taplo.toml`) are auto-discovered. The LazyVim defaults (e.g. shfmt `-i 2`,
  stylua 2-space/col-120, ruff/autopep8 line-length 100) apply only as fallback.
- There is **no Dockerfile formatter** in this stack; Dockerfiles are left
  untouched.
- Markdown (`.md`/`.markdown`/`.mdx`) is treated like `.txt` — only
  trailing-whitespace trimming + a final newline. No prettier (it mangled
  frontmatter, tables, lists, and `[[wikilinks]]`), so structure is preserved.
- `.txt` only gets trailing-whitespace trimming + a final newline.
- Tools resolve from `~/.local/share/nvim/mason/bin` first, then `PATH`.
  Missing tools are reported as `skip` (never a failure) and summarized as a
  `WARNING` at the end listing which formatters to install. Surface that warning
  to the user so they know coverage was incomplete.

## After running

Report the per-file results and the final `Formatted N, skipped N, failed N`
summary. If the script reformatted files you had already read in this
conversation, remember they are now stale on disk — re-read before editing them
again (the Edit tool will otherwise reject the edit).
