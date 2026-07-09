---
description: Reply to a coordination issue -- pass it to another party, or close it
argument-hint: <number>
---

Add your party's entry to an issue and either pass the ball to other parties (it
stays open) or close it. You draft the content, the user approves, and the program
appends the entry and updates `index.json`.

1. Resolve context: run `coordination-ledger context`. If `root` is empty, stop.
   Read the protocol at `conventions_path`.
2. `number` = `$ARGUMENTS`. Confirm it is open and who it awaits:
   `coordination-ledger check --party <party_label>` (or `coordination-ledger list`).
3. Draft the reply body and pick the mode:
   - **pass the ball** (the same issue continues) -- choose who must act next. Use
     this ONLY when it is genuinely the same item bouncing back (e.g. you answered
     and it returns to the author); a distinct unit of work is a NEW issue.
   - **close** -- `done` (propagated) or `divergent` (intentional non-propagation;
     say so in the body).
   Optionally refine the one-line `description`. For a split (one request is really
   several units of work): close `done` with a "superseded by ..." note, then
   `/coordination-ledger:open` each new issue.
4. **Preview in chat**: the reply body, the mode (to whom, or which status), and any
   updated description. Get the user's approval.
5. Record it -- pass the approved body on stdin, with exactly ONE of `--to` /
   `--status`:
   ```
   # pass the ball (stays open):
   printf '%s' "<body>" | coordination-ledger reply --number <N> --to <label[,label]>
   # close:
   printf '%s' "<body>" | coordination-ledger reply --number <N> --status <done|divergent>
   ```
   Add `--description "<updated summary>"` and/or `--as <your label>` as needed
   (`--as` defaults to the cwd's party). The program appends your entry with your
   repo's `ref:` SHA, reassigns `actors` or closes + stamps `date_resolved`, updates
   `index.json`, and commits. Stay silent on success.
