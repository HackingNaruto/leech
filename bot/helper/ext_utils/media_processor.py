#!/usr/bin/env python3
"""
KPSML-X Media Processor
Handles: Sample Video, Convert Video, Intro Subtitle (IntroSub), Zip Extract+Merge, Smart Audio Tag
"""

import logging
import os
import re
import zipfile
import json
from asyncio import create_subprocess_exec
from asyncio.subprocess import PIPE

LOGGER = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  UTILITIES
# ─────────────────────────────────────────────

def natural_sort_key(s):
    """Sort filenames naturally: Part1 < Part2 < Part10"""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]


async def run_ffmpeg(cmd: list) -> tuple[int, str, str]:
    """Run an ffmpeg command asynchronously and return (returncode, stdout, stderr)."""
    proc = await create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout.decode(), stderr.decode()


async def run_ffprobe(file_path: str) -> dict:
    """Run ffprobe to get stream info as a dict."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_format", file_path
    ]
    proc = await create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
    stdout, _ = await proc.communicate()
    try:
        return json.loads(stdout.decode())
    except Exception:
        return {}


# ─────────────────────────────────────────────
#  1. SAMPLE VIDEO
# ─────────────────────────────────────────────

async def create_sample_video(input_path: str, duration: int = 60) -> str | None:
    """
    Create a sample/preview clip from the input video.
    Returns the path to the sample file, or None on failure.
    """
    basename = os.path.splitext(input_path)[0]
    ext = os.path.splitext(input_path)[1]
    sample_path = f"{basename}_SAMPLE{ext}"

    cmd = [
        "ffmpeg", "-y",
        "-ss", "0",
        "-i", input_path,
        "-t", str(duration),
        "-c", "copy",
        "-avoid_negative_ts", "1",
        sample_path
    ]
    ret, _, err = await run_ffmpeg(cmd)
    if ret == 0 and os.path.exists(sample_path):
        LOGGER.info(f"Sample video created: {sample_path}")
        return sample_path
    else:
        LOGGER.error(f"Sample video creation failed: {err}")
        return None


# ─────────────────────────────────────────────
#  2. CONVERT VIDEO
# ─────────────────────────────────────────────

async def convert_video(input_path: str, output_format: str = "mp4") -> str | None:
    """
    Convert video to a different container format (e.g., mkv → mp4).
    Uses stream copy for lossless, fast conversion.
    Returns path to converted file, or None on failure.
    """
    output_format = output_format.lower().strip(".")
    basename = os.path.splitext(input_path)[0]
    output_path = f"{basename}_converted.{output_format}"

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-c:v", "copy",
        "-c:a", "copy",
        "-c:s", "copy",
        output_path
    ]
    ret, _, err = await run_ffmpeg(cmd)
    if ret == 0 and os.path.exists(output_path):
        LOGGER.info(f"Video converted: {output_path}")
        return output_path
    else:
        # Fallback: try with subtitle re-encode (some formats don't support copy)
        cmd2 = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-c:v", "copy",
            "-c:a", "copy",
            "-c:s", "mov_text" if output_format == "mp4" else "srt",
            output_path
        ]
        ret2, _, err2 = await run_ffmpeg(cmd2)
        if ret2 == 0 and os.path.exists(output_path):
            LOGGER.info(f"Video converted (fallback): {output_path}")
            return output_path
        LOGGER.error(f"Video conversion failed: {err2}")
        return None


# ─────────────────────────────────────────────
#  3. INTRO SUBTITLE (IntroSub)
# ─────────────────────────────────────────────

def _build_srt_block(text: str, duration_sec: int) -> str:
    """Build a single SRT subtitle block for intro."""
    end_h = duration_sec // 3600
    end_m = (duration_sec % 3600) // 60
    end_s = duration_sec % 60
    return (
        f"1\n"
        f"00:00:00,000 --> {end_h:02d}:{end_m:02d}:{end_s:02d},000\n"
        f"{text}\n\n"
    )


async def _has_subtitle_stream(input_path: str) -> bool:
    """Check if a video file has any subtitle stream."""
    info = await run_ffprobe(input_path)
    streams = info.get("streams", [])
    return any(s.get("codec_type") == "subtitle" for s in streams)


async def _extract_first_subtitle(input_path: str, out_srt: str) -> bool:
    """Extract the first subtitle stream to an SRT file."""
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-map", "0:s:0",
        out_srt
    ]
    ret, _, err = await run_ffmpeg(cmd)
    return ret == 0 and os.path.exists(out_srt)


def _prepend_intro_to_srt(srt_path: str, intro_text: str, duration_sec: int) -> str:
    """
    Prepend an intro block to an existing SRT file.
    Returns the modified SRT content as string.
    """
    intro_block = _build_srt_block(intro_text, duration_sec)
    with open(srt_path, "r", encoding="utf-8", errors="ignore") as f:
        original = f.read().strip()

    # Renumber existing blocks starting from 2
    def renumber(match):
        idx = int(match.group(1)) + 1
        return str(idx)

    renumbered = re.sub(r"^(\d+)$", renumber, original, flags=re.MULTILINE)
    return intro_block + renumbered


async def add_intro_subtitle(input_path: str, intro_text: str, duration_sec: int = 30) -> str | None:
    """
    Add an intro subtitle to a video.
    - If subtitle exists: extract → prepend intro → merge back
    - If no subtitle: create new SRT with intro → merge in
    Returns the path to the processed file, or None on failure.
    """
    base_dir = os.path.dirname(input_path)
    basename = os.path.splitext(os.path.basename(input_path))[0]
    ext = os.path.splitext(input_path)[1]
    out_srt = os.path.join(base_dir, f"{basename}_intro.srt")
    output_path = os.path.join(base_dir, f"{basename}_introsub{ext}")

    has_sub = await _has_subtitle_stream(input_path)

    if has_sub:
        # Extract existing subtitle
        raw_srt = os.path.join(base_dir, f"{basename}_raw.srt")
        extracted = await _extract_first_subtitle(input_path, raw_srt)
        if extracted:
            modified = _prepend_intro_to_srt(raw_srt, intro_text, duration_sec)
            with open(out_srt, "w", encoding="utf-8") as f:
                f.write(modified)
            os.remove(raw_srt)
        else:
            # Couldn't extract, create fresh
            with open(out_srt, "w", encoding="utf-8") as f:
                f.write(_build_srt_block(intro_text, duration_sec))
    else:
        # No subtitle: create new SRT
        with open(out_srt, "w", encoding="utf-8") as f:
            f.write(_build_srt_block(intro_text, duration_sec))

    # Merge the SRT into the video
    sub_codec = "mov_text" if ext.lower() == ".mp4" else "srt"
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-i", out_srt,
        "-map", "0",
        "-map", "1:s",
        "-c", "copy",
        "-c:s", sub_codec,
        output_path
    ]
    ret, _, err = await run_ffmpeg(cmd)

    # Cleanup temp SRT
    if os.path.exists(out_srt):
        os.remove(out_srt)

    if ret == 0 and os.path.exists(output_path):
        LOGGER.info(f"IntroSub added: {output_path}")
        return output_path
    else:
        LOGGER.error(f"IntroSub merge failed: {err}")
        return None


# ─────────────────────────────────────────────
#  4. ZIP EXTRACT + AUTO MERGE
# ─────────────────────────────────────────────

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".mov", ".flv", ".wmv", ".ts", ".m4v", ".webm"}


def _get_video_files(directory: str) -> list[str]:
    """Get all video files in a directory, sorted naturally."""
    files = []
    for root, _, fnames in os.walk(directory):
        for f in fnames:
            if os.path.splitext(f)[1].lower() in VIDEO_EXTENSIONS:
                files.append(os.path.join(root, f))
    files.sort(key=lambda x: natural_sort_key(os.path.basename(x)))
    return files


async def extract_and_merge_zip(zip_path: str, output_dir: str) -> str | None:
    """
    Extract a ZIP file, find all videos inside (naturally sorted),
    and merge them into a single output file using FFmpeg concat.
    Returns the merged output path, or None on failure.
    """
    extract_dir = os.path.join(output_dir, "zip_extract_temp")
    os.makedirs(extract_dir, exist_ok=True)

    # Extract ZIP
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)
        LOGGER.info(f"Extracted ZIP to: {extract_dir}")
    except Exception as e:
        LOGGER.error(f"ZIP extraction failed: {e}")
        return None

    # Find all video files
    video_files = _get_video_files(extract_dir)
    if not video_files:
        LOGGER.error("No video files found in ZIP archive.")
        return None

    LOGGER.info(f"Found {len(video_files)} video(s) to merge: {[os.path.basename(v) for v in video_files]}")

    if len(video_files) == 1:
        # Only one video, just return it
        return video_files[0]

    # Build concat list file
    concat_list = os.path.join(extract_dir, "concat_list.txt")
    with open(concat_list, "w", encoding="utf-8") as f:
        for vf in video_files:
            safe_path = vf.replace("'", r"'\''")
            f.write(f"file '{safe_path}'\n")

    # Determine output name from first file's base name (remove part numbers)
    first_name = os.path.splitext(os.path.basename(video_files[0]))[0]
    clean_name = re.sub(r'[._\-\s]*(part|pt|episode|ep|e)?[._\-\s]*\d+[._\-\s]*$', '', first_name, flags=re.IGNORECASE).strip()
    ext = os.path.splitext(video_files[0])[1]
    merged_output = os.path.join(output_dir, f"{clean_name}_merged{ext}")

    # Merge with FFmpeg concat
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list,
        "-c", "copy",
        merged_output
    ]
    ret, _, err = await run_ffmpeg(cmd)

    if ret == 0 and os.path.exists(merged_output):
        LOGGER.info(f"Merge complete: {merged_output}")
        # Cleanup extract dir
        import shutil
        shutil.rmtree(extract_dir, ignore_errors=True)
        return merged_output
    else:
        LOGGER.error(f"Merge failed: {err}")
        return None


# ─────────────────────────────────────────────
#  5. SMART AUDIO TAG
# ─────────────────────────────────────────────

CODEC_MAP = {
    "aac": "AAC",
    "mp3": "MP3",
    "ac3": "DD",
    "eac3": "DD+",
    "dts": "DTS",
    "truehd": "TrueHD",
    "flac": "FLAC",
    "opus": "Opus",
    "vorbis": "Vorbis",
}

CHANNEL_MAP = {
    "mono": "1.0",
    "stereo": "2.0",
    "2.1": "2.1",
    "3.0": "3.0",
    "4.0": "4.0",
    "5.0": "5.0",
    "5.1": "5.1",
    "6.1": "6.1",
    "7.0": "7.0",
    "7.1": "7.1",
}


def _build_audio_tag(tag_text: str, codec_name: str, channel_layout: str, channels: int) -> str:
    """
    Build a smart audio tag string like: 'Telegram @Channel - DD+ 5.1'
    """
    codec_label = CODEC_MAP.get(codec_name.lower(), codec_name.upper())

    # Determine channel layout label
    ch_label = CHANNEL_MAP.get(channel_layout.lower(), "")
    if not ch_label:
        # Fallback: compute from channel count
        if channels == 1:
            ch_label = "1.0"
        elif channels == 2:
            ch_label = "2.0"
        elif channels == 6:
            ch_label = "5.1"
        elif channels == 8:
            ch_label = "7.1"
        else:
            ch_label = f"{channels}.0"

    # Special cases
    if codec_name.lower() == "truehd":
        return f"{tag_text} - TrueHD Atmos"

    return f"{tag_text} - {codec_label} {ch_label}"


async def apply_smart_audio_tag(input_path: str, tag_text: str) -> str | None:
    """
    Detect audio stream info and apply a smart tag to the file's audio track(s).
    Returns path to the tagged file, or None on failure.
    """
    info = await run_ffprobe(input_path)
    streams = info.get("streams", [])
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    if not audio_streams:
        LOGGER.warning(f"No audio streams found in: {input_path}")
        return None

    base_dir = os.path.dirname(input_path)
    basename = os.path.splitext(os.path.basename(input_path))[0]
    ext = os.path.splitext(input_path)[1]
    output_path = os.path.join(base_dir, f"{basename}_tagged{ext}")

    # Build ffmpeg command with metadata for each audio stream
    cmd = ["ffmpeg", "-y", "-i", input_path]

    # Map all streams
    cmd += ["-map", "0"]
    cmd += ["-c", "copy"]

    for idx, stream in enumerate(audio_streams):
        codec = stream.get("codec_name", "aac")
        layout = stream.get("channel_layout", "")
        channels = stream.get("channels", 2)
        smart_tag = _build_audio_tag(tag_text, codec, layout, channels)
        cmd += [f"-metadata:s:a:{idx}", f"title={smart_tag}"]

    cmd.append(output_path)

    ret, _, err = await run_ffmpeg(cmd)
    if ret == 0 and os.path.exists(output_path):
        LOGGER.info(f"Smart audio tag applied: {output_path}")
        return output_path
    else:
        LOGGER.error(f"Audio tag failed: {err}")
        return None
