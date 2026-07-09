# coordination-ledger conventions (canonical)

Read by each coordination-ledger command before it acts. Govern every operation.
A root-level CLAUDE.md may add project vocabulary but not override the protocol.

## What the coordination ledger is (and is not)

- An OUTBOX/INBOX for changes that must cross the boundary between parties, plus
  their reconciliation state. NOT a changelog (git already has that).
- A LOCAL tracking artifact. NOT a knowledge base: durable/future-facing
  information belongs in the repos or a wiki, never in the coordination ledger.
- Every write is drafted by the agent and APPROVED by the user before landing.

## The program owns the structured state

- `bin/coordination-ledger` (Python) owns `index.json` and the structured parts of
  issue body files. Commands are thin wrappers: they gather approved content and
  shell out to it. NEVER hand-edit `index.json`; NEVER hand-format an issue's
  heading, `date:`, or `ref:` line -- the program writes those and commits.

## Parties

- A party is a repo that participates in coordination, recorded as `(path, label)`
  in `index.json` `parties`. `path` is the repo's location RELATIVE to the
  coordination root, at any depth: a top-level repo, or a repo nested inside another
  party (e.g. a submodule). `label` is one short token descriptive of
  function/scope (`code`, `paper`, `code-mc`), unique within the root.
- The label is the party's name on every surface: resolution (deepest matching path
  wins), entry headings (`### code`), the issue `actor`, and commit refs
  (`ref: code@<sha>`). Absolute paths are never stored -- the program computes them
  as `<root>/<path>`, so the ledger stays portable.
- Registered incrementally: `init` seeds the initial set (>= 2), `register` adds
  more over time.

## Issues and entries

- An issue is one cross-boundary thread. Its metadata lives in `index.json`
  `issues`: `number` (integer, global monotonic, immutable, never recycled),
  `slug` (kebab of the description, frozen at open -- the filename token),
  `author`, `actor`, `status`, `since`, `resolved`, and `description` (a short
  one-line summary; set at open, updated at close). `description` lives only in
  `index.json`.
- The issue's prose lives in the body file `issues/NNNN-<slug>.md`: a heading
  `# NNNN -- <slug>`, then up to two entries, one per party. Each entry is
  `### <label>`, then `- date: <YYYY-MM-DD>`, `- ref: <label>@<sha>` (the
  source-repo commit), then a body (orientation, not an implementation plan;
  ~half a page max).
- A new issue always takes the next free number (floored at max existing + 1). A
  reply appends the actor's entry into the same body file.

## Status (in index.json)

- `open` -- the `actor` must act.
- `done` -- propagated; the reply entry records the resolving commit.
- `divergent` -- the difference is intentional and will NOT propagate; a terminal
  reconciliation verdict, recorded so nobody later "fixes" it.
- Open vs resolved is a VIEW over the `status` field, not a stored table:
  `check`/`list` filter it. "Awaiting party X" = `status == open` and `actor == X`.

## Splitting an issue (a convention, not a status)

- If one incoming request is really several units of work: resolve the original
  `done` with a "superseded by NNNN-<slug>, MMMM-<slug>" note in the reply body,
  and open the new issues normally. Numbers are never recycled; history is in git.

## Three reference rules

1. Issues always resolve: `number` -> `issues/NNNN-<slug>.md`; the number is
   immutable and the slug is frozen at open, so a remembered pointer never dangles.
2. Cite issue numbers, never cache content: remember/cite a number (a pointer);
   re-read by number for current content. The coordination ledger is the single
   source of truth.
3. References go coordination-ledger -> repo only: the ledger points into repos by
   commit SHA (`ref:`). Repo commits, code, comments, and prose NEVER mention the
   coordination ledger. The coordination layer knows the repos; the repos do not
   know it exists -- not in their text and not in their config.

## Output policy (chat)

- Silent on routine bookkeeping (created/appended/committed). Speak only for
  deliverables (`check`/`list` output), warnings/contradictions, no-op notices, and
  errors (unregistered party, missing issue).

## Git

- The coordination root is its own local git repo that tracks ONLY the ledger files
  (`index.json`, `issues/`, `CLAUDE.md`, `.gitignore`) and gitignores everything
  else -- all party repos, wherever nested. It sits on top of the parties; it is
  NOT their superproject and never tracks them.
- The program commits after every write. NEVER push; no remote. Never touch or
  commit inside the party repos.
