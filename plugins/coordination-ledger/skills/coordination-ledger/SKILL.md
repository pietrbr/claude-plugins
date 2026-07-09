---
name: coordination-ledger
description: >-
  Cross-repo coordination ledger -- a local issue tracker that carries changes
  which must cross the boundary between repos under a common parent. Use when
  work in one repo affects another repo under the same root, when the user
  mentions "the ledger" / "coordination ledger", or
  to open/reply-to/check cross-repo issues. Routes to the coordination-ledger
  commands.
---

# Coordination Ledger

A coordination layer that sits on top of the repos under a common parent.
Outbox/inbox,
not a changelog: git records what each repo did; the coordination ledger carries
only what must cross the boundary, plus whether it has. A LOCAL tracking
artifact, NOT a knowledge base -- durable knowledge lives in the repos or a wiki,
never here.

This skill ROUTES and tells the agent WHEN to act. Each operation is its own
command; the command shells out to the `coordination-ledger` program (which owns
`index.json`) and reads the conventions itself (there are no hooks). Do NOT
perform operations from here.

## When to act (the agent drives; the user approves content)

- Doing work in a repo that changes something another party must know about
  -> propose `/coordination-ledger:open`.
- Starting/among work in a party repo -> `/coordination-ledger:check` for items
  awaiting your side; remind the user, do NOT act on them unprompted.
- Resolving an owed item -> `/coordination-ledger:reply`.
- No coordination root exists but you keep reaching into another repo under the
  same root -> suggest `/coordination-ledger:init` ONCE, then drop it.
- Coordinating a repo that isn't a registered party yet (e.g. a submodule of an
  existing party) -> offer `/coordination-ledger:register`.

Every write to the coordination ledger is drafted by the agent and APPROVED by
the user before it lands.

## Routing

| Intent                                      | Command                                   |
| ------------------------------------------- | ----------------------------------------- |
| Set up a coordination ledger over the repos | `/coordination-ledger:init`               |
| Register an additional party                | `/coordination-ledger:register <path>`    |
| Open a new cross-repo issue                 | `/coordination-ledger:open <description>` |
| Reply to / resolve an issue                 | `/coordination-ledger:reply <number>`     |
| List issues awaiting your side              | `/coordination-ledger:check [party]`      |

## Core concepts (for routing, not execution)

- **Coordination root**: a common-ancestor dir holding `index.json` + `issues/`;
  its own local git repo (never pushed) that tracks only the ledger and gitignores
  the party repos. It sits on top of the parties -- not their superproject.
- **Party**: a registered repo = `(path, label)`, at any relative path under the
  root (a top-level repo, or one nested inside another party -- e.g. a submodule).
  Registered with a meaningful label -- one short token descriptive of the repo's
  function or scope (e.g. `code`, `paper`) -- used everywhere the party is named.
  Registered incrementally (`init`, then `register`).
- **Issue**: metadata in `index.json` (number, author, actor, `status` of
  `open`/`done`/`divergent`, a one-line `description`); prose in the body file
  `issues/NNNN-<slug>.md` (up to two entries, headed by party label).

The full protocol (parties, issues/entries, statuses, splitting, the three
reference rules) is in the plugin's `references/conventions.md`, which each
command reads (from `conventions_path`) when it runs.
