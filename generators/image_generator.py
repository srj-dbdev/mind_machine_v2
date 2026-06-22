import os
import base64

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPEN_AI_API_KEY")
)

# ---------------------------------------------------
# Model config — switch here when ready for production
# ---------------------------------------------------

DALL_E_MODEL = "gpt-image-1-mini"   # testing  (~$0.005/image)
# DALL_E_MODEL = "gpt-image-1"      # production (~$0.011-0.167/image)

IMAGE_SIZE = "1024x1024"            # square — works for all models
# IMAGE_SIZE = "1024x1536"          # portrait — better for reels (gpt-image-1 only)

IMAGE_QUALITY = "low"               # low = cheapest (~$0.005)
# IMAGE_QUALITY = "medium"          # medium = balanced
# IMAGE_QUALITY = "high"            # high = best quality, most expensive


# ---------------------------------------------------
# Build a clean image prompt from scene data
# ---------------------------------------------------

def build_image_prompt(scene):
    """
    Builds a GPT Image prompt from a scene dict.
    Expects scene keys: text, keyword, mood
    """

    text = scene.get("text", "")
    keyword = scene.get("keyword", "")
    mood = scene.get("mood", "neutral")

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
    Generates a GPT Image for a single scene.

    Returns:
        dict with keys: keyword, path, media_type, source
        or None if generation fails
    """

    os.makedirs(output_dir, exist_ok=True)

    keyword = scene.get("keyword", f"scene_{index}")
    prompt = build_image_prompt(scene)

    print(f"  Generating image for: {keyword}")
    print(f"  Prompt: {prompt[:80]}...")

    try:
        response = client.images.generate(
            model=DALL_E_MODEL,
            prompt=prompt,
            n=1,
            size=IMAGE_SIZE,
            quality=IMAGE_QUALITY
        )

        # GPT Image models return base64, not a URL
        image_data = base64.b64decode(response.data[0].b64_json)

        filename = f"{index}_{keyword.replace(' ', '_')}.png"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "wb") as f:
            f.write(image_data)

        print(f"  ✓ Saved: {filename}")

        return {
            "keyword": keyword,
            "path": filepath,
            "media_type": "image",
            "source": "dalle",
            "score": 1000
        }

    except Exception as e:
        print(f"  Image generation error for scene {index}: {e}")
        return None


# ---------------------------------------------------
# Generate images for all scenes
# ---------------------------------------------------

def generate_images_for_scenes(scenes, output_dir="output/clips"):
    """
    Generates one GPT Image per scene.

    Expects:
        scenes = list of scene dicts from script JSON

    Returns:
        list of asset dicts (or None where generation failed)
    """

    cost_per_image = 0.005
    estimated_cost = len(scenes) * cost_per_image
    estimated_inr = estimated_cost * 84  # approximate USD to INR

    print(f"\nGenerating {len(scenes)} images ({DALL_E_MODEL}, {IMAGE_QUALITY} quality)")
    print(f"Estimated cost: ~${estimated_cost:.3f} USD (~₹{estimated_inr:.1f})\n")

    assets = []

    for index, scene in enumerate(scenes, start=1):
        asset = generate_image_for_scene(scene, output_dir, index)
        assets.append(asset)

    success = sum(1 for a in assets if a is not None)
    failed = sum(1 for a in assets if a is None)

    print(f"\nImage generation: {success} succeeded, {failed} failed")

    return assets