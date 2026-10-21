<p align="center"><img src="assets/icon.svg" width="128" height="128" alt=""></p>
<h1 align="center">roon-discord-presence</h1>
<p align="center">
  <a href="README.md">English</a> · <a href="README.ja.md">日本語</a> · <a href="README.zh-Hant.md">繁體中文</a> · <b>简体中文</b>
</p>

把 [Roon](https://roon.app) 正在播放的音乐显示为你的 **Discord 丰富状态（Rich Presence）**——
“正在收听……”，并附上曲名、艺人、专辑封面和播放进度条。

> 非官方工具，与 Roon Labs 及 Discord 无关。

- **以 Roon 扩展的形式运行**——在运行 Discord 的那台 Mac 上工作，自动跟随正在播放的区域（zone）。
- **专辑封面由你掌控**——Roon 的封面图只能在局域网内获取，因此封面会上传到*你自己选择*的位置：
  任何 S3 兼容存储（Cloudflare R2、AWS S3、Backblaze B2、MinIO）或你自己的上传脚本，
  也可以完全不使用封面。
- **自动恢复**——Roon 重启、Discord 重启或应用内更新后，都会自动重新连接。
- **在 Roon 中显示状态**——在“设置 → 扩展”中显示当前状态，并提供 `status --json` 供启动器使用
  （内置 Alfred 工作流；Raycast 等也可以基于同一份 JSON 集成）。

目前仅支持 macOS。

## 安装

```sh
uv tool install roon-discord-presence            # 或：pipx install roon-discord-presence
uv tool install 'roon-discord-presence[s3]'      # 需要上传封面到 S3/R2 时
```

> 尚未发布到 PyPI？可以直接从 GitHub 安装：
> `uv tool install 'roon-discord-presence[s3] @ git+https://github.com/alvinism/roon-discord-presence'`

然后运行引导式设置：

```sh
roon-discord-presence setup
```

它会询问 Roon Core 的位置（并测试连接），可选择配置专辑封面（实际上传一次并从公开地址读取来验证，
密钥则保存到“钥匙串”），然后写入配置文件、启动后台服务，并等待你在 **Roon → 设置 → 扩展**中
点击 *Discord Presence* 旁的**启用**。之后只要播放音乐，几秒内就会出现在你的 Discord 个人资料上。

想手动配置？运行 `roon-discord-presence config init` 生成带注释的配置文件，编辑后再运行
`roon-discord-presence start`。

## 命令

| 命令 | |
|---|---|
| `start` / `stop` / `restart` | 管理后台服务（launchd LaunchAgent） |
| `status [--json]` | 正在播放的内容，以及与 Discord／Roon 的连接状态——[JSON 格式说明](docs/status-json.md) |
| `setup` | 引导式设置（配置文件、封面、服务、Roon 授权） |
| `run [-v]` | 在前台运行（调试用） |
| `config init \| path \| check` | 创建、显示路径或校验配置文件 |
| `logs [-f]` | 显示（或持续跟踪）日志 |

## 配置

`~/.config/roon-discord-presence/config.toml`——所有项均为可选。

```toml
[roon]
host = "127.0.0.1"        # Roon Core 地址；若在另一台电脑上运行，请填写它的 IP
port = 9330
# zones = ["Desk"]        # 只跟随这些区域

[discord]
# client_id = "..."       # 使用你自己的 Discord 应用，可以修改“正在收听……”的名称
fallback_image = ""        # 没有封面时显示的资源键或 https 地址
status_display = "state"   # 成员列表显示："name"（应用名称）、"state"（艺人）或 "details"（曲名）

[covers]
provider = "none"          # none | s3 | command
size = 512
```

密钥可以引用 macOS“钥匙串”或环境变量，无需直接写在文件中：
`secret_access_key = "keychain:<service>[/<account>]"` 或 `"env:VAR"`。

修改配置后请运行 `roon-discord-presence restart`。

## 专辑封面

Discord 只能从公网获取图片，因此封面必须发布到 Discord 能访问的地方。详见
**[docs/covers.md](docs/covers.md)**（英文）：

- **`s3`**——任何带公开地址的 S3 兼容存储桶（附 Cloudflare R2 分步教程；R2 不收流量费，
  免费额度也很充足）
- **`command`**——你自己的脚本，例如用 `scp` 上传到 VPS（[示例](examples/upload-scp.sh)）

每张专辑封面只会上传一次（以内容哈希命名），之后重复使用。

## 前端集成

- **Alfred**——[`integrations/alfred`](integrations/alfred)：状态列表与启动／停止／重启。
  可从[最新版本](https://github.com/alvinism/roon-discord-presence/releases/latest)下载
  `Roon-Discord-Presence.alfredworkflow`，或运行 `python integrations/alfred/build.py` 自行构建
  （输出到 `dist/`）。

## 文件位置

| | |
|---|---|
| 配置文件 | `~/.config/roon-discord-presence/config.toml` |
| 状态（Roon 令牌、封面映射表、状态） | `~/Library/Application Support/roon-discord-presence/` |
| 日志（有大小上限） | `~/Library/Logs/roon-discord-presence/` |
| 服务 | `~/Library/LaunchAgents/io.github.alvinism.roon-discord-presence.plist` |

## 限制

- **Roon ARC** 的播放内容对扩展不可见，因此无法显示。
- Discord 必须是同一台 Mac 上的桌面应用（丰富状态通过本地套接字连接）。

## 开发

```sh
uv sync --all-extras
uv run pytest
uv run ruff check .
uv run roon-discord-presence run -v
```

## 许可证

MIT
