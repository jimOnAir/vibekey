# Presets & Assignments

*[← README](../README.md)*

An **Assignment** is what runs when a Control fires: a shippable **Preset**
with fixed behaviour, a key combo, or a shell command. Everything below is
editable from the Panel (double-click the cap in the drawing, or *Edit…*); the
defaults shown come from the shipped catalogue and survive upgrades untouched.

## The control map

| Control | Default Preset | What it really does |
|---|---|---|
| 🎙 Voice key | Dictation (hold, handy) | see [Dictation](#dictation) |
| ✓ Confirm | Next Session | advance the **Ring** of root Sessions, raise the new one's **Host** |
| ✕ Cancel | Interrupt | stop the agent — see [Interrupt](#interrupt) |
| Knob press | cycle Knob mode | `Scroll → Sessions → Volume → …`, resets to the first entry at boot |
| Knob long-press (≥400 ms) | Enter | one `Return` keystroke — sized to accept permission prompts |
| Knob turn | the current Knob mode | Scroll: native wheel · Sessions: Ring ± · Volume: `pactl` ±5 % |

Knob **modes** are an ordered list in your config (`knob_modes`) — put the
turn-Presets you actually use in it; each switch announces itself by
notification, tray glyph, and (if enabled) a ring pattern.

## Dictation

*Push-to-talk speech input, held down = recording, released = transcribed.*

vibekey is deliberately just the finger: **handy** does all the speech work,
the Daemon brackets your hold with handy's hotkey —

- press → `xdotool keydown ctrl+alt+space`, release → `keyup` (handy's Tauri
  global shortcut hears injected keys — the `handy_keys` backend does **not**,
  keep `keyboard_implementation = tauri`),
- if handy isn't running you get a notification and nothing else — vibekey
  never auto-starts apps,
- the chord lives in the Preset (default `ctrl+alt+space` = handy's Linux
  default); if it drifts from handy's own binding the Panel's handy card warns
  and offers a consented **Fix handy**,
- expected feel: **~0.5–2 s** from release to text (fast local models;
  accurate tiers take seconds),
- the Panel's tray badge watches the mic path end to end: Dongle unplugged,
  keypad asleep/off (its link drops after ~5 idle minutes — a key press wakes
  it and clears the badge), or the system input gone/muted → orange
  mic-with-slash. Your Dictation mic is the AU05's built-in one, so the badge
  tracks *that keypad's* state first of all.

Recommended handy settings, all graded by the handy card: push to talk,
always-on microphone, overlay off, typing tool `xdotool`, a fast model tier on
CPU **or** your GPU (Vulkan) — GPU pinning is per-box; on the dev machine the
RTX-class GPU beat CPU by ~30 % on short dictations.

## Agent Presets

For **OpenCode** v2 (works in plain terminals and inside Orca) plus an Orca
worktree stepper. The Daemon finds the OpenCode service on its own
(`~/.local/state/opencode/service.json`, ~5 s cache, one auth retry).

### Next / Previous Session — the Ring

The **Ring** is the Daemon's ordered cycle of root Sessions pulled from the
service API; the **Cursor** is its position. A step moves the Cursor and
raises that Session's **Host**:

1. **Orca-hosted:** match the terminal row by window title (`OC | …`) or
   worktree directory, switch tabs, raise the Orca window.
2. **Plain terminal:** raise the window OpenCode titles `OC | <session>`.

The Cursor may drift when you switch Sessions by hand — accepted for v1; a
step simply catches up to the Ring. Deleted Session ids skip to the next valid
id (and tell you). `Previous Session` and `Focus this Session's terminal`
(Raise without stepping) are in the catalogue too. While the Cursor's Session
blocks on a permission prompt the knob ring runs the **alarm** rhythm and the
Panel says *hold the knob for Enter* — the accept gesture meets the request
where it is raised (switch under Lighting).

### Interrupt

✕ Cancel stops the run with the gentlest mechanism that exists, in order:

1. `POST /api/session/{id}/interrupt` — idempotent, works with no focus;
2. `orca terminal send --interrupt` (Orca-native PTY level);
3. raise the Host, then **Esc**.

**Never `Ctrl+C`** — on an empty OpenCode prompt that *exits the app*. The
target is the focused window's Session when resolvable, else the Cursor's; the
status line always names which.

### Next / Previous Orca worktree

Cycles Orca worktrees (skipping archived ones) with
`worktree activate` + window raise. The cycle order is Daemon-owned (Orca
exposes no "what am I viewing" query), so the same accepted-drift note applies.

> **Known gap (v1):** `opencode --standalone` TUIs run a private, unregistered
> server — invisible to the Ring and un-interruptable by design. Not a bug.

## Keys, Media, System

Plain keystroke Presets (Enter, Escape, Tab, Shift+Tab, arrows, Ctrl+Enter,
the XF86 media keys) and shell-command Presets (`Spectacle` screenshot,
`loginctl lock-session`, Konsole, brightness). Upstream's catalogue shipped
`Ctrl+C` as a Preset; ours omits it on purpose — interrupt is handled above,
and users who want the chord can still type it into a custom combo.

## Writing your own Assignment

Double-click a Control → **custom command** (any shell one-liner, `bash -c`)
or **key combo** (`ctrl+shift+t`, `XF86AudioNext`, anything xdotool keysyms
understand). The running Daemon picks edits up within half a second.

From the terminal, the same edits go through the atomic CLI:

```bash
vibekey-config set-button key2 '{"preset":"key_enter","label":"Press Enter","keys":"Return"}'
vibekey-config set-button key2 null        # clear it
vibekey-config set knob_modes '["scroll","sessions","volume"]'
```

> **Layout caveat (open fog item):** combos pass X keysyms through unchanged —
> chords named by *symbol* (e.g. `plus`, brackets) can land elsewhere on non-US
> keyboard layouts. Letters, function keys, `Return`/`Escape`/arrows are safe.

## Preview: try before you fire

While the Panel **window** is open, the Daemon reports every Control (status
line, `[WOULD RUN …]`) but runs nothing — so you can explore the keys with
zero consequences. Close the window or uncheck *Preview* to go live.

---

*Next: [Lighting](lighting.md) — the ring rhythms and what makes them blink.*
