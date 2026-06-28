import json
import os
import traceback

from collectors.news_collector import fetch_news

from generators.script_generator import generate_script
from generators.voice_generator import generate_voice_per_scene
from generators.image_generator import (
    generate_images_for_scenes,
    generate_card_background
)

from downloaders.visuals_downloader import download_assets

from renderers.video_renderer import create_video

from utils.subtitle_generator import generate_subtitles

from utils.logger import setup_logger

from database.db import get_connection


def run_pipeline(max_reels=1):
    """
    Runs the full reel generation pipeline.

    Args:
        max_reels (int): Number of news topics to process.
                         Default is 1 for testing.
                         Set to 5 for production runs.
    """

    log = setup_logger()

    log.info("=" * 70)
    log.info("PIPELINE STARTED")
    log.info(f"Reels to generate: {max_reels}")
    log.info("=" * 70)

    topics = fetch_news()

    if not topics:
        log.warning("No news found.")
        return

    total = min(max_reels, len(topics))

    for index, topic in enumerate(topics[:max_reels], start=1):

        title = topic.get("title", "Untitled")

        try:

            log.info("")
            log.info("=" * 70)
            log.info(f"({index}/{total}) {title}")
            log.info("=" * 70)

            # --------------------------------------------------
            # Generate structured video plan (8-10 scenes)
            # --------------------------------------------------

            script = generate_script(topic)
            scenes = script.get("scenes", [])
            hook_text = script.get("hook", "")
            cta_text = script.get("cta", "")
            style = script.get("style", "breaking_news")
            music_mood = script.get("music_mood", "dramatic")

            log.info(f"Video plan generated — {len(scenes)} scenes")
            log.info(f"Style: {style} | Mood: {music_mood}")
            log.debug(f"hook_text: {hook_text}")
            log.debug(f"cta_text: {cta_text}")

            # --------------------------------------------------
            # Generate card background image
            # --------------------------------------------------

            log.info("Generating card background...")
            card_background = generate_card_background(
                style=style,
                music_mood=music_mood,
                output_dir="output/clips"
            )

            log.debug(f"card_background: {card_background}")

            if card_background is None:
                log.warning("Card background generation failed — cards will use black background")

            # --------------------------------------------------
            # Generate one audio file per scene
            # --------------------------------------------------

            log.info("Generating per-scene audio...")
            scene_audios = generate_voice_per_scene(script)
            log.info(f"Scene audios generated: {len(scene_audios)}")

            # --------------------------------------------------
            # Generate Whisper subtitles from scene audio
            # --------------------------------------------------

            log.info("Generating subtitles via Whisper...")
            subtitles = generate_subtitles(scene_audios)
            log.info(f"Subtitles generated for {len(subtitles)} scenes")

            # --------------------------------------------------
            # Generate DALL-E images for scenes
            # --------------------------------------------------

            log.info("Generating scene images...")
            dalle_assets = generate_images_for_scenes(
                scenes,
                headline=title
            )

            assets = []

            for i, (scene, dalle_asset) in enumerate(
                zip(scenes, dalle_assets)
            ):
                if dalle_asset is not None:
                    assets.append(dalle_asset)
                else:
                    log.warning(
                        f"DALL-E failed for scene {i+1} "
                        f"— trying Pexels/Pixabay fallback"
                    )
                    fallback = download_assets(
                        [scene],
                        output_dir="output/clips"
                    )
                    assets.append(fallback[0] if fallback else None)

            # --------------------------------------------------
            # Pair scene_audios with assets
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

            log.info(f"Paired {len(paired_audios)} segments:")

            for i, (sa, asset) in enumerate(
                zip(paired_audios, paired_assets)
            ):
                asset_info = (
                    f"[{asset['source']}] {asset['media_type']}"
                    if asset else "missing"
                )
                log.info(f"  {i+1}. {asset_info} ← {sa['text'][:50]}")

            # --------------------------------------------------
            # Render reel
            # --------------------------------------------------

            log.info("Rendering reel...")
            log.debug(f"Passing to create_video — hook_text='{hook_text}'")
            log.debug(f"Passing to create_video — cta_text='{cta_text}'")
            log.debug(f"Passing to create_video — card_background={card_background}")

            video_path = create_video(
                scene_audios=paired_audios,
                scenes=paired_assets,
                subtitles=subtitles,
                hook_text=hook_text,
                cta_text=cta_text,
                card_background=card_background
            )

            log.info(f"Reel created: {video_path}")

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

            log.info("Saved to database.")

        except Exception as e:
            log.error(f"FAILED: {title}")
            log.exception(e)

    log.info("")
    log.info("=" * 70)
    log.info("PIPELINE FINISHED")
    log.info("=" * 70)


if __name__ == "__main__":

    # ---------------------------------------------------
    # Change max_reels here for testing vs production
    # ---------------------------------------------------

    run_pipeline(max_reels=1)   # testing
    # run_pipeline(max_reels=5) # production