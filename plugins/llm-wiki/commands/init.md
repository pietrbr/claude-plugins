---
description: Create a new wiki topic and bind the current directory to it
argument-hint: <topic>
---

Create a new wiki under the vault and bind the current directory to it.

1. Resolve context: run `llm-wiki context "$PWD"`. Note `templates_path`. If `vault_path` is empty, ask the user for a vault path and set it (`llm-wiki config-set vault_path "<path>"`).
2. Topic = `$ARGUMENTS` (ask if missing). Let `W = <vault_path>/<topic>`. If `W` already exists, abort and point to `/llm-wiki:remove`.
3. Scaffold:
   - `mkdir -p W/raw/documents W/raw/attachments W/wiki/queries W/outputs/reports`
   - `W/wiki/index.md` from `<templates_path>/index.md` (substitute the topic name).
   - `W/log.md` from `<templates_path>/log.md` (substitute the topic name).
   - `W/qmd.yml`:
     ```yaml
     collections:
       <topic>:
         path: ./wiki
         pattern: "**/*.md"
     ```
   - `W/.gitignore`: `.DS_Store`, `*.sqlite`, `*.sqlite-wal`, `*.sqlite-shm`.
   - `W/CLAUDE.md`: a THIN per-wiki schema. Include a one-paragraph domain description (ask or infer) and this pointer: "Page templates and conventions are provided by the llm-wiki plugin and injected by the resolution hook; topic-specific overrides, if any, go below." Do NOT inline templates.
4. Ensure the vault is a git repo (`git -C "<vault_path>" rev-parse --git-dir >/dev/null 2>&1 || git -C "<vault_path>" init`). Commit `init: <topic> wiki`. Never push.
5. Bind cwd: `llm-wiki topic-set "$PWD" "<topic>"`.
6. If `command -v qmd` succeeds: `qmd collection add "W/wiki" --name <topic> && qmd embed --collection <topic>`.
7. Print next steps: ingest a source with `/llm-wiki:ingest <path|url>`.
