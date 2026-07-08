---
description: Bind the current directory to an existing wiki topic
argument-hint: <topic>
---

Bind the current working directory to a wiki topic, so future commands run here
resolve to it (remembered across sessions).

1. Resolve context: run `llm-wiki-state context "$PWD"`. If `vault_path` is empty, tell the user to run `/llm-wiki:set-vault` first and stop.
2. Topic = `$ARGUMENTS`. If missing, list existing topics (`ls -1 "<vault_path>"`) and ask which one.
3. Verify it exists: `<vault_path>/<topic>/wiki` must exist. If not, tell the user to run `/llm-wiki:init <topic>` and stop.
4. Bind it: `llm-wiki-state topic-set "$PWD" "<topic>"`.
5. Confirm: "This directory is now bound to topic '<topic>'."
