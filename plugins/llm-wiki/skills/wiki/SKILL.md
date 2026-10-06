---
name: wiki
description: >-
  LLM Wiki -- a persistent, compounding knowledge base in a local markdown vault. Use when the
  user wants to add a source to their wiki, ask their wiki a question, build or
  maintain a knowledge base, or mentions llm-wiki / "my wiki". Routes to the
  llm-wiki commands.
---

# LLM Wiki

A persistent, compounding knowledge base (Karpathy's LLM Wiki pattern). The LLM
reads raw sources, writes cross-linked wiki pages, files query answers back, and
lints for gaps. The human curates sources and asks questions; the LLM does the
bookkeeping.

This skill only routes. Each operation is its own command, which carries its own
instructions and gets its vault/topic/conventions injected by the resolution hook.
Do NOT perform operations from here -- invoke the matching command.

## Routing

| Intent                                  | Command                                     |
| --------------------------------------- | ------------------------------------------- |
| Set where wikis live (once per machine) | `/llm-wiki:set-vault <path>`                |
| Create a new topic                      | `/llm-wiki:init <topic>`                    |
| Bind the current directory to a topic   | `/llm-wiki:set-topic <topic>`               |
| List topics and bound directories       | `/llm-wiki:list`                            |
| Save a source (verbatim, no pages yet)  | `/llm-wiki:ingest <path\|url> [--type <t>]` |
| Turn raw sources into wiki pages        | `/llm-wiki:compile [<path>]`                |
| Ask the wiki a question                 | `/llm-wiki:query <question>`                |
| Health-check the wiki                   | `/llm-wiki:lint`                            |
| Delete a topic (git-recoverable)        | `/llm-wiki:remove <topic>`                  |
| Check environment/config                | `/llm-wiki:doctor`                          |

## Core concepts (for routing, not execution)

- **Vault / topic**: all wikis live under one vault dir; each topic is its own
  folder. A working directory is bound to a topic (remembered across sessions).
- **raw/ vs wiki/**: `raw/` holds immutable verbatim sources; `wiki/` holds the
  LLM-written pages. `ingest` fills `raw/`; `compile` produces `wiki/`.
- **Page types**: `source-summary` (one per source, framed faithful read),
  `concept` (idea/entity; `person` is a kind; derived syntheses live here too),
  `query` (filed Q&A). Every non-obvious claim cites its basis via `[[wikilink]]`.
- **Source types**: each source carries a provenance `source-type` (`paper`,
  `article`, `standard`, `conversation`, `user-note`), set via `ingest --type` or
  auto-classified. A conversation synthesis is captured by drafting a note, reviewing
  it, then `ingest --type user-note` + `compile` -- it flows through the normal
  faithful-read pipeline like any source (no verbatim promotion).

Reference: see `KARPATHY-LLM-WIKI.md` at the plugin repo root for the original
pattern. `qmd` (optional) provides search; without it, search falls back to
`index.md`. `marp` is not used.
