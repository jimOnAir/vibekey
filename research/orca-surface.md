# Orca CLI surface — findings for the *Orca next-worktree* stretch Preset

Ticket: [0004-orca-surface](../.wayfinder/tickets/0004-orca-surface.md) ·
Researched: 2026-11-15 · On this machine (Manjaro KDE, **X11**), against
**Orca 1.4.257** desktop app running (runtime `ready`, `desktopWindowStatus: "available"`).

All claims are from primary sources, in this order of weight:

1. **Live probes** of the `orca` CLI on this machine (`--help` of every relevant
   command, `--json` runs, and behaviour tests listed with their exact commands).
2. **`orca agent-context --json`** — the CLI's own machine-readable command
   registry (`schemaVersion: 1`, **327 commands**), the authoritative list of
   what exists.
3. The **version-matched guide** `orca skills get orca-cli`, bundled with this
   build (plus the `orca-cli` skill stub at `~/.agents/skills/orca-cli/SKILL.md`).

Live tests against the running desktop app were idempotent or restored the UI
state afterwards (activating the workspace hosting this research, closing each
probe with `wmctrl -a` back onto the Orca X11 window).

## Executable resolution (matters for the Daemon)

The skill stub is explicit: on Linux outside an Orca terminal, bare `orca` may
resolve to the **GNOME Orca screen reader** (`/usr/bin/orca`) — use `orca-ide`.
On this machine the collision is pre-resolved by a shim:

- `which orca` → `~/.config/orca/linux-orca-cli-shim/orca`, a two-line bash
  shim: `exec '/opt/stably-orca/resources/bin/orca-ide' "$@"`.
- `orca-ide` itself is **not** on `PATH` here (`which orca-ide` → not found);
  the real binary is `/opt/stably-orca/resources/bin/orca-ide` (node launcher
  for `/opt/stably-orca/resources/app.asar.unpacked/out/cli/index.js`).

**Consequence for the Daemon**: invoke the absolute path
`/opt/stably-orca/resources/bin/orca-ide` (or the shim) — never bare `orca`,
which is PATH-order luck. If the install moves (packaging), resolve the path
from `~/.config/orca/linux-orca-cli-shim/orca` or a config setting.

## Q1 — Next/previous worktree activation, CLI-only?

### Premises

- **P1**: worktrees are enumerable with stable machine-readable identity.
- **P2**: there is a command that shows a given worktree in the app.
- **P3**: neither a next/prev step nor a "what is on screen" query exists, so
  the cycle position must live in the Daemon.
- **P4**: activation changes the app's **content**, not the OS window — raising
  the window is an X11 step outside Orca.

### Evidence

- **P1** — `orca worktree list --json` returned 29 rows (exit 0), each with
  `id` (`<repoId>::<path>`), `identity.key` (`wt2:local:<uuid>`), `repoId`,
  `path`, `branch`, `displayName`, `comment`, `isArchived`, `isUnread`,
  `isPinned`, `sortOrder`, `lastActivityAt`, `workspaceStatus`, parent/child
  lineage, and all linked-issue fields. `orca worktree ps --json` adds a
  compact orchestration view (per-worktree `live:<n>` terminal counts, agents,
  a copy-paste `address:` line; includes folder workspaces, which `worktree
  list` omits). `orca worktree show --worktree <selector> --json` for one row.
  Selectors: `id:`, `identity:`, `name:`, `branch:`, `issue:`, `path:`,
  `folder:` (`folder:` only where accepted), `active`/`current`.
- **P2** — `orca worktree activate --worktree <selector> --json`. Live, twice:
  activating `identity:wt2:local:23a07744-…` (vibekey) and
  `identity:wt2:local:09238b8e-…` (gpu-monitor) each returned
  `{"activated": true, "worktreeId": "…", "sleepingAgentWake": "not-applicable"}`.
  Help text: "Open a worktree on its host, waking a sleeping recipe VM behind
  it"; note: "Folder workspaces cannot be activated from the CLI yet; open
  them from the Orca sidebar."
- **P3** — `orca worktree activate --help`, `worktree list --help`, and the
  full 327-command `agent-context` registry contain **no** next/previous/cycle
  command and no command that reports the currently displayed workspace.
  `active`/`current` selectors resolve from the **shell's cwd**, not UI state
  (guide: "the Orca workspace enclosing the shell cwd"; `worktree current`
  help: "Resolves the current shell directory to a path: selector"). Proof:
  `orca worktree current --json` run from
  `…/vibekey-research/orca-surface` returned the enclosing *repo* row
  `/home/dmitry/orca/projects/vibekey` — cwd-based, useless to a Daemon with
  no relevant cwd.
