# obsidian-llm-kb

7 个针对不同站点优化的 [Obsidian Web Clipper](https://obsidian.md/clipper) 模板。直接 Import 到 Web Clipper 设置里就能用，剪不同类型网页自动落到对应文件夹 + 抓对内容。

灵感来自 [Andrej Karpathy 2026.04.04 推文](https://x.com/karpathy/status/1893546148590481814) 的 LLM Knowledge Base 方法论 —— 这套模板是其中"raw 数据摄入"环节的具体落地。

## 怎么用

1. 装 [Obsidian Web Clipper 浏览器扩展](https://obsidian.md/clipper)
2. 在 Web Clipper 设置页 → Templates → **Import**，依次选这 7 个 JSON
3. 在你的 Obsidian vault 里建好这些子目录（模板里写死的 path）：

   ```
   raw/web/
   raw/papers/
   raw/data/
   raw/code/
   raw/wiki/
   raw/videos/
   raw/social/
   ```

4. 之后剪网页时按 ⇧⌘O，命中 trigger 的会自动选对应模板，没命中走 Long-form Article 兜底

## 7 个模板速查

| 文件 | 名字 | Trigger | 落到 | 内容抓法 |
|---|---|---|---|---|
| 01-longform-article | Long-form Article | (空 - 兜底) | `raw/web/` | `{{content}}` Reader 模式 |
| 02-arxiv-paper | arXiv Paper | `arxiv.org/abs/` `/html/` `/pdf/` | `raw/papers/` | Abstract + Full Content，arxiv_id 链式 replace |
| 03-tables-data | Tables & Data | (空 - 手动选) | `raw/data/` | `{{fullHtml\|markdown}}` 抓表格 |
| 04-github-repo | GitHub Repo | `github.com/` | `raw/code/` | `{{selectorHtml:".markdown-body"\|markdown}}` 抓 README |
| 05-wikipedia | Wikipedia | `wikipedia.org/wiki/` | `raw/wiki/` | `{{selectorHtml:"#mw-content-text"\|markdown}}` 去侧栏 |
| 06-youtube-video | YouTube Video | `youtube.com/watch` `youtu.be/` | `raw/videos/` | metadata + yt-dlp 命令占位 |
| 07-twitter-fxtwitter | Twitter (FxTwitter) | `fxtwitter.com` `vxtwitter.com` | `raw/social/` | 通过 FxTwitter 镜像抓静态 HTML |

## 几个非显然的注意点

- **arXiv 永远剪 `/html/` 链接**，不要剪 `/abs/` —— `/abs/` 只有摘要 3KB，`/html/` 是全文阅读版几十 KB
- **Tables & Data trigger 是空** —— 访问表格密集的页面（政府站 / Wikipedia / 数据页）后，从 Web Clipper 弹窗顶部下拉手动切到这个模板
- **Twitter / X 必须改 URL** —— 看到推文 URL 是 `twitter.com/...` 或 `x.com/...`，手动把域名改成 `fxtwitter.com` 再剪。原 twitter 是 SPA + 反爬，Web Clipper 抓不到任何内容
- **Reader 模式擅长长文章，不擅长表格/SPA** —— Long-form Article 用的 `{{content}}` 走 Reader，对博客/Substack/新闻效果好；遇到表格密集页面要手动切 Tables & Data

## 完全抓不到的网站（别浪费时间）

| 站点 | 原因 | 替代方案 |
|---|---|---|
| Twitter / X 直链 | SPA + 反爬 | 改 URL 用 fxtwitter |
| LinkedIn / Notion / 小红书 | SPA + 强反爬 | 手动复制粘贴 |
| IEEE / Bloomberg / FT 付费墙 | 反爬 + paywall | 去 arxiv 找同篇 preprint |
| Gmail / Google Docs | 需登录态 + SPA | 不抓 |

## Filter 语法陷阱

如果你想自己改这些模板：

- `replace` 分隔符是冒号 `:` 不是逗号 `,`：`{{url|replace:"abc":"xyz"}}`
- 链式 pipe：`{{url|replace:"a":"b"|replace:"c":"d"}}`
- `selector` 参数加引号：`{{selectorHtml:".markdown-body"|markdown}}`
- `split` filter 在 `noteNameFormat` 上下文不工作（实测）

## License

MIT
