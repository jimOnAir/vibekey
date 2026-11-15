# Handy on X11/Arch: can the Daemon drive its PTT hotkey? (ticket 0002)

**Audited upstream:** `cjpais/Handy` @ `v0.10.1` (`aca8985190c3ad7f361d8a80cb30f179513ed690`),
cloned to `/tmp/opencode/handy` (not vendored). Dependency crates inspected at the
versions this build pins: `tauri-plugin-global-shortcut` 2.3.2, `global-hotkey` 0.8.0,
`handy-keys` 0.3.5 (extracted under `/tmp/opencode/{tpgs-crate,gh-crate,hk-crate}`).
**Packaging audited:** AUR `handy` 0.10.1-1 (repo HEAD `e730233`, 2026-11-14), cloned to
`/tmp/opencode/aur-handy` — its `_tag` (PKGBUILD:6) pins **the same commit as this audit**.
**Target system:** this box — Manjaro, KDE Plasma, X11 session.
**Domain terms** per `GLOSSARY.md`: *Dictation* is push-to-talk handled by the handy app;
*Preset*, *Daemon*, *Grab*, *Dongle*, *Control* (physical input); "key" means an X11
keyboard key. All `file:line` refs are against audited commits.

> The ticket links `cfaxman/handy`; that URL is **404** (GitHub API, and `git clone`
> 401-prompts). The live, canonical upstream — the one the AUR package names
> (`url="https://github.com/cjpais/Handy"`, PKGBUILD:10) — is `cjpais/Handy`, and everything
> below is audited there. (`handy-keys`, handy's keyboard backend library, now lives at
> `github.com/handy-computer/handy-keys` — plausibly the source of the misattribution.)

## Verdict (feasibility for press/release hotkey injection)

**Feasible — YES.** handy's default keyboard backend on Linux registers its Dictation
hotkey as an **X11 server-side passive grab (`XGrabKey` on the root window)** and its event
loop dispatches both `KeyPress` → *Pressed* and `KeyRelease` → *Released* with no
`send_event` filtering; the XTEST spec guarantees XTEST-faked key events perform
"passive grab activation … just as if the corresponding input device action had
occurred"; and `xdotool keydown`/`keyup` inject via XTEST. Therefore the Daemon — which
Grabs the Dongle's evdev nodes and shells out to `xdotool` (settled, ticket 0001) — can
bracket a Dictation session with

```
xdotool keydown ctrl+alt+space   # on Voice Control press
xdotool keyup   ctrl+alt+space   # on Voice Control release
```

