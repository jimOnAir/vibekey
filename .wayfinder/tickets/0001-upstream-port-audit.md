---
title: "Upstream port audit: compositor-independence check"
type: wayfinder:research
status: closed
assignee: jimOnAir
blocked-by: []
branch: research/upstream-port-audit
---

## Question

Is the upstream daemon truly compositor-independent, and what must be replaced?

Take inventory of every Wayland/Omarchy-specific touchpoint in
[jimmibram/vibekey-driver](https://github.com/jimmibram/vibekey-driver)
(`wtype` call sites, the Quickshell panel, `$XDG_RUNTIME_DIR/vibekey` paths,
`~/.config/omarchy/vibekey/` config, any environment assumptions), and verify
each port assumption against this system (Manjaro, KDE, X11, AU05 on
`/dev/hidraw12`+`/dev/hidraw13` with no uaccess ACL):

- Does `EVIOCGRAB` on the keypad's evdev nodes keep its keystrokes away from
  **X11/libinput**, and is `hidraw` report reading still complete while the
  evdev node is grabbed?
- Do **systemd user services** get the udev `uaccess` ACL — and does access
  survive the dongle's periodic reboot/re-enumeration (observed on this box:
  after re-enumeration the ACL vanished entirely)?
- Does `xdotool` cover the injection surface `wtype` provided (key combos,
  hold/release pairs for press/release presets, repeat suppression)?

**Output**: a port-risk list on `research/upstream-port-audit`, with an explicit
*keep / replace* decision per component, linked from this ticket. Feeds
*Packaging & install spec*.

## Answer

**The daemon core is truly compositor-independent — KEEP it; all compositor
coupling sits in one argv builder, the Quickshell Panel, and the Omarchy preset
catalogue.** Full evidence: [`research/upstream-port-audit`](https://github.com/jimOnAir/vibekey/blob/research/upstream-port-audit/research/upstream-port-audit.md) (`f6e7473`).

- **Grab/hidraw on X11 — holds.** `EVIOCGRAB` is enforced in the kernel input
  core, so libinput (X11's path) receives nothing while grabbed; and hidraw
  copies raw reports *before* the input layer dispatches them — report reading
  stays complete during the Grab. This Dongle's topology verified against the
  daemon's assumptions.
- **Device access — uaccess rejected.** ACLs are UID-based (a user service
  would be covered), but nothing on this box tags `fff1:00dd`, and the Dongle
  re-enumerates constantly (journal: 19 reboots in 2.2 min) recreating nodes at
  root-only defaults. Even upstream's `TAG+="uaccess"` rule has a boot/greeter
  race bad for a headless service. **Recommendation: static package rule
  `MODE="0660", GROUP="vibekey"` on both `hidraw` and `input` subsystems, plus
  `sysusers.d` and group membership** — deterministic at node creation,
  session-independent.
- **wtype → xdotool — 1:1.** Upstream's whole injection surface is one-shot
  combos built at `vibekeyd:425-447`; hold/release Presets (PTT) use
  `command`/`release_command`, not keys. `xdotool key <combo>` covers it
  (`logo→super`, `altgr→ISO_Level3_Shift`); the keysym table is kept verbatim.
- **Keep/replace**: keep the device core, `actions.json` *schema*,
  config/state file protocol, `vibekey-config`; replace the wtype argv, the
  `actions.json` *contents* (38 `omarchy-*` presets → KDE/handy/OpenCode), the
  udev rule, the Quickshell Panel + QML + IPC, `install.sh` (→ PKGBUILD), and
  `vibekey-herdr-agent`.
- **Live confirmation (owner report + journal, 20:20:36–45)**: the Dongle
  re-enumerates on a constant ~3.5 s cycle even with no input — it is the
  documented watchdog, *not* knob-press-triggered; button presses that land in
  a reboot window silently vanish, which is what "reconnects when I press the
  knob" actually was. The Daemon holding both channels open (upstream design)
  is the cure; implementers shouldn't chase a phantom knob bug.
- **Top risks**: 🔴 no device access as currently configured (fixed only by the
  package rule) · 🔴 shipped defaults *are* Omarchy commands · 🔴 `xdotool`
  needs `DISPLAY`/`XAUTHORITY` in the user service (present via Plasma's env
  import, probed) — unit must `After=graphical-session.target`, since `spawn()`
  swallows failures silently.
