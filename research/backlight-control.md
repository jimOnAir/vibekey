# Backlight control: keycap indicator lights + knob ring (ticket 0010)

**Question:** the AU05 has glowing keycaps and a light ring around the knob; Ulanzi
Studio demonstrably drives them. Can our planned Daemon drive them too — per-light
on/off, colour, mode, brightness — from user-space on Linux, while the evdev nodes
are Grab-ed?

**Sources audited** (cloned to `/tmp/opencode/`, not vendored):

| Source | Commit (date) | What it contributes |
|---|---|---|
| `jimmibram/vibekey-driver` (upstream) | `41ba904b` (2026-10-28) | TEA key already in the ported code; **the Daemon already writes encrypted vendor frames over `/dev/hidraw13` on Linux while its evdev nodes are EVIOCGRAB-ed** (battery poll) |
| `MrCroxx/olanzi` | `eb78f88` (2026-10-09) | Full protocol docs (TEA key from `kwdm.dylib` disassembly, frame format, command table) **and a shipped, hardware-verified lighting read/write implementation** (Swift, macOS) |
| `arumwu/vibekey-lite` | `43fb901` (cited by olanzi) | `docs/protocol.md`: static-confirmed indicator-LED command table from Studio 3.3.6 with per-field offsets; device-observed power/standby values |
| `palaemonboy/OpenVibeKey` | `c6466fd` | Second independent shipped implementation; hardware-tested LED order, write gotchas (full 4-slot records, breath params), data-driven Studio command table |
| `kubja/ulanzi-vibekey` | `007fd4b` (2026-10-25) | USB endpoint topology doc. **No lighting content and no vendor writes at all** (typist-only project) |
| Ulanzi official docs | `docs.ulanzistudio.com/vibekey/en/au05`, FAQ `codex-claude-status.html` (2026-11) | First-party lighting semantics: the three modes, "status lighting requires Ulanzi Studio to keep running", per-light agent-status spec, standby behaviour, Studio's own Light Effect UI (mode + brightness, no colour) |
| Linux kernel `v7.2` | torvalds/linux | hidraw write semantics, hidraw ↔ input-layer independence (this box runs `7.2.9-1-MANJARO`) |
| ticket 0001 findings | `research/upstream-port-audit` | node topology verified on this Dongle (`hidraw12`=/input2, `hidraw13`=/input3), EVIOCGRAB mechanics, udev-rule decision |

**Domain terms** per `GLOSSARY.md`: *Control*, *Dongle*, *Daemon*, *Preset*,
*Knob mode*. The hardware ring around the knob is called **knob ring** throughout —
**Ring** (capitalised) is reserved for the Daemon's Session cycle and means something
else here. Following olanzi's own glossary (AGENTS.md:125), the lights are **indicator
lights** — four addressable channels: K1 (Voice), K2 (✓ Confirm), K3 (✕ Cancel), knob.

---

## Verdict (answers the ticket question)

**Documented — and already implemented by two independent open-source projects
against real hardware.** The lighting control surface is a TEA-encrypted vendor
channel (`0x55` output reports) whose key, frame format, GET/SET commands, field
offsets and effect semantics are fully published; nothing needs reverse-engineering.
The write path from our Daemon is not just possible, it is a small extension of code
upstream already runs on this OS today (`bin/vibekeyd:649-653`).

**One premise correction:** there is no colour control. The entire known command
family carries no colour byte, Studio's own Light Effect UI is mode + brightness
only, and per-AI-state lighting is implemented as *effect patterns* (on / breathe /
off) on four **monochrome-by-API** channels. The map's fog item "mode → ring colour"
must be re-scoped to "Knob mode → knob-ring **pattern** (on/off, maybe breathe)".
Red blink on error is likewise not available — only flash the device's own light.

Feasibility: (a) Knob-mode→knob-ring **yes (patterns, not colours)**, (b) failure
feedback **yes (monochrome flash)**, (c) battery-low indicator **yes (trivial once
the subsystem exists)**. Cost/risk table in §5.

---

## 1. Q1 — Is the LED command set documented? Yes, in full.

### 1.1 Transport: TEA-encrypted 0x55 reports (both directions)

