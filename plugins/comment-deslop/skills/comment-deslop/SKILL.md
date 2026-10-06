---
name: comment-deslop
description: De-slop code comments -- find and remove the comments an agent left behind that restate the code, narrate an edit, record history or decisions, leak task numbers, pin benchmarks, or pad a function past its comment budget. Use when the user says "de-slop", "clean up the comments", "remove the AI comments", "too many comments", "why is this commented", or asks to strip narration from a file or diff, and when a comment-deslop report appears on Stop and needs acting on.
---

# De-slop comments

A detector ships in this plugin's `bin/`, on `PATH` as `comment-deslop-hook.sh`
(a wrapper that picks an interpreter and never breaks the edit loop). It is the
single source of truth for what counts as slop -- do not re-derive the rules
here, and do not hand-grade comments the detector has not seen.

## Two entry points

**The hook** runs once per turn, on `Stop`, and writes its report to stderr with
exit 2. That prevents the turn from ending, so act on the report and then finish.
It arrives while you still know whether the comment was load-bearing, which is
the reason it runs in the turn rather than at review time. Each finding is
reported once per session, so a report you see is new.

**`/deslop`** is the batch pass over a path, a diff, or the whole repo. Use it
when the user asks to clean up existing code rather than code just written.

## Advisories are not findings

The report may carry a second block headed `comment-deslop advisory:`. Those rules
are excluded from the checks on purpose. **Do not fix them and do not delete the
comments they name.** Repeat the block to the user, say nothing about whether the
comment should go, and move on. In the hook they arrive on a channel you never
see, which is deliberate: the decision is the user's, not yours.

If the user decides they want one enforced, that is an engine change (moving the
id into `RULE_ORDER`), not a per-file judgment.

## Scope

A comment is in scope when any of its lines changed since the diff base
(`HEAD` by default). That means the detector will also flag the user's own
uncommitted comments, not only yours -- correct at a commit boundary, worth
naming if the user is surprised. `--all` drops the change filter; `--since REF`
moves the base.

## Acting on a report

Read the code around each finding before editing, then **delete the comment**.
The checks already spare comments that carry a constraint, a spec reference or a
reason, so a comment that reached the report has already failed that test. Do not
re-open it.

A better name or an extraction is the better fix where one exists. Where it does
not, delete the comment anyway: do not rewrite working code only to satisfy the
check, and never re-add a comment you deleted.

If a flagged comment genuinely must stay, that is a gap in the allowlist. Say so
to the user instead of keeping it quietly, and never claim it is "justified" to
dismiss the finding.

Skip findings in files kept as references to an outside source (downloaded
scripts, vendored or upstream copies): edit them only to match their source.

`/deslop` carries the per-rule fix table. Follow it rather than improvising.

`/deslop --llm` is a different job: the engine prints the comments no rule
matched and **you** judge them. Those verdicts are yours, so propose them and let
the user decide -- never apply them silently. The hook has no access to this pass.

## What it will not flag

Lint and compiler directives, shebangs, license and SPDX headers, URLs, shouted
issue keys (`ABC-123`), BDD markers, prescribed docstring sections, spec and DOI
citations, and uppercase intent markers (`TODO`, `NOTE`, `SAFETY`) are allowed
outright -- except when a marker also records a deferred decision (`TODO:
revisit`, `for now`), which is slop the marker cannot launder. Trailing comments
are exempt from the terseness rules, because `timeout = 5  # seconds` annotates
the value beside it.

If the user wants a rule's verdict changed, that is an engine change (a `NEVER`
entry or a threshold in `bin/comment-deslop`), not a judgment you make per file.
Say so and offer the edit.
