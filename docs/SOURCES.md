# Protocol & Hardware Sources

Every protocol fact this project relies on traces to one of these sources.
Confidence labels are the sources' own (device-observed / static-confirmed /
captured / measured / unverified). When we extend the daemon to a command,
cite the source line in the commit message.

## Primary reverse-engineering references

| Source | What it gives us | Key detail |
|---|---|---|
| [MrCroxx/olanzi](https://github.com/MrCroxx/olanzi) `docs/02-vibekey-protocol.md` | TEA key, frame format, cmd routing (`0x01` mic vs `0x06` dongle), control mapping, the on-device key table (`01 06 50`), **mic-link status query `06 03 0a 01`**, noise-reduction query `01 01 90 01` | measured end-to-end; 63-vs-64-byte truncation explained; heartbeat `06 01 23 00 01` semantics |
| [arumwu/vibekey-lite](https://github.com/arumwu/vibekey-lite) `docs/protocol.md` | same TEA/frames independently confirmed; **standby delay `01 01 2C 01`** and **sleep delay `01 01 42 01`** read layouts (u32-le seconds at offset 4, observed 300 s / 3600 s); raw key notice `0B 10` layout; host-online/handshake caveats | static-confirmed from Studio 3.3.6 + device-observed GETs; explicitly never sends SETs for the power values |
| [ihavespoons/vibed](https://github.com/ihavespoons/vibed) `docs/PROTOCOL.md` | **the SET counterparts**: standby time `01 01 2C 02 [u32]`, sleep time `01 01 42 02 [u32]`, standby state `01 01 0D 00/01`, **mic enable `01 01 2A`**, **noise reduction SET `01 01 90 04 [level][low u16][high u16]`**, motor `01 06 40`, audio button mode `01 06 51`, session auth `06 02 05`, notice table (link `0B 0B`, standby `0B 0D`, key `0B 10`, battery `0B 7B`, noise `0B 83`) | Studio 3.3.9 disassembly + **captured on firmware 4.4.0**; lists which writes read back changed (sleep time, noise reduction, light mode, work type/time/breathe level) and which are acknowledged-but-inert (motor, hooks, breathe brightness, always-on brightness) |
| [jimmibram/vibekey-driver](https://github.com/jimmibram/vibekey-driver) | the Daemon's skeleton we ported: evdev grab, hidraw vendor channel, battery poll, TEA codec | pinned in [UPSTREAM](../UPSTREAM); MIT |
| [kubja/ulanzi-vibekey](https://github.com/kubja/ulanzi-vibekey) | cross-check on key codes/protocol shape | referenced from spec §1 research |
| Ulanzi official docs (mirrored at manuals.plus; §1.3, §2.5, §2.9 quoted via olanzi/vibekey-lite) | standby behaviour ("five minutes without input → low-power standby and disconnects"), settings persistence, Studio offline limits | vendor statements, quoted by both RE projects |

## Commands now used by vibekeyd (implemented)

| Command | Source | Status on our firmware (4.4.2) |
|---|---|---|
| `01 01 02 01` battery GET | all three | works since v0.1.0 |
| `01 0B 88 01` / `04 …` lighting GET/SET | olanzi + vibed | works (spec §5.5), write-verified 2026-11-15 |
| `06 03 0A 01` mic-link GET (dongle answers even when mic off) | olanzi | **deployed** — replaces the 40 s silence heuristic with instant truth |
| `01 01 2C 01`/`02` standby delay GET/SET | vibekey-lite read + vibed SET | **deployed** — Panel setting |
| `01 01 42 01`/`02` sleep delay GET/SET | vibekey-lite read + vibed SET | **deployed** — Panel setting |
| `01 01 90 01`/`04` mic noise reduction GET/SET | olanzi read + vibed SET | **deployed** — Panel slider; readback-verified on 4.4.0 |
| `01 01 0D 01` standby state GET | vibekey-lite | deployed as state telemetry |

## Commands deliberately NOT used

- `01 01 2A` mic enable: **field-tested dead on our unit (fw 4.4.2,
  2026-11-15)** — reads 0 while the mic empirically streams audio (capture:
  62500/64000 non-zero samples with the keypad online), and SET [0|1] does not
  stick. The Panel initially surfaced it as "mic DISABLED on device"; that
  badge was a false positive and was removed. Lesson kept: a flag we cannot
  correlate with ground truth must not drive UI.
- `06 01 23 00 01` heartbeat + `01 01 10 00 03` host-online: flips keys from
  standard HID into vendor notices — our Daemon consumes standard HID and
  would have to re-implement every binding in the host. We stay invisible.
- `01 06 50` key-table rewrites: on-device remapping would break other hosts
  silently; vibekeyd's whole model is host-side Assignments.
- `01 06 40` motor: acknowledged but inert on 4.4.0 (vibed capture).
- `01 0B 89` hooks mode: Studio-AI-specific, inert without Studio.
- Firmware update (`0x1E`/`0x1F`): never.

## Verification habit

Protocol claims are cheap; devices disagree. Before shipping any *write*:
GET first, show the current value in the Panel, write only by consent
(the Manage-lights pattern), then GET again and surface readback mismatch as
`last_error`. The vibed "acknowledged but read back unchanged" list is the
warning poster for this rule.
