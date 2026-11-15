# Upstream port audit: compositor-independence check (ticket 0001)

**Audited upstream:** `jimmibram/vibekey-driver` @ `41ba904b` (2026-10-28), cloned to
`/tmp/opencode/vibekey-upstream` (not vendored into the repo).
**Verification target:** this system — Manjaro Linux, KDE Plasma, **X11** session
(session 3, `Type=x11`, `Seat=seat0`, `Active=yes`), AU05 Dongle `fff1:00dd` on
`/dev/hidraw12` + `/dev/hidraw13`.
**Domain terms** follow `GLOSSARY.md` (Control, Dongle, Grab, Preset, Daemon, Panel,
Preview, Alias, Assignment, Dictation). "key" below means an X11 keyboard key; physical
inputs are Controls. All upstream `file:line` refs are against the audited commit.

## Verdict (answers the ticket question)

**Yes — the Daemon's core is truly compositor-independent and is kept.** Everything
compositor- or Omarchy-specific sits in a thin, clearly bounded shell: (a) one argv
builder that shells out to `wtype` (→ `xdotool`), (b) the Quickshell Panel (→ PySide6,
settled), (c) the preset catalogue's `omarchy-*`/`hyprctl` commands and the herdr
agent (→ KDE/OpenCode/Orca Presets), (d) path/label cosmetics (`omarchy` in the config
dir), and (e) device access, which needs a package-owned udev rule regardless of
compositor. Nothing in `bin/vibekeyd` calls a Wayland, X11, or compositor API; the
device side (hidraw + EVIOCGRAB + sysfs discovery) works identically under X11, and the
device enumeration was verified against this Dongle on this box.

---

## 1. Inventory of Wayland / Omarchy / environment touchpoints

| # | Touchpoint | Where | Nature |
|---|---|---|---|
| T1 | `wtype` invocation (key-combo injection) | `bin/vibekeyd:408-447` (`WTYPE_MODIFIERS` 408, `WTYPE_KEYSYMS` 412, `wtype_argv` 425, argv built 441-447), called from `run_action` 478-482 | **Wayland-only tool**; the only compositor-dependent code in the Daemon |
| T2 | Config dir `~/.config/omarchy/vibekey/` | `bin/vibekeyd:43-45`, `bin/vibekey-config:21-23`, `Panel.qml:32-33` | Omarchy path segment; mechanism is XDG-neutral |
| T3 | Runtime dir `$XDG_RUNTIME_DIR/vibekey/` (`state.json`, `lock`, `preview`, `ssh-%C`) | `bin/vibekeyd:48-50,56`, `bin/vibekey-herdr-agent:19` | XDG-standard, compositor-neutral; systemd user services set `XDG_RUNTIME_DIR` (verified live) |
| T4 | `die_with_parent()` `PR_SET_PDEATHSIG` | `bin/vibekeyd:942-950`, default-on (`--no-pdeathsig` opt-out 975) | designed for the Quickshell `Process` parent; harmless under systemd (parent = `systemd --user`, dies only at logout) |
| T5 | Quickshell Panel (QML): imports `Quickshell`, `Quickshell.Io`, `Quickshell.Wayland`, `qs.Commons`, `qs.Ui`; `WlrLayershell` flash overlay | `Panel.qml:1-8, 406-435`; all other `.qml` files import `qs.*` | 100% Omarchy/Quickshell; replaced by PySide6 tray Panel (settled on the map) |
| T6 | Panel starts & supervises the Daemon as child | `Panel.qml:251-268` (`Process running: true`, 2 s `restartTimer`), `IpcHandler restartDriver` 384 | Panel↔Daemon coupling; replaced by `vibekeyd.service` user unit (`Restart=always`) |
| T7 | Preset catalogue commands: 38 `omarchy-*` command Presets, 11 `hyprctl`/`hyprpicker` Presets, hardcoded plugin path `$HOME/.config/omarchy/plugins/jimmibram.vibekey/bin/vibekey-herdr-agent` | `actions.json:94,101,406,409` (paths); `omarchy`/`hyprctl`/`voxtype`/`hyprpicker` across 10-354, 356-488 | every Omarchy/Hyprland/Voxtype Preset needs a KDE/handy replacement |
| T8 | herdr agent: `omarchy-osd` (54), `omarchy-shell … flash` (59), `hyprctl clients/activewindow/dispatch focuswindow` (80, 88, 286) | `bin/vibekey-herdr-agent` | whole file is herdr+Hyprland+Omarchy; replaced by OpenCode/Orca agent Presets (tickets 0003/0004/0006) |
| T9 | `install.sh`: `omarchy-plugin-validate`, plugin copy to `~/.config/omarchy/plugins/`, `omarchy-shell`/`omarchy plugin` CLI | `install.sh:15, 21-32` | Omarchy installer; replaced by `makepkg`/PKGBUILD + systemd unit + udev rule |
| T10 | `vibekey-install-access`: pkexec + copy rule to `/etc/udev/rules.d`, `udevadm trigger` dance | `bin/vibekey-install-access:12-37` | mechanism reusable (its trigger loop at 28-37 ports cleanly), but the Panel "Grant device access" flow goes away in favour of a package-owned rule |
| T11 | udev rule `TAG+="uaccess"` on `input` + `hidraw` | `udev/70-ulanzi-vibekey.rules:5-6` | correct for the mechanism, but see §3 — not the best choice for a re-enumerating Dongle with a user service |
| T12 | Env vars used anywhere: only `XDG_CONFIG_HOME`, `XDG_RUNTIME_DIR`, `HOME` fallbacks | `bin/vibekeyd:43,48`, `bin/vibekey-config:21`, `Panel.qml:28-29` | **No `WAYLAND_DISPLAY`, no `HYPRLAND_*`, no compositor env reads anywhere** — `grep` over the repo is clean |
| T13 | README requirements: "Omarchy 4 … `wtype` … `voxtype`" | `README.md:175-178` | documentation only |
| T14 | Miscellany: unused `import shlex` in `bin/vibekeyd:32`; `MockWindow/Game/Scribble/Picker/Tile/Device/KeyCap/ControlLabel/VibekeyIcon` QML files; `manifest.json` (Quickshell plugin manifest); `docs/*.png` | as listed | all die with the Quickshell Panel / are cosmetic |

