import os
import shutil
import subprocess
import tempfile
import time


# ---------------------------------------------------
# Font config
# ---------------------------------------------------

FONT_PATH = "assets/fonts/LobsterTwo-BoldItalic.ttf"


# ---------------------------------------------------
# Get audio duration
# ---------------------------------------------------

def get_audio_duration(audio_path):
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path
    ]
    result = subprocess.check_output(cmd)
    return float(result.decode().strip())


# ---------------------------------------------------
# Normalize any asset (video or image) to 1080x1920
# ---------------------------------------------------

def normalize_asset(input_file, output_file, duration, media_type="video"):
    """
    Normalizes a video clip or static image to 1080x1920 vertical format.
    For images, holds the frame for exactly `duration` seconds.
    For videos, loops and trims to exactly `duration` seconds.
    """

    if media_type == "image":
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", input_file,
            "-t", str(duration),
            "-vf", (
                "scale=1080:1920:"
                "force_original_aspect_ratio=increase,"
                "crop=1080:1920"
            ),
            "-r", "30",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-an",
            output_file
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", input_file,
            "-t", str(duration),
            "-vf", (
                "scale=1080:1920:"
                "force_original_aspect_ratio=increase,"
                "crop=1080:1920"
            ),
            "-r", "30",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-an",
            output_file
        ]

    subprocess.run(cmd, check=True)


# ---------------------------------------------------
# Escape text for ffmpeg drawtext
# ---------------------------------------------------

def escape_ffmpeg_text(text):
    """
    Escapes special characters for ffmpeg drawtext filter.
    """
    return (
        text
        .replace("\\", "\\\\")
        .replace("'",  "\u2019")
        .replace(":",  "\\:")
        .replace("%",  "\\%")
        .replace("[",  "\\[")
        .replace("]",  "\\]")
    )


# ---------------------------------------------------
# Burn subtitle chunks onto a video segment
# ---------------------------------------------------

def burn_subtitles(input_file, output_file, chunks, is_first_scene=False):
    """
    Burns subtitle chunks onto a video segment using ffmpeg drawtext.

    Each chunk appears at its start time and disappears at its end time.
    On the first scene, the full narration text also appears as a
    larger handwritten overlay at the top.

    Args:
        input_file:     normalized video segment
        output_file:    output path
        chunks:         list of {"text", "start", "end"} dicts
        is_first_scene: if True, adds larger headline text at top
    """

    if not os.path.exists(FONT_PATH):
        print(f"  Font not found — skipping subtitles")
        shutil.copy(input_file, output_file)
        return

    if not chunks:
        print(f"  No subtitle chunks — skipping")
        shutil.copy(input_file, output_file)
        return

    # Build drawtext filter chain for each chunk
    filter_parts = []

    # First scene headline text (LobsterTwo, larger, top area)
    if is_first_scene and chunks:
        full_text = escape_ffmpeg_text(
            " ".join(c["text"] for c in chunks)
        )
        total_start = chunks[0]["start"]
        total_end = chunks[-1]["end"]

        filter_parts.append(
            f"drawtext="
            f"fontfile={FONT_PATH}:"
            f"text='{full_text}':"
            f"fontcolor=white:"
            f"fontsize=58:"
            f"box=1:"
            f"boxcolor=black@0.45:"
            f"boxborderw=20:"
            f"x=(w-text_w)/2:"
            f"y=(h*0.12):"
            f"line_spacing=12:"
            f"borderw=2:"
            f"bordercolor=black@0.5:"
            f"expansion=none:"
            f"enable='between(t,{total_start},{total_end})'"
        )

    # Subtitle chunks at bottom (all scenes)
    for chunk in chunks:
        safe_text = escape_ffmpeg_text(chunk["text"])
        start = chunk["start"]
        end = chunk["end"]

        filter_parts.append(
            f"drawtext="
            f"fontfile={FONT_PATH}:"
            f"text='{safe_text}':"
            f"fontcolor=white:"
            f"fontsize=52:"
            f"box=1:"
            f"boxcolor=black@0.55:"
            f"boxborderw=16:"
            f"x=(w-text_w)/2:"
            f"y=(h*0.82):"
            f"borderw=2:"
            f"bordercolor=black@0.5:"
            f"expansion=none:"
            f"enable='between(t,{start},{end})'"
        )

    vf_filter = ",".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        "-i", input_file,
        "-vf", vf_filter,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-codec:a", "copy",
        output_file
    ]

    try:
        subprocess.run(cmd, check=True)
        print(f"  ✓ Subtitles applied ({len(chunks)} chunks)")
    except subprocess.CalledProcessError as e:
        print(f"  Subtitle burn failed: {e} — using segment without subtitles")
        shutil.copy(input_file, output_file)


# ---------------------------------------------------
# Combine a single video segment with its audio
# ---------------------------------------------------

