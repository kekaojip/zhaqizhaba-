# 🎬 video-to-notes

[English](./README_EN.md) | **中文**

> 把任意视频变成结构化学习笔记，告别手动截图和整理笔记的痛苦。

---

## 😩 你是否也有这些烦恼？

- 📚 **学习视频太多**，看完就忘，没有系统的笔记可以复习
- 🎓 **学生/科研人员**需要从视频中截图、整理公式、做汇报 PPT，耗时费力
- 🌍 **外语视频**看不懂，想要中文笔记却没有字幕
- 💼 **会议/讲座录像**需要整理成文档，手动转录太慢
- 🔬 **技术教程**里的代码和公式一闪而过，根本来不及记

**video-to-notes 就是为解决这些问题而生的。**

---

## ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 🌐 **多平台支持** | YouTube、Bilibili、Twitter、TikTok 等 30+ 主流平台 |
| 📝 **字幕优先** | 自动获取平台字幕，无字幕时用 Whisper 本地转录 |
| 🖼️ **智能帧分析** | 自动提取关键帧，PSNR 去重，分批并行分析 |
| 🧠 **AI 深度讲解** | 公式逐项解释，生活化类比，自动补充背景知识 |
| 🔰 **初学者友好** | 难度标注、结论速览、章节要点总结 |
| 🌏 **多语言支持** | 支持翻译为中/英/日/韩等语言 |
| 📄 **双格式输出** | 知识类 → Markdown，技术类 → Jupyter Notebook |

---

## 🚀 快速开始

### 作为 Claude Code Skill 使用

```bash
/video-to-notes https://www.youtube.com/watch?v=xxx
```

### 单独运行脚本

```bash
# 安装依赖
pip install yt-dlp faster-whisper
brew install ffmpeg  # macOS

# 运行
python scripts/prepare.py "https://www.bilibili.com/video/BVxxx" -o ./output
```

---

## 📦 安装

### 系统依赖

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
choco install ffmpeg
```

### Python 依赖

```bash
pip install -r requirements.txt
```

### 验证安装

```bash
ffmpeg -version && yt-dlp --version && python3 -c "import faster_whisper; print('✅ 全部就绪')"
```

---

## 🎯 使用示例

```bash
# B 站视频（自动检测时长，调整帧率）
python scripts/prepare.py "https://www.bilibili.com/video/BVxxx" -o ./output

# YouTube 视频，只要文字不要帧
python scripts/prepare.py "https://youtube.com/watch?v=xxx" -o ./output --no-frames

# 英文视频，生成中文笔记
python scripts/prepare.py "https://youtube.com/watch?v=xxx" -o ./output --translate-to zh

# 保留下载的视频文件
python scripts/prepare.py "URL" -o ./output --keep-video

# 使用 Groq API 加速转录（比本地快 10x）
python scripts/prepare.py "URL" -o ./output --whisper-api "https://api.groq.com/openai/v1/audio/transcriptions"
```

---

## ⚙️ 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `url` | 视频 URL（必需） | - |
| `-o, --output` | 输出目录 | ./output |
| `--fps` | 帧提取率（0=根据时长自动） | 0 |
| `--similarity` | 相似帧去重阈值（0-1） | 0.80 |
| `--no-dedup` | 禁用相似帧去重 | false |
| `--no-frames` | 跳过帧提取（纯文字模式） | false |
| `--keep-video` | 保留下载的视频文件 | false |
| `--lang` | 字幕语言优先级 | zh-Hans,zh,en,ja,ko |
| `--whisper-api` | 外部 Whisper API 地址 | None |
| `--whisper-model` | 本地 Whisper 模型 | base |
| `--translate-to` | 翻译目标语言 | None |

---

## 📊 输出结构

```
output/
├── meta.json            # 视频元数据（标题、时长、平台）
├── transcript.txt       # 带时间戳的原始转录
├── transcript_clean.txt # AI 优化后的文本（去口语化、分段）
└── frames/              # 去重后的关键帧
    ├── frame_0001.jpg
    └── ...
```

---

## 🔄 工作流程

```
视频 URL
  ↓
yt-dlp 获取字幕（手动 > 自动生成）
  ↓ 无字幕
下载音频 → Whisper 本地转录
  ↓
ffmpeg 提取帧 → PSNR 相似帧去重
  ↓
AI 文本优化 + 分批并行帧分析
  ↓
生成结构化学习笔记（.md 或 .ipynb）
```

---

## 📖 示例结果

查看真实的笔记生成效果：**[video-to-notes-demo](https://github.com/Allen0497/video-to-notes-demo)**

> 基于 B 站强化学习视频（35分钟）生成的完整学习笔记，包含公式讲解、关键帧截图和背景知识补充。

---

## 🆚 与同类工具对比

| | bilibili-analyzer | AI-Video-Transcriber | **video-to-notes** |
|--|:-----------------:|:--------------------:|:------------------:|
| 类型 | Skill | Web 应用 | **Skill** |
| 平台 | 仅 B 站 | 多平台 | **30+ 平台** |
| 内容来源 | 帧 OCR | 字幕/Whisper | **字幕/Whisper + 帧** |
| 公式讲解 | ❌ | ❌ | **✅ 逐项解释** |
| 初学者友好 | ❌ | ❌ | **✅** |
| 输出格式 | 文档 | 转录文本 | **md / ipynb** |

---

## 📄 许可证

MIT License

---

> 💡 创作不易，如果本项目对你有帮助，欢迎 Star ⭐ 支持！如有引用或二次创作，请注明出处并链接到本仓库，感谢 🙏
