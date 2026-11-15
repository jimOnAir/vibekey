# vibekey — buildable spec (port of jimmibram/vibekey-driver to Manjaro KDE / X11)

Status: **complete — all twelve tickets closed.** Everything here is settled
decision, consolidated from the wayfinder map
([.wayfinder/map.md](.wayfinder/map.md)) and its tickets; ticket 12 was the
last open question. Implementation sessions work from this document alone;
nothing here needs re-deciding.

Vocabulary follows [`GLOSSARY.md`](GLOSSARY.md) and is binding: Control, Dongle,
Grab, Preview, Alias, Assignment, Preset, Dictation, Daemon, Panel, Session, Host,
Ring, Cursor, Knob mode. "key" always means an X11 keyboard key; the physical
inputs are Controls.

Source of port: `jimmibram/vibekey-driver` @ `41ba904b` (MIT). Upstream code is
not vendored; clone it for reference (e.g. `/tmp/opencode/vibekey-upstream`) and
record the pinned commit in an `UPSTREAM` file (ticket 8).

## 1. System facts (target machine)

- Manjaro Linux, KDE Plasma, **X11** session (`Type=x11`, seat0).
- AU05 Dongle: USB `fff1:00dd`; presents `/dev/hidraw12` (interface `/input2`,
  standard reports) and `/dev/hidraw13` (interface `/input3`, vendor/TEA channel),
  plus three evdev nodes (`event*`: Consumer, "AU05 AU05 Mouse", Keyboard).
  `input2`/`input3` names resolve on this unit — keep upstream's hard-coded keys
  but fail loud (`state.json` `error`, `--probe`) if another unit renumbers (R5).
- The Dongle re-enumerates periodically — the documented watchdog: journal shows
  19 full re-enumerations in 2.2 min, a live check saw a ~3.5 s cycle, and it can
  also stay quiet for 100+ min (churn is episodic, ticket 1). Nodes are recreated
  root-only, and presses landing in a reboot window silently vanish.
  This is normal — the Daemon holding both hidraw channels open is the cure;
  do not chase a "knob reconnect" phantom (ticket 1).
- `xdotool` is a new runtime dep (not installed at charting time); `wmctrl` is.

## 2. Architecture

Three pieces, one package:

1. **`vibekeyd`** — resident Python (stdlib-only, as upstream) user service.
   Opens the Dongle's hidraw nodes, `EVIOCGRAB`s the matching evdev nodes —
   **every one except the wheel node** upstream passes through by evdev-`name`
   match on "mouse" (`vibekeyd:601-602`; the **Grab** exemption the `scroll`
   Knob mode and risk R8 depend on) — drains grabbed fds so `select()` doesn't
   spin, decodes HID reports into the six Controls, runs Assignments, owns the
   `lighting` subsystem (§5), polls battery (15 s vendor keepalive, §5.6),
   writes `state.json`.
   Compositor-independence is verified: the Grab is enforced in the kernel input
   core (libinput never issues `EVIOCGRAB`), and hidraw copies raw reports
   *before* the input layer, so report reading stays complete during the Grab
   ([evidence](https://github.com/jimOnAir/vibekey/blob/research/upstream-port-audit/research/upstream-port-audit.md) §2).
2. **Panel** — PySide6 tray application (replaces the Quickshell panel entirely).
   Tray icon + menu; main window is Variant A "drawn device" (§8). The Panel does
   **not** supervise the Daemon (systemd does) and writes config only by invoking
   `vibekey-config`.
3. **`vibekey-config`** — upstream CLI kept verbatim (atomic config.json writer;
   `show` / `set-button <slot> <json>` / `alias <raw-id> <slot>` /
   `forget <raw-id>` / `set <key> <json>`), extended only by allowing the new
   config fields (§4) in its validator.

Process supervision: `vibekeyd.service` **user unit** with `Restart=always`
(§9). Upstream's `PR_SET_PDEATHSIG` stays (harmless under systemd: parent is
`systemd --user`, it fires only at logout). Upstream's flock single-instance
guard on `$XDG_RUNTIME_DIR/vibekey/lock` stays.

### 2.1 What is kept vs replaced (port audit, ticket 1)

**KEEP (as-is unless noted):** device core (discovery, TEA transport, report
decode, Grab, battery poll + link keepalive), hidraw as the read channel (the Voice Control's
factory usage `0x01` ErrorRollOver never becomes an evdev event), `state.json` /
`preview` / config-watcher / `seen.json` file protocol (§3), `actions.json`
**schema** (with the one addition in §4.2), `vibekey-config`, first-run config
seeding from the catalogue `defaults`, Alias learning, knob wheel pass-through.

**REPLACE:** wtype argv → xdotool (§6); `actions.json` **contents** — all 38
`omarchy-*`, 11 `hyprctl`/`hyprpicker`, `voxtype`, and herdr presets → the KDE
table in §7; Quickshell Panel + QML + IPC → PySide6 Panel (§8), porting upstream
`Model.js` (pure logic: slot ids, knob-turn derivation, status text)
function-for-function; `~/.config/omarchy/vibekey/` → `~/.config/vibekey/`;
`install.sh` + `vibekey-install-access` → PKGBUILD + package udev rule (§9);
`vibekey-herdr-agent` → OpenCode/Orca Presets (§5.2–5.4); upstream Panel "Grant
device access" pkexec flow → deleted (the package rule makes it moot).

### 2.2 Injection adapter (wtype → xdotool)

Upstream's entire injection surface is `wtype_argv` (`bin/vibekeyd:425-447`)
building **one-shot** combos; PTT-style holds use `command`/`release_command`
(shell), never held keys. Port:

- one-shot combo: `xdotool key <mods+key>` (single invocation, atomic
  press+release). Modifier table: `ctrl|control→ctrl`, `shift→shift`,
  `alt→alt`, `super|meta|win|logo→super`, `altgr→ISO_Level3_Shift`; keysym table
  passes through verbatim (they are X keysym names; `Prior`/`Next` = PageUp/Down;
  `F1..F24` unchanged). Unknown modifier → reject the Assignment (log + state
  error), as upstream rejects.
- hold-pair (behavior presets, §5.2): `xdotool keydown <chord>` on the Control's
  press edge, `xdotool keyup <chord>` on its release edge. This is what drives
  handy's Dictation (ticket 2: XTEST fake events activate the Tauri backend's
  root-window `XGrabKey` passive grab, both edges delivered, no `send_event`
  filtering, KWin nowhere in the chain).
