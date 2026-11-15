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

- Daemon design and protocol work: [jimmibram/vibekey-driver](https://github.com/jimmibram/vibekey-driver), MIT — see [LICENSE](LICENSE)
- AU05 protocol documentation: [MrCroxx/olanzi](https://github.com/MrCroxx/olanzi), [kubja/ulanzi-vibekey](https://github.com/kubja/ulanzi-vibekey)

Not affiliated with Ulanzi.
