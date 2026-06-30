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

| Plugin | Description |
|--------|-------------|
| [llm-wiki](./plugins/llm-wiki) | A persistent, compounding knowledge base in a local markdown vault (Karpathy's LLM Wiki pattern). Per-operation commands to init, ingest, compile, query, lint, and remove topic wikis; optional qmd search. |

## License

The root [`LICENSE`](./LICENSE) (MIT) covers only the marketplace scaffolding
(this README and the `.claude-plugin/marketplace.json` manifest). Each plugin
under `plugins/` is licensed independently by its own `LICENSE` file, which
governs everything in that plugin's directory. Where a plugin carries its own
license, that license — not the root one — applies to the plugin.
