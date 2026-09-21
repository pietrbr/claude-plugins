# comment-deslop

De-slop the comments an agent just wrote. A `Stop` hook runs once per turn over
the files git says changed, parses each with tree-sitter, intersects the comment
nodes with the changed lines, and reports on stderr so the model fixes it before
the turn ends. `/deslop` is the manual pass over existing code.

Detection only: it never edits a source file, and it never calls a model.

## Model

```
tree-sitter  ->  what is a comment, and what code sits next to it
git          ->  which of those comments this session is accountable for
                 (a comment is in scope when ANY of its lines changed)
```

The hook runs after the writes land, so the files on disk and `git diff HEAD`
describe the same bytes. That is what lets the engine parse each whole file --
adjacency context is never a truncated Edit fragment -- and still report only
what changed.

## When it runs

`Stop` fires once when Claude finishes a turn, not once per edit. Exit 2 stops
the turn from ending and feeds the report to the model, so the agent fixes the
comments and then finishes. One report per turn, however many edits it contained.

Two rules are held back from the `Stop` report: `budget` and `density`. Both are
whole-function or whole-region verdicts, so neither is fixable at a line, and a
finding the agent cannot clear would block the turn forever. `/deslop` runs them.

### Reported once per session

Each finding is keyed on the rule, the comment text, and the code line beside it,
and recorded in `$XDG_CACHE_HOME/comment-deslop/sessions/<session>.jsonl`. A
finding already reported in this session is not repeated, so:

| what happened | next `Stop` |
| --- | --- |
| nothing changed | silent -- this is also the loop guard |
| you edited elsewhere in the file | still silent |
| the comment text changed | reported again |
| the code beside it changed | re-judged, and reported again if it still applies |

The line number is deliberately **not** part of the key: any insertion above a
comment shifts it, which would defeat the cache on the most common edit there is.

A suppressed finding is never silent -- the count reaches you through
`systemMessage`. `SessionEnd` deletes the file, and a 7-day sweep covers a
session that never ended cleanly.

