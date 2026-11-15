---
title: "Agent-preset design for OpenCode/Orca"
type: wayfinder:grilling
status: closed
assignee: jimOnAir
blocked-by:
  - 0003-opencode-surface.md
  - 0004-orca-surface.md
---

## Question

Lock the agent-preset vocabulary and behaviour for OpenCode + Orca. The
vocabulary is settled from charting — *next/previous OpenCode session*, *focus
the terminal running the agent*, *interrupt*; stretch: *Orca next-worktree*.

This ticket settles mechanics and edge behaviour:

- Map each Preset onto the Controls (✓ / ✕ / knob turn) sensibly; which land
  on knob directions.
- **next/prev Session**: adopt the composed mechanism (API session ring of
  root `ses_…` ids → host resolve: Orca `terminal switch` with title/directory
  match, else `wmctrl -a` on `OC | ` title)? Orca drift gap (Daemon-owned
  cursor vs sidebar clicks) — accept or mitigate? In-TUI `ctrl+tab` route —
  expose at all?
- **interrupt**: confirm API-first (`POST /api/session/{id}/interrupt`,
  no focus needed) with Esc-only keystroke fallback; `orca terminal send
  --interrupt` as the Orca-native alternative. Codify **never Ctrl+C**
  (empty-prompt exit path).
- Focus-presets for `--standalone` TUIs (API-opaque): window/title route only —
  in v1 or out?
- Behaviour and Panel/OSD report when: no OpenCode service running, no root
  Sessions, Session id stale, Orca not running mid-cycle.
- The Daemon's service discovery: read `~/.local/state/opencode/service.json`
  for port + Basic auth? Refresh policy when the service restarts.

## Answer

All decisions accepted by the dev (grilling, 2026-11-15):

- **Control map**: ✓ Confirm = *next Session* (fixed), ✕ Cancel = *interrupt*
  (fixed), knob **press** = cycle Knob mode, knob **long-press** (≥400 ms,
  measured on the release edge) = Enter injection, knob **turn** = active Knob
  mode's Preset.
- **Knob mode**: user-configured ordered list of turn-Presets, default
  `Scroll, Sessions, Volume`. Runtime state — resets to Scroll at boot. Every
  switch announces itself (`notify-send` + tray state). Mode-scoped ✓/✕
  declined for v1 (→ map *Out of scope*).
- **Session cycle**: one step = one root Session in the **Ring** (from the
  service API); step effect = raise that Session's **Host**. Host resolution:
  Orca — match `terminal list --json` row by `title == "OC | " + api.title`,
  fall back to directory match, then `orca terminal switch`; plain terminal —
  `wmctrl -a` on the `OC | ` title. **Cursor drift** from manual sidebar /
  `ctrl+tab` switches is accepted for v1 (no title-resync); no `ctrl+tab`
  Preset.
- **Interrupt (✕)**: hybrid target — the focused window's Session when
  resolvable (title or Orca row match), else the Cursor's Session; the resolved
  target is named in the status report. Mechanism order:
  `POST /api/session/{id}/interrupt` (idempotent) → `orca terminal send
  --interrupt` → **Esc keystroke; never Ctrl+C** (empty-prompt `app.exit`).
- **Standalone TUIs**: out of v1 entirely (API-opaque — invisible to the Ring,
  un-interruptable). Documented known gap.
- **Failure/status surface**: `notify-send` + tray icon state (works with the
  Panel closed): service down, zero root Sessions, stale Session id (skip to
  next valid), Orca not running mid-cycle, injection fired but unverifiable.
- **Service discovery**: read `~/.local/state/opencode/service.json`;
  ~5 s cache, one re-read + retry on auth failure; "service not running" is
  declared only after the retry fails.
