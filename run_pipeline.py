import json
import os
import traceback

from collectors.news_collector import fetch_news

from generators.script_generator import generate_script
from generators.voice_generator import generate_voice

from downloaders.pexels_downloader import download_videos

from renderers.video_renderer import create_video

from database.db import get_connection

from utils.audio_utils import build_narration


def run_pipeline():

    print("=" * 70)
    print("PIPELINE STARTED")
    print("=" * 70)

    topics = fetch_news()

    if not topics:
        print("No news found.")
        return

    for index, topic in enumerate(topics[:5], start=1):

        title = topic.get("title", "Untitled")

        try:

            print("\n")
            print("=" * 70)
            print(f"({index}/{min(5, len(topics))}) {title}")
            print("=" * 70)

            # --------------------------------------------------
            # Generate structured video plan
            # --------------------------------------------------

            script = generate_script(topic)

            print("\nVideo plan generated.")

            # --------------------------------------------------
            # Build narration
            # --------------------------------------------------

            narration = build_narration(script)

            print("\nNarration:\n")
            print(narration)

            # --------------------------------------------------
            # Generate Voice
            # --------------------------------------------------

            audio_path = generate_voice(narration)

            print("\nVoice generated:")
            print(audio_path)

            # --------------------------------------------------
            # Extract keywords directly from scenes
            # --------------------------------------------------

            keywords = []

            for scene in script.get("scenes", []):

                keyword = scene.get("keyword")

                if keyword:
                    keywords.append(keyword)

            print("\nVisual Keywords")

            for keyword in keywords:
                print(f" • {keyword}")

            # --------------------------------------------------
            # Download Pexels clips
            # --------------------------------------------------

            clips = download_videos(keywords)

            if not clips:

                print("\nNo Pexels clips found.")
                print("Using fallback background.")

            else:

                print(f"\nDownloaded {len(clips)} clips")

                for clip in clips:
                    print(
                        f" • {clip['keyword']} -> "
                        f"{os.path.basename(clip['path'])}"
                    )

            # --------------------------------------------------
            # Render Reel
            # --------------------------------------------------

            video_path = create_video(
                audio_path=audio_path,
                clips=clips
            )

            print("\nReel Created")
            print(video_path)

            # --------------------------------------------------
            # Save JSON script
            # --------------------------------------------------

            conn = get_connection()
            cur = conn.cursor()

            cur.execute(
                """
                INSERT INTO scripts
                (topic_id, script_text)
                VALUES (%s, %s)
                """,
                (
                    topic.get("id"),
                    json.dumps(script)
                )
            )

            conn.commit()

            cur.close()
            conn.close()

            print("\nSaved to database.")

        except Exception as e:

            print("\nFAILED")
            print(title)
            print(e)
            traceback.print_exc()

    print("\n")
    print("=" * 70)
    print("PIPELINE FINISHED")
    print("=" * 70)


if __name__ == "__main__":
    run_pipeline()