# Whisper Setup Guide

## Local: faster-whisper

[faster-whisper](https://github.com/SYSTRAN/faster-whisper) is a reimplementation of Whisper using CTranslate2, 4x faster than the original with lower memory usage.

### Install

```bash
pip install faster-whisper
```

### Model Selection

| Model | Size | Speed (CPU) | Accuracy | Recommended For |
|-------|------|-------------|----------|-----------------|
| `tiny` | 39M | Very fast | Low | Quick tests |
| `base` | 74M | Fast | Medium | **Default choice** |
| `small` | 244M | Medium | Good | Better accuracy |
| `medium` | 769M | Slow | Very good | High quality |
| `large-v3` | 1.5G | Very slow | Best | Maximum accuracy |

### Usage

```bash
# Default (base model, CPU)
python scripts/prepare.py "URL" -o ./output

# Better accuracy
python scripts/prepare.py "URL" -o ./output --whisper-model small

# Best accuracy (slow on CPU)
python scripts/prepare.py "URL" -o ./output --whisper-model large-v3
```

### GPU Acceleration

If you have an NVIDIA GPU with CUDA:

```bash
pip install faster-whisper[cuda]
```

The script auto-detects GPU availability.

## External API: Groq Whisper

[Groq](https://groq.com/) offers a fast Whisper API. Much faster than local CPU transcription.

### Setup

1. Get an API key from https://console.groq.com/
2. Set environment variable:
   ```bash
   export GROQ_API_KEY="gsk_..."
   ```

### Usage

```bash
python scripts/prepare.py "URL" -o ./output \
  --whisper-api "https://api.groq.com/openai/v1/audio/transcriptions"
```

### Other Compatible APIs

Any OpenAI-compatible Whisper API works:

```bash
# OpenAI
--whisper-api "https://api.openai.com/v1/audio/transcriptions"

# Local (e.g., whisper.cpp server)
--whisper-api "http://localhost:8080/v1/audio/transcriptions"
```
