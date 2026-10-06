---
description: List wiki topics, their size, and bound directories
argument-hint: (no arguments)
allowed-tools: Bash(llm-wiki:*)
---

Run `llm-wiki list '<cwd>'`, where `<cwd>` is the `cwd` value from the injected context (or `"$PWD"` if there is none). Print its output verbatim in a code block, with
nothing else. Read-only: change nothing.
