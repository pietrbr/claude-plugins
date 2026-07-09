---
description: Register an additional party in the coordination ledger
argument-hint: <path> [label]
---

Add a party to an existing ledger. `index.json` is the only place parties live,
and the program writes it. User-approved.

1. Resolve context: run `coordination-ledger context`. If `root` is empty, stop:
   tell the user to run `/coordination-ledger:init` first. Read the protocol at
   `conventions_path`.
2. `path` = first argument: the repo's location relative to `root` (may be nested,
   e.g. a submodule like `superproject/lib`). `label` = second argument, else the
   path's last component. Ask if `path` is missing.
3. **Preview in chat before writing**: the `| path | label |` row to add. Let the
   user edit, then approve.
4. `coordination-ledger register --path <path> [--label <label>]` -- it validates
   the path is a git repo/submodule, rejects a duplicate path or label, appends the
   party to `index.json`, and commits. Sessions under `root/<path>` then resolve to
   this party.
