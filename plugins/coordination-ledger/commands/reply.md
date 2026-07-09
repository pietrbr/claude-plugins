---
description: Reply to / resolve a coordination issue
argument-hint: <number>
---

Record your party's resolution of an issue. You draft the reply, the user
approves, and the program appends the entry, sets the status, and updates
`index.json`.

1. Resolve context: run `coordination-ledger context`. If `root` is empty, stop.
   Read the protocol at `conventions_path`.
2. `number` = `$ARGUMENTS`. Confirm it exists and awaits your side:
   `coordination-ledger check --party <party_label>` (or `coordination-ledger list`).
   If you are not the issue's actor, warn the user before proceeding.
3. Draft the reply body (what you did / decided and the resolving commit's effect)
   and choose the status: `done` (propagated) or `divergent` (the difference is
   intentional and will not propagate -- say so in the body). Optionally refine the
   one-line `description` to reflect the outcome. For a split (one request is really
   several units of work): resolve it `done` with a "superseded by ..." note in the
   body, then `/coordination-ledger:open` each new issue.
4. **Preview in chat**: the reply body, the status, and any updated description.
   Get the user's approval.
5. Record it -- pass the approved body on stdin:
   ```
   printf '%s' "<approved body>" | coordination-ledger reply \
     --number <N> --status <done|divergent> [--description "<updated summary>"]
   ```
   The program appends the entry with the actor's `ref:` SHA, sets the status +
   resolved date, updates `index.json`, and commits. Stay silent on success.
