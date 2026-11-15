# vibekey — Ulanzi AU05 for Manjaro KDE

Planning effort: turn the [Ulanzi Vibekey AU05](https://www.ulanzi.com/products/au05-vibe-key-ai-voice-input-keypad-i018)
USB keypad into a programmable control surface on a Manjaro Linux / KDE Plasma /
X11 desktop, porting the excellent
[jimmibram/vibekey-driver](https://github.com/jimmibram/vibekey-driver) (Omarchy).

**Status: implementation in progress** on the `impl/port` branch, built from
[spec.md](spec.md) (the wayfinder map's destination — all 12 tickets closed).
The map and its decision tickets stay as the provenance record.

## Layout

- `spec.md` — **the buildable spec** (architecture, config/preset schema, packaging, verification checklist)
- `bin/vibekeyd`, `bin/vibekey-config` — the daemon (ported device core + behaviors + lighting) and config CLI
- `actions.json` — the KDE/handy/OpenCode/Orca preset catalogue
- `panel/` — the PySide6 Panel (Variant A drawn device) + icons + `.desktop`
- `PKGBUILD`, `systemd/`, `udev/`, `sysusers/` — packaging per spec §9
- `UPSTREAM` — the pinned audited upstream commit
- `.wayfinder/map.md` — the map: destination, decisions so far, fog, out of scope
- `.wayfinder/tickets/` — decision tickets (research / prototype / grilling / task)
- `GLOSSARY.md` — binding vocabulary for all prose and naming
- `research/<name>` branches — findings from research tickets (throwaway; never merged)

## Credits

- Daemon design and protocol work: [jimmibram/vibekey-driver](https://github.com/jimmibram/vibekey-driver), MIT — see [LICENSE](LICENSE); pinned commit in `UPSTREAM`
- AU05 protocol documentation: [MrCroxx/olanzi](https://github.com/MrCroxx/olanzi), [kubja/ulanzi-vibekey](https://github.com/kubja/ulanzi-vibekey)

Not affiliated with Ulanzi.

## Install (spec §9)

```bash
makepkg -si                      # builds + installs the vibekey package
gpasswd -a $USER vibekey         # the ONE manual step; then re-login
systemctl --user enable --now vibekeyd
```

> **Re-login vs reboot:** a plain logout only restarts your desktop session — the
> *user manager* (`user@1000.service`), which is what hands the new group to
> `vibekeyd.service`, survives logout when **Linger is enabled** or another
> session (e.g. an agent/SSH one) is still open. If `systemctl --user status
> vibekeyd` still shows `access: "denied"` after re-login (`state.json` says the
> same), **reboot** — or stop every session and `systemctl --user daemon-reexec`
> is *not* enough (proven: re-exec keeps the manager's credentials).

`xdotool wmctrl libnotify python pyside6` come in as deps; **handy 0.10.1** (the
audited release — AUR `handy`) and `orca` are optdepends: install handy for the
Dictation Preset, and follow the Panel's **handy card** (tauri backend,
push_to_talk, always-on mic, overlay off). The Panel can also enable the unit
for you on first run (its button) and offers **Launch at login**.

## Uninstall / teardown (spec §9)

`pacman -Rns vibekey` removes what the package owns; user state survives by
design (config, autostart, group membership, unit). Full teardown:

```bash
systemctl --user disable --now vibekeyd
gpasswd -d $USER vibekey
rm ~/.config/autostart/vibekey-panel.desktop
rm -rf ~/.config/vibekey
```
