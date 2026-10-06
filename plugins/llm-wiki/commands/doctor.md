---
description: Report llm-wiki environment and configuration
argument-hint: (no arguments)
allowed-tools: Bash(llm-wiki:*)
---

Run `llm-wiki doctor '<cwd>'`, where `<cwd>` is the `cwd` value from the injected context (or `"$PWD"` if there is none). Read-only: change nothing. Print its output
verbatim in a code block. Then explain each `MISSING` line and each `INVALID` or
`writable=NO` value in one sentence, with its fix. If nothing is missing, add
nothing.
