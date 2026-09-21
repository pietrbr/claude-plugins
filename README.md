# claude-plugins

`pietro-marketplace` -- a Claude Code plugin marketplace.

## Install

```
/plugin marketplace add <this-repo>
```

Then install any plugin from it:

```
/plugin install <plugin>@pietro-marketplace
```

## Plugins

| Plugin                                                               | Description                                                                                                                                                                                                                |
| -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [llm-wiki](./plugins/llm-wiki)                                       | A persistent, compounding knowledge base in a local markdown vault (Karpathy's LLM Wiki pattern). Per-operation commands to init, ingest, compile, query, lint, and remove topic wikis; optional qmd search.               |
| [python-dev](./plugins/python-dev)                                   | Python development workflow: subagents that run tests + lint (`python-test-runner`), write tests (`python-test-writer`), and do root-cause debugging (`debugger`), plus a `run-python-tests` skill that drives the runner. |
| [guided-learning](./plugins/guided-learning)                         | A hands-on teaching posture for learning any procedural system by operating it yourself, with Claude as lab instructor -- scopes each step, runs read-only checks alongside you, and explains the output.                  |
| [format](./plugins/format)                                           | Format files with a conform.nvim/mason-style toolchain (isort/ruff/prettier/shfmt/stylua/taplo/latexindent/...). Defaults to git-changed files; respects repo-local formatter config.                                      |
| [conventional-commit-message](./plugins/conventional-commit-message) | Draft a Conventional Commits message from the conversation's changed files and current git state; infers type/scope from repo history and never commits or pushes.                                                         |
| [coordination-ledger](./plugins/coordination-ledger)                 | Cross-repo coordination ledger -- a local, never-pushed issue tracker for repos under a common parent (e.g. a paper and its codebase). A Python program owns the JSON index; per-operation commands (init, register, open, reply, check) are thin wrappers over it.                    |
| [session-summary](./plugins/session-summary)                         | Reorient inside a long or wandering session: `/summary` prints a schematic summary of the current conversation -- status, original problem, decisions and drift, open items, and the next step. Chat only.                    |

## License

The root [`LICENSE`](./LICENSE) (MIT) covers only the marketplace scaffolding
(this README and the `.claude-plugin/marketplace.json` manifest). Each plugin
under `plugins/` is licensed independently by its own `LICENSE` file, which
governs everything in that plugin's directory. Where a plugin carries its own
license, that license — not the root one — applies to the plugin.
