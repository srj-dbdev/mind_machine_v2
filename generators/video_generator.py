import subprocess

input_video = "assets/background.mp4"
input_audio = "voice.mp3"
output_video = "output/reel.mp4"

cmd = [
    "ffmpeg",
    "-y",
    "-stream_loop", "-1",
    "-i", input_video,
    "-i", input_audio,
    "-c:v", "libx264",
    "-c:a", "aac",
    "-shortest",
    output_video
]

subprocess.run(cmd)

print("Video created:", output_video)