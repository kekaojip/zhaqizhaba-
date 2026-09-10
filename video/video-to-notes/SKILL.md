---
name: video-to-notes
description: 从任意视频平台自动生成结构化学习笔记。字幕优先，Whisper 兜底，关键帧辅助视觉内容分析。支持 AI 文本优化、多语言摘要和条件式翻译。
metadata:
  short-description: 多平台视频笔记生成 Skill
source:
  - name: yt-dlp
    repository: https://github.com/yt-dlp/yt-dlp
    documentation: https://github.com/yt-dlp/yt-dlp#readme
    license: Unlicense
  - name: faster-whisper
    repository: https://github.com/SYSTRAN/faster-whisper
    license: MIT
  - name: FFmpeg
    repository: https://github.com/FFmpeg/FFmpeg
    documentation: https://ffmpeg.org/ffmpeg.html
    license: LGPL/GPL
---

# Video to Notes

## Description

多平台视频学习笔记生成工具。提供视频 URL 后，自动获取字幕或转录音频，提取关键帧，最终生成**结构化的学习笔记**。

**核心特点**:
- **多平台支持**：通过 yt-dlp 支持 YouTube、Bilibili、Twitter、TikTok 等 1000+ 平台
- **字幕优先**：优先获取平台字幕（手动 > 自动生成），无字幕时用 Whisper 本地转录
- **关键帧辅助**：全量帧提取 + 相似帧去重，补充 PPT/代码/公式等视觉内容
- **AI 文本处理**：智能分段、去口语化、多语言摘要、条件式翻译
- **双格式输出**：知识类 → Markdown，技术类 → Jupyter Notebook

## Installation

### 系统依赖

**FFmpeg**（必需）:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
choco install ffmpeg
```

**Python 3.9+**（必需）:
```bash
python3 --version
```

### Python 依赖

```bash
pip install yt-dlp faster-whisper
```

### 验证安装

```bash
ffmpeg -version
yt-dlp --version
python3 -c "import faster_whisper; print('OK')"
```

## Trigger

- `/video-to-notes` 命令
- 用户请求从视频生成笔记
- 用户提供视频链接并要求分析/总结/做笔记

## Provided Script

本 skill 提供 `scripts/prepare.py` 脚本用于视频预处理。

### 使用方法

```bash
# 基本用法
python scripts/prepare.py "<视频URL>" -o <输出目录>

# B 站视频
python scripts/prepare.py "https://www.bilibili.com/video/BVxxx" -o ./output

# YouTube 长视频（自动降低帧率）
python scripts/prepare.py "https://www.youtube.com/watch?v=xxx" -o ./output

# 只要转录文本，不提取帧
python scripts/prepare.py "<URL>" -o ./output --no-frames

# 指定 Whisper API
python scripts/prepare.py "<URL>" -o ./output --whisper-api "https://api.groq.com/openai/v1/audio/transcriptions"
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `url` | 视频 URL（必需） | - |
| `-o, --output` | 输出目录 | ./output |
| `--fps` | 帧提取率（0=根据时长自动选择） | 0 (auto) |
| `--similarity` | 相似帧去重阈值（0-1） | 0.80 |
| `--no-dedup` | 禁用相似帧去重 | false |
| `--no-frames` | 跳过帧提取 | false |
| `--lang` | 字幕语言优先级 | zh-Hans,zh,en,ja,ko |
| `--whisper-api` | 外部 Whisper API 地址 | None（用本地） |
| `--whisper-model` | 本地 Whisper 模型 | base |
| `--translate-to` | 翻译目标语言 | None |

### 自动帧率选择

| 视频时长 | fps | 说明 |
|---------|-----|------|
| ≤10 分钟 | 1.0 | 每秒 1 帧 |
| 10-30 分钟 | 0.5 | 每 2 秒 1 帧 |
| >30 分钟 | 0.2 | 每 5 秒 1 帧 |

### 相似帧去重

使用 ffmpeg PSNR 算法比较相邻帧，去除相似度超过阈值的重复帧，去重后自动重新编号。

### 输出结构

