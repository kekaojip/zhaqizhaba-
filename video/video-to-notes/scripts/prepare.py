#!/usr/bin/env python3
"""
video-to-notes prepare script
Downloads video, fetches subtitles/transcribes audio, extracts and deduplicates frames.

Usage:
    python prepare.py <url> -o <output_dir> [options]

Examples:
    python prepare.py "https://www.youtube.com/watch?v=xxx" -o ./output
    python prepare.py "https://www.bilibili.com/video/BVxxx" -o ./output --fps 0.5
    python prepare.py "https://www.youtube.com/watch?v=xxx" -o ./output --no-frames
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Video info
# ---------------------------------------------------------------------------

def get_video_info(url: str) -> dict:
    """Fetch video metadata via yt-dlp."""
    result = subprocess.run(
        ["yt-dlp", "--dump-json", "--no-download", url],
        capture_output=True, text=True, check=True,
    )
    info = json.loads(result.stdout)
    return {
        "title": info.get("title", "Unknown"),
        "duration": info.get("duration", 0),
        "uploader": info.get("uploader", "Unknown"),
        "platform": info.get("extractor", "unknown"),
        "language": info.get("language", ""),
        "url": url,
    }

# ---------------------------------------------------------------------------
# Subtitles
# ---------------------------------------------------------------------------

def get_subtitles(url: str, out_dir: Path, langs: str = "zh-Hans,zh,en,ja,ko") -> Optional[Path]:
    """Try to download subtitles. Prefer manual subs over auto-generated."""
    subprocess.run(
        [
            "yt-dlp",
            "--write-subs", "--write-auto-subs",
            "--sub-langs", langs,
            "--sub-format", "vtt/srt/best",
            "--skip-download",
            "-o", str(out_dir / "subs.%(ext)s"),
            url,
        ],
        capture_output=True, check=False,
    )
    # Priority: manual > auto, language order follows --sub-langs
    for pattern in ["subs.*.vtt", "subs.*.srt", "*.vtt", "*.srt"]:
        files = sorted(out_dir.glob(pattern))
        if files:
            return files[0]
    return None


def parse_subtitle(sub_path: Path, out_dir: Path) -> Path:
    """Parse VTT/SRT subtitle file into plain text with timestamps."""
    transcript_path = out_dir / "transcript.txt"
    lines = sub_path.read_text(encoding="utf-8", errors="replace").splitlines()
    segments = []
    current_time = ""

    for line in lines:
        line = line.strip()
        # Skip VTT header and empty lines
        if not line or line.startswith("WEBVTT") or line.startswith("NOTE"):
            continue
        # SRT sequence numbers
        if re.match(r"^\d+$", line):
            continue
        # Timestamp lines
        ts_match = re.match(r"(\d{2}:\d{2}:\d{2})[.,]\d+\s*-->", line)
        if ts_match:
            current_time = ts_match.group(1)
            continue
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", line).strip()
        if text and current_time:
            segments.append(f"[{current_time}] {text}")

    # Deduplicate consecutive identical lines (common in auto-subs)
    deduped = []
    for seg in segments:
        if not deduped or seg.split("] ", 1)[-1] != deduped[-1].split("] ", 1)[-1]:
            deduped.append(seg)

    transcript_path.write_text("\n".join(deduped), encoding="utf-8")
    return transcript_path

# ---------------------------------------------------------------------------
# Audio download & Whisper transcription
# ---------------------------------------------------------------------------

def download_audio(url: str, out_dir: Path) -> Path:
    """Download audio only for Whisper transcription."""
    audio_path = out_dir / "audio.m4a"
    subprocess.run(
        [
            "yt-dlp", "-x", "--audio-format", "m4a",
            "--audio-quality", "5",
            "-o", str(audio_path),
            url,
        ],
        check=True,
    )
    return audio_path


def transcribe_whisper(audio_path: Path, out_dir: Path,
                       model: str = "base", api: Optional[str] = None) -> Path:
    """Transcribe audio using faster-whisper (local) or external API."""
    transcript_path = out_dir / "transcript.txt"

    if api:
        # External Whisper API (e.g., Groq)
        import requests
        with open(audio_path, "rb") as f:
            resp = requests.post(
                api,
                files={"file": f},
                data={"model": "whisper-large-v3", "response_format": "verbose_json"},
            )
        resp.raise_for_status()
        data = resp.json()
        lines = []
        for seg in data.get("segments", []):
            ts = f"{int(seg['start']//3600):02d}:{int(seg['start']%3600//60):02d}:{int(seg['start']%60):02d}"
            lines.append(f"[{ts}] {seg['text'].strip()}")
        transcript_path.write_text("\n".join(lines), encoding="utf-8")
    else:
        # Local faster-whisper
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            print("[ERROR] faster-whisper not installed. Run: pip install faster-whisper")
            sys.exit(1)

        print(f"[INFO] Loading Whisper model '{model}' (this may take a moment)...")
        wmodel = WhisperModel(model, device="cpu", compute_type="int8")
        segments, info = wmodel.transcribe(str(audio_path), beam_size=5)
        print(f"[INFO] Detected language: {info.language} (prob={info.language_probability:.2f})")

        lines = []
        for seg in segments:
            ts = f"{int(seg.start//3600):02d}:{int(seg.start%3600//60):02d}:{int(seg.start%60):02d}"
            lines.append(f"[{ts}] {seg.text.strip()}")
        transcript_path.write_text("\n".join(lines), encoding="utf-8")

    return transcript_path

# ---------------------------------------------------------------------------
# Video download & frame extraction
# ---------------------------------------------------------------------------

def download_video(url: str, out_dir: Path) -> Path:
    """Download video (720p max) for frame extraction."""
    video_path = out_dir / "video.mp4"
    subprocess.run(
        [
            "yt-dlp",
            "-f", "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "--merge-output-format", "mp4",
            "-o", str(video_path),
            url,
        ],
        check=True,
    )
    return video_path


def auto_fps(duration: int) -> float:
    """Choose fps based on video duration."""
    if duration <= 600:       # ≤10 min
        return 1.0
    elif duration <= 1800:    # ≤30 min
        return 0.5
    else:                     # >30 min
        return 0.2


def extract_frames(video_path: Path, out_dir: Path, fps: float) -> Path:
    """Extract all frames at given fps."""
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-i", str(video_path),
            "-vf", f"fps={fps}",
            "-q:v", "2", "-y",
            str(frames_dir / "frame_%04d.jpg"),
        ],
        capture_output=True, check=True,
    )
    count = len(list(frames_dir.glob("frame_*.jpg")))
    print(f"[OK] Extracted {count} frames (fps={fps})")
    return frames_dir


def calculate_similarity(frame_a: Path, frame_b: Path) -> float:
    """Calculate PSNR-based similarity between two adjacent frames."""
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-i", str(frame_a), "-i", str(frame_b),
                "-lavfi", "psnr", "-f", "null", "-",
            ],
            capture_output=True, text=True, check=False,
        )
        stderr = result.stderr
        match = re.search(r"average:(\d+\.?\d*)", stderr)
        if match:
            psnr = float(match.group(1))
            # Convert PSNR to 0-1 similarity (higher PSNR = more similar)
            if psnr == float("inf"):
                return 1.0
            return min(1.0, psnr / 50.0)
    except Exception:
        pass
    return 0.0


def dedup_frames(frames_dir: Path, threshold: float = 0.80) -> int:
    """Remove similar adjacent frames, renumber remaining ones."""
    frames = sorted(frames_dir.glob("frame_*.jpg"))
    if len(frames) <= 1:
        return len(frames)

    keep = [frames[0]]
    for i in range(1, len(frames)):
        sim = calculate_similarity(frames[i - 1], frames[i])
        if sim < threshold:
            keep.append(frames[i])

    removed = len(frames) - len(keep)
    print(f"[INFO] Dedup: {len(frames)} → {len(keep)} frames ({removed} removed)")

    # Remove non-kept frames
    keep_set = set(str(f) for f in keep)
    for f in frames:
        if str(f) not in keep_set:
            f.unlink()

    # Renumber sequentially
    remaining = sorted(frames_dir.glob("frame_*.jpg"))
    # Use temp names to avoid collision
    for i, f in enumerate(remaining):
        f.rename(frames_dir / f"_tmp_{i:04d}.jpg")
    for i, f in enumerate(sorted(frames_dir.glob("_tmp_*.jpg"))):
        f.rename(frames_dir / f"frame_{i+1:04d}.jpg")

    return len(keep)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="video-to-notes: Download video, get transcript, extract frames"
    )
    parser.add_argument("url", help="Video URL (YouTube, Bilibili, etc.)")
    parser.add_argument("-o", "--output", default="./output", help="Output directory")
    parser.add_argument("--fps", type=float, default=0, help="Frame extraction rate (0=auto)")
    parser.add_argument("--similarity", type=float, default=0.80, help="Dedup threshold (0-1)")
    parser.add_argument("--no-dedup", action="store_true", help="Skip frame deduplication")
    parser.add_argument("--no-frames", action="store_true", help="Skip frame extraction")
    parser.add_argument("--lang", default="zh-Hans,zh,en,ja,ko", help="Subtitle language priority")
    parser.add_argument("--whisper-api", default=None, help="External Whisper API URL")
    parser.add_argument("--whisper-model", default="base", help="Local Whisper model name")
    parser.add_argument("--keep-video", action="store_true", help="Keep downloaded video file after frame extraction")
    parser.add_argument("--translate-to", default=None, help="Target language for translation")
    args = parser.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Video info
    print("[INFO] Fetching video info...")
    meta = get_video_info(args.url)
    print(f"[INFO] Title: {meta['title']}")
    print(f"[INFO] Duration: {meta['duration']}s | Platform: {meta['platform']}")

    # Step 2: Subtitles (priority) or Whisper transcription
    print("\n[INFO] Trying to get subtitles...")
    sub_path = get_subtitles(args.url, out_dir, args.lang)

    if sub_path:
        print(f"[OK] Subtitles found: {sub_path.name}")
        transcript_path = parse_subtitle(sub_path, out_dir)
        meta["source"] = "subtitle"
    else:
        print("[INFO] No subtitles available. Downloading audio for Whisper...")
        audio_path = download_audio(args.url, out_dir)
        print("[INFO] Transcribing with Whisper (this may take a while)...")
        transcript_path = transcribe_whisper(
            audio_path, out_dir,
            model=args.whisper_model, api=args.whisper_api,
        )
        meta["source"] = "whisper"
        audio_path.unlink(missing_ok=True)

    line_count = len(transcript_path.read_text().splitlines())
    print(f"[OK] Transcript: {transcript_path} ({line_count} lines)")

    if args.translate_to:
        meta["translate_to"] = args.translate_to

    # Step 3: Frame extraction (optional)
    frame_count = 0
    if not args.no_frames:
        print("\n[INFO] Downloading video for frame extraction...")
        try:
            video_path = download_video(args.url, out_dir)
        except subprocess.CalledProcessError:
            print("[WARN] Video download failed, skipping frames")
            video_path = None

        if video_path and video_path.exists():
            fps = args.fps if args.fps > 0 else auto_fps(meta["duration"])
            print(f"[INFO] Extracting frames (fps={fps})...")
            frames_dir = extract_frames(video_path, out_dir, fps)

            if not args.no_dedup:
                print(f"[INFO] Deduplicating frames (threshold={args.similarity})...")
                frame_count = dedup_frames(frames_dir, args.similarity)
            else:
                frame_count = len(list(frames_dir.glob("frame_*.jpg")))

            if not args.keep_video:
                video_path.unlink(missing_ok=True)
            else:
                print(f"[OK] Video kept: {video_path}")
            print(f"[OK] Frames: {frame_count} (after dedup)")

    # Save metadata
    meta["frame_count"] = frame_count
    (out_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Summary
    print(f"\n{'='*50}")
    print(f"[OK] Done!")
    print(f"  Transcript: {transcript_path}")
    if frame_count > 0:
        print(f"  Frames:     {out_dir}/frames/ ({frame_count} frames)")
    print(f"  Meta:       {out_dir}/meta.json")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
