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
# Pexels video scoring
# ---------------------------------------------------

def score_video(video_file):
    """
    Score a video file. Higher is better.
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


# ---------------------------------------------------
# Pexels video search
# ---------------------------------------------------

def search_pexels_video(keyword, output_dir, index):
    """
    Search Pexels for a video matching the keyword.

    Returns:
        dict with keys: keyword, path, score, media_type="video"
        or None if nothing found
    """

    url = (
        "https://api.pexels.com/videos/search"
        f"?query={keyword}"
        "&per_page=10"
    )

    response = requests.get(url, headers=PEXELS_HEADERS)

    if response.status_code != 200:
        print(f"  Pexels video error for '{keyword}': {response.status_code}")
        return None

    videos = response.json().get("videos", [])

    if not videos:
        print(f"  No Pexels videos found for: {keyword}")
        return None

    # Score and pick the best
    candidates = []

    for video in videos:
        best_file = max(video["video_files"], key=score_video)
        candidates.append({
            "video_id": video["id"],
            "video_url": best_file["link"],
            "score": score_video(best_file)
        })

    candidates.sort(key=lambda x: x["score"], reverse=True)
    best = candidates[0]

    filename = f"{index}_{keyword.replace(' ', '_')}.mp4"
    filepath = os.path.join(output_dir, filename)

    print(f"  Downloading Pexels video: {filename}")

    r = requests.get(best["video_url"])

    with open(filepath, "wb") as f:
        f.write(r.content)

    return {
        "keyword": keyword,
        "path": filepath,
        "score": best["score"],
        "media_type": "video"
    }


# ---------------------------------------------------
# Pixabay image fallback
# ---------------------------------------------------

def search_pixabay_image(keyword, output_dir, index):
    """
    Search Pixabay for an image matching the keyword.

    Returns:
        dict with keys: keyword, path, score, media_type="image"
        or None if nothing found
    """

    if not PIXABAY_API_KEY:
        print("  PIXABAY_API_KEY not set — skipping image fallback")
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

    response = requests.get(url)

    if response.status_code != 200:
        print(f"  Pixabay error for '{keyword}': {response.status_code}")
        return None

    hits = response.json().get("hits", [])

    if not hits:
        print(f"  No Pixabay images found for: {keyword}")
        return None

    # Pick highest resolution image
    best = max(hits, key=lambda x: x.get("imageWidth", 0))

    image_url = best.get("largeImageURL") or best.get("webformatURL")

    if not image_url:
        return None

    filename = f"{index}_{keyword.replace(' ', '_')}.jpg"
    filepath = os.path.join(output_dir, filename)

    print(f"  Downloading Pixabay image: {filename}")

    r = requests.get(image_url)

    with open(filepath, "wb") as f:
        f.write(r.content)

    return {
        "keyword": keyword,
        "path": filepath,
        "score": 0,
        "media_type": "image"
    }


# ---------------------------------------------------
# Main downloader — one asset per scene
# ---------------------------------------------------

def download_assets(scenes, output_dir="output/clips"):
    """
    Downloads one asset per scene — video preferred, image fallback.

    Expects:
        scenes = list of dicts with "keyword" key (from script JSON)

    Returns:
        [
            {
                "keyword": "...",
                "path": "...",
                "media_type": "video" | "image",
                "score": ...
            }
        ]
    """

    os.makedirs(output_dir, exist_ok=True)

    assets = []

    for index, scene in enumerate(scenes, start=1):

        keyword = scene.get("keyword", "").strip()

        if not keyword:
            print(f"  Scene {index}: no keyword, skipping")
            assets.append(None)
            continue

        print(f"\nScene {index}: searching for '{keyword}'")

        # Try Pexels video first
        asset = search_pexels_video(keyword, output_dir, index)

        # Fall back to Pixabay image
        if asset is None:
            print(f"  Falling back to Pixabay image for: {keyword}")
            asset = search_pixabay_image(keyword, output_dir, index)

        if asset is None:
            print(f"  No asset found for scene {index}: {keyword}")

        assets.append(asset)

    # Summary
    videos = sum(1 for a in assets if a and a["media_type"] == "video")
    images = sum(1 for a in assets if a and a["media_type"] == "image")
    missing = sum(1 for a in assets if a is None)

    print(f"\nAssets downloaded: {videos} videos, {images} images, {missing} missing")

    return assets