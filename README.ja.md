<p align="center"><img src="assets/icon.svg" width="128" height="128" alt=""></p>
<h1 align="center">roon-discord-presence</h1>
<p align="center">
  <a href="README.md">English</a> · <b>日本語</b> · <a href="README.zh-Hant.md">繁體中文</a> · <a href="README.zh-Hans.md">简体中文</a>
</p>

[Roon](https://roon.app) で再生中の曲を **Discord のリッチプレゼンス**として表示します。
「〜を再生中」の表示に、曲名・アーティスト・アルバムアート・再生バーが付きます。

> 非公式ツールです。Roon Labs および Discord とは関係ありません。

- **Roon エクステンションとして動作** — Discord を使っている Mac 上で動き、再生中のゾーンを自動で追従します。
- **アルバムアートは自分の管理下に** — Roon のアートワークはローカルネットワーク内でしか取得できないため、
  ジャケット画像は*自分で選んだ*公開先にアップロードします。S3 互換ストレージ（Cloudflare R2、AWS S3、
  Backblaze B2、MinIO）や自作のアップロードスクリプトに対応。ジャケットなしでも使えます。
- **自動復旧** — Roon の再起動、Discord の再起動やアプリ内アップデートの後も自動で再接続します。
- **Roon 内にステータス表示** — 設定 → エクステンションに現在の状態を表示。ランチャー向けに
  `status --json` も用意しています（Alfred ワークフロー同梱。Raycast なども同じ JSON で連携可能）。

現在は macOS のみ対応です。

## インストール

```sh
uv tool install roon-discord-presence            # または: pipx install roon-discord-presence
uv tool install 'roon-discord-presence[s3]'      # S3/R2 へのジャケットアップロードを使う場合
```

> まだ PyPI に公開されていない場合は GitHub から直接インストールできます:
> `uv tool install 'roon-discord-presence[s3] @ git+https://github.com/alvinism/roon-discord-presence'`

続いてガイド付きセットアップを実行します:

```sh
roon-discord-presence setup
```

Roon Core の場所を確認（接続テスト付き）し、必要ならアルバムアートを設定します（実際にアップロードして
公開 URL から取得できるかをテストし、シークレットはキーチェーンに保存）。その後、設定ファイルを書き出して
バックグラウンドサービスを起動し、**Roon → 設定 → エクステンション**で *Discord Presence* の
**有効化**を押すまで待機します。あとは曲を再生すれば、数秒で Discord のプロフィールに表示されます。

手動で設定したい場合は、`roon-discord-presence config init` でコメント付きの設定ファイルを作成し、
編集してから `roon-discord-presence start` を実行してください。

## コマンド

| コマンド | |
|---|---|
| `start` / `stop` / `restart` | バックグラウンドサービス（launchd の LaunchAgent）の起動・停止・再起動 |
| `status [--json]` | 再生中の曲や Discord・Roon との接続状態 — [JSON の仕様](docs/status-json.md) |
| `setup` | ガイド付きセットアップ（設定・ジャケット・サービス・Roon の承認） |
| `run [-v]` | フォアグラウンドで実行（デバッグ用） |
| `config init \| path \| check` | 設定ファイルの作成・場所の表示・検証 |
| `logs [-f]` | ログの表示（`-f` で追従） |

## 設定

`~/.config/roon-discord-presence/config.toml` — すべての項目は省略可能です。

```toml
[roon]
host = "127.0.0.1"        # Roon Core のアドレス。別のマシンで動いている場合はその IP
port = 9330
# zones = ["Desk"]        # これらのゾーンだけを追従

[discord]
# client_id = "..."       # 自分の Discord アプリを使うと「〜を再生中」の名前を変えられます
fallback_image = ""        # ジャケットがないときに表示するアセットキーまたは https URL
status_display = "state"   # メンバーリストの表示: "name"（アプリ名）、"state"（アーティスト）、"details"（曲名）

[covers]
provider = "none"          # none | s3 | command
size = 512
```

シークレットはファイルに直接書かず、macOS キーチェーンや環境変数を参照できます:
`secret_access_key = "keychain:<service>[/<account>]"` または `"env:VAR"`。

設定を変更したら `roon-discord-presence restart` で再起動してください。

## アルバムアート

Discord はインターネット上の画像しか取得できないため、ジャケットは Discord から見える場所に
公開する必要があります。詳しくは **[docs/covers.md](docs/covers.md)**（英語）を参照してください:

- **`s3`** — 公開 URL を持つ S3 互換バケット（Cloudflare R2 の手順付き。R2 は転送量無料で、
  無料枠も十分です）
- **`command`** — 自作スクリプト。例: VPS へ `scp`（[サンプル](examples/upload-scp.sh)）

各アルバムのジャケットは一度だけアップロードされ（内容のハッシュで命名）、以降は再利用されます。

## フロントエンド

- **Alfred** — [`integrations/alfred`](integrations/alfred): 状態表示と起動・停止・再起動。
  [最新リリース](https://github.com/alvinism/roon-discord-presence/releases/latest)から
  `Roon-Discord-Presence.alfredworkflow` をダウンロードするか、
  `python integrations/alfred/build.py` でビルドしてください（`dist/` に出力）。

## ファイルの場所

| | |
|---|---|
| 設定 | `~/.config/roon-discord-presence/config.toml` |
| 状態（Roon トークン、ジャケット対応表、ステータス） | `~/Library/Application Support/roon-discord-presence/` |
| ログ（サイズ上限あり） | `~/Library/Logs/roon-discord-presence/` |
| サービス | `~/Library/LaunchAgents/io.github.alvinism.roon-discord-presence.plist` |

## 制限事項

- **Roon ARC** での再生はエクステンションから見えないため、表示できません。
- Discord は同じ Mac 上のデスクトップアプリである必要があります（リッチプレゼンスはローカルソケットを使用）。

## 開発

```sh
uv sync --all-extras
uv run pytest
uv run ruff check .
uv run roon-discord-presence run -v
```

## ライセンス

MIT
