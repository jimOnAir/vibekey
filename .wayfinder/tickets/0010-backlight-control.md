---
title: "Backlight control: keycap LEDs + knob ring"
type: wayfinder:research
status: open
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
