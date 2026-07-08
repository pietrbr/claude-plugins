---
description: Delete a wiki topic (git-recoverable; no confirmation)
argument-hint: <topic>
---

Delete a wiki topic. Deletions are git-recoverable, so do NOT ask for confirmation.

1. Resolve context for `vault_path` (`llm-wiki-state context "$PWD"`). Topic = `$ARGUMENTS` (required). Let `W = <vault_path>/<topic>`.
2. Print what will be deleted and the current recovery commit: `git -C "<vault_path>" rev-parse --short HEAD`.
3. Delete `W`. If `command -v qmd` succeeds: `qmd collection remove <topic>`.
4. Remove bindings: for each line in `llm-wiki-state topic-list` whose topic is `<topic>`, run `llm-wiki-state topic-unset "<dir>"`. NEVER touch the config `vault_path`.
5. Commit the deletion to the vault repo (`remove: <topic>`). Never push.
6. Confirm, and remind the user it is recoverable from the printed commit.
