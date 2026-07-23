---
description: Summarize the current conversation -- status, original problem, decisions, open items, next step
---

Print a short, schematic recap of THIS conversation so the user can quickly
reorient. Chat only: do NOT read or write files, run tools, or commit. Base the
recap solely on the conversation so far.

Use this flexible skeleton -- a base, not fixed headers. Adapt it to the session:

**Status:** <where things stand right now, 1 line>

**Original problem:** <the initial ask, as first framed -- a stable anchor; do NOT fold later changes into this>

**Decisions & evolution:**
- <chose X over Y: say in a few words what X and Y are, and why X won>
- scope drifted: <what changed vs the original problem>   (include ONLY if drift actually happened)

**Open items:**
- [ ] <item -- short context>

**Next step:** <the single immediate action to resume on -- sharper than the backlog>

Rules:
- Schematic: bullets and short lines, no prose paragraphs -- but each line must
  carry enough context to be self-explanatory (name what X/Y are; don't leave
  bare labels).
- Scale to the session: a 2-message session gets ~4 lines; a long one gets more.
- Multi-topic / multi-workstream sessions: group **Decisions & evolution** and
  **Open items** under short per-topic sub-headers instead of one flat list.
- Collapse or drop empty sections (e.g. `Open items: none`) rather than padding.
- Report drift only when it happened; otherwise omit that bullet.
- Cover edge cases flexibly -- the skeleton bends to the conversation.
