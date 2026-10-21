#!/bin/bash
# Example `command` cover provider: copy the cover to a VPS that serves a directory over HTTPS.
#
#   [covers]
#   provider = "command"
#   [covers.command]
#   command = ["/path/to/upload-scp.sh"]
#
# Server side (once): a web server (nginx, Caddy…) serving /var/www/covers at
# https://covers.example.com, and an SSH key that may write there. Optionally clean up old files
# with a cron job:  find /var/www/covers -name '*.jpg' -mtime +30 -delete
set -euo pipefail

HOST="covers@vps.example.com"
REMOTE_DIR="/var/www/covers"
PUBLIC_URL="https://covers.example.com"

name="$1"   # content-hash file name, e.g. 0123abcd….jpg

# stdin is the JPEG; write it remotely (and refresh mtime so cleanup keeps covers in use)
ssh -o BatchMode=yes "$HOST" "cat > '$REMOTE_DIR/$name.tmp' && mv '$REMOTE_DIR/$name.tmp' '$REMOTE_DIR/$name'"

echo "$PUBLIC_URL/$name"
