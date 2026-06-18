import os
import json

from dotenv import load_dotenv
from openai import OpenAI

from database.db import get_connection

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPEN_AI_API_KEY")
)


def generate_script(topic, topic_id=None):
    """
    Generates a structured video plan from a news article.

    Expects:
    topic = {
        "title": "...",
        "description": "...",
        "content": "...",
        "source": {...}
    }
    """

    # --------------------------------------------------
    # Validate input
    # --------------------------------------------------

    if not isinstance(topic, dict):
        raise TypeError(
            f"generate_script() expected dict, got {type(topic).__name__}"
        )

    title = topic.get("title", "")
    description = topic.get("description", "")
    content = topic.get("content", "")

    source = ""
    source_data = topic.get("source")

    if isinstance(source_data, dict):
        source = source_data.get("name", "")

    # --------------------------------------------------
    # Prompt
    # --------------------------------------------------

    prompt = f"""
You are an expert Instagram Reel creator.

Your task is to convert ONE news article into a complete short-form video plan.

NEWS

Title:
{title}

Description:
{description}

Content:
{content}

Source:
{source}

--------------------------

Return ONLY valid JSON.

{{
    "title":"",
    "hook":"",
    "cta":"",
    "style":"",
    "music_mood":"",
    "scenes":[
        {{
            "order":1,
            "text":"",
            "keyword":"",
            "overlay":"",
            "mood":""
        }}
    ]
}}

Rules

1. Base everything ONLY on the supplied news.

2. Never invent facts.

3. Entire narration should be about 45 seconds.

4. Use between 8 and 10 scenes depending on the story.

5. Each scene should contain ONE short sentence.

6. The keyword must describe visuals specific to THIS story.

Think like a camera operator: what would you actually film for THIS story?
- Company products or assets (rocket, factory, data center)
- Specific people or roles (astronaut, surgeon, trader on floor)
- Concrete locations tied to this story (Cape Canaveral, Capitol Hill)
- Specific actions described (rocket launch, signing a bill, protest march)
- Physical objects mentioned (satellite, server rack, oil pipeline)

GOOD keywords — story-specific examples

Falcon 9 rocket
rocket launch
SpaceX launch pad
Microsoft headquarters
stock trader screen
Elon Musk
Cape Canaveral
satellite orbit
court hearing
oil refinery
soldiers marching
hospital emergency room
election ballot
solar panel farm

BAD keywords — never use these

financial district
stock exchange
business meeting
technology
economy
markets
growth
crisis
change
Breaking News
Stock rises today
Nvidia beats Microsoft

These are too generic — they could match any news story.
Always ask: would this keyword work ONLY for this story, or any story?

7. overlay should be 2-5 words.

8. mood should be one of

dramatic
positive
neutral
urgent
hopeful
serious

9. style should be one of

breaking_news
business
technology
finance
sports
world
science
politics

10. music_mood should be one of

dramatic
energetic
calm
uplifting
serious

Return JSON only.
"""

    # --------------------------------------------------
    # Call OpenAI
    # --------------------------------------------------

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError("OpenAI returned an empty response.")

    script = json.loads(content)

    # --------------------------------------------------
    # Display
    # --------------------------------------------------

    print("\n" + "=" * 60)
    print("VIDEO PLAN")
    print("=" * 60)

    print(json.dumps(script, indent=4, ensure_ascii=False))

    print("=" * 60)

    # --------------------------------------------------
    # Save to DB
    # --------------------------------------------------

    if topic_id is not None:

        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO scripts (topic_id, script_text)
            VALUES (%s, %s)
            """,
            (
                topic_id,
                json.dumps(script, ensure_ascii=False)
            )
        )

        conn.commit()

        cur.close()
        conn.close()

    return script
