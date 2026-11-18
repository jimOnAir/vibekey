# Configuration

*[← README](../README.md)*

Everything lives in two places, both small, both human-editable:

```
~/.config/vibekey/config.json      your setup — the only file you edit
$XDG_RUNTIME_DIR/vibekey/          live state — read-only for tools
```

There are no migrations: every new field has its default in code, so an old
config always boots, and an upgrade never touches your file. Deleting the
config resets to the seeded defaults; emptying a section on purpose is
respected (only a *missing* file is seeded).

## `config.json`

```jsonc
{
  "grab": true,                      // shape kept from upstream; the Grab itself
                                     // is toggled by the unit/CLI, not here
  "battery": true,                   // false stops the 15 s vendor keepalive
                                     // (battery reports + AU05 link awareness)


  "aliases": {                       // learned factory reports → Controls,
    "kbd:0x2a": "knob"               // for units reprogrammed in Ulanzi Studio
  },

  "buttons": {                       // the Assignments — editable slots only
    "key1": {                        // Voice key
      "preset": "dictation_ptt",     // informational catalogue id
      "label": "Dictation (hold, handy)",
      "behavior": "dictation.ptt",   // Daemon-side Preset (see below)
      "keys": "ctrl+alt+space"       // …and the chord it owns
    },
    "key2": { "preset": "session_next", "label": "Next Session",
              "behavior": "session.next" },
    "key3": { "preset": "erase_char_word", "label": "Erase char (hold = word)",
              "keys": "BackSpace", "long_press": "ctrl+BackSpace" }
  },

  "lighting": {                      // every key optional — defaults in code
    "mode_ring": true, "fail_blink": true, "low_battery": true,
    "attention_ring": true,          // §5.7: alarm rhythm on pending approval
    "brightness": 1.0,               // 0.0–1.0 multiplier on all written levels
    "pattern": "breathe:8"           // the one ring pattern; native (`breathe`,
                                     // `solid`) costs zero host traffic —
                                     // host rhythms are opt-in
                                     // (knob modes retired 2026-11-16; a
                                     // legacy "patterns" map still loads and
                                     // its "Sessions" wins)
  }

  // "orca_cli": "/path/to/orca-ide"  // optional override; otherwise the shim
                                      // and the standard install are probed
}
```

### Button entries

A slot's entry carries a `label` plus **one execution shape**:

| Field | Meaning |
|---|---|
| `behavior` | Daemon-implemented Preset: `dictation.ptt`, `session.next/prev/focus/interrupt`, `orca.worktree.next/prev` |
| `keys` | X combo executed as `xdotool key …` (aliases `ctrl/shift/alt/super/altgr`, keysyms pass through) |
| `command` | shell one-liner run via `bash -c` |
| `scroll` | native wheel pass-through (used by `scroll` knob turn only) |
| `release_command` / `release_keys` | the Control *release* half (press/release Assignments) |

Dispatch precedence: `behavior` → `keys` → `command`. The Panel writes these
fields through the atomic `vibekey-config` CLI; editing the file by hand works
too (the Daemon re-reads every 0.5 s).

The knob is not configurable and has no slot: **turn = Ring step, press =
Wheel, long-press = `Enter`** — the dial has one job (spec §5.3).

## The file protocol

The Daemon and Panel share nothing but these files — either can restart
without disturbing the other:

| File | Written by | Read by | Notes |
|---|---|---|---|
| `config.json` | `vibekey-config` only (atomic replace) | Daemon (mtime poll + `SIGHUP`), Panel | the truth |
| `seen.json` | Daemon | Panel | every raw report the unit ever sent — feeds the Alias UX |
| `state.json` | Daemon (in-place rewrite per event) | Panel (watcher + poll) | `connected`, `access`, `grabbed`, `battery`, `keypad{online, at}` (wireless link — asleep/off keypad still has its USB nodes), `ring{index,total,title,host}` (header), `picker{open,items,index}` (the Wheel), `last` (narrated event), `lighting{device_mode, channels, last_error}`, `error`/`last_error` |
| `preview` | Panel (`open` every 2 s while shown, `closed` on hide) | Daemon | freshness ≤ 6 s; while live, nothing runs |
| `manage_lights` | Panel (one-shot `"manage"`) | Daemon (consumes) | the consented [Device lighting mode](lighting.md#device-lighting-mode) request |
| `power` | Panel (one-shot JSON `standby_s`/`sleep_s`/`enc`) | Daemon (consumes) | the consented device power/noise-reduction writes; the Daemon re-reads and the Panel shows the truth |
| `lock` | `flock` by the Daemon | — | double-start guard |

Package files: `/usr/lib/vibekey/{bin/vibekeyd,bin/vibekey-config,actions.json}`
(the catalogue is resolved relative to the package dir, never cwd), the udev
rule, the user unit, `sysusers.d`, icons, and the `.desktop` entry.

## Handy's settings (read, and touched only by consent)

The handy card grades `~/.local/share/com.pais.handy/settings_store.json`
(nested under `"settings"`): `keyboard_implementation=tauri`,
`shortcut_activation=push_to_talk`, `always_on_microphone=true`,
`overlay_style=none`, and chord drift against `bindings.transcribe`. **Fix
handy** is the only write vibekey ever makes there — one field, only when you
click it, never silently.

---

*Next: [Troubleshooting](troubleshooting.md).*
