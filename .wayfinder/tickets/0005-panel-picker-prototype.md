---
title: "Panel & picker look on KDE"
type: wayfinder:prototype
status: open
assignee:
blocked-by: []
assets:
---

## Question

What should the PySide6 panel actually look and feel like on KDE, so it can be
reacted to rather than described?

Build a rough, throwaway PySide6 mock — no daemon, fake config — covering:
tray presence + menu; the main window drawing the keypad with each control's
assignment beside it; the grouped-tile picker (preset groups + a custom-command
field + a key-combo field); and the preview state (a control lighting up on a
fake event, the mock status line). Link the prototype here as an asset.

Rough questions to settle by reacting: window vs floating panel, tray-only vs
window+tray, picker grouping, how "preview" is communicated.
