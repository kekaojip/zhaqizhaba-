# kq-video-analyzer

一个统一的视频解析、下载和分析 Skill。

它不是第三个重复下载器，而是把仓库里两条已有路线合并成一个入口：

```text
快速模式：URL → 下载完整视频 → Gemini 直接看音视频 → summary.md
深度模式：URL → 字幕优先 → Whisper 兜底 → 关键帧 → Agent 深度分析
下载模式：URL → 下载视频
```

## 适用平台

底层使用 yt-dlp，因此适用于 yt-dlp 当前支持的平台，包括 YouTube、Bilibili、抖音、TikTok、X、Instagram、Facebook、Vimeo、Reddit 等。

平台支持范围由 yt-dlp 决定，不代表每个平台在任何时候都无需登录或都能稳定下载。

## 基本使用

```bash
python scripts/kq_video.py "https://www.youtube.com/watch?v=..." \
  -o ./output \
  --mode auto \
  --goal "总结这个视频"
```

也可以直接粘贴平台完整分享文案：

```bash
python scripts/kq_video.py "1.28 复制打开抖音，看看【某人的作品】 https://v.douyin.com/xxxxx/ 其他口令" \
  -o ./output \
  --mode deep \
  --goal "分析视频里实际演示了什么"
```

## 模式

- `auto`：按用户目标和环境自动选择 quick/deep
- `quick`：完整视频交给 Gemini 分析
- `deep`：字幕/Whisper + 关键帧，供当前 Agent 深度分析
- `download`：仅下载

## 安装

```bash
pip install -r requirements.txt
```

另需安装 `ffmpeg`。

## 环境变量

快速模式：

```bash
export GEMINI_API_KEY="..."
```

可选：

```bash
export GEMINI_MODEL="gemini-3-flash-preview"
```

外部 Whisper API 可使用：

```bash
export WHISPER_API_KEY="..."
# 或 GROQ_API_KEY / OPENAI_API_KEY
```

## 登录内容

如平台需要用户已登录状态：

```bash
python scripts/kq_video.py "<URL>" --cookies-from-browser chrome --mode deep
```

或者传 Netscape cookies 文件：

```bash
python scripts/kq_video.py "<URL>" --cookies-file ./cookies.txt --mode deep
```

## 可靠性边界

网页标题、简介、评论、相关推荐都不能替代实际视频分析。

只有在成功取得视频、音频、字幕或关键帧后，才能声称分析了视频内容。如果下载或转录失败，必须报告失败步骤并停止对应分析。
