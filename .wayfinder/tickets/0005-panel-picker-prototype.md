---
title: "Panel & picker look on KDE"
type: wayfinder:prototype
status: closed
assignee: jimOnAir
blocked-by: []
assets:
  - "branch: prototype/panel-picker (`3c26e5e`) — `prototype_panel_picker.py`, run `python3 prototype_panel_picker.py [--variant=A|B|C]`"
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

## Answer

**Variant A ("drawn device") won** — owner's pick after live A/B/C flipping
("looks good"). Design elements validated for the spec:

- **Panel = a window**; left half draws the real AU05 — horizontal aluminium
  bar, **knob over the mic/speaker end** (grip notches, mic slots, *Vibekey*
  logo), **three round-capped keys (🎙 ✓ ✕) in square housings**, long ⊗
  end-bar — with transparent interactive zones exactly over the art. Single
  click on the drawing simulates (zone glows), double-click edits.
- **Header strip**: current Knob mode chip · Ring position · battery — the
  always-visible mode indicator worked; no need for C's segmented buttons.
- **Bottom status line narrates every event** with the Preview distinction
  (*WOULD RUN* vs *RAN (sim)*) — this communicates Preview well; keep it.
- **Press vs long-press** (≥400 ms) felt right on the knob zone — keep as the
  mode-cycle vs Enter pair.
- **Picker = grouped-tile dialog + custom command / key-combo fields.**
- **Tray icon + menu** (VK glyph) for re-showing the Panel; *Preview* is a
  checkbox in the Panel, default on.
- Rejected for v1: C's windowless HUD, B's reorderable mode list (mode list
  stays config-editable, header shows the current one).

**Still open (carried, not blocking the spec):** the physical icon↔Control
mapping and whether the ⊗ end-bar is a 4th key — the prototype grew a **probe**
(pill → *probe*: logs real X key events to `/tmp/opencode/au05-probe.log`);
deferred to an implementation-time physical session, where it also settles the
existing *firmware-variant* fog item.