- The unit must start `After=graphical-session.target` because `xdotool` needs
  `DISPLAY`/`XAUTHORITY` (present via Plasma's user-manager env import, probed);
  `spawn()` swallows failures silently (§9, risk R3).
- Failure logging: every spawn with non-zero exit gets logged to the journal and
  surfaced as a `state.json` `last.error` so the Panel status line can
  narrate it (upstream swallowed these — port risk R3 mitigation).

## 3. File protocol (Daemon ↔ Panel), kept from upstream

Config dir `~/.config/vibekey/`, runtime dir `$XDG_RUNTIME_DIR/vibekey/`:

| File | Writer | Reader(s) | Notes |
|---|---|---|---|
| `config.json` | only via `vibekey-config` (atomic replace) | Daemon (0.5 s mtime poll + SIGHUP), Panel | schema §4 |
| `seen.json` | Daemon (per press) | Panel | learned raw ids for Alias UX |
| `actions.json` (catalogue) | package (`/usr/lib/vibekey/actions.json`) | Daemon (seed + behavior-presets), Panel (picker) | resolved relative to the package dir, **not** `bin/`-relative — a wrong path silently no-ops first-run seeding (risk R6) |
| `state.json` | Daemon only, rewritten in place on every event | Panel (`QFileSystemWatcher` + 1 s/5 s poll) | fields: upstream set (`version,pid,connected,access,grabbed,mouse_passthrough,preview,knob_position,device,battery,last,events,error,updated`) **plus** `knob_mode` (§5.3), `last_error` (§5.3 failure surface), `keypad` (`online`, `at` — wireless-link state, §5.6), `power` (`standby_s`, `sleep_s`, `enc` — device telemetry, §5.7), `attention` (`sid` while an agent awaits approval, else `null`, §5.7) and `lighting` incl. `device_mode`: `0|1|2|"unknown"|"disabled"`, `pending_mode`, `last_error` (§5.5) |
| `preview` | Panel (`open` every 2 s while shown, `closed` on hide) | Daemon (trusts `open` for 6 s) | while active: events are reported, nothing runs |
| `manage_lights` | Panel (one-shot `"manage"`) | Daemon (consumes + unlinks on its 0.5 s poll) | the consented Manage lights request (§5.5) — the Panel never touches the vendor channel |
| `power` | Panel (one-shot JSON: `standby_s`/`sleep_s`/`enc`) | Daemon (consumes) | consented device power & noise-reduction writes (§5.7); every write is read back |

Preview semantics: with Preview on, the Daemon still publishes the event
(`last` with the would-be action name) but suppresses the Assignment and the
wheel hold-back stays as upstream. The Panel status line narrates *WOULD RUN …*
vs *RAN (sim)* for its own simulated clicks (§8).

## 4. Config schema (`~/.config/vibekey/config.json`)

```json
{
  "grab": true,
  "battery": true,
  "aliases": { "kbd:0x46": "knob" },
  "knob_modes": ["scroll", "sessions", "volume"],
  "buttons": {
    "key1": {"preset": "dictation_ptt", "label": "Dictation (hold, handy)",
             "behavior": "dictation.ptt", "keys": "ctrl+alt+space"},
    "key2": {"preset": "session_next", "label": "Next Session",
             "behavior": "session.next"},
    "key3": {"preset": "session_interrupt", "label": "Interrupt",
             "behavior": "session.interrupt"}
  },
  "lighting": {
    "mode_ring": true, "fail_blink": true, "low_battery": true,
    "brightness": 1.0,
    "patterns": { "Scroll": "off", "Sessions": "heartbeat:8", "Volume": "breathe:8" }
  }
}
```

- **Slots** (upstream `SLOT_LABELS`, kept — all six remain *detected*): `key1`
  Voice · `key2` ✓ Confirm · `key3` ✕ Cancel · `knob` press · `knob_right` ·
  `knob_left`. **User-assignable in v1: `key1`/`key2`/`key3`** (picker) and the
  turn modes via `knob_modes`; `knob` is fixed behaviour (§5.3), and
  `knob_right`/`knob_left` resolve through the current Knob mode (§4,
  `knob_modes`), not through config `buttons` entries. Slot resolution from raw
  ids is upstream's `DEFAULT_SLOTS` table (`kbd:0x01`/`kbd:super+0x0b`→key1,
  `kbd:0x28`→key2, `kbd:0x29`→key3, `kbd:0x46`→knob, wheel and
  `kbd:0x4f`/`kbd:0x2a`→knob_right/left); the `aliases` map wins over it, as upstream.
- **`buttons.<slot>` entry fields** — `preset` (catalogue id, informational),
  `label`, and execution fields copied from the catalogue at seed/edit time
  (`command`, `keys`, `release_command`, `release_keys`, `scroll`) **plus the one
  new field `"behavior"`** (§4.2). Dispatch order: `behavior` → built-in (§5);
  else `keys` → xdotool one-shot; else `command` → `bash -c` (with
  `release_command`/`release_keys` on the release edge, as upstream).
  `vibekey-config`'s `ALLOWED_BUTTON_KEYS` gains `behavior` + `keys`/`label` as
  already allowed.
- **`knob_modes`** — ordered list of catalogue `knob_turn` ids; knob press cycles
  it; runtime state resets to the first entry at boot; default
  `["scroll","sessions","volume"]` (ticket 6). Missing → the default. This
  **replaces upstream's per-config `knob_right`/`knob_left` entries**: turn events
  resolve against the catalogue entry of the *current* mode (which therefore
  stays available; the copied-fields trick no longer applies to knob turn).
- **`lighting`** — exactly the block accepted in ticket 11, with the rhythm
  extension (owner request, 2026-11-15). `patterns` values are strings
  addressed by Knob-mode **label**; a mode with no entry → `off`. Grammar:
  `off` | `solid:<0-20>` | `breathe:<0-20>` | `<rhythm>[:<level>[:<period_ms>]]`
  where `<rhythm>` ∈ `pulse` · `heartbeat` · `tick` · `wave` · `gallop` (host-driven
  sequences, §5.5; level default 8) · `alarm` (reserved for §5.7's
  awaiting-approval override). Code defaults:
  `Scroll:off`, `Sessions:heartbeat:8`, `Volume:breathe:8`.
  `brightness` is a multiplier (0.0–1.0) applied to every level the lighting
  module writes (effective level = level × brightness).
  Hot-reloaded by the existing 0.5 s config poll. The switches are feature
  toggles: `mode_ring` §5.3, `fail_blink` §5.4, `low_battery` §5.4,
  `attention_ring` §5.7.
