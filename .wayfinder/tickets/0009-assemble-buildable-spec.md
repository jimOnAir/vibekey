---
title: "Assemble the buildable spec"
type: wayfinder:task
status: closed
assignee: jimOnAir
blocked-by:
  - 0005-panel-picker-prototype.md
  - 0006-agent-preset-design.md
  - 0007-dictation-preset-spec.md
  - 0008-packaging-install-spec.md
  - 0011-lighting-design.md
---

## Question

Consolidate every closed decision on this map into `spec.md` at the repo root —
this is the **destination**; nothing else is left to decide after it.

The spec must cover: architecture (daemon / panel / preset wiring), the config
schema and preset table, packaging and install/uninstall flows, and a
verification checklist an implementation session can run. Written against
`GLOSSARY.md`; implementation sessions work from it without returning to this
map for decisions.

## Answer

**[`spec.md`](../../spec.md) assembled** from all ten closed tickets + the
research branches: architecture (§2, incl. keep/replace and the xdotool
adapter), file protocol (§3), config schema + `behavior` extension (§4), every
preset behaviour with its exact mechanism (§5), the preset table and new
`defaults` (§7), Variant-A Panel surface (§8), full packaging/install/uninstall
(§9), and a 16-item verification checklist an implementation session can run
(§10) — including the probe/bench items the map deferred as fog. Accepted open
items are listed in §11 so nobody re-decides them. Assembled after a fresh-context
verifier pass against every closed ticket and the research branches; its findings
(Grab mouse-node exemption, fixed-knob semantics, declined `ctrl+tab` Preset,
stale-id notification, preview narration mapping, and several precision fixes)
are applied.

One decision the map and tickets did **not** settle surfaced while writing
§5.5: the *Backlight control* note explicitly carried "who owns the device-global
lighting mode" to "the spec (ticket 9)", and ticket 0011 never answered it
(its Panel scope — three switches + slider — is compatible with any answer).
Per the no-invention rule it is opened as ticket
[0012-lighting-device-mode-ownership](0012-lighting-device-mode-ownership.md);
`spec.md` §5.5 is the only subsection marked pending, everything in it else is
buildable as written.
