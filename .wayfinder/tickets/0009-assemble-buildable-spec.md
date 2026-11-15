---
title: "Assemble the buildable spec"
type: wayfinder:task
status: open
assignee:
blocked-by:
  - 0005-panel-picker-prototype.md
  - 0006-agent-preset-design.md
  - 0007-dictation-preset-spec.md
  - 0008-packaging-install-spec.md
---

## Question

Consolidate every closed decision on this map into `spec.md` at the repo root —
this is the **destination**; nothing else is left to decide after it.

The spec must cover: architecture (daemon / panel / preset wiring), the config
schema and preset table, packaging and install/uninstall flows, and a
verification checklist an implementation session can run. Written against
`GLOSSARY.md`; implementation sessions work from it without returning to this
map for decisions.
