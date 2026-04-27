#!/bin/bash
# 周日 09:00 跑：编译 raw/ 下最近一周新增/修改的 .md 到 wiki/concepts/
# 规则源: ~/obsidian-vault/wiki/SCHEMA.md [COMPILE PROMPT]

set -euo pipefail

VAULT="$HOME/obsidian-vault"
LOG_DIR="$VAULT/.scripts/logs"
TS=$(date +%Y-%m-%d_%H%M)
LOG="$LOG_DIR/compile_${TS}.log"
CLAUDE="$(command -v claude || echo claude)"

mkdir -p "$LOG_DIR"
cd "$VAULT"

# 找最近 8 天内新增/修改的 raw/ 文件（覆盖一整周 + 1 天容错）
RAW_FILES=$(find raw -type f -name "*.md" -mtime -8 2>/dev/null || true)

if [ -z "$RAW_FILES" ]; then
    echo "[$(date '+%F %T')] 本周 raw/ 无新增 .md 文件，跳过编译" | tee "$LOG"
    exit 0
fi

PROMPT="请按 wiki/SCHEMA.md 的 [COMPILE PROMPT] 规则，编译以下最近一周新增/修改的 raw/ 文件：

${RAW_FILES}

执行步骤（严格按 SCHEMA.md）：
1. 读 wiki/SCHEMA.md 了解编译规则
2. 读 wiki/INDEX.md 了解已有概念，避免重复创建
3. 识别每份文档的关键概念（人名/公司/工具/方法），在 wiki/concepts/ 创建或更新对应 .md 文件
4. 用 [[wikilinks]] 建立交叉引用
5. 更新 wiki/INDEX.md
6. 完成后输出本次编译摘要：处理了几份 raw、新增/更新了哪些 concepts、新建了多少 wikilinks。"

{
    echo "[$(date '+%F %T')] === 开始编译 ==="
    echo "待处理 raw 文件:"
    echo "$RAW_FILES"
    echo "---"
} | tee "$LOG"

"$CLAUDE" \
    --print \
    --model sonnet \
    --add-dir "$VAULT" \
    --dangerously-skip-permissions \
    "$PROMPT" 2>&1 | tee -a "$LOG"

echo "[$(date '+%F %T')] === 编译完成 ===" | tee -a "$LOG"
