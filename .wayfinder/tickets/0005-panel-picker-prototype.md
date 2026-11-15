---
title: "Panel & picker look on KDE"
type: wayfinder:prototype
status: open
assignee: jimOnAir
blocked-by: []
assets:
---

## Question

What should the PySide6 panel actually look and feel like on KDE, so it can be
reacted to rather than described?

Build a rough, throwaway PySide6 mock — no daemon, fake config — covering:
tray presence + menu; the main window drawing the keypad with each control's
assignment labels beside it; the grouped-tile picker (preset groups + a custom-command
field + a key-combo field); the **Knob-mode** affordances from *Agent-preset
design for OpenCode/Orca* — editing the ordered mode list, an always-visible
current-mode indicator, and a simulated mode-switch notification; and the
preview state (a control lighting up on a fake event, the mock status line,
long-press vs press distinguishable on the knob). Link the prototype here as an
asset.

Rough questions to settle by reacting: window vs floating panel, tray-only vs
window+tray, picker grouping, how "preview" is communicated.
