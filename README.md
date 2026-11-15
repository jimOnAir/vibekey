# vibekey — Ulanzi AU05 for Manjaro KDE

Planning effort: turn the [Ulanzi Vibekey AU05](https://www.ulanzi.com/products/au05-vibe-key-ai-voice-input-keypad-i018)
USB keypad into a programmable control surface on a Manjaro Linux / KDE Plasma /
X11 desktop, porting the excellent
[jimmibram/vibekey-driver](https://github.com/jimmibram/vibekey-driver) (Omarchy).

**Status: planning done — [spec.md](spec.md) is the buildable spec** (wayfinder
ticket 9, the map's destination). The map and its decision tickets stay as the
provenance record; one lighting sub-question remains open in
[ticket 0012](.wayfinder/tickets/0012-lighting-device-mode-ownership.md).
No implementation code yet — implementation sessions work from `spec.md`.

## Layout

- `spec.md` — **the buildable spec** (architecture, config/preset schema, packaging, verification checklist)
- `.wayfinder/map.md` — the map: destination, decisions so far, fog, out of scope
- `.wayfinder/tickets/` — decision tickets (research / prototype / grilling / task)
- `GLOSSARY.md` — binding vocabulary for all prose and naming
- `research/<name>` branches — findings from research tickets (throwaway; never merged)

## Credits

- Daemon design and protocol work: [jimmibram/vibekey-driver](https://github.com/jimmibram/vibekey-driver), MIT — see [LICENSE](LICENSE)
- AU05 protocol documentation: [MrCroxx/olanzi](https://github.com/MrCroxx/olanzi), [kubja/ulanzi-vibekey](https://github.com/kubja/ulanzi-vibekey)

Not affiliated with Ulanzi.
