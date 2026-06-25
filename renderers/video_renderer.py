import os
import shutil
import subprocess
import tempfile
import time


# ---------------------------------------------------
# Font config
# ---------------------------------------------------

FONT_PATH = "assets/fonts/LobsterTwo-BoldItalic.ttf"

# Title card config
TITLE_CARD_DURATION = 3       # seconds the title card stays on screen
TITLE_CARD_FADE_DURATION = 0.5 # seconds for fade in/out


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
# Word-wrap text to fixed character width
# ---------------------------------------------------

def wrap_text(text, max_chars=28):
    """
    Wraps text into lines of max_chars width.
    Returns a string with \n separating lines,
    formatted for ffmpeg drawtext.
    """
    words = text.split()
    lines = []
    current = []
    current_len = 0

    for word in words:
        # +1 for the space
        if current_len + len(word) + (1 if current else 0) <= max_chars:
            current.append(word)
            current_len += len(word) + (1 if len(current) > 1 else 0)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
            current_len = len(word)

    if current:
        lines.append(" ".join(current))

    return "\n".join(lines)


# ---------------------------------------------------
# Generate title card with black background + yellow text
# ---------------------------------------------------

def create_title_card(output_file, hook_text, temp_dir):
    """
    Creates a title card segment:
    - Black background
    - Yellow LobsterTwo text, word-wrapped, centered
    - Fades in from black, holds, fades out to black
    - Duration: TITLE_CARD_DURATION seconds
    """

    if not os.path.exists(FONT_PATH):
        print("  Font not found — skipping title card")
        return None

    safe_text = escape_ffmpeg_text(wrap_text(hook_text, max_chars=24))

    fade_in_end = TITLE_CARD_FADE_DURATION
    fade_out_start = TITLE_CARD_DURATION - TITLE_CARD_FADE_DURATION

    # Generate black background with yellow text + fade in/out
    vf_filter = (
        # Draw yellow wrapped text centered on black background
        f"drawtext="
        f"fontfile={FONT_PATH}:"
        f"text='{safe_text}':"
        f"fontcolor=yellow:"
        f"fontsize=62:"
        f"x=(w-text_w)/2:"
        f"y=(h-text_h)/2:"
        f"line_spacing=20:"
        f"borderw=3:"
        f"bordercolor=black@0.6:"
        f"expansion=none,"
        # Fade in from black
        f"fade=t=in:st=0:d={TITLE_CARD_FADE_DURATION},"
        # Fade out to black
        f"fade=t=out:st={fade_out_start}:d={TITLE_CARD_FADE_DURATION}"
    )

    cmd = [
    "ffmpeg", "-y",
    # Black video background
    "-f", "lavfi",
    "-i", f"color=c=black:s=1080x1920:r=30:d={TITLE_CARD_DURATION}",
    # Silent audio track
    "-f", "lavfi",
    "-i", f"anullsrc=channel_layout=stereo:sample_rate=44100",
    "-vf", vf_filter,
    "-c:v", "libx264",
    "-preset", "medium",
    "-crf", "23",
    "-pix_fmt", "yuv420p",
    # Encode silent audio as AAC
    "-c:a", "aac",
    "-b:a", "128k",
    "-t", str(TITLE_CARD_DURATION),
    output_file
]

    try:
        subprocess.run(cmd, check=True)
        print(f"  ✓ Title card created ({TITLE_CARD_DURATION}s)")
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"  Title card creation failed: {e}")
        return None


# ---------------------------------------------------
# Add fade-in effect to first scene
# ---------------------------------------------------

def add_fade_in(input_file, output_file):
    """
    Adds a fade-in from black to the first scene
    so it blends smoothly after the title card fade-out.
    """

    cmd = [
        "ffmpeg", "-y",
        "-i", input_file,
        "-vf", f"fade=t=in:st=0:d={TITLE_CARD_FADE_DURATION}",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-codec:a", "copy",
        output_file
    ]

    try:
        subprocess.run(cmd, check=True)
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"  Fade-in failed: {e}")
        return input_file


# ---------------------------------------------------
# Burn subtitle chunks onto a video segment
# ---------------------------------------------------

def burn_subtitles(input_file, output_file, chunks):
    """
    Burns subtitle chunks onto a video segment using ffmpeg drawtext.
    Each chunk appears at its start time and disappears at its end time.
    Text is word-wrapped and displayed at the bottom of the frame.
    """

    if not os.path.exists(FONT_PATH):
        print(f"  Font not found — skipping subtitles")
        shutil.copy(input_file, output_file)
        return

    if not chunks:
        print(f"  No subtitle chunks — skipping")
        shutil.copy(input_file, output_file)
        return

    filter_parts = []

    for chunk in chunks:
        # Wrap each chunk to fit screen width
        wrapped = escape_ffmpeg_text(
            wrap_text(chunk["text"], max_chars=28)
        )
        start = chunk["start"]
        end = chunk["end"]

        filter_parts.append(
            f"drawtext="
            f"fontfile={FONT_PATH}:"
            f"text='{wrapped}':"
            f"fontcolor=white:"
            f"fontsize=52:"
            f"box=1:"
            f"boxcolor=black@0.55:"
            f"boxborderw=16:"
            f"x=(w-text_w)/2:"
            f"y=(h*0.80):"
            f"line_spacing=12:"
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
    subtitles=None,
    hook_text=None
):
    """
    Creates the final reel with title card, scene-synced clips,
    and Whisper subtitles.

    Args:
        scene_audios: [{"order":1, "text":"...", "audio_path":"..."}]
        scenes:       [{"keyword":"...", "path":"...", "media_type":"..."}]
        subtitles:    [{"label":"...", "chunks":[...]}]
        hook_text:    string — displayed on title card (hook from script)
    """

    os.makedirs("output", exist_ok=True)
    temp_dir = tempfile.mkdtemp()

    # Build subtitle lookup by label
    subtitle_map = {}
    if subtitles:
        for s in subtitles:
            subtitle_map[s["label"]] = s.get("chunks", [])

    try:

        segments = []

        # --------------------------------------------------
        # Title card — prepended before scene 1
        # --------------------------------------------------

        if hook_text:
            print("\nCreating title card...")
            title_card = os.path.join(temp_dir, "title_card.mp4")
            result = create_title_card(title_card, hook_text, temp_dir)
            if result:
                segments.append(title_card)

        # --------------------------------------------------
        # Mode 1: per-scene sync (preferred)
        # --------------------------------------------------

        if scene_audios and scenes:

            print("\nRendering with per-scene sync...")

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

                # Burn subtitles onto scene
                chunks = subtitle_map.get(label, [])

                if chunks:
                    subtitled = os.path.join(
                        temp_dir, f"subtitled_{i}.mp4"
                    )
                    burn_subtitles(normalized, subtitled, chunks)
                    normalized = subtitled

                # First scene — add fade in from black
                if i == 0 and hook_text:
                    faded = os.path.join(temp_dir, f"faded_{i}.mp4")
                    add_fade_in(normalized, faded)
                    normalized = faded

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