---
title: "OpenCode automation surface"
type: wayfinder:research
status: open
assignee: jimOnAir
blocked-by: []
branch: research/opencode-surface
---

## Question

What can drive OpenCode sessions programmatically from the desktop today?

- `opencode serve` / its HTTP API: can an external process **list sessions,
  switch/focus one, interrupt an in-flight run, send input**?
- TUI keystroke fallback where no API exists: what does the running TUI accept
  (Esc vs Ctrl+C semantics for "interrupt")?
- How to identify and focus the terminal window running a given session:
  title patterns, `xdotool`/`wmctrl` search, KDE window-activation hooks.

**Output**: per-operation mechanism facts and gaps for *next/prev session*,
*focus terminal*, *interrupt*, on `research/opencode-surface`, linked from this
ticket. Feeds *Agent-preset design for OpenCode/Orca*.