- Vendor interface (interface 3) HID descriptor: **Input report `0x55`, 63 bytes AND
  Output report `0x55`, 63 bytes** (olanzi `docs/02-vibekey-protocol.md:44-51`).
  Payload is **TEA-encrypted (not XTEA), ECB, 8-byte blocks, 32 rounds,
  delta `0x9E3779B9`, key `ca ba a5 ca 6d 8a 2a bc ba 9e 5a ca ca 8b b8 9b`** —
  extracted from `_gaui_custom_encrypt_keys` in Ulanzi Studio's `kwdm.dylib` and
  published with a decisive verification vector
  (olanzi `docs/02-vibekey-protocol.md:57-78`).
- **The same key is already in the code we are porting**:
  `TEA_KEY = struct.unpack("<IIII", bytes.fromhex("cabaa5ca6d8a2abcba9e5acaca8bb89b"))`
  (`vibekey-upstream/bin/vibekeyd:139`; identical words in
  `olanzi/native/Sources/OlanziCore/DeviceProtocol.swift:35`). So the ticket's
  "check if the code/docs reveal the key derivation" resolves: yes, twice.
- 63-vs-64 framing (both projects, byte-identical): pad plaintext to 64 B, TEA the
  whole 64, **transmit only the first 63 bytes** (the 64th ciphertext byte never
  crosses the wire); on read, decrypt only the first 56 B (7 blocks) and treat the
  remainder as zero (olanzi `docs/02-vibekey-protocol.md:80-90`,
  `DeviceProtocol.swift:76-88`; upstream `bin/vibekeyd:174-185`).

### 1.2 Frame format and the lighting commands

Plaintext frame (after decrypt): `frame[0]` cmd (`&0x1F`; cmd `0x01` = handled by the
keypad over the 2.4 GHz link), `frame[1]` group (`0x0B` = notice/config), `frame[2]`
opcode, `frame[3]` access (`0x01` read, `0x04` write; replies set `0x80` and OR
`0x10` into access, so a write ack carries `0x14`), `frame[4..]` params (olanzi
`docs/02-vibekey-protocol.md:95-124`).

The indicator-light family is group `0x0B` opcode `0x88` — one GET, seven SET
sub-commands selected by a field-mask byte (`vibekey-lite/docs/protocol.md:270-296`,
static-confirmed from Studio 3.3.6; implemented + hardware-exercised in
`olanzi/native/Sources/OlanziCore/DeviceLighting.swift:44-113` and
`OpenVibeKey/…/VibeKitDevice.swift:92-132`; the seven Studio builder names are in
OpenVibeKey's data-driven table `protocol-commands.json`:
`setDeviceIndicatorLightCurrentMode / AllOnModeBrightnessLevel / WorkModeType /
WorkModeTime / WorkModeBreatheLevel / WorkModeBreatheBrightnessLevel /
WorkModeAlwaysOnBrightnessLevel`):

```text
GET all:   01 0b 88 01 00 ...
→ reply:   81 0b 88 11 ?? ?? mode bright  [type workTime level brBright onBright] ×4
SET:       01 0b 88 04 fieldMask ledIndex mode bright  [4 × 5-byte records] ...
→ ack:     81 0b 88 14 … (echoes request; verify at the masked field's offset)
```

| Mask | Value offset | Meaning |
|---|---|---|
| `0x01` | frame[6] | lighting mode: `0` all-off, `1` all-on, `2` work/active (per-light) — labels confirmed by Studio UI (`LightingSettingsView.swift:42`) and official docs §2.4 (Always On / Always Off / Working, Working = factory default) |
| `0x02` | frame[7] | global brightness, all-on mode |
| `0x04` | `8 + 5·ledIndex` | per-light effect type: `0` off, `1` always-on, `2` breathing |
| `0x08` | `9 + 5·ledIndex` | work time (unit undocumented) |
| `0x10` | `10 + 5·ledIndex` | breathing level (unit undocumented) |
| `0x20` | `11 + 5·ledIndex` | per-light breathing brightness |
| `0x40` | `12 + 5·ledIndex` | per-light always-on brightness |

(vibekey-lite `docs/protocol.md:274-292` — mask table incl. `0x08`/`0x10`, which
olanzi deliberately never writes (only their type/brightness masks;
`DeviceLighting.swift:95` refuses to change `workTime`/`breatheLevel`);
offsets identical in `DeviceLighting.swift:50-75`.)

