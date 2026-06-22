# 🎬 Mind Machine v2
### Auto-Generated News Reels Pipeline

An automated pipeline that converts breaking news into Instagram-ready Reels using AI — fully generated, narrated, and rendered without any manual editing.

---

## 📌 What It Does

Mind Machine fetches live news headlines, generates a structured video script using GPT, creates scene-by-scene narration audio, generates matching AI images for each scene, and renders a fully synced vertical video reel — automatically.

**One command. One news story. One reel.**

---

## 🏗️ Pipeline Architecture

```
News API
    ↓
fetch_news()          — Fetches latest headlines as structured article dicts
    ↓
generate_script()     — GPT-4.1-mini converts article into 8-10 scene video plan (JSON)
    ↓
generate_voice_per_scene()  — gTTS generates one MP3 audio file per scene
    ↓
generate_images_for_scenes() — GPT Image generates one image per scene
    ↓
download_assets()     — Fallback: Pexels video → Pixabay image if AI generation fails
    ↓
create_video()        — ffmpeg renders scene-synced reel (clips cut on narration change)
    ↓
PostgreSQL            — Script and metadata saved to database
    ↓
output/reel_*.mp4     — Final Instagram Reel (1080x1920, ~45 seconds)
```

---

## 📁 Project Structure

```
mind_machine_v2/
│
├── collectors/
│   └── news_collector.py        # Fetches news from News API
│
├── generators/
│   ├── script_generator.py      # GPT-4.1-mini → structured JSON video plan
│   ├── voice_generator.py       # gTTS → per-scene MP3 audio files
│   ├── keyword_generator.py     # Story-specific visual search keywords
│   └── image_generator.py       # GPT Image (gpt-image-1-mini) → scene images
│
├── downloaders/
│   └── visuals_downloader.py    # Pexels video → Pixabay image fallback chain
│
├── renderers/
│   └── video_renderer.py        # ffmpeg: normalizes, syncs, and renders final reel
│
├── database/
│   └── db.py                    # PostgreSQL connection via psycopg2
│
├── utils/
│   └── audio_utils.py           # Text cleaning and narration builder
│
├── output/                      # Generated reels, audio, clips (gitignored)
├── run_pipeline.py              # Main pipeline entry point
├── .env.example                 # Environment variable reference (no secrets)
└── README.md
```

---

## ⚙️ How It Works

### 1. News Collection
Fetches the latest headlines from News API, returning structured article dicts with title, description, content, and source.

### 2. Script Generation
GPT-4.1-mini converts a single news article into a structured JSON video plan:
```json
{
    "title": "...",
    "hook": "...",
    "cta": "...",
    "style": "breaking_news",
    "music_mood": "dramatic",
    "scenes": [
        {
            "order": 1,
            "text": "Narration sentence for this scene",
            "keyword": "story-specific visual keyword",
            "overlay": "Short text overlay",
            "mood": "dramatic"
        }
    ]
}
```
The prompt enforces **story-specific** visual keywords — not generic stock terms like "financial district" but specific subjects like "Federal Reserve building" or "rocket launch pad".

### 3. Voice Generation
gTTS generates one MP3 file per scene (hook → scenes → CTA). Each audio file's duration drives the exact length of its matching video clip — this is what makes the cuts sync to narration changes.

### 4. Image Generation
GPT Image (`gpt-image-1-mini`) generates one photorealistic image per scene using a prompt built from the scene's keyword, narration text, and mood. Returns base64-encoded PNG, decoded and saved locally.

If image generation fails for any scene, `visuals_downloader.py` runs a fallback waterfall:
1. Pexels video search
2. Pixabay image search

### 5. Video Rendering
ffmpeg pipeline in `video_renderer.py`:
- Normalizes all assets (video or image) to `1080x1920` vertical format
- For images: holds frame for exact audio duration using `-loop 1`
- For videos: loops and trims to exact audio duration
- Combines each asset with its matching scene audio
- Concatenates all segments into final reel

### 6. Database Save
Script JSON and topic metadata saved to PostgreSQL for tracking, analytics, and future reuse.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- PostgreSQL
- ffmpeg installed and on PATH

### Installation

```bash
# Clone the repo
git clone https://github.com/srj-dbdev/mind_machine_v2.git
cd mind_machine_v2

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Fill in your API keys in .env
```

### Environment Variables

```env
# News
NEWS_API_KEY=

# OpenAI (script generation + image generation)
OPEN_AI_API_KEY=

# Stock media fallbacks
PEXELS_API_KEY=
PIXABAY_API_KEY=

# Optional
OPENROUTER_API_KEY=
GEMINI_API_KEY=

# Database
DB_HOST=
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_PORT=
```

### Run the Pipeline

```bash
python run_pipeline.py
```

By default, generates **1 reel per run** (cost-controlled for testing).
To change, edit `max_reels` in `run_pipeline.py`:

```python
run_pipeline(max_reels=1)   # testing
run_pipeline(max_reels=5)   # production
```

---

## 💰 Cost Per Reel (Approximate)

| Step | Service | Cost |
|---|---|---|
| Script generation | GPT-4.1-mini | ~$0.001 |
| Voice narration | gTTS | Free |
| Image generation (10 scenes) | gpt-image-1-mini low | ~$0.05 |
| Stock fallback | Pexels / Pixabay | Free |
| **Total** | | **~$0.05 (~₹4)** |

---

## 🗂️ Git Workflow

This project follows a branch-per-feature workflow:

```bash
# Create a branch for each fix or feature
git checkout -b fix/issue-name
git checkout -b feat/feature-name

# Commit with clear messages
git commit -m "fix: description of what was fixed"
git commit -m "feat: description of new feature"
git commit -m "refactor: description of cleanup"
git commit -m "chore: non-code changes like config or docs"

# Merge back to main when done
git checkout main
git merge feat/feature-name
git push
git branch -d feat/feature-name
```

---

## 🛣️ Roadmap

- [ ] Fix image/narration sync overlap in renderer
- [ ] Switch to OpenAI TTS for better voice quality
- [ ] Upgrade to `gpt-image-1` medium for better image relevance
- [ ] Add text overlays and captions burned into video via ffmpeg `drawtext`
- [ ] Add background music layer
- [ ] Auto-upload to Instagram via Graph API
- [ ] Web dashboard for pipeline monitoring

---

## 🧱 Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| AI — Script | OpenAI GPT-4.1-mini |
| AI — Images | OpenAI GPT Image (gpt-image-1-mini) |
| Voice | gTTS (Google Text-to-Speech) |
| Video rendering | ffmpeg |
| Stock media | Pexels API, Pixabay API |
| News | News API |
| Database | PostgreSQL + psycopg2 |
| Environment | python-dotenv |
| Version control | Git + GitHub |

---

## 👤 Author

**Sankalp** — [@srj-dbdev](https://github.com/srj-dbdev)

8 years of database development experience, building AI-powered content automation tools.

---

## 📄 License

This project is for personal and portfolio use.
Stock media used via Pexels and Pixabay APIs under their respective free licenses.
AI-generated content via OpenAI API under OpenAI's usage policies.
