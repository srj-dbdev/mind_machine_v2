import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPEN_AI_API_KEY")
)


def generate_keywords(topic):

    prompt = f"""
You are generating search keywords for stock videos.

News headline:
{topic}

Generate exactly 5 short visual search keywords.

Rules:
- 1 to 3 words only
- Things that can actually be filmed
- Suitable for Pexels stock videos
- Return ONLY a JSON array.

Example:

[
    "world economy",
    "stock market",
    "business meeting",
    "india skyline",
    "financial charts"
]
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    keywords = json.loads(response.choices[0].message.content)

    print("\nGenerated Keywords:")
    print(keywords)

    return keywords