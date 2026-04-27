#!/bin/bash
# 每月 1 号 09:00 跑：lint 整个 wiki/，体检报告写到 output/
# 规则源: ~/obsidian-vault/wiki/SCHEMA.md [LINT PROMPT]

set -euo pipefail

VAULT="$HOME/obsidian-vault"
LOG_DIR="$VAULT/.scripts/logs"
TS=$(date +%Y-%m-%d)
LOG="$LOG_DIR/lint_${TS}.log"
OUTPUT="$VAULT/output/lint-${TS}.md"
CLAUDE="$(command -v claude || echo claude)"

mkdir -p "$LOG_DIR" "$VAULT/output"
cd "$VAULT"

PROMPT="请按 wiki/SCHEMA.md 的 [LINT PROMPT] 规则扫描整个知识库，执行健康检查：

1. **孤立概念**：列出 wiki/concepts/ 下没有任何 wikilink 指向的文件
2. **内容矛盾**：扫描 wiki/concepts/ 找出潜在事实矛盾或表述冲突
3. **缺失关联**：建议应该建立但还没有的 [[wikilinks]] 连接
4. **未编译 raw**：对比 raw/ 与 wiki/concepts/ 中 frontmatter 里的 source 字段，列出 raw/ 中还没被任何 concept 引用过的 .md 文件
5. **过期警告**：找出 wiki/concepts/ 里 compiled_at 超过 90 天且引用的 raw 文件已更新的 concepts

将完整报告以 Markdown 格式保存到 $OUTPUT，包含上述 5 个章节，每节给出文件路径列表 + 一句话说明。"

echo "[$(date '+%F %T')] === 开始 lint ===" | tee "$LOG"

"$CLAUDE" \
    --print \
    --model sonnet \
    --add-dir "$VAULT" \
    --dangerously-skip-permissions \
    "$PROMPT" 2>&1 | tee -a "$LOG"

echo "[$(date '+%F %T')] === lint 完成，报告: $OUTPUT ===" | tee -a "$LOG"
