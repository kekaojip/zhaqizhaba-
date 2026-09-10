---
name: kq-video-analyzer
description: 统一解析和分析主流视频平台链接。支持直接 URL 或整段分享文案，自动提取链接；可选择快速整视频分析、深度字幕/Whisper/关键帧分析，或仅下载。适用于抖音、Bilibili、YouTube、TikTok、X、Instagram、Facebook、Vimeo、Reddit 等 yt-dlp 支持的平台。
metadata:
  short-description: 多平台视频解析、下载与深度分析
---

# KQ Video Analyzer

## Goal

把用户提供的视频链接或平台分享文案，转换成可靠的可分析内容。

核心原则：

1. 优先处理实际视频、音频、字幕和关键帧。
2. 评论区、标题、描述和网页元数据只能作为辅助信息，不能冒充视频内容。
3. 如果下载或转录失败，必须明确报告失败位置，不得假装已经看过视频。
4. 第三方平台若需要登录，使用用户已有浏览器 cookies 或 cookies 文件，不绕过平台权限。

## Entry Point

```bash
python scripts/kq_video.py "<URL 或完整分享文案>" -o ./output --mode auto --goal "<用户目标>"
```

脚本会自动从类似下面的整段文案里提取第一个 http/https 链接：

```text
1.28 复制打开抖音，看看【某人的作品】 https://v.douyin.com/xxxxx/ 其他分享口令
```

## Modes

### auto

默认模式。

- 用户要求“总结、说了什么、核心内容”且存在 `GEMINI_API_KEY` 时，走 `quick`。
- 用户要求“深度分析、拆解、逐段、字幕、关键帧、教程、代码、公式、笔记”等时，走 `deep`。
- 没有 `GEMINI_API_KEY` 时，默认走 `deep`，生成字幕和关键帧供当前 Agent 分析。

### quick

流程：

```text
URL
→ yt-dlp 解析
→ 下载完整视频
→ Gemini Files API
→ Gemini 直接结合音频和画面分析
→ summary.md
```

适合：快速总结、短视频、普通信息提取。

要求：

- `GEMINI_API_KEY`
- `google-genai`
- `yt-dlp`
- `ffmpeg`

### deep

流程：

```text
URL
→ yt-dlp 解析
→ 优先下载平台字幕
→ 无字幕则下载音频并用 Whisper 转录
→ 下载 720p 视频
→ ffmpeg 定时抽帧 + mpdecimate 去重
→ transcript.txt + frames/ + analysis_manifest.json
→ 当前 Agent 读取这些文件完成最终分析
```

适合：教程、代码、PPT、公式、长视频、需要证据的拆解。

深度模式生成：

```text
<output>/<title_id>/
├── metadata.json
├── transcript.txt
├── analysis_manifest.json
└── frames/
    ├── frame_00001.jpg
    ├── frame_00002.jpg
    └── ...
```

Agent 在 `DEEP_PREP_READY` 后必须：

1. 先读取 `transcript.txt`。
2. 根据用户目标选择相关时间段和关键帧。
3. 分析画面中字幕、代码、PPT、操作过程、物体和 UI。
4. 将语音内容与视觉证据交叉验证。
5. 对无法确认的内容明确标记不确定。

### download

仅解析并下载视频，不做 AI 分析。

```bash
python scripts/kq_video.py "<URL>" -o ./output --mode download
```

## Authentication

公开链接先直接尝试。

需要登录时，可以使用：

```bash
--cookies-from-browser chrome
--cookies-from-browser edge
--cookies-from-browser firefox
--cookies-from-browser safari
```

或：

```bash
--cookies-file ./cookies.txt
```

不得要求用户提供账号密码。

## Whisper

本地转录默认使用：

```text
faster-whisper
model=base
device=auto
```

`device=auto` 会尝试检测 CUDA，有 NVIDIA GPU 时优先 GPU，否则使用 CPU int8。

外部 OpenAI-compatible Whisper API：

```bash
python scripts/kq_video.py "<URL>" \
  --mode deep \
  --whisper-api "https://api.example.com/openai/v1/audio/transcriptions"
```

API Key 优先级：

1. `--whisper-api-key`
2. `WHISPER_API_KEY`
3. `GROQ_API_KEY`
4. `OPENAI_API_KEY`

请求会携带 `Authorization: Bearer <key>`。

## Douyin

抖音分享短链可直接作为输入，例如：

```bash
python scripts/kq_video.py "https://v.douyin.com/xxxx/" --mode deep
```

也可以直接传完整复制文案。

如果 `yt-dlp` 无法获取作品：

1. 先确认短链本身仍有效。
2. 再尝试浏览器 cookies。
3. 如果仍失败，停止视频分析并报告具体错误。
4. 网页抓到的评论、推荐内容、搜索关联词不能代替视频内容。

## Failure Rules

以下情况必须停止对应流程：

- `yt-dlp` 无法解析链接。
- 视频/音频无法下载。
- 无字幕且 Whisper 不可用。
- `ffmpeg` 不存在。
- quick 模式缺少 `GEMINI_API_KEY`。
- Gemini 上传或处理失败。

不得把网页摘要、评论区推断或标题扩写包装成“视频分析结果”。

## Installation

```bash
pip install -r requirements.txt
```

还必须安装 `ffmpeg` 并确保在 PATH 中。

## Compatibility

- Claude Code: intended
- Codex: intended
- General Python runtime with shell access: intended
- Plain ChatGPT chat without executable runtime: repository can be read, but the Skill itself cannot be assumed to be installed or runnable
