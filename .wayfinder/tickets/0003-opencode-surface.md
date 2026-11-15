---
title: "OpenCode automation surface"
type: wayfinder:research
status: closed
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

## Answer

**All three operations have mechanisms on OpenCode v2.2.7 — interrupt is a
first-class API call; session-cycling must be composed.** Full evidence:
[`research/opencode-surface`](https://github.com/jimOnAir/vibekey/blob/research/opencode-surface/research/opencode-surface.md) (`5d16b67`).
Live-verified against the running v2.2.7 service (Basic auth from
`~/.local/state/opencode/service.json`); V1 doc routes (`/session/:id/abort`,
`/tui/*`) do **not** apply to v2's `/api/*` surface.

- **next/prev Session**: no single "focus Session X" primitive — compose it:
  ring of root Session ids from `GET /api/session?parentID=null&order=desc`
  (stable `ses_…` keys) → host resolution: **Orca** row match
  (`title == "OC | " + api.title`, or `worktreePath == location.directory` as
  fallback — titles auto-rename/ellipsis) → `orca terminal switch`; plain
  terminal → `wmctrl -a` on the `OC | …` title OpenCode sets itself. In-TUI
  alternative: `ctrl+tab` / `ctrl+shift+tab`. ⚠️ The one real gap: v2.2.7
  defines the `tui.session.select` event every TUI listens for, but **no HTTP
  route publishes it**.
- **focus terminal**: Orca: `orca terminal switch` (rows carry
  `agentIdentity: "opencode"`). Standalone: title prefix `OC | ` →
  `wmctrl -lp`/`-a`, confirm via `_NET_WM_PID` + `pgrep -a opencode`.
  `--standalone` TUIs are API-opaque (private unregistered server, 401) —
  window/title route only.
- **interrupt**: best is `POST /api/session/{id}/interrupt` →
  `{interrupted:true}`, idempotent, needs no window focus (SSE:
  `session.execution.interrupted`). Orca alternative: `orca terminal send
  --interrupt` (PTY-level). Keystroke fallback: **Esc only — never Ctrl+C**,
  which on an empty prompt exits the app.
- **Multi-instance**: shared SQLite registry `~/.local/share/opencode/opencode.db`
  (`session_v2`) exists, but the HTTP API is the supported read path;
  `session.list` filters/cursors are enough for a Daemon-side cycle keyed by
  `ses_…`.
