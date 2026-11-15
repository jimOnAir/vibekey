---
title: "Lighting design: ring, blink, battery"
type: wayfinder:grilling
status: open
assignee: jimOnAir
blocked-by: []
---

## Question

Turn *Backlight control*'s feasibility into v1 behaviour (owner decided:
**all three in v1**). Ground facts are settled — 4 monochrome channels,
mode/effect/brightness 0–20, `0x14` ack, writes dropped in standby,
device-side persistence. Decide:

- **Ring = Knob-mode indicator**: the pattern per mode for the v1 defaults —
  Scroll / Sessions / Volume (candidates: distinct breathe rates, brightness
  levels, or effect combos — monochrome means patterns carry meaning; keep
  them distinguishable at a glance). Custom knob modes with no ring pattern →
  default?
- **Failure blink**: which preset failures get a blink (✕ with no Sessions?
  next/Session with no service? Dictation with handy absent?) — every failure
  vs only ones the user just performed an action for; pattern (e.g. three
  fast blinks on the ring? keycap of the pressed Control?) and the standby
  caveat (missed while asleep — acceptable?).
- **Low-battery**: threshold %, what indication where (ring vs Panel only vs
  both), and hysteresis so it doesn't blink forever.
- **Panel affordance**: a Lighting section (enable/disable ring indicator,
  brightness scale, per-feature toggles) — how much before it's
  over-settings?
- **Config schema**: the lighting block in `config.json` (defaults + off
  switches), hot-reload behaviour.
- Write discipline recap for the spec: single-writer module serialising
  Preset-emitted lighting events (from 0010's recommendation) — confirm as
  architecture.
