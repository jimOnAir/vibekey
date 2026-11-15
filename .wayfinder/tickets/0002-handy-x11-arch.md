---
title: "handy on X11/Arch"
type: wayfinder:research
status: closed
assignee: jimOnAir
blocked-by: []
branch: research/handy-x11-arch
---

## Question

Can [handy](https://github.com/cfaxman/handy) be the STT app behind the
"vibekey is just the finger" arrangement?

- How are record start/stop triggered: a global hotkey only, or also CLI /
  socket? Is the PTT mode hold-to-record (press/release), or toggle?
- Does the trigger respond to **injected** X11 key events
  (`xdotool keydown … keyup`), under a compositor's grab chain?
- Arch/Manjaro install path: AUR PKGBUILD, dependencies, whisper model
  provisioning; realistic key-release → text latency.

**Output**: feasibility verdict for press/release hotkey injection plus the
recommended mechanism, on `research/handy-x11-arch`, linked from this ticket.
Feeds *Dictation preset spec*.

## Answer

**Feasible — YES: handy works on Manjaro KDE/X11 as the Dictation app behind
hotkey injection.** Full evidence chain: [`research/handy-x11-arch`](https://github.com/jimOnAir/vibekey/blob/research/handy-x11-arch/research/handy-x11-arch.md) (`35477cf`, 359 lines).

- **Recommended mechanism**: hold-pair injection — `xdotool keydown ctrl+alt+space`
  on Voice Control press, `keyup` on release — against handy's default **Tauri**
  shortcut backend in **`push_to_talk`** activation mode.
- **Why injection works**: Tauri backend = `XGrabKey` on the root window, event
  loop delivers both press and release edges, zero `send_event` filtering; XTEST
  fake events trigger passive grab activation "just as if the corresponding
  input device action had occurred". KWin sits nowhere between.
- **⚠️ Trap**: never switch handy to the `handy_keys` backend — on Linux it
  reads `/dev/input` evdev directly, where XTEST events don't exist. Pin
  `keyboard_implementation = tauri`.
- **Triggers**: global hotkey (any modifier chord; Linux default
  `ctrl+alt+space`, cancel `Esc`) with `toggle` / `push_to_talk` /
  `hold_or_toggle` (default, 300 ms); plus toggle-only CLI
  (`handy --toggle-transcription`) and `SIGUSR2` as documented fallbacks. No
  external socket/API.
- **Arch**: AUR `handy` 0.10.1-1 pins the audited commit; whisper.cpp engine
  vendored (CPU + Vulkan, **no CUDA**); models download at first run
  (Parakeet v3 ≈1.3 GB); `optdepends` itself lists `xdotool` for X11.
- **Latency**: ~0.5–2 s key-up→text on modern x86 with Parakeet (5.3× realtime
  logged); enable `always_on_microphone` (mic-open ≈500 ms otherwise clips the
  first syllable, #1283).
- **Transcript landing**: window focused at insertion; XTEST never moves focus
  and the Daemon's keypad Grab is kernel-level and disjoint — no conflict. Keep
  the overlay off (Linux default; visible overlay can steal the paste); default
  `Shift+Insert` paste.
