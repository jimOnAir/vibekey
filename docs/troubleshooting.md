# Troubleshooting

*[← README](../README.md)*

Ordered by "this is what actually happens". Each entry: symptom → cause → fix.

## `No permission to read the Dongle`

Red banner in the Panel, or `access: "denied"` in state.json. The nodes are
`root:vibekey 0660` now, but your **Daemon process** predates the group grant:
user services inherit groups from `user@1000.service`, and that manager is not
recreated by a plain logout whenever lingering or another session (agent, SSH,
a second seat) keeps it alive — `daemon-reexec` does **not** refresh its
credentials either (verified in the field).

```bash
getent group vibekey                       # dmitry listed? then it's the manager
systemctl --user --no-pager status vibekeyd
reboot                                     # the honest reset
```

## Presses reach the Panel, nothing happens

**Preview.** While the Panel *window* is open, the Daemon reports events
(`WOULD RUN …`) and runs nothing by design. Close the window or uncheck
Preview. (Tray-only is fine.)

## `xdotool … exit 1` in the status line / notifications

The Daemon's X authorisation was missing or stale — typically the service
started before Plasma imported `DISPLAY`/`XAUTHORITY` into the user manager
(fresh-boot race). From the build with the **X-env self-heal** this resolves
itself within seconds (the Daemon copies the live values from
`plasmashell`/`kwin_x11`, and re-syncs whenever an injected key fails); on
older installs:

```bash
systemctl --user restart vibekeyd     # Plasma's env is in place by now
```

Check with `tr '\0' '\n' < /proc/$(pgrep -f vibekeyd | head -1)/environ | grep -E '^(DISPLAY|XAUTHORITY)'`.

## Mic key: no recording, no text

Work the chain:

0. **Tray mic badge?** An orange mic-with-slash on the tray icon (or the ✗ line
   atop the Panel's handy card) means Dictation's mic is unusable right now:
   Dongle unplugged, keypad **asleep/off** (press any AU05 key — it answers and
   the badge clears within a second), or no/muted system input. The one thing
   no software can see: a hardware mute on some *other* wired mic — audio
   stack reports it live and deaf alike. If the badge is quiet yet nothing
   transcribes, record a two-second proof (`arecord -d 2 t.wav`) and play it
   back before blaming the chain below.
1. **Is handy running?** vibekey never starts it — `pgrep -x handy`, and check
   the tray (Plasma hides icons by default — the `^` overflow).
2. **Right backend?** handy must keep `keyboard_implementation = tauri`.
   The `handy_keys` backend reads `/dev/input` directly, where injected keys
   **do not exist** — the classic silent failure.
3. **Chord match?** Panel → handy card shows drift in red; **Fix handy** or
   change it in handy, your call (one-way, only on click).
4. **Activation mode?** `push_to talk` is the spec pin; `hold_or_toggle`
   (default) also works for holds ≥ 300 ms.
5. First syllable missing → **always-on microphone** ON (mic warm-up is
   ~500 ms otherwise).
6. Slow but working is normal: ~0.5–2 s (fast model, GPU/CPU) to several
   seconds on accurate tiers.

## The ring lights up and blinks while the keypad was idle

A host-driven **rhythm** pattern (`heartbeat`, `alarm`, …) keeps writing ring
steps to the keypad — but a keypad in standby never ACKs them. Before the
sleep breaker this stampeded one timed-out write per 1.3 s forever, which
looks like the keyboard slowly flickering and fills `journalctl --user -u
vibekeyd` with `lighting write timed out: rhythm`. Now three unanswered
frames pause the rhythm; it resumes on the next ACK or the moment you wake
the keypad with a key. If you are on an older package: `systemctl --user
restart vibekeyd` stops it until the next sleep — updating fixes it for good.

## The ring never lights up

Two gates:

- **Device lighting mode** — if the unit sits in *Always Off/On* (set from
  Ulanzi Studio or factory), per-light writes are invisible and vibekeyd goes
  idle by design. The Panel's Lighting section offers **Manage lights** — one
  consented click, mode becomes *Working*.
- **The keypad sleeps** after 5 idle minutes (it disconnects from the Dongle;
  writes drop until any key wakes it). Failure blinks deliberately only fire
  right after your press, so they can't be missed; a rhythm step into sleep is
  simply lost until the next cycle.

## My Voice key seems to send `Super+H`

Some firmware variants do exactly that (and others send the knob press as
`Backspace`, turns as `Right/Backspace` keys instead of wheel ticks). Both
variants are handled — that's what the Alias machinery and the
press-vs-turn heuristic are for. To see what *your* unit actually sends:
`vibekeyd --probe` (or the Panel status line with Preview on) — every raw id
is narrated.

## Cursor "drifts" / Orca cycle order surprises you

By design: OpenCode and Orca expose no "what is the user looking at" query,
so the Daemon owns its Ring/Cursor positions and can't observe your manual
switches. A step catches up to the current list; deleted ids skip with a
notification.

## My `--standalone` TUI is invisible to ✓/✕

Expected v1 gap: standalone instances run a private, unregistered server —
the Daemon can neither list nor interrupt them. Use the shared service
(the default `opencode` startup) for agent Controls.

## `orca` does nothing / opens a screen reader

vibekeyd never calls bare `orca` (that name belongs to GNOME's screen reader);
it resolves the shim in `~/.config/orca/linux-orca-cli-shim/orca`, the
installed `/opt/stably-orca/...` path, or your `orca_cli` override, in that
order. If Orca moved, set `orca_cli`.

## I miss knob-scroll / knob-volume

Knob modes were retired 2026-11-16 — the dial is the Session Ring now. The
capability moved to the buttons: assign the Media Presets (volume up/down,
play/pause…) or any key combo to a Control in the Panel; the knob's native
wheel events stay Grabbed, so they never leak into your apps.

## `Quit` in the tray doesn't stick

Quit stops the Panel process and nothing else — by design the **Daemon** keeps
running (your Controls stay live). If the tray icon reappears a second later,
something is *supervising* the Panel with a restart-always policy: the shipped
setup (KDE autostart) does not, but a transient dev unit started with
`systemd-run --property=Restart=always` does — relaunch it with
`Restart=on-failure` instead. Bring the Panel back any time from the
applications menu (**vibekey Panel**).

## Still stuck?

The two files that explain everything: `$XDG_RUNTIME_DIR/vibekey/state.json`
(what the Daemon believes) and `journalctl --user -u vibekeyd -b` (what
happened). Issues welcome on the tracker — attach both, plus
`vibekeyd --probe` output for anything device-protocol shaped.
