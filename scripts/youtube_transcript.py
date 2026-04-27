#!/usr/bin/env python3
"""
YouTube transcript fetcher
监控 raw/videos/，新 .md 文件出现就用 yt-dlp 抓字幕填入 Transcript 段。
- 只下字幕（--skip-download），不占硬盘
- 多语言降级 zh-Hans > zh-CN > zh > zh-Hant > en
- 已处理文件靠 frontmatter `transcript_status` marker 跳过
- 没字幕的视频标 no_sub_found，等用户手动决定（VoiceInk/放弃）
"""
import os
import re
import sys
import glob
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime

VAULT = Path.home() / "obsidian-vault"
VIDEOS_DIR = VAULT / "raw" / "videos"
LOG_FILE = VAULT / ".scripts" / "logs" / "youtube_transcript.log"
import shutil
YT_DLP = shutil.which("yt-dlp") or "/opt/homebrew/bin/yt-dlp"

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def log(msg):
    line = f"[{datetime.now():%F %T}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def fetch_subtitle(url, tmpdir):
    """
    返回 (srt_path, lang, status):
      status ∈ {"ok", "no_sub", "rate_limited", "network_error", "unknown_error", "timeout"}
    """
    cmd = [
        YT_DLP, "--skip-download",
        "--write-auto-sub", "--write-sub",
        "--sub-lang", "zh-Hans,zh-CN,zh,zh-Hant,en",
        "--convert-subs", "srt",
        "--output", str(Path(tmpdir) / "sub.%(ext)s"),
        url,
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        log("  yt-dlp TIMEOUT (>180s)")
        return None, None, "timeout"

    stderr_full = r.stderr if r.stderr else ""
    stdout_full = r.stdout if r.stdout else ""
    stderr_tail = stderr_full[-800:].strip()

    # 优先级 1: 任何 HTTP / 网络 / 限流错误 → retry（不论是否在 tail 或 full 里）
    if "429" in stderr_full or "Too Many Requests" in stderr_full:
        log(f"  RATE_LIMITED: {stderr_tail[-200:]}")
        return None, None, "rate_limited"
    if "HTTP Error" in stderr_full or "Unable to download" in stderr_full:
        log(f"  NETWORK_ERROR: {stderr_tail[-200:]}")
        return None, None, "network_error"
    if "Connection" in stderr_full or "Network" in stderr_full \
       or "timed out" in stderr_full.lower():
        log(f"  NETWORK_ERROR: {stderr_tail[-200:]}")
        return None, None, "network_error"

    # 优先级 2: returncode 非零（且不是上面识别的网络错误）→ retry，不要冒险判 no_sub
    if r.returncode != 0:
        log(f"  UNKNOWN_ERROR (rc={r.returncode}): {stderr_tail[-300:]}")
        return None, None, "unknown_error"

    # 优先级 3: returncode == 0 才能判 no_sub（终态）
    # 严格匹配 yt-dlp 自己的"has no" 句式
    if "has no automatic captions" in stdout_full or "has no subtitles" in stdout_full:
        return None, None, "no_sub"

    srts = glob.glob(str(Path(tmpdir) / "*.srt"))
    if not srts:
        # rc=0 但没字幕文件且没明确 "has no" 信号 —— 保守起见走 retry
        log("  WEIRD: rc=0 但无 srt 也无 no-captions 信号，走 retry")
        return None, None, "unknown_error"

    # 按语言优先级排序选最好的
    priority = ["zh-Hans", "zh-CN", "zh", "zh-Hant", "en"]
    def rank(p):
        m = re.search(r"sub\.([^.]+)\.srt", os.path.basename(p))
        lang = m.group(1) if m else "unknown"
        return priority.index(lang) if lang in priority else 99
    srt = sorted(srts, key=rank)[0]
    m = re.search(r"sub\.([^.]+)\.srt", os.path.basename(srt))
    return srt, (m.group(1) if m else "unknown"), "ok"


def clean_srt(srt_path):
    """SRT → 纯文本（去序号/时间戳/HTML tag，去相邻重复）"""
    with open(srt_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    out = []
    prev = None
    for line in lines:
        line = line.rstrip()
        if not line:
            continue
        if re.match(r"^\d+$", line):
            continue
        if "-->" in line:
            continue
        line = re.sub(r"<[^>]*>", "", line)
        if line and line != prev:
            out.append(line)
            prev = line
    return " ".join(out)


def add_frontmatter_field(content, key, value):
    """在 YAML frontmatter 末尾插入一个字段（之前），保持 --- 包裹结构"""
    return re.sub(
        r"(^---\n.*?\n)(---\n)",
        rf"\1{key}: {value}\n\2",
        content,
        count=1,
        flags=re.DOTALL,
    )


def write_if_changed(file_path, new_content, old_content):
    """幂等写入：内容没变化就不写（避免 WatchPaths 自我触发）"""
    if new_content == old_content:
        log("  (内容未变化，跳过写入避免触发 watcher)")
        return False
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    return True


def process_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    original_content = content

    # 终态（done / no_sub_found）跳过；retry_pending / rate_limited / network_error 还会重试
    m_status = re.search(r"^transcript_status:\s*(\S+)", content, re.MULTILINE)
    if m_status and m_status.group(1) in ("done", "no_sub_found", "skipped"):
        return "skip_done"
    if "TODO: 用 yt-dlp" not in content and not m_status:
        return "skip_no_todo"

    m = re.search(r'^source:\s*"([^"]+)"', content, re.MULTILINE)
    if not m:
        log(f"  SKIP: 无 source URL → {file_path.name}")
        return "skip_no_url"
    url = m.group(1)

    log(f"处理: {file_path.name}")
    log(f"  URL: {url}")

    # 如果文件已经有旧的 transcript_status（retry 类），先剥掉再写新的
    content = re.sub(r"^transcript_status:\s*\S+\n", "", content, flags=re.MULTILINE)
    content = re.sub(r"^transcript_lang:\s*\S+\n", "", content, flags=re.MULTILINE)
    content = re.sub(r"^transcript_last_attempt:\s*\S+\n", "", content, flags=re.MULTILINE)

    with tempfile.TemporaryDirectory() as tmpdir:
        srt, lang, status = fetch_subtitle(url, tmpdir)

        now_ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        if status == "ok":
            transcript = clean_srt(srt)
            content = add_frontmatter_field(content, "transcript_status", "done")
            content = add_frontmatter_field(content, "transcript_lang", lang)
            content = re.sub(
                r"## Transcript\n.*$",
                f"## Transcript\n\n_Source: yt-dlp auto-sub ({lang}) | Fetched: {now_ts}_\n\n{transcript}\n",
                content,
                flags=re.DOTALL,
            )
            write_if_changed(file_path, content, original_content)
            log(f"  ✓ OK: lang={lang}, {len(transcript)} chars")
            return "ok"

        elif status == "no_sub":
            content = add_frontmatter_field(content, "transcript_status", "no_sub_found")
            content = content.replace(
                "## Transcript",
                "## Transcript\n\n> ⚠️ yt-dlp 未找到字幕。手动用 VoiceInk 录屏转录，或放弃。\n\n### Original TODO（已失效）",
                1,
            )
            write_if_changed(file_path, content, original_content)
            log("  ✗ NO_SUB (终态，下次跳过)")
            return "no_sub"

        else:
            # rate_limited / network_error / timeout / unknown_error → 标 retry
            # 幂等性：transcript_last_attempt 不写入文件（每次都变会引爆 WatchPaths）
            # 只写 transcript_status，连续 retry 多次状态相同就不会重写
            content = add_frontmatter_field(content, "transcript_status", f"retry_{status}")
            wrote = write_if_changed(file_path, content, original_content)
            if wrote:
                log(f"  ⏳ RETRY ({status})，下次 launchd 触发会重试")
            else:
                log(f"  ⏳ RETRY ({status})，状态未变化（已切断自触发循环）")
            return f"retry_{status}"


def main():
    if not VIDEOS_DIR.exists():
        log(f"FATAL: {VIDEOS_DIR} 不存在")
        sys.exit(0)
    md_files = sorted(VIDEOS_DIR.glob("*.md"))
    if not md_files:
        log("(空目录，跳过)")
        return
    for f in md_files:
        try:
            process_file(f)
        except Exception as e:
            log(f"  ! EXCEPTION on {f.name}: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
