# vibekey — Ulanzi AU05 for Manjaro KDE

Planning effort: turn the [Ulanzi Vibekey AU05](https://www.ulanzi.com/products/au05-vibe-key-ai-voice-input-keypad-i018)
USB keypad into a programmable control surface on a Manjaro Linux / KDE Plasma /
X11 desktop, porting the excellent
[jimmibram/vibekey-driver](https://github.com/jimmibram/vibekey-driver) (Omarchy).

**Status: planning.** The way ahead is charted as a [wayfinder map](.wayfinder/map.md)
with decision tickets in the [local-markdown tracker](.wayfinder/README.md).
No implementation code yet — the map's destination is a buildable `spec.md`.

## Layout

- `.wayfinder/map.md` — the map: destination, decisions so far, fog, out of scope
- `.wayfinder/tickets/` — decision tickets (research / prototype / grilling / task)
- `GLOSSARY.md` — binding vocabulary for all prose and naming
- `research/<name>` branches — findings from research tickets (throwaway; never merged)

## Credits

- Daemon design and protocol work: [jimmibram/vibekey-driver](https://github.com/jimmibram/vibekey-driver), MIT — see [LICENSE](LICENSE)
- AU05 protocol documentation: [MrCroxx/olanzi](https://github.com/MrCroxx/olanzi), [kubja/ulanzi-vibekey](https://github.com/kubja/ulanzi-vibekey)

Not affiliated with Ulanzi.
