# coordination-ledger

A cross-repo **coordination ledger** for Claude Code: a lightweight, local issue
tracker that carries the subset of changes which must cross the boundary between
repos under a common parent (e.g. a paper and its codebase), plus their
reconciliation state.

It is an **outbox/inbox, not a changelog** -- git already records what each repo
did; the ledger carries only what must propagate, and whether it has. It is a
**local tracking artifact, not a knowledge base**: durable knowledge belongs in
the repos themselves or in a wiki. The ledger is committed locally and **never
pushed**.

## Model

```
<parent>/                 # coordination root: its OWN local git repo (never pushed)
  CLAUDE.md               # project prose + pointer (thin)
  index.json              # structured state: parties + issues (authoritative; numbers derived)
  issues/
    .gitkeep              # so the dir commits when empty
    0002-eta-anchoring.md # issue BODY (prose entries), headed ### code / ### paper
  .gitignore              # ignore-all + allowlist the coordination files
  evaluation/             # gitignored party repo (own repo) -- never references the ledger
  paper/                  # gitignored party repo (own repo) -- never references the ledger
```

- **Party** -- a registered repo, `(path, label)` in `index.json`, at any relative
  path under the root (a top-level repo, or one nested inside another party -- e.g.
  a submodule). `path` is stored relative (portable); the label is a short token
  descriptive of function/scope (`code`, `paper`) used on every surface: entry
  headings, the issue `actor`, and commit refs (`ref: code@<sha>`). Registered
  incrementally -- `init` seeds the first ones, `register` adds more.
- **Issue** -- metadata in `index.json` (number, author, actor, status, dates, a
  one-line `description`); the prose lives in `issues/NNNN-<slug>.md` (up to two
  entries, one per party).
- **Status** (in `index.json`) -- `open` (the `actor` must act) / `done`
  (propagated) / `divergent` (intentionally will not propagate). Open vs resolved
  is a view over the field, not a stored table.

**Zero footprint in the parties:** the party repos never reference the ledger --
not in their text (no issue numbers in commits/code/prose) and not in their
config. The commands resolve which party you are in structurally, by walking up to
the coordination root.

## Commands

| Command                                   | Does                                                                  |
| ----------------------------------------- | --------------------------------------------------------------------- |
| `/coordination-ledger:init`               | Set up a coordination ledger over the repos under the current dir.    |
| `/coordination-ledger:register <path>`    | Register an additional party (any relative path, incl. a submodule).  |
| `/coordination-ledger:open <description>` | Open a new cross-repo issue (author = your party; actor = the other). |
| `/coordination-ledger:reply <number>`     | Append your party's entry and set status (`done` / `divergent`).      |
| `/coordination-ledger:check [party]`      | List the open issues awaiting your party. Read-only.                  |

Every write is drafted by the agent and **approved by the user** before it lands.
The agent typically invokes these as part of normal work; you rarely type them.

## How it works

`bin/coordination-ledger` (Python, stdlib only) owns every `index.json` operation
and the structured parts of issue body files. It keeps **no machine-local state**
and runs **only when a command invokes it** -- there are no hooks. It finds the
coordination root by walking up to the nearest ancestor holding `index.json` +
`issues/`, maps the working directory to a party (deepest matching path wins, so
nested repos and submodules resolve to the most specific party), allocates issue
numbers, stamps `ref:` SHAs, writes the body files, and commits (never pushes).
Commands gather user-approved content, shell out to it, and read `conventions.md`
for the protocol.

## Splitting

Not a status -- a convention: if one request is really several units of work,
resolve the original `done` with a "superseded by ..." note and open the new
issues. See `references/conventions.md` for the exact form.