```
<输出目录>/
├── meta.json           # 视频元数据
├── transcript.txt      # 带时间戳的转录文本
└── frames/             # 去重后的帧图片
    ├── frame_0001.jpg
    ├── frame_0002.jpg
    └── ...
```

## Workflow (Prompt)

你是一个视频学习笔记生成助手。当用户提供视频链接时，按以下步骤执行：

### Step 1: 运行 prepare.py

```bash
python skills/tools/video-to-notes/scripts/prepare.py "<视频URL>" -o <输出目录>
```

脚本自动完成：字幕获取 → (无字幕时) Whisper 转录 → 帧提取 → 相似帧去重。

检查输出：
- `meta.json`：确认视频标题、时长、来源
- `transcript.txt`：确认转录文本可用
- `frames/`：确认帧图片数量

### Step 2: AI 文本处理

读取 `transcript.txt`，进行以下处理：

1. **智能分段**：根据内容主题将连续文本分成逻辑段落
2. **去口语化**：移除"嗯"、"那个"、"就是说"等口语填充词
3. **错别字修正**：修正语音识别常见错误
4. **语言检测**：如果 `meta.json` 中有 `translate_to` 字段，将内容翻译为目标语言

将处理后的文本保存为 `transcript_clean.txt`。

### Step 3: 分 batch 并行分析帧

如果 `frames/` 目录有图片，使用 **Task 工具**分批并行分析。

**分批策略**（根据总帧数动态计算）：

| 总帧数 | 分批数量 | 每批帧数 |
|--------|---------|---------|
| 1-30 | 1 批 | 全部 |
| 31-60 | 2 批 | ~15-30 张/批 |
| 61-120 | 3 批 | ~20-40 张/批 |
| 121-200 | 4 批 | ~30-50 张/批 |
| 200+ | 5 批 | 平均分配 |

**Task Prompt 模板**:

```
读取并分析 <输出目录>/frames/ 目录下的 frame_0001.jpg 到 frame_0020.jpg（共20张图片）。

对每张图片，详细记录：
1. **帧号**: frame_xxxx.jpg
2. **场景类型**: PPT/代码编辑器/终端/浏览器/白板/图表/其他
3. **文字内容**: 完整转录屏幕上的所有文字、代码、公式
4. **视觉要点**: 图表结构、代码逻辑、公式含义、关键截图

输出格式：
## frame_0001.jpg
- 类型: [场景类型]
- 文字: [完整文字/代码/公式]
- 要点: [视觉要点]
```

### Step 4: 整合生成笔记

将优化后的转录文本（主）+ 帧分析结果（辅）整合，生成学习笔记。

**判断视频类型**:
- 技术/编程类 → 生成 `.ipynb`（含代码块和可视化）
- 知识/教程类 → 生成 `.md`

**整合原则**:
1. 以转录文本为骨架，**按主题而非时间线**组织
2. 关键帧图片只在内容直接相关时插入
3. 代码/公式优先从帧图片获取（比转录更准确）
4. 图片引用格式：`![frame_xxxx: 描述](./frames/frame_xxxx.jpg)`
5. 代码块标注来源：`<!-- 来自 frame_xxxx -->`

**公式讲解与知识补充（重要！）**:

笔记的目标读者是**初学者**，不是领域专家。对于每一个出现的公式或专业概念，必须做到：

1. **公式拆解**：不要只列出公式，必须逐项解释每个符号的含义和直觉
   ```
   ❌ 错误示例：
   $$V_\pi(s) = \mathbb{E}[R_t + \gamma V_\pi(s')]$$

   ✅ 正确示例：
   $$V_\pi(s) = \mathbb{E}[R_t + \gamma V_\pi(s')]$$
   - $V_\pi(s)$：状态 $s$ 的价值，即"从这个状态出发，按策略 $\pi$ 走下去，平均能拿多少总奖励"
   - $R_t$：当前这一步立刻拿到的奖励（即时奖励）
   - $\gamma$：折扣因子（0到1之间），表示"未来的奖励打几折"，γ=0.99 意味着 100 步后的奖励只值现在的 37%
   - $V_\pi(s')$：下一个状态的价值
   - 整体含义：当前状态的价值 = 现在拿到的奖励 + 打折后的未来价值
   ```

