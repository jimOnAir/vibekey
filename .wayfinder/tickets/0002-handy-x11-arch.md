---
title: "handy on X11/Arch"
type: wayfinder:research
status: open
assignee: jimOnAir
blocked-by: []
branch: research/handy-x11-arch
---

## Question

Can [handy](https://github.com/cfaxman/handy) be the STT app behind the
"vibekey is just the finger" arrangement?

- How are record start/stop triggered: a global hotkey only, or also CLI /
  socket? Is the PTT mode hold-to-record (press/release), or toggle?
- Does the trigger respond to **injected** X11 key events
  (`xdotool keydown … keyup`), under a compositor's grab chain?
- Arch/Manjaro install path: AUR PKGBUILD, dependencies, whisper model
  provisioning; realistic key-release → text latency.

**Output**: feasibility verdict for press/release hotkey injection plus the
recommended mechanism, on `research/handy-x11-arch`, linked from this ticket.
Feeds *Dictation preset spec*.
