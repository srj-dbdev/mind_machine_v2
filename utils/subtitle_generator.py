import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPEN_AI_API_KEY")
)

# ---------------------------------------------------
# Whisper model config
# ---------------------------------------------------

# WHISPER_MODEL = "gpt-4o-mini-transcribe"  # cheapest (~$0.003/min)
WHISPER_MODEL = "whisper-1"             # standard (~$0.006/min)


# ---------------------------------------------------
# Transcribe one audio file with word timestamps
# ---------------------------------------------------

def transcribe_audio(audio_path):
    """
    Transcribes an audio file using Whisper and returns
    word-level timestamps.

    Args:
        audio_path: path to MP3 audio file

    Returns:
        [
            {"word": "Kevin", "start": 0.0, "end": 0.3},
            {"word": "Warsh", "start": 0.3, "end": 0.6},
            ...
        ]
        or [] if transcription fails
    """

    if not os.path.exists(audio_path):
        print(f"  Audio file not found: {audio_path}")
        return []

    try:
        with open(audio_path, "rb") as f:
            response = client.audio.transcriptions.create(
                model=WHISPER_MODEL,
                file=f,
                response_format="verbose_json",
                timestamp_granularities=["word"]
            )

        words = []

        if hasattr(response, "words") and response.words:
            for w in response.words:
                words.append({
                    "word": w.word.strip(),
                    "start": float(w.start),
                    "end": float(w.end)
                })

        return words

    except Exception as e:
        print(f"  Whisper transcription failed for {audio_path}: {e}")
        return []


# ---------------------------------------------------
# Group words into subtitle chunks
# ---------------------------------------------------

def group_words_into_chunks(words, max_words_per_chunk=4):
    """
    Groups word-level timestamps into subtitle chunks
    for display. Each chunk shows max_words_per_chunk
    words at a time.

    Args:
        words:               list of word timestamp dicts
        max_words_per_chunk: how many words per subtitle line

    Returns:
        [
            {
                "text": "Kevin Warsh is reshaping",
                "start": 0.0,
                "end": 1.6
            },
            ...
        ]
    """

    if not words:
        return []

    chunks = []
    current_chunk = []

    for word in words:
        current_chunk.append(word)

        if len(current_chunk) >= max_words_per_chunk:
            chunks.append({
                "text": " ".join(w["word"] for w in current_chunk),
                "start": current_chunk[0]["start"],
                "end": current_chunk[-1]["end"]
            })
            current_chunk = []

    # Add any remaining words
    if current_chunk:
        chunks.append({
            "text": " ".join(w["word"] for w in current_chunk),
            "start": current_chunk[0]["start"],
            "end": current_chunk[-1]["end"]
        })

    return chunks


# ---------------------------------------------------
# Generate subtitles for all scene audios
# ---------------------------------------------------

def generate_subtitles(scene_audios):
    """
    Generates word-level subtitle chunks for all scene audios.

    Args:
        scene_audios: list of scene audio dicts from voice_generator

    Returns:
        [
            {
                "label": "scene_1",
                "audio_path": "...",
                "chunks": [
                    {"text": "Kevin Warsh is", "start": 0.0, "end": 1.2},
                    ...
                ]
            },
            ...
        ]
    """

    print(f"\nGenerating subtitles for {len(scene_audios)} scenes...")

    results = []

    for sa in scene_audios:

        label = sa.get("label", "")
        audio_path = sa.get("audio_path", "")

        print(f"  Transcribing: {label}")

        words = transcribe_audio(audio_path)

        chunks = group_words_into_chunks(words, max_words_per_chunk=4)

        print(f"  ✓ {len(words)} words → {len(chunks)} subtitle chunks")

        results.append({
            "label": label,
            "audio_path": audio_path,
            "chunks": chunks
        })

    print(f"\nSubtitles generated for {len(results)} scenes")

    return results