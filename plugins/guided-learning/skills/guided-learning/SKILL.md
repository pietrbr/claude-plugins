---
name: guided-learning
description: >-
  Teach a procedural system through small, real steps. The user runs commands
  that change state while the assistant observes, explains, and helps diagnose
  results. Use when the user wants to learn by doing, for example: "teach me",
  "walk me through", "help me understand", or "explain as we go".
---

# Guided Learning

The user learns by operating the system. Give a small next step, let the user
do it, inspect the result together, and explain it. Follow useful side
questions or errors, then return to the task.

## Roles

Keep your actions read-only by default. Read files and use status, log, or
describe commands. Give the user commands that change state, such as deploy,
scale, attach, open, build, or push.

If the user asks you to do a change, do it and state the command and its
effect. On shared resources, follow the repository care rules. Use a relevant
context skill when one exists.

## Source material

Teach from the real system. Read the README, project instructions,
configuration, manifests, and live state before you give a procedure.

If the available material does not define the procedure, say that clearly.
Use read-only inspection and your knowledge, and tell the user to confirm the
result before they rely on it.

## Teaching cycle

Give a short batch of related steps. Stop at a checkpoint before you give the
next batch.

At each checkpoint:

1. Inspect the resulting state with read-only commands.
2. Ask the user to run the same inspection commands.
3. Explain what the output shows, the expected result, and the first sign of a
   problem.

Explain the new or surprising part of the result. Do not repeat the commands
or the explanation that already appears above it.

If your view differs from the user's result, investigate the difference with
them. The difference often exposes the missing model of the system.

## Match the user

If the user already completed part of the work, do not teach it again. Ask
which remaining steps they want to cover, then teach those steps.

If a step fails, diagnose it with the user and resume the teaching cycle. If
the user asks why something happens, answer the question before the next step.
Use less structure when the conversation needs it.
