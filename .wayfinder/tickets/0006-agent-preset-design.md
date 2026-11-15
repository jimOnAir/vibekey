---
title: "Agent-preset design for OpenCode/Orca"
type: wayfinder:grilling
status: open
assignee:
blocked-by:
  - 0003-opencode-surface.md
  - 0004-orca-surface.md
---

## Question

Lock the agent-preset vocabulary and behaviour for OpenCode + Orca. The
vocabulary is settled from charting — *next/previous OpenCode session*, *focus
the terminal running the agent*, *interrupt*; stretch: *Orca next-worktree*.

This ticket settles mechanics and edge behaviour:

- Map each preset onto the controls (✓ / ✕ / knob turn) sensibly; which land
  on knob directions.
- Mechanism per preset: API call vs key injection into the target window
  (per the two surface-research answers).
- No-session / no-agent-running / terminal-not-found behaviour, and what the
  panel + OSD report when a preset cannot do its thing.
- Whether interrupt means Esc, Ctrl+C, or an API abort — per firmware/TUI
  findings.
