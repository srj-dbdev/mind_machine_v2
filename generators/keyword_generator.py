import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPEN_AI_API_KEY")
)


def generate_keywords(topic):
    """
    Generates story-specific visual search keywords from a news headline.

    Used as a refinement step after script generation to improve
    Pexels/Pixabay search relevance.

    Expects:
    topic = a headline string or dict with "title" key
    """

    # Accept either a plain string or a dict
    if isinstance(topic, dict):
        headline = topic.get("title", "")
    else:
        headline = str(topic)

    prompt = f"""
You are generating highly specific search keywords for stock videos and images.

News headline:
{headline}

Think like a camera operator covering THIS specific story.
What would you actually point the camera at?

Generate exactly 8 keywords.

Rules:
- Be specific to THIS story, not generic finance/tech/news visuals
- 1 to 4 words only
- Must be something a camera can physically film
- Mix of: people/roles, locations, objects, actions
- Suitable for Pexels and Pixabay stock search
- Return ONLY a JSON array of 8 strings

GOOD example for "SpaceX stock debut impresses investors":
[
    "Falcon 9 rocket",
    "rocket launch",
    "SpaceX launch pad",
    "stock market screen",
    "investors applauding",
    "Elon Musk",
    "Cape Canaveral",
    "satellite orbit"
]

BAD example — never return these types:
[
    "financial district",
    "stock exchange",
    "technology",
    "business meeting",
    "economy",
    "markets",
    "growth",
    "crisis"
]

These are too generic — they match every finance story, not this one.
Always ask: would this keyword work ONLY for this story, or for any story?

Return ONLY a JSON array. No explanation, no markdown.
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "You return only a JSON object with a single key 'keywords' containing an array of strings."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    raw = json.loads(response.choices[0].message.content)

    # Handle both {"keywords": [...]} and bare [...] responses
    if isinstance(raw, dict):
        keywords = raw.get("keywords", [])
    elif isinstance(raw, list):
        keywords = raw
    else:
        keywords = []

    print("\nGenerated Keywords:")
    for kw in keywords:
        print(f"  • {kw}")

    return keywords
