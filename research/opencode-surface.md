# OpenCode automation surface (wayfinder ticket 0003)

Question: what can drive OpenCode Sessions (agent) programmatically from the
desktop today, for the three agent Presets: **next/previous Session**, **focus
the terminal running a Session**, **interrupt the in-flight run**.

Method: probed the live install on this machine (`opencode v2.2.7`,
`/usr/bin/opencode`), its HTTP API, its on-disk state, and the Orca CLI;
cross-checked against the source at tag `v2.2.7` (`github.com/anomalyco/opencode`)
and opencode.ai docs. Every claim below is cited to one of: **[live]**
observed against the running service on this machine, **[src]** source at
v2.2.7, **[bin]** string extracted from the installed 247 MB binary,
**[docs]** official documentation, **[orca]** observed via the installed
`orca` CLI. Domain terms follow `GLOSSARY.md`.

> Version warning: opencode.ai/docs/server/ documents the **V1** API
> (`/session/:id/abort`, `/tui/append-prompt`, …). It carries a banner saying
> V2 docs live under `/docs/llms.txt`. This machine runs **V2.2.7** with a
> different `/api/*` surface. Design the Daemon against V2 and treat the V1
> routes as non-existent. **[docs][live]**

## Premises

- P1. The keypad Assignments must act from outside the OpenCode process, with
  no UI of OpenCode's own to script (desktop tool, no plugin slot assumed).
- P2. Sessions of interest run in TUIs, several at once; many of them inside
  Orca worktree tabs (sibling ticket context: `orca terminal list --json` rows
  carry `agentIdentity` and worktree identity).
- P3. The injection toolbox per the completed sibling ticket is xdotool +
  wmctrl on KDE/X11 (xdotool is not yet installed on this machine — it would
  be a dependency of the port, **[live]** `which xdotool` → not found).

## 1. `opencode serve` / HTTP API

### 1.1 Architecture on this machine (v2.2.7)

- `opencode serve` starts a headless HTTP server (flags: `--hostname`,
  `--port`, `--cors`, `--service`, `--stdio`). **[live]** `opencode serve --help`
- A plain `opencode` TUI attaches to a shared **background service**
  (`opencode serve --service`), not its own server. Only `opencode
  --standalone` spawns a private one. **[live]** process tree: two TUIs
  (`--session ses_…`) share the service pid; the standalone TUI spawned
  `serve --stdio --port 0` as a child.
- The TUI itself is a client of that server (SolidJS/opentui TypeScript,
  `packages/tui`). **[src][live]**

### 1.2 Discovery of the live instance

- **`~/.local/state/opencode/service.json`** (`${XDG_STATE_HOME:-~/.local/state}/opencode/service.json`)
  is a one-line JSON registry: `{"id","version","url","pid","password"}`.
  Observed: `{"url":"http://127.0.0.1:49374","pid":19522,"password":"…"}`.
  **[live]** The writer is in the binary: `XDG_STATE_HOME??…".local","state","opencode","service.json"`,
  written under `service.lock`; multi-runtime variants `service-<name>.json`. **[bin]**
- CLI form: `opencode service status` prints the URL; `opencode service
  start|stop|restart` manage it. **[live]**
- Built-in convenience: `opencode api <operationId|method path>` "Make a
  request to the running server" — resolves discovery + auth itself, so the
  Daemon can shell out instead of speaking HTTP. **[live]** `opencode api --help`
- The private server of a `--standalone` TUI is **not** registered anywhere
  and answered `401 UnauthorizedError` on `/api/info` without credentials —
  treat standalone instances as API-opaque. **[live]** (port found via `ss -tlnp`, still 401)

### 1.3 Auth

- The background service requires **HTTP Basic auth**; password is the
  generated one in `service.json`. No-auth request → `401 {"_tag":"UnauthorizedError"}`;
  `Authorization: Basic opencode:<password>` → 200. **[live]**
- V1 docs describe `OPENCODE_SERVER_PASSWORD` / `OPENCODE_SERVER_USERNAME`
  (username defaults to `opencode`); V2's service generates and stores the
  password in `service.json` instead. **[docs][live]** Reading `service.json`
  as the same user is therefore sufficient for a local Daemon.
- A pairing flow also exists for apps: `POST /api/pair` → one-time link,
  `GET /auth/connect/{code}`; CLI `opencode pair` prints it. **[live]** spec + `--help`

### 1.4 The session operations we need (all **[live]** verified against v2.2.7, schema per served `/openapi.json`)

