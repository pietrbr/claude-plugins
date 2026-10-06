---
description: Set the llm-wiki vault directory (where all topics live)
argument-hint: <path>
allowed-tools: Bash(llm-wiki:*)
---

Vault path = `$ARGUMENTS`. If it is missing, ask the user for it. Then run this command. Put each argument in single quotes and write each `'` in it as `'\''`:

```
llm-wiki set-vault -- '<cwd>' '<path>'
```

`<cwd>` is the `cwd` value from the injected context, in single quotes. If there is no injected context, use `"$PWD"`.

Do not do any part of this work yourself. Print the program's output verbatim in
a code block. If it fails, print its error verbatim and add one sentence with the fix.
