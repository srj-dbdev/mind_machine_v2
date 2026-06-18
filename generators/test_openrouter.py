from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(
api_key=os.getenv("OPENROUTER_API_KEY"),
base_url="https://openrouter.ai/api/v1"
)

try:
    response = client.chat.completions.create(
        model="openrouter/auto",
        messages=[{"role": "user","content": "Give me 3 Instagram Reel ideas about AI."}]
        )

    print("\n SUCCESS \n")
    print(response.choices[0].message.content)

except Exception as e:
    print("\nERROR\n")
    print(e)