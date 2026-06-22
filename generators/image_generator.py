import os
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPEN_AI_API_KEY")
)

# ---------------------------------------------------
# Model config — switch here when ready for production
# ---------------------------------------------------

DALL_E_MODEL = "dall-e-2"       # testing  (~$0.002/image)
# DALL_E_MODEL = "dall-e-3"     # production (~$0.04/image)

IMAGE_SIZE = "512x512"          # dall-e-2 testing (cheapest)
# IMAGE_SIZE = "1024x1024"      # dall-e-2 better quality
# IMAGE_SIZE = "1024x1792"      # dall-e-3 vertical (best for reels)


# ---------------------------------------------------
# Build a clean image prompt from scene data
# ---------------------------------------------------

def build_image_prompt(scene):
    """
    Builds a DALL-E prompt from a scene dict.

    Expects scene keys: text, keyword, mood
    """

    text = scene.get("text", "")
    keyword = scene.get("keyword", "")
    mood = scene.get("mood", "neutral")

    # Map mood to visual style guidance
    mood_styles = {
        "dramatic":  "dramatic lighting, high contrast, cinematic",
        "positive":  "bright, optimistic, warm lighting",
        "neutral":   "clean, professional, journalistic",
        "urgent":    "intense, fast-paced, bold colors",
        "hopeful":   "soft lighting, uplifting, warm tones",
        "serious":   "muted tones, documentary style, realistic"
    }

    style = mood_styles.get(mood, "clean, professional, photorealistic")

    prompt = (
        f"{keyword}. {text}. "
        f"News photography style. {style}. "
        f"No text, no watermarks, no logos. "
        f"Photorealistic."
    )

    return prompt


# ---------------------------------------------------
# Generate one image for a scene
# ---------------------------------------------------

def generate_image_for_scene(scene, output_dir, index):
    """
    Generates a DALL-E image for a single scene.

    Returns:
        dict with keys: keyword, path, media_type="image", source="dalle"
        or None if generation fails
    """

    os.makedirs(output_dir, exist_ok=True)

    keyword = scene.get("keyword", f"scene_{index}")
    prompt = build_image_prompt(scene)

    print(f"  Generating DALL-E image for: {keyword}")
    print(f"  Prompt: {prompt[:80]}...")

    try:
        response = client.images.generate(
            model=DALL_E_MODEL,
            prompt=prompt,
            n=1,
            size=IMAGE_SIZE
        )

        image_url = response.data[0].url

        # Download the generated image
        r = requests.get(image_url, timeout=30)

        if r.status_code != 200:
            print(f"  Failed to download generated image: {r.status_code}")
            return None

        filename = f"{index}_{keyword.replace(' ', '_')}_dalle.png"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "wb") as f:
            f.write(r.content)

        print(f"  ✓ Saved: {filename}")

        return {
            "keyword": keyword,
            "path": filepath,
            "media_type": "image",
            "source": "dalle",
            "score": 1000
        }

    except Exception as e:
        print(f"  DALL-E error for scene {index}: {e}")
        return None


# ---------------------------------------------------
# Generate images for all scenes
# ---------------------------------------------------

def generate_images_for_scenes(scenes, output_dir="output/clips"):
    """
    Generates one DALL-E image per scene.

    Expects:
        scenes = list of scene dicts from script JSON

    Returns:
        list of asset dicts (or None where generation failed)
    """

    print(f"\nGenerating {len(scenes)} DALL-E images ({DALL_E_MODEL})...")
    print(f"Estimated cost: ~${len(scenes) * 0.002:.3f} USD\n")

    assets = []

    for index, scene in enumerate(scenes, start=1):
        asset = generate_image_for_scene(scene, output_dir, index)
        assets.append(asset)

    # Summary
    success = sum(1 for a in assets if a is not None)
    failed = sum(1 for a in assets if a is None)

    print(f"\nDALL-E generation complete: {success} succeeded, {failed} failed")

    return assets