<p align="center"><img src="assets/icon.svg" width="128" height="128" alt=""></p>
<h1 align="center">roon-discord-presence</h1>
<p align="center">
  <a href="README.md">English</a> · <a href="README.ja.md">日本語</a> · <b>繁體中文</b> · <a href="README.zh-Hans.md">简体中文</a>
</p>

把 [Roon](https://roon.app) 正在播放的音樂顯示為你的 **Discord 豐富狀態（Rich Presence）**——
「正在聆聽……」，並附上曲名、演出者、專輯封面與播放進度條。

> 非官方工具，與 Roon Labs 及 Discord 無關。

- **以 Roon 擴充功能形式執行**——在執行 Discord 的那台 Mac 上運作，自動跟隨正在播放的區域（zone）。
- **專輯封面由你掌控**——Roon 的封面圖只能在區域網路內取得，因此封面會上傳到*你自己選擇*的位置：
  任何 S3 相容的儲存空間（Cloudflare R2、AWS S3、Backblaze B2、MinIO）或你自己的上傳腳本，
  也可以完全不使用封面。
- **自動恢復**——Roon 重新啟動、Discord 重新啟動或應用程式內更新後，都會自動重新連線。
- **在 Roon 中顯示狀態**——於「設定 → 擴充功能」顯示目前狀態，另提供 `status --json` 供啟動器使用
  （內附 Alfred 工作流程；Raycast 等也可以利用同一份 JSON 整合）。

目前僅支援 macOS。

## 安裝

```sh
uv tool install roon-discord-presence            # 或：pipx install roon-discord-presence
uv tool install 'roon-discord-presence[s3]'      # 需要上傳封面到 S3/R2 時
```

> 尚未發布到 PyPI？可以直接從 GitHub 安裝：
> `uv tool install 'roon-discord-presence[s3] @ git+https://github.com/alvinism/roon-discord-presence'`

接著執行引導式設定：

```sh
roon-discord-presence setup
```

它會詢問 Roon Core 的位置（並測試連線），可選擇設定專輯封面（實際上傳一次並從公開網址讀取來驗證，
密鑰則存入「鑰匙圈」），然後寫入設定檔、啟動背景服務，並等待你在 **Roon → 設定 → 擴充功能**中
按下 *Discord Presence* 旁的**啟用**。之後只要播放音樂，幾秒內就會出現在你的 Discord 個人檔案上。

想手動設定？執行 `roon-discord-presence config init` 產生附註解的設定檔，編輯後再執行
`roon-discord-presence start`。

## 指令

| 指令 | |
|---|---|
| `start` / `stop` / `restart` | 管理背景服務（launchd LaunchAgent） |
| `status [--json]` | 正在播放的內容，以及與 Discord／Roon 的連線狀態——[JSON 格式說明](docs/status-json.md) |
| `setup` | 引導式設定（設定檔、封面、服務、Roon 授權） |
| `run [-v]` | 在前景執行（除錯用） |
| `config init \| path \| check` | 建立、顯示路徑或驗證設定檔 |
| `logs [-f]` | 顯示（或持續追蹤）記錄 |

## 設定

`~/.config/roon-discord-presence/config.toml`——所有項目皆為選填。

```toml
[roon]
host = "127.0.0.1"        # Roon Core 位址；若在另一台電腦上執行，請填它的 IP
port = 9330
# zones = ["Desk"]        # 只跟隨這些區域

[discord]
# client_id = "..."       # 使用你自己的 Discord 應用程式，可更改「正在聆聽……」的名稱
fallback_image = ""        # 沒有封面時顯示的素材鍵值或 https 網址
status_display = "state"   # 成員列表顯示："name"（應用程式名稱）、"state"（演出者）或 "details"（曲名）

[covers]
provider = "none"          # none | s3 | command
size = 512
```

密鑰可以引用 macOS「鑰匙圈」或環境變數，不必直接寫在檔案中：
`secret_access_key = "keychain:<service>[/<account>]"` 或 `"env:VAR"`。

修改設定後請執行 `roon-discord-presence restart`。

## 專輯封面

Discord 只能從公開網路取得圖片，因此封面必須發布到 Discord 存取得到的地方。詳見
**[docs/covers.md](docs/covers.md)**（英文）：

- **`s3`**——任何具有公開網址的 S3 相容儲存桶（附 Cloudflare R2 逐步教學；R2 免收流量費，
  免費額度也相當充裕）
- **`command`**——你自己的腳本，例如用 `scp` 上傳到 VPS（[範例](examples/upload-scp.sh)）

每張專輯封面只會上傳一次（以內容雜湊值命名），之後重複使用。

## 前端整合

- **Alfred**——[`integrations/alfred`](integrations/alfred)：狀態清單與啟動／停止／重新啟動。
  可從[最新版本](https://github.com/alvinism/roon-discord-presence/releases/latest)下載
  `Roon-Discord-Presence.alfredworkflow`，或執行 `python integrations/alfred/build.py` 自行建置
  （輸出於 `dist/`）。

## 檔案位置

| | |
|---|---|
| 設定檔 | `~/.config/roon-discord-presence/config.toml` |
| 狀態（Roon 權杖、封面對照表、狀態） | `~/Library/Application Support/roon-discord-presence/` |
| 記錄（有大小上限） | `~/Library/Logs/roon-discord-presence/` |
| 服務 | `~/Library/LaunchAgents/io.github.alvinism.roon-discord-presence.plist` |

## 限制

- **Roon ARC** 的播放內容對擴充功能不可見，因此無法顯示。
- Discord 必須是同一台 Mac 上的桌面應用程式（豐富狀態透過本機通訊端連線）。

## 開發

```sh
uv sync --all-extras
uv run pytest
uv run ruff check .
uv run roon-discord-presence run -v
```

## 授權

MIT
