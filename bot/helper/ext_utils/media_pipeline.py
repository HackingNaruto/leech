#!/usr/bin/env python3
"""
KPSML-X Media Processing Pipeline Hook
Integrate media_processor into the task listener's upload flow.
"""

import os
import logging
from bot import user_data
from bot.helper.ext_utils.media_processor import (
    create_sample_video,
    convert_video,
    add_intro_subtitle,
    apply_smart_audio_tag,
    extract_and_merge_zip,
)

LOGGER = logging.getLogger(__name__)

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".mov", ".flv", ".wmv", ".ts", ".m4v", ".webm"}
ZIP_EXTENSIONS   = {".zip"}


def _is_video(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in VIDEO_EXTENSIONS


def _is_zip(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in ZIP_EXTENSIONS


def _uget(user_id: int, key: str, default=None):
    return user_data.get(user_id, {}).get(key, default)


async def process_media_file(listener, file_path: str) -> tuple[str, list[str]]:
    """
    Apply all enabled user-setting processing steps to a single file.
    Returns (final_path, extra_files).
    """
    user_id = listener.user_id
    extra_files: list[str] = []

    if not _is_video(file_path):
        return file_path, extra_files

    current_path = file_path

    # 1. Intro Subtitle
    if _uget(user_id, "intro_sub", False):
        intro_text = _uget(user_id, "intro_text", "")
        intro_dur  = _uget(user_id, "intro_duration", 30)
        if intro_text:
            LOGGER.info(f"[{user_id}] Applying IntroSub...")
            result = await add_intro_subtitle(current_path, intro_text, intro_dur)
            if result:
                if current_path != file_path and os.path.exists(current_path):
                    os.remove(current_path)
                current_path = result

    # 2. Smart Audio Tag
    if _uget(user_id, "audio_tag", False):
        tag_text = _uget(user_id, "audio_tag_text", "")
        if tag_text:
            LOGGER.info(f"[{user_id}] Applying Smart Audio Tag: {tag_text}")
            result = await apply_smart_audio_tag(current_path, tag_text)
            if result:
                if current_path != file_path and os.path.exists(current_path):
                    os.remove(current_path)
                current_path = result

    # 3. Sample Video
    if _uget(user_id, "sample_video", False):
        duration = _uget(user_id, "sample_duration", 60)
        LOGGER.info(f"[{user_id}] Creating {duration}s sample video...")
        sample = await create_sample_video(current_path, duration)
        if sample:
            extra_files.append(sample)

    # 4. Convert Video
    if _uget(user_id, "convert_video", False):
        fmt = _uget(user_id, "convert_format", "mkv")
        current_ext = os.path.splitext(current_path)[1].lower().strip(".")
        if current_ext != fmt.lower():
            LOGGER.info(f"[{user_id}] Converting video to {fmt.upper()}...")
            result = await convert_video(current_path, fmt)
            if result:
                if current_path != file_path and os.path.exists(current_path):
                    os.remove(current_path)
                current_path = result

    return current_path, extra_files


async def handle_zip_auto_merge(listener, zip_path: str) -> str | None:
    """
    If user has Auto Merge Zip enabled and the file is a ZIP, extract and merge.
    Returns the merged video path, or None if disabled / not applicable.
    """
    user_id = listener.user_id
    if not _uget(user_id, "auto_merge_zip", False):
        return None

    if not _is_zip(zip_path):
        return None

    LOGGER.info(f"[{user_id}] Auto Merge Zip triggered for: {zip_path}")
    output_dir = os.path.dirname(zip_path)
    merged = await extract_and_merge_zip(zip_path, output_dir)
    return merged
