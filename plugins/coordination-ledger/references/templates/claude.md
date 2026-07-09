# <parent> -- coordination

This directory is the coordination root for the repos registered in `index.json`.
It sits on top of them: its own LOCAL git repo (never pushed) tracking ONLY the
coordination files, with the party repos gitignored -- never tracked, committed,
or built from here.

Coordination is governed by the **coordination-ledger plugin**; its commands carry
the protocol. `index.json` is the authoritative state (parties and issues); the
`coordination-ledger` program manages it. Do substantive work in a
session inside the relevant party repo.

## Shared vocabulary

<!-- Project-specific terms that must stay consistent across parties. -->
