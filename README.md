# obsidian-llm-kb

把 [Andrej Karpathy 的 LLM Knowledge Base 方法论](https://x.com/karpathy/status/1893546148590481814) 落地到 Obsidian + Claude Code。从浏览器一键剪取（论文/博客/视频/推文），每周让 LLM 自动编译成可检索 wiki。

> 核心主张（Karpathy 原文）：**从操纵代码，转向操纵知识。让 LLM 成为知识的编译器。** 不需要向量数据库，不需要 RAG —— 文件系统 + LLM 索引就够。

## 这是什么

```
你读到的内容
   ↓  Web Clipper（7 个针对不同站点的 template 自动路由）
~/obsidian-vault/raw/{web,papers,data,videos,wiki,code,social,conversations}/
   ↓  周日 09:00 launchd 自动调 Claude Code 编译
~/obsidian-vault/wiki/concepts/  （LLM 增量产出的概念词条 + INDEX.md）
   ↓  每月 1 号 09:00 自动 lint
~/obsidian-vault/output/lint-YYYY-MM-DD.md  （健康检查报告）
```

YouTube 还有专属管道：剪进来 30 秒内 yt-dlp 自动抓字幕填入（不下载视频）。

## 包含什么

| 类 | 数量 | 内容 |
|---|---|---|
| Web Clipper templates | 7 | longform / arxiv / tables / github / wikipedia / youtube / twitter |
| 自动化脚本 | 3 | `compile.sh` `lint.sh` `youtube_transcript.py` |
| launchd 任务 | 3 | 周日编译 / 月初体检 / 视频字幕监听 |
| 装机脚本 | 1 | `install.sh` |

## 装机要求

- macOS（launchd 是 macOS 专属，Linux 用户需自己改 systemd）
- [Obsidian](https://obsidian.md) + 启用 [Web Clipper](https://obsidian.md/clipper) 浏览器扩展
- [Claude Code CLI](https://docs.claude.com/claude-code) （compile/lint 调它跑 Sonnet）
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) （仅 YouTube 字幕功能需要：`brew install yt-dlp`）
- Homebrew Python 3（绕过系统 stub 的 sandbox）

## 一键装机

```bash
git clone https://github.com/Shihao-labs/obsidian-llm-kb.git
cd obsidian-llm-kb
./install.sh
```

默认装到 `~/obsidian-vault`。自定义：`./install.sh /path/to/your/vault`

装完会做：
1. 在 vault 下建 `raw/{web,papers,data,...}` 八个子目录
2. 把脚本拷到 `<vault>/.scripts/`
3. 生成 launchd plist 到 `~/Library/LaunchAgents/` 并加载
4. 复制 `wiki/SCHEMA.md` 编译规则文档（如果不存在）

剩下的手动步骤：
1. 装 Web Clipper 浏览器扩展，把 Vault 字段填成你的 vault 名
2. 在 Web Clipper 设置 → Templates → Import，依次导入 `templates/` 下 7 个 JSON
3. （可选）`brew install yt-dlp`

## Web Clipper Templates 速查

| 文件 | 触发 | 落到 | 说明 |
|---|---|---|---|
| 01-longform-article | (空 - 兜底) | `raw/web/` | 博客/Substack/公众号长文 |
| 02-arxiv-paper | `arxiv.org/abs/` `/html/` `/pdf/` | `raw/papers/` | **剪 `/html/` 拿全文，不要剪 `/abs/`**（abs 只有摘要 3KB） |
| 03-tables-data | (空 - 手动选) | `raw/data/` | 政府/数据/表格密集，用 `{{fullHtml\|markdown}}` |
| 04-github-repo | `github.com/` | `raw/code/` | 用 `selectorHtml:.markdown-body` 抓 README |
| 05-wikipedia | `wikipedia.org/wiki/` | `raw/wiki/` | 用 `selectorHtml:#mw-content-text` 去掉侧栏噪音 |
| 06-youtube-video | `youtube.com/watch` `youtu.be/` | `raw/videos/` | metadata 占位，30 秒后字幕自动填入 |
| 07-twitter-fxtwitter | `fxtwitter.com` `vxtwitter.com` | `raw/social/` | **必须把 URL 里 `twitter.com`/`x.com` 手动改成 `fxtwitter.com`** |

## 抓不了的网站（别浪费时间）

| 站点 | 原因 | 替代 |
|---|---|---|
| Twitter/X 直链 | SPA + 反爬 | 改 URL 用 fxtwitter |
| LinkedIn / Notion / 小红书 | SPA + 强反爬 | 手动复制 |
| IEEE / Bloomberg / FT 付费墙 | 反爬 + paywall | 去 arxiv 找 preprint |
| Gmail / Google Docs | 需登录态 | 不抓 |

## 自定义

### 改编译时机
编辑 `~/Library/LaunchAgents/com.shihao.obsidian-compile-weekly.plist`，改 `StartCalendarInterval` 字典里的 Weekday/Hour/Minute。

### 改编译模型
`<vault>/.scripts/compile.sh` 里：
```bash
"$CLAUDE" --print --model sonnet ...
```
把 `sonnet` 换成 `opus` 质量更高（贵 5 倍），或 `haiku` 快但不够细。

### 加新 Web Clipper template
照着 `templates/` 里现有 JSON 改一个 schema 0.1.0 格式的，import 即可。Filter 语法注意：
- `replace` 分隔符是冒号 `:` 不是逗号 `,`：`{{url|replace:"abc":"xyz"}}`
- 链式 pipe：`{{url|replace:"a":"b"|replace:"c":"d"}}`
- selector 参数加引号：`{{selectorHtml:".markdown-body"|markdown}}`

## 已知陷阱

| 陷阱 | 现象 | 修法 |
|---|---|---|
| YouTube 视频抓字幕 429 | `transcript_status: retry_rate_limited` | 等 30 分钟，launchd 自动重试 |
| WatchPaths 自我触发死循环 | 30 秒一次刷屏跑 | `write_if_changed` 幂等写入（已修） |
| launchd Python sandbox 拒绝 | `Operation not permitted` | 用 `/opt/homebrew/bin/python3` 而不是 `/usr/bin/python3` |
| arxiv `/abs/` 剪进来只有 3KB | 那是摘要页不是正文 | 改剪 `/html/` 链接 |

## 我个人的工作流

每天日常浏览 → 看到值得存的内容 → ⇧⌘O 一键剪进 raw/  
周日早上 → launchd 自动跑 compile，新 wiki/concepts/ 词条 + 更新 INDEX.md  
月初 → 自动 lint 报告告诉我哪些概念是孤儿、哪些 raw 还没被编译  
跟 Claude 的有价值对话 → 让它自己判断归档到 `raw/conversations/`（见 SCHEMA.md）

不需要写日报、不需要打 tag、不需要主动整理。**喂料给系统，系统帮你建图书馆。**

## 致谢

- [Andrej Karpathy](https://twitter.com/karpathy) — 2026.04.04 LLM Knowledge Base 推文是这套系统的原型
- [Obsidian Web Clipper](https://github.com/obsidianmd/obsidian-clipper) by [@kepano](https://github.com/kepano)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- Claude Code（用它跑 compile/lint）

## License

MIT
