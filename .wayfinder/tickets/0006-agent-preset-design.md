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

- Map each Preset onto the Controls (✓ / ✕ / knob turn) sensibly; which land
  on knob directions.
- **next/prev Session**: adopt the composed mechanism (API session ring of
  root `ses_…` ids → host resolve: Orca `terminal switch` with title/directory
  match, else `wmctrl -a` on `OC | ` title)? Orca drift gap (Daemon-owned
  cursor vs sidebar clicks) — accept or mitigate? In-TUI `ctrl+tab` route —
  expose at all?
- **interrupt**: confirm API-first (`POST /api/session/{id}/interrupt`,
  no focus needed) with Esc-only keystroke fallback; `orca terminal send
  --interrupt` as the Orca-native alternative. Codify **never Ctrl+C**
  (empty-prompt exit path).
- Focus-presets for `--standalone` TUIs (API-opaque): window/title route only —
  in v1 or out?
- Behaviour and Panel/OSD report when: no OpenCode service running, no root
  Sessions, Session id stale, Orca not running mid-cycle.
- The Daemon's service discovery: read `~/.local/state/opencode/service.json`
  for port + Basic auth? Refresh policy when the service restarts.
