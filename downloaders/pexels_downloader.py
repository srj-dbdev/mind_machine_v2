import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("PEXELS_API_KEY")

HEADERS = {
    "Authorization": API_KEY
}


def score_video(video_file):
    """
    Score a video file.

    Higher score is better.
    """

    width = video_file.get("width", 0)
    height = video_file.get("height", 0)

    score = width + height

    # Strongly prefer vertical videos
    if height > width:
        score += 5000

    # Prefer Full HD+
    if height >= 1920:
        score += 3000

    if width >= 1080:
        score += 3000

    return score


def download_videos(
    keywords,
    output_dir="output/clips",
    max_total_videos=5
):
    """
    Downloads the best clips across all keywords.

    Returns:
        [
            {
                "keyword": "...",
                "path": "...",
                "score": ...
            }
        ]
    """

    os.makedirs(output_dir, exist_ok=True)

    downloaded = []
    seen_video_ids = set()

    # Remove duplicate keywords while preserving order
    keywords = list(dict.fromkeys(keywords))

    for keyword in keywords:

        if len(downloaded) >= max_total_videos:
            break

        print(f"\nSearching Pexels for: {keyword}")

        url = (
            "https://api.pexels.com/videos/search"
            f"?query={keyword}"
            "&per_page=10"
        )

        response = requests.get(url, headers=HEADERS)

        if response.status_code != 200:
            print("Pexels API Error:", response.text)
            continue

        videos = response.json().get("videos", [])

        if not videos:
            print("No videos found.")
            continue

        candidates = []

        for video in videos:

            if video["id"] in seen_video_ids:
                continue

            best_file = max(
                video["video_files"],
                key=score_video
            )

            candidates.append({
                "video_id": video["id"],
                "keyword": keyword,
                "video_url": best_file["link"],
                "score": score_video(best_file)
            })

        candidates.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        for candidate in candidates:

            if candidate["video_id"] in seen_video_ids:
                continue

            filename = (
                f"{len(downloaded)+1}_"
                f"{keyword.replace(' ','_')}.mp4"
            )

            filepath = os.path.join(
                output_dir,
                filename
            )

            print("Downloading:", filename)

            r = requests.get(candidate["video_url"])

            with open(filepath, "wb") as f:
                f.write(r.content)

            downloaded.append({
                "keyword": keyword,
                "path": filepath,
                "score": candidate["score"]
            })

            seen_video_ids.add(candidate["video_id"])

            break

    print("\nDownloaded clips:")

    for clip in downloaded:
        print("-", clip["keyword"])

    return downloaded