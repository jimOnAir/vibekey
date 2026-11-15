---
title: "Upstream port audit: compositor-independence check"
type: wayfinder:research
status: open
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
