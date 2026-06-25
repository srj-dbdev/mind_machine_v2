import json
import os
import traceback

from collectors.news_collector import fetch_news

from generators.script_generator import generate_script
from generators.voice_generator import generate_voice_per_scene
from generators.image_generator import generate_images_for_scenes

from downloaders.visuals_downloader import download_assets

from renderers.video_renderer import create_video

from utils.subtitle_generator import generate_subtitles

from database.db import get_connection


def run_pipeline(max_reels=1):
    """
    Runs the full reel generation pipeline.

    Args:
        max_reels (int): Number of news topics to process.
                         Default is 1 for testing.
                         Set to 5 for production runs.
    """

    print("=" * 70)
    print("PIPELINE STARTED")
    print(f"Reels to generate: {max_reels}")
    print("=" * 70)

    topics = fetch_news()

    if not topics:
        print("No news found.")
        return

    total = min(max_reels, len(topics))

    for index, topic in enumerate(topics[:max_reels], start=1):

        title = topic.get("title", "Untitled")

        try:

            print("\n")
            print("=" * 70)
            print(f"({index}/{total}) {title}")
            print("=" * 70)

            # --------------------------------------------------
            # Generate structured video plan (8-10 scenes)
            # --------------------------------------------------

            script = generate_script(topic)
            scenes = script.get("scenes", [])
            print(f"\nVideo plan generated — {len(scenes)} scenes")

            # --------------------------------------------------
            # Generate one audio file per scene
            # --------------------------------------------------

            print("\nGenerating per-scene audio...")
            scene_audios = generate_voice_per_scene(script)
            print(f"Scene audios: {len(scene_audios)}")

            # --------------------------------------------------
            # Generate Whisper subtitles from scene audio
            # --------------------------------------------------

            print("\nGenerating subtitles via Whisper...")
            subtitles = generate_subtitles(scene_audios)

            # --------------------------------------------------
            # Generate DALL-E images for scenes
            # Falls back to Pexels/Pixabay if generation fails
            # --------------------------------------------------

            print("\nGenerating scene images...")
            dalle_assets = generate_images_for_scenes(
                scenes,
                headline=title
            )

            # For any scene where DALL-E failed, try visuals downloader
            assets = []

            for i, (scene, dalle_asset) in enumerate(
                zip(scenes, dalle_assets)
            ):
                if dalle_asset is not None:
                    assets.append(dalle_asset)
                else:
                    print(
                        f"\nDALL-E failed for scene {i+1} "
                        f"— trying Pexels/Pixabay fallback"
                    )
                    fallback = download_assets(
                        [scene],
                        output_dir="output/clips"
                    )
                    assets.append(fallback[0] if fallback else None)

            # --------------------------------------------------
            # Pair scene_audios with assets
            # hook and cta reuse first/last asset
            # --------------------------------------------------

            paired_audios = []
            paired_assets = []
            scene_index = 0

            for sa in scene_audios:

                label = sa.get("label", "")

                if label == "hook":
                    first_asset = next(
                        (a for a in assets if a is not None), None
                    )
                    paired_audios.append(sa)
                    paired_assets.append(first_asset)

                elif label == "cta":
                    last_asset = next(
                        (a for a in reversed(assets) if a is not None), None
                    )
                    paired_audios.append(sa)
                    paired_assets.append(last_asset)

                else:
                    asset = (
                        assets[scene_index]
                        if scene_index < len(assets)
                        else None
                    )
                    paired_audios.append(sa)
                    paired_assets.append(asset)
                    scene_index += 1

            print(f"\nPaired {len(paired_audios)} segments:")

            for i, (sa, asset) in enumerate(
                zip(paired_audios, paired_assets)
            ):
                asset_info = (
                    f"[{asset['source']}] {asset['media_type']}"
                    if asset else "missing"
                )
                print(
                    f"  {i+1}. {asset_info} "
                    f"← {sa['text'][:50]}"
                )

            # --------------------------------------------------
            # Render reel with per-scene sync + subtitles
            # --------------------------------------------------

            print("\nRendering reel...")

            video_path = create_video(
                scene_audios=paired_audios,
                scenes=paired_assets,
                subtitles=subtitles,
                hook_text=script.get("hook", "")
            )

            print(f"\nReel created: {video_path}")

            # --------------------------------------------------
            # Save script to DB
            # --------------------------------------------------

            conn = get_connection()
            cur = conn.cursor()

            cur.execute(
                """
                INSERT INTO scripts (topic_id, script_text)
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

            print("Saved to database.")

        except Exception as e:

            print("\nFAILED")
            print(f"Topic: {title}")
            print(f"Error: {e}")
            traceback.print_exc()

    print("\n")
    print("=" * 70)
    print("PIPELINE FINISHED")
    print("=" * 70)


if __name__ == "__main__":

    # ---------------------------------------------------
    # Change max_reels here for testing vs production
    # ---------------------------------------------------

    run_pipeline(max_reels=1)   # testing
    # run_pipeline(max_reels=5) # production