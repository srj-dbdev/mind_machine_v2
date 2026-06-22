import json
import os
import traceback

from collectors.news_collector import fetch_news

from generators.script_generator import generate_script
from generators.voice_generator import generate_voice_per_scene

from downloaders.pexels_downloader import download_assets

from renderers.video_renderer import create_video

from database.db import get_connection


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
            # Generate structured video plan (8-10 scenes)
            # --------------------------------------------------

            script = generate_script(topic)

            print("\nVideo plan generated.")

            scenes = script.get("scenes", [])

            print(f"Scenes: {len(scenes)}")

            # --------------------------------------------------
            # Generate one audio file per scene
            # --------------------------------------------------

            print("\nGenerating per-scene audio...")

            scene_audios = generate_voice_per_scene(script)

            print(f"\nScene audios generated: {len(scene_audios)}")

            # --------------------------------------------------
            # Download one asset per scene
            # (Pexels video first, Pixabay image fallback)
            # --------------------------------------------------

            print("\nDownloading assets...")

            assets = download_assets(scenes)

            # --------------------------------------------------
            # Align assets with scene_audios
            # scenes list may be longer than scene_audios
            # (hook and cta are in scene_audios but not in scenes)
            # so we build a combined list in order
            # --------------------------------------------------

            # scene_audios includes hook, scenes, cta
            # assets are indexed to scenes only
            # We need to pair them carefully:
            #   hook audio   → no asset (use first asset)
            #   scene audios → matching asset by position
            #   cta audio    → no asset (use last asset)

            paired_audios = []
            paired_assets = []

            scene_index = 0

            for sa in scene_audios:

                label = sa.get("label", "")

                if label == "hook":
                    # Use first available asset for hook
                    first_asset = next(
                        (a for a in assets if a is not None), None
                    )
                    paired_audios.append(sa)
                    paired_assets.append(first_asset)

                elif label == "cta":
                    # Use last available asset for cta
                    last_asset = next(
                        (a for a in reversed(assets) if a is not None), None
                    )
                    paired_audios.append(sa)
                    paired_assets.append(last_asset)

                else:
                    # Scene — match by position
                    asset = assets[scene_index] if scene_index < len(assets) else None
                    paired_audios.append(sa)
                    paired_assets.append(asset)
                    scene_index += 1

            print(f"\nPaired {len(paired_audios)} audio segments with assets")

            for i, (sa, asset) in enumerate(
                zip(paired_audios, paired_assets)
            ):
                asset_type = asset["media_type"] if asset else "missing"
                asset_kw = asset["keyword"] if asset else "none"
                print(
                    f"  {i+1}. [{asset_type}] {asset_kw} "
                    f"← {sa['text'][:40]}"
                )

            # --------------------------------------------------
            # Render reel with per-scene sync
            # --------------------------------------------------

            print("\nRendering reel...")

            video_path = create_video(
                scene_audios=paired_audios,
                scenes=paired_assets
            )

            print("\nReel created:")
            print(video_path)

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