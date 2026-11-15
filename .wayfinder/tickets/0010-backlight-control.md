---
title: "Backlight control: keycap LEDs + knob ring"
type: wayfinder:research
status: closed
assignee: jimOnAir
blocked-by: []
branch: research/backlight-control
---

## Question

The AU05 has lighting — product/build photos show glowing keycaps and an RGB
LED ring around the knob — and Ulanzi Studio demonstrably changes it, so a
**write path to the device exists**. Can our Daemon drive it?

Establish with evidence from primary sources
([MrCroxx/olanzi](https://github.com/MrCroxx/olanzi) protocol docs,
[kubja/ulanzi-vibekey](https://github.com/kubja/ulanzi-vibekey), upstream
`vibekey-driver`'s vendor-channel code (TEA-encrypted report `0x55` for
battery — the same channel may carry writes), Ulanzi Studio behaviour):

1. Are LED commands (on/off, colour, mode, brightness — per-key and ring)
   documented anywhere open-source, or does driving them need a USB capture
   reverse-engineering effort? Estimate that effort if undocumented.
2. The write path from the Daemon: it already holds the vendor `hidraw` node
   open — can it `write()` reports there while the evdev nodes are `EVIOCGRAB`-ed
   (nothing grabs hidraw)? Any report-ID/encryption gotchas (TEA)?
3. Do lighting settings persist on the device/dongle after unplug (Studio
   applies them device-side), and does the AU05 apply them live while
   transmitting?
4. What would a `Knob mode → ring colour` mapping and failure-feedback use
   cost, given the answers — is it a Preset add-on or its own subsystem?

**Output**: feasibility verdict + cost/risk assessment on
`research/backlight-control`, linked from this ticket. Its answer drives a
scoping decision: v1 (spec already open), v1.5, or out of scope — decided in a
follow-up, not here.

## Answer

**DOCUMENTED — feasible today, zero reverse-engineering.** Full findings:
[`research/backlight-control`](https://github.com/jimOnAir/vibekey/blob/research/backlight-control/research/backlight-control.md) (`91b6732`).
The lighting contract is published and implemented by two independent
open-source projects against real AU05 hardware (MrCroxx/olanzi,
palaemonboy/OpenVibeKey); the TEA key already sits in the upstream code
(`vibekeyd:139`).

- **Contract**: vendor-channel `0x55` reports — GET `01 0b 88 01`, SET
  `01 0b 88 04 <fieldMask> <ledIndex> …`; **4 addressable MONOCHROME
  channels** (K1/K2/K3 keycaps + knob ring, `ledIndex` 0–3); per channel:
  mode (off/all-on/work), effect (off/always-on/breathe), brightness 0–20.
  **No colour byte exists** — Studio's Light Effect UI is mode+brightness too.
- **Write path proven, not inferred**: upstream already `os.write()`s TEA
  frames to `/dev/hidraw13` every 60 s (battery) while its evdev nodes are
  `EVIOCGRAB`-ed; `hidraw.c` (v7.2) has zero interaction with the input-layer
  grab. Gotchas: exact 64-byte writes with report-ID prefix (63/64-byte TEA
  truncation), always send all four 5-byte light records, ring-brightness
  readback is stale (trust the `0x14` ack), **writes dropped while the keypad
  sleeps**.
- **Persistence**: lighting config lives device-side; live writes while
  transmitting are the product's own design (Studio Agent Status Sync).
- **Cost**: (a) Knob mode → ring pattern **S** (~½ day inside a ~1-day shared
  `lighting` module), risk M; (b) failure blink **S–M** (+~1 day blink
  runner), risk M — monochrome, lost if the device sleeps, ack-confirmed;
  (c) low-battery blink **XS–S** (tens of lines on the battery poll), risk L —
  the device has no known low-battery indication, so genuine added value.
- **Architecture** (as recommended in the note): a small **own Daemon
  subsystem** — single writer over shared global device state; Presets emit
  lighting *events*, the module serialises writes. Three ~1-hour bench probes
  close the remaining unknowns (implementation-time).
