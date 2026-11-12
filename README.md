# astrbot_plugin_japan_livecam (日本实况街景) 🗾

基于 [Mini Tokyo 3D](https://minitokyo3d.com/) 与 YouTube 实时视频流核心的 AstrBot 插件。可以在 QQ 群/私聊中直接获取日本东京、羽田机场、成田机场、涩谷、新宿、富士山等 65+ 个地标的**当前秒数真实视频截图**。

> [!IMPORTANT]
> **绝对真实实况保障（杜绝封面假象）**：
> 本插件**严格只截取正在播放的视频流真实现况**（真黑夜、跑道真地勤、实时人流）。若因网络或凭证问题导致抽帧失败，插件会**如实报告失败，坚决不拿静态预设封面图糊弄替代**！

---

## ✨ 特性

- 🎥 **真·当前秒数实时视频抽帧**：直接驱动无头浏览器接入 YouTube 正在播放的视频核心，跳过前置贴片广告，精准抓取当下发生的真实画面。
- 📸 **65+ 核心地标机位**：覆盖羽田机场 T2 停机坪、成田机场、涩谷十字路口、新宿歌舞伎町、秋叶原、东京站、彩虹大桥、富士山河口湖、江之电七里滨踏切等。
- 🛡️ **智能 Cookie 注入**：内置全格式兼容器，兼容标准 Netscape `cookies.txt` 或直接从浏览器 F12 复制的 Cookie 纯文本，彻底攻克 YouTube 机器人风控。
- 🤖 **LLM Agent 自然语言融合**：接入 `@filter.llm_tool`，在群聊中随意说“*想看看目前东京羽田机场的画面*”、“*帮我看下涩谷街头现在下雨没*”，大模型即可自动调取。
- ⚡ **快捷指令支持**：支持 `/livecam <地点>`（如 `/livecam 羽田机场`）与 `/livecam list` 查看机位目录。
- 🚫 **无外部链接输出**：不展示任何 YouTube 直播源外链，仅展示真实大图与 Mini Tokyo 3D 三维机位坐标。

---

## 🚀 安装与部署指南

### 1. 克隆插件到 AstrBot

进入你的 AstrBot 项目目录下的 `data/plugins/`：

```bash
cd AstrBot/data/plugins
git clone https://github.com/Anon2Tokyo/astrbot_plugin_japan_livecam.git
```

### 2. 在 Google Cloud / Linux 服务器上安装抽帧依赖

在云服务器中运行以下命令安装 Playwright 及其无头浏览器内核：

```bash
pip install playwright
playwright install chromium
playwright install-deps chromium
```

### 3. 配置认证凭证（cookies.txt）

为了让云服务器顺利穿透 YouTube 直播流的机器人验证：

1. 在电脑浏览器登录 YouTube，按 **F12** 进入网络（Network）选项卡，刷新页面。
2. 找到第一个 `www.youtube.com` 请求，在请求标头（Request Headers）中找到 `Cookie:` 并右键复制其值。
3. 在云服务器插件目录下创建 `cookies.txt` 并粘贴保存：
   ```bash
   cd AstrBot/data/plugins/astrbot_plugin_japan_livecam
   nano cookies.txt
   # (粘贴复制的内容，Ctrl+O 保存，Ctrl+X 退出)
   chmod 600 cookies.txt
   ```

*(也可以直接将该 Cookie 文本设为环境变量 `YOUTUBE_COOKIES`)*

---

## 💬 使用示例

### 1. 自然语言交互 (LLM Agent)
直接在 QQ 对话：
* `“想看看目前东京羽田机场的画面”`
* `“涩谷现在人多吗？调个画面看看”`
* `“看下富士山现在能不能看见”`

### 2. 快捷指令
* `/livecam 羽田机场`：直接调取羽田机场第 2 航站楼实时停机坪画面。
* `/livecam 涩谷`：查看涩谷十字路口实况。
* `/livecam 富士山`：查看河口湖富士山景观机位。
* `/livecam` 或 `/livecam list`：获取支持的热门地点分类列表。

---

## 📄 开源许可

[MIT License](LICENSE) © 2026 soyorin (Anon2Tokyo)