def combine_segment(video_file, audio_file, output_file):
    """
    Muxes one video segment with its matching scene audio.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", video_file,
        "-i", audio_file,
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        output_file
    ]
    subprocess.run(cmd, check=True)


# ---------------------------------------------------
# Main renderer — scene-synced
# ---------------------------------------------------

def create_video(
    audio_path=None,
    clips=None,
    scene_audios=None,
    scenes=None,
    subtitles=None
):
    """
    Creates the final reel with clips synced to scene narration.

    Preferred mode — scene_audios + scenes (per-scene sync):
        scene_audios = [{"order":1, "text":"...", "audio_path":"..."}]
        scenes       = [{"keyword":"...", "path":"...", "media_type":"..."}]
        subtitles    = [{"label":"...", "chunks":[...]}] (optional)

    Fallback mode — audio_path + clips (original behaviour):
        audio_path = single MP3
        clips      = [{"path":"...", "media_type":"..."}]
    """

    os.makedirs("output", exist_ok=True)
    temp_dir = tempfile.mkdtemp()

    # Build subtitle lookup by label for quick access
    subtitle_map = {}
    if subtitles:
        for s in subtitles:
            subtitle_map[s["label"]] = s.get("chunks", [])

    try:

        # --------------------------------------------------
        # Mode 1: per-scene sync (preferred)
        # --------------------------------------------------

        if scene_audios and scenes:

            print("\nRendering with per-scene sync...")

            segments = []

            for i, (scene_audio, asset) in enumerate(
                zip(scene_audios, scenes)
            ):

                if asset is None:
                    print(f"  Scene {i+1}: no asset, skipping")
                    continue

                audio_file = scene_audio["audio_path"]
                duration = get_audio_duration(audio_file)
                media_type = asset.get("media_type", "video")
                label = scene_audio.get("label", "")

                print(
                    f"  Scene {i+1}: {media_type} "
                    f"({duration:.2f}s) — {asset['keyword']}"
                )

                # Normalize asset to exact audio duration
                normalized = os.path.join(temp_dir, f"norm_{i}.mp4")
                normalize_asset(
                    asset["path"],
                    normalized,
                    duration,
                    media_type
                )

                # Burn subtitles if available
                chunks = subtitle_map.get(label, [])
                is_first = (i == 0)

                if chunks or is_first:
                    subtitled = os.path.join(temp_dir, f"subtitled_{i}.mp4")
                    burn_subtitles(
                        normalized,
                        subtitled,
                        chunks,
                        is_first_scene=is_first
                    )
                    normalized = subtitled

                # Combine with scene audio
                segment = os.path.join(temp_dir, f"segment_{i}.mp4")
                combine_segment(normalized, audio_file, segment)
                segments.append(segment)

        # --------------------------------------------------
        # Mode 2: fallback — single audio, equal clip split
        # --------------------------------------------------

        else:

            print("\nRendering with equal clip split (fallback)...")

            if not clips:
                clips = [{
                    "path": "assets/background.mp4",
                    "media_type": "video"
                }]

            total_duration = get_audio_duration(audio_path)
            clip_duration = total_duration / len(clips)

            print(
                f"  Total: {total_duration:.2f}s, "
                f"each clip: {clip_duration:.2f}s"
            )

            segments = []

            for i, clip in enumerate(clips):
                media_type = clip.get("media_type", "video")
                normalized = os.path.join(temp_dir, f"norm_{i}.mp4")
                normalize_asset(
                    clip["path"],
                    normalized,
                    clip_duration,
                    media_type
                )
                segments.append(normalized)

        # --------------------------------------------------
        # Concatenate all segments
        # --------------------------------------------------

        if not segments:
            raise ValueError("No segments to render.")

        concat_file = os.path.join(temp_dir, "segments.txt")

        with open(concat_file, "w", encoding="utf8") as f:
            for seg in segments:
                f.write(f"file '{os.path.abspath(seg)}'\n")

        merged = os.path.join(temp_dir, "merged.mp4")

        print("\nConcatenating segments...")

        subprocess.run([
            "ffmpeg", "-y",
            "-fflags", "+genpts",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            merged
        ], check=True)

        # --------------------------------------------------
        # Fallback mode — add single audio track
        # --------------------------------------------------

        timestamp = int(time.time())
        output_video = f"output/reel_{timestamp}.mp4"

        if audio_path and not scene_audios:

            print("\nAdding narration track...")

            subprocess.run([
                "ffmpeg", "-y",
                "-i", merged,
                "-i", audio_path,
                "-map", "0:v",
                "-map", "1:a",
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                output_video
            ], check=True)

        else:
            shutil.copy(merged, output_video)

        print(f"\nReel created: {output_video}")
        return output_video

    finally:
        shutil.rmtree(temp_dir)