| Need | Route | operationId | Verified behaviour |
|---|---|---|---|
| List Sessions | `GET /api/session` | `session.list` | 200; query params `limit`, `order=asc\|desc`, `search`, `parentID` (pass `null` → root Sessions only), `archived`, `directory`; returns `data[]` + `cursor`. Rows carry `id` (`ses_…`), `title`, `agent`, `model`, `cost`, `tokens`, `time.{created,updated,busy,idle,viewed}`, `location.directory`. Covers **all projects**, one call. |
| Which are running | `GET /api/session/active` | `session.active` | `{"data":{"ses_X":{"type":"running"}}}` — confirmed showing both my parent Session and a probe while busy. |
| Interrupt | `POST /api/session/{id}/interrupt` | `session.interrupt` | `{"interrupted":true}` while running; `{"interrupted":false}` when idle (idempotent). Query `resume=true\|false`. Emits durable event `session.execution.interrupted` (seen on SSE). |
| Send input | `POST /api/session/{id}/prompt` | `session.prompt` | body `{text, files?, agents?, skills?, delivery?: "steer"\|"queue", resume?}`; returns the queued inbox User message. |
| Events | `GET /api/event?types=…` | `event.subscribe` | SSE stream; observed `session.execution.started`, `session.execution.interrupted`; type list includes `session.idle`, `permission.asked`, `session.status` updates — the Daemon can track "is a run in flight" without polling. |
| Create/delete probe | `POST /api/session`, `DELETE /api/session/{id}` | — | Used for the live probe; delete → 204. |

Also present and relevant: `session.view` (marks viewed, body `{idle}`),
`session.background` (unblocks blocking tools, not an interrupt),
`session.command`, `pty.*` + persistent-pty routes (server-hosted terminals —
a future route, not needed now), `rpc.call` (plugin RPC). **[live]** spec

### 1.5 Switching/focusing a Session *inside* a TUI over HTTP — gap

