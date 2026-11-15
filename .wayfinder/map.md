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

- [Agent-preset design for OpenCode/Orca](tickets/0006-agent-preset-design.md): ✓ = *next Session* and ✕ = *interrupt* fixed; knob press cycles **Knob mode** (default `Scroll, Sessions, Volume`, resets at boot), long-press = Enter; cycle steps the **Ring** of root Sessions, raising each **Host** (Orca `terminal switch` / `wmctrl`); interrupt is hybrid-target (focused window else Cursor), API-first, **never Ctrl+C**; standalone TUIs excluded from v1.
- [OpenCode automation surface](tickets/0003-opencode-surface.md): on v2.2.7 all three agent ops have mechanisms — *interrupt* is a first-class idempotent `POST /api/session/{id}/interrupt` (keystroke fallback Esc only, **never Ctrl+C**); *next/prev* must be composed (API session ring of `ses_…` ids + host resolution via Orca row match or `OC | ` window title); no route publishes `tui.session.select`, and `--standalone` TUIs are API-opaque (title/window route only). Findings on `research/opencode-surface`.
- [handy on X11/Arch](tickets/0002-handy-x11-arch.md): Dictation is feasible — Daemon injects a hold-pair (`xdotool keydown/keyup ctrl+alt+space`) against handy's **Tauri** `push_to_talk` mode (XTEST activates root-window grabs; press+release edges delivered). Pin the `tauri` backend (`handy_keys` never sees XTEST); ~0.5–2 s Parakeet latency; AUR `handy` 0.10.1 packages cleanly on Arch. Findings on `research/handy-x11-arch`.
- [Upstream port audit: compositor-independence check](tickets/0001-upstream-port-audit.md): daemon core verified compositor-independent on X11 (`EVIOCGRAB` silences libinput; hidraw reads stay complete during Grab) → **keep**; replace wtype→`xdotool`, Quickshell Panel, Omarchy preset catalogue, and the udev rule — uaccess loses the Dongle re-enumeration race → static `MODE="0660", GROUP="vibekey"` rule + `sysusers.d`. Findings on `research/upstream-port-audit`.
- [Orca CLI surface](tickets/0004-orca-surface.md): *Orca next-worktree* Preset is CLI-clean — `worktree activate` + `terminal switch` cover it, only window-raise falls to X11 (`wmctrl` by `orca-ide` PID); the Daemon must own the cycle cursor (Orca exposes no "which workspace is displayed" query) and re-list terminal handles per fire. Findings on `research/orca-surface`.

## Not yet specified

- **Firmware-variant confirmation on this actual Dongle** — the port audit
  verified this Dongle's node topology (`hidraw12` + vendor channel + 3 event
  nodes) matches the daemon's assumptions; still open: which knob-turn/press
  detection variant this firmware uses. Needs `vibekeyd --probe` against the
  running port with device access — probably graduates off-map as an
  implementation-time probe, not a decision here.
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
- **Mode-scoped ✓/✕ sets** (✓/✕ following the current Knob mode) — richer
  model than v1 needs; declined in *Agent-preset design for OpenCode/Orca*,
  post-v1 candidate.
