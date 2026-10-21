# `status --json`

Front-ends (Alfred, Raycast, menu bar apps…) should only depend on this output and on the
`start` / `stop` / `restart` commands.

```sh
roon-discord-presence status --json
```

```json
{
  "schema": 1,
  "service": "running",
  "state": "playing",
  "roon": "ok",
  "core": "Core",
  "discord": true,
  "covers": "s3",
  "playing": {
    "zone": "Desk",
    "title": "Song",
    "artist": "Artist",
    "album": "Album",
    "cover": "https://covers.example.com/0123abcd.jpg"
  },
  "shown": true,
  "zones": [{ "name": "Desk", "state": "playing" }],
  "updated": 1792585391
}
```

| Field | Meaning |
|---|---|
| `schema` | Bumped on breaking changes. |
| `service` | `running` (LaunchAgent loaded) or `stopped`. |
| `state` | One-word summary: `stopped`, `starting`, `approve` (enable the extension in Roon), `roon-offline`, `idle`, `playing`. |
| `roon` | `ok`, `approve` or `offline`. |
| `core` | Roon Core name, once paired. |
| `discord` | Whether the Discord desktop app is connected. |
| `covers` | Cover provider in use: `none`, `s3` or `command`. |
| `playing` | The followed zone's track, or `null`. `cover` is `null` until published. |
| `shown` | Whether the presence is currently set on Discord. |
| `zones` | All zones Roon reports, with their transport state. |
| `updated` | Unix time of the last change. |

Only `schema`, `service` and `state` are always present; the rest appear while the service is
running and has reported in.
