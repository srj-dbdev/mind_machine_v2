import os
import requests
from dotenv import load_dotenv

load_dotenv()

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")

PEXELS_HEADERS = {
    "Authorization": PEXELS_API_KEY
}


# ---------------------------------------------------
# Source 1: Pexels Video
# ---------------------------------------------------

def score_pexels_video(video_file):
    """
    Score a Pexels video file. Higher is better.
    Strongly prefers vertical HD.
    """

    width = video_file.get("width", 0)
    height = video_file.get("height", 0)
    score = width + height

    if height > width:
        score += 5000
    if height >= 1920:
        score += 3000
    if width >= 1080:
        score += 3000

    return score


def search_pexels_video(keyword, output_dir, index):
    """
    Search Pexels for a stock video matching the keyword.

    Returns:
        dict with keys: keyword, path, score, media_type, source
        or None if nothing found
    """

    if not PEXELS_API_KEY:
        print(f"  PEXELS_API_KEY not set — skipping Pexels")
        return None

    url = (
        "https://api.pexels.com/videos/search"
        f"?query={keyword}"
        "&per_page=10"
    )

    try:
        response = requests.get(url, headers=PEXELS_HEADERS, timeout=10)

        if response.status_code != 200:
            print(f"  Pexels error for '{keyword}': {response.status_code}")
            return None

        videos = response.json().get("videos", [])

        if not videos:
            print(f"  No Pexels videos for: {keyword}")
            return None

        candidates = []

        for video in videos:
            best_file = max(video["video_files"], key=score_pexels_video)
            candidates.append({
                "video_url": best_file["link"],
                "score": score_pexels_video(best_file)
            })

        candidates.sort(key=lambda x: x["score"], reverse=True)
        best = candidates[0]

        filename = f"{index}_{keyword.replace(' ', '_')}.mp4"
        filepath = os.path.join(output_dir, filename)

        print(f"  Downloading Pexels video: {filename}")

        r = requests.get(best["video_url"], timeout=30)

        with open(filepath, "wb") as f:
            f.write(r.content)

        return {
            "keyword": keyword,
            "path": filepath,
            "score": best["score"],
            "media_type": "video",
            "source": "pexels"
        }

    except Exception as e:
        print(f"  Pexels exception for '{keyword}': {e}")
        return None


# ---------------------------------------------------
# Source 2: Pixabay Image
# ---------------------------------------------------

def search_pixabay_image(keyword, output_dir, index):
    """
    Search Pixabay for a stock image matching the keyword.

    Returns:
        dict with keys: keyword, path, score, media_type, source
        or None if nothing found
    """

    if not PIXABAY_API_KEY:
        print(f"  PIXABAY_API_KEY not set — skipping Pixabay")
        return None

    url = (
        "https://pixabay.com/api/"
        f"?key={PIXABAY_API_KEY}"
        f"&q={keyword.replace(' ', '+')}"
        "&image_type=photo"
        "&orientation=vertical"
        "&min_width=1080"
        "&per_page=10"
        "&safesearch=true"
    )

    try:
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            print(f"  Pixabay error for '{keyword}': {response.status_code}")
            return None

        hits = response.json().get("hits", [])

        if not hits:
            print(f"  No Pixabay images for: {keyword}")
            return None

        best = max(hits, key=lambda x: x.get("imageWidth", 0))
        image_url = best.get("largeImageURL") or best.get("webformatURL")

        if not image_url:
            return None

        filename = f"{index}_{keyword.replace(' ', '_')}.jpg"
        filepath = os.path.join(output_dir, filename)

        print(f"  Downloading Pixabay image: {filename}")

        r = requests.get(image_url, timeout=10)

        with open(filepath, "wb") as f:
            f.write(r.content)

        return {
            "keyword": keyword,
            "path": filepath,
            "score": 0,
            "media_type": "image",
            "source": "pixabay"
        }

    except Exception as e:
        print(f"  Pixabay exception for '{keyword}': {e}")
        return None


# ---------------------------------------------------
# Main downloader — Pexels first, Pixabay second
# Only called when DALL-E fails in run_pipeline.py
# ---------------------------------------------------

def download_assets(scenes, output_dir="output/clips"):
    """
    Downloads one asset per scene as a fallback when DALL-E fails.

    Priority:
        1. Pexels video
        2. Pixabay image

    Expects:
        scenes = list of scene dicts with "keyword" key

    Returns:
        list of asset dicts (or None where nothing found)
    """

    os.makedirs(output_dir, exist_ok=True)

    assets = []

    for index, scene in enumerate(scenes, start=1):

        keyword = scene.get("keyword", "").strip()

        if not keyword:
            print(f"\nScene {index}: no keyword, skipping")
            assets.append(None)
            continue

        print(f"\nFallback scene {index}: '{keyword}'")

        # 1. Try Pexels video
        asset = search_pexels_video(keyword, output_dir, index)

        # 2. Fall back to Pixabay image
        if asset is None:
            print(f"  Pexels found nothing — trying Pixabay")
            asset = search_pixabay_image(keyword, output_dir, index)

        if asset is None:
            print(f"  No fallback asset found for: '{keyword}'")
        else:
            print(
                f"  ✓ [{asset['source']}] {asset['media_type']} "
                f"— {os.path.basename(asset['path'])}"
            )

        assets.append(asset)

    # Summary
    pexels = sum(1 for a in assets if a and a["source"] == "pexels")
    pixabay = sum(1 for a in assets if a and a["source"] == "pixabay")
    missing = sum(1 for a in assets if a is None)

    print(f"\nFallback assets: {pexels} Pexels | {pixabay} Pixabay | {missing} missing")

    return assets