---

## 2. Q1 — Does EVIOCGRAB keep keystrokes away from X11/libinput, and does hidraw keep reading?

### Premises

- P1. The Daemon opens the Dongle's **hidraw** nodes for reports (`bin/vibekeyd:574-591`,
  `input2` = standard reports, `input3` = vendor/TEA channel) and separately opens and
  grabs **every** evdev node matching `fff1:00dd` (`find_event_nodes` 529-546,
  `EVIOCGRAB` loop 606-617, ioctl constant 52). It drains the grabbed evdev fds so
  `select()` doesn't spin (`drain_events` 763-772, called from the loop 934).
- P2. On X11, KDE's keyboard input path is X server → `xf86-input-libinput` → `/dev/input/event*`
  (evdev). Live proof the Dongle is on that path right now: `xinput list` shows
  `AU05 AU05 Keyboard` (id=20), `Consumer Control` (id=21/22), `Mouse` (id=23) as X
  slave devices, while `getfacl` shows dmitry has no access to `event28-30` — X reads
  them through a **logind-supplied fd** (`org.freedesktop.login1.Session.TakeDevice`,
  which hands the client an fd and can revoke it with `EVIOCREVOKE`; this is why X works
  although the user is in neither `input` nor any ACL).

### Evidence (kernel, authoritative)

