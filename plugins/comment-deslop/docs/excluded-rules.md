# Excluded rules

A development register: what the two upstreams detect that this engine does not
enforce, why, and what it would cost to promote.

Four of these now run as **advisories** -- reported to the user, withheld from the
model, never affecting the exit code. "Excluded" below means *excluded from the
checks*, not unimplemented. Promoting one is a one-line move of its id from
`ADVISORY_ORDER` into `RULE_ORDER`; the detector already exists and has corpus
cases and a per-kind floor. Not loaded by the skill or the
command -- the skill must describe only what the engine actually does, or it will
promise verdicts that never arrive.

Sources:

- **CC** -- comment-checker ([Rust](https://github.com/systemfsoftware/comment-checker),
  Apache-2.0; [second implementation](https://github.com/code-yeongyu/go-claude-code-comment-checker),
  MIT). Five tree-sitter classifier verdicts.
- **CS** -- comment-slop ([ionworks](https://github.com/ionworks/comment-slop), MIT).
  Seventeen text tiers.

Update this file when a rule moves in or out. A rule reinstated without a corpus
case is a rule that will rot.

## Dropped detectors

### `dead-code` (CC: Dead Code)

**Status: advisory.** Implemented as a two-stage test -- a code-shaped body (`DEAD_CODE_RE`) that then parses without `ERROR` nodes. It also gates the findings path: a code-shaped comment is skipped by every prose rule and by `budget`.

Commented-out code and stranded debug statements (`// console.log("debug", value)`).

**Why out.** The user's `CLAUDE.md` puts commented-out code out of scope
explicitly ("Commented-out code is out of scope"), so the rule has no mandate.
It is also the highest-false-positive rule in either upstream: distinguishing
`# x = 1` from prose about `x` needs a parse of the comment body, not of the
file, and both upstreams do it with heuristics on punctuation density.

**To reinstate.** Re-lex the comment body in the host language and require a
successful statement parse, not a punctuation score. tree-sitter can do this --
parse the stripped body and reject a tree containing `ERROR` nodes. Needs its own
negative corpus (prose containing `=`, `()`, `;`, dict literals in docstrings,
commented-out YAML).

**Risk if reinstated.** Fires on the commented-out block a developer is actively
bisecting, i.e. exactly when an edit-loop interruption is least welcome.

### `untracked-todo` (CC: Untracked TODO)

**Status: advisory.** Spared when the comment carries a shouted issue key, a URL, a `#123`, or an owner tag (`TODO(alice)`).

A `TODO` with no ticket or issue reference.

**Why out.** The single place the two upstreams contradict each other: CC flags
it, CS protects `TODO`/`SAFETY`/`NOTE` in its `NEVER` escape hatch. Resolving it
toward "flag" buys little here, because the underlying concern in `CLAUDE.md` is
decision-recording (`TODO: revisit`), which `history` already catches through
`NEVER_OVERRIDE`. Two hooks giving opposite verdicts on the same line is the
failure this plugin exists to avoid.

**To reinstate.** Remove `TODO` from `NEVER`, add a tracked-reference test
(shouted issue key, or a URL) as the spare condition. Cheap to build; the cost is
policy, not code.

**Risk if reinstated.** Every scratch marker in a work-in-progress branch becomes
a finding, and the agent will start inventing ticket numbers to satisfy it.

### `narration (model)` (CS: `--llm`)

A model pass over comments, judging whether each narrates the code.

**Why out.** Costs the offline-and-fast property a write-time hook depends on
(~150ms today, all of it local). Exploratory and off by default upstream, whose
own `docs/llm-sweep.md` reports it unvalidated. A model call inside the edit loop
also makes the hook's verdicts non-reproducible, which breaks the corpus gate.

**To reinstate.** Only in the batch path (`/deslop`), never in the hook, and only
as an additive pass over comments the deterministic rules spared. Would need a
wall-clock bound and a cache keyed on comment text.

### `banner`, `section-label` (CS)

**Status: advisory.** Divider and short-label shapes, capped at 90 characters of prose.

Decorative dividers (`# ----`) and bare section headings.

**Why out.** Repo house style, not slop. CS reports these against its own
codebase and deliberately leaves the fires in place, which is the tell: a rule
whose author does not act on it is a preference, not a defect. Firing on every
touched divider line is pure edit-loop noise.

`step-marker` (`Step 1:`) is **kept** -- numbering a procedure the code's own
order already gives is narration, not decoration.

**To reinstate.** Make it opt-in per repo, not default-on. There is no config file
today (see below), so this needs the config surface first.

### `--include-unreviewed` (CS flag)

**Status: advisory, never reported.** It is computed only to feed `--llm`. It is
printed in no report and excluded from `--json` advisories, because it fires on
nearly every short comment and a list that long is not a verdict.

Report every short unmatched comment.

**Why out.** Low precision by construction; upstream says "never the hook". A
deliberate high-recall sweep is a different job from a write-time gate.

**To reinstate.** Add as a flag on the batch path only, with its findings labelled
as unreviewed so the agent does not treat them as verdicts.

## The hook itself, on trial

The hook runs on `Stop`, once per turn. It started on `PostToolUse`, once per
edit, and the measurements that moved it are worth keeping:

- 130 to 150 ms per invocation, which was never the problem
- four reports for one kept comment across four edits of the same file
- 367 findings, about 12,000 tokens, in a single report for one real file

`PostToolUse` remains implemented: pass a tool payload to `--hook` and it reads
`tool_input.file_path`. It is not wired, and wiring it back means re-opening
repetition, because the session cache is keyed per finding and not per edit.

**The standing fallback** is to remove the hook and keep the manual command only,
positioned beside `/simplify` as a mid-task pass. Decide after using the `Stop`
hook for a while. If it goes, delete `--hook`, `read_hook`, `emit_hook` and the
`systemMessage` channel; keep the exit codes, which are a useful CLI contract for
a commit gate.

## Kept, but not in the hook

### `budget` -- batch path only

At most one comment per function; none in a function under ten code lines. The
rule is in the engine and runs under `/deslop`, but `hooks/hooks.json` passes
`--no-rules budget`.

**Why.** Measured over two real repositories it was 51% and 32% of all findings
(133/259 and 546/1693) -- the single largest source in both. Worse, it is the one
rule an agent cannot act on at the line it just edited: "`run_evaluation` already
spent its one comment (19 in the function)" asks for the function to be split,
which is a refactor, not a comment fix. A hook finding that cannot be resolved in
the turn that produced it trains the agent to ignore the hook.

It is also the rule that most often fights the justification clause: it fired on
`# Find matching conflict row (conflicts are app-level, not per-slice)`, which
carries a fact the code cannot show. The `JUSTIFY_RE`/`CONSTRAINT_RE` spares
catch some of these, not all.

**To put it back in the edit loop.** Delete `--no-rules budget` from
`hooks/hooks.json`. Nothing else changes.

**Also scoped out of shell**, where `main` is the whole program and there are no
real function boundaries to count against; `density` governs shell instead.

## Demoted, not dropped

### `density` -> shell only (CS)

Per-language comment-to-code ceiling over a changed region.

`budget` (at most one comment per function; none in a function under ten code
lines) supersedes it wherever tree-sitter gives function nodes: it is stricter,
more explainable, and matches the policy wording. `density` survives at a 40%
ceiling for shell, which has no function boundaries to count against.

**If `budget` is ever removed**, density must be restored for all languages, or
comment accumulation goes unmeasured.

### `changelog-memo`, `edit-narration`, `historical`, `unbuilt` -> merged into `history`

Four upstream tiers (one CC verdict, three CS tiers) are one rule with sixteen
patterns. The trailing-comment exemption is applied **per pattern**, not per
rule, so `# Fixed: skip None entries` still fires inline while `# this used to
return a tuple` does not.

Splitting them again would only change the report label. Keep them merged unless
the per-kind floors need to move independently.

### `code-reference` + the `CLAUDE.md` reference policy -> merged into `reference`

CS flags pointers that rot (`file.ts:120`). The policy adds: comments may
reference only tracked repository files, or papers and specifications by name,
number, or DOI. One rule now does both, and spares a path that `git ls-files`
resolves.

## Dropped mechanisms

### Fail-open on unreliable context (CC)

CC truncates its adjacency window on `Edit`/`MultiEdit` because it classifies the
tool payload, and it spares any context-dependent verdict it cannot vouch for.

**Structurally unnecessary here.** The hook runs `PostToolUse`, so the engine
parses the whole file from disk and the code window is always trustworthy. The
concept was deleted rather than ported -- do not reintroduce it without first
changing what the engine reads.

### `--strip` (CC)

Delete flagged whole-line comments from the file.

**Why out.** Blunt line deletion is the wrong remediation for most findings:
`restatement` usually wants a rename, `verbose` wants a rewrite, `budget` wants a
split. The fix belongs to the agent reading the report with the surrounding code,
which is what `/deslop` does.

### Pre-commit / `prek` gate (CS)

CS runs as a second layer in `.pre-commit-config.yaml`.

**Built, not wired.** The CLI already supports it (`--since REF`, exit 2, path
arguments), but nothing installs a hook into a user's repo. Whether a repo gates
commits on this is a per-repo decision, and `/code-review` already covers that
boundary.

## Not built by either upstream

Kept here because they are the obvious next rules, not because they were
rejected.

- **Config file.** Every threshold and both escape hatches (`NEVER`,
  `NEVER_OVERRIDE`) are constants in `bin/comment-deslop`. Tuning means editing
  the engine. A `[tool.comment-deslop]` block would unblock `banner`,
  per-repo ceilings, and per-repo rule selection. CS has the same limitation and
  documents it as deliberate; that stops being true once a second repo uses this.
- **Theory and derivation dumps.** `CLAUDE.md` forbids textbook explanations in
  code. Currently caught only incidentally, by `verbose`. A real rule would need
  to recognise exposition (definitions, derivations, worked examples) as distinct
  from a constraint.
- **Comment/code staleness.** A comment whose cited identifiers no longer exist in
  the file. Cheap with tree-sitter and high precision, and neither upstream has
  it.
