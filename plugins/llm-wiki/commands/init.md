---
description: Create a new wiki topic and bind the current directory to it
argument-hint: <topic> ["<one-paragraph domain description>"]
---

Create a new wiki under the vault and bind the current directory to it.

1. Topic = the first word of `$ARGUMENTS`. If it is missing, ask for it.
2. Description: one paragraph about the domain of the wiki. Take it from the rest of `$ARGUMENTS`, or infer it from the conversation. If you cannot infer it, ask the user.
3. Create, commit, bind, and index in one call. Put each value in single quotes and write each `'` in it as `'\''`:
   ```
   llm-wiki init --description='<description>' -- "$PWD" '<topic>'
   ```
   The program makes the folders, `index.md`, `log.md`, `qmd.yml`, `.gitignore`, and `CLAUDE.md`, commits, binds the current directory, and adds the qmd collection. Do NOT create files or run git yourself. If it fails, quote its error verbatim and stop.
4. Print its output. The last line names the next step.