- **Grab is enforced in the input core, below every userspace reader.**
  `drivers/input/input.c` (Linux master), kernel-doc for `input_grab_device()`:
  *"When a device is grabbed by an input handle all events generated by the device are
  delivered only to this handle. Also events injected by other input handles are
  ignored while device is grabbed."* The enforcement site is `input_pass_values()`:
  `handle = rcu_dereference(dev->grab); if (handle) { … deliver only to it; break; }` —
  the `h_list` loop (which would include libinput's evdev client) is skipped entirely.
  `EVIOCGRAB` is the `_IOW('E', 0x90, int) /* Grab/Release device */` ioctl
  (`include/uapi/linux/input.h`), handled in `drivers/input/evdev.c` (`case EVIOCGRAB:
  … evdev_grab(...)`); one grab at a time (second getter gets `EBUSY`), auto-released
  on fd close.
- **libinput does not fight for the grab.** `grep -ci grab src/evdev.c` over libinput
  `master` → **0 matches**: the evdev backend never issues EVIOCGRAB (it relies on
  logind's fd-passing/revoke). So the Daemon's `EVIOCGRAB` succeeds even while X is
  attached to the same event nodes, and from then on libinput reads nothing — X never
  learns the keys were pressed. This is exactly why upstream's README can promise the
  factory Enter/Escape/PrintScreen keystrokes "never reach your apps" under Hyprland
  (`README.md:84-85,113-115`), and the argument is compositor-agnostic: it is a kernel
  input-core filter, not a Wayland feature.
- **hidraw delivery is upstream of, and independent from, the input layer.**
  `drivers/hid/hid-core.c`, `hid_report_raw_event()`: every raw report is first copied
  to all hidraw readers — `if (hid->claimed & HID_CLAIMED_HIDRAW)
  hidraw_report_event(hid, data, size)` — and only then fed to the input layer
  (`hidinput_report_event()`). `drivers/hid/hidraw.c` `hidraw_report_event()` appends
  the report to each opener's ring buffer. EVIOCGRAB lives in the input subsystem and
  cannot affect that earlier copy. **So yes: report reading stays complete while the
  evdev nodes are grabbed** — which is precisely how the upstream Daemon sees the Voice
  Control at all (factory usage `0x01` ErrorRollOver is dropped by hid-input and never
  becomes an evdev event, `bin/vibekeyd:7-9,65`).
- **Per-node grabs.** Each event node is grabbed individually, and the knob-scroll
  mode deliberately skips the node whose evdev `name` contains "mouse"
  (`bin/vibekeyd:601-602, 606-617`). On this box that topology exists verbatim:
  `event28` Consumer / `event29` "AU05 AU05 Mouse" / `event30` Keyboard (kernel
  journal + `/dev/input/by-id/usb-AU05_AU05_202606031150-if02-event-*`), so wheel
  pass-through for the scroll mode will work under libinput unchanged.

### Verified against this Dongle on this box

- HID interfaces match the Daemon's hard-coded keys: kernel logs
  `hidraw12: … on usb-0000:0d:00.0-5/input2` (the report interface; hid-generic named it
  "Mouse" because it carries a mouse collection too) and `hidraw13: … /input3` (vendor,
  also spawns legacy `hiddev104`). `find_hidraw_nodes`' `"input2"/"input3"` keys
  (`bin/vibekeyd:500,575`) therefore resolve here.
- `find_event_nodes`' sysfs assumption holds: `/sys/class/input/event30/device/id/vendor`
  → `fff1`, `…/product` → `00dd`.

### Conclusion

The Grab mechanism (kernel EVIOCGRAB) is the *only* mechanism that works equally under
X11 and Wayland and does not require compositor cooperation. **Keep as-is.** Port risk:
if the Daemon dies with a Control logically "down" in XKB (crash between press and
release of an injected combo), X has no physical key to release — irrelevant, because
injection is always a one-shot `key` press+release within a single process (§4), and
kernel-side state is irrelevant once the physical press was never delivered.

---

## 3. Q2 — Do systemd user services get the uaccess ACL, and does it survive re-enumeration?

### Mechanism (systemd 261, as installed here)

1. `73-seat-late.rules` (installed copy, `/usr/lib/udev/rules.d/73-seat-late.rules:14-16`):
   skips `ACTION=="remove"`; resolves the seat (`ID_SEAT`, else parent import, else
   `seat0`); `TAG=="uaccess|xaccess-*", ENV{MAJOR}!="", RUN{builtin}+="uaccess"`.
2. The builtin (`src/udev/udev-builtin-uaccess.c`, systemd main): no-op unless run by
   the udev worker for a device that actually carries the `uaccess` tag; requires
   `logind_running()`; then `sd_seat_get_active(seat)` → **the active session's UID** —
   and calls `devnode_acl(fd, uids)`. No active session on the seat → **silently no
   ACL**. It runs on `add` events; the ACL is a property of the freshly (re)created
   node.
3. ACL entries are **UID-based, not cgroup-based**: any process of that UID opening the
   node gets `rw` — a **systemd user service is covered** (same UID 1000; user manager
   env verified live: `systemd-run --user env` carries `XDG_RUNTIME_DIR=/run/user/1000`,
   `DISPLAY=:0`, `XAUTHORITY=/tmp/xauth_JSqSAy`).
4. Live proof the machinery works here: `/dev/hidraw0` (EVision keyboard, vendor rule
   tags it) → `getfacl`: `user:dmitry:rw-`; `udevadm test` shows `RUN{builtin}+="uaccess"`
   firing for it.

### Why the ACL "vanished entirely" on this box — fully explained

- **There is no rule tagging `fff1:00dd` on this box at all.** `/etc/udev/rules.d/`
  contains no `70-ulanzi-vibekey.rules`; `udevadm test` for `hidraw12` ends with
  `TAGS=:seat:` — seat tag present, **`uaccess` absent** → step 1's condition never
  matches → the node is recreated at udev defaults on every add: `hidraw` →
  `crw------- root:root` (observed for `hidraw2`, 12, 13 — all untagged devices),
  `event*` → `root:input 0660` (group from `50-udev-default.rules:51 SUBSYSTEM=="input",
  GROUP="input"`). dmitry is **not** a member of `input` (`id`, `getent group input`),
  so neither reports nor Grab are possible today.
- **Re-enumeration wipes node state.** Journal (this box): 19 full USB re-enumerations
  of `fff1:00dd` between 15:05:36 and 15:07:45 (~every 7 s; HID instance numbers
  `.000D`→`.0032`; each cycle recreates `hidraw12/13` and `event28-30`). Node
  recreation destroys any ACL — including one applied manually via `setfacl` or by a
  transient rule. Nothing re-applied it afterwards *because no rule matches*. Other
  devices "keep their `+`" only because their vendor/package rules re-TAG them, so the
  builtin fires on every `add`. (Note: upstream's claim that the Dongle reboots every
  ~4 s *while unheld* matched this episode, but the Dongle then stayed up for 100+ min
  with nothing holding it — holder scan empty; the churn appears episodic here.)
- Had the upstream TAG+=uaccess rule been installed, the ACL **would** have been
  re-applied on each re-add (session 3 active on seat0 throughout, X11) — but with a
  residual race: the grant only lands a few ms after node creation, and **only if an
  active session exists at that moment** — at boot the Dongle enumerates while only the
  greeter session is active, so the ACL would be granted to the greeter's UID; after
  real login there is no further `add` to re-grant, leaving a **user service denied
  until the next re-enumeration** (the upstream Panel papers over exactly this with its
  re-triggering "Grant device access" button, `Panel.qml:327-341`; a service has no
  button).

### What the package-installed static rule should look like

Both subsystems are mandatory: **`hidraw`** (interfaces 2+3 — reports and vendor
channel/battery) and **`input`** (all three event nodes — the Grab). Recommend a
deterministic, session-independent grant via a dedicated group, not uaccess:

```udev
# /usr/lib/udev/rules.d/90-vibekey.rules   (package-owned)
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="fff1", ATTRS{idProduct}=="00dd", MODE="0660", GROUP="vibekey"
SUBSYSTEM=="input",  ATTRS{idVendor}=="fff1", ATTRS{idProduct}=="00dd", MODE="0660", GROUP="vibekey"
```
plus `sysusers.d: g vibekey -` and installing the user into `vibekey` (PKGBUILD
`post_install`), and on install re-trigger like upstream does
(`vibekey-install-access:28-37`: `udevadm control --reload` + `udevadm trigger
--parent-match=<usb parent> --action=add` — reusable verbatim).

| Option | Applies at | Survives re-enumeration | Independent of session state | Verdict |
|---|---|---|---|---|
| `TAG+="uaccess"` (upstream) | udev worker, on `add`, only if an active session exists | Yes (re-added each `add`) — **but not if the node's `add` happened pre-login** | No | Works (proven here via hidraw0) but has a boot/greeter race for a service; Panel-era UX |
| `MODE/GROUP="input"` + user in `input` | node creation, always | Yes | Yes | Deterministic but scope = **all** keyboards/mice on the box (keystroke-sniffing group) — reject for the default install |
| `MODE="0660", GROUP="vibekey"` both subsystems + `sysusers.d` | node creation, always | Yes | Yes | **Recommended**: deterministic at creation, minimal scope, service-friendly |

Keep `TAG+="uaccess"` as an optional extra line only if ad-hoc CLI tools (e.g.
`vibekeyd --probe` from a shell of the active user) should work without group
membership — it does not conflict with the group grant.

---

## 4. Q3 — wtype call sites and xdotool equivalence

### Upstream's full injection surface (all `wtype` sites; enumerated by grep)

| Site (file:line) | What it does | xdotool equivalent |
|---|---|---|
| `bin/vibekeyd:425-447` `wtype_argv` → argv `["wtype", "-M", m..., "-k", KEY, "-m", m...]` (441-447) | Build a **one-shot** combo: press modifiers (`-M`), press+release the key (`-k`), release modifiers (`-m`); single process, modifiers auto-released at exit (wtype man: `-M` press, `-m` release, `-k` "Type (press and release)") | `xdotool key m1+m2+KEY` — one invocation, same atomic press+release semantics |
| `bin/vibekeyd:468, 478-482` (press phase `keys` field) → `spawn(argv)` | Run the combo when a Control fires | same as above |
| `bin/vibekeyd:474, 479` (release phase `release_keys`) → same builder | Run a combo when a Control releases | same; still one-shot (e.g. "on key-up send Tab") |
| `bin/vibekeyd:408-411` `WTYPE_MODIFIERS` (`ctrl,shift,alt,super/meta/win→logo,altgr`) | Map user chord names to wtype modifier names | `ctrl/shift/alt` identical (xdotool aliases → `Control_L` etc.); **`logo→super`**; **`altgr→ISO_Level3_Shift`** (xdotool has no `altgr` alias; falls through to keysym resolution — "any valid X Keysym string will work") |
| `bin/vibekeyd:412-422` `WTYPE_KEYSYMS` (`Return, Escape, BackSpace, Prior, Next, space, plus, …`) | Normalize to wtype/XKB names | **Pass through unchanged** — these are X keysym names; xdotool resolves keysyms as-is (`Prior`/`Next` = `Page_Up`/`Page_Down`). `F1-F24` handling (437-438) unchanged |
| `bin/vibekeyd:476` (`command` / `release_command`, spawned via `bash -c`, 450-460) | PTT hold/release pairs: `voxtype record start/stop` (`actions.json:12-18`) | **Compositor-neutral — no tool change**; replace `voxtype` with the Dictation app's CLI/hotkey per the map (handy) |
| `bin/vibekeyd:469-472, 885-896` (`scroll`) | Native wheel pass-through (mouse event node left un-grabbed) | **No injection at all** — libinput gets the wheel ticks directly (X shows the AU05 Mouse slave, §2) |
| `README.md:175` requirement line | — | dependency note becomes `xdotool` |

### Coverage analysis (combos, hold/release, repeat)

- **Key combos:** fully covered — the Daemon only ever builds one-shot combos; `xdotool
  key` matches 1:1.
- **Hold/release pairs:** upstream holds **nothing** down across invocations — PTT and
  similar press/release Assignment pairs use `command`/`release_command` (shell), not
  keys (`bin/vibekeyd:463-484`; the whole `wtype` path is always
  press+release within one process). So no cross-process modifier-hold has to be ported.
  If a future Preset wants *key*-based hold (e.g. hold `Shift` while pressed), xdotool
  has `keydown`/`keyup` (both accept the same keystroke syntax) — capability preserved.
- **Repeat suppression:** there is none upstream to port. X11 auto-repeat needs a
  physical (or held XTEST) key press visible to the server; the Grab means X never
  sees the Dongle's presses, and one-shot `key` cannot repeat. The knob's repeaty
  "turn" events run through `command`-based Presets or native wheel — same as upstream.
- **Residual X11-only notes:** XTEST synthetic events can be rejected by apps when sent
  with `--window` (XSendEvent path); the Daemon never targets a window (XTEST to the
  focused window — same model as wtype's virtual keyboard). `xdotool` needs
  `DISPLAY` + `XAUTHORITY` + XTEST (available in this user session env, verified; see
  R3 for the ordering risk).

---

## 5. Panel↔Daemon coupling (the contract the PySide6 Panel must reimplement)

All file-based, compositor-neutral — **keep the protocol** (revisit only if ticket 0005
proves the polls annoying, per map.md fog):

| Contract | Daemon side | Panel side (upstream, to reimplement) |
|---|---|---|
| Live state | `state.json`, rewritten in-place on every event (`write_json_inplace`, `bin/vibekeyd:213-224`; single-writer rationale 214-217) | `FileView watchChanges` + 1 s/5 s poll (`Panel.qml:178-223`) → `QFileSystemWatcher` + poll |
| Preview heartbeat | reads `preview` file, trusts `open` for 6 s (`bin/vibekeyd:56-57, 798-808`; used 847-848, and wheel held back 885-886) | writes `open` every 2 s while popup open, `closed` on hide (`Panel.qml:236-247, 363-374`) |
| Assignments | polls `config.json` every 0.5 s by mtime (`bin/vibekeyd:59, 284-301, 907-910`), also SIGHUP (981) | writes only via `bin/vibekey-config` subprocess (atomic replace; `Panel.qml:274-315`) |
| Seen/Alias | `seen.json` per press (`bin/vibekeyd:341-369`); `aliases` map wins over defaults (307-318, `slot_for` 833-842) | learns an Alias when an editor is open and a fresh `state.last.id` arrives → `vibekey-config alias` (`Panel.qml:154-162`) |
| First-run defaults | seeds `config.json` from `actions.json` `defaults` (`bin/vibekeyd:238-281`) — **mirrors** `Model.js:89-99,162-170` (keep the two implementations in sync) | reads the same catalogue for the picker (`Panel.qml:205-214`) |
| Supervisor | `flock` single-instance (`bin/vibekeyd:953-966`); `PR_SET_PDEATHSIG` (942-950) | Panel `Process` + restart timer (251-268), `restartDriver` IPC (384) → **systemd user unit** `Restart=always`, unit owns supervision |
| Access affordance | state `access:"denied"` + hint (`bin/vibekeyd:810-816`) | pkexec "Grant device access" (327-341) → **delete** (package rule, §3) |
| Feedback flash | — | `IpcHandler flash` + layershell overlay (`Panel.qml:376-435`), called by herdr agent → tray icon flash / `org.freedesktop.Notifications` |
| herdr OSD | — | `omarchy-osd` (`vibekey-herdr-agent:54`) → replaced with agent Presets |

`Model.js` (270 lines) is pure, framework-free logic (slot ids, knob-turn pair
derivation, status text) — port it function-for-function into the PySide6 Panel.

---

## 6. Keep / replace decision table

| Component | Decision | Port action |
|---|---|---|
| `bin/vibekeyd` device core (discovery 499-546, TEA 139-188, report decode 685-761, Grab 606-617, state/Preview/config plumbing 195-401, 779-936) | **KEEP** | as-is; stdlib-only; verified topology on this Dongle |
| EVIOCGRAB Grab | **KEEP** | works identically under X11 (§2); no libinput conflict |
| hidraw report reading (incl. ErrorRollOver Voice Control) | **KEEP** | independent of Grab (§2); this is why hidraw, not evdev, is the read channel |
| `wtype_argv` + modifier/keysym tables (`bin/vibekeyd:408-447`) | **REPLACE** | `xdotool key` + `super`/`ISO_Level3_Shift` mapping (§4) |
| `command`/`release_command` shell path (incl. PTT pattern) | **KEEP** | compositor-neutral; only Preset *contents* change |
| `PR_SET_PDEATHSIG` default (942-950) | **KEEP (note)** | harmless under systemd; document, or launch unit with `--no-pdeathsig` for clarity |
| Config dir `~/.config/omarchy/vibekey/` | **REPLACE path** | `~/.config/vibekey/` (3 sites: `vibekeyd:43`, `vibekey-config:21`, new Panel) |
| Runtime dir `$XDG_RUNTIME_DIR/vibekey/` + files (`state.json`, `preview`, `lock`) | **KEEP** | XDG-standard; present in systemd user services (verified live) |
| `bin/vibekey-config` | **KEEP** | path rename only |
| `actions.json` catalogue **schema** (presets/knob_turn/defaults) | **KEEP** | good structure; used by daemon seed + Panel picker |
| `actions.json` catalogue **contents** (38 `omarchy-*`, 11 `hyprctl`/`hyprpicker`, 3 `voxtype`, 4 hardcoded plugin paths) | **REPLACE** | KDE/handy/OpenCode/Orca Preset set (feeds tickets 0006-0008) |
| `udev/70-ulanzi-vibekey.rules` (`TAG+="uaccess"`) | **REPLACE** | package rule, `MODE="0660" GROUP="vibekey"` on `hidraw` **and** `input` + `sysusers.d` (§3) |
| `bin/vibekey-install-access` | **REPLACE** | not shipped as runtime UX; reuse its udevadm re-trigger loop in `post_install` |
| `install.sh` | **REPLACE** | PKGBUILD: install daemon + catalogue under `/usr/lib/vibekey` (mind `PLUGIN_DIR`-relative `actions.json` lookup, `vibekeyd:46-47`), user unit `vibekeyd.service` (`Restart=always`, `After=graphical-session.target`) |
| Quickshell Panel (all `.qml`, `manifest.json`, layershell flash, IPC, `Quickshell.env/execDetached`) | **REPLACE** | PySide6 tray Panel per ticket 0005; port `Model.js` helpers |
| Panel↔Daemon file protocol | **KEEP** | §5 contract |
| `bin/vibekey-herdr-agent` (hyprctl/herdr/omarchy-osd) | **REPLACE** | OpenCode/Orca agent Presets (tickets 0003/0004/0006); keep its SSH control-socket idea only if remote Sessions enter scope |
| README/requirements text | **REPLACE** | rewrite for Manjaro/KDE; retain MIT attribution |

---

## 7. Port risks, ranked

| Sev | Risk | Evidence | Mitigation (feeds ticket 0008) |
|---|---|---|---|
| 🔴 R1 | **No device access as shipped:** untagged `hidraw` = `0600 root:root`, `event*` = `0660 root:input`, user not in `input`; each Dongle re-enumeration recreates nodes, wiping any ad-hoc ACL (observed: 19 re-enumerations in 2.2 min; nodes now bare) | §3 live probes | package udev rule (§3) + `sysusers.d` + `groupmems`; `udevadm trigger` on install; Daemon already retries (`vibekeyd:58, 810-816`) |
| 🔴 R2 | **Preset catalogue is unusable off-Omarchy:** 38 `omarchy-*`, 11 `hyprctl`/`hyprpicker` commands, hardcoded plugin paths; default first-run config *seeds these* (`vibekeyd:265-281`), so a naive port ships broken Assignments (incl. `key2`→herdr agent path) | `actions.json:94,101,136-354,406-409` | full KDE replacement set (spectacle, konsole, pactl/brightnessctl, `loginctl lock-session`, KWin/dbus alternatives); new `defaults` block |
| 🔴 R3 | **Injection needs the X session env in a *user service*:** `xdotool` requires `DISPLAY`+`XAUTHORITY`+XTEST; today these exist in the user-manager env (verified via `systemd-run --user env`), but only because Plasma imported them — starting the unit before/without a graphical session silently breaks every key-Assignment (`spawn` swallows failures, `vibekeyd:450-460`) | live probes; xdotool man | `After=graphical-session.target` + `PartOf=`, and/or resolve env at spawn time (read `XAUTHORITY` fallback); log injection failures |
| 🟡 R4 | **Daemon supervision moves:** upstream safety = Panel child + `PDEATHSIG` + flock; port must supply `Restart=always` etc. flock stays as double-start guard | `Panel.qml:251-268`; `vibekeyd:942-966` | user unit (settled on map); note in spec |
| 🟡 R5 | **Hard-coded `input2`/`input3` interface names** gate connection (`vibekeyd:575`); verified for this unit, but firmware variants exist upstream (knob-as-wheel vs Right/Backspace, `README.md:118-124`) and another variant could renumber interfaces | journal `…/input2`→hidraw12, `…/input3`→hidraw13; by-id `if02`/`if03` | keep constant but fail loud in `state.json` `error`/`--probe`; matches existing map.md fog item |
| 🟡 R6 | **`~/.config/omarchy` rename + catalogue-relative `actions.json`** (`PLUGIN_DIR` = parent of `bin/`) → packaging layout must match or first-run seeding silently no-ops | `vibekeyd:43,46-47` | spec the FHS layout (`/usr/lib/vibekey/{bin,actions.json}`, `~/.config/vibekey/`) |
| 🟡 R7 | **herdr agent + flash/OSD IPC have no X11/KDE analogues** (`hyprctl`, `omarchy-osd`, `omarchy-shell -q … flash`) | `vibekey-herdr-agent:54,59,80,88,286` | design in tickets 0003/0004/0006; delete IPC surface |
| 🟡 R8 | **Knob scroll pass-through relies on name matching** the mouse event node (`name ~ "mouse"`, `vibekeyd:601-602`); works here ("AU05 AU05 Mouse") but is firmware-name-sensitive like R5 | `xinput` id=23; `/dev/input/event29` | same probe-time check |
| 🟢 R9 | XTEST-rejection by niche apps (only `--window`/XSendEvent mode — unused) | xdotool man SENDEVENT NOTES | none needed |
| 🟢 R10 | State/Preview heartbeat & `state.json` file protocol racy by design (single writer, in-place rewrite) — unchanged from upstream, worked under Quickshell; Qt's watcher behaves equivalently | `vibekeyd:213-224`, `Panel.qml:218-223` | keep; revisit only in ticket 0005 prototype |
| 🟢 R11 | Cosmetic cruft: dead `import shlex` (`vibekeyd:32`); README Omarchy sections | — | sweep during port |

## Rejected paths

- **uinput instead of Grab+xdotool** (single synthetic-device design): unneeded — the
  kernel-level Grab is compositor-independent (§2) and upstream protocol work rides on
  hidraw; xdotool covers injection without loading `uinput`.
- **Joining the user to `input`:** works but grants every keyboard/mouse system-wide —
  the dedicated group (§3) is strictly better at equal cost.
- **Staying with `TAG+="uaccess"` alone:** functional here (hidraw0 proves it) but the
  add-time active-session requirement (§3 step 2) is a standing footgun for a
  headless-ish user service around a churning Dongle.
- **KWin scripting / `qdbus` instead of xdotool for combos:** couples Presets to KDE
  internals for no gain; XTEST is the compositor-agnostic X11 mechanism (and the map
  already settled xdotool).

## Sources

- Upstream: `github.com/jimmibram/vibekey-driver` @ `41ba904b` (2026-10-28) — all
  `file:line` refs; README claims at 84-85, 109-147, 148-178.
- Linux kernel (`master`, fetched 2026-11-15): `include/uapi/linux/input.h`
  (EVIOCGRAB); `drivers/input/input.c` (`input_grab_device` kernel-doc;
  `input_pass_values` grab filter; `input_inject_event` doc); `drivers/input/evdev.c`
  (`case EVIOCGRAB`); `drivers/hid/hid-core.c` (`hid_report_raw_event`: hidraw copy
  before `hidinput_report_event`); `drivers/hid/hidraw.c` (`hidraw_report_event`).
- systemd (`main`, 261 installed): `src/udev/rules.d/73-seat-late.rules` (installed
  copy quoted); `src/udev/udev-builtin-uaccess.c`;
  `org.freedesktop.login1.Session` API (`TakeDevice`/`PauseDevice`/`ResumeDevice`,
  `EVIOCREVOKE` in `drivers/input/evdev.c`).
- libinput `master`: `src/evdev.c` — no EVIOCGRAB usage (0 matches).
- `xdotool(1)` (Arch `extra/xdotool` 4.20260303.1; man.archlinux.org/man/xdotool.1.en):
  `key`, `keydown`/`keyup`, aliases alt/ctrl/shift/super/meta, keysym fallback,
  `--clearmodifiers`, XTEST requirement, SENDEVENT NOTES.
- `wtype(1)` (man.archlinux.org/man/wtype.1.en, v0.4): `-M/-m/-P/-p/-k`, modifier list
  incl. `logo`/`altgr`, auto-release on exit.
- Live probes on this host (2026-11-15, ~14:32 boot, X11 session 3 active): `ls -l`/
  `getfacl` of `/dev/hidraw*`, `/dev/input/event28-30`; `loginctl show-session 3`;
  `id`; `udevadm test` (hidraw0 vs hidraw12); `udevadm info`; kernel journal Dongle
  churn (`journalctl -k`); `xinput list`; `systemctl --user show-environment`;
  `systemd-run --user env`; `getent group input`; `/usr/lib/udev/rules.d/50-udev-default.rules:51`.
