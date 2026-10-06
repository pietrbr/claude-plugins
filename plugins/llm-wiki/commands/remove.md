---
description: Delete wiki topics (git-recoverable; no confirmation)
argument-hint: <topic> [<topic> ...]
allowed-tools: Bash(llm-wiki:*)
---

Topics = the words of `$ARGUMENTS`. If there are none, ask the user. If the user typed `/llm-wiki:remove` in this prompt, do not ask for confirmation, because the program refuses unsafe deletions and prints a recovery command. If anything else started this command (for example, the wiki skill), name the topics and ask the user to confirm the deletion first. Run this command, with one quoted argument per topic. Put each argument in single quotes and write each `'` in it as `'\''`:

```
llm-wiki remove -- '<topic>' ['<topic>' ...]
```

Do not do any part of this work yourself. Print the program's output verbatim in
a code block. If it fails, print its error verbatim and add one sentence with the fix.
