# llm-wiki

A Claude Code plugin that builds persistent, compounding knowledge bases inside an
Obsidian vault using Andrej Karpathy's LLM Wiki pattern. You curate sources and ask
questions; the LLM reads raw material, writes cross-linked wiki pages, files query
answers back, and lints for gaps -- all from your Claude Code session.

The original pattern is vendored verbatim at [`KARPATHY-LLM-WIKI.md`](./KARPATHY-LLM-WIKI.md).

## How it works

- **Per-operation commands.** Each operation is its own slash command
  (`/llm-wiki:ingest`, `/llm-wiki:compile`, ...). There is also a thin `wiki` skill
  that routes natural-language requests ("add this to my wiki") to the right command.
- **Command-driven only.** The plugin is designed to be used through its commands and
  skill. Ad-hoc free-form chat _inside_ the vault is not a supported access path --
  the commands inject the conventions and resolve the active wiki for you; raw chat
  does not.
- **Deterministic state.** A small CLI (`bin/llm-wiki`) and two hooks resolve
  the vault path and active topic and inject them into context, so commands never
  guess where you are.
- **Hook-answered commands.** `list`, `set-vault`, `set-topic`, and `remove` need no
  judgment, so the prompt hook runs them in the CLI and shows the result without a
  model turn. The model does not see that output. `doctor` runs the CLI report inside
  its prompt, so the model sees it and can discuss it.

## Install

```
/plugin marketplace add <this-repo>
/plugin install llm-wiki@pietro-marketplace
```

### Prerequisites

- **Git** -- the vault is a git repo; the plugin auto-commits (never pushes). Set
  `git config --global user.name` / `user.email`.
- **qmd (optional)** -- hybrid BM25 + vector search over wiki pages. Without it,
  search falls back to `index.md`, which is fine for small/medium wikis. Install with:
  ```
  npm i -g @tobilu/qmd
  ```
  (qmd is a Node package, so this needs Node.) The SessionStart hook warns once if
  qmd is missing and stays silent once it is present.

There is no bundled dependency install and **marp is not used**.

## Quick start

```
/llm-wiki:set-vault ~/Documents/LLM-wiki     # once per machine
/llm-wiki:init my-topic                       # create a wiki, binds this directory
/llm-wiki:ingest ~/papers/some-paper.pdf      # save a source verbatim
/llm-wiki:compile                             # turn raw sources into wiki pages
/llm-wiki:query "what does X say about Y?"     # ask, with cited answer, filed back
/llm-wiki:lint                                # health-check
```

Type `/llm-wiki:` and the menu filters to all commands with their argument hints.

## Commands

| Command                        | What it does                                                 |
| ------------------------------ | ------------------------------------------------------------ |
| `/llm-wiki:set-vault <path>`   | Set where all wikis live (machine-local, once).              |
| `/llm-wiki:init <topic>`       | Create a topic and bind the current directory to it.         |
| `/llm-wiki:set-topic <topic>`  | Bind the current directory to an existing topic.             |
| `/llm-wiki:list`               | List topics, their size, and bound directories (instant).    |
| `/llm-wiki:ingest <path\|url>` | Save a source to `raw/` verbatim (PDFs preserved). No pages. |
| `/llm-wiki:compile [<path>]`   | Read raw sources and create/update wiki pages.               |
| `/llm-wiki:query <question>`   | Answer from the wiki with citations; file the answer.        |
| `/llm-wiki:lint`               | Audit for dead links, orphans, drift, stale syntheses.       |
| `/llm-wiki:merge <from> <into>` | Merge a topic into another: dedupe sources, reconcile pages. |
| `/llm-wiki:remove <topic>...`  | Delete topics (git-recoverable; no confirmation).            |
| `/llm-wiki:doctor`             | Report environment + config (qmd, git, vault, topic).        |

## Key concepts

### Vault and topics

