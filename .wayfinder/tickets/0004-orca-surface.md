---
title: "Orca CLI surface"
type: wayfinder:research
status: open
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
