---
title: "Packaging & install spec"
type: wayfinder:grilling
status: closed
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

## Answer

All six accepted as recommended (grilling, 2026-11-15):

- **Package & deps**: single `vibekey` package (daemon + Panel +
  `vibekey-config` CLI), installed `makepkg -si`;
  `depends=(python pyside6 xdotool wmctrl libnotify)` — note the Arch package
  is **`pyside6`**, not `python-pyside6` (verified via `pacman -Qs`, 6.11.2-2
  installed); `optdepends=(handy: Dictation Preset — AUR, never hard-depended;
  orca: agent Presets)`.
- **udev + group**: package-owned `/usr/lib/udev/rules.d/70-ulanzi-vibekey.rules`
  — `fff1:00dd` on **both** `hidraw` and `input` subsystems, static
  `MODE="0660", GROUP="vibekey"` (port audit rejected uaccess); `sysusers.d`
  creates the group; the one manual step `gpasswd -a $USER vibekey` (+ re-login)
  is documented **and detected** — Daemon/Panel on EACCES print the exact
  command. No sudo-script.
- **Daemon unit**: `/usr/lib/systemd/user/vibekeyd.service`
  (`WantedBy=default.target`, `Restart=always`, `After=graphical-session.target`
  — port-audit R3: `xdotool` needs `DISPLAY`/`XAUTHORITY`; `spawn()` swallows
  failures silently). Enablement: README one-liner
  `systemctl --user enable --now vibekeyd`, or the **first-run Panel button**
  (Panel runs as the user, so it may enable).
- **Panel autostart**: checkbox **"Launch at login"** → writes standard
  `~/.config/autostart/vibekey-panel.desktop`; reversible from KDE's own UI.
  (Closes the packaging-side autostart fog.)
- **Paths**: config `~/.config/vibekey/`, state/preview heartbeat
  `$XDG_RUNTIME_DIR/vibekey/`.
- **Versioning**: own tag series from **0.1.0**; PKGBUILD `source=` = GitHub
  archive of our tag; upstream commit pinned in an `UPSTREAM` file + README
  credit; MIT `LICENSE` retained (upstream copyright notice intact).
- **Uninstall**: standard Arch semantics — `pacman -Rns` removes what the
  package owns; user state (config dir, autostart file, group membership,
  enabled unit) survives; the full teardown (disable unit, `gpasswd -d`, drop
  configs) is one README section.