`ledIndex 0..3` = the four lights. **Index↔physical light is corroborated three
ways**: olanzi labels them 键1/键2/键3/旋钮 (`DeviceLighting.swift:27`,
`LightingSettingsView.swift:79`); OpenVibeKey comment "灯序 [btn1,btn2,btn3,dial]
= index 0..3" (`VibeKitDevice.swift:104`); and the official agent-status spec maps
exactly onto them — K1 breathes while listening, K2 breathes when confirmation is
pending, K3 breathes when intervention is needed, **knob light stays on while the
agent is progressing** (docs FAQ `codex-claude-status.html`, "Lighting indicators").
The factory GET on olanzi's unit parses cleanly under this layout (mode=2, bright=7;
K1 breathe, K2 breathe, K3 always-on, knob off — the sample at
`docs/02-vibekey-protocol.md:153`). vibekey-lite's older caveat ("which physical
light each LED index selects … need hardware tests", `protocol.md:294-296`) is
superseded by the two later shipped implementations.

Brightness scale: **Studio's sliders pass raw levels `0…20`** — olanzi states this
from Studio observation and guards it in code (`DeviceLighting.swift:98-104`,
slider `0...20` `LightingSettingsView.swift:214`). OpenVibeKey instead clamps to
`0…100` (`VibeKitDevice.swift:99-101`); use **0…20** (factory sample replies `07`,
`02` — small levels, consistent). A generic `01 06 20 04 <brightness>` also exists
(olanzi doc-02:181; vibekey-lite `protocol.md:299-306` — static-confirmed, AU05
applicability unproven; ignore).

### 1.3 Colour: no — and that is now well-evidenced

- The `0x88` family is the complete known lighting surface: seven SET builders, none
  takes a colour/RGB parameter (§1.2; OpenVibeKey's full data-driven Studio command
  table has no other LED command).
- **Studio's own Light Effect UI is three radio modes + one Brightness slider — no
  colour picker** (official docs §2.4 and its screenshot `en-light.CTiWtFFD.png`,
  downloaded & inspected; olanzi's Studio-alternative UI likewise offers only
  mode/effect/brightness, `LightingSettingsView.swift`).
- Agent-status lighting is specified purely as *which light is on/breathing*
  (official FAQ §"Lighting rules": one consistent breath rhythm; states not
  countable by colour).
- The only "red" in official materials is Studio's battery icon wording (§2.9.2),
  and the AU05-X is a different product line with its own guide.
- olanzi's roadmap line "state values → LED colors ⬜ Not done (Phase 5)"
  (`docs/01-ulanzi-studio-scope.md:271`) is about *understanding* the mapping, not a
  colour API; nothing in their published `0x88` fields can carry a colour.

Treat the lights as **monochrome, per-light: off / always-on (level 0-20) /
breathing (level 0-20)** plus the global mode. Breathing acceptance on the *knob*
light is unverified — olanzi only permits type `2` for index 0 (K1) mirroring
Studio's UI (`DeviceLighting.swift:108`), while the factory reply shows K2 also
breathing and OpenVibeKey writes any type to any index. Bench-check if needed.

### 1.4 Reverse-engineering fallback — not needed; and what it would cost if extended

For anything already answered above: **zero RE cost — published**. If we ever need a
*new* behaviour (e.g. an undocumented field, or firmware ≥ 4.6.x changes — olanzi
measured 4.4.2, the official screenshot unit runs 4.6.4/4.6.3), the capture path is
cheap precisely because the key is public: run Ulanzi Studio in Windows (it works
there, docs §1.2.2 "no additional permissions") with Wireshark + usbpcap capturing
interrupt-OUT + SET_REPORT traffic to `fff1:00dd`, change the setting in Studio,
`write()`-style decrypt the captured 63-byte payloads with the known TEA key, diff
plaintexts. ~half a day, no hardware work; **no HIDP/OTA/derivation hunt is required
for lighting**. (Do not capture into the repo — findings only; this repo is public.)

---

## 2. Q2 — Write path from the user-space Daemon (Linux)

### 2.1 The mechanism already exists in the ported code

