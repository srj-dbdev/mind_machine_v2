import os
import shutil
import subprocess
import tempfile
import time


# ---------------------------------------------------
# Font config
# ---------------------------------------------------

FONT_PATH = "assets/fonts/LobsterTwo-BoldItalic.ttf"

TITLE_CARD_DURATION  = 3
TITLE_CARD_FADE      = 0.5


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

def wrap_text(text, max_chars=24):
    words = text.split()
    lines = []
    current = []
    current_len = 0

    for word in words:
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
# Generate card (title or end) with background image
# ---------------------------------------------------

def create_card(
    output_file,
    text,
    card_background,
    temp_dir,
    is_end_card=False
):
    """
    Creates a title or end card segment:
    - Thematic background image (dark/vibrant/neutral)
    - Semi-transparent dark overlay for readability
    - Yellow LobsterTwo text, word-wrapped, centered
    - Fade in from black, hold, fade out to black
    - Silent AAC audio track for concat compatibility
    """

    if not os.path.exists(FONT_PATH):
        print("  Font not found — skipping card")
        return None

    bg_path = card_background.get("path") if card_background else None
    overlay_opacity = card_background.get("overlay_opacity", 0.45) if card_background else 0.6

    safe_text = escape_ffmpeg_text(wrap_text(text, max_chars=20))
    fade_out_start = TITLE_CARD_DURATION - TITLE_CARD_FADE

    # Build video filter chain
    # 1. Scale background to 1080x1920
    # 2. Add dark overlay for readability
    # 3. Draw yellow text centered
    # 4. Fade in / fade out

    vf_filter = (
        f"scale=1080:1920:force_original_aspect_ratio=increase,"
        f"crop=1080:1920,"
        # Dark overlay
        f"drawbox="
        f"x=0:y=0:w=iw:h=ih:"
        f"color=black@{overlay_opacity}:"
        f"t=fill,"
        # Yellow text — double size (font 120)
        f"drawtext="
        f"fontfile={FONT_PATH}:"
        f"text='{safe_text}':"
        f"fontcolor=yellow:"
        f"fontsize=120:"
        f"x=(w-text_w)/2:"
        f"y=(h-text_h)/2:"
        f"line_spacing=24:"
        f"borderw=4:"
        f"bordercolor=black@0.7:"
        f"expansion=none,"
        # Fade in
        f"fade=t=in:st=0:d={TITLE_CARD_FADE},"
        # Fade out
        f"fade=t=out:st={fade_out_start}:d={TITLE_CARD_FADE}"
    )

    # Use background image if available, else black
    if bg_path and os.path.exists(bg_path):
        video_input = ["-loop", "1", "-i", bg_path]
    else:
        video_input = [
            "-f", "lavfi",
            "-i", f"color=c=black:s=1080x1920:r=30"
        ]

    cmd = [
        "ffmpeg", "-y",
        *video_input,
        "-f", "lavfi",
        "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-vf", vf_filter,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        "-ac", "2",
        "-t", str(TITLE_CARD_DURATION),
        output_file
    ]

    card_name = "end card" if is_end_card else "title card"

    try:
        subprocess.run(cmd, check=True)
        mood = card_background.get("visual_mood", "default") if card_background else "default"
        print(f"  ✓ {card_name} created ({mood} background, {TITLE_CARD_DURATION}s)")
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"  {card_name} creation failed: {e}")
        return None


# ---------------------------------------------------
# Add fade-in to first scene
# ---------------------------------------------------

def add_fade_in(input_file, output_file):
    cmd = [
        "ffmpeg", "-y",
        "-i", input_file,
        "-vf", f"fade=t=in:st=0:d={TITLE_CARD_FADE}",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-codec:a", "copy",
        output_file
    ]
    try:
        subprocess.run(cmd, check=True)
        return output_file
    except subprocess.CalledProcessError:
        return input_file


# ---------------------------------------------------
# Burn subtitle chunks onto a video segment
# ---------------------------------------------------

def burn_subtitles(input_file, output_file, chunks):

    if not os.path.exists(FONT_PATH):
        shutil.copy(input_file, output_file)
        return

    if not chunks:
        shutil.copy(input_file, output_file)
        return

    filter_parts = []

    for chunk in chunks:
        wrapped = escape_ffmpeg_text(wrap_text(chunk["text"], max_chars=28))
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
        print(f"  Subtitle burn failed: {e}")
        shutil.copy(input_file, output_file)


# ---------------------------------------------------
# Combine a single video segment with its audio
# Normalizes audio to 44100Hz stereo AAC
# ---------------------------------------------------

def combine_segment(video_file, audio_file, output_file):
    cmd = [
        "ffmpeg", "-y",
        "-i", video_file,
        "-i", audio_file,
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        "-ac", "2",
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
    hook_text=None,
    cta_text=None,
    card_background=None
):
    """
    Creates the final reel:
    [Title Card] → [Scene 1..N with subtitles] → [End Card]

    Args:
        scene_audios:    per-scene audio dicts
        scenes:          per-scene asset dicts
        subtitles:       Whisper subtitle chunks per scene
        hook_text:       text for title card
        cta_text:        text for end card
        card_background: dict from generate_card_background()
                         {path, visual_mood, overlay_opacity}
    """

    os.makedirs("output", exist_ok=True)
    temp_dir = tempfile.mkdtemp()

    subtitle_map = {}
    if subtitles:
        for s in subtitles:
            subtitle_map[s["label"]] = s.get("chunks", [])

    try:

        segments = []

        # --------------------------------------------------
        # Title card
        # --------------------------------------------------

        if hook_text:
            print("\nCreating title card...")
            title_card = os.path.join(temp_dir, "title_card.mp4")
            result = create_card(
                title_card,
                hook_text,
                card_background,
                temp_dir,
                is_end_card=False
            )
            if result:
                segments.append(title_card)

        # --------------------------------------------------
        # Scene segments
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

                # Normalize
                normalized = os.path.join(temp_dir, f"norm_{i}.mp4")
                normalize_asset(asset["path"], normalized, duration, media_type)

                # Subtitles
                chunks = subtitle_map.get(label, [])
                if chunks:
                    subtitled = os.path.join(temp_dir, f"subtitled_{i}.mp4")
                    burn_subtitles(normalized, subtitled, chunks)
                    normalized = subtitled

                # Fade in on first scene
                if i == 0 and hook_text:
                    faded = os.path.join(temp_dir, f"faded_{i}.mp4")
                    add_fade_in(normalized, faded)
                    normalized = faded

                # Combine with audio
                segment = os.path.join(temp_dir, f"segment_{i}.mp4")
                combine_segment(normalized, audio_file, segment)
                segments.append(segment)

        # --------------------------------------------------
        # Fallback mode
        # --------------------------------------------------

        else:

            print("\nRendering with equal clip split (fallback)...")

            if not clips:
                clips = [{"path": "assets/background.mp4", "media_type": "video"}]

            total_duration = get_audio_duration(audio_path)
            clip_duration = total_duration / len(clips)

            for i, clip in enumerate(clips):
                media_type = clip.get("media_type", "video")
                normalized = os.path.join(temp_dir, f"norm_{i}.mp4")
                normalize_asset(clip["path"], normalized, clip_duration, media_type)
                segments.append(normalized)

        # --------------------------------------------------
        # End card
        # --------------------------------------------------

        if cta_text:
            print("\nCreating end card...")
            end_card = os.path.join(temp_dir, "end_card.mp4")
            result = create_card(
                end_card,
                cta_text,
                card_background,
                temp_dir,
                is_end_card=True
            )
            if result:
                segments.append(end_card)

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