---
title: "Dictation preset spec"
type: wayfinder:grilling
status: closed
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

## Answer

All five accepted as recommended (grilling, 2026-11-15):

- **Chord (Q1)**: the Dictation Preset owns its chord (default `ctrl+alt+space`
  = handy's Linux default). The Panel reads handy's config on open; on drift it
  shows a mismatch warning with a **"Fix handy"** button — one-way write into
  handy's config, only on that explicit click (no silent overwrite, per the
  no-config-overwrite line).
- **Prerequisites (Q2)**: Panel status card checks handy's config on open —
  `keyboard_implementation=tauri` and `activation_mode=push_to_talk` shown
  ✓/✗ against the exact config line. The Daemon does **not** gate fires on it.
- **Fallback (Q3)**: none in v1 — the Preset fires as-is; XTEST passive-grab
  activation is spec-guaranteed, and the `--toggle-transcription`/SIGUSR2
  degraded mode was declined (toggle semantics clash with hold UX; a silent
  mode switch confuses more than it saves). Revisit only on a real misfire.
- **handy not running (Q4)**: the Daemon `pgrep`s handy at Preset fire (ms);
  absent → `notify-send "handy is not running"` in place of the WOULD-RAN line.
  Never auto-starts another app.
- **Setup guidance (Q5)**: a **"handy" card in the Panel**: detected values vs
  recommended (`always_on_microphone` ON — first syllable clipping otherwise,
  overlay OFF, model tiers) + copy-paste snippet; read-only apart from Q1's
  consented fix button.
- **Published expectation**: ~0.5–2 s key-up→text (Parakeet, CPU/Vulkan;
  whisper-medium tier is seconds) — goes in docs and the Preset's tooltip.