`HEAD` is the default base, so the report also covers the user's own uncommitted
comments, not only the agent's. That is correct at a commit boundary; `--since
REF` moves the base and `--all` drops the filter.

## Rules

Fourteen rules, in report-priority order. Only the last four need tree-sitter.

| rule                    | catches                                                                     |
| ----------------------- | --------------------------------------------------------------------------- |
| `bare-identifier`       | a lone name that repeats the identifier below it                            |
| `history`               | changelog memos, completed-edit narration, prior states, roads not taken, recorded decisions, deferrals (`for now`, `revisit`) |
| `flow-narration`        | names the `for`/`while`/`if`/`try` the code already shows                    |
| `conditional-narration` | `If X, do Y` restatements of the surrounding condition                      |
| `narrative`             | chatty asides, comments about comments, emoji                               |
| `restatement`           | says what the adjacent code says, with the shared tokens cited as evidence  |
| `process-leak`          | task numbers, plan references, review chatter                               |
| `benchmark`             | a measured snapshot with units (`~144x fewer buffers, measured 812ms`)      |
| `reference`             | line-number pointers, untracked paths, personal notes                       |
| `step-marker`           | `Step 1:` labels the code's own order already gives                         |
| `verbose`               | over 30 words or 3 prose lines (90 / 10 for author-chosen docstring prose)   |
| `redundant-docstring`   | a docstring the name and signature already state                            |
| `budget`                | more than one comment in a function; any comment in a function under 10 code lines |
| `density`               | a shell region over 40% comment                                             |

`history` merges what the two upstreams split across `changelog-memo`,
`edit-narration`, `historical` and `unbuilt`; the trailing-comment exemption is
applied per pattern, so `# Fixed: ...` still fires inline while `# this used to
...` does not.

One finding per line: when several rules match, the highest-priority one is
reported.

`budget` is a whole-function verdict, not a per-comment one, so the **hook runs
with `--no-rules budget`** (see `hooks/hooks.json`); `/deslop` runs it. Measured
on two real repos it was 51% of all findings, and it is not fixable at the line
the agent just touched -- it asks for the function to be split. Drop the flag from
`hooks.json` to put it back in the edit loop.

## Advisories

Four of the excluded rules still run, as **advisories**: they never affect the
exit code and never reach the model. In the hook they go out as `systemMessage`
in the JSON output, which Claude Code shows the user and withholds from Claude;
findings continue to go to stderr, where the model reads and fixes them. One
invocation, two audiences.

| advisory         | notes                                                          |
| ---------------- | -------------------------------------------------------------- |
| `dead-code`      | the comment body matches a code shape *and* parses without error |
| `untracked-todo` | a `TODO`/`FIXME`/`XXX`/`HACK` with no ticket, issue, URL or owner |
| `banner`         | a decorative divider or a section label                        |
| `unreviewed`     | every short unmatched comment -- high recall, opt-in only      |

`dead-code` also **removes commented-out code from the findings path entirely**:
a code-shaped comment is skipped by every prose rule and by `budget`, so it can
only ever produce an advisory. That is what "commented-out code is out of scope"
has to mean to be consistent.

`--advisory LIST` (or `all`) selects them; `--no-advisory` silences them. Default
is `dead-code,untracked-todo,banner`.

`unreviewed` is never reported, in any mode. It exists only to feed `--llm`,
because it fires on almost every short comment and a list that long is not a
verdict.

The advisory block groups by rule, because an advisory is one decision per rule
and not one per instance. Rules are ordered by count ascending, so the specific
ones come first and house style sinks to a single line with its number. Nothing
is capped: every count is printed and `--json` returns every row.

### Deliberately not implemented

Rationale, reinstatement cost, and the rules neither upstream has are tracked in
[`docs/excluded-rules.md`](./docs/excluded-rules.md).

- **dead code** -- commented-out code is out of scope; an advisory instead.
- **untracked TODO** -- the one place the two upstreams contradict each other.
  `TODO` stays allowed; an advisory instead. A `TODO` that defers a decision is a
  real `history` finding.
- **LLM narration sweep** -- costs the offline-and-fast property an in-turn
  hook depends on.
- **`--include-unreviewed`** -- low precision by design; available as the
  `unreviewed` advisory instead.
- **banners and section labels** -- repo house style, not slop; an advisory
  instead. `step-marker` is kept as a real rule.

### Allowed outright

Lint and compiler directives, shebangs, coding declarations, license and SPDX
headers, URLs, shouted issue keys (`ABC-123`), BDD markers, prescribed docstring
sections (`Args:`, `@param`, `# Safety`), spec and DOI citations, and uppercase
intent markers (`TODO`, `NOTE`, `SAFETY`, `FIXME`).

Two escape hatches, both in `bin/comment-deslop`:

- `NEVER` -- widen this rather than narrowing a rule's pattern.
- `NEVER_OVERRIDE` -- the phrases an intent marker cannot launder (`revisit`,
  `for now`, `chose X over Y`, `kept for backwards compat`).

A **file header** -- the first comment run in a file, with nothing but blank
lines above it -- is exempt from `verbose`, `narrative`, `density` and `budget`.
A documented CLI header (`claude-format.sh` has 33 lines of it) is the script's
docstring, not slop. `history`, `process-leak`, `benchmark`, `reference` and
`step-marker` still apply there.

A **trailing** comment is exempt from the rules whose signal is terseness
(`bare-identifier`, `restatement`, `narrative`, `conditional-narration`,
`process-leak`, and the `history` patterns that read as a label), because
`timeout = 5  # seconds` annotates the value beside it.

`budget` additionally spares any comment that carries a justification or names an
external system under a constraint (`the protocol caps the field at one octet`) --
otherwise the per-function quota would fight the reason the comment is allowed to
exist.

## Languages

Python, JS/JSX, TS, TSX, Rust, Go, C, C++, Java, Lua, shell, YAML, TOML,
Dockerfile.

