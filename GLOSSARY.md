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
