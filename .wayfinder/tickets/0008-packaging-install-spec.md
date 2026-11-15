---
title: "Packaging & install spec"
type: wayfinder:grilling
status: open
assignee: jimOnAir
blocked-by:
  - 0001-upstream-port-audit.md
---

## Question

Lock the `vibekey` package shape, given the port audit's keep/replace decisions.

Settle:

- `PKGBUILD` in-repo, single `vibekey` package (daemon + panel + CLI), installed
  with `makepkg -si`; AUR submission stays out of scope.
- runtime dependency list from the port audit (python, PySide6, xdotool, handy,
  …).
- package-owned `/usr/lib/udev/rules.d/…` rule for `fff1:00dd` — **port audit
  rejects upstream's `TAG+="uaccess"`** (Dongle re-enumeration race, session
  dependency): adopt the recommended static `MODE="0660", GROUP="vibekey"` on
  both `hidraw` and `input` subsystems + `sysusers.d` entry + group membership.
  Confirm (or amend) this in the package, no sudo-script either way.
- `vibekeyd.service` user unit (`WantedBy=default.target`, `Restart=always`) —
  must carry `After=graphical-session.target` for `xdotool`'s
  `DISPLAY`/`XAUTHORITY`, per port-audit risk R3.
- config/state paths on this system: `~/.config/vibekey/`,
  `$XDG_RUNTIME_DIR/vibekey/` (upstream's `~/.config/omarchy/vibekey/` moves).
- versioning scheme against upstream; install/upgrade/remove flows;
  `LICENSE`/attribution handling for a public repo.
