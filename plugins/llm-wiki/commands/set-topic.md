---
description: Bind the current directory to an existing wiki topic
argument-hint: <topic>
allowed-tools: Bash(llm-wiki:*)
---

Topic = `$ARGUMENTS`. If it is missing, run `llm-wiki list '<cwd>'`, show the topics, and ask which one. Then run this command. Put each argument in single quotes and write each `'` in it as `'\''`:

```
llm-wiki set-topic -- '<cwd>' '<topic>'
```

`<cwd>` is the `cwd` value from the injected context, in single quotes. If there is no injected context, use `"$PWD"`.

Do not do any part of this work yourself. Print the program's output verbatim in
a code block. If it fails, print its error verbatim and add one sentence with the fix.
