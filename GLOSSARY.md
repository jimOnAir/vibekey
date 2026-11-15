# vibekey (Ulanzi AU05 control surface)

This context: a programmable control surface built on the AU05 keypad — the
driver reads the device directly, factory keystrokes are replaced by the user's
assignments. Vocabulary here is binding in specs, tickets, docs, and code.

## Language

### The keypad

**Control**:
One of the six physical inputs on the AU05: Voice key, ✓ Confirm, ✕ Cancel,
knob press, knob turn (both directions count as one Control).
_Avoid_: button, key ("key" means an X11 keyboard key)

**Dongle**:
The USB receiver the AU05 presents to the machine (`fff1:00dd`); the keypad
pairs to it and it re-enumerates periodically.
_Avoid_: receiver, adapter

**Grab**:
Holding the AU05's keyboard events so the user's applications never see the
factory keystrokes; only assignments run.
_Avoid_: intercept, capture

**Preview**:
While the panel is open, the state where Control events are reported but no
assignment runs.
_Avoid_: dry-run, test mode

**Alias**:
A learned factory report that counts as one of the six Controls, for units
reprogrammed in Ulanzi Studio.
_Avoid_: remap, override

**Device lighting mode**:
The AU05's global lighting setting — Always Off / Always On / Working
(Studio's labels; Working = factory) — that gates whether per-channel lighting
writes are visible on the device. The Daemon changes it only through Manage
lights.
_Avoid_: lighting mode, device mode, work mode, takeover

### Assignments

**Assignment**:
What runs when a Control fires — a preset or a user-written custom command or
key combo.
_Avoid_: mapping, binding, action ("action" is reserved for panel UI verbs)

**Preset**:
A named, shippable Assignment with fixed behaviour (dictation, agent, volume,
…).
_Avoid_: macro, shortcut

**Dictation**:
Push-to-talk speech input: recording runs while the Voice key is held, handled
by the handy app.
_Avoid_: voice typing, transcription

### The app

**Daemon**:
The resident process that reads the Dongle, applies the Grab, and runs
Assignments.
_Avoid_: driver ("driver" is reserved for the kernel HID driver)

**Panel**:
The tray application where the user views status and edits Assignments.
_Avoid_: control panel, widget, bar plugin

**Session** (agent):
An OpenCode conversation running in a terminal; agent presets move focus
between Sessions.
_Avoid_: window, tab

**Host**:
The window or terminal where a Session runs; a Session step raises its Host.
_Avoid_: container, pane

**Ring**:
The Daemon's ordered cycle it steps through for *next/previous Session*.
_Avoid_: carousel, list, queue

**Cursor**:
The Daemon's position in the Ring; may drift from what the user views manually.
_Avoid_: pointer, index

**Knob mode**:
The active Preset for knob-turn; cycled by knob press.
_Avoid_: knob setting, dial mode

**Manage lights**:
The consented Panel action that sets the Device lighting mode to Working and
hands the Daemon the per-channel lighting fields.
_Avoid_: takeover, own lights, fix lighting, enable lighting