2. **生活化类比**：用日常生活的例子帮助理解抽象概念
   - 折扣因子 → "今天的100块比明年的100块更值钱"
   - 策略 → "下棋时的习惯/风格"
   - 优势函数 → "这步棋比平均水平好多少"
   - 重要性采样 → "用旧的问卷调查结果估算新产品的满意度"

3. **背景知识补充**：视频中可能一笔带过或默认观众已知的知识，需要主动补充
   - 数学前置知识（期望、概率分布、梯度、链式法则等）
   - 领域背景（为什么这个问题重要、历史发展脉络）
   - 算法之间的关系和演进动机（"为什么有了 A 还需要 B"）

4. **难度标注**：对于较难的推导，标注难度并提供跳过建议
   ```
   > ⚠️ 以下推导较为数学化，初学者可以先跳过，只需记住结论：...
   ```

5. **总结框**：每个章节末尾用简洁的总结框概括核心要点
   ```
   > 📌 本节要点：
   > - xxx
   > - xxx
   ```

**可选**：如果用户要求，生成多语言摘要（中/英/日等）。

## Output Format

### 知识文档类（Markdown）

```markdown
# {主题}

## 概述
{主题背景，为什么重要，这个领域的发展脉络}

## 前置知识
{读者可能需要的数学/领域基础，简要介绍}

## {章节1}
{内容，基于转录文本重组}

### {关键公式}
$$公式$$
- 逐项解释每个符号
- 生活化类比
- 直觉理解

> 📌 本节要点：
> - 要点1
> - 要点2

![frame_xxxx: 图片实际内容描述](./frames/frame_xxxx.jpg)

## {章节2}
{内容}

> ⚠️ 以下推导较为数学化，初学者可以先跳过，只需记住结论：...

{详细推导}

> 📌 本节要点：
> - 要点1

## 核心要点总结
- 要点1
- 要点2

## 延伸阅读
{相关论文、教程、资源链接}
```

### 技术教程类（Jupyter Notebook）

每个章节包含：
- Markdown cell：概念讲解（来自转录文本）+ 公式逐项解释 + 生活化类比
- Markdown cell：公式推导（LaTeX 格式），难度较高的推导标注 ⚠️ 并提供结论速览
- Code cell：代码实现（来自帧分析或转录），附带详细注释
- Markdown cell：📌 本节要点总结框

### 图片插入规范

| 规则 | 说明 |
|------|------|
| 帧号必须标注 | `![frame_0015: 描述](./frames/frame_0015.jpg)` |
| 描述必须准确 | 描述图片的实际内容 |
| 内容必须匹配 | 图片上下文必须与图片内容相关 |
| 代码标注来源 | `<!-- 代码来自 frame_0025 -->` |
| 不要乱插图 | 没有合适的图就不插 |

## Quality Checklist

### 内容质量
- [ ] 内容按主题重组，不是时间线流水账
- [ ] 章节结构清晰，有逻辑顺序
- [ ] 不看视频也能理解全部内容
- [ ] 口语化表达已清理
- [ ] 包含总结和核心要点

### 公式与知识讲解
- [ ] 每个公式都有逐项符号解释
- [ ] 抽象概念配有生活化类比或直觉解释
- [ ] 视频中一笔带过的前置知识已补充（数学基础、领域背景）
- [ ] 算法之间的演进动机已说明（"为什么有了 A 还需要 B"）
- [ ] 较难的推导标注了难度，并提供结论速览
- [ ] 每个章节末尾有 📌 要点总结框

### 图文对应
- [ ] 每张图片标注了帧号
- [ ] 图片描述准确反映实际内容
- [ ] 图片与上下文直接相关
- [ ] 代码块标注了来源帧号

### 翻译质量（如适用）
- [ ] 专业术语翻译准确
- [ ] 保留原文关键术语（括号标注）
- [ ] 语句通顺自然

## Tags

`video`, `notes`, `transcription`, `subtitle`, `whisper`, `yt-dlp`, `ffmpeg`, `multi-platform`, `ai`, `translation`

## Compatibility

- Claude Code: Yes
- Codex: Yes
