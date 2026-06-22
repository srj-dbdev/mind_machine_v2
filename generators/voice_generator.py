import os
import time

from gtts import gTTS

from utils.audio_utils import build_narration, clean_text


# ---------------------------------------------------
# Core TTS function
# ---------------------------------------------------

def _generate_voice_gtts(text, output_path, lang="en"):
    """
    Generates speech from text using gTTS (Google Translate TTS).
    Free, no API key required.
    """
    tts = gTTS(text=text, lang=lang, slow=False)
    tts.save(output_path)


# ---------------------------------------------------
# Single narration MP3 (full script)
# ---------------------------------------------------

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

    _generate_voice_gtts(text, output_path)

    print("\n========== NARRATION ==========")
    print(text)
    print("===============================\n")
    print(f"Voice saved at: {output_path}")

    return output_path


# ---------------------------------------------------
# Per-scene audio (one MP3 per scene)
# ---------------------------------------------------

def generate_voice_per_scene(script, output_dir="output/audio"):
    """
    Generates one MP3 per scene so clips sync exactly
    to narration line changes.

    Returns:
        [
            {
                "order": 1,
                "text": "...",
                "audio_path": "output/audio/scene_1.mp3",
                "label": "scene_1"
            },
            ...
        ]
    """

    os.makedirs(output_dir, exist_ok=True)

    # Build ordered list: hook → scenes → cta
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

        try:
            _generate_voice_gtts(item["text"], audio_path)

            scene_audios.append({
                "order": item["order"],
                "text": item["text"],
                "audio_path": audio_path,
                "label": item["label"]
            })

        except Exception as e:
            print(f"  Voice failed for {item['label']}: {e}")
            # Skip this scene, don't crash the pipeline
            continue

    print(f"\nGenerated {len(scene_audios)} scene audio files")

    return scene_audios