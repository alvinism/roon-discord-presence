# roon-discord-presence

Roon now-playing → Discord Rich Presence. Python ≥3.11, uv, macOS (launchd) only for now.

## Layout
- `src/roon_discord_presence/`
  - `moo.py` — Roon MOO/1 framing; `roon.py` — our own minimal Roon extension client
    (register, subscribe_zones, provides ping + status services). We deliberately do not use
    `roonapi` (0.1.6 races itself on non-blocking init and lacks a status service).
  - `tracker.py` — zone choice + when to push to Discord (rate limit 4 s, 60 s heartbeat,
    5 s idle grace); pure logic, unit-tested with fake clocks.
  - `discord.py` — pypresence wrapper; on failure reconnect and retry once immediately
    (Discord drops IPC pipes on in-app reloads), then back off 15 s.
  - `covers/` — `CoverCache` (image_key → URL, background publish) + providers `s3`, `command`.
  - `daemon.py` — main loop, Roon status line, `status.json`; `service.py` — LaunchAgent;
    `cli.py` — commands; `config.py` — TOML + `keychain:`/`env:` secret refs.
- `integrations/alfred/` — `control.sh` + `status.js` (JXA, no Python needed), `build.py`.
- `docs/status-json.md` is the contract for front-ends; bump `schema` on breaking changes.

## Commands
`uv sync --all-extras` · `uv run pytest` · `uv run ruff check .` ·
`uv run roon-discord-presence run -v`

## Rules
- Never commit personal values (domains, bucket names, keys, personal Discord app ids);
  use example.com placeholders.
- IDs are `io.github.alvinism.*`.
- Running a second Roon client with the same extension id kicks the first one off Roon.

## Roadmap
v0.2: `http` provider + Cloudflare Worker / Docker cover services, Raycast extension, SwiftBar
plugin, Roon settings page (com.roonlabs.settings), Linux (systemd). Later: SwiftUI menu bar
app, Homebrew tap, Windows.
