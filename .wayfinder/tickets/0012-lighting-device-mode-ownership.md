---
title: "Lighting device-mode ownership"
type: wayfinder:grilling
status: open
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
