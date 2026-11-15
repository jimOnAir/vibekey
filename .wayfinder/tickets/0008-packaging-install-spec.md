---
title: "Packaging & install spec"
type: wayfinder:grilling
status: open
assignee:
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
- package-owned `/usr/lib/udev/rules.d/…` rule (`fff1:00dd`, uaccess — no
  sudo-script) and `vibekeyd.service` user unit (`WantedBy=default.target`,
  `Restart=always`).
- config/state paths on this system: `~/.config/vibekey/`,
  `$XDG_RUNTIME_DIR/vibekey/` (upstream's `~/.config/omarchy/vibekey/` moves).
- versioning scheme against upstream; install/upgrade/remove flows;
  `LICENSE`/attribution handling for a public repo.