Upstream's Daemon holds the vendor node open **read-write**
(`os.open(hidraw["input3"], os.O_RDWR | O_NONBLOCK | O_CLOEXEC)`,
`bin/vibekeyd:586-591`) and *writes* TEA frames into it every 60 s for battery:
`os.write(self.vendor_fd, vendor_frame(BATTERY_REQUEST))` (`bin/vibekeyd:649-653`,
frame built at `:174-177`, request `01 01 02 01` at `:188`) — **while the same
process EVIOCGRABs the Dongle's evdev nodes** (`set_grab` loop, `bin/vibekeyd:606-616`, ioctl at `:611`)
and reads vendor replies on the same fd (`read_vendor`, `:659`). Lighting GET/SET are
the same framing with different opcode/payload. So the answer to "can it `write()`
reports while evdev is Grabbed, nothing grabs hidraw" is: yes — and this exact
codebase already does it on this OS today.

### 2.2 Kernel evidence that Grab cannot touch the write path

- `write()` on a hidraw node → `hidraw_write` (`drivers/hid/hidraw.c`, v7.2:170-181)
  → `hidraw_send_report(file, buf, count, HID_OUTPUT_REPORT)` (`:113`): checks
  `count ≤ HID_MAX_BUFFER_SIZE(64)` (`:128`) and `count ≥ 2` (`:135`); **"The first
  byte of the report buffer is expected to be a report number"** (`:110-111`
  comment). Routing: `__hid_hw_output_report()` — interrupt-OUT endpoint — with
  fallback to `__hid_hw_raw_request(…, HID_REQ_SET_REPORT)` control transfer when
  `-ENOSYS` (`:149-162`; `hid-core.c:2573`; `usbhid/hid-core.c:943-969`: without
  `urbout` returns `-ENOSYS`, otherwise `usb_interrupt_msg` sends the buffer,
  report ID included on the wire). The AU05 vendor interface has a 64-byte interrupt
  OUT endpoint, EP `0x01` OUT 64 B / 2 ms (`kubja/ulanzi-vibekey
  docs/hardware_protocol.md:33-37`), so writes go there.
