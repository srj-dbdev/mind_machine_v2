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
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        audio_path
    ]

    result = subprocess.check_output(cmd)

    return float(result.decode().strip())


# ---------------------------------------------------
# Normalize clip
# ---------------------------------------------------

def normalize_clip(input_file, output_file):

    cmd = [

        "ffmpeg",

        "-y",

        "-i", input_file,

        "-vf",

        (
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
# Trim clip
# ---------------------------------------------------

def trim_clip(input_file, output_file, duration):

    cmd = [

        "ffmpeg",

        "-y",

        "-i", input_file,

        "-t", str(duration),

        "-c:v", "libx264",

        "-preset", "fast",

        "-crf", "23",

        "-an",

        output_file

    ]

    subprocess.run(cmd, check=True)


# ---------------------------------------------------
# Main renderer
# ---------------------------------------------------

def create_video(audio_path, clips):

    os.makedirs("output", exist_ok=True)

    if not clips:

        clips = [{
            "path": "assets/background.mp4"
        }]

    temp_dir = tempfile.mkdtemp()

    normalized = []

    print("\nNormalizing clips...")

    for i, clip in enumerate(clips):

        output_clip = os.path.join(
            temp_dir,
            f"normalized_{i}.mp4"
        )

        normalize_clip(
            clip["path"],
            output_clip
        )

        normalized.append(output_clip)

    audio_duration = get_audio_duration(audio_path)

    print(
        f"\nNarration Length: {audio_duration:.2f} sec"
    )

    clip_duration = audio_duration / len(normalized)

    print(
        f"Each clip will be {clip_duration:.2f} sec"
    )

    trimmed = []

    print("\nTrimming clips...")

    for i, clip in enumerate(normalized):

        trimmed_clip = os.path.join(
            temp_dir,
            f"trimmed_{i}.mp4"
        )

        trim_clip(
            clip,
            trimmed_clip,
            clip_duration
        )

        trimmed.append(trimmed_clip)

    concat_file = os.path.join(
        temp_dir,
        "clips.txt"
    )

    with open(concat_file, "w", encoding="utf8") as f:

        for clip in trimmed:

            f.write(
                f"file '{os.path.abspath(clip)}'\n"
            )

    merged_video = os.path.join(
        temp_dir,
        "merged.mp4"
    )

    print("\nMerging clips...")

    subprocess.run([

        "ffmpeg",

        "-y",

        "-f", "concat",

        "-safe", "0",

        "-i", concat_file,

        "-c", "copy",

        merged_video

    ], check=True)

    timestamp = int(time.time())

    output_video = (
        f"output/reel_{timestamp}.mp4"
    )

    print("\nAdding narration...")

    subprocess.run([

        "ffmpeg",

        "-y",

        "-i", merged_video,

        "-i", audio_path,

        "-map", "0:v",

        "-map", "1:a",

        "-c:v", "copy",

        "-c:a", "aac",

        "-shortest",

        output_video

    ], check=True)

    shutil.rmtree(temp_dir)

    print("\nVideo created:")

    print(output_video)

    return output_video