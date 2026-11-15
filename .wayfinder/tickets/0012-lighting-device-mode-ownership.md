---
title: "Lighting device-mode ownership"
type: wayfinder:grilling
status: closed
assignee: jimOnAir
blocked-by: []
---

## Question

*Backlight control* (`research/backlight-control`, §6.2) explicitly carried this
to the spec: the AU05's lighting has a **device-global mode** — `0` all-off,
`1` all-on, `2` work/active — and per-light fields (effect type, breathe/always-on
brightness) are only visible when the device sits in mode `2`. Ulanzi Studio (or
a factory state) may leave the user's unit in mode `0`/`1`, in which case every
write vibekeyd makes is invisible. The research note's rule — never silently
flip the user's mode — is binding; the *positive* design is open:

- Does the Daemon **read mode at startup and act as guest or owner**? If the
  device is in mode 0/1, does vibekeyd (a) skip lighting writes entirely and
  surface why, (b) propose a one-time "let vibekeyd manage lights" action that
  writes mode 2, or (c) write per-light fields regardless (invisible until the
  user switches back)?
- If a management action exists: it needs a Panel affordance — but ticket 11
  settled the Lighting section at **three switches + one slider, nothing more**.
  Does this add a fourth control, fold into an existing switch, or appear
  contextually (only while mode ≠ 2)?
- Who owns **global brightness** (mask `0x02`, the all-on-mode level)? The
  config `brightness` multiplier is specced (spec §4); does the Panel slider
  ever write the device's own global-brightness field, or is that Studio's?
- What goes into `state.json` `lighting` / the Panel status line when vibekeyd
  detects a mode it does not own?

Closes the last open subsection of `spec.md` §5.5. Ground rules already set:
4 monochrome channels, mode 2 = per-light, no silent flips, single-writer
module, ack-confirmed writes (`0x14`).

## Answer

All seven accepted as recommended (grilling, 2026-11-15):

- **Posture (Q1)**: **guest with one consented Manage lights** — read the
  Device lighting mode by GET at connect; mode 0/1 → all lighting policies
  idle + Panel line + contextual button (ack-confirmed write of mode 2, then
  apply the current pattern; no ack → "press any key, try again", no
  auto-retry); one `notify-send` per Daemon **start** (never per Dongle
  re-enumeration) only when mode known ≠ 2 and ≥1 lighting switch on; **no
  consent memory** — every connect re-reads, Studio drift handled the same
  way, revert stays the user's side (no "give back" offered).
- **Panel affordance (Q1 cont.)**: contextual line + button inside the existing
  Lighting section only while mode ≠ Working — ticket 11's
  "three switches + slider" scope untouched in the normal case.
- **Mask ownership (Q2)**: vibekeyd owns `0x04`/`0x20`/`0x40`
  (read-modify-write), writes `0x01` (mode) **only** via consent, **never**
  `0x02` (device global brightness); the Panel slider is the config
  `lighting.brightness` multiplier alone.
- **Unknown mode (Q3)**: optimistic — treat as Working with a lazy re-GET at
  the first Control event after a boot/reconnect that left it unknown (and on
  feature-enabling hot-reload); `state.json` `lighting.device_mode:
  0|1|2|"unknown"|"disabled"`.
- **All switches off (Q4)**: total vendor silence — no lighting GET at all,
  `device_mode: "disabled"`, no notify; hot-reload-on re-GETs immediately.
- **Vocabulary**: `GLOSSARY.md` gains **Device lighting mode** and
  **Manage lights** (Avoid-lists included).

Landed as `spec.md` §5.5 (+ §3 `device_mode`, §8 contextual affordance, §10
item 12 bench lines) — **spec complete, frontier empty, map at destination.**
