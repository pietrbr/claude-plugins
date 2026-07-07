---
name: run-python-tests
description: Run Python tests and linting via the python-test-runner subagent. Use when the user asks to run tests, wants to check if tests pass, says "run tests", "check tests", "validate changes", or after Python code edits that need verification.
argument-hint: [test file, -k filter, or --debug]
allowed-tools: Agent
---

Spawn the `python-test-runner` subagent. Tell it to:

1. Run the full test suite
2. Run ruff linting and formatting
3. Return a report of any errors or warnings, or confirm all passed

If the user specified particular tests, scripts, or flags, pass those through verbatim:

$ARGUMENTS
