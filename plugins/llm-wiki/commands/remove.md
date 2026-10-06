---
description: Delete wiki topics (git-recoverable; no confirmation)
argument-hint: <topic> [<topic> ...]
---

The resolution hook answers this command itself, without a model turn. If you
see this text, the hook did not run. Run this command, with the arguments inside
single quotes, and write each `'` in them as `'\''`:

```
llm-wiki run remove "$PWD" '$ARGUMENTS'
```

Print its output verbatim, in a code block, with nothing else.
