# Lighting

*[← README](../README.md)*

The AU05 has four **monochrome** indicator lights — the three keycaps and the
knob **ring** (no colour exists on the device, patterns carry the meaning).
vibekeyd drives them over the vendor channel it already holds, from one
**single-writer** module: Presets emit lighting *events*, and the module
serialises every write with an ack check — the light-state equivalent of
never having two hands on the wheel.

## What the lights say

| Signal | Where | Meaning |
|---|---|---|
| **Ring pattern** | knob ring | your pulse, at a glance, screen-free (default `breathe:8` — the firmware's own, zero host traffic) |
| **Alarm override** | knob ring | fast double-tick while the Cursor Session waits for approval |
| **Failure blink** | the culprit keycap, 3 fast blinks | *that* press you just made did not work |
| **Battery breathe** | knob ring, slow | ≤ 10 %, until you charge (one notification per crossing) |

Switches for all three live in the Panel's Lighting section; the patterns
themselves are config-editable ([docs/config.md](config.md)).

## The alarm: "an agent is waiting for you"

When the **Cursor Session** (the one the ring is pointing at) has a pending
permission request, the Daemon overrides the ring with the `alarm` rhythm —
double-ticks until you answer. The status line and tray tooltip say what to
do: **hold the knob** (that's Enter). Scoped v1: the Cursor Session only, on
the shared OpenCode service (standalone TUIs stay invisible, as elsewhere),
and it yields to the low-battery breathe. Switch: *Alarm ring while an agent
awaits approval* (`lighting.attention_ring`, default on).

## Ring rhythms

A pattern string says *what the ring does*:

```
"off"          no light (the Scroll default — silence is never ambiguous)
"solid:8"      steady at level 8 (of 20)
"breathe:8"    the firmware's own breathing, level 8  (zero host traffic)
"heartbeat:8"  a host-driven rhythm — see the catalogue
"pulse:10:2000" same rhythm with a custom level and period (ms)
```

### Catalogue

| Rhythm | Character | Cycle | Shape (level over time) |
|---|---|---|---|
| `pulse` | one soft, eased heartbeat-strength beat | 2.6 s | `▁▂▄█▃▁ …` |
| `heartbeat` | lub-dub — two accents, second stronger | 2.8 s | `▁▅█▂▆█▁ …` |
| `tick` | dry metronome blip, like a clock | 1.3 s | `▇▁ … ▇▁` |
| `wave` | long tide, seven eased steps up and down | 2.4 s | `▁▃▆█▆▃▂ …` |
| `gallop` | three-beat clip-clop | 2.2 s | `▄█▂▅█▂▇▁ …` |
| `alarm` | urgent double-tick (reserved: §see below) | 1.4 s | `█▁█▁▄▁ …` |

Default out of the box: **`breathe:8`** — the firmware's own breathing: zero
host writes, so nothing can stutter (a host-driven rhythm against a keypad
that misses ACKs strobes and stalls the ring — that blinking was the reason
native became the default; the breaker also pauses any rhythm after three
unanswered writes and resumes on wake). Want a host rhythm anyway? Set e.g.
`"pattern": "heartbeat:8"`, which points at your Sessions. Set it with the single `lighting.pattern` key
(the old per-mode `patterns` map still loads, `Sessions` entry wins, for
config compatibility). Unknown rhythm names fall back to `off`, never a
crash.

Rhythm cycles are queued as timed writes on the single writer; switching Knob
mode flushes the running cycle, so two rhythms never stutter over each other.
The `brightness` slider scales every level vibekeyd writes (0.0–1.0).

> The Panel exposes the three switches and the slider only — pattern editing
> is a config-file thing by design (ticket 11: no pattern editors in the UI).

## Failure blinks

Only **reactions to your own presses** blink — if you pressed a Control the
device is awake, which sidesteps the one hard limitation of this hardware:
**writes to a sleeping keypad are dropped** (it disconnects after 5 idle
minutes). No ambient status lighting, no missed-message roulette: the cap of
the Control that failed blinks three fast times at brightness 16, the ring
stays untouched. Handy absent for Dictation, no OpenCode service, an
un-interruptable Session — the culprit keycap says so, and a notification
agrees.

## Battery

At ≤ 10 % the ring takes over slow breathing (`breathe:6`) and you get exactly
one notification; charging above 20 % releases the latch and your Knob-mode
rhythm resumes (the latch owns the ring while it lasts — rhythms queue
nothing). The AU05 itself has no low-battery indication, so this one is pure
added value.

## Device lighting mode

There is one lighting setting bigger than all of the above: the device-global
mode — *Always Off / Always On / Working* — configured in Ulanzi Studio.
Per-light writes are only visible while it sits at **Working**. vibekeyd is a
polite guest:

- reads the mode on connect; on *Always Off/On* all lighting policies idle
  (everything else still works),
- the Panel shows a line plus a single consented action — **Manage lights** —
  which sets *Working*; never silently, and never any of the device's other
  global fields (vibekeyd does not touch global brightness at all),
- if you set the device back to Off in Studio later, vibekeyd notices and
  politely goes quiet again;
- a keypad asleep at connect is treated optimistically (features live, lazy
  re-read on your next press).

With all three switches off, vibekeyd sends **zero** lighting traffic — the
device is yours entirely.

---

*Next: [Configuration](config.md) — the schema, the files, the protocol.*
