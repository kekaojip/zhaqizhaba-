# Installation Guide

## System Dependencies

### FFmpeg (Required)

FFmpeg is used for frame extraction and audio processing.

#### macOS

```bash
brew install ffmpeg
```

#### Ubuntu/Debian

```bash
sudo apt update
sudo apt install ffmpeg
```

#### CentOS/RHEL

```bash
sudo yum install epel-release
sudo yum install ffmpeg
```

#### Windows

```powershell
# Chocolatey
choco install ffmpeg

# Or Scoop
scoop install ffmpeg

# Or download manually: https://ffmpeg.org/download.html
```

#### Verify

```bash
ffmpeg -version
```

### Python 3.9+ (Required)

```bash
python3 --version
# Should be 3.9 or higher. 3.11+ recommended.
```

### yt-dlp (Required)

```bash
pip install yt-dlp

# Verify
yt-dlp --version
```

### faster-whisper (Required for no-subtitle videos)

```bash
pip install faster-whisper

# Verify
python3 -c "from faster_whisper import WhisperModel; print('OK')"
```

## All-in-One Install

```bash
# macOS
brew install ffmpeg
pip install yt-dlp faster-whisper requests

# Ubuntu/Debian
sudo apt install ffmpeg
pip install yt-dlp faster-whisper requests
```

## Verify Everything

```bash
ffmpeg -version && \
yt-dlp --version && \
python3 -c "import faster_whisper; print('faster-whisper OK')" && \
echo "All dependencies installed!"
```
