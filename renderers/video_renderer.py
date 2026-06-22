import os
import shutil
import subprocess
import tempfile
import time


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
    For images, holds the frame for `duration` seconds.
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
        # Video: loop if shorter than needed, then trim to duration
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

def create_video(audio_path=None, clips=None, scene_audios=None, scenes=None):
    """
    Creates the final reel with clips synced to scene narration.

    Preferred mode — scene_audios + scenes (per-scene sync):
        scene_audios = [{"order":1, "text":"...", "audio_path":"..."}]
        scenes = [{"keyword":"...", "path":"...", "media_type":"video|image"}]

    Fallback mode — audio_path + clips (original behaviour):
        audio_path = single MP3
        clips = [{"path":"...", "media_type":"video|image"}]
    """

    os.makedirs("output", exist_ok=True)
    temp_dir = tempfile.mkdtemp()

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

                print(
                    f"  Scene {i+1}: {media_type} "
                    f"({duration:.2f}s) — {asset['keyword']}"
                )

                # Normalize asset to duration
                normalized = os.path.join(
                    temp_dir, f"norm_{i}.mp4"
                )
                normalize_asset(
                    asset["path"],
                    normalized,
                    duration,
                    media_type
                )

                # Combine with scene audio
                segment = os.path.join(
                    temp_dir, f"segment_{i}.mp4"
                )
                combine_segment(normalized, audio_file, segment)
                segments.append(segment)

        # --------------------------------------------------
        # Mode 2: fallback — single audio, equal clip split
        # --------------------------------------------------

        else:

            print("\nRendering with equal clip split (fallback)...")

            if not clips:
                clips = [{"path": "assets/background.mp4", "media_type": "video"}]

            total_duration = get_audio_duration(audio_path)
            clip_duration = total_duration / len(clips)

            print(f"  Total: {total_duration:.2f}s, each clip: {clip_duration:.2f}s")

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
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            merged
        ], check=True)

        # --------------------------------------------------
        # In fallback mode, add the single audio track
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
            # Scene-synced mode: audio already embedded per segment
            shutil.copy(merged, output_video)

        print(f"\nReel created: {output_video}")
        return output_video

    finally:
        shutil.rmtree(temp_dir)