- **This path never touches the input subsystem.** `grep -c grab drivers/hid/hidraw.c`
  (v7.2) → **0**. `EVIOCGRAB` is an input-core filter (`drivers/input/input.c`,
  see ticket 0001 §2) and hidraw has no grab/exclusive-open concept at all —
  `/usr/include/linux/hidraw.h` on this box offers only descriptor/feature/report
  ioctls (`:34-45`), no grab. The daemon's Grab therefore cannot interfere with, or
  be interfered by, vendor writes; and multiple hidraw openers coexist (ticket 0001
  verified delivery to *all* openers — reads don't compete either).
- Node choice matters: `hidraw12` (/input2, standard collections) vs `hidraw13`
  (/input3, vendor). **LED frames go to `/dev/hidraw13`** — the node the Daemon
  already keeps as `vendor_fd` (topology verified on this Dongle by ticket 0001).
- Permissions: the package-owned udev rule settled in ticket 0001
  (`MODE="0660", GROUP="vibekey"` covering the Dongle's `hidraw`) grants the user
  service write access; nothing extra needed.

### 2.3 Write gotchas (from the two implementations)

1. **Exact size**: `write()` must be 1 + 63 = **64 bytes**, first byte `0x55`; zero-pad
   plaintext to 64, encrypt, send `ct[:63]` (§1.1).
2. **Always carry all four 5-byte records**: unfilled slots are written as 0 —
   "必须一次带上全部 4 灯当前 type，否则未填的槽会被写 0、把其它灯清掉（联动冲突 bug）"
   (OpenVibeKey `VibeKitDevice.swift:106`); same comment in olanzi
   (`DeviceLighting.swift:81-84`). Read-modify-write, never blind partials.
3. **Breathing needs its parameters**: writing only the type leaves breathing dead
   after a few seconds; OpenVibeKey persists per-LED `[type, 0x0a, 0x02, 0x02, 0x02]`
   as known-good sustained-breath params ("实测可持续呼吸的参数",
   `VibeKitDevice.swift:109`).
4. **Knob-ring readback is stale**: plaintext offset 27 (ring alwaysOnBrightness)
   verifiably returns the *old* value — "wire[27] 已由实物验证会返回旧值，不能作为
   冲突依据" (olanzi `NativeDeviceService.swift:384`; UI tooltip
   `LightingSettingsView.swift:189`). **Confirm ring writes by the write-ack frame**
   (ack access `0x14` echoes the masked field at its computed offset —
   `matchesLightingWriteReply`, `DeviceLighting.swift:50-65`), not by GET.
5. **Replies are async input reports** on the same fd; correlate by pattern
   (`cmd&0x1F`, group, opcode, `access|0x10`), not by exclusivity — our Daemon's
   existing `read_vendor`/`handle_vendor` loop already multiplexes frame types
   (battery today; add `88` parsing there). olanzi's helper drains-and-matches with a
   **1.3 s timeout** (`HIDTransport.swift:234-249`) — use a similar deadline.
6. **The keypad must be wirelessly online**: `cmd=0x01` frames are executed by the
   keypad over the 2.4 GHz link; powered-off or in standby (5-min idle → *disconnects
   from the Dongle*, official docs §2.5) the Dongle just never answers (measured:
   powered-off unit answered only the 2 `0x06` dongle-level queries, olanzi
   `docs/02-vibekey-protocol.md:186-207`). Treat no-ack as no-op; check `06 03 0a 01`
   online status first if we want to know.
7. **Serialize writes** — both projects run all vendor writes on one worker ("All
   writes run serially on the device worker, outside HID callbacks", olanzi
   `docs/09-native-macos.md:146`); our Daemon is single-process, so a simple
   write-queue on the main loop suffices.
8. **Be the only config host** (of the *write* kind): "close other config tools" —
   olanzi `HIDTransport.swift:249`. Ulanzi Studio does not run on Linux; warn about
   `--poll`-style helper tools if the user runs any.

---

## 3. Q3 — Persistence & live behaviour

**Stored on the device (survives unplug, Studio absent):** the lighting *configuration*
— mode, global brightness, per-light records — is device-side config, not a live
tether: Studio's offline-mode limitation list is about *dynamic* features
("Fn keys…, automatic preset switching, and **status lighting** require Ulanzi
Studio to keep running" — official docs §2.9.1), while shortcuts and the saved
device config persist ("the device can then execute only the most recently
synchronized shortcuts", §1.1). olanzi's runtime doc likewise speaks of
"**stored lighting**, standby, or sleep settings" that its flows do not change
(`docs/09-native-macos.md:146`). The device also runs its own firmware light logic
with no host: pairing/connected states ("the Dongle indicator and device knob
light stay on", §1.3.1; slow knob blink when unpaired — official manual, mirrored
at manuals.plus), standby/sleep timing ("**In any lighting mode**, five minutes
without input puts the device into low-power standby and disconnects it", §2.5),
and the standby/sleep delays read back as saved values from the device itself
(device-observed 300 s / 3600 s, vibekey-lite `docs/protocol.md:309-325`).
Within-session write→GET readback verification is the pattern both implementations
use (olanzi `NativeDeviceService.swift:375-420`; `LightingTests.swift:203-212`).
*Cross power-cycle readback of a lighting change is not explicitly logged by any of
the projects — one 10-minute bench probe closes that too (§6).*

**Live behaviour:** yes, changes apply while the device is actively transmitting —
this is literally the product's design: Studio's Agent Status Sync updates the
lights continuously *while* the agent session runs and the user watches ("Vibe Key
displays the corresponding lighting feedback as the agent's status changes",
official docs §2.4.1 + FAQ). Full duplex is on the USB level independent (separate
IN/OUT endpoints, §2.2), and a live vendor session even keeps the lights awake:
"VibeKey Lite … was observed to keep the AU05 lights awake past its saved
five-minute standby delay" (vibekey-lite `protocol.md:381-383`). Caveat mirrored
from the same source: when the keypad has gone to standby it is *disconnected* —
writes are dropped until any key wakes it (official docs §2.5), so flash feedback
for a long-idle device is best-effort (wake → write → apply).

**Firmware conflict surface:** if the user has configured the *device* to mode 0 or
1 (all-off / all-on), per-light work-mode fields stay invisible; per-light control
means mode 2 (work). Studio's model separates "mode" (user preference) from
host-driven effects (writes in mode 2), so the Daemon must **read the config, own
its fields, and not silently flip the user's mode** — a design decision for the
spec (ticket 9), listed in §6.

---

## 4. What the map's fog says vs. what is true

Map: "*RGB* LED ring — if driveable, Knob mode could announce *on the device*
(mode → ring colour)". Reality: **driveable, but not RGB** — the knob ring is one
monochrome channel (ledIndex 3). The "no screen to show the mode" gap closes via
*patterns*: e.g. Scroll = off, Sessions = on, Volume = breathe (pending ring-
breathe bench check; fallback: off / dim / bright — though distinguishing
brightness *levels* at a glance is weak UX; prefer on/off/pattern over levels).

---

## 5. Q4 — Cost of the use-cases, and where the code lives

**Shared foundation first** (everything below sits on it): a `lighting` module in
the ported `vibekeyd` — GET/parse/SET builders (~120–150 Python lines reusing the
existing `vendor_frame`/`vendor_decode`/read loop), write-queue + ack matcher,
startup read of the device config, CLI probe flag. **S ≈ 0.5–1 day + 1 h bench
verification.** Architecture: **own Daemon subsystem, not a Preset add-on** — the
lights are one shared piece of global device state (same status as battery/Grab in
the Daemon's design), Presets *request* lighting events through it, and
Knob-mode mapping, feedback flashes, and battery policy are three policies over
one single writer (gotchas §2.3 need enforcing in exactly one place). `state.json`
gains a `lighting` section for the Panel.

| Use case | Mechanism (per §1.2) | Cost | Risk | Notes |
|---|---|---|---|---|
| **(a) Knob mode → knob ring** | on acked SET mask `0x40` (ledIndex 3) or type mask `0x04`; 1 write per Knob-mode change; e.g. off/on/breathe per mode | **S** (~½ day on foundation) | **M** | No colour — patterns only; ring-breathe acceptance unverified (fallback dim/bright/off); mode-0/1 user setting hides all of it (§3) |
| **(b) Failure feedback flash** | timed ring (or ✕-key) on↔off pairs, 2–3 blinks ≈ 4–6 writes, then restore owner-state | **S–M** (+~1 day on foundation: blink runner, coalescing, restore-after) | **M** | Monochrome only ("red blink" not possible); device in standby = feedback silently lost until wake (acceptable? — spec call); stale ring readback → trust acks |
| **(c) Battery low indicator** | policy on the existing battery poll (`bin/vibekeyd:877-883`): pct ≤ 10 && !charging → slow ring breath or periodic dim flash | **XS–S** (tens of lines once (a)+(b) exist) | **L** | Official manual's "flashing red" is Studio's *app* icon — the device may not indicate low battery at all, so this is real added value; same standby caveat as (b) |

Bonus already implied by evidence: the **official agent-status mapping** (K2 breath
when approval needed, K3 breath on intervention, knob-ring on while agent works —
§1.3) is exactly the OpenCode/Orca Preset vocabulary we adopted (tickets 0003/0004/0006)
and costs ~zero extra protocol work to reproduce — the Daemon becomes a Linux drop-in
for Studio's status-light pipeline.

---

## 6. Open items for the bench / spec (all cheap)

1. **Bench probe (~1 h, with the prototype's vendor fd):** GET `0x88`; SET ring
   always-on `bright=5` (mask `0x40`, idx 3, full records); confirm visible + ack;
   power-cycle device, GET again → settles cross-unplug persistence empirically;
   try type `2` (breathe) on ledIndex 3 → settles ring-breathing; verify on-device
   light order by watching which cap lights per ledIndex.
2. **Design decision for the spec (ticket 9):** who owns *mode*? Proposal: Daemon
   reads mode at start; only manages per-light fields when the user keeps mode 2;
   Panel exposes "let vibekeyd manage lights" toggle (writes mode 2) — never
   silently flip it.
3. **Firmware drift:** all documented measurements at FW 4.4.2 (our Dongle's FW is
   unrecorded; official screenshots show 4.6.x exists). The probe above re-validates
   on our unit; treat failures as new fog, not port blockers.
4. Panel surface (user brightness control / mode selector) — pure UI on top of the
   module, no protocol risk; post-v1 candidate.

## Bottom line for the map

**Backlight control: documented and feasible.** Add to *Decisions so far*: the
Daemon can drive all four indicator lights (on/off/breathe/brightness 0-20,
device-stored config) through the vendor hidraw node it already holds — **no
colour**; (a) becomes Knob mode → ring pattern (S), (b) monochrome flash (S-M),
(c) battery-low via existing poll (XS-S) — all on one ~1-day `lighting` subsystem
inside the Daemon, with the three bench checks in §6.1 as implementation-time
verification, not planning blockers.