- **`grab`** / **`battery`** / **`aliases`**: upstream semantics; `battery` now
  also gates the link-keepalive probe (§5.6) — with it off, link state stays
  optimistic.
- The `knob` slot is **fixed behaviour in v1** (§5.3): press = Knob-mode cycle,
  long-press = Enter injection (ticket 6 — not a user Assignment; upstream's
  `knob: key_enter` default is subsumed by that fixed behaviour).
- No migration code: every new field (`knob_modes`, `lighting`, `behavior`) has
  its default in code when absent, so upgrades never touch user config.

### 4.2 `behavior` presets — schema change and rationale

The Preset vocabulary decided on this map (agent, Dictation) has *fixed
behaviour* (GLOSSARY), which upstream's command-string catalogue cannot express.
New catalogue/entry field `"behavior"`: a small allow-list implemented in the
Daemon, resolved from `actions.json` at runtime — a deliberate exception to
"the Daemon never needs the catalogue once config exists" (that rule keeps
working for command/keys presets). Allow-list:

| `behavior` | § |
|---|---|
| `dictation.ptt` | 5.2 |
| `session.next` / `session.prev` | 5.3 |
| `session.focus` | 5.3 |
| `session.interrupt` | 5.3 |
| `orca.worktree.next` / `orca.worktree.prev` | 5.3 |
| `sessions.turn` (knob_turn side entry) | 5.3 |

Unknown `behavior` in config → do nothing, log, `state.json` `error`.

## 5. Behaviors (Daemon-side Presets)

### 5.1 Service discovery (OpenCode)

