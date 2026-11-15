---
title: "Dictation preset spec"
type: wayfinder:grilling
status: open
assignee:
blocked-by:
  - 0002-handy-x11-arch.md
---

## Question

Lock the dictation preset, given handy's verified mechanism (vibekey stays just
the finger — no coupling into handy's pipeline).

Settle:

- press → record-start, release → record-stop wired via the chosen mechanism
  (hotkey injection vs otherwise, per the handy research answer).
- behaviour when handy is not running, and what the panel/OSD says.
- how injected hotkeys survive the daemon's own grab and X11 focus state.
- the latency budget a user can tolerate between release and text.
