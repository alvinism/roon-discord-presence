#!/bin/bash
# Alfred front-end for roon-discord-presence.
#   control.sh status                Script Filter JSON: current state + actions
#   control.sh start|stop|restart    prints a line for the notification
#   control.sh logs                  opens the log in Console

find_bin() {
  for c in "$RDP_BIN" "$HOME/.local/bin/roon-discord-presence" \
           /opt/homebrew/bin/roon-discord-presence /usr/local/bin/roon-discord-presence; do
    [[ -n "$c" && -x "${c/#\~/$HOME}" ]] && { echo "${c/#\~/$HOME}"; return; }
  done
}
BIN=$(find_bin)

if [[ -z "$BIN" ]]; then
  [[ "$1" == status ]] && cat <<'JSON' && exit 0
{"items":[{"title":"roon-discord-presence is not installed","subtitle":"Install: uv tool install roon-discord-presence — or set RDP_BIN in this workflow's configuration","valid":false}]}
JSON
  echo -n "roon-discord-presence not found"; exit 1
fi

case "$1" in
  status)
    osascript -l JavaScript "$(dirname "$0")/status.js" "$("$BIN" status --json 2>&1)"
    ;;
  start|stop|restart)
    out=$("$BIN" "$1" 2>&1); echo -n "${out##*$'\n'}"
    ;;
  logs)
    open -a Console "$HOME/Library/Logs/roon-discord-presence/roon-discord-presence.log"
    ;;
esac