Read `~/.local/state/opencode/service.json` (`{"url","pid","password",…}`) for
URL + Basic-auth (`Authorization: Basic opencode:<password>`), ~5 s cache; on 401
re-read once and retry; "service not running" is declared **only after the retry
fails** (ticket 6). Target OpenCode **v2** API (`/api/*`); the V1 documented
routes (`/session/:id/abort`, `/tui/*`) do not exist on v2.2.7 — treat them as
non-existent ([evidence](https://github.com/jimOnAir/vibekey/blob/research/opencode-surface/research/opencode-surface.md)).
`--standalone` TUIs run private, unregistered servers (401) and are **out of v1
entirely** — documented known gap (ticket 6).

### 5.2 `dictation.ptt` — Voice Control (ticket 7, on ticket 2's mechanism)

- Press edge: `pgrep` handy (ms); absent → `notify-send "handy is not running"`
  in place of the action, **never auto-start** another app.
- Present → `xdotool keydown <chord>`; release edge → `xdotool keyup <chord>`.
  Chord is owned by this Preset: entry `keys` (catalogue default
  `ctrl+alt+space` = handy's Linux default).
- Required handy settings (checked by the **Panel**, never gated by the Daemon at
  fire): `keyboard_implementation = tauri` (the `handy_keys` backend reads
  `/dev/input` evdev, where XTEST events do not exist — hard trap),
  `shortcut_activation = push_to_talk` (ticket 7 prose calls it
  "activation_mode"; the store key is `shortcut_activation` — **verified**
  against the installed store: nested under `settings`), `overlay_style = none`,
  `always_on_microphone = true`, `accelerator = cpu` unless a per-box GPU test
  wins. No fallback mode in v1 (no CLI/SIGUSR2 degraded path).
- Published expectation, in docs and the Preset's tooltip: **~0.5–2 s
  key-up→text** (Parakeet v3, CPU/Vulkan; whisper-medium tier is seconds).
- `state.json` `last` reports the fire as `dictation.ptt`.

### 5.3 Agent Presets (ticket 6, on tickets 3/4's mechanisms)

**Control map**: ✓ Confirm = *next Session* (fixed default), ✕ Cancel =
*interrupt* (fixed default), knob **press** = cycle Knob mode, knob
**long-press** (≥400 ms, decided on the release edge) = Enter injection
(`xdotool key Return`, fixed — ticket 6), knob **turn** =
current Knob mode's `knob_turn` entry.

**Ring** = the Daemon's ordered cycle of root Sessions: ids from
`GET /api/session?parentID=null&order=desc` (stable `ses_…` keys; cursor-paginate
`session.list`). **Cursor** = Daemon position; a step = advance Cursor by turn
direction (✓ = forward) and raise the new Session's **Host**:

1. Orca: `orca terminal list --json` (re-listed **per fire** — handles are
   runtime-scoped; never match on `title`), row match
   `title == "OC | " + api.title`, fallback `worktreePath == location.directory`
   → `orca terminal switch --terminal <handle>`; then raise Orca's window:
   find via `wmctrl -lp` where `_NET_WM_PID` == the `orca-ide` main pid, `wmctrl
   -i -a <id>` (Orca's `terminal switch` changes content, never the OS window).
2. Plain terminal: `wmctrl -a` on the `OC | <title>` window title OpenCode sets
   itself (verify via `_NET_WM_PID` + `pgrep -a opencode` if multiple hits).

Orca CLI: invoke the **absolute** path — `/opt/stably-orca/resources/bin/orca-ide`
or the shim resolved from `~/.config/orca/linux-orca-cli-shim/orca`, overridable
by a config key — never bare `orca` (GNOME screen-reader collision). Preconditions:
`orca status --json`; `orca open --json` is the sanctioned cold start. Never talk
to the runtime `:6768`/daemon sockets directly.

`session.focus` (shipped Preset, assignable): raise the Cursor's Host only, no
Ring step — same resolution path.

`session.next`/`session.prev`/`sessions.turn` (knob-turn right/left): the cycle
above. Stale Session id (deleted) → skip to the next valid id **and** surface the
skip on the failure/status line below (ticket 6 lists "stale Session id (skip to
next valid)" among the notified events).
**Cursor drift** from user sidebar clicks / `ctrl+tab` is accepted for v1
(no title-resync). Mode announce on every Knob-mode switch (press):
`notify-send` + tray state + `state.json` `knob_mode`; ring pattern per §5.5.

`session.interrupt` — hybrid target: the **focused window's** Session when
resolvable (window title from `xdotool getactivewindow getwindowname`, matched as
above), else the Cursor's Session; the resolved target is named in the status
report. Mechanism order (ticket 6, verified on v2.2.7):

1. `POST /api/session/{id}/interrupt` → `{"interrupted":…}` — idempotent, no
   focus needed.
2. `orca terminal send --terminal <h> --interrupt` (Orca-hosted Sessions).
3. Keystroke fallback: raise Host, then `xdotool key Escape`.
   **Never Ctrl+C** — on an empty OpenCode prompt it is an `app.exit` path.

`orca.worktree.next`/`orca.worktree.prev` (the charting-era *stretch* — in v1,
the destination names "OpenCode/Orca agent presets"): Daemon-owned cycle
over `orca worktree list --json` — candidates = non-`isArchived` rows, order =
`sortOrder` (fallback `path`); `orca worktree activate --worktree
identity:<key> --json`, then raise the single Orca window (same `wmctrl` step).
Prev = same Ring backwards.

**Failure/status surface** (`notify-send` + tray icon state, works with the Panel
closed): OpenCode service down (after retry), zero root Sessions, all Session ids
stale, Orca not running mid-cycle, injection fired but unverifiable.

### 5.4 Lighting events

Presets **emit lighting events**; only the lighting module writes (§5.5).
Failure blink: when a Preset fire fails, and `fail_blink` is on, the **keycap of
the culprit Control** (ledIndex by slot: key1→0, key2→1, key3→2) blinks three
fast on↔off pairs at level 16, ring untouched. Fire-time-only blinks dodge the
standby gotcha: if the user just pressed a key, the device is awake.
No ambient blinks.

Low battery (on the §5.2 keepalive battery poll): `percent ≤ 10 && !charging` →
knob ring `breathe:6` while it lasts + exactly **one** `notify-send` per crossing;
hysteresis resets the latch at `> 20` %. The feature (ring indication and the
notification together) is gated by the `low_battery` switch.

### 5.5 Lighting module — protocol and architecture

Ground facts ([evidence](https://github.com/jimOnAir/vibekey/blob/research/backlight-control/research/backlight-control.md),
verified by two independent projects on real AU05 hardware; the TEA key already
sits in the upstream code at `bin/vibekeyd:139`):

- Vendor channel only: write to `vendor_fd` (`/dev/hidraw13`), TEA-encrypted
  report `0x55` (ECB, 8-byte blocks, 32 rounds): pad plaintext to 64 B, encrypt
  all 64, transmit `b"\x55" + ct[:63]`. **Exactly 64 bytes per `write()`.**
- GET all: `01 0b 88 01 00…`; SET:
  `01 0b 88 04 <fieldMask> <ledIndex> <mode> <bright> [4 × 5-byte records]…`;
  ack replies carry `cmd&0x1F=0x01`, group `0x0b`, opcode `0x88`, access
  `0x14` (`0x04|0x10`) and echo the masked field — **trust the ack**, ring
  readback verifiably returns stale values.
- 4 **monochrome** channels (`ledIndex` 0–3): K1 Voice, K2 ✓, K3 ✕, knob ring.
  **No colour byte exists anywhere in the family.** Per channel: effect type
  (0 off / 1 always-on / 2 breathe), breathe brightness (mask `0x20`),
  always-on brightness (mask `0x40`), all levels **0–20**. Field masks: `0x04`
  per-light type (offset `8+5·i+0`), `0x20`/`0x40` brightness
  (offsets `+3`/`+4`).
- Gotchas to enforce in the module (all from the note's §2.3): always send all
  four 5-byte records (a zeroed slot clears that light — read-modify-write);
  sustained breathing needs its params alongside the type (known-good per-LED
  record `[type, 0x0a, 0x02, 0x02, 0x02]`); correlate replies by frame pattern
  with a ~1.3 s deadline inside the existing `read_vendor` multiplexer (battery
  frames share the fd); writes are silently dropped while the keypad is in
  standby (5-min idle disconnects it) — treat no-ack as no-op; be the only
  config host (no other writer — Ulanzi Studio does not run on Linux; warn in
  docs against vendor-`--poll` helpers).
- Architecture: **single-writer module** inside the Daemon (confirmed
  architecture, tickets 10/11) over shared global device state — a write queue on
  the main loop, one outstanding acked SET at a time; Presets emit events
  (§5.4); Knob-mode→ring pattern (§5.3) and battery policy (§5.4) are policies
  on top. Startup: GET the device lighting config, keep the four records in
  memory, expose `lighting` in `state.json` (channels, acked state, errors) for
  the Panel.

#### Device lighting mode policy (ticket 12)

The **Device lighting mode** (GLOSSARY — Always Off / Always On / Working;
values `0`/`1`/`2`) gates whether per-light writes are visible on the device.
The Daemon is a **guest with one consented Manage lights**:

- Read the mode by GET at every connect; publish it in `state.json`
  `lighting.device_mode` (§3).
- Mode `0`/`1` → **all lighting policies idle** (ring pattern, failure blink,
  battery breathe write nothing). The Panel Lighting section shows the line
  `Device lighting mode: Always Off — vibekeyd's lighting is idle.` (or
  *Always On*) with a contextual **Manage lights** button; one `notify-send`
  per **Daemon start** — never per Dongle re-enumeration — only when the mode
  is known ≠ 2 **and** at least one lighting switch is on:
  `vibekey: AU05 device lighting is "Always Off" — knob ring and keycap blinks are idle. Open the Panel → Lighting to let vibekeyd manage lights.`
- **Manage lights** click → SET mask `0x01` = `2` (ack-confirmed as above),
  then immediately apply the current Knob mode's pattern. No ack (keypad
  asleep) → status line `No answer from the device — press any key on the
  AU05, then try again.`; the button stays, no auto-retry — a key press *is*
  the wake mechanism (same physics as fire-time-only blinks).
- **No consent memory**: every connect re-reads; if the user later sets mode
  0/1 in Studio, the line + button return (boot notify per its once-rule).
  Reverting is always the user's side, in Studio — vibekeyd never writes the
  mode back and offers no "give back" (it cannot know which mode they'd want).
- Mode **unknown** (GET unanswered — keypad asleep) → **optimistic**: treat as
  Working, features stay live; writes issued into sleep drop silently (the
  accepted gotcha), and blinks are fire-time (awake). `state.json` shows
  `"unknown"`, the Panel shows no line/button, and the Daemon re-GETs lazily
  at the first Control event after a boot/reconnect that left the mode
  unknown, and on config hot-reload that enables a feature.
- **Mask ownership** (binding):

  | mask | field | owner |
  |---|---|---|
  | `0x04` | per-light effect type | vibekeyd (read-modify-write) |
  | `0x20` / `0x40` | per-light breathing / always-on brightness | vibekeyd (read-modify-write) |
  | `0x01` | Device lighting mode | vibekeyd **only** via a consented Manage lights click |
  | `0x02` | device global brightness (all-on level) | user/Studio — **never** written by vibekeyd |

  The Panel brightness slider changes only the config `lighting.brightness`
  multiplier (§4) — it never touches the device's global brightness, so
  vibekeyd cannot dim a device the user set to Always On.
- **Rhythm engine** (owner extension, 2026-11-15): patterns naming a built-in
  rhythm (`pulse` · `heartbeat` · `tick` · `wave` · `gallop`; table
  `RHYTHMS` in `vibekeyd`) run as queued cycles on the single writer — one SET
  per step with `not_before` pacing; `pump()` re-queues the next cycle when
  idle past `rhythm_tail`. Rhythm steps never dirty the owner records; a mode
  switch, the `mode_ring` switch, or the low-battery latch purges queued
  `rhythm` frames so cycles never interleave. Device-native `breathe` remains
  available and is still the Volume default (zero host traffic for it).
- **All three switches off → total silence**: no lighting GET, no `0x88`
  traffic from vibekeyd at all (the battery opcode on the same fd is
  unaffected), `device_mode: "disabled"`, no notify — cleanest form of "be
  the only config host" for users who deliberately killed all lighting.
  Hot-reload turning any switch on triggers a GET immediately.

### 5.6 Wireless link awareness (owner ask, 2026-11-15)

The AU05 is wireless behind the Dongle: it drops its 2.4 GHz link after ~5
idle minutes (or a power switch), while its USB nodes and its PipeWire mic
source **remain** — so neither `/dev` presence nor `pactl` can distinguish
"keypad off" from "keypad idle" (field-proven: capture returns digital
silence while the node is up). The Daemon owns the truth, **authoritatively**:

- `06 03 0A 01` (docs/SOURCES.md) is answered by the **Dongle itself** — even
  with the keypad powered off; its byte 4 is the linked state. Queried every
  `BATTERY_INTERVAL` (15 s, piggybacked on the battery request) → instant
  `keypad: {"online": …}` in `state.json`. Pushed notices `0B 0B` (link),
  `0B 0D` (standby), `0F0` (mic powered on) are consumed when firmware sends
  them (unverified emission without the host-online handshake — harmless).
- Fallback while no link query has been answered (`battery: false`, odd
  firmware): the 40 s `LINK_STALE` silence heuristic (events + mic-relayed
  replies as contact) — published with `via` for debuggability.
- Optimistic at connect; `last_contact` is refreshed only by **mic-proof**
  traffic (the Dongle's own link answer never counts as the keypad being up).

The Panel's tray mic badge and handy card consume it: **badge = the AU05's
Dictation mic is unusable now** — Dongle gone (`connected: false`), keypad
asleep/off (`keypad.online: false`), or the audio stack is broken (missing/muted —
the only pactl-sourced case). The keypad cannot be woken from the host
(writes into sleep are dropped, §5.4) — the badge says press a key, which is
itself the proof of life.

### 5.7 Device power config, mic info, awaiting-approval ring (owner batch, 2026-11-15)

Three vendor-channel features with layouts per [docs/SOURCES.md](docs/SOURCES.md)
(vibed captured on 4.4.0, vibekey-lite device-observed reads):

- **Telemetry** (`state.json: power`): standby delay GET `01 01 2C 01`, sleep
  delay GET `01 01 42 01` (u32-le seconds at payload offset 4), noise reduction
  GET `01 01 90 01` (level@4, low u16@5, high u16@7). Read on link-up and
  every 5 min; skipped while the keypad is offline (those frames would die in
  the radio dark). The mic-enable field `01 01 2A` is NOT used — field-tested
  meaningless on 4.4.2 (see docs/SOURCES.md).
- **Consented writes** (the `power` one-shot file, manage_lights pattern):
  SET ops are `01 01 2C 02` / `01 01 42 02` (+u32-le) and `01 01 90 04`
  (+level, low, high) — note the differing op bytes. The Panel's
  "Device (power & mic)" box is the only author; every Apply re-GETs
  promptly and the card shows what the device actually reports (vibed lists
  writes that ack-but-don't-persist — the readback is the contract).
- **Awaiting-approval alarm**: every 5 s the Daemon asks
  `GET /api/session/{cursor}/permission` (v2 API) for the Cursor Session;
  a non-empty list means the agent is blocked. While true the ring runs the
  `alarm` rhythm (overrides the mode pattern, low_battery latch still outranks
  it), `state.json: attention` publishes `{sid, at}`, the status line says
  "hold the knob for Enter" — the knob's long-press is exactly the accept
  gesture for that Session. Standalone TUIs stay invisible (documented gap);
  `lighting.attention_ring` (default on) switches it off entirely.

## 6. xdotool specifics for the Panel (editors)

The picker's key-combo field stores the same chord syntax as `keys` entries
(`ctrl+shift+t`, `XF86AudioLowerVolume`, `Prior`…): normalized with upstream's
tables, executed as `xdotool key …`. **Non-US keyboard layout handling is an
accepted open fog item** (map "Not yet specified"): v1 passes keysyms through —
chords referencing symbols by name may misfire on non-US layouts.

## 7. Preset catalogue (`/usr/lib/vibekey/actions.json`)

Schema `version: 1` + `defaults` + `presets` + `knob_turn` (kept). New contents:

```json
"defaults": {
  "key1": "dictation_ptt", "key2": "session_next", "key3": "session_interrupt",
  "knob_modes": ["scroll", "sessions", "volume"]
}
```

(First-run seeding writes `buttons` from the per-slot preset entries — copying
`behavior` like the other fields — and `knob_modes` verbatim; upstream's
`"knob": "key_enter"` default is superseded by the fixed knob behaviour, §4.)
Command **content** below (group labels, step sizes like ±5 %, exact flags) follows
the replacement families named by the port audit's R2 and is catalogue content,
editable by the user — the *decided* parts are the presets' existence, behaviour,
defaults, and the fixed controls' wiring to them.

### 7.1 `presets`

| group | id | label | execution |
|---|---|---|---|
| Dictation | `dictation_ptt` | Dictation (hold, handy) | `behavior: dictation.ptt`, `keys: "ctrl+alt+space"`, tooltip "~0.5–2 s to text" |
| Agent | `session_next` | Next Session | `behavior: session.next` |
| Agent | `session_prev` | Previous Session | `behavior: session.prev` |
| Agent | `session_focus` | Focus this Session's terminal | `behavior: session.focus` |
| Agent | `session_interrupt` | Interrupt | `behavior: session.interrupt` |
| Agent | `orca_worktree_next` | Next Orca worktree | `behavior: orca.worktree.next` |
| Agent | `orca_worktree_prev` | Previous Orca worktree | `behavior: orca.worktree.prev` |
| Keys | `key_enter` | Press Enter | `keys: "Return"` |
| Keys | `key_escape` | Press Escape | `keys: "Escape"` |
| Keys | `key_tab` / `key_shift_tab` | Tab / Shift+Tab | `keys: "Tab"` / `"shift+Tab"` |
| Keys | `key_up`/`key_down`/`key_left`/`key_right` | Arrows | `keys: "Up"`… |
| Keys | `key_ctrl_enter` | Ctrl+Enter | `keys: "ctrl+Return"` |
| Media | `media_play` / `media_next` / `media_prev` | Play/pause, next, previous | `keys: "XF86AudioPlay"` / `"XF86AudioNext"` / `"XF86AudioPrev"` |
| Media | `media_lower` / `media_raise` / `media_mute` | Volume keys | `keys: "XF86AudioLowerVolume"` / `"…RaiseVolume"` / `"XF86AudioMute"` |
| System | `sys_screenshot` | Screenshot (Spectacle) | `command: "spectacle -rb"` (background, capture-to-clipboard; confirm the exact flags against the installed Spectacle during checklist item 13 — fact-check, not a re-decision) |
| System | `sys_lock` | Lock screen | `command: "loginctl lock-session"` |
| System | `sys_terminal` | New Konsole | `command: "konsole"` |
| System | `sys_bright_up` / `sys_bright_down` | Brightness ±5 % | `command: "brightnessctl set 5%+"` / `"brightnessctl set 5%-"` |

The Keys group **omits upstream's `key_ctrl_c` Preset**: ticket 6 codified
*never Ctrl+C* for the interrupt mechanism, so it is not shipped as a one-click
Preset; a user may still enter it as a custom combo. Likewise **no `ctrl+tab`
tab-cycle Preset ships** — ticket 6 declined the in-TUI route (stays a user
habit). The herdr group is gone (map Out of scope). Custom Assignments (free
`command` / `keys` / release pair) remain supported by the schema and the picker.

### 7.2 `knob_turn`

| id | label | right | left |
|---|---|---|---|
| `scroll` | Scroll | `scroll: "down"` (native wheel pass-through) | `scroll: "up"` |
| `sessions` | Sessions | `behavior: "sessions.turn"`, `dir: +1` | `behavior: "sessions.turn"`, `dir: -1` |
| `volume` | Volume | `command: "pactl set-sink-volume @DEFAULT_SINK@ +5%"` | `… -5%` |

Custom knob modes are config-editable (`knob_modes` + catalogue entries are the
same objects; users add turn entries to a user-mergeable section only if they
edit actions.json — Panel shows current mode, no reorder UI in v1, ticket 5).

## 8. Panel (PySide6) — Variant A "drawn device" (ticket 5)

Prototype `prototype/panel-picker` @ `3c26e5e` (`prototype_panel_picker.py`) is
the **visual source of truth** — port the drawing, hit zones, and status line
from it, do not redesign:

- **Window** (not a shell panel): left half draws the real AU05 — horizontal
  aluminium bar; speaker mesh + *Ulanzi* logo + five mic slots at the far end;
  aluminium knob with grip ticks and a recessed ring groove (the LED ring lives
  there); **three square white keycaps** (Voice / ✓ / ✕); strap hole. No 4th key
  (the "⊗ end-bar" was perspective — closed). Transparent interactive zones
  exactly over the art: **single click = simulate** (zone glows, event reported,
  nothing fires — Preview), **double-click = edit** (picker opens for that slot).
- **Header strip**: Knob-mode chip (current mode, live from `state.json`) ·
  knob turn position (`knob_position`) · battery.
- **Bottom status line** narrates every event, with the Preview distinction
  (*WOULD RUN …* from the Daemon's `last` vs *RAN (sim)* for zone clicks).
- **Preview checkbox, default on** — owns the `preview` heartbeat file.
- **Picker**: grouped-tile dialog over the catalogue (groups Dictation/Agent/
  Keys/Media/System) + a custom command field + a key-combo field (writing
  entries via `vibekey-config set-button`).
- **Icon language**: Ulanzi-style line art matching the physical caps — Voice
  cap: plain mic glyph, no arcs; ✓/✕ caps: central glyph (check/cross) between
  two open arcs, split rotated 45°; knob turn = open-ring ↺ ↻ arrows. Uniform
  graphite strokes, rounded caps/join, invert to white on press. Renderers
  `draw_mic/draw_check/draw_cross/draw_turn` + `_arcs(rot=)` + `line_icon()` in
  the prototype. **Gotcha (seen live):** a stylesheet'd `QPushButton` draws its
  `QIcon` at the pixmap's native size and ignores `setIconSize` — render pixmaps
  at the exact intended px, no devicePixelRatio 2× tricks.
- **Tray**: purple glossy circle with a white centered **U** (canonical renderer
  `draw_app_icon()` on the prototype branch); menu = show/hide Panel, Quit.
  Tray state conveys the **Knob mode** (dark bottom-left badge: ↕ Scroll,
  terminal Sessions, speaker Volume, first letter of a custom mode) and Daemon
  failure states (orange top-right **!**); both can show at once, tooltip names
  the mode (spec §8/§5.3; verified legible at 22 px).
- **handy card** (ticket 7): read-only card reading handy's store
  (`$XDG_DATA_HOME/com.pais.handy/settings_store.json`, with the config-dir
  path as fallback — **verified against the installed handy 0.10.0 on this box:
  data dir, everything nested under a top-level `settings` key**; GPU lives in
  `transcribe_accelerator`/`transcribe_gpu_device`, chord in
  `bindings.transcribe.current_binding`) showing
  detected-vs-recommended: `keyboard_implementation=tauri` ✓/✗,
  `shortcut_activation=push_to_talk` ✓/✗ (against the exact config line),
  `always_on_microphone` ON, overlay OFF, model tiers + copy-paste snippet.
  Chord drift vs the Dictation Preset's `keys` → warning + **"Fix handy"**
  button: one-way consented write of the chord into handy's `bindings` map only
  on click (never silent overwrite; the rest stays read-only guidance).
- **Lighting section**: three switches (`mode_ring` / `fail_blink` /
  `low_battery`) + one global brightness slider → `vibekey-config set lighting
  <json>`; no pattern editors (patterns live in config.json). While the Device
  lighting mode ≠ Working: one status line + contextual **Manage lights**
  button (ticket 12, §5.5 — the three-switch scope holds for the normal case).
- **Launch at login** checkbox → writes/removes
  `~/.config/autostart/vibekey-panel.desktop` (standard XDG autostart; reversible
  from KDE's own UI).
- **First-run enable button**: when the unit is not enabled (`systemctl --user
  is-enabled vibekeyd` ≠ enabled) the Panel shows a button running
  `systemctl --user enable --now vibekeyd` (Panel runs as the user, so it may).
- **Device access**: on EACCES (Daemon reports `access:"denied"` in
  `state.json`) Panel and Daemon print the exact fix:
  `gpasswd -a $USER vibekey` (+ re-login). No pkexec flow ships.

## 9. Packaging & install (ticket 8)

Single Arch package `vibekey` (daemon + Panel + `vibekey-config`), repo-root
`PKGBUILD`, installed `makepkg -si`. AUR submission out of scope (map).

- `depends=(python pyside6 xdotool wmctrl libnotify)` — the Arch package name is
  **`pyside6`** (verified `pacman -Qs`, 6.11.2-2 installed), **not**
  `python-pyside6`.
  `optdepends=(handy: Dictation Preset — AUR, never hard-depended; orca: agent
  Presets)`. Docs recommend the audited `handy` **0.10.1** (the AUR pkgver whose
  commit the handy note verified; R6's pin carried as guidance, since handy is
  opt-not-dep).
- `/usr/lib/udev/rules.d/70-ulanzi-vibekey.rules` (package-owned; filename
  settled ticket 8):
  ```udev
  SUBSYSTEM=="hidraw", ATTRS{idVendor}=="fff1", ATTRS{idProduct}=="00dd", MODE="0660", GROUP="vibekey"
  SUBSYSTEM=="input",  ATTRS{idVendor}=="fff1", ATTRS{idProduct}=="00dd", MODE="0660", GROUP="vibekey"
  ```
  Both subsystems mandatory (hidraw = reports + vendor writes; input = Grab).
  Static group rule, **not** `TAG+="uaccess"`: the Dongle's constant
  re-enumeration recreates nodes root-only and uaccess has a boot/greeter race
  for a headless user service (ticket 1, decisive).
- `/usr/lib/sysusers.d/vibekey.conf`: `g vibekey -`.
- `/usr/lib/systemd/user/vibekeyd.service`:
  ```ini
  [Unit]
  Description=vibekey AU05 daemon
  After=graphical-session.target
  [Service]
  ExecStart=/usr/lib/vibekey/bin/vibekeyd
  Restart=always
  [Install]
  WantedBy=default.target
  ```
- FHS: `/usr/lib/vibekey/{bin/vibekeyd,bin/vibekey-config,actions.json}` (+ Panel
  module dir; Panel entry point `/usr/bin/vibekey-panel`), icons
  `/usr/share/icons/hicolor/<size>/apps/vibekey.png` rendered from
  `draw_app_icon()` (16/22/24/32/48/64/128/256 + an SVG),
  `/usr/share/applications/vibekey-panel.desktop` (Name=vibekey Panel,
  Icon=vibekey, no-show-in-XFCE-style cruft — a plain utility entry).
- `post_upgrade`/`post_install`: `udevadm control --reload` and re-trigger the
  Dongle's nodes so existing devices get the new ownership without unplug
  (upstream's `vibekey-install-access:28-37` trigger loop, ported; enumerate
  parents via `udevadm info -e -p /sys/class/hidraw` filtered on the ids). Print
  the `gpasswd -a $USER vibekey` note (the one manual step — detected-and-taught
  at runtime too, §8; no sudo-script ships).
- Versioning: own series from **0.1.0**; `source=` = GitHub archive of our tag
  (`https://github.com/jimOnAir/vibekey/archive/v0.1.0.tar.gz`); upstream commit
  pinned in `UPSTREAM` + README credit; MIT `LICENSE` retained with upstream's
  copyright notice intact (repo is public; protocol credit to MrCroxx/olanzi and
  kubja/ulanzi-vibekey per README).

**Install flow (README):** `makepkg -si` → `gpasswd -a $USER vibekey` → re-login
→ `systemctl --user enable --now vibekeyd` (or open the Panel and click the
first-run button) → Panel: Launch-at-login checkbox, Preview, assignments.

**Uninstall (standard Arch semantics):** `pacman -Rns vibekey` removes package
files only; user state (`~/.config/vibekey/`, autostart file, group membership,
enabled unit) survives. One README section documents the full teardown:
`systemctl --user disable --now vibekeyd`, `gpasswd -d $USER vibekey`,
remove `~/.config/vibekey/` and the autostart entry.

## 10. Verification checklist (run in an implementation session)

Deterministic gates first, then the physical ones (each line = one command or
one observable outcome):

1. **Build**: `makepkg -sri` succeeds; `pacman -Ql vibekey` contains the §9 file
   list (rule under `/usr/lib/udev/rules.d/`, unit under
   `/usr/lib/systemd/user/`, `sysusers.d`, `actions.json`, icons, `.desktop`).
2. **Group/device access**: after `gpasswd -a` + re-login (or immediately — the
   Dongle re-enumerates often, ticket 1): `getfacl`/`ls -l` show
   `hidraw12`/`13` and the three `event*` nodes as `vibekey:rw` group-owned;
   daemon starts with no `access:"denied"`.
3. **Unit env**: `systemctl --user status vibekeyd` active; journal shows
   `connected:`; `busctl --user get-property …` or `After=graphical-session`
   hold verified by `systemd-analyze --user verify`; `DISPLAY` present in the
   service env (`systemctl --user show vibekeyd -p Environment` +
   `journalctl --user -u vibekeyd` on a test spawn).
4. **Grab leaks nothing**: `xev` shows **no** Enter/Escape/PrintScreen/keypad
   keysyms from the AU05 while the Daemon runs; wheel events **do** pass through
   while Knob mode = `scroll`, and do **not** while a custom turn mode without
   `scroll` is active.
5. **Firmware/variant probe** (implementation-time fog item, map "Not yet
   specified"): run `vibekeyd --probe`; use the prototype's *probe* window
   (pill → probe, logs to `/tmp/opencode/au05-probe.log`) to record this unit's
   knob-turn/press detection variant **and** settle the physical icon↔Control
   mapping (which cap is which slot). Record findings in the implementation PR.
6. **Config round-trip**: Panel edit → `vibekey-config` → `state.json` reflects
   new label within 1 s; Daemon re-fires with new action (config poll ≤0.5 s);
   `SIGHUP` forces immediate reload; empty `buttons: {}` survives restart
   (seed only creates a missing file, never overwrites).
7. **Preview**: with Preview on, a physical Voice press fires **nothing** (handy
   idle) and the status line narrates *WOULD RUN …* from the Daemon's `last`;
   a Panel zone click glows the zone and narrates *RAN (sim)* (zone clicks are
   always local simulation — §8 — regardless of the Preview checkbox; the
   checkbox gates what the **Daemon** runs for physical presses).
8. **Dictation**: hold Voice → handy records (overlay absent); release → text in
   the focused window 0.5–2 s later. Kill handy → next press → notify-send, no
   auto-start. Flip handy to `handy_keys` → Panel handy card shows ✗ (injection
   dead is expected — do not "fix" the Daemon). Before first use: confirm
   `ctrl+alt+space` is not already grabbed (handy note R2: check KWin's global
   shortcuts, `~/.config/kglobalshortcutsrc` — a bound chord makes handy's
   registration fail with `AlreadyRegistered`).
9. **Agent Presets** (needs ≥2 OpenCode root Sessions, one in Orca):
   `curl -u opencode:$(jq -r .password ~/.local/state/opencode/service.json)
   <url>/api/session?parentID=null` shows the Ring; ✓ raises the next Host;
   knob-turn in `sessions` mode steps the Ring both directions; ✕ on an
   in-flight run returns `{"interrupted":true}` and stops it; kill the service →
   one retry → single notify, tray state; `journalctl -f` shows **no `Ctrl+C`
   injection ever** (grep a test run for `xdotool key ctrl+c` = zero).
10. **Orca worktree Preset**: step cycles non-archived worktrees; window raises
    via `wmctrl -i -a` despite KWin focus-stealing prevention (⚠️ untested at
    charting — ticket 4 gap; verify with Panel closed).
11. **Lighting bench probes** (ticket 10, ~3 × 1 h, implementation-time):
    GET `0x88` parses; SET ring always-on `bright=5` (mask `0x40`, idx 3, full
    records) visible + `0x14` ack; power-cycle → GET settles cross-unplug
    persistence; type `2` (breathe) on ledIndex 3 settles ring-breathing; watch
    which physical cap lights per ledIndex 0–3. Standby: unplug keys 5 min →
    SET → no ack (dropped) — confirms fire-time-only blink design.
12. **Lighting policies**: knob press → ring pattern per config (chip + notify +
    ring agree); trigger a failure (handy not running / service down) →
    culprit keycap blinks 3×, ring stays; battery ≤10 % → ring `breathe:6` +
    one notify; >20 % → latch reset. **Device-mode bench** (§5.5): set Device
    lighting mode `0` via the vendor-channel test tool → lighting idles, one
    boot notify, Panel line + **Manage lights** appears; click → mode acked
    `2`, patterns resume; repeat the click with the keypad asleep → the
    no-ack line shows and mode is unchanged on the next try; all three
    switches off → `0x88` traffic vanishes entirely (`tcpdump`/`usbmon` or
    Daemon log = zero GETs).
13. **Command Presets**: each `command` preset does its thing with the Panel
    closed — volume turn moves `pactl` sink volume, brightness turn moves
    `brightnessctl`, `sys_lock` locks, `sys_screenshot` captures
    (confirm `spectacle -rb` flags against the installed Spectacle — fact-check),
    `sys_terminal` opens Konsole, media keys act in the running player.
14. **Panel/UX**: icon legible at 32 px on a dark tray; Launch-at-login writes
    /removes the autostart file; first-run enable button enables the unit;
    "Fix handy" changes handy's chord only after click; header chip tracks knob
    presses in real time.
15. **Uninstall**: `pacman -Rns vibekey` → binaries/rules/unit gone;
    `~/.config/vibekey/`, group membership, unit file state as §9 promises;
    README teardown steps verified end-to-end.
16. **Style gate**: prose and code names use GLOSSARY terms (no
    "remap/binding/macro", no "driver" for the Daemon, no capital-R Ring for the
    knob ring — call it knob ring).

## 11. Accepted open items (do not block; do not re-decide here)

- **Firmware-variant confirmation + physical icon↔Control mapping** on this
  unit — probe at implementation (checklist 5).
- **Lighting bench probes** (checklist 11) close the three residual unknowns
  ticket 10 named.
- **Non-US keyboard layout handling** for key combos — fog (map); v1 = keysyms
  verbatim.
- **Panel↔Daemon IPC upgrade** if the file protocol annoys in practice — fog;
  the protocol is kept as specced.
- **Cursor drift** (no title-resync), **standalone-TUI opacity**,
  **folder-workspace activation gap** — documented v1 gaps (tickets 4/6).
- **Mode-scoped ✓/✕ sets** — declined v1, post-v1 (map Out of scope).