against handy in **`push_to_talk`** activation mode (press = start recording, release =
transcribe + type/paste), with `hold_or_toggle` (handy's default) as a human-friendly
alternative and **two `handy --toggle-transcription` CLI invocations as an evidenced
no-hotkey fallback**. Required pins: keep the **Tauri** keyboard implementation (the
Linux default — *not* `handy_keys`, whose evdev listener cannot see XTEST events), keep
the overlay off (Linux default), and give handy its `xdotool` (already a Daemon
dependency — handy itself opts-depends on it). Release→text is **sub-second to ~2 s**
with the CPU-fast Parakeet model on a modern CPU, seconds with Whisper models — no
hidden architecture problem, just model cost.

---

## 1. Q1 — How recording is triggered, and what the hotkey may be

### Trigger surfaces (all at v0.10.1)

| Surface | Semantics | Evidence |
|---|---|---|
| **Global hotkey** (`transcribe` binding) | press **and** release edges both delivered; activation mode = `toggle` \| `push_to_talk` \| `hold_or_toggle` (default) | `src-tauri/src/shortcut/mod.rs:39-58` (backend dispatch), `tauri_impl.rs:110-129` (`on_shortcut` closure; `is_pressed = event.state == ShortcutState::Pressed`, :114), `handler.rs:38-51` (edges → coordinator) |
| **CLI** (`handy --toggle-transcription` / `--toggle-post-process` / `--cancel`) | **toggle only** — "sent to running instance"; a second process forwards the flag via the single-instance plugin and exits | `src-tauri/src/cli.rs:15-25`; `lib.rs:908-921` (forward + dispatch); `transcription_coordinator.rs:677-686` (`send_external_input` — *"Always a toggle press"*, mode hard-coded `Toggle`); README:96-101 |
| **Unix signal** (`SIGUSR2` = toggle `transcribe`) | toggle only, external like the CLI | `signal_handle.rs:26-57` (SIGUSR1 is macOS-only — WebKitGTK GC conflict, #1660); README:240-246 (`pkill -USR2 -n handy`) |
| **Headless CLI** (`-f/--transcribe-file` WAV) | batch file transcription in a *separate* instance — not a mic trigger | `cli.rs:31-36`; `lib.rs:905-912` (headless skips single-instance) |
| **Tray menu** | start/stop via internal Tauri commands | `tray.rs` (internal; no external API) |

There is **no general-purpose external socket/API**: Tauri IPC is webview-internal, and
the single-instance channel only carries the three remote-control flags above. The
README sells signals/CLI precisely as the escape hatch when a WM/hotkey daemon owns
keybindings (README:238-246) — which is *exactly* the "vibekey is just the finger"
posture, though there the finger injects keys, so the hotkey path stays primary.

### Activation modes (the PTT question)

`settings.rs:171-189` defines `ShortcutActivation`:

- `Toggle` — "Press to start, press again to stop"; **release edges ignored**
  (`transcription_coordinator.rs:132-140`, `effective_hold_threshold` comment "toggle
  never defers releases").
- `PushToTalk` — "Hold to record, release to stop" (hold + release both act;
  `transcription_coordinator.rs:141-147`, :183-189 — in this mode *every* release stops).
- `HoldOrToggle` — **default**; a hold ≥ `hold_threshold_ms` (default **300 ms**,
  `settings.rs:586-588`) behaves as PTT, a tap becomes a toggle
  (`transcription_coordinator.rs:103-109, 163-189`; README:20).

The coordinator is a single pure state machine fed `InputEvent { is_pressed, mode, … }`
edges (`transcription_coordinator.rs:120-205`); `Effect::Start` / `Effect::Stop`
(`:735-757`) are what actually begin/end the recording. Pressing *and releasing* an
injected chord drives both edges identically to a physical key (§2). Post-`stop`,
transcription runs, then the transcript is inserted (Q5) — processing happens **after
release** (README:19-23; streaming is only "planned", issue #433 comment 2026-01-10).

### What the hotkey may be

- Any **modifier-combination with at least one non-modifier key**: the raw string
  (`ctrl`, `shift`, `alt`/`option`, `meta`/`command`/`cmd`/`super`/`win`/`windows` +
  letter/number/F-key/…) is parsed by `keyboard-types` into a Tauri `Shortcut`
  (`tauri_impl.rs:42-74`; accepted examples incl. `ctrl+alt+shift+space` in the test at
  :180-193). `fn` is rejected (:53-58). Side-specific modifiers (`ctrl_left+…`) are
  accepted by the handy-keys recorder but **rejected for the Tauri backend** and reset to
  default (:67-70, tests :173-177) — keep plain modifier names, which are also what
  `xdotool` spells.
- Per-binding strings live in `settings_store.json` (`bindings` map); shipped defaults
  on Linux: Dictation **`ctrl+alt+space`**, post-processed Dictation
  `ctrl+alt+shift+space`, cancel **`Escape`** (registered dynamically only while
  recording) — `settings.rs:959-1008` (cancel binding from :1001), `tauri_impl.rs:21-23`
  (cancel is registered dynamically, not at init).
- A third mode exists: `KeyboardImplementation::None` — *"Built-in global shortcuts
  disabled; use CLI flags or signals"* (`settings.rs:233-239`, `mod.rs:57-58`) — the
  fully hotkey-free arrangement (see §6 fallback).

Linux default backend is **`Tauri`** (`settings.rs:241-249`) — i.e. the X11-grab path
this ticket needs, out of the box.

## 2. Q2 — Does an *injected* (xdotool/XTEST) hotkey fire handy's listener under KDE/X11?

**Yes.** The full chain, each link sourced:

1. **Registration is a server-side `XGrabKey` on the root window.**
   `tauri-plugin-global-shortcut` 2.3.2 (`Cargo.lock:6666-6669`; declared at
   `src-tauri/Cargo.toml:105`) wraps `global-hotkey` 0.8.0 (`Cargo.lock:2323-2326`), whose
   X11 backend uses `x11rb`: `conn.grab_key(false, root, mods | m, keycode, ASYNC, ASYNC)`
   (`global-hotkey-0.8.0/src/platform_impl/x11/mod.rs:140-166`), grabbing the extra
   NumLock/CapsLock mask variants (`ignored_mods`, :101-110) so lock states can't break
   matching.
2. **Both edges are delivered, no `send_event` filtering.** The backend's event loop maps
   `Event::KeyPress` → `HotKeyState::Pressed` and `Event::KeyRelease` → `HotKeyState::Released`
   (`x11/mod.rs:255-292`); a `!state.pressed` guard plus XKB
   `DETECTABLE_AUTO_REPEAT` (:236-247) keep key auto-repeat from re-firing the press.
   `grep -rn send_event` over the crate: **no matches** — nothing anywhere down the chain
   discards synthetic-flag events. The plugin forwards every event, `Pressed` *and*
   `Released`, to handy's handler (`tpgs-2.3.2/src/lib.rs:407-423` dispatch), and handy
   branches on `event.state` (`tauri_impl.rs:114`).
3. **XTEST fake input activates passive grabs — by spec.** `xdotool key`/`keydown`/`keyup`
   use **XTEST by default** (`xdotool(1)`, Arch `extra/xdotool`: the *SENDEVENT NOTES* —
   only the `--window` mode falls back to `XSendEvent` with `send_event=True`, which is
   the mode apps ignore; the sibling audit (`research/upstream-port-audit.md` §4, R9)
   already ruled `--window` unused). The XTEST 2.2 spec (X Consortium Standard,
   x.org/releases/X11R7.7/doc/xextproto/xtest.html, §5 *XTestFakeInput*):
   > "When the simulated event(s) are processed, they cause event propagation,
   > **passive grab activation**, and so on, just as if the corresponding input device
   > action had occurred."
   An `XGrabKey` on the root *is* a passive keyboard grab → it fires.
4. **KDE/X11 adds no input chain between the Daemon and the grab.** X11 keyboard input
   lives in the X server; KWin (a reparenting/compositing WM) is just another client —
   handy's root-window grab and the Daemon's XTEST injection both terminate in the same
   server. (Contrast Wayland, which is why upstream pushes the CLI/signal path there,
   README:225-246; out of scope for this map.) The one KDE interaction: KWin's *custom
   shortcuts* are also `XGrabKey`s — if the chosen chord is already bound (e.g. user
   mapped something to `Ctrl+Alt+Space`), handy's registration gets an X `Access` error →
   `AlreadyRegistered` (`x11/mod.rs:157-166`) and handy logs "Shortcut … is already in
   use" without recording (§6 risk R2: the Panel/spec must pick an unbound chord; default
   `ctrl+alt+space` is unbound in stock Plasma, but this box's `~/.config/kglobalshortcuts`
   check belongs in the install-time checklist of ticket 0007/0008).

**Pitfall — do not switch the backend.** The alternative `handy_keys` backend
(Linux-dependable `handy-keys` 0.3.5, `Cargo.lock:2569-2577` pulls the `evdev` crate)
listens by **reading `/dev/input/event*` directly** — "Reading evdev directly needs no
X11 or Wayland connection" (`handy-keys-0.3.5/src/platform/linux/listener.rs:1-6`). XTEST
events are synthesized *inside the X server* and never appear on evdev nodes → **with
`keyboard_implementation = handy_keys`, xdotool-injected hotkeys would be invisible to
handy.** (Its "blocking" variant additionally `EVIOCGRAB`s every physical keyboard and
re-injects via uinput, :12-27 — a second opinion on Grab, not ours.) The Linux default is
`Tauri` (§1) and the fallback logic even persists a failed HandyKeys init back to Tauri
(`shortcut/mod.rs:45-54`); the Dictation Preset spec should nonetheless *pin* `tauri`
explicitly. No handy issue or doc reports its X11 hotkey ignoring injected keys — the
only synthetic-event story in its docs concerns handy's **own output** side (§5), which
uses xdotool too.

## 3. Q3 — Arch/Manjaro install path

- **AUR package exists: `handy`** (`https://aur.archlinux.org/packages/handy`), current
  **0.10.1-1**, maintained (last update 2026-11-14, well inside our supply-chain
  window — first submitted 2026-01-20). PKGBUILD: builds from the git tag (`git+$url.git#tag=v0.10.1`,
  source line; `_tag` at PKGBUILD:6 == the commit audited here), `arch=(x86_64
  aarch64)`, `license=(MIT)` — fine for our MIT port's provenance habits.
- **Build:** `bun install && bun tauri build --bundles deb` (PKGBUILD `build()`) —
  needs `bun`, `cargo`, `clang`, `cmake`, `nodejs`, `shaderc`, `vulkan-headers`,
  `spirv-headers` as makedepends (PKGBUILD:30-43); `options=('!lto')`; expect a long
  Rust+whisper.cpp compile on first `makepkg -si`.
- **Runtime deps** (PKGBUILD:12-29): `gtk3`, `webkit2gtk-4.1`, `libappindicator-gtk3`,
  `gtk-layer-shell`, `libevdev`, `alsa-lib`, `openssl`, **`openblas`**,
  `vulkan-icd-loader`, libsoup3/cairo/glib2/… — all standard pacman/AUR territory; no
  system whisper.cpp: the engine is vendored Rust (`transcribe-cpp` 0.4.2 = whisper.cpp
  GGUF/ggml, `src-tauri/Cargo.toml:83-88`).
  *AUR-comment history*: older pkgrels shipped `libtranscribe.so.0` without a
  `NEEDED libopenblas` entry (`cblas_sgemm` symbol error, AUR comments 2026-07); fixed —
  `openblas` is a hard dep now and the packager verified `ldd` resolution.
- **GPU:** Linux build features = `transcribe-cpp { dynamic-backends, vulkan }`
  (`src-tauri/Cargo.toml:187-190`): optimized CPU modules loaded per-ISA **+ a Vulkan
  ggml backend**. **No CUDA path on Linux** — maintainer confirms the Vulkan choice for
  portability and that CUDA would be "significantly faster" but isn't there yet
  (Discussion #179). User setting `Auto|Cpu|Gpu` (`settings.rs:337-342`); on weak
  iGPUs Vulkan can *lose* to CPU — see §4 (#1884).
- **Models are not shipped.** Catalog (`src-tauri/src/catalog/catalog.json`) lists
  whisper-small/medium/large-v3-turbo, Parakeet v3, Canary, etc. as HuggingFace GGUF
  repos; downloaded on demand via `hf-hub` (`Cargo.toml:97-99`). Default selected model
  is empty (`settings.rs:577-579`) → **first run: pick a model in Settings, download
  runs from the app** (Parakeet TDT v3 Q8 ≈ 1.3 GB, F16 ≈ 2.5 GB — `catalog.json` sizes).
  Pre-provisioning is possible headlessly: `handy --list-models` / `--list-devices` /
  `-f test.wav --model <id>` exercise the same registry (cli.rs:38-63).
- **User must additionally install a typing tool.** The package's own `optdepends`
  (PKGBUILD:45-49): `wtype` (Wayland), **`xdotool` (X11)**, `kwtype-git` (KDE/Wayland) —
  on our X11 box, `xdotool`, which the vibekey package already requires (map note;
  sibling audit §4). README:170-184 documents the same table plus the enigo-fallback
  caveat.
- Non-AUR options exist (upstream `.deb`/AppImage releases, README:36-44) — AUR is the
  right path here; also note the map already scopes *our* daemon packaging to a repo
  PKGBUILD, with AUR submission out of scope.

## 4. Q4 — Realistic release→text latency (evidence, not benchmarks we ran)

Pipeline after key-up: VAD trims silence → batch transcribe → post-process → paste. The
model dominates:

- **In-repo benchmark baseline** (`catalog.json`): 30 s dictation, reported as speed
  *scores* (higher = faster) on a **Ryzen 4750U**, Q8_0: CPU `whisper-tiny.en 41.2 →
  base.en 20.6 → small.en 6.3 → medium 1.9 → large-v3-turbo 1.43`, while
  **`parakeet-tdt-0.6b-v3` scores 13.7 CPU / 25.1 Vulkan** and `canary-180m-flash` 21.7
  CPU. Their grading methodology calls ≤ **4 s** end-wait "fast on CPU" and ≤ **10 s**
  "accurate-tier" (`catalog.json "methodology"`) — i.e. upstream itself plans around a
  1–10 s release→text envelope on laptop silicon.
- **Concrete logged number:** a user's v0.9.3 log line shows Parakeet-v3 on CPU doing
  "12.12 s for 64.29 s of audio (5.30× real-time)" on a Haswell-era desktop (issue
  #1884) — a ~10 s Dictation → **~2 s** to text on CPU, faster still with any GPU
  (Vulkan 25/13.7 ≈ 1.8× here; the maintainer "transcribes 10 min in under a second" on
  a 3090-class GPU, Discussion #179).
- **Lower bound / failure mode:** ancient, low-voltage CPUs can't keep up — whisper-small
  "practically unusable, +1 minute per second of audio" on a 2015 Core m3 (issue #77;
  closed, local-only design). On such hardware *any* STT choice suffers; Parakeet-CPU is
  the sane pick.
- **Press-side latency (matters for hold-style Dictation):** with on-demand mic open,
  first audio lands ~**500 ms** after the press (489–591 ms logged), clipping first
  syllables — taps shorter than init produced *zero samples* (issue #1283; later fixed
  toward 80–200 ms, PR #1329). For our Preset, turn on **`always_on_microphone`**
  (setting exists; default false, `settings.rs:591-594`) so the Daemon's keydown starts
  capture immediately.
- **Tune explicitly:** the same #1884 shows `Auto` picking a *slow* iGPU Vulkan device
  (~30% regression) — for a deterministic Preset, set accelerator **CPU** (or test
  Gpu per §6 R5). Paste itself (xdotool Shift+Insert, §5) is milliseconds.

**Bottom line for the spec:** modern-x86 + Parakeet-Q8 + CPU → realistically **0.5–2 s**
from key-up to text; Whisper medium-class quality → **several seconds**; the 4–10 s
"fast/accurate" grades are upstream's own accepted envelope.

## 5. Q5 — Where the transcript lands; interaction with the Grab and focus

- **Insertion target = whatever window holds X keyboard focus at insertion time**
  (seconds *after* key-up, once transcription finishes). On Linux the default Paste
  Method is **`Shift+Insert`** (`settings.rs:250-261` — comment: works in terminals *and*
  GUI apps, layout-independent): handy puts the text on **both clipboard and PRIMARY**,
  sends `Shift+Insert` via the typing tool, then restores both selections
  (README:168). The typing tool on X11 is **xdotool** — handy literally spawns it:
  "X11: prefer xdotool" for key combos (`clipboard.rs:186-188`) and for `Direct` typing
  (`clipboard.rs:232-234, 272-275`); `TypingTool::{Auto,Wtype,Kwtype,Dotool,Ydotool,Xdotool}`
  configurable (`settings.rs:325-333`, Settings → Typing Tool). `CtrlV`/`Ctrl+Shift+V`/
  `None`/`ExternalScript` exist too (`PasteMethod`, `settings.rs:164-171`).
- **No conflict with the Daemon's Grab.** The Grab is `EVIOCGRAB` on the *Dongle's* evdev
  nodes only (never the virtual keyboard; sibling audit §2); handy's xdotool output is
  XTEST inside the X server — a different universe from the kernel input core the Grab
  filters. Conversely the Daemon's injected chord is unaffected by handy reading/writing
  the clipboard. Focus is also untouched by the injected hotkey (XTEST key events never
  move X focus), so **the focused app at Voice-Control press is the app that receives
  the transcript** — the "type into the app you're in" behaviour users expect.
- **The overlay is the one focus hazard, and it's off by default.** Upstream: "The
  recording overlay is disabled by default on Linux … When the overlay is visible it can
  steal focus, which prevents Handy from pasting back into the application that
  triggered transcription" (README:205, and the X11-specific "Overlay & Pasting Issues"
  note README:259-265); `default_overlay_style()` returns `None` on Linux
  (`settings.rs:629-633`). The Dictation Preset spec should keep `overlay_style: none`
  and offer **audio feedback** instead (README:205, `SoundTheme`/`audio_feedback`
  settings exist) so the user knows Dictation is live without a window that could eat
  the paste.
- **Panel/daemon note:** nothing in this path needs the Panel; handy keeps its own
  tray + settings window. The Daemon's Dictation Preset is exactly the upstream
  `command`/`release_command` pair shape (`voxtype record start/stop` in the audit's
  table at `vibekeyd:476` → now a `keydown`/`keyup` chord pair).

## 6. Conclusions, recommended mechanism, risks

### Recommended mechanism (primary)

**Hold-pair injection against a grabbed chord:**

```
Preset  "Dictation"          command:         xdotool keydown ctrl+alt+space
                                             release_command: xdotool keyup   ctrl+alt+space
handy:  keyboard_implementation = tauri      (Linux default; do not change)
        shortcut_activation      = push_to_talk
        binding "transcribe"     = ctrl+alt+space (verify not grabbed by KWin)
        overlay_style            = none       (Linux default)
        always_on_microphone     = true
        accelerator              = cpu        (unless per-box Gpu test wins)
        paste_method             = shift_insert (Linux default)
```

Why not the alternatives:

- **Double `xdotool key` (single shot) per edge** — a one-shot `key ctrl+alt+space` is a
  press *immediately followed by* its release; in `push_to_talk` the release would stop
  recording ~0 s in; in `hold_or_toggle` it reads as a *tap* → toggle. Two `key`
  invocations to bracket the utterance work only under `toggle` (press=start,
  press=stop) — viable but semantically indirect and it throws away the mode that
  matches the Voice Control's physics. **Rejected as primary.**
- **`toggle` + two one-shot `key` presses** — works, keeps a human tap affordance on the
  physical keyboard too; second choice if a user wants handy's `hold_or_toggle` default
  left untouched (the Daemon's hold >300 ms behaves like PTT there as well — that's the
  *forgiving middle*, and honestly acceptable; `push_to_talk` is chosen for explicitness:
  "every release stops", `transcription_coordinator.rs:183-189`).
- **CLI/signal fallback (`handy --toggle-transcription` × 2, or `pkill -USR2 -n handy`)**
  — fully evidenced (§1), and combines with `KeyboardImplementation::None` for a box
  where zero key-chords are wanted; external inputs "always a toggle press", parity is
  the Daemon's job (it knows hold state, trivial), and they're **exempt from debounce**
  (`transcription_coordinator.rs:677-678` — "always exempt from debounce"). Costs one process launch per edge to
  reach the single-instance forwarder — unmeasured; flag for the prototype. **Keep as
  documented fallback**, not primary.
- **`--transcribe-file` piping** — the Daemon would have to own the mic and a 16 kHz WAV
  capture and the app-less path skips VAD/download niceties (cli.rs:31-36); it's a batch
  tool, not the live Dictation arrangement. **Rejected.**

### Residual risks (for the Preset spec, ticket 0007, and packaging ticket 0008)

| # | Risk | Severity | Mitigation (evidence) |
|---|---|---|---|
| R1 | User flips keyboard implementation to HandyKeys → injected events invisible (evdev-only listener) | 🔴 if it happens | Pin `tauri` in the Preset's documented handy settings; handy itself falls back to Tauri on init failure (`mod.rs:45-54`) |
| R2 | Chord already `XGrabKey`'d by KWin/custom shortcut → handy registers nothing | 🟡 | Install-time checklist: try default, else pick a free chord; failure is visible in handy logs ("already in use", `tauri_impl.rs:100-105`) |
| R3 | Mic-open delay clips first syllable on fast taps | 🟡 → 🟢 | `always_on_microphone=true` (issue #1283; default false `settings.rs:591-594`) |
| R4 | Overlay enabled (e.g. imported settings) steals paste focus | 🟡 | Keep `overlay_style=none` (Linux default, `settings.rs:629-633`; README:205) |
| R5 | `Auto` accelerator picks slow Vulkan iGPU; Whisper-model latency on weak CPUs | 🟡 | Set `accelerator=cpu`; ship Parakeet-v3 as the recommended model (#1884; catalog methodology) |
| R6 | AUR build is long & maintainer-fresh (0.10.1-1, 2026-11-14) | 🟢 | Pin pkgver in ticket 0008; `makepkg` from source respects the 7-day gate as a new build |
| R7 | Transcript lands in whatever window is focused ~1–2 s after release | 🟢 | Same semantics as a human pressing the hotkey; document |

### If handy weren't suitable…

Moot — it is suitable, and it's the user's stated choice (map: "dictation = handy stays
the STT app"). Noted for completeness only: the ticket-1 audit's upstream pairing was
`voxtype`, which shares the CLI-start/stop shape; no alternative was otherwise
investigated per ticket scope.

---

## Sources

Primary (audited commits on disk under `/tmp/opencode/`):

- `cjpais/Handy` @ `v0.10.1` — README.md (:19-23, :96-107, :131-147, :168-184, :205,
  :225-246, :259-265); `src-tauri/Cargo.toml:83-105, 181-190`; `Cargo.lock:2323, 2569,
  6666`; `src-tauri/src/cli.rs`; `signal_handle.rs`; `lib.rs:905-921`;
  `settings.rs:164-189, 233-261, 325-342, 577-594, 629-633, 959-1008`;
  `shortcut/{mod,tauri_impl,handler}.rs`; `transcription_coordinator.rs:103-205,
  655-760`; `clipboard.rs:186-275`; `catalog/catalog.json` (methodology, results).
- AUR `handy` git repo (`aur.archlinux.org/handy.git` @ `e730233`) — PKGBUILD; package
  page + comments (openblas history, kwtype optdep) `aur.archlinux.org/packages/handy`.
- `global-hotkey` 0.8.0 — `src/platform_impl/x11/mod.rs:101-166, 236-292`;
  `tauri-plugin-global-shortcut` 2.3.2 — `src/lib.rs:24, 269-273, 407-423`;
  `handy-keys` 0.3.5 — `src/platform/linux/listener.rs:1-27`; crates.io tarballs.
- XTEST Extension Protocol v2.2, X Consortium Standard —
  `x.org/releases/X11R7.7/doc/xextproto/xtest.html` §5 (passive grab activation).
- `xdotool(1)` (Arch `extra/xdotool`) — `key`/`keydown`/`keyup`, SENDEVENT NOTES (XTEST
  default; `--window` = XSendEvent caveat), as also cited in
  `research/upstream-port-audit.md` §4.

GitHub issues/discussions on `cjpais/Handy` (issue reports as user-experience evidence):
#77 (CPU floor), #433 (post-release batch; streaming planned), #1283 (+ PR #1329)
(mic-open ~500 ms → 80–200 ms, `always_on_microphone`), #1884 (Vulkan-Auto regression,
RTF logs), #197 & Discussion #179 (Vulkan-not-CUDA rationale, GPU speed data).
