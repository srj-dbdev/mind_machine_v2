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

IMAGE_SIZE = "1024x1024"
IMAGE_QUALITY = "low"


# ---------------------------------------------------
# Style → visual mood mapping
# ---------------------------------------------------

STYLE_MOOD_MAP = {
    # Dark/moody styles
    ("breaking_news", "dramatic"): "dark",
    ("breaking_news", "serious"):  "dark",
    ("breaking_news", "urgent"):   "dark",
    ("finance",       "serious"):  "dark",
    ("finance",       "dramatic"): "dark",
    ("politics",      "serious"):  "dark",
    ("politics",      "dramatic"): "dark",
    ("world",         "urgent"):   "dark",
    ("world",         "dramatic"): "dark",

    # Vibrant/colorful styles
    ("technology",    "energetic"): "vibrant",
    ("technology",    "uplifting"): "vibrant",
    ("science",       "hopeful"):   "vibrant",
    ("science",       "uplifting"): "vibrant",
    ("sports",        "energetic"): "vibrant",
    ("sports",        "positive"):  "vibrant",

    # Neutral/subtle styles
    ("business",      "calm"):      "neutral",
    ("business",      "serious"):   "neutral",
}

def get_visual_mood(style, music_mood):
    """
    Returns 'dark', 'vibrant', or 'neutral' based on
    script style and music_mood combination.
    """
    key = (style, music_mood)
    if key in STYLE_MOOD_MAP:
        return STYLE_MOOD_MAP[key]

    # Fallback rules by music_mood alone
    if music_mood in ("dramatic", "serious", "urgent"):
        return "dark"
    if music_mood in ("energetic", "uplifting", "positive"):
        return "vibrant"

    return "neutral"


# ---------------------------------------------------
# Build card background prompt
# ---------------------------------------------------

def build_card_background_prompt(style, music_mood, visual_mood):
    """
    Builds a DALL-E prompt for a thematic card background.
    No text, no people — pure cinematic background.
    """

    style_themes = {
        "breaking_news": "news broadcast studio, dramatic lighting",
        "technology":    "futuristic tech environment, circuit patterns, neon glow",
        "finance":       "financial data visualization, abstract market charts",
        "business":      "modern corporate architecture, glass buildings",
        "sports":        "stadium lights, dynamic motion blur",
        "world":         "global map, earth from space, world landmarks",
        "science":       "laboratory equipment, scientific visualization",
        "politics":      "government architecture, flags, institutional buildings"
    }

    mood_styles = {
        "dark":    (
            "dark moody cinematic, deep shadows, dramatic contrast, "
            "low-key lighting, noir atmosphere, very dark background"
        ),
        "vibrant": (
            "vibrant colorful cinematic, bold saturated colors, "
            "dynamic energy, bright dramatic lighting"
        ),
        "neutral": (
            "clean professional cinematic, subtle tones, "
            "balanced lighting, sophisticated atmosphere"
        )
    }

    theme = style_themes.get(style, "abstract cinematic background")
    mood = mood_styles.get(visual_mood, mood_styles["neutral"])

    prompt = (
        f"{theme}. {mood}. "
        f"Vertical 9:16 composition. Abstract background. "
        f"No text, no people, no faces, no logos, no watermarks. "
        f"Photorealistic, high quality."
    )

    return prompt


# ---------------------------------------------------
# Generate card background image
# ---------------------------------------------------

def generate_card_background(style, music_mood, output_dir):
    """
    Generates one thematic background image for title and end cards.
    Used for both cards — generated once per reel.

    Returns:
        dict with path, visual_mood, overlay_opacity
        or None if generation fails
    """

    os.makedirs(output_dir, exist_ok=True)

    visual_mood = get_visual_mood(style, music_mood)
    prompt = build_card_background_prompt(style, music_mood, visual_mood)

    # Overlay opacity — darker image needs less overlay
    overlay_opacity = {
        "dark":    0.35,   # light overlay, image already dark
        "vibrant": 0.55,   # heavier overlay to ensure text readability
        "neutral": 0.45    # medium overlay
    }.get(visual_mood, 0.45)

    print(f"\nGenerating card background...")
    print(f"  Style: {style} | Mood: {music_mood} → {visual_mood}")
    print(f"  Prompt: {prompt[:80]}...")

    try:
        response = client.images.generate(
            model=DALL_E_MODEL,
            prompt=prompt,
            n=1,
            size=IMAGE_SIZE,
            quality=IMAGE_QUALITY
        )

        image_data = base64.b64decode(response.data[0].b64_json)

        filename = f"card_background_{style}_{visual_mood}.png"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "wb") as f:
            f.write(image_data)

        print(f"  ✓ Card background saved: {filename}")

        return {
            "path": filepath,
            "visual_mood": visual_mood,
            "overlay_opacity": overlay_opacity
        }

    except Exception as e:
        print(f"  Card background generation failed: {e}")
        return None


# ---------------------------------------------------
# Build scene image prompt
# ---------------------------------------------------

def build_image_prompt(scene, headline=None):
    """
    Builds a GPT Image prompt from a scene dict.
    If headline provided (first scene), uses full headline as subject.
    """

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

    if headline:
        subject = f"{headline}. Key visual: {keyword}."
    else:
        subject = f"{keyword}. {scene.get('text', '')}."

    prompt = (
        f"{subject} "
        f"News photography style. {style}. "
        f"No text, no watermarks, no logos. "
        f"Photorealistic."
    )

    return prompt


# ---------------------------------------------------
# Generate one image for a scene
# ---------------------------------------------------

def generate_image_for_scene(scene, output_dir, index, headline=None):
    """
    Generates a GPT Image for a single scene.
    """

    os.makedirs(output_dir, exist_ok=True)

    keyword = scene.get("keyword", f"scene_{index}")
    prompt = build_image_prompt(scene, headline=headline)

    if headline:
        print(f"  Generating OPENING image from headline: {headline[:60]}...")
    else:
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

def generate_images_for_scenes(scenes, output_dir="output/clips", headline=None):
    """
    Generates one GPT Image per scene.
    First scene uses full headline for stronger opening image.
    """

    cost_per_image = 0.005
    estimated_cost = len(scenes) * cost_per_image
    estimated_inr = estimated_cost * 84

    print(f"\nGenerating {len(scenes)} images ({DALL_E_MODEL}, {IMAGE_QUALITY} quality)")
    print(f"Estimated cost: ~${estimated_cost:.3f} USD (~₹{estimated_inr:.1f})\n")

    assets = []

    for index, scene in enumerate(scenes, start=1):
        scene_headline = headline if index == 1 else None
        asset = generate_image_for_scene(
            scene, output_dir, index, headline=scene_headline
        )
        assets.append(asset)

    success = sum(1 for a in assets if a is not None)
    failed = sum(1 for a in assets if a is None)

    print(f"\nImage generation: {success} succeeded, {failed} failed")

    return assets