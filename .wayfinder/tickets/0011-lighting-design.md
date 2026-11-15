---
title: "Lighting design: ring, blink, battery"
type: wayfinder:grilling
status: closed
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

## Answer

All accepted as recommended (grilling, 2026-11-15):

- **Ring = Knob-mode indicator**: `Scroll → off` (the common default stays
  silent; off is never ambiguous — it means "needs no attention"),
  `Sessions → solid:8` (a Session is live), `Volume → breathe:8` (transient
  adjustment); any custom mode without a pattern → `off`. Defaults editable.
- **Failure blink**: **the keycap of the culprit Control** blinks three fast
  times (b16); ring untouched; no ambient blinks — only reactions to presses.
  (Fire-time blinks dodge the standby gotcha entirely: if the user pressed a
  key, the device is awake.)
- **Low battery**: ≤10% → ring `breathe:6` while it lasts + **one** notify-send
  per crossing; hysteresis resets at >20%.
- **Panel surface**: one Lighting section — three switches (mode-ring /
  failure-blink / battery-blink) + one global brightness slider. Pattern
  editing stays in `config.json` (no pattern editors in the Panel).
- **Config schema** (accepted as drafted):

  ```json
  "lighting": {
    "mode_ring": true, "fail_blink": true, "low_battery": true,
    "brightness": 1.0,
    "patterns": { "Scroll": "off", "Sessions": "solid:8", "Volume": "breathe:8" }
  }
  ```

  `effect:brightness` strings; hot-reloaded by the existing config watcher.
- **Architecture confirmed**: single-writer `lighting` module serialising
  Preset-emitted lighting events over shared global device state (0010).
