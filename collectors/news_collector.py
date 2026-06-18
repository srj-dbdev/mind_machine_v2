import requests
import os
from dotenv import load_dotenv
from database.db import get_connection

load_dotenv()


def fetch_news():
    API_KEY = os.getenv("NEWS_API_KEY")  # FIXED NAME

    url = (
        "https://newsapi.org/v2/everything?"
        "q=artificial intelligence"
        "&language=en"
        "&sortBy=publishedAt"
        f"&apiKey={API_KEY}"
    )

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

    except Exception as e:
        print("[NEWS] Request failed:", e)
        return []

    # ---------------- SAFE GUARD ----------------
    if "articles" not in data:
        print("[NEWS] Invalid response:", data)
        return []

    articles = data["articles"][:10]

    results = []

    conn = get_connection()
    cur = conn.cursor()

    for article in articles:

        title = article.get("title", "No Title")
        url = article.get("url", "")

        # store DB
        cur.execute(
            """
            INSERT INTO topics
            (topic, source, article_url, category)
            VALUES (%s, %s, %s, %s)
            """,
            (title, "newsapi", url, "AI")
        )

        results.append({
            "title": title,
            "url": url
        })

    conn.commit()
    cur.close()
    conn.close()

    print("[NEWS] Inserted successfully")

    return results