- **P3 (order)** — the `worktree list` row order is not defined as sidebar
  order and is not sorted by `sortOrder` or `lastActivityAt` (observed
  `sortOrder` in file order: 1794573744896, 1794396513958, …, 1794745375315);
  `ps` returns a different order again. Both carry `truncated`/`--limit`
  paging. So a deterministic cycle needs the Daemon to define its own order
  (e.g. sort by the `sortOrder` integer, or by `path`) and to skip
  `isArchived` rows.
- **P4** — X11 probe with `wmctrl`/`xprop` (both this machine's, KDE):
  - Orca shows as **one** X11 window: `0x08400004`, `_NET_WM_PID 9470`
    (= the `orca-ide` main process), title plain `"Orca"`.
  - With focus on another window (`0x00800003`, "GPU Monitor"),
    `orca worktree activate --worktree identity:wt2:local:23a07744-…` still
    returned `activated: true`, but `xprop -root _NET_ACTIVE_WINDOW` stayed
    `0x800003`. The same held for `orca terminal switch` (see Q2): the app
    switched what it shows without touching the OS window.
  - `wmctrl -i -a 0x08400004` then did raise and focus the Orca window
    (`_NET_ACTIVE_WINDOW` → `0x08400004`).
  - `xdotool` is **not installed** on this machine yet (the port's settled
    choice is `wtype` → `xdotool`); `wmctrl` is.

### Conclusions

1. **Yes, with one added step.** "Next Orca worktree" = the Daemon keeps the
   cycle cursor and the candidate order, calls `worktree list --json` to
   (re)build candidates, then `worktree activate --worktree identity:<key>`.
   No keystroke hacks into Orca are needed to *switch* workspaces.
2. **Focus the window is not Orca's job** (on this build): append an X11 raise
   (`wmctrl -i -a <id>`, window found by `_NET_WM_PID` of the `orca-ide` main
   process or title `"Orca"`). Since Orca's window is single and plain-titled,
   worktree→window mapping is trivial: all worktrees live in that one window.
3. **Gap**: nothing tells the Daemon (or anyone) which workspace the user is
   looking at, so the cursor can drift from the user's manual sidebar clicks.
   Acceptable for a "next" cycle (it's relative to the Daemon's cursor), wrong
   for "bring me back where I was".

## Q2 — Focus a specific terminal; run/read/wait inside it?

### Premises

- **P5**: terminals are enumerable and addressable by a runtime-issued handle.
- **P6**: one command focuses a terminal tab; the same receipt confirms it.
- **P7**: send/read/wait form a complete drive loop.

### Evidence

- **P5** — `orca terminal list --json` (live, exit 0): rows carry `handle`
  (`term_<uuid>`), `ptyId` (`<repoId>::<path>@@<hash>` — durable identity),
  `incarnationId`, `worktreeId`, `worktreePath`, `branch`, `tabId`, `leafId`,
  `title`, `connected`, `writable`, `lastOutputAt`, `preview` (screen snippet),
  `executionHostId`, and `agentIdentity` when an agent CLI is running (e.g.
  `opencode2`). `--include-visual-layouts` adds tab/pane topology; JSON omits
  it by default. `--worktree <selector>` scopes to a worktree.
  Guides' rules (version-matched guide): *"never match on* `title` *(the
  running program's own title, which agents repaint constantly)"* — confirmed
  live: the hosting terminal's title was `"OC | Research: upstream port
  audit"`, an agent-chosen name; `agentIdentity` is only the agent *type*, not
  a Session identity. To re-find a specific agent's terminal, join
  `worktree ps --json` `agents[].paneKey` (`<tabId>:<leafId>`) to `terminal
  list` rows.
- **P6** — `orca terminal switch --terminal <handle> --json` (alias
  `terminal focus`; `--help` of the alias prints the same page). Live:
  returned `{"focus": {"handle": "term_00715edc-…", "tabId": "b753db12-…",
  "worktreeId": "c7577d4c-…::/home/dmitry/orca/projects/vibekey",
  "navigated": true}}`. It brings the tab to the foreground of its workspace's
  view; it does **not** raise the OS window (X11 probe in P4). Omitting
  `--terminal` targets "the active terminal in the current worktree" — cwd
  scoped, so the Daemon must always pass an explicit handle.
- **P7** — help + guide, all machine-readable with `--json`:
  - `terminal send --terminal <h> --text … [--enter] [--interrupt]` — PTY
    write; without `--enter` bytes go verbatim; an agent prompt with
    `--enter` is bracketed-pasted. Receipt separates `input_accepted` from
    `turn_started` ("`accepted: true` proves input acceptance, not a started
    turn"); `--wait-submit <s>` observes submission without resending;
    `--retry-request <id>` replays an ambiguous send. A text+Enter agent
    prompt is refused with `agent_prompt_blocked` while the agent shows a
    permission menu.
  - `terminal read --terminal <h> [--screen] [--cursor <n>] [--limit <n>]` —
    default returns accumulated output with escapes stripped (repainting TUIs
    read as stacked fragments — confirmed in live previews); `--screen`
    returns the rendered frame; cursor paging via `nextCursor`/`oldestCursor`.
  - `terminal wait --terminal <h> --for exit|tui-idle --timeout-ms <ms>` —
    designed for agent CLIs ("always pass `--timeout-ms`").
  - `terminal show --terminal <h> --json` — metadata + wait verdict; `agentWait`
    field observed `null` outside `--agent-wait` use.
- **Handle volatility** — guide: handles are runtime-scoped; after an Orca
  restart or a `terminal_handle_stale` error, re-list and use the replacement.
  `ptyId`/`tabId`/`leafId` are the durable parts.

### Conclusions

4. **Yes, fully.** Focus: `terminal list` → `terminal switch` (`navigated:
   true` receipt). Drive: `read` → `send` → `wait --for tui-idle` → `read
   --cursor`. This is a supported agent workflow, not a side effect.
5. The Daemon must treat handles as ephemeral (fresh `terminal list` per
   Preset fire is ~cheap) and must never identify terminals by `title`.

## Q3 — Stable machine-readable enumeration incl. window identity?

- Every command takes `--json`; the envelope is uniform:
  `{id, ok, result…, _meta.runtimeId}`, structured errors with `code` +
  `nextSteps` (observed live from a deliberate `app_not_found`).
- `orca agent-context --json` is a **command schema for agents** — "pure local
  read of the command registry — works without a running Orca app" (help).
  327 commands with `command/path/aliases/flags/positionalArgs/examples/notes`.
  A Daemon can codegen/validate against this.
- `orca status --json` → app running + pid, runtime `reachable`, `runtimeId`,
  `appVersion`, and a long `capabilities` list (`runtime.status.compat.v1`,
  `terminal.multiplex.v1`, …) — behavioural versioning of the runtime.
- **Window identity is not in Orca's JSON.** `worktree *` rows carry no window
  id; `terminal *` rows carry no shell PID (the PTYs live in the terminal
  daemon, see Q4). X11 must supply it: Orca = a single top-level X11 window
  whose `_NET_WM_PID` matches the `orca-ide` main process (`status --json`
  `app.pid` 9470 == `wmctrl -lp` pid — confirmed). `orca computer
  list-apps/list-windows` exists (Orca's own accessibility/desktop-control
  layer, observed working against native apps on this X11 session), but it is
  for driving *other* apps and refused `--app pid:9470` (`app_not_found`); it
  is not the route to raise Orca's own window.

### Conclusion

6. Enumeration: solid and supported. The only join the preset needs is
   Orca-JSON (`worktreeId`/`identity.key`) ↔ one X11 window (via `app.pid`),
   which is trivially stable on this single-window build.

## Q4 — Any socket/API beyond the CLI?

### Evidence (all observed on this machine)

- The desktop app embeds the **runtime server** and listens on
  `127.0.0.1:6768` (the `orca serve` default port; `ss -tlnp` attributes it to
  `orca-ide` pid 9470) plus an ephemeral `127.0.0.1:34487`. `orca serve --help`
  documents `--port/--bind`, `--pairing-address`, pairing codes
  (`orca://pair?…`), LAN/Tailscale acceptance rules, `--grant-desktop-control`.
  The CLI is just a client of that runtime; env overrides `ORCA_PAIRING_CODE`
  / `ORCA_ENVIRONMENT` point any command at another Orca host.
- A separate **terminal daemon** ("orcad") owns the PTYs so they survive app
  restarts: `daemon-entry.js --socket ~/.config/orca/daemon/daemon-v56.sock
  --token …/daemon-v56.token --pid-record …/daemon-v56.pid` (process args
  observed; sockets are `srw-------`, per-user, version-numbered; pid file
  names pid 10569, boot id, cgroup scope). `orca terminal-daemon
  status --json` → `{"daemon": {"verdict": "live", "pid": 10569}}`.
- A **plugin system** (`orca plugin …`, dev load/reload, worker handlers,
  panels, events) is the sanctioned extension surface *inside* Orca.
- No documented raw HTTP/JSON API for third-party apps; the wire protocol is
  internal, versioned only by capability flags, and pairs/keys are managed.
  Skill stub: `runtime_access_denied` means the *caller's sandbox* blocked the
  connection — the CLI assumes a same-user local socket/port.

### Conclusions

7. Orca is client/server internally, but **the CLI is the supported external
   contract** (uniform JSON + `agent-context` schema). The preset should not
   speak the 6768 protocol or the daemon socket directly — the CLI already
   covers every operation the stretch Preset needs, and is what versioning and
   `--retry-*` idempotency protections apply to.
8. Operational preconditions for the Daemon: Orca must be running
   (`orca open --json` "Launch Orca and wait for the runtime to be reachable"
   is the sanctioned cold-start; `orca status --json` the liveness check).
   The Preset's first call should be a status/list call that doubles as a
   precondition test.

## Preset-operation table — *Orca next-worktree* stretch Preset

Desired operation | Command(s) that achieve it | Gap / risk
--- | --- | ---
Build candidate list | `orca worktree list --limit 10000 --json` (or `worktree ps --json` incl. folders) | order not defined by Orca — Daemon imposes one (`sortOrder` is internal epoch-ms; stability across versions unproven); filter `isArchived`; respect `truncated`
Which worktree is on screen | — **none** | `active`/`current` = shell cwd, not UI; Daemon keeps its own cursor; drifts when the user clicks the sidebar
Show next worktree (cycle) | `orca worktree activate --worktree identity:<key> --json` → `activated: true` | folder workspaces refused from CLI (sidebar only); recipe-VM wake can make it slow; does **not** raise the OS window
Raise/focus Orca's window | X11, not Orca: find window by `_NET_WM_PID == status.app.pid` (`wmctrl -lp`), then `wmctrl -i -a <id>` | verified on this KDE/X11; KWin focus-stealing prevention from a hotkey context untested; `xdotool` not yet installed (planned `wtype`→`xdotool`); single-window assumption holds on 1.4.257
Focus a terminal tab in that worktree | `orca terminal list --worktree identity:<key> --json` → `orca terminal switch --terminal <handle> --json` → `navigated: true` | handles runtime-scoped — re-list per fire; never match `title`; pick the agent's row by joining `ps` `paneKey` (`tabId:leafId`), not `agentIdentity`
Run a command in it | `orca terminal send --terminal <h> --text "…" --enter --json` (+`--wait-submit 10`) | `accepted` ≠ turn started; `agent_prompt_blocked` while a permission menu is up (send text and Enter separately)
Read output | `orca terminal read --terminal <h> [--screen] [--cursor <nextCursor>] --json` | default strips escapes (TUIs look garbled) — use `--screen` for what's visible; page with cursors
Wait until the agent is idle | `orca terminal wait --terminal <h> --for tui-idle --timeout-ms <ms> --json` | needs a recognized agent TUI; always pass a timeout
Liveness / cold start | `orca status --json`; `orca open --json` | Orca not running ⇒ every other command fails; `open` launches the app — a deliberate Daemon policy choice
Schema discovery | `orca agent-context --json` (327 commands, works offline) | none
Socket/API bypass | (runtime at `127.0.0.1:6768`; daemon socket `~/.config/orca/daemon/daemon-vNN.sock` + token) | **don't** — internal protocol, capability-flag versioning only; the CLI is the supported surface

## Bottom line

The stretch Preset is implementable **without keystroke hacks into Orca**:
`worktree list --json` → (Daemon-owned cycle) → `worktree activate` →
`terminal list --json` + `terminal switch` cover the whole interaction, each
with `--json` receipts. Exactly one step falls outside Orca and lands in the
port's already-chosen X11 toolbox (`xdotool`/`wmctrl`): raising Orca's single
desktop X11 window, findable by the `orca-ide` PID. The two real gaps for
*Agent-preset design* (ticket 6): no "currently displayed workspace" query
(the Daemon must own cycle state and tolerate drift), and terminal handles
that must be re-listed rather than cached.
