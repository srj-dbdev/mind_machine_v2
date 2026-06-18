import asyncio
import edge_tts
import os
import time

from utils.audio_utils import build_narration


async def _generate_voice_async(text, output_path):
    communicate = edge_tts.Communicate(
        text=text,
        voice="en-US-GuyNeural"
    )

    await communicate.save(output_path)


def generate_voice(script, output_path=None):
    """
    Generates narration from either:
    - a plain string
    - the structured JSON returned by script_generator.py
    """

    # Build narration if script is JSON
    if isinstance(script, dict):
        text = build_voice_text(script)
    else:
        text = str(script)

    # Create output folder
    os.makedirs("output", exist_ok=True)

    # Timestamped filename
    if output_path is None:
        timestamp = int(time.time())
        output_path = f"output/voice_{timestamp}.mp3"

    asyncio.run(
        _generate_voice_async(
            text,
            output_path
        )
    )

    print("\n========== NARRATION ==========")
    print(text)
    print("===============================\n")

    print(f"Voice saved at: {output_path}")

    return output_path