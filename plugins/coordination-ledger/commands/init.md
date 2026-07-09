---
description: Set up a coordination ledger over the repos under this directory
argument-hint: (run from a common-ancestor dir over the repos)
---

Create a coordination ledger here -- a common-ancestor dir sitting on top of the
repos to coordinate. The program owns `index.json`; you gather approved content.

1. Resolve context: run `coordination-ledger context` and read the JSON it prints.
   If `root` is non-empty, a ledger already exists at or above here -- stop and
   point the user to it. Read the protocol at `conventions_path`.
2. Decide the initial parties (>= 2) with the user. A party is a repo to
   coordinate; for each pick `(path, label)`:
   - `path` = its location relative to this dir -- a top-level repo, or a nested
     one / submodule (e.g. `superproject/lib`). Candidates below here:
     `for d in */; do [ -e "$d.git" ] && echo "${d%/}"; done`.
   - `label` = a short token descriptive of function/scope (default: the path's
     last component), unique within the root.

   **Preview in chat before writing**: this directory's absolute path (the
   coordination root) and the chosen parties as a `| path | label |` table. Let
   the user edit paths/labels, then approve.

3. Scaffold, then register each party (the program writes and commits; it never
   touches the party repos):
   - `coordination-ledger init` -- writes `index.json`, `issues/.gitkeep`,
     `.gitignore`, `CLAUDE.md`, and a local git repo. It refuses (with context) if
     this dir already holds a ledger or sits inside another git repo.
   - `coordination-ledger register --path <path> --label <label>` for each party.
4. Report the registry. Point to `/coordination-ledger:open` to file the first
   issue and `/coordination-ledger:register` to add parties later.
