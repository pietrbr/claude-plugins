---
name: conventional-commit-message
description: Generate a conventional commit message from files edited in this conversation and current git state. Use when the user asks for a commit message, wants to commit changes, or says "what should my commit say".
argument-hint: [optional scope or hint]
allowed-tools: Bash(git:*), AskUserQuestion
disallowed-tools: Bash(git reset:*), Bash(git push:*)
---

# Conventional Commit Message

Review the files edited in this conversation and the git context below, then propose a commit message. Do NOT run `git commit` - output the message only.

## Git context

**Status:**
!`git status --short 2>/dev/null || echo "(not a git repo)"`

**Staged changes:**
!`git diff --cached --stat 2>/dev/null`

**Unstaged changes:**
!`git diff --stat 2>/dev/null`

**Recent commits (style reference):**
!`git log --oneline -5 2>/dev/null`

**Known scopes in this repo (with usage count, most-used first):**
!`out=$(git log --pretty=format:'%s' 2>/dev/null | sed -nE 's/^[a-zA-Z]+\(([A-Za-z0-9_,-]+)\)!?:.*/\1/p' | tr ',' '\n' | sed 's/^ *//;s/ *$//' | grep -v '^$' | sort | uniq -c | sort -rn | awk '{printf "%s (%s), ", $2, $1}' | sed 's/, $//'); echo "${out:-(none yet)}"`

$ARGUMENTS

## Types

- `feat` new feature for API or UI
- `fix` bug fix for API or UI
- `refactor` code restructuring without behavior changes
- `perf` performance improvements (special refactor type)
- `style` code formatting (whitespace, semicolons, etc.)
- `test` adding or correcting tests
- `docs` documentation changes only
- `build` build tools, dependencies, versions
- `ops` infrastructure, deployment, CI/CD, backups
- `chore` initial commits, .gitignore modifications, maintenance tasks

## Choosing the scope

A scope should name a **durable subsystem or concern**, not the file or module you happened to touch. Naming scopes after modules breeds near-synonyms - several scopes for one subsystem, or two names for the same concern - and the log stops showing the project's real seams. Keep the vocabulary small and concept-level (the examples below are generic illustrations, not scopes to use; the real vocabulary is the known-scopes list above).

- Reuse from the known-scopes list above; its usage counts show the established vocabulary (count-of-1 scopes are often synonyms-in-progress, not precedent).
- Prefer the subsystem over a module inside it - e.g. `auth`, not `auth_jwt_middleware` - since the concept survives refactors.
- Assume any "new" scope is a synonym of an existing one until proven otherwise; only mint one for a concern no existing scope covers.
- Omit the scope when the change is repo-wide or it would just echo the type.

If you're genuinely torn between reusing a scope and creating one, or between two existing scopes, don't guess - see "When to ask".

## LaTeX-only repos

When the changes are predominantly `.tex`/`.bib`/`.sty` files (a paper, thesis, or slide deck), the document is the product - map types to it, overriding the code-centric list above:

- `feat` - the default: new content (sections, paragraphs, figures, tables, results). Adding text is a new feature of the document; reach for another type only when the commit adds no new content.
- `fix` - corrections that change meaning: wrong math, wrong numbers, broken `\ref`/`\cite`, factual errors.
- `style` - typos, grammar, wording polish, formatting; anything that doesn't change meaning.
- `refactor` - restructuring with no content change: splitting files, moving sections, extracting macros.
- `build` - preamble, packages, document class, Makefile/latexmk.
- `docs` - only repo meta-files (README, CLAUDE.md), never the document itself.

Scope: usually omit. Use the section/chapter name only when the commit is genuinely confined to one section; use `bib` or `figs` when it touches only references or figures. Since most commits end up as unscoped `feat`, the subject must name the content added ("add mobility sweep to results"), not just "add text".

Body: rarely warranted - a prose diff describes itself, so rule 4's "multiple sub-changes" case almost never applies here. If the commit has an underlying rationale not evident from the text (e.g. "reviewer 2 asked for a mobility analysis", "sign error made the estimator diverge in simulation"), the body records that - and only that. Never enumerate the smaller edits bundled in: a LaTeX commit routinely carries many minor changes (typos, wording, spacing) that need no explanation, no bullet, no mention.

## When to ask

Only ask in real ambiguity, never when one scope clearly fits - a question on every commit would defeat the purpose. When you do ask, use `AskUserQuestion` with a single question and 2-3 concrete options so the user decides in one click. Each option should be a real candidate: reuse an existing scope (note its usage count), reuse a different existing scope, or a specific new scope. Give enough context in the option descriptions - the relevant known scopes and a recent commit subject or two - so the choice is obvious without leaving the prompt. Then build the final message around their answer.

## Rules

1. Choose the type from the list above that best fits the change
2. Choose the scope per "Choosing the scope" above
3. Subject line: imperative mood, <=72 chars, no trailing period
4. Add a body **only** when at least one of these applies: the _why_ is non-obvious (e.g. surprising root cause, non-obvious tradeoff), there are important side effects or migration notes, or the commit unavoidably covers multiple sub-changes. If none applies, write no body.
5. Always use bullet points in the body. Each bullet must capture one of: a non-obvious reason for the change, a tradeoff or constraint, an important side effect or migration note, or - only if the commit is unavoidably multi-part - a minimal sub-change entry. Never write a bullet that just restates what the diff already shows.
6. For breaking changes: add `!` before the colon and a `BREAKING CHANGE: <description>` footer

Output the message in a single fenced code block, then ask if the user wants to adjust or run it.
