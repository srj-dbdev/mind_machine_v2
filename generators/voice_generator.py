import asyncio
import edge_tts
import os
import time

from utils.audio_utils import build_narration, clean_text


async def _generate_voice_async(text, output_path):
    communicate = edge_tts.Communicate(
        text=text,
        voice="en-US-GuyNeural"
    )
    await communicate.save(output_path)


def generate_voice(script, output_path=None):
    """
    Generates a single narration MP3 from the full script.
    Used as a fallback or for preview purposes.
    """

    if isinstance(script, dict):
        text = build_narration(script)
    else:
        text = str(script)

    os.makedirs("output", exist_ok=True)

    if output_path is None:
        timestamp = int(time.time())
        output_path = f"output/voice_{timestamp}.mp3"

    asyncio.run(_generate_voice_async(text, output_path))

    print("\n========== NARRATION ==========")
    print(text)
    print("===============================\n")
    print(f"Voice saved at: {output_path}")

    return output_path


def generate_voice_per_scene(script, output_dir="output/audio"):
    """
    Generates one MP3 per scene so clips can be synced
    to narration line changes exactly.

    Returns:
        [
            {
                "order": 1,
                "text": "...",
                "audio_path": "output/audio/scene_1.mp3"
            },
            ...
        ]
    """

    os.makedirs(output_dir, exist_ok=True)

    # Build hook + scenes + cta as ordered list
    items = []

    hook = clean_text(script.get("hook", ""))
    if hook:
        items.append({
            "order": 0,
            "text": hook,
            "label": "hook"
        })

    for scene in script.get("scenes", []):
        text = clean_text(scene.get("text", ""))
        if text:
            items.append({
                "order": scene.get("order", len(items)),
                "text": text,
                "label": f"scene_{scene.get('order', len(items))}"
            })

    cta = clean_text(script.get("cta", ""))
    if cta:
        items.append({
            "order": 999,
            "text": cta,
            "label": "cta"
        })

    # Generate one MP3 per item
    scene_audios = []

    for item in items:
        audio_path = os.path.join(
            output_dir,
            f"{item['label']}.mp3"
        )

        print(f"  Generating audio: {item['label']} → {item['text'][:50]}")

        asyncio.run(
            _generate_voice_async(item["text"], audio_path)
        )

        scene_audios.append({
            "order": item["order"],
            "text": item["text"],
            "audio_path": audio_path
        })

    print(f"\nGenerated {len(scene_audios)} scene audio files")

    return scene_audios