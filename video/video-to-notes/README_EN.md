# 🎬 video-to-notes

**English** | [中文](./README.md)

> Turn any video into structured study notes — no more manual screenshots and note-taking.

---

## 😩 Sound familiar?

- 📚 **Too many videos to watch**, nothing sticks without organized notes
- 🎓 **Students & researchers** spending hours screenshotting, copying formulas, preparing presentations
- 🌍 **Foreign language videos** with no subtitles you can understand
- 💼 **Meeting recordings** that need to be turned into documents
- 🔬 **Technical tutorials** where code and formulas flash by too fast to copy

**video-to-notes was built to solve exactly these problems.**

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🌐 **30+ Platforms** | YouTube, Bilibili, Twitter, TikTok, and more via yt-dlp |
| 📝 **Subtitle-first** | Auto-fetches platform subtitles; falls back to local Whisper |
| 🖼️ **Smart frames** | Full extraction + PSNR dedup + batch parallel analysis |
| 🧠 **AI deep-dive** | Every formula explained symbol-by-symbol with real-life analogies |
| 🔰 **Beginner-friendly** | Difficulty labels, conclusion previews, section summaries |
| 🌏 **Multi-language** | Translate notes to any language |
| 📄 **Dual output** | Knowledge → Markdown, Technical → Jupyter Notebook |

---

## 🚀 Quick Start

### As a Claude Code Skill

```bash
/video-to-notes https://www.youtube.com/watch?v=xxx
```

### Standalone Script

```bash
pip install yt-dlp faster-whisper
brew install ffmpeg  # macOS

python scripts/prepare.py "https://www.youtube.com/watch?v=xxx" -o ./output
```

---

## 📦 Installation

```bash
# macOS
brew install ffmpeg && pip install -r requirements.txt

# Ubuntu/Debian
sudo apt install ffmpeg && pip install -r requirements.txt
```

---

## 🎯 Examples

```bash
# Basic usage
python scripts/prepare.py "https://youtube.com/watch?v=xxx" -o ./output

# Text only (no frames)
python scripts/prepare.py "URL" -o ./output --no-frames

# Translate to Chinese
python scripts/prepare.py "URL" -o ./output --translate-to zh

# Keep downloaded video
python scripts/prepare.py "URL" -o ./output --keep-video

# Fast transcription via Groq API
python scripts/prepare.py "URL" -o ./output --whisper-api "https://api.groq.com/openai/v1/audio/transcriptions"
```

---

## ⚙️ Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `url` | Video URL (required) | - |
| `-o, --output` | Output directory | ./output |
| `--fps` | Frame rate (0=auto) | 0 |
| `--similarity` | Dedup threshold (0-1) | 0.80 |
| `--no-frames` | Skip frame extraction | false |
| `--keep-video` | Keep downloaded video file | false |
| `--lang` | Subtitle language priority | zh-Hans,zh,en,ja,ko |
| `--whisper-api` | External Whisper API URL | None |
| `--whisper-model` | Local Whisper model | base |
| `--translate-to` | Translation target language | None |

---

## 📊 Output

```
output/
├── meta.json            # Video metadata
├── transcript.txt       # Raw timestamped transcript
├── transcript_clean.txt # AI-cleaned text
└── frames/              # Deduplicated keyframes
```

---

## 📖 Demo

See a real example: **[video-to-notes-demo](https://github.com/Allen0497/video-to-notes-demo)**

> Full study notes generated from a 35-min Bilibili RL lecture, with formula explanations, keyframe screenshots, and background knowledge.

---

## 🆚 Comparison

| | bilibili-analyzer | AI-Video-Transcriber | **video-to-notes** |
|--|:-----------------:|:--------------------:|:------------------:|
| Type | Skill | Web App | **Skill** |
| Platforms | Bilibili only | Multi | **30+** |
| Content | Frame OCR | Subtitle/Whisper | **Subtitle/Whisper + Frames** |
| Formula explanation | ❌ | ❌ | **✅** |
| Beginner-friendly | ❌ | ❌ | **✅** |
| Output | Document | Transcript | **md / ipynb** |

---

## 📄 License

MIT License

---

> 💡 If this project helps you, a Star ⭐ would be appreciated! If you reference or build upon this work, please credit this repository. Thank you 🙏
