---
title: "Dictation preset spec"
type: wayfinder:grilling
status: open
assignee: jimOnAir
blocked-by:
  - 0002-handy-x11-arch.md
---

## Question

Lock the dictation preset, given handy's verified mechanism (vibekey stays just
the finger — no coupling into handy's pipeline).

Settle:

- Chord ownership: the Preset carries its own `ctrl+alt+space` (or
  user-configured chord) — how is the chord configured per Assignment, and
  what guarantees it matches handy's configured hotkey (defaults aligned;
  does the Panel detect/repair a mismatch, or only warn)?
- Pin handy's `keyboard_implementation = tauri` (the `handy_keys` backend
  never sees XTEST) — is that a documented precondition, a Panel check, or
  both?
- `push_to_talk` mode required; `hold_or_toggle`'s 300 ms threshold rejected
  or kept as a user option? Fallback policy when injection fails: toggle via
  CLI (`handy --toggle-transcription`) / `SIGUSR2`, or refuse and report?
- behaviour when handy is not running, and what the Panel/OSD says.
- Panel guidance for the two handy settings that shape perceived quality:
  `always_on_microphone` (first-syllable clipping) and overlay-off.
- Latency expectation to publish: ~0.5–2 s key-up→text (Parakeet, CPU/Vulkan).
