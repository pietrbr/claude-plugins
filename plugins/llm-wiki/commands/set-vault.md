---
description: Set the llm-wiki vault directory (where all topics live)
argument-hint: <path>
---
Set the vault path for this machine. Argument: `$ARGUMENTS` (a directory path).

1. Expand the path (resolve `~`). If no argument was given, ask the user for the vault path.
2. Create it if needed: `mkdir -p "<path>"`.
3. Save it: `llm-wiki-state config-set vault_path "<path>"`.
4. Ensure it is a git repo: `git -C "<path>" rev-parse --git-dir >/dev/null 2>&1 || git -C "<path>" init`.
5. Confirm: "Vault set to <path>."
