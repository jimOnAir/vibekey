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
| ✕ Cancel | Erase | tap = last character, hold = last word — see [Erase & Interrupt](#erase--interrupt) |
| Knob press | toggle the **Wheel** | on-screen Ring of Sessions; press again = confirm selection |
| Knob long-press (≥400 ms) | Enter | one `Return` keystroke — sized to accept permission prompts |
| Knob turn | step the **Ring** | select ±1 Session; its Host raises live, under the Wheel |

The knob is dedicated to the **Ring of Sessions** (modes retired
2026-11-16): there is nothing to switch — press opens the **Wheel** and
confirms from it. Need page-scroll or volume on the knob? Assign
key-combo/Media Presets to any of the three buttons instead — they are
fully reassignable, and the Media Presets (`XF86*`) survive the retirement.

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

## The Ring & the Wheel

The knob is the **Session Ring** dial. Press it and the **Wheel** opens over
the screen (drawn by the Panel): every Session with its Host badge, the
**Close** slot, as a ring: the selection glows at the bottom of the wheel,
its neighbours rise along the sides and fade, the rim carries every Session.
Turning while the Wheel is
open *only selects* — nothing switches, no windows move. **Press switches**:
the selection becomes the Cursor and its Host is raised (Orca tab plus window
raise, or plain-terminal raise). Press on the Close slot, ✕, or fifteen idle
seconds dismiss without changing anything. With the Wheel closed, plain knob
turns still dial the Ring directly (debounced live raise) for quick stepping.
Selection and Cursor are deliberately separate while browsing: the Wheel is a
chooser, and only the press commits.

Long-press (≥400 ms) remains one `Return` keystroke — sized for accepting an
agent's permission prompt without touching the keyboard. While a Session
blocks on approval the knob ring itself runs the `alarm` rhythm, so the need
finds you even with the Wheel closed.

Up to 12 root Sessions ride the Wheel; the Ring underneath has no cap.

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

### Erase & Interrupt

✕ Cancel is the **eraser** (owner 2026-11-18): a tap sends `BackSpace` — the
last character; holding past 400 ms starts **repeating** `Ctrl+BackSpace`
every ~0.22 s — words vanish one after another for as long as you hold, the
way a held backspace eats characters.
While the Wheel is open ✕ keeps its older meaning: it closes the Wheel, and
does not erase.

**Interrupt did not vanish — it moved to the catalogue.** Bind the
`session_interrupt` preset (or any behavior) to a key through the Panel to
stop the run with the gentlest mechanism that exists, in order:

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
