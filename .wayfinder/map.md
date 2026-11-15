---
title: "Wayfinder map: vibekey for Manjaro KDE — Ulanzi AU05 driver port"
label: wayfinder:map
---

# Wayfinder map: vibekey for Manjaro KDE — Ulanzi AU05 driver port

## Destination

A locked, buildable **spec** (`spec.md` at the repo root) for porting the MIT-licensed
[jimmibram/vibekey-driver](https://github.com/jimmibram/vibekey-driver) to this
system — `vibekeyd` daemon, PySide6 tray panel, handy dictation, OpenCode/Orca
agent presets, `vibekey` package with udev rule + systemd user service — with
zero open decisions when the map is done. Implementation follows in fresh
sessions; nothing on this map builds it.

## Notes

- **System**: Manjaro Linux, KDE Plasma, **X11** session. AU05 dongle present as
  USB `fff1:00dd` (`/dev/hidraw12`, `/dev/hidraw13`), currently `root:root 0600` —
  no uaccess ACL (the dongle re-enumerates on its periodic reboot and loses it).
- **Source**: upstream is MIT; attribution and its copyright notice stay in
  `LICENSE`/`README`. Protocol knowledge credited to
  [MrCroxx/olanzi](https://github.com/MrCroxx/olanzi) and
  [kubja/ulanzi-vibekey](https://github.com/kubja/ulanzi-vibekey).
  This repo is **public** — nothing secret, ever.
- **Skills**: `research` tickets → load skill `research`; `prototype` → `prototype`;
  `grilling` → `grilling` + `domain-modeling`. `GLOSSARY.md` is binding for all
  ticket prose, decisions, and naming.
- **Plan, don't do**: the only deliverable is the spec (ticket 9). No
  implementation code lands on `master` from a ticket.
- **Settled at charting** (from grilling rounds 1–2 — don't relitigate; design
  tickets refine *within* these): destination = spec; **port** upstream rather
  than rewrite; **PySide6** tray app replacing the Quickshell panel; `wtype` →
  `xdotool`; package-owned udev rule + `vibekeyd.service` **user** unit; single
  `vibekey` package installed with `makepkg -si`; dictation = handy stays the
  STT app, vibekey injects its PTT hotkey on press / releases on key-up; agent
  preset vocabulary = next/prev OpenCode session, focus the agent's terminal,
  interrupt, stretch: Orca next-worktree.

## Decisions so far

<!-- one line per closed ticket: name + gist + link -->

- [Orca CLI surface](tickets/0004-orca-surface.md): *Orca next-worktree* Preset is CLI-clean — `worktree activate` + `terminal switch` cover it, only window-raise falls to X11 (`wmctrl` by `orca-ide` PID); the Daemon must own the cycle cursor (Orca exposes no "which workspace is displayed" query) and re-list terminal handles per fire. Findings on `research/orca-surface`.

## Not yet specified

- **Firmware-variant confirmation on this actual dongle** — knob-turn/press
  detection has firmware variants; settling which this unit uses needs
  `vibekeyd --probe` against a running port with device access. Probably
  graduates off-map as an implementation-time probe, not a decision here.
- **KDE tray autostart UX for the panel** (the daemon's autostart is settled;
  the panel's is not).
- **Non-US keyboard layout handling** for key-combo assignments.
- **Vendor-channel capabilities beyond battery** reading — worth anything else
  on `0x55`/vendor reports is unknown until the port audit lands.
- **Panel↔daemon IPC upgrade** if file-based state (`state.json`, preview
  heartbeat) proves annoying in the prototype.

## Out of scope

- **herdr presets** — replaced by OpenCode/Orca presets for this port; upstream
  keeps them on Omarchy.
- **Wayland / Quickshell surfaces** — the system is X11; not this effort's target.
- **Windows / macOS** — Linux, this machine.
- **Omarchy marketplace listing** — upstream already owns that.
- **AUR submission** — a `PKGBUILD` living in the repo is in scope; publishing
  to AUR is a later, separate effort.
