---
description: List the coordination issues awaiting your side
argument-hint: [party]
---

Surface the open issues that your party must act on. Read-only: no writes, no
commit, and never act on them unprompted.

1. Resolve context: run `coordination-ledger context`. If `root` is empty, stop:
   no coordination ledger here.
2. Run `coordination-ledger check [--party <label>]`. With no `--party` it uses the
   cwd's party; at the root, pass one (from `parties`), or run
   `coordination-ledger list` to see every issue.
3. Report the rows. Do NOT open issue bodies unless the user wants detail on a
   specific one; do NOT act on them -- wait for the user to choose one and confirm
   before doing any work.
