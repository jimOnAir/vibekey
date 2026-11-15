---
title: "Orca CLI surface"
type: wayfinder:research
status: closed
assignee: jimOnAir
blocked-by: []
branch: research/orca-surface
---

## Question

What does Orca expose for programmatic control from the desktop?

Via the `orca` CLI: worktrees, folder contexts, terminals, automations,
worktree comments.

- Can **"next / previous worktree"** and **"focus its terminal window"** be
  performed with CLI commands alone, without keystroke hacks?
- Is there a stable way to enumerate worktrees/terminals together with their
  window identity (for the focus operation)?

**Output**: mechanism facts and gaps for the *Orca next-worktree* stretch
preset, on `research/orca-surface`, linked from this ticket. Feeds
*Agent-preset design for OpenCode/Orca*.

## Answer

**The stretch Preset is implementable without keystroke hacks into Orca.**
Full findings with live-probe evidence: [`research/orca-surface`](https://github.com/jimOnAir/vibekey/blob/research/orca-surface/research/orca-surface.md).

- **Enumerate/activate**: `orca worktree list --json` (rows carry `identity.key`) → `orca worktree activate --worktree identity:<key> --json` (`activated: true`). No next/prev command exists and **no query for the displayed workspace** (`active`/`current` resolve from shell cwd) → the Daemon owns the cycle cursor and the candidate order.
- **Window raise is X11, not Orca**: single top-level window; find by `_NET_WM_PID == orca-ide` pid (`wmctrl -lp`), then `wmctrl -i -a` — verified on this KDE/X11.
- **Terminals**: `terminal list --json` → `terminal switch --terminal <handle>` (`navigated: true`); handles are runtime-scoped → re-list per fire, never match on `title`. A full drive loop exists: `read` → `send` → `wait --for tui-idle`.
- **Preconditions**: Orca must run (`orca status --json`; `orca open --json` is the sanctioned cold start). Use the absolute `orca-ide` path/shim — bare `orca` collides with the GNOME screen reader. The CLI is the supported contract; do **not** speak to runtime `:6768` / daemon sockets directly.
- **Gaps carried to** *Agent-preset design for OpenCode/Orca*: cycle state drifts on user sidebar clicks; folder workspaces cannot be activated from the CLI; KWin focus-stealing prevention from a hotkey context is untested; `xdotool` not yet installed on this box.