All wikis live under one **vault** directory. Each **topic** is its own folder under
it. A working directory is **bound** to a topic via `set-topic` (or `init`), and that
binding is remembered across sessions. Bindings are exact per-directory (no
subdirectory inheritance), so you cannot accidentally write to the wrong wiki.

### Two zones: raw vs wiki

```
<vault>/<topic>/
  raw/                immutable, verbatim sources (the LLM never edits these)
    documents/        copied source files + <name>.meta.md sidecars
    attachments/
  wiki/               LLM-owned pages
    index.md          catalog, read first
    queries/          filed query answers
  outputs/reports/    dated lint reports
  CLAUDE.md           thin per-wiki schema (points to plugin conventions/templates)
  log.md              append-only operation log
  qmd.yml             search collection config
```

`ingest` fills `raw/` (verbatim copy + a `.meta.md` sidecar carrying `compiled: false`).
`compile` reads uncompiled sources and produces `wiki/` pages, then flips the sidecar
to `compiled: true`. `raw/` is sacred: sources go in, nothing comes out.

### Page types

- **source-summary** -- one per source. A _faithful, wiki-blind_ read under a declared
  **frame** (lens), with a lens-bound disclaimer. It states what it covers, not an
  enumeration of what it misses (the negative space is the implicit complement of the
  frame). Focused deep-reads are appended over time as dated, lens-labeled sections.
- **concept** -- an idea/entity. Descriptive and _derived_ (synthesized) knowledge live
  in the same page type; a synthesis is just a concept whose body draws on other
  concepts (`informed-by:`). `person` is a kind of concept (an author entity).
- **query** -- a filed Q&A answer (`type: query`, `informed-by:` provenance). A durable
  answer can be rewritten as a derived concept.

### Citation discipline

Every non-obvious claim links its basis: `[[source-summary-x]]` means "a source said
this"; `[[concept-y]]` means "derived/connected." This is how a reader (and `lint`)
tells what a source said from what was concluded.

### Compile: faithful read, then merge

`compile` runs two passes: (1) a **wiki-blind source-reader** subagent reads the raw
source under a brief and returns a framed summary -- it never sees existing wiki pages,
so it cannot bend the reading to confirm them; (2) the main agent **merges** the result
into concept/person pages, runs the backlink audit, and updates the index. With a focus
(from your comments/discussion) it also runs focused reads; otherwise just a neutral one.

## State and config

Machine-local state lives in `~/.config/llm-wiki/` (outside any vault, so it is not
committed and not synced):

- `config.json` -- `{ "vault_path": "..." }`
- `topics.json` -- `{ "<abs-dir>": "<topic>" }`

These are read/written by `bin/llm-wiki`, which the hooks and commands call. You
never invoke it directly.

## Obsidian integration

- **Graph view** renders `[[wikilinks]]` as a visual network; orphans show as isolated
  nodes (what `lint` flags).
- **Dataview** queries page frontmatter (`type`, `tags`, `informed-by`, ...).
- **Web Clipper** can save articles straight into `<topic>/raw/documents/`; then run
  `/llm-wiki:ingest`.

## Known issues

- **`@` autocomplete may surface `~/.claude/`** when this (or any) plugin operating
  under `~/.claude/plugins/` is in use. This is an upstream Claude Code scope bug
  ([anthropics/claude-code#21587](https://github.com/anthropics/claude-code/issues/21587)),
  not a plugin bug. The command-driven design (commands do not read plugin files at
  prompt time) reduces it.

## Uninstall

```
/plugin uninstall llm-wiki
```

Your wikis under the vault are untouched. To also clear machine-local state, remove
`~/.config/llm-wiki/`.

## Acknowledgments

Originally created by [ekadetov](https://github.com/ekadetov); based on Andrej
Karpathy's LLM Wiki pattern (vendored at [`KARPATHY-LLM-WIKI.md`](./KARPATHY-LLM-WIKI.md)).

## License

MIT