The v2.2.7 event protocol **defines** TUI-control events `tui.session.select`
(`{sessionID}` — "Session ID to navigate to"), `tui.command.execute`,
`tui.prompt.append`, `tui.toast.show`, and every TUI **subscribes** to them,
filtered by the TUI's own `directory` (**[src]** `packages/tui/src/app.tsx:1337-1358`:
`event.on("tui.session.select", … route.navigate({type:"session", …})`).
But **no v2.2.7 HTTP route publishes these events** (searched all server/core/protocol
routes; V1's `POST /tui/open-sessions` etc. have no V2 successor). **[src]** So
"make TUI instance X display Session Y" has **no API route today** — only
keystrokes (below) or window-level switching.

## 2. TUI keystroke fallback (v2.2.7 defaults, configurable via `cli.json`)

From the V2 keybinds doc and the compiled defaults in the binary (strings match
exactly) **[docs][bin]**:

- **Interrupt in-flight run: `Escape`** → command `session.interrupt`
  (default `escape`). One press. `ctrl+b` = `session.background` (different
  thing). Inside the shell/subagent composer picker, `ctrl+d` kills that
  child.
- **Danger — do not use Ctrl+C as "interrupt":** `app.exit` defaults to
  `ctrl+c,ctrl+d,<leader>q`, and the `app.exit` layer is enabled whenever the
  prompt is unfocused or empty **[src]** `app.tsx` (~line 1327); `prompt.clear`
  also binds `ctrl+c` (clears text only). With an empty prompt, Ctrl+C is an
  **exit** path, not an abort. Fallbacks must press Esc.
- **In-TUI Session cycling (tabs):** `session.tab.next` = `ctrl+tab` /
  `alt+down`; `session.tab.previous` = `ctrl+shift+tab` / `alt+up`;
  `session.tab.select.1..10` = `<leader>1..0` / `ctrl+1..0`;
  quick slots `<leader>1..9`; `session.list` = `<leader>l` (leader defaults
  `ctrl+x`); `open.menu` = `ctrl+o`; unread: `alt+shift+down/up`.
- These switch **tabs of one TUI instance only** — there is no key to jump to
  another terminal window's TUI.

## 3. Window targeting on KDE/X11

- **The TUI sets the terminal title itself, by default.** `terminalTitleEnabled
  = () => config.data.terminal?.title ?? true`; format: `OC | <session title>`
  (clipped to 40 chars + `…`), plain `OpenCode` on home route or fallback
  title, `OC | <plugin>` for plugin routes; cleared on destroy.
  **[src]** `packages/tui/src/app.tsx:611,636-660` + `util/renderer.ts`
  (`renderer.setTerminalTitle`, OSC via opentui). Toggle command
  `terminal.title.toggle` (default unbound). **[docs]**
  → On KDE/X11: `wmctrl -lp` / `_NET_WM_NAME` match on title prefix `OC | `
  identifies terminal windows running OpenCode; activate with `wmctrl -a`, and
  use `_NET_WM_PID` (wmctrl column) for the owning terminal process, with
  `pgrep -a opencode` to find TUI PIDs. Orca observed propagating the exact
  same `OC | …` title into its tab titles. **[orca]**
- **Inside Orca there is no per-TUI window** — all agent terminals are tabs of
  the single "Orca" window **[live]** (`wmctrl -lp` shows one Orca window while
  3 TUIs run). The focus primitive is
  **`orca terminal switch --terminal <handle>`** ("Switch to a terminal tab in
  the UI"). **[orca]**
- **PTY-level input without any window focus:** `orca terminal send
  --terminal <handle> --text $'\x1b'` writes raw bytes to the PTY ("control
  bytes pass through", Escape documented explicitly), and `--interrupt`
  "Send as an interrupt-style input when supported". **[orca]** `--help`.
  This beats keystroke injection for Orca-hosted TUIs: no X11 focus needed.
- **Orca rows are already identity-rich** **[orca]** `orca terminal list --json`:
  `handle` (`term_…`), `worktreePath`, `branch`, `tabId`, `title`
  (`"OC | <session title>"`), `connected`, `writable`, `lastOutputAt`,
  `agentIdentity` (observed value for OpenCode rows: `"opencode"`; rows of
  plain shells omit it). TUI process cmdlines also carry the bound Session:
  observed `opencode --session ses_e218…` under Orca, giving an
  `ps`-visible TUI→Session mapping. **[live]**
- Which route applies: **Orca-hosted TUI (this user's normal state) → Orca CLI
  (`terminal list` / `switch` / `send`)** for focus and even input; **plain
  terminal windows (Konsole et al.) → title `OC | ` + wmctrl activation +
  xdotool keystrokes** (xdotool + wmctrl toolbox per sibling ticket).

## 4. Multi-instance reality / global registry

- **One shared SQLite DB: `~/.local/share/opencode/opencode.db`**
  (`$XDG_DATA_HOME`): observed tables `session` (2007 rows, v1), **`session_v2`
  (2376 rows)**, `session_message`, `project`, `project_directory`, `worktree`
  (35 rows). `session_v2` columns include `id`, `project_id`, `directory`,
  `title`, `agent`, `model`, `time_created/updated/busy/idle/viewed/archived`,
  `permission`, `metadata`. All background-service clients share it, so it is
  a **cross-project, cross-TUI registry** — but the HTTP API (1.4) is the
  supported read path; prefer it over poking SQLite. **[live]**
- **Stable identity:** Session `id` (`ses_…`, SQLite primary key, survives
  rename/move/restart) is the only stable cycle key. `title` mutates (auto
  renamed by the agent) and is ellipsized in titles; `directory` is stable per
  worktree but many Sessions share one. Recommended "next/previous": Daemon
  keeps an ordered ring of root Session ids from `session.list?parentID=null`
  (sorted by `time.updated`, or by `active` state first), keyed by `ses_…`.
- Live-instance liveness: `service.json.url/pid` (+ `/api/info` →
  `{version,pid,urls,capabilities}`) for the service; per-TUI liveness via
  `orca terminal list` (`connected`, `incarnationId`) or `pgrep -a opencode`;
  per-Session busy state via `/api/session/active` + SSE — no polling of
  windows needed. **[live][orca]**

## Conclusions — per-operation table

| Operation | Mechanism available today | Gap / risk |
|---|---|---|
| **next / previous Session** (cross-instance cycle) | No single "focus Session X" primitive. Build it: ring of root Session ids from `GET /api/session?parentID=null&order=desc` (stable `ses_…` keys) → per target Session resolve its host: inside Orca, `orca terminal list --json` row where `title == "OC \| "+api.title` (or `worktreePath == session.location.directory`) → `orca terminal switch --terminal <handle>`; outside Orca, `wmctrl -a` on the `OC | …` window title. In-TUI alternative: send `ctrl+tab` / `ctrl+shift+tab` (or `<leader>1..9`) to the focused TUI. | ⚠️ **No API route to make a TUI select a Session in 2.2.7** (`tui.session.select` exists but is unpublishable, §1.5). Title↔Session matching is fragile (auto-renames, 40-char ellipsis); one directory can host several Sessions — fall back to `directory` when titles miss. Cycle is Daemon-side state (order of `ses_…` ids), not OpenCode state. |
| **Focus the terminal running the Session** | Orca-hosted: `orca terminal switch --terminal term_…` (rows tagged `agentIdentity:"opencode"`, `writable`, `connected`). Plain terminal: title prefix `OC | ` (set by OpenCode itself, §3) → `wmctrl -lp`/`wmctrl -a`; `_NET_WM_PID` + `pgrep -a opencode` for process-tree confirmation. | Orca route covers this user's main case but is Orca-specific (not generic X11). Standalone-TUI windows are findable, but a `--standalone` instance exposes no usable API (401, unregistered) — keystroke route only for it. Multiple Konsole tabs/windows can share a title after renames; activate-most-recent needs care. |
| **Interrupt in-flight run** | **Preferred (no focus needed):** `POST /api/session/{id}/interrupt` (Basic auth from `service.json`) → `{interrupted:true}`, idempotent when idle, event-observable. Orca alternative: `orca terminal send --terminal … --interrupt` (or raw `$'\x1b'`), PTY-level, no window focus. Fallback: `Escape` into the focused TUI. | API needs the Session id (same title→id mapping as above) and the service to exist (standalone instances untargetable). Keystroke fallback must send **Esc only** — `ctrl+c` is an app-exit path, `ctrl+d` deletes/terminates in composer contexts. Esc interrupts only the Session the TUI is *displaying*; parallel tabs need per-Session API calls. |
| *(bonus) Send input* | `POST /api/session/{id}/prompt` (`delivery:"steer"|"queue"`) — verified; or `orca terminal send --text … --enter` (bracketed-paste safe); or xdotool type into focused TUI. | None material; API is the clean path. |

### Keystroke fallback, exactly (when no API/Orca route applies)

1. Focus the window: `wmctrl -a "<title>"` or `xdotool search --name "^OC \| …" windowactivate` (X11).
2. Interrupt: press `Escape` (xdotool `key Escape`). **Never Ctrl+C/Ctrl+D.**
3. In-TUI cycle: `key ctrl+Tab` / `key ctrl+shift+Tab`; numbered slots `<ctrl+x> N` (leader + digit) for tabs 1..9.
4. There is no keystroke that crosses terminal windows — cross-window "next/previous" must activate a different window (row 1 of the cycle above), not send keys.

### Flagged — no clean mechanism

- **Publish `tui.session.select`** (drive an arbitrary TUI to a Session): event +
  TUI handler exist; publisher route absent in v2.2.7. Fileable as feature
  request; until then it's window-switching or keystrokes.
- **`--standalone` TUIs**: private server is undiscoverable and auth-locked —
  only title/keystroke routes work. Document to users: run on the background
  service (default) if they want the keypad's API path.

## Sources

- **[live]** This machine, opencode 2.2.7: `ss -tlnp`, process table, served
  `http://127.0.0.1:49374/openapi.json` (139 paths; saved copy during research),
  Basic-auth calls to `session.list` / `session.active` / `session.create` /
  `session.prompt` / `session.interrupt` / `session.delete` / `event` SSE,
  `~/.local/{state,share}/opencode/` (`service.json`, `opencode.db` schema+rows).
  Probe Session `vibekey-research-probe` was created in `/tmp/opencode/ocrepo`
  and deleted afterwards (DELETE → 204).
- **[bin]** `strings /usr/bin/opencode` — `service.json` writer path logic,
  compiled keybind defaults.
- **[src]** `github.com/anomalyco/opencode` @ tag `v2.2.7`:
  `packages/tui/src/app.tsx` (title effect 611-660, `tui.*` event handlers
  1337-1358, `app.exit` layer ~1327), `packages/tui/src/util/renderer.ts`,
  `packages/tui/src/config/keybind.ts`, `packages/server/src/handlers/session.ts:608`
  (`session.interrupt`), `packages/server/src/handlers/rpc.ts`,
  `packages/protocol/openapi.json` (event type lists).
- **[docs]** https://opencode.ai/docs/cli/keybinds/ (V2 keybind tables),
  https://opencode.ai/docs/api/ (V2 route reference),
  https://opencode.ai/docs/server/ (V1, banner-noted),
  https://opencode.ai/docs/cli/ (CLI).
- **[orca]** `orca terminal --help`, `orca terminal list --json`,
  `orca terminal switch --help`, `orca terminal send --help` on this machine.
