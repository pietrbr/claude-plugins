---
description: Report llm-wiki environment and configuration
argument-hint: (no arguments)
---
Report the environment. Read-only; change nothing. Print a concise checklist using
`OK` / `MISSING` (ASCII only) with fix hints.

1. Tools: `command -v qmd` (optional - search falls back to index.md if MISSING; hint: `npm i -g @tobilu/qmd`), `command -v git`.
2. Config: `llm-wiki-state config-get vault_path`; report whether that directory exists and is a git repo. If unset, hint `/llm-wiki:set-vault <path>`.
3. Current binding: `llm-wiki-state context "$PWD"` (vault_path, resolved topic, templates_path). If topic is empty, hint `/llm-wiki:set-topic <name>`.
4. Topic map: `llm-wiki-state topic-list`.
5. Print the checklist with OK/MISSING per item and the relevant hints.
