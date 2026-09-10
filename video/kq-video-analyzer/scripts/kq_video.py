#!/usr/bin/env python3
"""
kq-video-analyzer

One entry point for:
- resolving pasted share text or direct video URLs
- downloading video
- quick Gemini video summarization
- deep preparation via subtitles / Whisper / keyframes
- download-only mode

The script prepares reliable artifacts. In deep mode, the host agent should read
transcript.txt and frames/ and produce the final analysis.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

URL_RE = re.compile(r"https?://[^\s<>\]\[\"']+")

DEEP_HINTS = (
    "深度", "拆解", "逐段", "逐帧", "关键帧", "字幕", "转录", "教程",
    "笔记", "代码", "公式", "画面", "镜头", "分析视频", "deep", "frame",
    "transcript", "notes", "tutorial", "code", "formula",
)

DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")


def fail(message: str, code: int = 1) -> None:
    print(f"[ERROR] {message}", file=sys.stderr)
    raise SystemExit(code)


def extract_first_url(source: str) -> str:
    if source.startswith(("http://", "https://")):
        return source
    match = URL_RE.search(source)
    if not match:
        fail("No http/https URL found in the supplied text.")
    return match.group(0).rstrip(".,;:!?，。；：！？")


def sanitize_name(value: str, max_len: int = 90) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    value = re.sub(r"\s+", "_", value.strip()).strip("._")
    return (value[:max_len] or "video")


def run(cmd: list[str], *, capture: bool = False, check: bool = True) -> subprocess.CompletedProcess:
    print("[CMD]", " ".join(cmd))
    return subprocess.run(
        cmd,
        text=True,
        capture_output=capture,
        check=check,
    )


def ensure_runtime() -> None:
    try:
        import yt_dlp  # noqa: F401
    except ImportError:
        fail("yt-dlp is missing. Install requirements before running.")
    if shutil.which("ffmpeg") is None:
        fail("ffmpeg is missing from PATH.")


def auth_args(args: argparse.Namespace) -> list[str]:
    extra: list[str] = []
    if args.cookies_from_browser:
        extra += ["--cookies-from-browser", args.cookies_from_browser]
    if args.cookies_file:
        extra += ["--cookies", args.cookies_file]
    if args.user_agent:
        extra += ["--user-agent", args.user_agent]
    if args.referer:
        extra += ["--referer", args.referer]
    return extra


def ytdlp_cmd(args: argparse.Namespace) -> list[str]:
    return [sys.executable, "-m", "yt_dlp", "--no-playlist", *auth_args(args)]


def get_metadata(url: str, args: argparse.Namespace) -> dict:
    result = run(
        [*ytdlp_cmd(args), "--dump-single-json", "--skip-download", url],
        capture=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        fail(
            "yt-dlp could not resolve this URL. "
            "If the platform requires login, retry with --cookies-from-browser or --cookies-file."
        )
    try:
        info = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        fail(f"yt-dlp returned invalid metadata JSON: {exc}")
    return {
        "id": str(info.get("id") or ""),
        "title": info.get("title") or info.get("fulltitle") or "video",
        "uploader": info.get("uploader") or info.get("channel") or "",
        "duration": info.get("duration") or 0,
        "extractor": info.get("extractor_key") or info.get("extractor") or "",
        "webpage_url": info.get("webpage_url") or url,
        "description": info.get("description") or "",
    }


def choose_mode(requested: str, goal: str) -> str:
    if requested != "auto":
        return requested
    goal_l = goal.lower()
    if any(hint.lower() in goal_l for hint in DEEP_HINTS):
        return "deep"
    if os.getenv("GEMINI_API_KEY"):
        return "quick"
    return "deep"


def download_video(url: str, out_dir: Path, args: argparse.Namespace, *, max_height: int = 1080) -> Path:
    template = str(out_dir / "video.%(ext)s")
    fmt = (
        f"bestvideo[height<={max_height}][ext=mp4]+bestaudio[ext=m4a]/"
        f"bestvideo[height<={max_height}]+bestaudio/"
        f"best[height<={max_height}]/best"
    )
    result = run(
        [
            *ytdlp_cmd(args),
            "-f", fmt,
            "--merge-output-format", "mp4",
            "-o", template,
            url,
        ],
        check=False,
    )
    if result.returncode != 0:
        fail("Video download failed.")
    candidates = sorted(out_dir.glob("video.*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        fail("yt-dlp reported success but no video file was produced.")
    return candidates[0]


def try_subtitles(url: str, out_dir: Path, args: argparse.Namespace) -> Optional[Path]:
    for old in out_dir.glob("subtitle*.*"):
        old.unlink(missing_ok=True)

    result = run(
        [
            *ytdlp_cmd(args),
            "--write-subs",
            "--write-auto-subs",
            "--sub-langs", args.lang,
            "--sub-format", "vtt/srt/best",
            "--skip-download",
            "-o", str(out_dir / "subtitle.%(ext)s"),
            url,
        ],
        check=False,
    )
    if result.returncode != 0:
        return None

    candidates = []
    for pattern in ("subtitle*.vtt", "subtitle*.srt", "*.vtt", "*.srt"):
        candidates.extend(out_dir.glob(pattern))
    candidates = sorted(set(candidates))
    return candidates[0] if candidates else None


def parse_subtitle(path: Path, out_path: Path) -> None:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    output: list[str] = []
    current_ts = ""
    last_text = ""

    for raw in lines:
        line = raw.strip()
        if not line or line == "WEBVTT" or line.startswith(("NOTE", "Kind:", "Language:")):
            continue
        if re.fullmatch(r"\d+", line):
            continue

        ts_match = re.match(
            r"(?:(\d{2}):)?(\d{2}):(\d{2})[.,]\d+\s*-->",
            line,
        )
        if ts_match:
            hh = ts_match.group(1) or "00"
            current_ts = f"{hh}:{ts_match.group(2)}:{ts_match.group(3)}"
            continue

        text = re.sub(r"<[^>]+>", "", line)
        text = re.sub(r"\s+", " ", text).strip()
        if text and text != last_text:
            output.append(f"[{current_ts}] {text}" if current_ts else text)
            last_text = text

    out_path.write_text("\n".join(output), encoding="utf-8")


def download_audio(url: str, out_dir: Path, args: argparse.Namespace) -> Path:
    target = out_dir / "audio.m4a"
    result = run(
        [
            *ytdlp_cmd(args),
            "-x",
            "--audio-format", "m4a",
            "--audio-quality", "5",
            "-o", str(target),
            url,
        ],
        check=False,
    )
    if result.returncode != 0 or not target.exists():
        fail("Audio download failed for Whisper fallback.")
    return target


def pick_whisper_device(requested: str) -> tuple[str, str]:
    if requested in {"cpu", "cuda"}:
        return (requested, "int8" if requested == "cpu" else "float16")
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() > 0:
            return ("cuda", "float16")
    except Exception:
        pass
    return ("cpu", "int8")


def transcribe_local(audio_path: Path, transcript_path: Path, args: argparse.Namespace) -> None:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        fail("faster-whisper is missing and no usable subtitles were found.")

    device, compute_type = pick_whisper_device(args.device)
    print(f"[INFO] Whisper device={device} compute_type={compute_type} model={args.whisper_model}")
    model = WhisperModel(args.whisper_model, device=device, compute_type=compute_type)
    segments, info = model.transcribe(str(audio_path), beam_size=5)
    print(f"[INFO] Whisper language={info.language} probability={info.language_probability:.3f}")

    lines = []
    for seg in segments:
        seconds = int(seg.start)
        ts = f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"
        lines.append(f"[{ts}] {seg.text.strip()}")
    transcript_path.write_text("\n".join(lines), encoding="utf-8")


def transcribe_external(audio_path: Path, transcript_path: Path, args: argparse.Namespace) -> None:
    try:
        import requests
    except ImportError:
        fail("requests is required for --whisper-api.")

    api_key = (
        args.whisper_api_key
        or os.getenv("WHISPER_API_KEY")
        or os.getenv("GROQ_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    with audio_path.open("rb") as f:
        response = requests.post(
            args.whisper_api,
            headers=headers,
            files={"file": (audio_path.name, f, "audio/mp4")},
            data={
                "model": args.whisper_api_model,
                "response_format": "verbose_json",
            },
            timeout=args.http_timeout,
        )
    response.raise_for_status()
    data = response.json()

    lines = []
    for seg in data.get("segments", []):
        seconds = int(seg.get("start", 0))
        ts = f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"
        text = str(seg.get("text", "")).strip()
        if text:
            lines.append(f"[{ts}] {text}")

    if not lines and data.get("text"):
        lines = [str(data["text"]).strip()]
    transcript_path.write_text("\n".join(lines), encoding="utf-8")


def prepare_transcript(url: str, out_dir: Path, args: argparse.Namespace) -> tuple[Path, str]:
    transcript = out_dir / "transcript.txt"
    subtitle = try_subtitles(url, out_dir, args)
    if subtitle:
        parse_subtitle(subtitle, transcript)
        if transcript.exists() and transcript.stat().st_size > 0:
            return transcript, "subtitle"

    audio = download_audio(url, out_dir, args)
    try:
        if args.whisper_api:
            transcribe_external(audio, transcript, args)
        else:
            transcribe_local(audio, transcript, args)
    finally:
        if not args.keep_audio:
            audio.unlink(missing_ok=True)
    return transcript, "whisper_api" if args.whisper_api else "whisper_local"


def frame_interval(duration: float) -> int:
    if duration <= 10 * 60:
        return 2
    if duration <= 30 * 60:
        return 4
    if duration <= 60 * 60:
        return 6
    return 10


def extract_frames(video_path: Path, frames_dir: Path, duration: float, args: argparse.Namespace) -> int:
    frames_dir.mkdir(parents=True, exist_ok=True)
    interval = args.frame_interval or frame_interval(duration)
    vf = f"fps=1/{interval}"
    if args.dedup_frames:
        vf += ",mpdecimate"
    result = run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "error",
            "-i", str(video_path),
            "-vf", vf,
            "-q:v", "3",
            "-y",
            str(frames_dir / "frame_%05d.jpg"),
        ],
        check=False,
    )
    if result.returncode != 0:
        fail("ffmpeg frame extraction failed.")
    return len(list(frames_dir.glob("frame_*.jpg")))


def quick_summary(video_path: Path, out_dir: Path, metadata: dict, args: argparse.Namespace) -> Path:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        fail("Quick mode requires GEMINI_API_KEY.")

    try:
        from google import genai
    except ImportError:
        fail("google-genai is missing. Install requirements before quick mode.")

    client = genai.Client(api_key=api_key)
    uploaded = client.files.upload(
        file=str(video_path),
        config={"mime_type": "video/mp4", "display_name": video_path.stem},
    )

    deadline = time.time() + args.gemini_timeout
    while True:
        current = client.files.get(name=uploaded.name)
        state = current.state.name if hasattr(current.state, "name") else str(current.state)
        if state == "ACTIVE":
            uploaded = current
            break
        if state == "FAILED":
            fail("Gemini Files API marked the upload as FAILED.")
        if time.time() >= deadline:
            fail("Gemini video processing timed out.")
        time.sleep(4)

    goal = args.goal.strip()
    prompt = (
        "Analyze this video based on its actual audio and visuals. "
        "Do not infer content from comments or page metadata. "
        "Reply in the video's primary language unless the user asks otherwise. "
        "Give: 1) concise summary, 2) key points, 3) important visual evidence, "
        "4) uncertain or unreadable parts."
    )
    if goal:
        prompt += f"\nUser goal: {goal}"

    try:
        response = client.models.generate_content(
            model=args.gemini_model,
            contents=[uploaded, prompt],
        )
        summary = response.text or ""
    finally:
        try:
            client.files.delete(name=uploaded.name)
        except Exception:
            pass

    path = out_dir / "summary.md"
    header = f"# {metadata.get('title', 'Video')}\n\n"
    path.write_text(header + summary.strip() + "\n", encoding="utf-8")
    return path


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Unified multi-platform video analyzer")
    parser.add_argument("source", help="Direct URL or pasted share text containing a URL")
    parser.add_argument("-o", "--output", default="./output")
    parser.add_argument("--mode", choices=("auto", "quick", "deep", "download"), default="auto")
    parser.add_argument("--goal", default="", help="What you want extracted or analyzed")
    parser.add_argument("--cookies-from-browser", default=None)
    parser.add_argument("--cookies-file", default=None)
    parser.add_argument("--user-agent", default=None)
    parser.add_argument("--referer", default=None)
    parser.add_argument("--lang", default="zh-Hans,zh,en,ja,ko")
    parser.add_argument("--whisper-model", default="base")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--whisper-api", default=None)
    parser.add_argument("--whisper-api-key", default=None)
    parser.add_argument("--whisper-api-model", default="whisper-large-v3")
    parser.add_argument("--http-timeout", type=int, default=180)
    parser.add_argument("--frame-interval", type=int, default=0, help="Seconds between extracted frames; 0=auto")
    parser.add_argument("--no-dedup-frames", dest="dedup_frames", action="store_false")
    parser.set_defaults(dedup_frames=True)
    parser.add_argument("--keep-video", action="store_true")
    parser.add_argument("--keep-audio", action="store_true")
    parser.add_argument("--gemini-model", default=DEFAULT_GEMINI_MODEL)
    parser.add_argument("--gemini-timeout", type=int, default=600)
    args = parser.parse_args()

    ensure_runtime()

    url = extract_first_url(args.source)
    metadata = get_metadata(url, args)
    mode = choose_mode(args.mode, args.goal)

    base = Path(args.output)
    folder = sanitize_name(f"{metadata['title']}_{metadata['id']}")
    out_dir = base / folder
    out_dir.mkdir(parents=True, exist_ok=True)

    metadata.update({
        "input": args.source,
        "resolved_url": url,
        "selected_mode": mode,
        "goal": args.goal,
    })
    write_json(out_dir / "metadata.json", metadata)

    print(f"[INFO] title={metadata['title']}")
    print(f"[INFO] platform={metadata['extractor']} id={metadata['id']}")
    print(f"[INFO] mode={mode}")

    if mode == "download":
        video = download_video(url, out_dir, args)
        print(f"[OK] video={video}")
        return

    if mode == "quick":
        video = download_video(url, out_dir, args)
        summary = quick_summary(video, out_dir, metadata, args)
        if not args.keep_video:
            video.unlink(missing_ok=True)
        print(f"[OK] summary={summary}")
        return

    transcript, transcript_source = prepare_transcript(url, out_dir, args)
    video = download_video(url, out_dir, args, max_height=720)
    frames_dir = out_dir / "frames"
    frame_count = extract_frames(video, frames_dir, float(metadata.get("duration") or 0), args)

    if not args.keep_video:
        video.unlink(missing_ok=True)

    manifest = {
        "status": "DEEP_PREP_READY",
        "title": metadata["title"],
        "platform": metadata["extractor"],
        "resolved_url": url,
        "transcript": str(transcript),
        "transcript_source": transcript_source,
        "frames_dir": str(frames_dir),
        "frame_count": frame_count,
        "goal": args.goal,
        "next_action": (
            "Host agent must read transcript.txt and relevant frames, then answer the user's goal. "
            "Do not substitute comments or metadata for actual video content."
        ),
    }
    write_json(out_dir / "analysis_manifest.json", manifest)
    print(f"[OK] transcript={transcript}")
    print(f"[OK] frames={frames_dir} count={frame_count}")
    print(f"[OK] manifest={out_dir / 'analysis_manifest.json'}")


if __name__ == "__main__":
    main()
