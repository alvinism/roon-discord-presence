// Turns `roon-discord-presence status --json` into Alfred Script Filter items.
// Runs with `osascript -l JavaScript`, which ships with every macOS.

function run(argv) {
  let s
  try {
    s = JSON.parse(argv[0])
  } catch (e) {
    return JSON.stringify({ items: [{ title: "Could not read status", subtitle: String(argv[0]).slice(0, 200), valid: false }] })
  }

  const extras = []
  if (s.service === "running" && s.state !== "starting") {
    extras.push(s.discord ? "Discord connected" : "waiting for Discord")
    if (s.covers === "none") extras.push("covers off")
  }
  const tail = extras.length ? " · " + extras.join(" · ") : ""

  const summary = {
    stopped: ["Off", "Not running and won't start at login"],
    starting: ["Starting…", "Waiting for the service to report in"],
    approve: ["Waiting for Roon approval", "Enable “Discord Presence” in Roon → Settings → Extensions"],
    "roon-offline": ["Can't reach Roon Core", "Check [roon] host/port in the config" + tail],
    idle: ["Nothing playing", "Running" + tail],
  }
  let title, subtitle
  if (s.state === "playing") {
    const p = s.playing
    title = `${p.title} — ${p.artist}`
    subtitle = `${p.album} · ${p.zone} · ${s.shown ? "shown on Discord" : "updating Discord…"}` +
      (s.covers === "none" ? " · covers off" : "")
  } else {
    [title, subtitle] = summary[s.state] || [s.state, ""]
  }

  const action = (arg, title, subtitle) => ({ uid: arg, title, subtitle, arg })
  const items = [{ uid: "status", title, subtitle, valid: false }]
  if (s.service === "running") {
    items.push(action("stop", "Stop", "Clear Discord status and don't start at login"))
    items.push(action("restart", "Restart", "Reload after changing the config"))
  } else {
    items.push(action("start", "Start", "Run now and at every login"))
  }
  items.push(action("logs", "Open Log", "View the log in Console"))
  return JSON.stringify({ rerun: 1, skipknowledge: true, items })
}
