# Album art providers

Roon serves artwork only on your local network, but Discord downloads images from the public
internet. A **cover provider** takes the JPEG that Roon gives us and makes it reachable at a
public `https://` URL. Without one (`provider = "none"`), Discord shows `fallback_image`, or no
image.

How publishing works, whatever the provider:

1. When a new album starts, the JPEG is fetched from Roon at `covers.size` pixels (default 512).
2. It is named by content hash (`<sha256-prefix>.jpg`), so the same art is never uploaded twice.
3. The provider publishes it; the URL is remembered per album and reused.
4. Known covers are re-confirmed with the provider at most once a day, so providers can refresh
   objects before a storage lifecycle rule deletes them.
5. The upload runs in the background: the presence appears immediately and the cover swaps in a
   moment later. If publishing fails it is retried after 5 minutes.

## `s3` — any S3-compatible bucket

Install with S3 support: `uv tool install 'roon-discord-presence[s3]'`.

```toml
[covers]
provider = "s3"

[covers.s3]
endpoint = "https://<account-id>.r2.cloudflarestorage.com"
bucket = "roon-covers"
region = "auto"                      # R2: "auto"; AWS: e.g. "eu-west-1"
access_key_id = "..."
secret_access_key = "keychain:roon-discord-presence"   # or "env:RDP_S3_SECRET"
public_base_url = "https://covers.example.com"         # where the bucket is publicly served
prefix = ""                          # optional key prefix, e.g. "covers"
reupload_after_days = 20             # refresh objects older than this (keep < lifecycle rule)
```

Store the secret in the Keychain (it prompts without echoing):

```sh
security add-generic-password -s roon-discord-presence -w
```

### Cloudflare R2 walkthrough

R2 has no egress fees and a free tier of 10 GB storage — at ~60 KB per cover that is well over
100,000 albums, and with the lifecycle rule below the bucket only holds the last month's covers.

1. **R2 Object Storage → Create bucket**, e.g. `roon-covers`, storage class **Standard**.
2. **Bucket → Settings → Custom Domains → Connect Domain**, e.g. `covers.example.com`
   (the domain must be on Cloudflare). Leave the `r2.dev` public URL disabled.
3. **Settings → Object lifecycle rules → Add rule**: delete objects after **30 days**.
4. **R2 → Manage API tokens → Create API token**: permission **Object Read & Write**,
   **specific bucket** only. Copy the Access Key ID and Secret Access Key, and note your
   account ID (it is in the S3 endpoint URL).
5. Fill in `[covers.s3]` as above, then `roon-discord-presence config check` and
   `roon-discord-presence restart`.

Other S3-compatible services work the same way: set `endpoint`, `region`, and a
`public_base_url` that serves the bucket's objects (bucket website, CDN, or custom domain).

## `command` — bring your own uploader

Run any program you like. It receives the JPEG on **stdin** and the file name as its **last
argument**, and must print the public `https://` URL on its last line of stdout. Exit non-zero
to signal failure (stderr ends up in the log).

```toml
[covers]
provider = "command"

[covers.command]
command = ["/Users/me/bin/upload-cover.sh"]
timeout = 30
```

It must be idempotent — it is called again (at most daily) for covers it already published.

See [`examples/upload-scp.sh`](../examples/upload-scp.sh) for a VPS + web server setup.

## `none`

No uploads. Set `discord.fallback_image` to an asset key from your Discord application, or to
any https image URL, to show a fixed image instead.