Directory walks skip caches, virtualenvs, `vendor`/`third_party`/`site-packages`,
and **nested git repositories** (submodules and vendored checkouts -- someone
else's comments). Skipped repos are named in the output rather than dropped
silently; point at one directly to scan it. Comment extraction is tree-sitter when a parser is available and a
hand-written lexer otherwise; the lexer handles Python triple quotes, shell
word-boundary `#` (`${x#pre}`, `$((16#ff))`), heredocs, and `.ts` without JSX.

## Install

The hook is wired by `hooks/hooks.json`; installing the plugin is enough.

tree-sitter is optional, and **uv is not required**. To turn the AST rules on:

```bash
comment-deslop doctor --install
```

That creates a plugin-owned venv under `$XDG_CACHE_HOME/comment-deslop/venv` and
installs `tree-sitter-language-pack` into it. It uses `uv` when present because it
is faster, and falls back to the stdlib `venv` module and that venv's `pip`, both
of which ship with every Python 3.11+. A venv also side-steps PEP 668: installing
into a Homebrew or distro Python directly is refused as externally-managed, which
is why "just pip install it" is the least portable option, not the most.

The hook never creates the venv. A hook must not download a native
wheel because someone edited a file, so provisioning is opt-in.

The wrapper tries, in order: `$COMMENT_DESLOP_PYTHON`, the plugin venv,
`uv run --with tree-sitter-language-pack`, then plain `python3`. Measured hook
latency is ~140ms through the venv and ~165ms through `uv run` -- the venv is
marginally faster, but portability is the reason to prefer it. Without any parser
the AST-backed rules degrade (`flow-narration` falls back to the next code line)
or drop (`budget`, `redundant-docstring`, and the keyword half of `dead-code`);
the rest are unaffected.

`COMMENT_DESLOP_NO_UV=1` skips the `uv` branch.

## Model triage (`--llm`)

comment-slop's `--llm` sweep needed an API call because it is a standalone CLI.
Here the model is already in the loop, so `/deslop --llm` inverts it: the engine
prints the candidate set and the **agent** judges it.

```bash
comment-deslop-hook.sh --all --llm src/
```

Output is JSON: `{"candidates": [{file, line, comment, code}]}` -- the short
comments that no rule matched, each with the adjacent code line. A line carrying
a finding or a specific advisory is excluded, because something already states
what is wrong with it.

No API key, no network, no model call in the engine, and the hook cannot reach it.

## CLI

```bash
comment-deslop-hook.sh                        # changed lines, cwd repo
comment-deslop-hook.sh src/ --all             # every line under src/
comment-deslop-hook.sh --since main app.py    # changed since main
comment-deslop-hook.sh --json src/app.py      # machine-readable findings
comment-deslop-hook.sh --no-rules budget .    # drop a rule
comment-deslop-hook.sh --advisory all src/    # include the unreviewed sweep
comment-deslop-hook.sh --no-advisory src/     # findings only
comment-deslop-hook.sh --all --llm src/       # triage candidates for the agent
comment-deslop doctor --install               # create the parser venv (opt-in)
comment-deslop doctor                         # parser / git availability
comment-deslop eval                           # corpus + per-kind floors
```

Exit `0` on a clean file, an unsupported path, or any internal failure -- the
hook never breaks the edit loop. Exit `2` when there are findings.

## Calibration

`eval/corpus.json` holds 53 labeled cases: 31 positives across all 14 rules and
22 negatives that must stay silent (justified comments, spec citations,
directives, BDD markers, trailing annotations, strings that look like comments,
shell expansions, a TS type assertion). `comment-deslop eval` prints per-rule
precision and recall and fails on a per-kind floor breach, so one rule cannot
weaken behind a healthy aggregate. Cases marked `"ast": true` are skipped when no
parser is available.

Run it after any pattern or threshold change.

## Credit

The design synthesises two prior tools. No code is vendored from either.

- [comment-checker](https://github.com/systemfsoftware/comment-checker)
  (Apache-2.0) and its
  [separate implementation](https://github.com/code-yeongyu/go-claude-code-comment-checker)
  (MIT) -- the tree-sitter `PostToolUse` hook, comment-to-adjacent-code
  classification, and cited evidence.
- [comment-slop](https://github.com/ionworks/comment-slop) (MIT) -- the
  changed-lines scoping, the text tiers, the `NEVER` escape hatch, the
  trailing-comment exemption, the doc-comment prose model, and the labeled-corpus
  gate.
