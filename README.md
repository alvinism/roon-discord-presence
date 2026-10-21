<p align="center"><img src="https://raw.githubusercontent.com/alvinism/roon-discord-presence/main/assets/icon.png" width="128" height="128" alt=""></p>
<h1 align="center">roon-discord-presence</h1>
<p align="center">
  <b>English</b> · <a href="https://github.com/alvinism/roon-discord-presence/blob/main/README.ja.md">日本語</a> · <a href="https://github.com/alvinism/roon-discord-presence/blob/main/README.zh-Hant.md">繁體中文</a> · <a href="https://github.com/alvinism/roon-discord-presence/blob/main/README.zh-Hans.md">简体中文</a>
</p>

Show what [Roon](https://roon.app) is playing as your **Discord Rich Presence** — "Listening to …"
with title, artist, album art and a progress bar.

> Unofficial. Not affiliated with Roon Labs or Discord.

- **Runs as a Roon extension** on the Mac where Discord runs; follows whichever zone is playing.
- **Album art on your own terms** — Roon's artwork is only reachable on your network, so covers
  are published through a provider *you* choose: any S3-compatible bucket (Cloudflare R2, AWS S3,
  Backblaze B2, MinIO) or your own upload script. Or skip covers entirely.
- **Self-healing** — survives Roon restarts, Discord restarts and in-app Discord updates.
- **Status line in Roon** under Settings → Extensions, plus `status --json` for launchers
  (Alfred workflow and Raycast extension included; other tools can build on the same JSON).

macOS only for now.

## Install

```sh
uv tool install roon-discord-presence            # or: pipx install roon-discord-presence
uv tool install 'roon-discord-presence[s3]'      # with S3/R2 cover upload support
```


Then run the guided setup:

```sh
roon-discord-presence setup
```

It asks where your Roon Core is (and checks it), optionally sets up album art (testing an
upload end to end and keeping the secret in the Keychain), writes the config, starts the
background service, and waits while you click **Enable** next to *Discord Presence* in
**Roon → Settings → Extensions**. Play something — your Discord profile shows it within seconds.

Prefer doing it by hand? `roon-discord-presence config init` writes a commented config file;
edit it, then `roon-discord-presence start`.

## Commands

| Command | |
|---|---|
| `start` / `stop` / `restart` | manage the background service (a launchd LaunchAgent) |
| `status [--json]` | what is playing, whether Discord/Roon are connected — [JSON schema](docs/status-json.md) |
| `setup` | guided setup (config, covers, service, Roon approval) |
| `run [-v]` | run in the foreground (debugging) |
| `config init \| path \| check` | create, locate or validate the config file |
| `logs [-f]` | show (or follow) the log |

## Configuration

`~/.config/roon-discord-presence/config.toml` — every key is optional.

```toml
[roon]
host = "127.0.0.1"        # the Roon Core; use its IP if it runs on another machine
port = 9330
# zones = ["Desk"]        # only follow these zones

[discord]
# client_id = "..."       # your own Discord app, to change the "Listening to …" name
fallback_image = ""        # asset key or https URL when there is no cover
status_display = "state"   # member list shows "name" (app), "state" (artist) or "details" (title)

[covers]
provider = "none"          # none | s3 | command
size = 512
```

Secrets can reference the macOS Keychain or the environment instead of being written in the file:
`secret_access_key = "keychain:<service>[/<account>]"` or `"env:VAR"`.

Restart after changing the config: `roon-discord-presence restart`.

## Album art

Discord fetches images from the public internet, so covers must be published somewhere it can
reach. See **[docs/covers.md](docs/covers.md)** for:

- **`s3`** — any S3-compatible bucket with a public URL (step-by-step guide for Cloudflare R2,
  which has free egress and a generous free tier),
- **`command`** — your own script, e.g. `scp` to a VPS ([example](examples/upload-scp.sh)).

Each album is uploaded once (named by content hash) and reused afterwards.

## Front-ends

- **Raycast** — [`integrations/raycast`](integrations/raycast): a menu bar item with the track
  on your Discord status, plus a status view with cover, connections and zones. Run
  `npm install && npm run dev` in that folder to add it to Raycast.
- **Alfred** — [`integrations/alfred`](integrations/alfred): status list with start/stop/restart.
  Download `Roon-Discord-Presence.alfredworkflow` from the
  [latest release](https://github.com/alvinism/roon-discord-presence/releases/latest), or build it
  with `python integrations/alfred/build.py` (output in `dist/`).

## Files

| | |
|---|---|
| Config | `~/.config/roon-discord-presence/config.toml` |
| State (Roon token, cover map, status) | `~/Library/Application Support/roon-discord-presence/` |
| Log (size-limited) | `~/Library/Logs/roon-discord-presence/` |
| Service | `~/Library/LaunchAgents/io.github.alvinism.roon-discord-presence.plist` |

## Limitations

- **Roon ARC** playback is not visible to extensions, so it can't be shown.
- Discord must be the desktop app on the same Mac (Rich Presence uses a local socket).

## Development

```sh
uv sync --all-extras
uv run pytest
uv run ruff check .
uv run roon-discord-presence run -v
```

## License

MIT
