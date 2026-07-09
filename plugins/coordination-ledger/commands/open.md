---
description: Open a new cross-repo coordination issue
argument-hint: <description>
---

File a new issue for a change that must cross the boundary to another party. You
draft the content, the user approves, and the program writes `index.json` + the
issue body (allocating the number, freezing the slug, and stamping the `ref:` SHA).

1. Resolve context: run `coordination-ledger context`. If `root` is empty, stop:
   run `/coordination-ledger:init` first. Author = `party_label`; if empty (you are
   at the root or an unregistered dir), ask which registered party (from `parties`)
   authors this. Read the protocol at `conventions_path`.
2. `description` = a short one-line summary of the change (from `$ARGUMENTS`, or
   ask). Draft the body: one or two lines on what changed and why the other side
   cares, plus optional orientation (not an implementation plan).
3. Actor (who must act): with exactly two parties the program picks the other one;
   with more, choose the target party and pass `--actor <label>`.
4. **Preview in chat**: the `description`, the author -> actor direction, and the
   body prose. Get the user's approval.
5. Create it -- pass the approved body on stdin:
   ```
   printf '%s' "<approved body>" | coordination-ledger open \
     --author <party_label> --description "<description>" [--actor <label>]
   ```
   The program allocates the next number, derives+freezes the slug, stamps
   `ref: <author>@<sha>` from the author repo's HEAD, writes the body file, updates
   `index.json`, and commits. Stay silent on success.
